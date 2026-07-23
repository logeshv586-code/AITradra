"""Tests for the CommodityImpactAgent causal-chain pipeline (no LLM/network needed)."""

import asyncio
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.commodity_impact_agent import (
    CommodityImpactAgent,
    classify_cause,
    detect_commodities,
    detect_direction,
    get_agent,
)


def _articles(*headlines):
    return [
        {"headline": h, "source": "TestWire", "url": "http://x", "published_at": "2026-07-23T09:00:00"}
        for h in headlines
    ]


class TestDetection:
    def test_detects_commodity_mentions(self):
        assert "tomato" in detect_commodities("Tomato prices surge 80% after floods in Karnataka")
        assert "crude_oil" in detect_commodities("Brent crude jumps 4% on OPEC supply cut")
        assert detect_commodities("Company reports record quarterly earnings") == []

    def test_word_boundary_matching(self):
        # 'corn' must not match 'corner'
        assert "corn" not in detect_commodities("Retailer opens store on the corner of Main St")
        assert "corn" in detect_commodities("Corn futures rally on drought fears")

    def test_direction_detection(self):
        assert detect_direction("Onion prices surge to record high") == "UP"
        assert detect_direction("Sugar prices crash on bumper harvest") == "DOWN"
        assert detect_direction("Committee meets to discuss wheat procurement") is None

    def test_cause_classification(self):
        cause, phrase = classify_cause("Tomato crop damaged by floods in growing regions")
        assert cause == "weather_disaster"
        cause, _ = classify_cause("Government imposes export ban on onions")
        assert cause == "policy"
        cause, _ = classify_cause("OPEC cut deepens crude supply crunch")
        assert cause == "supply_shock"


class TestCausalChain:
    def test_flood_tomato_event_builds_full_chain(self):
        """The core scenario: flood → tomato price spike → QSR stocks bearish."""
        agent = CommodityImpactAgent()
        events = agent.detect_events(_articles(
            "Tomato prices surge 80% after floods destroy crops in Karnataka",
            "Tomato costlier as heavy rain damages supply routes",
            "Vegetable inflation spikes; tomato leads the rally",
        ))
        assert len(events) == 1
        event = events[0]
        assert event.commodity == "tomato"
        assert event.direction == "UP"
        assert event.cause_type == "weather_disaster"

        impacted = {i["ticker"]: i["impact"] for i in event.impacts}
        # Domino's India buys tomatoes → margin pressure → BEARISH
        assert impacted["JUBLFOOD.NS"] == "BEARISH"

    def test_price_fall_flips_direction(self):
        agent = CommodityImpactAgent()
        events = agent.detect_events(_articles(
            "Sugar prices slump on record harvest and oversupply",
            "Sugar crashes as bumper crop floods the market",
        ))
        assert events[0].direction == "DOWN"
        impacted = {i["ticker"]: i["impact"] for i in events[0].impacts}
        # Sugar miller hurt by falling prices; beverage maker benefits
        assert impacted["BALRAMCHIN.NS"] == "BEARISH"
        assert impacted["VBL.NS"] == "BULLISH"

    def test_cause_implies_direction_without_price_verb(self):
        agent = CommodityImpactAgent()
        events = agent.detect_events(_articles(
            "Drought devastates wheat crop across northern plains",
        ))
        assert len(events) == 1
        assert events[0].direction == "UP"  # crop loss implies price up

    def test_suggestions_have_timing_and_exit_rules(self):
        agent = CommodityImpactAgent()
        events = agent.detect_events(_articles(
            "Crude oil surges 6% as OPEC announces production cut",
            "Brent hits record high on deepening supply crunch",
            "Oil price rally accelerates on inventory drawdown",
        ))
        event = events[0]
        assert event.suggestions, "expected trade suggestions"
        for s in event.suggestions:
            assert s["action"] in ("BUY", "AVOID/SELL", "WATCH")
            assert s["hold_horizon"]
            assert s["exit_rule"]
            assert s["entry_timing"]
        # Producers should be BUY candidates when crude rises with high corroboration
        buys = {s["ticker"] for s in event.suggestions if s["action"] == "BUY"}
        assert "ONGC.NS" in buys
        # Airlines should be flagged bearish
        bearish = {s["ticker"] for s in event.suggestions if s["direction"] == "BEARISH"}
        assert "INDIGO.NS" in bearish

    def test_low_corroboration_yields_watch(self):
        agent = CommodityImpactAgent()
        events = agent.detect_events(_articles("Copper edges higher"))
        # Single vague headline → low confidence → WATCH, not BUY
        assert all(s["action"] == "WATCH" for s in events[0].suggestions)

    def test_exposure_lookup(self):
        exposures = get_agent().get_exposure("JUBLFOOD.NS")
        commodities = {e["commodity"] for e in exposures}
        assert "tomato" in commodities and "onion" in commodities


class TestPersistence:
    def test_store_and_fetch_commodity_event(self):
        from gateway.knowledge_store import KnowledgeStore
        with tempfile.TemporaryDirectory() as tmp:
            store = KnowledgeStore(db_path=os.path.join(tmp, "test.db"))
            agent = CommodityImpactAgent()
            events = agent.detect_events(_articles(
                "Onion prices surge after export ban lifted supply concerns",
            ))
            row_id = store.store_commodity_event(events[0].to_dict())
            assert row_id > 0
            fetched = store.get_recent_commodity_events(hours=1)
            assert len(fetched) == 1
            assert fetched[0]["commodity"] == "onion"
            assert isinstance(fetched[0]["impacts"], list)
            assert isinstance(fetched[0]["suggestions"], list)

    def test_full_scan_pipeline_without_llm(self):
        """End-to-end: news in DB → scan → events persisted + insights stored."""
        from gateway import knowledge_store as ks_module
        from gateway.knowledge_store import KnowledgeStore
        with tempfile.TemporaryDirectory() as tmp:
            store = KnowledgeStore(db_path=os.path.join(tmp, "test.db"))
            original = ks_module.knowledge_store
            ks_module.knowledge_store = store
            try:
                store.store_news([{
                    "ticker": None,
                    "headline": "Tomato prices double after floods wipe out Karnataka crop",
                    "source": "TestWire", "url": "http://x",
                    "published_at": "2026-07-23T09:00:00",
                }])
                agent = CommodityImpactAgent()
                events = asyncio.run(agent.run_scan(lookback_hours=48, use_llm=False))
                assert len(events) == 1
                assert events[0]["commodity"] == "tomato"
                stored = store.get_recent_commodity_events(hours=1)
                assert len(stored) == 1
                insights = store.get_insights("JUBLFOOD.NS")
                assert any(i["insight_type"] == "commodity_impact" for i in insights)
            finally:
                ks_module.knowledge_store = original


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
