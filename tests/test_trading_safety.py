from types import SimpleNamespace

import pytest

from agents.base_agent import AgentContext
from agents.risk_manager import RiskManagerAgent
from brokers.broker_router import Order, OrderSide, PaperBroker
from core.trading_safety import (
    DailyEquityTracker,
    LIVE_ACK_PHRASE,
    StrategyValidationStore,
    get_execution_status,
    normalize_candles_latest_first,
)


def _execution_settings(**overrides):
    values = {
        "PAPER_TRADE_MODE": True,
        "AUTOTRADE_ENABLED": False,
        "HYPERLIQUID_PRIVATE_KEY": None,
        "LIVE_TRADING_ACK": "",
        "REQUIRE_PROTECTIVE_ORDERS": True,
        "REQUIRE_STRATEGY_VALIDATION": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_live_execution_is_fail_closed_by_default():
    status = get_execution_status(_execution_settings())
    assert status["mode"] == "paper"
    assert status["live_execution_allowed"] is False
    assert status["blockers"]


def test_live_execution_requires_every_gate():
    status = get_execution_status(
        _execution_settings(
            PAPER_TRADE_MODE=False,
            AUTOTRADE_ENABLED=True,
            HYPERLIQUID_PRIVATE_KEY="0x-test-only",
            LIVE_TRADING_ACK=LIVE_ACK_PHRASE,
        )
    )
    assert status["mode"] == "live"
    assert status["live_execution_allowed"] is True
    assert status["blockers"] == []


def test_candles_are_normalized_latest_first():
    bars = [
        {"timestamp": 100, "close": 1},
        {"timestamp": 300, "close": 3},
        {"timestamp": 200, "close": 2},
    ]
    normalized = normalize_candles_latest_first(bars)
    assert [bar["timestamp"] for bar in normalized] == [300, 200, 100]
    assert normalized[0]["close"] == 3


def test_daily_equity_tracker_reports_loss(tmp_path):
    tracker = DailyEquityTracker(path=tmp_path / "equity.json")
    assert tracker.update(100_000) == 0
    assert tracker.update(98_000) == pytest.approx(-0.02)


def test_strategy_validation_requires_oos_and_thresholds(tmp_path, monkeypatch):
    import core.trading_safety as safety

    monkeypatch.setattr(safety.settings, "REQUIRE_STRATEGY_VALIDATION", True)
    monkeypatch.setattr(safety.settings, "STRATEGY_VALIDATION_MAX_AGE_DAYS", 30)
    monkeypatch.setattr(safety.settings, "MIN_BACKTEST_SHARPE", 1.0)
    monkeypatch.setattr(safety.settings, "MAX_BACKTEST_DRAWDOWN_PCT", 20.0)
    monkeypatch.setattr(safety.settings, "MIN_BACKTEST_WIN_RATE", 0.52)
    monkeypatch.setattr(safety.settings, "MIN_BACKTEST_TRADES", 30)
    monkeypatch.setattr(safety.settings, "MIN_BACKTEST_PROFIT_FACTOR", 1.2)

    store = StrategyValidationStore(path=tmp_path / "validation.json")
    metrics = {
        "sharpe_ratio": 1.4,
        "max_drawdown_pct": 9.0,
        "win_rate": 0.58,
        "total_trades": 45,
        "profit_factor": 1.5,
    }
    store.record("BTC", "strategy-v1", metrics, approved=True, out_of_sample_passed=True)
    assert store.check("BTC", "strategy-v1")["eligible"] is True

    store.record("ETH", "strategy-v1", metrics, approved=True, out_of_sample_passed=False)
    result = store.check("ETH", "strategy-v1")
    assert result["eligible"] is False
    assert any("Out-of-sample" in reason for reason in result["reasons"])


@pytest.mark.asyncio
async def test_paper_broker_uses_reference_price_and_friction():
    broker = PaperBroker()
    result = await broker.place_order(
        Order(
            ticker="AAPL",
            side=OrderSide.BUY,
            qty=2,
            reference_price=200.0,
        )
    )
    assert result["status"] == "FILLED"
    assert result["reference_price"] == 200.0
    assert result["fill_price"] > 200.0
    assert result["fee"] > 0
    assert result["fill_price"] != 100.0


@pytest.mark.asyncio
async def test_risk_manager_blocks_daily_loss_before_new_trade():
    agent = RiskManagerAgent()
    context = AgentContext(task="risk", ticker="BTC")
    context.observations["portfolio"] = {
        "total_value": 100_000,
        "cash": 100_000,
        "daily_pnl_pct": -0.03,
        "open_positions": [],
    }
    context.observations["signal_aggregator_result"] = {
        "verdict": "BUY",
        "confidence": 90,
        "entry_point": 100,
        "stop_loss": 95,
        "take_profit": 110,
    }
    result = await agent.act(context)
    assert result.result["decision"] == "BLOCK"
    assert "Daily loss limit" in result.result["reason"]


@pytest.mark.asyncio
async def test_risk_manager_accepts_strong_buy_label_when_other_gates_pass():
    agent = RiskManagerAgent()
    context = AgentContext(task="risk", ticker="BTC")
    context.observations.update(
        {
            "portfolio": {
                "total_value": 100_000,
                "cash": 100_000,
                "daily_pnl_pct": 0,
                "open_positions": [],
            },
            "signal_aggregator_result": {
                "verdict": "STRONG BUY",
                "confidence": 90,
                "entry_point": 100,
                "stop_loss": 95,
                "take_profit": 110,
            },
            "specialist_outputs": {
                "risk": {"risk_level": "MEDIUM", "annualized_volatility": 0.2}
            },
        }
    )
    result = await agent.act(context)
    assert result.result["decision"] == "APPROVE"
    assert result.result["stop_loss"] < result.result["entry"] < result.result["take_profit"]
