"""Advanced intelligence endpoints — debate, reflection lessons, skill optimizer.

Surfaces the TradingAgents-inspired adversarial research layer and the
SkillOpt-inspired self-training loop to the UI:
  - bull/bear debates with risk-bench sizing
  - trade lessons learned from resolved predictions
  - learned-skill training status, epochs, and validation results
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from core.logger import get_logger
from gateway.knowledge_store import knowledge_store

logger = get_logger(__name__)
router = APIRouter(prefix="/api/advanced", tags=["Advanced Intelligence"])


# ── Bull/Bear debate ──────────────────────────────────────────────────────────

@router.post("/debate/{ticker}")
async def run_debate(ticker: str, use_llm: bool = Query(True)):
    """Run a fresh bull-vs-bear debate on a ticker and return the verdict."""
    from agents.debate_engine import get_engine
    result = await get_engine().run_debate(ticker, use_llm=use_llm)
    return result.to_dict()


@router.get("/debate/records")
async def get_debate_records(ticker: str | None = Query(None), limit: int = Query(20, ge=1, le=100)):
    """Recent debate records (all tickers, or filtered)."""
    records = knowledge_store.get_recent_debates(ticker=ticker, limit=limit)
    return {"count": len(records), "records": records}


# ── Reflection memory (trade lessons) ─────────────────────────────────────────

@router.get("/lessons/{ticker}")
async def get_lessons(ticker: str, limit: int = Query(10, ge=1, le=50)):
    """Lessons learned from resolved predictions for this ticker (+ cross-ticker)."""
    from memory.reflection_memory import get_memory
    return {"ticker": ticker.upper(), "lessons": get_memory().get_lessons_for(ticker, limit=limit)}


@router.get("/lessons")
async def get_recent_lessons(limit: int = Query(20, ge=1, le=100)):
    """Most recent trade lessons across all tickers."""
    from memory.reflection_memory import get_memory
    mem = get_memory()
    return {"stats": mem.stats(), "lessons": mem.get_recent(limit=limit)}


@router.get("/lessons/report-card/{agent_name}")
async def get_agent_report_card(agent_name: str):
    """An agent's outcome track record (feeds the skill optimizer)."""
    from memory.reflection_memory import get_memory
    return get_memory().get_agent_report_card(agent_name)


# ── Skill optimizer ───────────────────────────────────────────────────────────

@router.get("/skills/status")
async def get_skill_optimizer_status():
    """Learned-skill versions, validation outcomes, and training config."""
    from self_improvement.skill_optimizer import get_optimizer
    return get_optimizer().status()


@router.post("/skills/epoch")
async def run_skill_epoch(use_llm: bool = Query(True)):
    """Run one skill-optimization epoch now (also scheduled weekly)."""
    from self_improvement.skill_optimizer import get_optimizer
    return await get_optimizer().run_epoch(use_llm=use_llm)


@router.get("/skills/learned/{agent_name}")
async def get_learned_skill(agent_name: str):
    """The current learned rules document injected into this agent's prompts."""
    from core.skill_manager import skill_manager
    content = skill_manager.get_learned_skill(agent_name)
    return {"agent": agent_name, "has_learned_skill": bool(content), "content": content}
