from __future__ import annotations

import numpy as np
import pandas as pd

from core.systematic_research import CandidateSpec, SystematicResearchEngine


def _synthetic_ohlcv(rows: int = 620) -> pd.DataFrame:
    """Deterministic multi-regime data with trend, pullbacks and reversals."""
    index = pd.date_range("2022-01-03", periods=rows, freq="B")
    x = np.arange(rows, dtype=float)
    cyclical = 0.012 * np.sin(x / 13.0) + 0.006 * np.sin(x / 37.0)
    drift = np.where((x // 120) % 2 == 0, 0.0012, -0.00045)
    returns = drift + cyclical
    close = 100.0 * np.exp(np.cumsum(returns))
    open_ = close * (1.0 - 0.001)
    high = np.maximum(open_, close) * 1.004
    low = np.minimum(open_, close) * 0.996
    volume = np.full(rows, 1_000_000.0)
    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": volume,
        },
        index=index,
    )


def test_discover_uses_train_validation_and_untouched_test() -> None:
    df = _synthetic_ohlcv()
    engine = SystematicResearchEngine(
        min_history=260,
        max_candidates=20,
        top_k=4,
        min_robustness_score=0.0,
        bootstrap_samples=40,
        signflip_samples=40,
        seed=7,
    )

    result = engine.discover(df, ticker="TEST")

    assert result["status"] == "ok"
    assert result["ticker"] == "TEST"
    assert result["strategy_id"].startswith("systematic-")
    assert result["candidate_count"] <= 20
    assert 1 <= result["top_k"] <= 4
    assert result["data_split"]["train_bars"] > result["data_split"]["validation_bars"]
    assert result["data_split"]["test_bars"] > 0
    assert result["data_split"]["train_bars"] + result["data_split"]["validation_bars"] + result["data_split"]["test_bars"] == len(df)
    assert "untouched_test" in result
    assert "block_bootstrap" in result["statistics"]
    assert "trial_adjusted_probability" in result["statistics"]
    assert "walk_forward" in result
    assert "regime_stability" in result
    assert isinstance(result["signals"], list)
    assert result["signals"]


def test_insufficient_history_fails_closed_without_signals() -> None:
    engine = SystematicResearchEngine(
        min_history=260,
        bootstrap_samples=5,
        signflip_samples=5,
    )
    result = engine.discover(_synthetic_ohlcv(120), ticker="SHORT")

    assert result["status"] == "insufficient_history"
    assert result["systematic_gate_passed"] is False
    assert result["signals"] == []
    assert result["gate_failures"]


def test_friction_reduces_vectorized_strategy_return() -> None:
    df = _synthetic_ohlcv(400)
    close = df["Close"]
    engine = SystematicResearchEngine(
        min_history=100,
        bootstrap_samples=5,
        signflip_samples=5,
    )
    spec = CandidateSpec.make("mean_reversion", window=10, z_entry=1.0)
    position = engine._position(close, spec)

    no_friction = engine._strategy_returns(
        close,
        position,
        fee_bps=0.0,
        slippage_bps=0.0,
    )
    with_friction = engine._strategy_returns(
        close,
        position,
        fee_bps=10.0,
        slippage_bps=10.0,
    )

    assert float(with_friction.sum()) <= float(no_friction.sum())


def test_position_transitions_generate_buy_sell_and_exit_signals() -> None:
    index = pd.date_range("2026-01-01", periods=7, freq="D")
    position = pd.Series([0, 1, 1, 0, -1, -1, 0], index=index, dtype=float)

    signals = SystematicResearchEngine._signals_from_position(
        position,
        confidence=0.8,
        strategy_id="systematic-test",
    )

    assert [signal["action"] for signal in signals] == ["BUY", "EXIT", "SELL", "EXIT"]
    assert all(signal["source"] == "systematic_research" for signal in signals)
    assert all(signal["strategy_id"] == "systematic-test" for signal in signals)


def test_candidate_catalog_contains_multiple_strategy_families() -> None:
    families = {spec.family for spec in SystematicResearchEngine._candidate_specs()}
    assert {"momentum", "sma_cross", "mean_reversion", "breakout"}.issubset(families)
