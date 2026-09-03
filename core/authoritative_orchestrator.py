"""Single authoritative analysis entry point.

Legacy API surfaces historically invoked a separate 14-agent LangGraph while the
new customer paths invoked MythicOrchestrator. That could produce different trade
opinions for the same ticker. This adapter preserves the legacy ``analyze`` method
shape but routes it through QueryRouter -> MythicOrchestrator, making one decision
pipeline authoritative.
"""

from __future__ import annotations

from typing import Any

from agents.base_agent import AgentContext


class AuthoritativeOrchestrator:
    def __init__(self, default_research_mode: str = "DEEP") -> None:
        self.default_research_mode = default_research_mode

    async def analyze(
        self,
        ticker: str,
        query: str = "Should I buy this asset?",
        *,
        research_mode: str | None = None,
        history: list[dict[str, Any]] | None = None,
        session_id: str = "authoritative",
    ) -> dict[str, Any]:
        from agents.query_router import query_router

        mode = str(research_mode or self.default_research_mode).upper()
        if mode not in {"QUICK", "DEEP", "INSTITUTIONAL"}:
            mode = self.default_research_mode
        ctx = AgentContext(
            task=query or f"Analyze {ticker}",
            ticker=str(ticker).upper(),
            session_id=session_id,
            metadata={"research_mode": mode, "history": history or []},
        )
        result_ctx = await query_router.run(ctx)
        result = result_ctx.result or {}
        specialist_details = result.get("specialist_details", {}) or {}
        return {
            **result,
            "agent_data": specialist_details,
            "authoritative_pipeline": "QueryRouter->MythicOrchestrator",
            "legacy_pipeline_executed": False,
            "execution_authority": False,
        }


authoritative_orchestrator = AuthoritativeOrchestrator()
