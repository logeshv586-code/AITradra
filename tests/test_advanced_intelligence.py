"""Tests for the DebateEngine, ReflectionMemory, and SkillOptimizer (offline, no LLM)."""

import asyncio
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _swap_knowledge_store(tmp_dir):
    """Point the module-level knowledge_store singleton at a temp DB."""
    from gateway import knowledge_store as ks_module
    from gateway.knowledge_store import KnowledgeStore
    store = KnowledgeStore(db_path=os.path.join(tmp_dir, "test.db"))
    original = ks_module.knowledge_store
    ks_module.knowledge_store = store
    return store, original


class TestDebateEngine:
    def test_rule_based_verdict_bullish_evidence(self):
        from agents.debate_engine import DebateEngine
        engine = DebateEngine()
        evidence = {
            "bull": [f"[agent] BULLISH signal {i}" for i in range(6)],
            "bear": ["[agent] BEARISH risk flag"],
            "neutral": [],
        }
        result = engine._rule_based_verdict("AAPL", evidence)
        assert result.verdict == "BUY"
        assert result.winning_side == "BULL"
        assert result.confidence >= 50

    def test_rule_based_verdict_holds_on_conflict(self):
        from agents.debate_engine import DebateEngine
        engine = DebateEngine()
        evidence = {
            "bull": ["[a] BULLISH", "[b] BUY"],
            "bear": ["[c] BEARISH", "[d] SELL"],
            "neutral": [],
        }
        result = engine._rule_based_verdict("TSLA", evidence)
        assert result.verdict == "HOLD"
        assert result.winning_side == "DRAW"

    def test_risk_bench_blocks_hold_and_sizes_buy(self):
        from agents.debate_engine import DebateEngine, DebateResult
        hold = DebateResult(ticker="X", verdict="HOLD", confidence=40,
                            winning_side="DRAW", key_reason="")
        bench = DebateEngine.run_risk_bench(hold)
        assert bench["blended_size_pct"] == 0.0

        buy = DebateResult(ticker="X", verdict="BUY", confidence=80,
                           winning_side="BULL", key_reason="", evidence_count=8)
        bench = DebateEngine.run_risk_bench(buy)
        assert bench["blended_size_pct"] > 0
        assert bench["stances"]["aggressive"]["size_pct"] >= bench["stances"]["conservative"]["size_pct"]

    def test_full_debate_persists_record_and_insight(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, original = _swap_knowledge_store(tmp)
            try:
                # Seed bullish insights + news so the debate has evidence
                for i in range(4):
                    store.store_insight("NVDA", f"Agent{i}", "signal",
                                        "BULLISH momentum confirmed", confidence=0.8)
                store.store_news([{
                    "ticker": "NVDA", "headline": "NVDA rallies on record demand",
                    "source": "T", "sentiment_score": 0.8,
                    "published_at": "2026-07-23T09:00:00",
                }])
                from agents.debate_engine import DebateEngine
                result = asyncio.run(DebateEngine().run_debate("NVDA", use_llm=False))
                assert result.verdict == "BUY"
                assert result.mode == "rule_based"
                records = store.get_recent_debates(ticker="NVDA")
                assert len(records) == 1
                assert records[0]["verdict"] == "BUY"
                assert "risk_bench" in records[0]
                insights = store.get_insights("NVDA")
                assert any(i["insight_type"] == "debate_verdict" for i in insights)
            finally:
                from gateway import knowledge_store as ks_module
                ks_module.knowledge_store = original


class TestReflectionMemory:
    def test_lesson_written_and_retrieved(self):
        from memory.reflection_memory import ReflectionMemory
        with tempfile.TemporaryDirectory() as tmp:
            mem = ReflectionMemory(db_path=os.path.join(tmp, "test.db"))
            record = asyncio.run(mem.reflect_on_outcome(
                ticker="AAPL", source_agent="TechnicalSpecialist",
                direction="BULLISH", accuracy=0.2,
                price_at_prediction=100.0, actual_price=95.0,
                context="pre-earnings setup", use_llm=False,
            ))
            assert record["was_correct"] == 0
            assert "FAILED" in record["lesson"]

            lessons = mem.get_lessons_for("AAPL")
            assert len(lessons) == 1
            # Cross-ticker failure lessons surface for other tickers too
            cross = mem.get_lessons_for("MSFT", limit=5)
            assert any(l["ticker"] == "AAPL" for l in cross)

    def test_report_card_aggregates(self):
        from memory.reflection_memory import ReflectionMemory
        with tempfile.TemporaryDirectory() as tmp:
            mem = ReflectionMemory(db_path=os.path.join(tmp, "test.db"))
            for acc in (0.8, 0.9, 0.1):
                asyncio.run(mem.reflect_on_outcome(
                    ticker="TSLA", source_agent="MacroSpecialist",
                    direction="BULLISH", accuracy=acc,
                    price_at_prediction=100, actual_price=110, use_llm=False,
                ))
            card = mem.get_agent_report_card("MacroSpecialist")
            assert card["total_lessons"] == 3
            assert card["correct"] == 2
            assert len(card["recent_failures"]) == 1


class TestSkillOptimizer:
    def _seed_outcomes(self, mem, agent, accuracies, ticker="AAPL"):
        for acc in accuracies:
            asyncio.run(mem.reflect_on_outcome(
                ticker=ticker, source_agent=agent, direction="BULLISH",
                accuracy=acc, price_at_prediction=100, actual_price=90,
                use_llm=False,
            ))

    def test_heuristic_epoch_creates_learned_skill(self):
        from memory.reflection_memory import ReflectionMemory
        from self_improvement.skill_optimizer import SkillOptimizer
        import memory.reflection_memory as rm_module

        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "test.db")
            mem = ReflectionMemory(db_path=db)
            original = rm_module._memory_instance
            rm_module._memory_instance = mem
            try:
                # A failing agent: hit rate well below 45%
                self._seed_outcomes(mem, "TechnicalSpecialist", [0.1, 0.2, 0.3, 0.1, 0.2, 0.4])
                opt = SkillOptimizer(db_path=db, skills_dir=os.path.join(tmp, "learned"))
                results = asyncio.run(opt.run_epoch(use_llm=False))
                assert len(results["updated"]) == 1
                assert results["updated"][0]["agent"] == "TechnicalSpecialist"
                rules = opt.get_rules("TechnicalSpecialist")
                assert len(rules) == 1
                assert "confirming signals" in rules[0]
                # Version recorded with a baseline
                status = opt.status()
                assert status["versions"][0]["status"] == "active"
                assert status["versions"][0]["baseline_accuracy"] is not None
            finally:
                rm_module._memory_instance = original

    def test_validation_gate_rolls_back_degraded_version(self):
        from memory.reflection_memory import ReflectionMemory
        from self_improvement.skill_optimizer import SkillOptimizer
        import memory.reflection_memory as rm_module

        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "test.db")
            mem = ReflectionMemory(db_path=db)
            original = rm_module._memory_instance
            rm_module._memory_instance = mem
            try:
                agent = "RiskSpecialist"
                # Decent-but-low history triggers an edit epoch
                self._seed_outcomes(mem, agent, [0.4, 0.4, 0.4, 0.4, 0.4])
                opt = SkillOptimizer(db_path=db, skills_dir=os.path.join(tmp, "learned"))
                results = asyncio.run(opt.run_epoch(use_llm=False))
                assert len(results["updated"]) == 1
                assert opt.get_rules(agent), "skill doc should exist after epoch"

                # Post-activation outcomes are WORSE → validation must roll back
                self._seed_outcomes(mem, agent, [0.1, 0.1, 0.1, 0.1, 0.1])
                judged = opt.validate_active_versions()
                assert judged and judged[0]["outcome"] == "rolled_back"
                # Rolled back to nothing (no previous version existed)
                assert opt.get_rules(agent) == []
                # Rejected edits are buffered so they aren't re-proposed
                assert opt.status()["rejected_edits_buffered"] >= 1
            finally:
                rm_module._memory_instance = original

    def test_validation_gate_keeps_improved_version(self):
        from memory.reflection_memory import ReflectionMemory
        from self_improvement.skill_optimizer import SkillOptimizer
        import memory.reflection_memory as rm_module

        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "test.db")
            mem = ReflectionMemory(db_path=db)
            original = rm_module._memory_instance
            rm_module._memory_instance = mem
            try:
                agent = "MacroSpecialist"
                self._seed_outcomes(mem, agent, [0.3, 0.3, 0.3, 0.3, 0.3])
                opt = SkillOptimizer(db_path=db, skills_dir=os.path.join(tmp, "learned"))
                asyncio.run(opt.run_epoch(use_llm=False))
                # Post-activation outcomes IMPROVE → version kept
                self._seed_outcomes(mem, agent, [0.8, 0.9, 0.8, 0.9, 0.8])
                judged = opt.validate_active_versions()
                assert judged and judged[0]["outcome"] == "kept"
                assert opt.get_rules(agent), "improved skill must survive validation"
            finally:
                rm_module._memory_instance = original

    def test_apply_edits_ops(self):
        from self_improvement.skill_optimizer import SkillOptimizer
        rules = ["rule one", "rule two", "rule three"]
        edits = [
            {"op": "delete", "index": 2},
            {"op": "replace", "index": 1, "text": "rule one v2"},
            {"op": "add", "text": "rule four"},
        ]
        out = SkillOptimizer.apply_edits(rules, edits)
        assert out == ["rule one v2", "rule three", "rule four"]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
