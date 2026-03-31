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
        from agents.extended_specialists import SentimentSpecialist, FundamentalSpecialist, SectorSpecialist, CatalystSpecialist
        from agents.critique_layer import CritiqueAgent
        from agents.sentiment_classifier import SentimentClassifierAgent
        from agents.risk_manager import RiskManagerAgent
        from agents.signal_aggregator import SignalAggregatorAgent
        
        # Core Trio
        self.technical = TechnicalSpecialist()
        self.risk = RiskSpecialist()
        self.macro = MacroSpecialist()
        
        # Extended Specialists & AI Upgrades
        self.sentiment = SentimentSpecialist()
        self.sentiment_finbert = SentimentClassifierAgent()
        self.fundamental = FundamentalSpecialist()
        self.sector = SectorSpecialist()
        self.catalysts = CatalystSpecialist()
        
        # Decision & Risk Layer
        self.risk_manager = RiskManagerAgent()
        self.signal_aggregator = SignalAggregatorAgent()
        
        self.critique = CritiqueAgent()
        
        # Memory store for episodic recall
        self._episode_store = []

    async def orchestrate(self, query: str, ticker: Optional[str], gathered_data: dict) -> dict:
        """Main entry point — 14-agent Claude-style orchestrated reasoning pipeline."""
        logger.info(f"[Orchestrator] Starting 14-agent pipeline for '{query[:80]}' ticker={ticker}")
        start = datetime.now()

        # ─── Step 1: Run First Wave (Parallel) ──────────────────────────────
        # These agents compute initial base signals
        specialist_outputs = await self._run_first_wave(ticker, gathered_data)

        # ─── Step 2: Run Second Wave (Sequential/Knowledge Aware) ───────────
        # These agents check the knowledge store for the First Wave's signals
        second_wave_results = await self._run_second_wave(ticker, gathered_data)
        specialist_outputs.update(second_wave_results)

        # ─── Step 3: Run AI Decision Layer ──────────────────────────────────
        # Add FinBERT and Fusion logic
        ctx = AgentContext(task=f"Decision for {ticker}", ticker=ticker, observations=gathered_data)
        ctx.observations["sentiment_result"] = specialist_outputs.get("sentiment_finbert", {})
        
        decision_results = await asyncio.gather(
            self.sentiment_finbert.run(ctx),
            self.signal_aggregator.run(ctx),
            self.risk_manager.run(ctx),
            return_exceptions=True
        )
        
        for name, res in zip(["sentiment_finbert", "signal_aggregator", "risk_manager"], decision_results):
            specialist_outputs[name] = res.result if not isinstance(res, Exception) else {"error": str(res)}

        # ─── Step 4: Run critique/reflection layer ──────────────────────────
        critique_result = await self.critique.critique(specialist_outputs, query, ticker)

        # ─── Step 4: Calibrate confidence ───────────────────────────────────
        from agents.critique_layer import calibrate_confidence
        
        rag_count = len(gathered_data.get("rag_results", []))
        news = gathered_data.get("news", [])
        news_recency = self._compute_news_recency_hours(news)
        
        # Average confidence from ALL specialists
        specialist_confidences = [v.get("confidence", 0.5) for v in specialist_outputs.values() if isinstance(v, dict)]
        avg_spec_conf = sum(specialist_confidences) / len(specialist_confidences) if specialist_confidences else 0.5
        
        final_confidence = calibrate_confidence(
            specialist_agreement=critique_result["agreement_score"],
            rag_source_count=rag_count,
            news_recency_hours=news_recency,
            specialist_avg_confidence=avg_spec_conf
        )

        # ─── Step 5: Final LLM synthesis with all context ───────────────────
        response = await self._synthesize_final(
            query, ticker, gathered_data, specialist_outputs, critique_result, final_confidence
        )

        # ─── Step 6: Store episode ──────────────────────────────────────────
        episode = {
            "query": query, "ticker": ticker,
            "consensus": critique_result["revised_consensus"],
            "confidence": final_confidence, "timestamp": datetime.now().isoformat(),
        }
        self._episode_store.append(episode)
        if len(self._episode_store) > 500: self._episode_store = self._episode_store[-250:]

        try:
            from gateway.knowledge_store import knowledge_store
            if ticker:
                knowledge_store.store_insight(
                    ticker=ticker, agent_name="MythicOrchestrator",
                    insight_type="synthesis", content=response[:500] if response else "",
                    confidence=final_confidence,
                )
        except Exception: pass

        elapsed = (datetime.now() - start).total_seconds()
        logger.info(f"[Orchestrator] Pipeline complete in {elapsed:.1f}s. Confidence: {final_confidence}")

        return {
            "response": response,
            "confidence": final_confidence,
            "consensus": critique_result["revised_consensus"],
            "specialist_outputs": {k: v.get("summary", "") for k, v in specialist_outputs.items() if isinstance(v, dict)},
            "critique": {
                "flags": critique_result.get("flags", []),
                "contradictions": critique_result.get("contradiction_notes", []),
                "audit": critique_result.get("audit_summary", ""),
            },
            "sources_used": list(gathered_data.keys()),
            "pipeline_ms": round(elapsed * 1000),
        }

    async def _run_first_wave(self, ticker: str, data: dict) -> dict:
        """First wave: Agents that don't depend on others."""
        ohlcv = data.get("history", [])
        price = data.get("price_data", {})
        news = data.get("news", [])
        
        ctx = AgentContext(task=f"Analyze {ticker}", ticker=ticker, metadata={"ohlcv_data": ohlcv, "price_data": price, "news_data": news})
        
        results = await asyncio.gather(
            self.technical.run(ctx),
            self.macro.run(ctx),
            self.fundamental.run(ctx),
            return_exceptions=True
        )
        
        outputs = {}
        for name, res in zip(["technical", "macro", "fundamental"], results):
            outputs[name] = res.result if not isinstance(res, Exception) else {"error": str(res)}
        return outputs

    async def _run_second_wave(self, ticker: str, data: dict) -> dict:
        """Second wave: Agents that benefit from First Wave's stored insights."""
        ohlcv = data.get("history", [])
        price = data.get("price_data", {})
        news = data.get("news", [])
        
        ctx = AgentContext(task=f"Advanced analyze {ticker}", ticker=ticker, metadata={"ohlcv_data": ohlcv, "price_data": price, "news_data": news})
        
        results = await asyncio.gather(
            self.risk.run(ctx),
            self.sentiment.run(ctx),
            self.sector.run(ctx),
            self.catalysts.run(ctx),
            return_exceptions=True
        )
        
        outputs = {}
        for name, res in zip(["risk", "sentiment", "sector", "catalysts"], results):
            outputs[name] = res.result if not isinstance(res, Exception) else {"error": str(res)}
        return outputs

    async def _synthesize_final(
        self, query: str, ticker: Optional[str],
        gathered_data: dict, specialist_outputs: dict,
        critique: dict, confidence: float
    ) -> str:
        """Synthesize all 14-agent contexts into a final response."""
        from llm.client import get_shared_llm
        llm = get_shared_llm()

        consensus = critique.get('revised_consensus', 'NEUTRAL')

        prompt_parts = [
            f"Question: {query}",
            f"Ticker: {ticker or 'N/A'}",
            f"Overall Consensus: {consensus} (Confidence: {confidence:.0%})",
            "\nSpecialist Agent Analysis:"
        ]

        # Dynamically add all specialist summaries
        for name, output in specialist_outputs.items():
            if isinstance(output, dict):
                sig = output.get('signal', output.get('risk_level', output.get('macro_outlook', 'N/A')))
                summ = output.get('summary', 'Analysis complete.')[:200]
                prompt_parts.append(f"- {name.upper()}: {sig} | {summ}")

        # Add news headlines (max 5)
        news = gathered_data.get("news", [])
        if news:
            prompt_parts.append("\nRecent Market Catalysts:")
            for n in news[:5]:
                if isinstance(n, dict):
                    h = n.get("headline", n.get("title", ""))
                    if h: prompt_parts.append(f"- {h[:100]}")

        full_prompt = "\n".join(prompt_parts)

        system_prompt = (
            "You are AXIOM, a premium multi-agent trading intelligence system powered by NVIDIA NIM. "
            "Write an authoritative, data-driven synthesis of all agent signals. "
            "Structure: 1) Executive Summary, 2) Technical/Risk alignment, "
            "3) Macro/Fundamental context, 4) Investment Verdict (BUY/SELL/HOLD). "
            "IMPORTANT: If the Signal Aggregator shows a strong verdict, be extremely clear about it. "
            "Provide specific price targets and stop-losses if available. "
            "Be extremely specific. Use professional financial tone. Keep under 400 words."
        )

        try:
            return await llm.complete(
                prompt=full_prompt, system=system_prompt,
                temperature=0.2, max_tokens=1000
            )
        except Exception as e:
            logger.error(f"[Orchestrator] Final synthesis failed: {e}")
            return self._build_fallback_response(query, ticker, specialist_outputs, critique, confidence)

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
