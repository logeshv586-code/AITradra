"""Commodity causal-chain intelligence endpoints.

Exposes the CommodityImpactAgent's output to the UI:
  - detected commodity events (what moved, why, and which stocks it hits)
  - actionable buy/sell suggestions with timing and exit rules
  - per-ticker commodity exposure map
  - on-demand scan trigger
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from core.logger import get_logger
from gateway.knowledge_store import knowledge_store

logger = get_logger(__name__)
router = APIRouter(prefix="/api/commodity", tags=["Commodity Intelligence"])


@router.get("/events")
async def get_commodity_events(hours: int = Query(72, ge=1, le=720), limit: int = Query(20, ge=1, le=100)):
    """Recent detected commodity events with full causal chains."""
    events = knowledge_store.get_recent_commodity_events(hours=hours, limit=limit)
    return {"count": len(events), "events": events}


@router.get("/suggestions")
async def get_commodity_suggestions(hours: int = Query(72, ge=1, le=720)):
    """Flattened, ranked trade suggestions across all recent commodity events."""
    events = knowledge_store.get_recent_commodity_events(hours=hours, limit=50)
    suggestions = []
    seen: set[tuple[str, str]] = set()
    for event in events:
        for s in event.get("suggestions", []):
            key = (s.get("ticker", ""), s.get("trigger_event", ""))
            if key in seen:
                continue  # keep only the newest suggestion per ticker+event
            seen.add(key)
            suggestions.append(s)
    order = {"BUY": 0, "AVOID/SELL": 1, "WATCH": 2}
    suggestions.sort(key=lambda s: (order.get(s.get("action"), 3), -s.get("confidence", 0)))
    return {"count": len(suggestions), "suggestions": suggestions}


@router.get("/exposure/{ticker}")
async def get_ticker_exposure(ticker: str):
    """Which commodities affect this stock, and in which direction."""
    from agents.commodity_impact_agent import get_agent
    exposures = get_agent().get_exposure(ticker)
    return {"ticker": ticker.upper(), "count": len(exposures), "exposures": exposures}


@router.post("/scan")
async def trigger_commodity_scan(lookback_hours: int = Query(48, ge=1, le=336), use_llm: bool = Query(True)):
    """Run a commodity scan now (also runs automatically on the scheduler)."""
    from agents.commodity_impact_agent import get_agent
    events = await get_agent().run_scan(lookback_hours=lookback_hours, use_llm=use_llm)
    return {"scanned": True, "events_detected": len(events), "events": events}


@router.get("/status")
async def get_commodity_status():
    """Agent status: coverage and last scan info."""
    from agents.commodity_impact_agent import get_agent
    return get_agent().status()
