import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gateway.knowledge_store import knowledge_store
from gateway.local_plugin_registry import local_plugin_registry
from gateway.market_intel_router import (
    build_agent_status_payload,
    get_research_suggestions,
)


def test_local_plugin_registry_has_manifest_entries():
    plugins = local_plugin_registry.get_plugins()
    assert plugins
    assert any(plugin["id"] == "mirofish-local-mirror" for plugin in plugins)


def test_agent_status_payload_uses_live_heartbeat():
    knowledge_store.update_agent_health(
        "MacroSpecialist",
        "active",
        latency_ms=321,
        task="test mission control heartbeat",
    )

    payload = build_agent_status_payload()
    macro = next(agent for agent in payload["agents"] if agent["name"] == "MacroSpecialist")

    assert macro["status"] == "active"
    assert macro["latency_ms"] == 321
    assert macro["current_task"] == "test mission control heartbeat"
    assert payload["summary"]["total"] >= 1

    swarm = next(
        agent for agent in payload["agents"] if agent["id"] == "swarm_intelligence"
    )
    quantic = next(
        agent for agent in payload["agents"] if agent["id"] == "quantic_analysis"
    )
    strategy_gen = next(
        agent for agent in payload["agents"] if agent["id"] == "strategy_gen"
    )

    assert swarm["type"] == "v4_mythic"
    assert quantic["type"] == "specialist"
    assert strategy_gen["type"] == "specialist"


@pytest.mark.asyncio
async def test_research_suggestions_endpoint_prefers_stored_signals(monkeypatch):
    monkeypatch.setattr(
        "gateway.market_intel_router.knowledge_store.get_latest_research_suggestions",
        lambda limit=5: [
            {
                "ticker": "TSLA",
                "score": 84.2,
                "signal": "BUY",
                "reasoning": "Institutional flow and volatility compression are aligned.",
                "breakdown_json": '{"primary_driver": "technical"}',
                "perf_1m": 3.4,
                "created_at": "2026-04-17T10:00:00",
            }
        ],
    )
    monkeypatch.setattr(
        "gateway.market_intel_router.intelligence_service.get_watchlist_intelligence",
        lambda max_age_minutes=240: [],
    )

    payload = await get_research_suggestions(limit=1)

    assert payload["count"] == 1
    assert payload["suggestions"][0]["ticker"] == "TSLA"
    assert payload["suggestions"][0]["signal"] == "BUY"
    assert payload["suggestions"][0]["type"] == "QUANTIC"
