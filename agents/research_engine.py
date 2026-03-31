"""AXIOM Deep Research Engine — Specialist agents for deep stock analysis and autonomous suggestions."""

import os
import asyncio
from typing import List, Dict, Any
from datetime import datetime
from agents.base_agent import BaseAgent, AgentContext
from core.logger import get_logger
from gateway.knowledge_store import knowledge_store

logger = get_logger(__name__)

class DeepResearchAgent(BaseAgent):
    """Daily Deep Analysis agent that provides high-conviction research suggestions."""
    def __init__(self):
        super().__init__("DeepResearchAgent")

    async def observe(self, context: AgentContext) -> AgentContext:
        from core.config import settings
        watchlist = settings.DEFAULT_WATCHLIST
        context.observations["watchlist"] = watchlist
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        """Analyze the 14-agent consensus for each stock and build deep research cards."""
        suggestions = []
        for ticker in context.observations["watchlist"]:
            insights = knowledge_store.get_agent_insights(ticker)
            if not insights: continue
            
            # Weighted Consensus Calculation (85% Logic)
            # Specialists: Technical, Risk, Macro, Sentiment, Fundamental
            breakdown = {
                "technical": {"signal": "NEUTRAL", "confidence": 0.5, "reason": "No data"},
                "risk": {"signal": "LOW", "confidence": 0.5, "reason": "No data"},
                "macro": {"signal": "NEUTRAL", "confidence": 0.5, "reason": "No data"},
                "sentiment": {"signal": "NEUTRAL", "confidence": 0.5, "reason": "No data"},
                "fundamental": {"signal": "NEUTRAL", "confidence": 0.5, "reason": "No data"}
            }
            
            total_score = 0
            weights = {"TechnicalSpecialist": 0.2, "RiskSpecialist": 0.2, "MacroSpecialist": 0.2, "SentimentSpecialist": 0.2, "FundamentalSpecialist": 0.2}
            count = 0
            
            for i in insights:
                name = i["agent_name"]
                content = i["content"].upper()
                conf = i.get("confidence", 0.5)
                
                # Signal Mapping
                val = 0.5
                sig = "NEUTRAL"
                if any(w in content for w in ["BULLISH", "BUY", "UPGRADE"]): 
                    val = 1.0
                    sig = "BULLISH"
                elif any(w in content for w in ["BEARISH", "SELL", "DOWNGRADE"]): 
                    val = 0.0
                    sig = "BEARISH"
                
                if name in weights:
                    # Update breakdown
                    key = name.replace("Specialist", "").lower()
                    breakdown[key] = {"signal": sig, "confidence": conf, "reason": i["content"]}
                    total_score += val * weights[name]
                    count += 1
            
            # Historical 1-month context (Trivial)
            perf_1m = 0
            try:
                ohlcv = knowledge_store.get_historical_ohlcv(ticker, limit=20)
                if len(ohlcv) >= 20:
                    start_px = ohlcv[-1].get("close", ohlcv[-1].get("c", 0))
                    end_px = ohlcv[0].get("close", ohlcv[0].get("c", 1))
                    perf_1m = (end_px - start_px) / start_px * 100
            except Exception: pass

            # Deep Research Threshold: 80% (Making it slightly more reachable)
            if count >= 3 and total_score >= 0.80:
                suggestions.append({
                    "ticker": ticker,
                    "score": total_score,
                    "signal": "STRONG BUY" if total_score > 0.9 else "BUY",
                    "reasoning": "High-conviction alignment discovered across multi-agent specialist fleet.",
                    "breakdown": breakdown,
                    "performance_1m": round(perf_1m, 2),
                    "created_at": datetime.now().isoformat()
                })
        
        context.observations["suggestions"] = sorted(suggestions, key=lambda x: x["score"], reverse=True)[:5]
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan = ["Archive deep research suggestions to database"]
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        """Store the final research suggestions in KnowledgeStore."""
        suggestions = context.observations.get("suggestions", [])
        for s in suggestions:
            try:
                knowledge_store.store_research_suggestion(
                    ticker=s["ticker"],
                    score=s["score"],
                    signal=s["signal"],
                    reasoning=s["reasoning"],
                    breakdown=s["breakdown"],
                    perf_1m=s["performance_1m"]
                )
            except Exception as e:
                logger.error(f"Failed to store suggestion for {s['ticker']}: {e}")
        
        context.result = suggestions
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        context.reflection = f"Deep Research generated {len(context.result)} high-conviction suggestions."
        return context
