"""MythicOrchestrator — ReAct loop orchestrator for multi-agent reasoning.

Adapted from the Claude Agent System architecture pattern:
User → Orchestrator → (Memory + Specialist Agents + Reflection) → Tools → Result Synthesis → Final Response

Uses open-source local LLM (NVIDIA Nemotron GGUF / Ollama) instead of cloud APIs.
"""

import json
import asyncio
from datetime import datetime
from typing import Optional
from core.logger import get_logger
from agents.base_agent import AgentContext

logger = get_logger(__name__)


class MythicOrchestrator:
    """
    The top-level orchestrator that:
    1. Collects context from all 4 knowledge sources in parallel
    2. Dispatches to specialist agents (Technical, Risk, Macro)
    3. Runs critique/reflection layer
    4. Synthesizes final response via LLM with calibrated confidence
    
    Implements a ReAct (Reason-Act) loop with max_steps safety.
    """

    def __init__(self):
        from agents.specialist_agents import TechnicalSpecialist, RiskSpecialist, MacroSpecialist
        from agents.critique_layer import CritiqueAgent
        
        self.technical = TechnicalSpecialist()
        self.risk = RiskSpecialist()
        self.macro = MacroSpecialist()
        self.critique = CritiqueAgent()
        
        # Memory store for episodic recall
        self._episode_store = []

    async def orchestrate(self, query: str, ticker: Optional[str], gathered_data: dict) -> dict:
        """
        Main entry point — full orchestrated reasoning pipeline.
        
        Args:
            query: User question
            ticker: Stock ticker (optional)
            gathered_data: Pre-fetched data from QueryRouter parallel fan-out:
                - rag_results: list
                - knowledge_results: dict
                - price_data: dict
                - news: list
                - history: list (OHLCV)
        
        Returns:
            {response, confidence, consensus, specialist_outputs, critique, sources_used}
        """
        logger.info(f"[Orchestrator] Starting mythic-tier pipeline for '{query[:80]}' ticker={ticker}")
        start = datetime.now()

        # ─── Step 1: Dispatch to all 3 specialists in parallel ──────────────
        specialist_outputs = await self._run_specialists(ticker, gathered_data)

        # ─── Step 2: Run critique/reflection layer ──────────────────────────
        critique_result = await self.critique.critique(specialist_outputs, query, ticker)

        # ─── Step 3: Calibrate confidence ───────────────────────────────────
        from agents.critique_layer import calibrate_confidence
        
        rag_count = len(gathered_data.get("rag_results", []))
        news = gathered_data.get("news", [])
        news_recency = self._compute_news_recency_hours(news)
        
        final_confidence = calibrate_confidence(
            specialist_agreement=critique_result["agreement_score"],
            rag_source_count=rag_count,
            news_recency_hours=news_recency,
            specialist_avg_confidence=sum(critique_result["specialist_confidences"].values()) / 3
        )

        # ─── Step 4: Final LLM synthesis with all context ───────────────────
        response = await self._synthesize_final(
            query, ticker, gathered_data, specialist_outputs, critique_result, final_confidence
        )

        # ─── Step 5: Store episode in memory ────────────────────────────────
        episode = {
            "query": query,
            "ticker": ticker,
            "consensus": critique_result["revised_consensus"],
            "confidence": final_confidence,
            "timestamp": datetime.now().isoformat(),
        }
        self._episode_store.append(episode)
        if len(self._episode_store) > 500:
            self._episode_store = self._episode_store[-250:]

        elapsed = (datetime.now() - start).total_seconds()
        logger.info(f"[Orchestrator] Pipeline complete in {elapsed:.1f}s. Consensus: {critique_result['revised_consensus']}, Confidence: {final_confidence}")

        return {
            "response": response,
            "confidence": final_confidence,
            "consensus": critique_result["revised_consensus"],
            "specialist_outputs": {
                "technical_summary": specialist_outputs.get("technical", {}).get("summary", ""),
                "risk_summary": specialist_outputs.get("risk", {}).get("summary", ""),
                "macro_summary": specialist_outputs.get("macro", {}).get("summary", ""),
            },
            "critique": {
                "flags": critique_result.get("flags", []),
                "contradictions": critique_result.get("contradiction_notes", []),
                "audit": critique_result.get("audit_summary", ""),
            },
            "sources_used": list(gathered_data.keys()),
            "pipeline_ms": round(elapsed * 1000),
        }

    async def _run_specialists(self, ticker: Optional[str], gathered_data: dict) -> dict:
        """Run all 3 specialist agents in parallel."""
        ohlcv_data = gathered_data.get("history", [])
        price_data = gathered_data.get("price_data", {})
        news_data = gathered_data.get("news", [])
        insights = gathered_data.get("knowledge_results", {}).get("insights", [])

        # Build per-specialist contexts
        tech_ctx = AgentContext(
            task=f"Technical analysis for {ticker}",
            ticker=ticker,
            metadata={"ohlcv_data": ohlcv_data, "price_data": price_data}
        )
        risk_ctx = AgentContext(
            task=f"Risk analysis for {ticker}",
            ticker=ticker,
            metadata={"ohlcv_data": ohlcv_data, "price_data": price_data}
        )
        macro_ctx = AgentContext(
            task=f"Macro analysis for {ticker}",
            ticker=ticker,
            metadata={"news_data": news_data, "insights_data": insights, "price_data": price_data}
        )

        # Run all 3 in parallel
        results = await asyncio.gather(
            self.technical.run(tech_ctx),
            self.risk.run(risk_ctx),
            self.macro.run(macro_ctx),
            return_exceptions=True
        )

        outputs = {}
        for i, (name, ctx_result) in enumerate(zip(
            ["technical", "risk", "macro"], results
        )):
            if isinstance(ctx_result, Exception):
                logger.warning(f"Specialist {name} failed: {ctx_result}")
                outputs[name] = {"signal": "NEUTRAL", "confidence": 0.3, "summary": f"{name} analysis unavailable"}
            else:
                outputs[name] = ctx_result.result if ctx_result.result else {}

        return outputs

    async def _synthesize_final(
        self, query: str, ticker: Optional[str],
        gathered_data: dict, specialist_outputs: dict,
        critique: dict, confidence: float
    ) -> str:
        """Synthesize all context into a final response via LLM."""
        from llm.client import LLMClient
        llm = LLMClient()

        # Build a rich prompt with all context
        sections = [f"USER QUESTION: {query}"]
        if ticker:
            sections.append(f"TICKER: {ticker}")

        # Price data
        if "price_data" in gathered_data and gathered_data["price_data"]:
            pd = gathered_data["price_data"]
            sections.append(f"\n📊 CURRENT PRICE DATA:\n{json.dumps(pd, indent=2, default=str)[:500]}")

        # Specialist outputs (structured summaries)
        tech = specialist_outputs.get("technical", {})
        risk = specialist_outputs.get("risk", {})
        macro = specialist_outputs.get("macro", {})

        sections.append(f"""
📈 SPECIALIST ANALYSIS:
───────────────────────────
TECHNICAL: Signal={tech.get('signal', 'N/A')} | {tech.get('summary', 'No analysis')}
RISK: Level={risk.get('risk_level', 'N/A')} | VaR={risk.get('var_pct', 'N/A')}% | {risk.get('summary', 'No analysis')}
MACRO: Outlook={macro.get('macro_outlook', 'N/A')} | Sentiment={macro.get('sentiment_score', 'N/A')} | {macro.get('summary', 'No analysis')}""")

        # Critique / consensus
        sections.append(f"""
🔍 CONSENSUS: {critique.get('revised_consensus', 'N/A')}
Agreement: {critique.get('agreement_score', 0):.0%}
Contradictions: {', '.join(critique.get('contradiction_notes', [])) or 'None'}
Flags: {', '.join(critique.get('flags', [])) or 'None'}""")

        # News
        news = gathered_data.get("news", [])
        if news:
            news_block = "\n📰 RECENT NEWS:\n"
            for n in news[:5]:
                if isinstance(n, dict):
                    headline = n.get("headline", n.get("title", n.get("txt", "")))
                    url = n.get("url", "")
                    news_block += f"- {headline}"
                    if url:
                        news_block += f" ({url})"
                    news_block += "\n"
            sections.append(news_block)

        # RAG results
        rag = gathered_data.get("rag_results", [])
        if rag:
            rag_block = "\n📚 RAG KNOWLEDGE:\n"
            for r in rag[:3]:
                rag_block += f"- {json.dumps(r, default=str)[:200]}\n"
            sections.append(rag_block)

        # Knowledge insights
        kr = gathered_data.get("knowledge_results", {})
        if kr.get("insights"):
            insights_block = "\n🧠 PRIOR INSIGHTS:\n"
            for ins in kr["insights"][:3]:
                if isinstance(ins, dict):
                    insights_block += f"- [{ins.get('agent_name', '')}] {ins.get('content', '')[:150]}\n"
            sections.append(insights_block)

        full_prompt = "\n".join(sections)

        system_prompt = f"""You are AXIOM MYTHIC — an autonomous trading intelligence system.
You have access to multi-agent specialist analysis, a critique layer, and calibrated confidence scoring.

RULES:
- Answer using ONLY the provided multi-specialist data context.
- Always cite news URLs when referencing news stories.
- Be specific with numbers, percentages, and price levels.
- Start with an overall consensus signal and confidence score.
- Format response with clear sections using emoji headers.
- Include the specialist agreement and any contradiction flags.
- If specialists disagree, explain the disagreement and your reasoning.
- End with calibrated confidence: {confidence:.0%}

Current timestamp: {datetime.now().isoformat()}"""

        try:
            response = await llm.complete(
                prompt=full_prompt,
                system=system_prompt,
                temperature=0.3,
                max_tokens=1500
            )
            return response
        except Exception as e:
            logger.error(f"[Orchestrator] Final synthesis failed: {e}")
            # Fallback to structured response without LLM
            return self._build_fallback_response(
                query, ticker, specialist_outputs, critique, confidence
            )

    def _build_fallback_response(self, query, ticker, specialists, critique, confidence):
        """Build a structured response when LLM is unavailable."""
        tech = specialists.get("technical", {})
        risk = specialists.get("risk", {})
        macro = specialists.get("macro", {})
        consensus = critique.get("revised_consensus", "NEUTRAL")

        return f"""🧠 AXIOM MYTHIC — MULTI-AGENT INTELLIGENCE

📊 Consensus: {consensus} (Confidence: {confidence:.0%})

📈 Technical Analysis
{tech.get('summary', 'No technical data available.')}
Signal: {tech.get('signal', 'N/A')} | Trend: {tech.get('indicators', {}).get('trend', 'N/A')}

⚠️ Risk Assessment
{risk.get('summary', 'No risk data available.')}
Level: {risk.get('risk_level', 'N/A')} | VaR(95%): {risk.get('var_pct', 'N/A')}%

🌍 Macro Environment
{macro.get('summary', 'No macro data available.')}
Outlook: {macro.get('macro_outlook', 'N/A')} | Sentiment: {macro.get('sentiment_score', 'N/A')}

🔍 Critique
{critique.get('audit_summary', 'No audit available.')}
Flags: {', '.join(critique.get('flags', [])) or 'None'}

👉 Confidence: {confidence:.0%} (Multi-agent consensus with calibration)"""

    def _compute_news_recency_hours(self, news: list) -> float:
        """Compute the average recency of news articles in hours."""
        if not news:
            return 168  # Default to 7 days if no news

        now = datetime.now()
        recencies = []
        for article in news[:10]:
            if not isinstance(article, dict):
                continue
            pub = article.get("published_at") or article.get("pubDate")
            if pub:
                try:
                    pub_dt = datetime.fromisoformat(str(pub).replace("Z", "+00:00"))
                    diff_hours = (now - pub_dt.replace(tzinfo=None)).total_seconds() / 3600
                    recencies.append(max(diff_hours, 0))
                except Exception:
                    pass

        return min(recencies) if recencies else 48  # Return best (most recent) if available

    def get_recent_episodes(self, ticker: str = None, limit: int = 5) -> list:
        """Recall recent orchestrator episodes for memory augmentation."""
        episodes = self._episode_store
        if ticker:
            episodes = [e for e in episodes if e.get("ticker") == ticker]
        return episodes[-limit:]


# Global singleton
mythic_orchestrator = MythicOrchestrator()
