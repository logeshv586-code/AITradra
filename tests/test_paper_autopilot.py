"""Tests for the PaperAutopilot: entries, exit rules, risk gates, reporting."""

import asyncio
import os
import sys
import tempfile
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class _Env:
    """Swap all singletons (knowledge store, reflection memory) onto a temp DB."""

    def __init__(self, tmp_dir):
        self.tmp_dir = tmp_dir
        self.db_path = os.path.join(tmp_dir, "test.db")

    def __enter__(self):
        from gateway import knowledge_store as ks_module
        from gateway.knowledge_store import KnowledgeStore
        import memory.reflection_memory as rm_module
        from memory.reflection_memory import ReflectionMemory

        self._ks_original = ks_module.knowledge_store
        ks_module.knowledge_store = KnowledgeStore(db_path=self.db_path)
        self.store = ks_module.knowledge_store

        self._rm_original = rm_module._memory_instance
        rm_module._memory_instance = ReflectionMemory(db_path=self.db_path)

        from agents.paper_autopilot import PaperAutopilot
        self.pilot = PaperAutopilot(db_path=self.db_path)
        return self

    def __exit__(self, *exc):
        from gateway import knowledge_store as ks_module
        import memory.reflection_memory as rm_module
        ks_module.knowledge_store = self._ks_original
        rm_module._memory_instance = self._rm_original
        return False

    def seed_price(self, ticker, close, date="2026-07-22"):
        self.store.store_daily_ohlcv(ticker, [{
            "date": date, "open": close - 1, "high": close + 1,
            "low": close - 2, "close": close, "volume": 1_000_000,
        }])

    def seed_debate_buy(self, ticker, confidence=75, size_pct=4.0):
        self.store.store_debate_record({
            "ticker": ticker, "verdict": "BUY", "confidence": confidence,
            "winning_side": "BULL", "key_reason": "test thesis",
            "mode": "rule_based", "evidence_score": 0.6, "evidence_count": 6,
            "risk_bench": {"blended_size_pct": size_pct},
            "created_at": datetime.now(timezone.utc).isoformat(),
        })


class TestAutopilotEntries:
    def test_opens_position_from_debate_buy(self):
        with tempfile.TemporaryDirectory() as tmp, _Env(tmp) as env:
            env.seed_price("AAPL", 200.0)
            env.seed_debate_buy("AAPL", confidence=75, size_pct=4.0)
            report = asyncio.run(env.pilot.run_cycle())
            entries = report["actions_this_cycle"]["entries"]
            assert len(entries) == 1
            entry = entries[0]
            assert entry["ticker"] == "AAPL"
            assert entry["entry_price"] == 200.0
            # 4% of 100k = 4000 → 20 shares @ 200
            assert entry["qty"] == 20
            assert entry["stop"] == pytest.approx(190.0)    # -5%
            assert entry["target"] == pytest.approx(220.0)  # +10%
            assert len(report["open_positions"]) == 1

    def test_low_confidence_debate_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp, _Env(tmp) as env:
            env.seed_price("TSLA", 300.0)
            env.seed_debate_buy("TSLA", confidence=40)  # below the 60 floor
            report = asyncio.run(env.pilot.run_cycle())
            assert report["actions_this_cycle"]["entries"] == []

    def test_one_entry_batch_per_day(self):
        with tempfile.TemporaryDirectory() as tmp, _Env(tmp) as env:
            env.seed_price("AAPL", 200.0)
            env.seed_debate_buy("AAPL")
            asyncio.run(env.pilot.run_cycle())
            # Fresh candidate appears same day — must NOT open another batch
            env.seed_price("MSFT", 400.0)
            env.seed_debate_buy("MSFT")
            report2 = asyncio.run(env.pilot.run_cycle())
            assert report2["actions_this_cycle"]["entries"] == []

    def test_no_doubling_into_held_ticker(self):
        with tempfile.TemporaryDirectory() as tmp, _Env(tmp) as env:
            env.seed_price("AAPL", 200.0)
            env.seed_debate_buy("AAPL")
            asyncio.run(env.pilot.run_cycle())
            # Simulate a new day by clearing the once-per-day gate
            env.pilot._get_conn().execute(
                "UPDATE autopilot_positions SET opened_at = '2026-07-20 10:00:00'")
            env.pilot._get_conn().commit()
            env.seed_debate_buy("AAPL", confidence=90)
            report = asyncio.run(env.pilot.run_cycle())
            tickers = [e["ticker"] for e in report["actions_this_cycle"]["entries"]]
            assert "AAPL" not in tickers

    def test_position_size_capped_by_platform_limit(self):
        with tempfile.TemporaryDirectory() as tmp, _Env(tmp) as env:
            env.seed_price("NVDA", 100.0)
            env.seed_debate_buy("NVDA", confidence=95, size_pct=25.0)  # absurd ask
            report = asyncio.run(env.pilot.run_cycle())
            entry = report["actions_this_cycle"]["entries"][0]
            # MAX_POSITION_PCT = 0.05 → max 5% of 100k = 5000 → 50 shares
            assert entry["qty"] == 50


class TestAutopilotExits:
    def _open_position(self, env, ticker="AAPL", price=200.0):
        env.seed_price(ticker, price)
        env.seed_debate_buy(ticker)
        asyncio.run(env.pilot.run_cycle())

    def test_stop_loss_exit_and_lesson(self):
        with tempfile.TemporaryDirectory() as tmp, _Env(tmp) as env:
            self._open_position(env, "AAPL", 200.0)
            env.seed_price("AAPL", 189.0, date="2026-07-23")  # below 190 stop
            exits = asyncio.run(env.pilot.manage_exits())
            assert len(exits) == 1
            assert exits[0]["reason"] == "STOP_LOSS"
            assert exits[0]["realized_pnl"] < 0
            # Outcome fed the lesson loop
            from memory.reflection_memory import get_memory
            lessons = get_memory().get_lessons_for("AAPL")
            assert lessons and lessons[0]["was_correct"] == 0

    def test_take_profit_exit(self):
        with tempfile.TemporaryDirectory() as tmp, _Env(tmp) as env:
            self._open_position(env, "AAPL", 200.0)
            env.seed_price("AAPL", 221.0, date="2026-07-23")  # above 220 target
            exits = asyncio.run(env.pilot.manage_exits())
            assert exits[0]["reason"] == "TAKE_PROFIT"
            assert exits[0]["realized_pnl"] > 0

    def test_time_exit_after_hold_horizon(self):
        with tempfile.TemporaryDirectory() as tmp, _Env(tmp) as env:
            self._open_position(env, "AAPL", 200.0)
            conn = env.pilot._get_conn()
            conn.execute("UPDATE autopilot_positions SET hold_until = '2026-01-01T00:00:00+00:00'")
            conn.commit()
            env.seed_price("AAPL", 201.0, date="2026-07-23")  # inside stop/target band
            exits = asyncio.run(env.pilot.manage_exits())
            assert exits[0]["reason"] == "TIME_EXIT"

    def test_report_card_contents(self):
        with tempfile.TemporaryDirectory() as tmp, _Env(tmp) as env:
            self._open_position(env, "AAPL", 200.0)
            env.seed_price("AAPL", 221.0, date="2026-07-23")
            asyncio.run(env.pilot.manage_exits())
            report = asyncio.run(env.pilot.build_report())
            assert report["closed_summary"]["count"] == 1
            assert report["closed_summary"]["win_rate"] == 1.0
            assert report["closed_summary"]["total_realized_pnl"] > 0
            assert report["balance"]["equity"] > 100_000
            assert report["risk_limits"]["stop_loss_pct"] == 5.0


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
