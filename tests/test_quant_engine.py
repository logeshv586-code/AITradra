"""Tests for the QuantEngine expert upgrade: real targets, levels, setups, desk notes."""

import math
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.quant_engine import (
    atr,
    classify_regime,
    desk_note,
    expert_view,
    normalize_bars,
    rsi,
    swing_levels,
)


def _bars(closes, spread=1.0, volume=1_000_000):
    """Chronological OHLCV bars from a close series."""
    return [
        {"open": c - 0.3 * spread, "high": c + spread, "low": c - spread,
         "close": c, "volume": volume}
        for c in closes
    ]


def _uptrend(n=60, start=100.0, step=0.8):
    return _bars([start + i * step + (0.5 if i % 3 == 0 else -0.3) for i in range(n)])


def _downtrend(n=60, start=100.0, step=0.8):
    return _bars([start - i * step + (0.3 if i % 3 == 0 else -0.5) for i in range(n)])


def _range_bound(n=80, low=95.0, high=105.0):
    closes = []
    for i in range(n):
        phase = (i % 20) / 20.0
        closes.append(low + (high - low) * (phase if phase < 0.5 else 1 - phase) * 2)
    return _bars(closes)


class TestIndicators:
    def test_rsi_bounds_and_direction(self):
        up = [100 + i for i in range(30)]
        down = [130 - i for i in range(30)]
        assert rsi(up) > 70
        assert rsi(down) < 30
        assert 0 <= rsi(up) <= 100

    def test_atr_positive_and_scales_with_spread(self):
        calm = atr(_bars([100] * 30, spread=0.5))
        wild = atr(_bars([100] * 30, spread=3.0))
        assert 0 < calm < wild

    def test_regime_classification(self):
        assert classify_regime([b["close"] for b in _uptrend()]) == "TRENDING_UP"
        assert classify_regime([b["close"] for b in _downtrend()]) == "TRENDING_DOWN"
        assert classify_regime([b["close"] for b in _range_bound()]) in ("RANGE_BOUND", "VOLATILE_CHOP")

    def test_swing_levels_found_in_range(self):
        levels = swing_levels(_range_bound())
        assert levels["support"], "range should have identifiable support"
        assert levels["resistance"], "range should have identifiable resistance"
        px = _range_bound()[-1]["close"]
        assert all(s["level"] < px for s in levels["support"])
        assert all(r["level"] > px for r in levels["resistance"])

    def test_normalize_accepts_newest_first(self):
        bars = _uptrend(30)
        newest_first = [dict(b, date=f"2026-07-{30-i:02d}") for i, b in enumerate(reversed(bars))]
        norm = normalize_bars(newest_first)
        assert norm[-1]["close"] == bars[-1]["close"]


class TestExpertView:
    def test_uptrend_produces_actionable_buy_view(self):
        view = expert_view(_uptrend())
        assert view["direction"] == "UP"
        assert view["conviction"] >= 55
        plan = view["trade_plan"]
        # A real plan: stop below entry below target, positive R:R
        assert plan["stop"] < plan["entry"] < plan["target1"] <= plan["target2"]
        assert plan["risk_reward"] and plan["risk_reward"] > 0
        assert view["expected_move_pct"] > 0
        assert "trend" in view["commentary"].lower() or "uptrend" in view["commentary"].lower()

    def test_downtrend_warns_not_buys(self):
        view = expert_view(_downtrend())
        assert view["direction"] == "DOWN"
        assert view["setup"] in ("breakdown_risk", "bear_rally_fade", "oversold_reversal_watch")
        # Defensive plan: stop ABOVE entry (protecting/shorting), target below
        plan = view["trade_plan"]
        assert plan["stop"] > plan["entry"] > plan["target1"]

    def test_target_never_equals_current_price(self):
        """The bug from the screenshots: predicted price == current price."""
        for maker in (_uptrend, _downtrend, _range_bound):
            view = expert_view(maker())
            px = view["indicators"]["price"]
            assert view["trade_plan"]["target1"] != pytest.approx(px), \
                f"{maker.__name__}: target must differ from current price"

    def test_range_produces_level_based_plan(self):
        view = expert_view(_range_bound())
        plan = view["trade_plan"]
        assert plan["target1"] != plan["entry"]
        assert view["key_levels"]["support"] and view["key_levels"]["resistance"]

    def test_insufficient_data_says_so_honestly(self):
        view = expert_view(_bars([100, 101]))
        assert view["setup"] == "insufficient_data"
        assert "no trade" in view["commentary"].lower()


class TestDeskNote:
    def test_desk_note_reads_like_an_expert(self):
        view = expert_view(_uptrend())
        note = desk_note("AAPL", view, headlines=[{"headline": "AAPL beats on earnings"}])
        assert "AAPL — Desk Note" in note
        assert "Entry" in note and "Stop" in note and "T1" in note
        assert "R:R" in note
        assert "AAPL beats on earnings" in note
        assert "Conviction" in note


class TestIntelligenceServiceUpgrade:
    def _snapshot_from(self, bars, px):
        """Run the real service prediction path against a temp store."""
        from gateway import knowledge_store as ks_module
        from gateway.knowledge_store import KnowledgeStore
        from gateway.intelligence_service import IntelligenceService
        from core.quant_engine import expert_view as ev

        service = IntelligenceService.__new__(IntelligenceService)
        stats = {"points": len(bars), "sma20": 0, "sma50": 0, "rsi14": 50,
                 "annualized_volatility": 20, "change_5d": 1, "change_20d": 5,
                 "volume_ratio": 1.0, "max_drawdown": 5}
        expert = ev(bars, px)
        prediction = IntelligenceService._derive_prediction(
            service, "TEST", {"px": px}, stats, 0.0, {"score": 0.0, "top_headlines": []}, expert)
        return {
            "ticker": "TEST", "price_data": {"px": px},
            "prediction_direction": prediction["prediction_direction"],
            "expected_move_percent": prediction["expected_move_percent"],
            "confidence_score": prediction["confidence_score"],
            "expert_view": prediction["expert_view"],
            "intelligence_profile": {}, "sector": "Technology",
        }

    def test_prediction_record_has_distinct_target_and_plan(self):
        from gateway.intelligence_service import IntelligenceService
        bars = _uptrend()
        px = bars[-1]["close"]
        snapshot = self._snapshot_from(bars, px)
        service = IntelligenceService.__new__(IntelligenceService)
        record = IntelligenceService.to_prediction_record(service, snapshot)
        assert record["predicted_price"] != record["current_price"]
        assert record["stop_price"] is not None
        assert record["risk_reward"] is not None
        assert record["setup"] is not None

    def test_expert_breaks_lazy_sideways_default(self):
        """A clean uptrend must not be called SIDEWAYS by the fallback."""
        snapshot = self._snapshot_from(_uptrend(), _uptrend()[-1]["close"])
        assert snapshot["prediction_direction"] == "UP"
        assert snapshot["confidence_score"] >= 55


class TestChatFallbackUpgrade:
    def test_llm_fallback_answers_with_desk_note_from_stored_bars(self):
        from gateway import knowledge_store as ks_module
        from gateway.knowledge_store import KnowledgeStore
        with tempfile.TemporaryDirectory() as tmp:
            store = KnowledgeStore(db_path=os.path.join(tmp, "t.db"))
            original = ks_module.knowledge_store
            ks_module.knowledge_store = store
            try:
                bars = _uptrend(40)
                store.store_daily_ohlcv("NVDA", [
                    {"date": f"2026-{6 + i // 28:02d}-{i % 28 + 1:02d}", **{
                        "open": b["open"], "high": b["high"], "low": b["low"],
                        "close": b["close"], "volume": b["volume"]}}
                    for i, b in enumerate(bars)
                ])
                from llm.client import LLMClient
                client = LLMClient()
                answer = client._intelligent_fallback(
                    "TICKER: NVDA\nShould I buy NVDA now?", "", expect_json=False)
                assert "NVDA — Desk Note" in answer
                assert "Stop" in answer and "Entry" in answer

                data = client._intelligent_fallback(
                    "TICKER: NVDA\nAnalyze.", "", expect_json=True)
                assert data["signal"] in ("BULLISH", "BEARISH", "NEUTRAL")
                assert data["trade_plan"]["target1"] is not None
                assert data["confidence"] > 0.35  # better than the old canned 0.35
            finally:
                ks_module.knowledge_store = original


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
