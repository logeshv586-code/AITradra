"""Exercise real route bodies with fake services; never load/sign a live broker.

Extracting route definitions avoids starting the application's model/data stack.
The request validation, financial checks and order construction are production code.
"""
import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException
from pydantic import BaseModel, Field, ValidationError

from brokers.broker_router import Order, OrderSide, OrderType
from core.config import settings
from core.trade_plan import finite_number, build_trade_guidance, economics_for_settings


def route_namespace():
    path = Path(__file__).resolve().parents[1] / "gateway/customer_market_router.py"
    names = {"ManualOrderRequest", "ResearchRequest", "_safe_float", "_price_is_actionable",
             "_customer_brief", "_run_customer_research", "manual_trading_order"}
    tree = ast.parse(path.read_text())
    nodes = [node for node in tree.body if getattr(node, "name", None) in names]
    for node in nodes:
        node.decorator_list = []
    ns = dict(BaseModel=BaseModel, Field=Field, Literal=Literal, Any=Any,
              HTTPException=HTTPException, settings=settings, Order=Order,
              OrderSide=OrderSide, OrderType=OrderType, finite_number=finite_number,
              build_trade_guidance=build_trade_guidance, economics_for_settings=economics_for_settings)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), ns)
    return ns


def setup_route():
    ns = route_namespace()
    broker = SimpleNamespace(get_balance=AsyncMock(return_value={"total": 100000, "available": 100000}),
                             get_positions=AsyncMock(return_value=[]),
                             place_order=AsyncMock(return_value={"status": "FILLED"}))
    research = AsyncMock(return_value={"price": {"current": 100, "fresh": True}, "prediction": {}})
    ns.update(CustomerHyperliquidBroker=Mock(return_value=broker),
              _broker_connection=lambda _: {"secrets": {"private_key": "test-only"}},
              get_execution_status=lambda *a, **kw: {"live_execution_allowed": True},
              _hl_ticker=lambda s: s.upper(), _run_customer_research=research,
              DailyEquityTracker=lambda **kw: SimpleNamespace(update=lambda value: 0),
              customer_runtime=SimpleNamespace(record_history=Mock()))
    return ns, broker, research


def request(ns, **kwargs):
    values = dict(connection_id="test", ticker="BTC", side="buy", qty=1,
                  stop_loss=95, take_profit=110, confirm_live=True)
    return ns["ManualOrderRequest"](**{**values, **kwargs})


@pytest.mark.parametrize("field", ["qty", "stop_loss", "take_profit"])
@pytest.mark.parametrize("value", [float("inf"), float("nan")])
def test_manual_request_rejects_nonfinite_values(field, value):
    with pytest.raises(ValidationError):
        request(route_namespace(), **{field: value})


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["zero_equity", "infinite_equity", "missing_cash", "reserve",
                                   "stop_budget", "costs", "wrong_side", "add_on", "stale_quote"])
async def test_manual_entry_checks_never_submit_failed_plan(case):
    ns, broker, research = setup_route()
    changes = {}
    if case == "zero_equity": broker.get_balance.return_value["total"] = 0
    if case == "infinite_equity": broker.get_balance.return_value["total"] = float("inf")
    if case == "missing_cash": broker.get_balance.return_value.pop("available")
    if case == "reserve": broker.get_balance.return_value["available"] = 20000
    if case == "stop_budget": changes["qty"] = 100
    if case == "costs": changes["take_profit"] = 100.1
    if case == "wrong_side": changes["side"] = "sell"
    if case == "add_on": broker.get_positions.return_value = [{"ticker": "BTC"}]
    if case == "stale_quote": research.return_value["price"]["fresh"] = False
    with pytest.raises(HTTPException):
        await ns["manual_trading_order"](request(ns, **changes))
    broker.place_order.assert_not_awaited()


@pytest.mark.asyncio
async def test_reviewed_manual_plan_submits_expected_protection():
    ns, broker, _ = setup_route()
    result = await ns["manual_trading_order"](request(ns))
    assert result["order"]["status"] == "FILLED"
    order = broker.place_order.call_args.args[0]
    assert order.side == OrderSide.BUY
    assert (order.qty, order.stop_loss, order.take_profit) == (1, 95, 110)


@pytest.mark.asyncio
async def test_reduce_only_exit_remains_available_without_research_or_entry_checks():
    ns, broker, research = setup_route()
    result = await ns["manual_trading_order"](request(ns, reduce_only=True, side="sell", stop_loss=None, take_profit=None))
    assert result["risk_reducing_exit"]
    assert broker.place_order.call_args.args[0].reduce_only
    broker.get_balance.assert_not_awaited()
    research.assert_not_awaited()


def test_customer_brief_suppresses_buy_without_risk_review():
    ns = route_namespace()
    ns.update(intelligence_service=SimpleNamespace(to_prediction_record=lambda s: {"recommendation": "BUY"}),
              _why_it_moved=lambda *a: {"summary": "Test evidence"}, _agent_view=lambda *a: {},
              customer_runtime=SimpleNamespace(list_connections=lambda: []))
    brief = ns["_customer_brief"]({"ticker": "BTC", "price_data": {"px": 100, "source_used": "test"}}, [])
    assert brief["trade_guidance"]["action"] == "WAIT"
    assert brief["prediction"]["recommendation"] == "HOLD"
    assert not brief["prediction"]["actionable"]


@pytest.mark.asyncio
async def test_explicit_paper_account_reaches_real_risk_review():
    from agents.base_agent import AgentContext
    from agents.risk_manager import RiskManagerAgent
    ns = route_namespace()
    snapshot = {"ticker": "BTC", "price_data": {"px": 100, "source_used": "test"}}
    async def orchestrate(**kwargs):
        portfolio = kwargs["gathered_data"]["portfolio"]
        assert portfolio["scope"] == "paper_scenario"
        signal = {"verdict": "BUY", "confidence": 95, "entry_point": 100, "stop_loss": 95, "take_profit": 110}
        ctx = AgentContext(task="paper review", ticker="BTC", observations={
            "portfolio": portfolio, "signal_aggregator_result": signal})
        reviewed = (await RiskManagerAgent().act(ctx)).result
        return {"specialist_details": {"signal_aggregator": signal, "risk_manager": reviewed}}
    ns.update(intelligence_service=SimpleNamespace(refresh_ticker_intelligence=AsyncMock(return_value=snapshot),
                                                   to_prediction_record=lambda s: {}),
              data_engine=SimpleNamespace(get_news=AsyncMock(return_value=[])),
              knowledge_store=SimpleNamespace(get_recent_insights=lambda **kw: []),
              _normalized_history=lambda price: [], _why_it_moved=lambda *a: {"summary": "Test evidence"}, _agent_view=lambda *a: {},
              mythic_orchestrator=SimpleNamespace(orchestrate=orchestrate), DEFAULT_HISTORY_USER="test",
              customer_runtime=SimpleNamespace(list_connections=lambda: [], record_history=Mock()))
    result = await ns["_run_customer_research"]("BTC", ns["ResearchRequest"](paper_account_value=100000))
    assert result["trade_guidance"]["action"] == "BUY"
    assert result["trade_guidance"]["paper_account_value"] == 100000
    assert not result["trade_guidance"]["execution_authority"]
