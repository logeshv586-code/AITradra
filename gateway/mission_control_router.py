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


class SwipeRequest(BaseModel):
    idea_id: str
    action: str

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


def _fallback_ideas() -> list[dict]:
    return [
        {
            "id": "idea_001",
            "ticker": "NVDA",
            "title": "AI infrastructure momentum scan",
            "thesis": "Check whether price strength, news catalysts, and risk remain aligned before entry.",
            "action": "WATCH",
            "confidence": 62,
        },
        {
            "id": "idea_002",
            "ticker": "AAPL",
            "title": "Large-cap quality pullback review",
            "thesis": "Review whether recent weakness is technical noise or a catalyst-led risk shift.",
            "action": "RESEARCH",
            "confidence": 55,
        },
    ]


@router.get("/ideas")
async def get_mission_ideas():
    """Compatibility endpoint for the Mission Control idea queue."""
    try:
        suggestions = knowledge_store.get_latest_research_suggestions(limit=10)
        ideas = []
        for idx, item in enumerate(suggestions):
            breakdown = {}
            if item.get("breakdown_json"):
                try:
                    breakdown = json.loads(item["breakdown_json"])
                except (TypeError, ValueError):
                    breakdown = {}
            ticker = str(item.get("ticker") or breakdown.get("ticker") or "").upper()
            if not ticker:
                continue
            ideas.append({
                "id": f"idea_{idx + 1:03d}",
                "ticker": ticker,
                "title": breakdown.get("title") or f"{ticker} research opportunity",
                "thesis": item.get("reasoning") or breakdown.get("summary") or f"Review live evidence for {ticker}.",
                "action": str(item.get("signal") or breakdown.get("signal") or "WATCH").upper(),
                "confidence": item.get("score") or breakdown.get("confidence_score") or 50,
                "source": "knowledge_store",
            })
        if not ideas:
            ideas = _fallback_ideas()
        return {"status": "online", "ideas": ideas}
    except Exception as e:
        logger.error(f"Failed to fetch mission ideas: {e}")
        return {"status": "online", "ideas": _fallback_ideas(), "source": "fallback"}


@router.post("/swipe")
async def swipe_idea(req: SwipeRequest):
    """Compatibility endpoint for swipe-style research triage."""
    action = req.action.strip().upper()
    if action not in {"YES", "NO", "MAYBE", "WATCH", "SKIP"}:
        raise HTTPException(status_code=400, detail="Unsupported swipe action")
    logger.info(f"Mission idea {req.idea_id} marked {action}")
    return {
        "status": "success",
        "idea_id": req.idea_id,
        "action": action,
        "message": "Research preference recorded",
    }

@router.post("/activate")
async def activate_suggestion(req: ActivateRequest):
    """Manually approve/activate a research suggestion (triggers Virtual Trade)."""
    try:
        from gateway.server import app
        # Trigger a simulation buy
        res = await app.state.simulation.buy_stock(req.ticker, req.amount, f"MISSION_ACTIVATE: {req.reasoning}")
        return {"status": "success", "result": res}
    except Exception as e:
        logger.error(f"Failed to activate suggestion for {req.ticker}: {e}")
        return {"status": "error", "message": str(e)}

@router.get("/status")
async def get_legacy_status():
    """Legacy endpoint for compatibility, now redirects to suggestions."""
    return {"status": "migrated", "message": "Mission Control has pivoted to Deep Research. Use /api/mission/suggestions"}
