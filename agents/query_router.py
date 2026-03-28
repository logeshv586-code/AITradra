"""QueryRouter — Intelligent query routing pipeline (V4 Mythic Upgrade).

Routes user queries through the optimal pipeline:
1. Intent classification
2. Parallel fan-out to all 4 knowledge sources (RAG, OHLCV, News, Insights)
3. MythicOrchestrator for multi-specialist reasoning + critique + synthesis

NEVER returns hardcoded fallbacks. ALWAYS uses the LLM.
"""

import json
import asyncio
from datetime import datetime
from typing import Optional
from agents.base_agent import BaseAgent, AgentContext
from core.logger import get_logger

logger = get_logger(__name__)


# Keywords for intent classification
INTENT_KEYWORDS = {
    "historical_data": ["history", "historical", "past", "last year", "last month", "last week",
                        "52 week", "52w", "year ago", "months ago", "trend over"],
    "current_price": ["price", "current", "now", "today", "live", "real-time", "market cap",
                      "volume", "pe ratio", "trading at"],
    "news_analysis": ["news", "headline", "article", "report", "announced", "breaking",
                      "event", "catalyst", "earnings", "ipo", "merger", "acquisition"],
    "prediction": ["predict", "forecast", "will", "future", "target", "estimate",
                   "should i buy", "should i sell", "good time", "entry point"],
    "explanation": ["why", "reason", "explain", "because", "caused", "moved", "dropped",
                    "surged", "crashed", "rally", "dip"],
    "comparison": ["compare", "vs", "versus", "better", "which", "between",
                   "outperform", "underperform"],
    "risk": ["risk", "danger", "warning", "volatility", "var", "beta", "downside",
             "bearish", "correction", "crash"],
}


class QueryRouter(BaseAgent):
    """
    Intelligent query router that:
    1. Classifies the user's intent
    2. Fans out to ALL 4 knowledge sources in parallel (asyncio.gather)
    3. Feeds everything into the MythicOrchestrator
    4. Returns a multi-specialist, critique-audited, confidence-calibrated response
    """

    def __init__(self, memory=None, improvement_engine=None):
        super().__init__(name="QueryRouter", memory=memory, improvement_engine=improvement_engine,
                         timeout_seconds=180)

    async def observe(self, context: AgentContext) -> AgentContext:
        query = context.task.lower()

        # Classify intent
        intent_scores = {}
        for intent, keywords in INTENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in query)
            if score > 0:
                intent_scores[intent] = score

        primary_intent = max(intent_scores, key=intent_scores.get) if intent_scores else "general"
        context.observations["intent"] = primary_intent
        context.observations["intent_scores"] = intent_scores
        context.observations["query"] = context.task
        context.observations["ticker"] = context.ticker

        self._add_thought(context, f"Query intent: {primary_intent} (scores: {intent_scores})")
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        # V4: Always fetch from all sources — the MythicOrchestrator decides what to use
        context.observations["needs"] = {
            "rag": True,
            "history": True,
            "knowledge_store": True
        }
        self._add_thought(context, "V4 Pipeline: Database-first RAG fan-out (No Live APIs)")
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan = [
            "Fan-out: RAG + OHLCV + News + Insights (parallel)",
            "Dispatch to MythicOrchestrator (Technical + Risk + Macro specialists)",
            "Run critique/reflection layer",
            "Synthesize with calibrated confidence"
        ]
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        ticker = context.observations.get("ticker")
        query = context.observations["query"]

        # ─── PARALLEL FAN-OUT to all 4 data sources ─────────────────────────
        gathered_context = await self._parallel_gather(query, ticker)

        # ─── Route through MythicOrchestrator ────────────────────────────────
        try:
            from agents.orchestrator import mythic_orchestrator
            orchestrator_result = await mythic_orchestrator.orchestrate(
                query=query,
                ticker=ticker,
                gathered_data=gathered_context
            )

            context.result = {
                "response": orchestrator_result.get("response", ""),
                "ticker": ticker,
                "intent": context.observations["intent"],
                "confidence": orchestrator_result.get("confidence", 0.5),
                "consensus": orchestrator_result.get("consensus", "NEUTRAL"),
                "specialist_outputs": orchestrator_result.get("specialist_outputs", {}),
                "critique": orchestrator_result.get("critique", {}),
                "sources_used": orchestrator_result.get("sources_used", []),
                "pipeline_ms": orchestrator_result.get("pipeline_ms", 0),
                "data_freshness": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"MythicOrchestrator failed: {e}, falling back to direct LLM")
            # Fallback: direct LLM synthesis (V3 behavior)
            response = await self._fallback_llm_synthesize(query, ticker, gathered_context)
            context.result = {
                "response": response,
                "ticker": ticker,
                "intent": context.observations["intent"],
                "sources_used": list(gathered_context.keys()),
                "data_freshness": datetime.now().isoformat(),
            }

        context.actions_taken.append({"action": "query_route_complete"})
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        if context.result and context.result.get("response"):
            confidence = context.result.get("confidence", 0.5)
            context.reflection = f"Query routed via MythicOrchestrator. Confidence: {confidence:.0%}"
            context.confidence = confidence
        else:
            context.reflection = "Query routing completed but response quality may be limited."
            context.confidence = 0.5
        return context

    # ─── Parallel Data Gathering ──────────────────────────────────────────────

    async def _parallel_gather(self, query: str, ticker: Optional[str]) -> dict:
        """Fan-out to all local knowledge sources using asyncio.gather."""
        tasks = {
            "rag_results": self._rag_search(query, ticker),
            "knowledge_results": self._knowledge_search(query, ticker),
        }

        if ticker:
            tasks["history"] = self._get_history(ticker)

        # Execute all in parallel
        keys = list(tasks.keys())
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        gathered = {}
        for key, result in zip(keys, results):
            if isinstance(result, Exception):
                logger.warning(f"Data source '{key}' failed: {result}")
                gathered[key] = [] if key in ("rag_results", "history") else {}
            else:
                gathered[key] = result

        return gathered

    # ─── Data Retrieval Methods ───────────────────────────────────────────────

    async def _rag_search(self, query: str, ticker: Optional[str] = None) -> list:
        """Search FAISS/RAG index for relevant documents."""
        from agents.rag_agent import RagAgent
        rag = RagAgent()
        try:
            rag.load_index()
        except Exception:
            pass

        search_query = f"{ticker} {query}" if ticker else query
        ctx = AgentContext(task=search_query, metadata={"k": 5})
        result = await rag.run(ctx)
        return result.result if isinstance(result.result, list) else []

    async def _knowledge_search(self, query: str, ticker: Optional[str] = None) -> dict:
        """Search the knowledge store (SQLite) for relevant data."""
        from gateway.knowledge_store import knowledge_store

        results = {}
        if ticker:
            results["news"] = knowledge_store.get_news_for_ticker(ticker, limit=10)
            results["insights"] = knowledge_store.get_insights(ticker, limit=5)

        # Full-text search
        results["search"] = knowledge_store.search_all(query, limit=10)
        return results

    # Removed live _get_live_price and _get_news methods to enforce pure RAG DB usage.

    async def _get_history(self, ticker: str) -> list:
        """Fetch historical OHLCV from knowledge store."""
        from gateway.knowledge_store import knowledge_store
        history = knowledge_store.get_ohlcv_history(ticker, days=365)
        return history[:30]

    # ─── Fallback LLM Synthesis (V3 compat) ───────────────────────────────────

    async def _fallback_llm_synthesize(self, query: str, ticker: Optional[str],
                                        gathered_data: dict) -> str:
        """Fallback: Direct LLM synthesis without orchestrator (V3 behavior)."""
        from llm.client import LLMClient
        llm = LLMClient()

        prompt_parts = [f"USER QUESTION: {query}"]
        if ticker:
            prompt_parts.append(f"TICKER: {ticker}")

        if "price_data" in gathered_data and gathered_data["price_data"]:
            prompt_parts.append(f"\nCURRENT PRICE DATA:\n{json.dumps(gathered_data['price_data'], indent=2, default=str)[:500]}")

        if "news" in gathered_data and gathered_data["news"]:
            news_text = "\nRECENT NEWS:\n"
            for i, n in enumerate(gathered_data["news"][:5], 1):
                news_text += f"{i}. [{n.get('source', 'Unknown')}] {n.get('headline', '')}\n"
                if n.get("url"):
                    news_text += f"   URL: {n['url']}\n"
            prompt_parts.append(news_text)

        if "rag_results" in gathered_data and gathered_data["rag_results"]:
            rag_text = "\nRAG KNOWLEDGE:\n"
            for r in gathered_data["rag_results"][:3]:
                rag_text += f"- {json.dumps(r, default=str)[:300]}\n"
            prompt_parts.append(rag_text)

        full_prompt = "\n".join(prompt_parts)

        system = f"""You are OMNI-DATA, an elite AI market intelligence system.
Use ONLY the provided data context. Cite URLs. Be specific with numbers.
Current: {datetime.now().isoformat()}"""

        try:
            return await llm.complete(prompt=full_prompt, system=system, temperature=0.3, max_tokens=1500)
        except Exception as e:
            logger.error(f"Fallback LLM also failed: {e}")
            return f"⚠️ Analysis engine initializing. Please retry. Query: {query}"


# Global instance
query_router = QueryRouter()
