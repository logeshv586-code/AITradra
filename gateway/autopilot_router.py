"""Paper-trading auto-pilot endpoints — status, reports, manual controls.

The autopilot only ever talks to the PaperBroker; these endpoints cannot
place real-money orders.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Query

from core.logger import get_logger
from gateway.knowledge_store import knowledge_store

logger = get_logger(__name__)
router = APIRouter(prefix="/api/autopilot", tags=["Paper Autopilot"])


@router.get("/status")
async def get_autopilot_status():
    """Current report card: balance, open book with stops/targets, closed stats."""
    from agents.paper_autopilot import get_autopilot
    return await get_autopilot().build_report()


@router.post("/cycle")
async def run_autopilot_cycle():
    """Run one autopilot cycle now (exits → entries → report)."""
    from agents.paper_autopilot import get_autopilot
    return await get_autopilot().run_cycle()


@router.get("/history")
async def get_autopilot_history(limit: int = Query(50, ge=1, le=500)):
    """All autopilot positions, open and closed, newest first."""
    from agents.paper_autopilot import get_autopilot
    return {"positions": get_autopilot().get_trade_history(limit=limit)}


@router.get("/reports")
async def get_autopilot_reports(limit: int = Query(10, ge=1, le=50)):
    """Persisted daily report cards, newest first."""
    insights = knowledge_store.get_insights("PORTFOLIO", limit=limit)
    reports = []
    for i in insights:
        if i.get("insight_type") == "autopilot_report":
            try:
                reports.append(json.loads(i["content"]))
            except Exception:
                pass
    return {"count": len(reports), "reports": reports}


@router.post("/close/{ticker}")
async def close_position(ticker: str):
    """Manually close an open autopilot position at market."""
    from agents.paper_autopilot import get_autopilot
    pilot = get_autopilot()
    conn = pilot._get_conn()
    pos = conn.execute(
        "SELECT * FROM autopilot_positions WHERE status='open' AND ticker=?",
        (ticker.upper(),),
    ).fetchone()
    if not pos:
        raise HTTPException(status_code=404, detail=f"No open autopilot position in {ticker.upper()}")
    price = pilot._latest_price(ticker.upper())
    if price is None:
        raise HTTPException(status_code=409, detail=f"No market price available for {ticker.upper()}")
    action = await pilot._close_position(pos, price, "MANUAL")
    if not action:
        raise HTTPException(status_code=500, detail="Close order was rejected")
    return action
