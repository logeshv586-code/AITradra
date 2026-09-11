from types import SimpleNamespace
import json

import pytest

from agents.base_agent import AgentContext
from agents.risk_manager import RiskManagerAgent
from core.config import Settings, settings
from core.trade_plan import build_trade_guidance, trade_economics, signal_direction
from core.trade_qualification import TradeQualificationService


def signal(**overrides):
    return {"verdict": "BUY", "confidence": 95, "entry_point": 100,
            "stop_loss": 95, "take_profit": 110, **overrides}


def risk(**overrides):
    return {"decision": "APPROVE", "entry": 100, "stop_loss": 95,
            "take_profit": 110, "suggested_position_size": 1000, **overrides}


def context(**portfolio_overrides):
    return AgentContext(task="risk", ticker="AAPL", observations={
        "portfolio": {"total_value": 100000, "cash": 100000,
                      "daily_pnl_pct": 0, "open_positions": [], **portfolio_overrides},
        "signal_aggregator_result": signal(),
    })


@pytest.mark.parametrize("direction,stop,target", [("BUY", 95, 110), ("SELL", 105, 90)])
def test_net_returns_include_adverse_fills_and_both_fees(direction, stop, target):
    actual = trade_economics(direction, 100, stop, target, fee_bps=10, slippage_bps=20)
    if direction == "BUY":
        target_pnl = 109.78 - 100.2 - (109.78 + 100.2) * .001
        stop_pnl = 94.81 - 100.2 - (94.81 + 100.2) * .001
    else:
        target_pnl = 99.8 - 90.18 - (99.8 + 90.18) * .001
        stop_pnl = 99.8 - 105.21 - (99.8 + 105.21) * .001
    assert actual["eligible"]
    assert actual["net_target_return_pct"] == pytest.approx(target_pnl)
    assert actual["stop_scenario_loss_pct"] == pytest.approx(-stop_pnl)
    assert actual["net_reward_risk"] == pytest.approx(target_pnl / -stop_pnl)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), 0, -1, None, "bad", True])
@pytest.mark.parametrize("field", ["entry", "stop", "target"])
def test_unusable_prices_fail_closed_and_serialize(value, field):
    values = {"entry": 100, "stop": 95, "target": 110, field: value}
    result = trade_economics("BUY", **values)
    assert not result["eligible"]
    json.dumps(result, allow_nan=False)


def test_small_target_loses_money_after_costs():
    result = trade_economics("BUY", 100, 99, 100.1)
    assert not result["eligible"]
    assert result["net_target_return_pct"] < 0


@pytest.mark.parametrize("bad", ["DO NOT BUY", "BUY OR SELL", "STRONG SELL NOW"])
def test_free_text_cannot_authorize_direction(bad):
    assert signal_direction({"verdict": bad}) == "HOLD"


def test_conflicting_signal_fails_closed():
    assert signal_direction(signal(direction="SELL")) == "HOLD"
    assert signal_direction(signal(verdict="HOLD", direction="BUY")) == "HOLD"


@pytest.mark.parametrize("confidence", [float("inf"), float("nan"), 101, -1, True])
def test_qualification_rejects_invalid_confidence(confidence):
    result = TradeQualificationService().qualify(
        "AAPL", signal(confidence=confidence), risk(),
        execution_status={"live_execution_allowed": False})
    assert not result.execution_allowed
    json.dumps(result.to_dict(), allow_nan=False)


def test_cost_gate_cannot_be_skipped_by_disabling_protection_setting():
    result = TradeQualificationService().qualify(
        "AAPL", signal(take_profit=100.1), risk(take_profit=100.1),
        settings_obj=SimpleNamespace(REQUIRE_PROTECTIVE_ORDERS=False),
        execution_status={"live_execution_allowed": False})
    assert not result.execution_allowed
    assert not result.gates["trade_economics"]["eligible"]


@pytest.mark.parametrize("changes", [{"price_fresh": False}, {"current_price": 105},
                                      {"risk": {}}, {"signal": {}},
                                      {"risk": risk(decision="BLOCK", reason="Daily loss stop")}])
def test_guidance_waits_on_incomplete_or_changed_review(changes):
    kwargs = dict(signal=signal(), risk=risk(), current_price=100, price_fresh=True, settings_obj=settings)
    kwargs.update(changes)
    result = build_trade_guidance(**kwargs)
    assert result["action"] == "WAIT"
    assert result["reasons"]
    assert not result["execution_authority"]


def test_complete_guidance_stays_advisory_and_distinguishes_sell():
    result = build_trade_guidance(signal(verdict="SELL", stop_loss=105, take_profit=90),
                                 risk(stop_loss=105, take_profit=90),
                                 current_price=100, price_fresh=True, settings_obj=settings)
    assert result["action"] == "SELL"
    assert not result["execution_authority"]
    assert "reduce-only" in result["sell_meaning"]
    assert "not guaranteed" in result["notice"]


@pytest.mark.asyncio
@pytest.mark.parametrize("limits", [{"daily_pnl_pct": -.05}, {"many_positions": True}])
async def test_emergency_exit_precedes_entry_breakers(limits):
    agent = RiskManagerAgent()
    positions = [{"ticker": "OTHER", "unrealized_pnl_pct": -.25}]
    if limits.get("many_positions"):
        positions *= agent.max_open_pos
    ctx = context(open_positions=positions, daily_pnl_pct=limits.get("daily_pnl_pct", 0))
    result = (await agent.act(ctx)).result
    assert result["decision"] == "FORCE_CLOSE"
    assert result["ticker"] == "OTHER"


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [("total_value", float("nan")), ("cash", float("inf")),
                                        ("daily_pnl_pct", float("nan"))])
async def test_invalid_portfolio_never_approves(field, value):
    result = (await RiskManagerAgent().act(context(**{field: value}))).result
    assert result["decision"] == "BLOCK"


@pytest.mark.asyncio
async def test_size_respects_stop_loss_budget_and_reports_actual_allocation(monkeypatch):
    monkeypatch.setattr(settings, "MAX_TRADE_RISK_PCT", .0001)
    result = (await RiskManagerAgent().act(context())).result
    assert result["decision"] == "APPROVE"
    assert 0 < result["planned_stop_loss_amount"] <= 10
    assert result["suggested_position_size"] <= 100000 * settings.MAX_POSITION_PCT
    assert result["position_pct"] == round(result["suggested_position_size"] / 100000 * 100, 2)


@pytest.mark.parametrize("field", ["MAX_TRADE_RISK_PCT", "TRADE_FEE_BPS", "TRADE_SLIPPAGE_BPS", "MIN_NET_REWARD_RISK"])
def test_nonfinite_risk_settings_are_rejected(field):
    with pytest.raises(ValueError):
        Settings(_env_file=None, **{field: float("nan")})


def test_hypothetical_account_cannot_qualify_live_execution():
    result = TradeQualificationService().qualify(
        "AAPL", signal(), risk(review_scope="paper_scenario"),
        execution_status={"live_execution_allowed": True},
        strategy_validation={"eligible": True}, precision_validation={"eligible": True})
    assert not result.live_execution_allowed
    assert "Hypothetical" in result.live_blockers[0]


def test_invalid_approved_risk_levels_do_not_fall_back_to_signal():
    result = TradeQualificationService().qualify(
        "AAPL", signal(), risk(stop_loss=0), execution_status={"live_execution_allowed": False})
    assert not result.execution_allowed
