"""QueryRouter — single V4 authoritative research path.

All research modes now gather the same point-in-time/local evidence and enter the
same MythicOrchestrator. QUICK reduces depth inside Mythic; it no longer bypasses
the specialist/risk pipeline with a separate direct-LLM opinion.
"""

from __future__ import annotations

import json
import asyncio
from datetime import datetime
from typing import Optional

from agents.base_agent import BaseAgent, AgentContext
from core.logger import get_logger
from agents.collector_agent import fetch_ticker as _collector_fetch_ticker

logger = get_logger(__name__)


INTENT_KEYWORDS = {
    "historical_data": ["history", "historical", "past", "last year", "last month", "last week", "52 week", "52w", "year ago", "months ago", "trend over"],
    "current_price": ["price", "current", "now", "today", "live", "real-time", "market cap", "volume", "pe ratio", "trading at"],
    "news_analysis": ["news", "headline", "article", "report", "announced", "breaking", "event", "catalyst", "earnings", "ipo", "merger", "acquisition"],
    "prediction": ["predict", "forecast", "will", "future", "target", "estimate", "should i buy", "should i sell", "good time", "entry point"],
    "explanation": ["why", "reason", "explain", "because", "caused", "moved", "dropped", "surged", "crashed", "rally", "dip"],
    "comparison": ["compare", "vs", "versus", "better", "which", "between", "outperform", "underperform"],
    "risk": ["risk", "danger", "warning", "volatility", "var", "beta", "downside", "bearish", "correction", "crash"],
}


class QueryRouter(BaseAgent):
    def __init__(self, memory=None, improvement_engine=None):
        super().__init__(
            name="QueryRouter",
            memory=memory,
            improvement_engine=improvement_engine,
            timeout_seconds=180,
        )

    async def observe(self, context: AgentContext) -> AgentContext:
        query = context.task.lower()
        found_ticker = await self._extract_ticker_from_query(context.task)
        if found_ticker:
            if context.ticker and found_ticker.upper() != context.ticker.upper():
                self._add_thought(
                    context,
                    f"User mentioned {found_ticker.upper()}; overriding context ticker {context.ticker}",
                )
            context.ticker = found_ticker.upper()

        intent_scores = {}
        for intent, keywords in INTENT_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in query)
            if score > 0:
                intent_scores[intent] = score
        primary_intent = max(intent_scores, key=intent_scores.get) if intent_scores else "general"
        context.observations.update(
            {
                "intent": primary_intent,
                "intent_scores": intent_scores,
                "query": context.task,
                "ticker": context.ticker,
            }
        )
        self._add_thought(context, f"Query intent: {primary_intent}")
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        context.observations["needs"] = {
            "rag": True,
            "history": True,
            "knowledge_store": True,
        }
        self._add_thought(context, "Using one authoritative database-first Mythic pipeline")
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan = [
            "Gather RAG, OHLCV, news and durable insights in parallel",
            "Route every research mode through MythicOrchestrator",
            "Apply specialist fusion, critique and deterministic risk checks",
            "Return one calibrated result shape to every caller",
        ]
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        ticker = context.observations.get("ticker")
        query = context.observations["query"]
        research_mode = str(context.metadata.get("research_mode", "QUICK") or "QUICK").upper()
        if research_mode not in {"QUICK", "DEEP", "INSTITUTIONAL"}:
            research_mode = "QUICK"

        if ticker:
            try:
                from gateway.knowledge_store import knowledge_store

                news_count = len(knowledge_store.get_news_for_ticker(ticker, limit=1))
                if news_count == 0:
                    self._add_thought(context, f"{ticker} has no local news; triggering non-blocking sync")
                    asyncio.create_task(_collector_fetch_ticker(ticker))
            except Exception as exc:
                logger.debug("Lazy ticker sync check failed: %s", exc)

        gathered_context = await self._parallel_gather(query, ticker)

        try:
            from agents.orchestrator import mythic_orchestrator

            orchestrator_result = await mythic_orchestrator.orchestrate(
                query=query,
                ticker=ticker,
                gathered_data=gathered_context,
                session_id=context.session_id or "default",
                research_mode=research_mode,
                history=context.metadata.get("history", []),
            )
            context.result = {
                "response": orchestrator_result.get("response", ""),
                "ticker": ticker,
                "intent": context.observations["intent"],
                "research_mode": research_mode,
                "confidence": orchestrator_result.get("confidence", 0.5),
                "consensus": orchestrator_result.get("consensus", "NEUTRAL"),
                "specialist_outputs": orchestrator_result.get("specialist_outputs", {}),
                "specialist_details": orchestrator_result.get("specialist_details", {}),
                "critique": orchestrator_result.get("critique", {}),
                "sources_used": orchestrator_result.get("sources_used", []),
                "pipeline_ms": orchestrator_result.get("pipeline_ms", 0),
                "data_freshness": datetime.now().isoformat(),
                "authoritative_pipeline": "QueryRouter->MythicOrchestrator",
                "execution_authority": False,
            }
        except Exception as exc:
            logger.error("MythicOrchestrator failed: %s", exc)
            response = await self._fallback_llm_synthesize(query, ticker, gathered_context)
            context.result = {
                "response": response,
                "ticker": ticker,
                "intent": context.observations["intent"],
                "research_mode": research_mode,
                "confidence": 0.0,
                "consensus": "NEUTRAL",
                "sources_used": list(gathered_context.keys()),
                "data_freshness": datetime.now().isoformat(),
                "authoritative_pipeline": "fallback_direct_llm_after_mythic_failure",
                "execution_authority": False,
                "pipeline_error": type(exc).__name__,
            }
        context.actions_taken.append({"action": "query_route_complete", "pipeline": "mythic"})
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        if context.result and context.result.get("response"):
            confidence = float(context.result.get("confidence", 0.0) or 0.0)
            context.reflection = f"Query completed through authoritative Mythic pipeline. Confidence: {confidence:.0%}"
            context.confidence = confidence
        else:
            context.reflection = "Authoritative routing completed without a usable response"
            context.confidence = 0.0
        return context

    async def _parallel_gather(self, query: str, ticker: Optional[str]) -> dict:
        tasks = {
            "rag_results": self._rag_search(query, ticker),
            "knowledge_results": self._knowledge_search(query, ticker),
        }
        if ticker:
            tasks["intelligence_snapshot"] = self._get_intelligence_snapshot(ticker)
            tasks["history"] = self._get_history(ticker)
            tasks["news"] = self._get_news(ticker)
        keys = list(tasks)
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        gathered = {}
        for key, result in zip(keys, results):
            if isinstance(result, Exception):
                logger.warning("Data source %s failed: %s", key, result)
                gathered[key] = [] if key in ("rag_results", "history", "news") else {}
            else:
                gathered[key] = result

        snapshot = gathered.get("intelligence_snapshot")
        if isinstance(snapshot, dict) and snapshot:
            gathered["price_data"] = snapshot.get("price_data", {})
            gathered["analysis_context"] = snapshot.get("analysis", {})
            gathered["intelligence_profile"] = snapshot.get("intelligence_profile", {})
            if not gathered.get("news"):
                gathered["news"] = snapshot.get("top_headlines", [])
        return gathered

    async def _rag_search(self, query: str, ticker: Optional[str] = None) -> list:
        from agents.rag_agent import RagAgent

        rag = RagAgent()
        try:
            rag.load_index()
        except Exception:
            pass
        search_query = f"{ticker} {query}" if ticker else query
        result = await rag.run(AgentContext(task=search_query, metadata={"k": 5}))
        return result.result if isinstance(result.result, list) else []

    async def _knowledge_search(self, query: str, ticker: Optional[str] = None) -> dict:
        from gateway.knowledge_store import knowledge_store

        results = {}
        if ticker:
            results["news"] = knowledge_store.get_news_for_ticker(ticker, limit=10)
            results["insights"] = knowledge_store.get_insights(ticker, limit=5)
        results["search"] = knowledge_store.search_all(query, limit=10)
        return results

    async def _get_intelligence_snapshot(self, ticker: str) -> dict:
        from gateway.intelligence_service import intelligence_service

        return await intelligence_service.get_ticker_intelligence(ticker, max_age_minutes=120)

    async def _get_history(self, ticker: str) -> list:
        from gateway.knowledge_store import knowledge_store

        # Keep enough history for regime/signal work instead of truncating to 30
        # bars, while still bounding response size.
        history = knowledge_store.get_ohlcv_history(ticker, days=365)
        return history[:260]

    async def _get_news(self, ticker: str) -> list:
        try:
            from agents.mcp_news_agent import McpNewsAgent

            agent = McpNewsAgent()
            result = await agent.run(AgentContext(task=f"Fetch news for {ticker}", ticker=ticker))
            articles = result.result.get("articles", []) if isinstance(result.result, dict) else []
            if articles:
                return [
                    {
                        "headline": item.get("title", ""),
                        "summary": item.get("title", ""),
                        "source": item.get("source", "MCP News"),
                        "sentiment_score": item.get("sentiment", 0.5),
                        "published_at": item.get("published_at", item.get("publishedAt", "")),
                        "url": item.get("url", ""),
                    }
                    for item in articles
                ]
        except Exception as exc:
            logger.warning("MCP news fetch failed for %s: %s", ticker, exc)
        from gateway.knowledge_store import knowledge_store

        return knowledge_store.get_news_for_ticker(ticker, limit=10, days=14)

    async def _fallback_llm_synthesize(self, query: str, ticker: Optional[str], gathered_data: dict) -> str:
        """Research-only fallback; confidence is forced to zero by the caller."""
        from llm.client import get_shared_llm

        llm = get_shared_llm()
        prompt_parts = [f"USER QUESTION: {query}"]
        if ticker:
            prompt_parts.append(f"TICKER: {ticker}")
        if gathered_data.get("price_data"):
            prompt_parts.append(
                f"\nCURRENT PRICE DATA:\n{json.dumps(gathered_data['price_data'], indent=2, default=str)[:500]}"
            )
        if gathered_data.get("news"):
            news_text = "\nRECENT NEWS:\n"
            for index, item in enumerate(gathered_data["news"][:5], 1):
                news_text += f"{index}. [{item.get('source', 'Unknown')}] {item.get('headline', '')}\n"
                if item.get("url"):
                    news_text += f"   URL: {item['url']}\n"
            prompt_parts.append(news_text)
        if gathered_data.get("rag_results"):
            prompt_parts.append(
                "\nRAG KNOWLEDGE:\n"
                + "\n".join(
                    f"- {json.dumps(row, default=str)[:300]}"
                    for row in gathered_data["rag_results"][:3]
                )
            )
        system = f"""You are OMNI-DATA market intelligence.
{self._get_skills_context()}
Use only the supplied evidence. This fallback is research-only and cannot authorize trading.
Current: {datetime.now().isoformat()}"""
        try:
            return await llm.complete(
                prompt="\n".join(prompt_parts),
                system=system,
                temperature=0.2,
                max_tokens=1200,
            )
        except Exception as exc:
            logger.error("Fallback LLM also failed: %s", exc)
            return f"Analysis unavailable for now. Query: {query}"

    async def _extract_ticker_from_query(self, query: str) -> Optional[str]:
        from llm.client import get_shared_llm

        llm = get_shared_llm()
        prompt = f"""EXTRACT TICKER SYMBOL
Identify whether this query names a specific traded asset.
Query: "{query}"
Return ONLY the normalized symbol or NONE.
"""
        try:
            result = await llm.complete_small(prompt=prompt)
            symbol = str(result).strip().upper().replace('"', "").replace("'", "")
            if symbol in ("NONE", "NA", "") or len(symbol) > 12:
                return None
            return symbol
        except Exception:
            return None


query_router = QueryRouter()
