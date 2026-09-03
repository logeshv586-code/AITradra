from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from core.portfolio_optimizer import inverse_volatility_allocation
from self_improvement.benchmark_scorecard import (
    BenchmarkScorecard,
    default_benchmark_symbol,
)
from self_improvement.shadow_trade_store import ShadowTradeStore


def test_shadow_trade_store_is_append_only_and_auditable(tmp_path):
    store = ShadowTradeStore(tmp_path / "shadow.sqlite3")
    created_at = (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
    decision = store.record_decision(
        ticker="AAPL",
        direction="BUY",
        confidence=75,
        entry_price=100,
        horizon_hours=24,
        created_at=created_at,
        evidence={"core_probability_up": 0.70},
        plugins={"finbert": {"probability_up": 0.80}},
    )
    assert decision["execution_authority"] is False
    assert len(store.pending_due()) == 1

    resolution = store.resolve(
        decision["id"],
        exit_price=105,
        price_source="test",
    )
    assert resolution["correct"] is True
    assert resolution["return_pct"] == 5.0
    assert store.audit_chain()["valid"] is True

    resolved = store.resolved_decisions()
    assert resolved[0]["evidence"]["core_probability_up"] == 0.70
    assert resolved[0]["plugin_snapshot"]["finbert"]["probability_up"] == 0.80


def test_benchmark_scorecard_requires_return_sharpe_and_drawdown():
    scorecard = BenchmarkScorecard()
    benchmark = pd.Series([0.001] * 120)
    strong = scorecard.evaluate_summary(
        {
            "total_return_pct": 20.0,
            "sharpe_ratio": 2.0,
            "max_drawdown_pct": 2.0,
            "total_trades": 30,
            "win_rate": 0.60,
            "profit_factor": 1.5,
        },
        benchmark,
        benchmark_name="SPY",
    )
    assert strong["status"] == "BEATS_BENCHMARK"
    assert strong["execution_authority"] is False

    weak = scorecard.evaluate_summary(
        {
            "total_return_pct": 1.0,
            "sharpe_ratio": 0.1,
            "max_drawdown_pct": 25.0,
        },
        benchmark,
        benchmark_name="SPY",
    )
    assert weak["status"] == "DOES_NOT_BEAT_BENCHMARK"


def test_default_benchmarks_are_market_appropriate():
    assert default_benchmark_symbol("AAPL") == "SPY"
    assert default_benchmark_symbol("RELIANCE.NS") == "^NSEI"
    assert default_benchmark_symbol("ETH-USD") == "BTC-USD"


def test_inverse_volatility_never_breaks_central_asset_cap():
    index = pd.date_range("2025-01-01", periods=80, freq="D")
    prices = pd.DataFrame(
        {
            "AAPL": 100 * np.cumprod(np.full(80, 1.001) + np.sin(np.arange(80)) * 0.001),
            "MSFT": 100 * np.cumprod(np.full(80, 1.0008) + np.cos(np.arange(80)) * 0.0015),
            "NVDA": 100 * np.cumprod(np.full(80, 1.0012) + np.sin(np.arange(80) / 2) * 0.002),
        },
        index=index,
    )
    result = inverse_volatility_allocation(prices, max_weight=0.05)
    assert result["available"] is True
    assert result["weights"]
    assert max(result["weights"].values()) <= 0.05
