"""Mission Control Router — Deep Research & Stock Suggestions API."""

import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from gateway.knowledge_store import knowledge_store
from core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/mission", tags=["Mission Control"])

class ActivateRequest(BaseModel):
    ticker: str
    amount: float = 1000.0
    reasoning: str = ""

@router.get("/suggestions")
async def get_research_suggestions():
    """Fetch the latest high-conviction deep research suggestions."""
    try:
        suggestions = knowledge_store.get_latest_research_suggestions(limit=10)
        # Parse breakdown_json
        for s in suggestions:
            if s.get("breakdown_json"):
                s["breakdown"] = json.loads(s["breakdown_json"])
        
        return {
            "status": "online",
            "suggestions": suggestions
        }
    except Exception as e:
        logger.error(f"Failed to fetch research suggestions: {e}")
        raise HTTPException(status_code=500, detail="Internal research failure")

@router.post("/activate")
async def activate_suggestion(req: ActivateRequest):
    """Manually approve/activate a research suggestion (triggers Virtual Trade)."""
    try:
        from gateway.server import app
        # Trigger a simulation buy
        res = app.state.simulation.buy_stock(req.ticker, req.amount, f"MISSION_ACTIVATE: {req.reasoning}")
        return {"status": "success", "result": res}
    except Exception as e:
        logger.error(f"Failed to activate suggestion for {req.ticker}: {e}")
        return {"status": "error", "message": str(e)}

@router.get("/status")
async def get_legacy_status():
    """Legacy endpoint for compatibility, now redirects to suggestions."""
    return {"status": "migrated", "message": "Mission Control has pivoted to Deep Research. Use /api/mission/suggestions"}
