"""Tests for AitradraPrime — the unified master agent (offline, no LLM)."""

import asyncio
import os
import sys
import tempfile
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class _Env:
    def __init__(self, tmp_dir):
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
        return self

    def __exit__(self, *exc):
        from gateway import knowledge_store as ks_module
        import memory.reflection_memory as rm_module
        ks_module.knowledge_store = self._ks_original
        rm_module._memory_instance = self._rm_original
        return False

    def seed_bullish_world(self, ticker="NVDA", price=100.0):
        """Uptrend + bullish specialists + positive news = a clean BUY setup."""
        now = datetime.now(timezone.utc)
        records = []
        for i in range(21):
            px = price * (0.90 + i * 0.005)  # steady uptrend into `price`
            records.append({"date": f"2026-07-{i+1:02d}", "open": px, "high": px + 1,
                            "low": px - 1, "close": px, "volume": 1_000_000})
        self.store.store_daily_ohlcv(ticker, records)
        for agent in ("TechnicalSpecialist", "MacroSpecialist", "SentimentSpecialist"):
            self.store.store_insight(ticker, agent, "signal",
                                     "BULLISH — momentum and breadth confirm", confidence=0.8)
        self.store.store_news([{
            "ticker": ticker, "headline": f"{ticker} rallies on record demand",
            "source": "wire", "sentiment_score": 0.8,
            "published_at": now.isoformat(),
        }])


class TestUnifiedVerdict:
    def test_bullish_world_produces_buy_with_full_trade_plan(self):
        with tempfile.TemporaryDirectory() as tmp, _Env(tmp) as env:
            env.seed_bullish_world("NVDA")
            from agents.master_agent import get_master
            v = asyncio.run(get_master().analyze("NVDA", use_llm=False))
            assert v.verdict == "BUY"
            assert v.confidence >= 55
            # All five components reported in
            assert set(v.components) == {"debate", "specialists", "commodity", "momentum", "news"}
            assert v.components["specialists"]["signal"] > 0
            assert v.components["momentum"]["signal"] > 0
            # One coherent trade plan
            assert v.entry_price is not None
            assert v.stop_price < v.entry_price < v.target_price
            assert 0 < v.position_size_pct <= 5.0
            assert v.narrative and "NVDA" in v.narrative

    def test_conflicting_world_holds(self):
        with tempfile.TemporaryDirectory() as tmp, _Env(tmp) as env:
            env.store.store_insight("TSLA", "TechnicalSpecialist", "signal", "BULLISH breakout")
            env.store.store_insight("TSLA", "RiskSpecialist", "signal", "BEARISH — extreme risk")
            from agents.master_agent import get_master
            v = asyncio.run(get_master().analyze("TSLA", use_llm=False))
            assert v.verdict == "HOLD"
            assert v.position_size_pct == 0.0

    def test_dissent_is_surfaced_as_named_risk(self):
        with tempfile.TemporaryDirectory() as tmp, _Env(tmp) as env:
            env.seed_bullish_world("AAPL")
            # A commodity event that hurts AAPL while everything else is bullish
            env.store.store_commodity_event({
                "commodity": "crude_oil", "direction": "UP", "cause_type": "supply_shock",
                "cause_detail": "supply crunch", "confidence": 0.9,
                "headlines": [], "suggestions": [],
                "impacts": [{"ticker": "AAPL", "relation": "input-cost consumer",
                             "impact": "BEARISH", "reasoning": "component cost pressure"}],
                "detected_at": datetime.now(timezone.utc).isoformat(),
            })
            from agents.master_agent import get_master
            v = asyncio.run(get_master().analyze("AAPL", use_llm=False))
            assert v.components["commodity"]["signal"] < 0
            assert any("commodity" in r for r in v.risks)

    def test_verdict_persisted_to_intelligence_and_insights(self):
        with tempfile.TemporaryDirectory() as tmp, _Env(tmp) as env:
            env.seed_bullish_world("NVDA")
            from agents.master_agent import get_master
            asyncio.run(get_master().analyze("NVDA", use_llm=False))
            snap = env.store.get_ticker_intelligence("NVDA")
            assert snap["agent"] == "AitradraPrime"
            assert snap["recommendation"] == "BUY"
            assert snap["should_invest"] is True
            insights = env.store.get_insights("NVDA")
            assert any(i["insight_type"] == "prime_verdict" for i in insights)


class TestPrimeFeedsAutopilot:
    def test_autopilot_trades_from_prime_verdict(self):
        with tempfile.TemporaryDirectory() as tmp, _Env(tmp) as env:
            env.seed_bullish_world("NVDA", price=100.0)
            from agents.master_agent import get_master
            asyncio.run(get_master().analyze("NVDA", use_llm=False))

            from agents.paper_autopilot import PaperAutopilot
            pilot = PaperAutopilot(db_path=env.db_path)
            report = asyncio.run(pilot.run_cycle())
            entries = report["actions_this_cycle"]["entries"]
            assert len(entries) == 1
            assert entries[0]["ticker"] == "NVDA"
            assert entries[0]["source"] == "prime"


class TestDailyBriefing:
    def test_briefing_rolls_everything_into_one_report(self):
        with tempfile.TemporaryDirectory() as tmp, _Env(tmp) as env:
            env.seed_bullish_world("NVDA")
            from agents.master_agent import get_master
            master = get_master()
            asyncio.run(master.analyze("NVDA", use_llm=False))
            briefing = asyncio.run(master.daily_briefing(tickers=["NVDA"]))
            assert briefing["agent"] == "AitradraPrime"
            assert briefing["headline"]
            assert briefing["top_picks"][0]["ticker"] == "NVDA"
            assert briefing["portfolio"] is not None  # autopilot balance folded in
            assert "learning" in briefing and "commodity_watch" in briefing
            # Persisted for the history endpoint
            stored = env.store.get_insights("PORTFOLIO")
            assert any(i["insight_type"] == "prime_briefing" for i in stored)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
