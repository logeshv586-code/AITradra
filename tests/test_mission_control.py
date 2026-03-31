import pytest
import asyncio
from httpx import AsyncClient
from gateway.server import app
from gateway.knowledge_store import knowledge_store

@pytest.mark.asyncio
async def test_mission_ideas():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/mission/ideas")
    assert response.status_code == 200
    data = response.json()
    assert "ideas" in data
    assert len(data["ideas"]) > 0

@pytest.mark.asyncio
async def test_swipe_action():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/api/mission/swipe", json={"idea_id": "idea_001", "action": "YES"})
    assert response.status_code == 200
    assert response.json()["status"] == "success"

@pytest.mark.asyncio
async def test_episode_persistence():
    session_id = "test_session_123"
    knowledge_store.store_episode_start(session_id, "TestAgent", "Test Task")
    knowledge_store.update_episode_checkpoint(session_id, "TestAgent", {"progress": 50})
    
    state = knowledge_store.get_episode_state(session_id, "TestAgent")
    assert state == {"progress": 50}
    
    knowledge_store.complete_episode(session_id, "TestAgent", {"final": "done"})
    # Verify status in DB (manual query or helper)
    # Check if active episodes filters it out
    active = knowledge_store.get_active_episodes()
    assert not any(e["session_id"] == session_id and e["agent_name"] == "TestAgent" for e in active)
