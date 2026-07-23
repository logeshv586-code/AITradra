"""AitradraPrime endpoints — the platform's single unified voice.

One agent, one verdict, one report: Prime fuses the specialist fleet,
commodity causal chains, the bull/bear debate, price momentum, news
sentiment, and past trade lessons into a single accuracy-weighted answer.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Query

from core.logger import get_logger
from gateway.knowledge_store import knowledge_store

logger = get_logger(__name__)
router = APIRouter(prefix="/api/prime", tags=["AITradra Prime"])


@router.post("/analyze/{ticker}")
async def prime_analyze(ticker: str, use_llm: bool = Query(True)):
    """Run the full unified analysis: every subsystem votes, Prime speaks once."""
    from agents.master_agent import get_master
    verdict = await get_master().analyze(ticker, use_llm=use_llm)
    return verdict.to_dict()


@router.get("/verdict/{ticker}")
async def prime_latest_verdict(ticker: str):
    """The latest stored unified verdict without re-running analysis."""
    snap = knowledge_store.get_ticker_intelligence(ticker.upper())
    if snap and snap.get("agent") == "AitradraPrime":
        return snap
    return {"ticker": ticker.upper(), "verdict": None,
            "detail": "No Prime verdict yet — POST /api/prime/analyze/{ticker} to generate one"}


@router.get("/briefing")
async def prime_briefing():
    """The daily portfolio briefing: picks, paper P&L, commodity watch, lessons."""
    from agents.master_agent import get_master
    return await get_master().daily_briefing()


@router.get("/briefings/history")
async def prime_briefing_history(limit: int = Query(7, ge=1, le=30)):
    """Previously persisted briefings, newest first."""
    insights = knowledge_store.get_insights("PORTFOLIO", limit=limit * 3)
    briefings = []
    for i in insights:
        if i.get("insight_type") == "prime_briefing":
            try:
                briefings.append(json.loads(i["content"]))
            except Exception:
                pass
        if len(briefings) >= limit:
            break
    return {"count": len(briefings), "briefings": briefings}
