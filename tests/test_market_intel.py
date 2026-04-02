import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gateway.knowledge_store import knowledge_store
from gateway.local_plugin_registry import local_plugin_registry
from gateway.market_intel_router import build_agent_status_payload


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
