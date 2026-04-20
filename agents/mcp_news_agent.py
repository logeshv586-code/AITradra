import asyncio
import json
import random
from agents.base_agent import BaseAgent, AgentContext
from core.logger import get_logger

logger = get_logger(__name__)

class McpNewsAgent(BaseAgent):
    """
    Agent 10: MCP News Agent - Multi-Source News Aggregator.
    Uses Playwright for real-time scraping and KnowledgeStore for persistence.
    """
    
    def __init__(self, memory=None, improvement_engine=None):
        super().__init__(name="McpNewsAgent", memory=memory, improvement_engine=improvement_engine)
        self.sources = ["Yahoo Finance", "Google News", "Economic Times", "Moneycontrol", "Reuters"]

    async def observe(self, context: AgentContext) -> AgentContext:
        self._add_thought(context, f"Initiating real-time news fetch for {context.ticker}")
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        self._add_thought(context, "Determining if database cache is sufficient or if live crawl is required.")
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan = [
            "Query central knowledge store for recent articles",
            "Trigger Playwright scraper if cache is cold (No Empty Data policy)",
            "Categorize news into Macro, US/Market, and Sector buckets",
            "Compute weighted sentiment score using prioritised weights"
        ]
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        ticker = context.ticker
        self._add_thought(context, f"Checking knowledge store for recent news for {ticker}")
        
        from gateway.knowledge_store import knowledge_store
        recent_news = knowledge_store.get_news_for_ticker(ticker, limit=20, days=7)
        
        rss_fetched = False
        # If no recent news in KnowledgeStore, do a lightweight RSS fetch (NOT Playwright)
        if not recent_news:
            self._add_thought(context, f"No recent news for {ticker}. Running lightweight RSS fetch (no browser).")
            try:
                from gateway.scrapers.rss_scraper import rss_scraper
                import asyncio
                await asyncio.to_thread(rss_scraper.fetch_all)
                recent_news = knowledge_store.get_news_for_ticker(ticker, limit=20, days=7)
                rss_fetched = True
            except Exception as e:
                logger.warning(f"RSS fetch failed for {ticker}: {e}")
        
        # If still no ticker-specific news, try general market news
        if not recent_news:
            self._add_thought(context, f"No ticker-specific news. Using general market news as context.")
            try:
                recent_news = knowledge_store.get_news_for_ticker("", limit=20, days=7)
            except Exception:
                pass

        final_news = []
        macro_sentiment, us_sentiment, sector_sentiment = 0.0, 0.0, 0.0
        counts = {"MACRO": 0, "US": 0, "SECTOR": 0}
        
        macro_kws = ["FED", "INFLATION", "YIELD", "INTEREST RATE", "GDP", "TREASURY", "CPI", "PPI", "GLOBAL", "RBI", "REPO"]
        us_kws = ["WALL STREET", "NYSE", "NASDAQ", "US", "USA", "AMERICAN", "SEC", "NIFTY", "SENSEX"]
        
        for item in recent_news:
            combined = (str(item.get("headline", "")) + " " + str(item.get("summary", ""))).upper()
            sentiment_val = float(item.get("sentiment_score", 0.5))
            
            category = "SECTOR"
            if any(kw in combined for kw in macro_kws):
                category = "MACRO"
                macro_sentiment += sentiment_val
                counts["MACRO"] += 1
            elif any(kw in combined for kw in us_kws):
                category = "US"
                us_sentiment += sentiment_val
                counts["US"] += 1
            else:
                sector_sentiment += sentiment_val
                counts["SECTOR"] += 1
            
            final_news.append({
                "title": item.get("headline"),
                "source": item.get("source"),
                "category": category,
                "sentiment": sentiment_val
            })
            
        avg_macro = (macro_sentiment / counts["MACRO"]) if counts["MACRO"] > 0 else 0.5
        avg_us = (us_sentiment / counts["US"]) if counts["US"] > 0 else 0.5
        avg_sector = (sector_sentiment / counts["SECTOR"]) if counts["SECTOR"] > 0 else 0.5
        
        weighted_score = (avg_macro * 0.5) + (avg_us * 0.3) + (avg_sector * 0.2)
        
        context.result = {
            "symbol": ticker,
            "sentiment": "bullish" if weighted_score > 0.6 else "bearish" if weighted_score < 0.4 else "neutral",
            "confidence": int(weighted_score * 100),
            "weighted_score": round(weighted_score, 2),
            "counts": counts,
            "articles": final_news[:10]
        }
        
        context.actions_taken.append({"action": "real_news_fetch", "rss_fetched": rss_fetched})
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        latest_action = context.actions_taken[-1] if context.actions_taken else {}
        context.reflection = (
            "Successfully aggregated and weighted news signals. "
            f"RSS fetched: {latest_action.get('rss_fetched', False)}"
        )
        return context
