"""Legacy AgentOrchestrator compatibility adapter.

The old 14-agent LangGraph used a different regime detector, signal path and
confidence model than V4. Keeping both active meant identical requests could
produce different trade opinions. The public constructor is retained so older
startup code does not break, but every ``analyze`` call now delegates to the one
authoritative QueryRouter -> MythicOrchestrator pipeline.

No legacy agent, HMM regime path, ML opinion, or legacy synthesis can authorize or
influence a new trading decision through this adapter.
"""

from __future__ import annotations

from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


class AgentOrchestrator:
    """Backward-compatible facade over the authoritative V4 pipeline."""

    def __init__(
        self,
        data_agent=None,
        news_agent=None,
        trend_agent=None,
        risk_agent=None,
        ml_agent=None,
        synthesis_agent=None,
        arbitrage_agent=None,
        portfolio_agent=None,
        macro_agent=None,
        social_sentiment_agent=None,
        earnings_agent=None,
        options_flow_agent=None,
        regime_detector_agent=None,
        backtest_agent=None,
        **_: Any,
    ) -> None:
        # Keep references only for diagnostics/compatibility. They are not executed
        # by analyze(). In particular, the legacy HMM regime path is retired.
        self.legacy_agents = {
            "data": data_agent,
            "news": news_agent,
            "trend": trend_agent,
            "risk": risk_agent,
            "ml": ml_agent,
            "synthesis": synthesis_agent,
            "arbitrage": arbitrage_agent,
            "portfolio": portfolio_agent,
            "macro": macro_agent,
            "social": social_sentiment_agent,
            "earnings": earnings_agent,
            "options": options_flow_agent,
            "regime": regime_detector_agent,
            "backtest": backtest_agent,
        }
        self.graph = None
        logger.info(
            "Legacy AgentOrchestrator initialized as compatibility facade; V4 Mythic pipeline is authoritative"
        )

    async def analyze(self, ticker: str, query: str = "") -> dict:
        from core.authoritative_orchestrator import authoritative_orchestrator

        logger.info(
            "Legacy analyze(%s) redirected to authoritative Mythic pipeline",
            ticker,
        )
        result = await authoritative_orchestrator.analyze(
            ticker=ticker,
            query=query or f"Analyze {ticker}",
            research_mode="DEEP",
            session_id="legacy-adapter",
        )
        return {
            "ticker": str(ticker).upper(),
            "analysis": {
                "response": result.get("response", ""),
                "consensus": result.get("consensus", "NEUTRAL"),
                "confidence": result.get("confidence", 0.0),
            },
            "agent_data": result.get("agent_data", {}),
            "errors": [result["pipeline_error"]] if result.get("pipeline_error") else [],
            "agents_executed": list((result.get("agent_data") or {}).keys()),
            "authoritative_pipeline": result.get(
                "authoritative_pipeline", "QueryRouter->MythicOrchestrator"
            ),
            "legacy_pipeline_executed": False,
            "execution_authority": False,
        }
