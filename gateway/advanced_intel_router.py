"""Advanced intelligence endpoints — research council, scorecard, debate and lessons."""

from __future__ import annotations

from fastapi import APIRouter, Query

from gateway.knowledge_store import knowledge_store

router = APIRouter(prefix="/api/advanced", tags=["Advanced Intelligence"])


# ── Research Council V2 ──────────────────────────────────────────────────────

@router.post("/research/{ticker}")
async def run_research_council(
    ticker: str,
    as_of: str | None = Query(
        None,
        description="Optional ISO-8601 point-in-time cutoff. Newer evidence is excluded.",
    ),
    use_llm_debate: bool = Query(True),
):
    """Run provenance-aware research with an optional bounded bull/bear debate."""
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
        description="Optional ISO-8601 point-in-time cutoff. Newer evidence is excluded.",
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
        "live_gate_eligible": False,
    }


@router.post("/research/scorecard/evaluate")
async def evaluate_research_scorecard():
    """Resolve audit-grade research outcomes from later market sessions.

    This evaluates research quality only. Results never feed the autonomous live
    precision gate or broker authorization.
    """
    from self_improvement.research_scorecard import research_scorecard

    result = research_scorecard.evaluate_pending()
    return {
        **result,
        "live_gate_input": False,
        "execution_authority": False,
    }


@router.get("/research/scorecard")
async def get_research_scorecard(
    horizon_sessions: int = Query(5, ge=1, le=120),
    outcome_limit: int = Query(20, ge=1, le=200),
):
    """Return forward research calibration/alpha metrics and recent outcomes."""
    from self_improvement.research_scorecard import research_scorecard

    return {
        "summary": research_scorecard.summary(horizon_sessions=horizon_sessions),
        "recent_outcomes": research_scorecard.recent_outcomes(limit=outcome_limit),
        "note": (
            "Research scorecard metrics are forward research evidence, not a "
            "profitability guarantee and not autonomous-live permission."
        ),
    }


# ── Bull/Bear debate ─────────────────────────────────────────────────────────

@router.post("/debate/{ticker}")
async def run_debate(ticker: str, use_llm: bool = Query(True)):
    """Run the legacy/adversarial bull-vs-bear debate directly."""
    from agents.debate_engine import get_engine

    result = await get_engine().run_debate(ticker, use_llm=use_llm)
    return result.to_dict()


@router.get("/debate/records")
async def get_debate_records(
    ticker: str | None = Query(None), limit: int = Query(20, ge=1, le=100)
):
    records = knowledge_store.get_recent_debates(ticker=ticker, limit=limit)
    return {"count": len(records), "records": records}


# ── Reflection memory ────────────────────────────────────────────────────────

@router.get("/lessons/{ticker}")
async def get_lessons(ticker: str, limit: int = Query(10, ge=1, le=50)):
    from memory.reflection_memory import get_memory

    return {
        "ticker": ticker.upper(),
        "lessons": get_memory().get_lessons_for(ticker, limit=limit),
    }


@router.get("/lessons")
async def get_recent_lessons(limit: int = Query(20, ge=1, le=100)):
    from memory.reflection_memory import get_memory

    mem = get_memory()
    return {"stats": mem.stats(), "lessons": mem.get_recent(limit=limit)}


@router.get("/lessons/report-card/{agent_name}")
async def get_agent_report_card(agent_name: str):
    from memory.reflection_memory import get_memory

    return get_memory().get_agent_report_card(agent_name)


# ── Skill optimizer ──────────────────────────────────────────────────────────

@router.get("/skills/status")
async def get_skill_optimizer_status():
    from self_improvement.skill_optimizer import get_optimizer

    return get_optimizer().status()


@router.post("/skills/epoch")
async def run_skill_epoch(use_llm: bool = Query(True)):
    from self_improvement.skill_optimizer import get_optimizer

    return await get_optimizer().run_epoch(use_llm=use_llm)


@router.get("/skills/learned/{agent_name}")
async def get_learned_skill(agent_name: str):
    from core.skill_manager import skill_manager

    content = skill_manager.get_learned_skill(agent_name)
    return {
        "agent": agent_name,
        "has_learned_skill": bool(content),
        "content": content,
    }
