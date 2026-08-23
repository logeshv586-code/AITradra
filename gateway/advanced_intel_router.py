"""Advanced intelligence endpoints — research council, debate, lessons and skill optimizer.

The Research Council V2 adds point-in-time, provenance-weighted evidence and a
structured research-manager decision on top of the existing TradingAgents-inspired
bull/bear debate.  All outputs are advisory and carry no execution authority.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from core.logger import get_logger
from gateway.knowledge_store import knowledge_store

logger = get_logger(__name__)
router = APIRouter(prefix="/api/advanced", tags=["Advanced Intelligence"])


# ── Research Council V2 ──────────────────────────────────────────────────────

@router.post("/research/{ticker}")
async def run_research_council(
    ticker: str,
    as_of: str | None = Query(
        None,
        description="Optional ISO-8601 point-in-time cutoff. Evidence newer than this is excluded.",
    ),
    use_llm_debate: bool = Query(True),
):
    """Run leakage-safe research synthesis with optional bounded bull/bear debate."""
    from agents.research_council import get_research_council

    result = await get_research_council().analyze(
        ticker,
        as_of=as_of,
        use_llm_debate=use_llm_debate,
        persist=True,
    )
    return result.to_dict()


@router.get("/research/{ticker}/evidence")
async def get_research_evidence(
    ticker: str,
    as_of: str | None = Query(
        None,
        description="Optional ISO-8601 point-in-time cutoff. Evidence newer than this is excluded.",
    ),
):
    """Inspect the exact deduplicated evidence pack used by Research Council V2."""
    from agents.research_council import get_research_council

    pack = get_research_council().build_evidence_pack(ticker, as_of=as_of)
    return {
        "ticker": pack["ticker"],
        "as_of": pack["as_of"],
        "benchmark_context": pack["benchmark_context"],
        "evidence_count": len(pack["items"]),
        "items": [item.to_dict() for item in pack["items"]],
        "execution_authority": False,
    }


# ── Bull/Bear debate ─────────────────────────────────────────────────────────

@router.post("/debate/{ticker}")
async def run_debate(ticker: str, use_llm: bool = Query(True)):
    """Run a fresh bull-vs-bear debate on a ticker and return the verdict."""
    from agents.debate_engine import get_engine
    result = await get_engine().run_debate(ticker, use_llm=use_llm)
    return result.to_dict()


@router.get("/debate/records")
async def get_debate_records(ticker: str | None = Query(None), limit: int = Query(20, ge=1, le=100)):
    """Recent debate/research records (all tickers, or filtered)."""
    records = knowledge_store.get_recent_debates(ticker=ticker, limit=limit)
    return {"count": len(records), "records": records}


# ── Reflection memory (trade lessons) ────────────────────────────────────────

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


# ── Skill optimizer ──────────────────────────────────────────────────────────

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
