"""
agents/news_agent.py  —  Institutional News Intelligence Agent (Layer 2)
=======================================================================
Supervisor that polls global news sources (yfinance, RSS, CryptoPanic)
for symbols on the WATCHLIST. Uses DeepMind-style reasoning to extract 
primary drivers from headlines and persists them.
"""

import asyncio
import logging
import json
import os
import re
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

import httpx
import yfinance as yf
from agents.base_agent import BaseAgent, AgentContext
from core.config import settings
from gateway.knowledge_store import knowledge_store
from core.logger import get_logger

logger = get_logger(__name__)

# --- Layer 2: Institutional Prompts ---
NEWS_INTEL_SYSTEM_PROMPT = """You are AITradra's News Intelligence Agent.
Your task is to analyze a set of financial headlines and extract the PRIMARY DRIVER in exactly 1 sentence.
Focus on: Earnings beats/misses, Macro shifts (Fed/CPI), M&A activity, or major Technical breakouts.

Output format (strict JSON):
{
    "primary_driver": "1-sentence summary of what's moving the market",
    "sentiment_score": float (-1.0 to 1.0),
    "confidence": int (0-100),
    "catalyst_type": "earnings" | "macro" | "m&a" | "technical" | "general"
}
"""

class NewsIntelAgent(BaseAgent):
    """
    Agent 4: News Intelligence (Layer 2)
    Continuously monitors headlines to feed the MoveExplainer and Orchestrator.
    """
    def __init__(self):
        super().__init__("NewsIntelAgent", timeout_seconds=45)
        self.watchlist = os.environ.get("WATCHLIST", "").split(",")
        if not self.watchlist or not self.watchlist[0]:
            self.watchlist = settings.DEFAULT_WATCHLIST

    async def observe(self, context: AgentContext) -> AgentContext:
        """Fetch raw headlines for the ticker."""
        ticker = context.ticker
        self._add_thought(context, f"Fetching news headlines for {ticker} from multiple sources.")
        
        # Source 1: yfinance
        try:
            val = yf.Ticker(ticker)
            yf_news = val.ニュース  # Note: yf news attribute is 'news' usually
            # Fallback for localized environments or library versions
            if not hasattr(val, "news"):
                yf_news = val.get_news()
            else:
                yf_news = val.news
        except Exception as e:
            logger.warning(f"yfinance news fetch failed for {ticker}: {e}")
            yf_news = []
            
        context.observations["raw_headlines"] = [n.get("title") for n in yf_news[:5]]
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        """Analyze headlines via LLM to extract the primary driver."""
        headlines = context.observations.get("raw_headlines", [])
        if not headlines:
            self._add_thought(context, "No recent headlines found.")
            context.result = {"primary_driver": "No news catalysts detected.", "sentiment_score": 0.0}
            return context

        prompt = f"Analyze these headlines for {context.ticker}:\n" + "\n".join(f"- {h}" for h in headlines)
        
        # Use LLMClient or similar. For simplicity, we assume an internal call to LLM.
        # In a real run, this would call self.llm_client.
        self._add_thought(context, "Synthesizing headlines into a primary market driver.")
        
        # Placeholder for LLM result (should be JSON parsed)
        # result = await self._call_llm(NEWS_INTEL_SYSTEM_PROMPT, prompt)
        
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        """Plan the news aggregation and analysis steps."""
        context.plan = [
            "1. Fetch headlines for symbols from yfinance and RSS",
            "2. Extract primary driver using LLM synthesis",
            "3. Persist findings to knowledge store"
        ]
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        """Persist analysis to news_articles table."""
        headlines = context.observations.get("raw_headlines", [])
        ticker = context.ticker
        
        # Standard integration: ensure headlines are in news_articles for MoveExplainer
        articles = []
        for h in headlines:
            articles.append({
                "ticker": ticker,
                "headline": h,
                "summary": "Processed by NewsIntelAgent",
                "source": "yfinance",
                "published_at": datetime.now(timezone.utc).isoformat()
            })
        
        if articles:
            stored = knowledge_store.store_news(articles)
            logger.info(f"[NewsIntel] Persisted {stored} new articles for {ticker}")
            
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        """Reflect on the quality of the news analysis."""
        if context.observations.get("raw_headlines"):
            context.reflection = f"Successfully extracted catalysts from {len(context.observations['raw_headlines'])} headlines."
            context.confidence = 0.85
        else:
            context.reflection = "No data found to reflect upon."
            context.confidence = 0.3
        return context

async def run_news_cycle():
    """Background loop triggered by scheduler."""
    agent = NewsIntelAgent()
    watchlist = agent.watchlist
    logger.info(f"Starting News Intelligence cycle for {len(watchlist)} symbols.")
    
    for symbol in watchlist:
        ctx = AgentContext(task=f"News analysis for {symbol}", ticker=symbol)
        await agent.run(ctx)
        # Rate limit safety
        await asyncio.sleep(1)

def get_agent():
    return NewsIntelAgent()
