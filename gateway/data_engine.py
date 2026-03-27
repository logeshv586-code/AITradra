import asyncio
import yfinance as yf
from datetime import datetime, timedelta
from core.logger import get_logger
from gateway.cache import cache
from gateway.scrapers.rss_scraper import rss_scraper
from gateway.scrapers.web_scraper import web_scraper
from gateway.scrapers.social_scraper import social_scraper

logger = get_logger(__name__)

class DataEngine:
    """
    Tries sources in order. Never raises. Always returns something.
    Each method logs which source was actually used.
    """

    SOURCE_CHAIN = [
        "yfinance",
        "rss_scraper",
        "web_scraper",
        "social_scraper",
        "llm_estimate",
    ]

    async def get_price_data(self, ticker: str) -> dict:
        """
        Returns OHLCV + Freshness metadata.
        """
        # 1. Check cache
        data, is_fresh = cache.get(ticker, "price")
        if data and is_fresh:
            return {**data, "source_used": "cache", "freshness_minutes": 0, "is_estimated": False}

        # 2. Try yfinance
        try:
            t = yf.Ticker(ticker)
            info = t.info
            if info:
                res = {
                    "px": info.get("currentPrice") or info.get("regularMarketPrice"),
                    "chg": info.get("regularMarketChange"),
                    "pct_chg": info.get("regularMarketChangePercent"),
                    "open": info.get("open"),
                    "high": info.get("dayHigh"),
                    "low": info.get("dayLow"),
                    "close": info.get("previousClose"),
                    "volume": info.get("volume"),
                    "avg_volume": info.get("averageVolume"),
                    "mktcap": info.get("marketCap"),
                    "pe": info.get("trailingPE"),
                    "week52_high": info.get("fiftyTwoWeekHigh"),
                    "week52_low": info.get("fiftyTwoWeekLow"),
                    "ts": datetime.now().isoformat()
                }
                cache.set(ticker, "price", res, "yfinance")
                return {**res, "source_used": "yfinance", "freshness_minutes": 0, "is_estimated": False}
        except Exception as e:
            logger.warning(f"yfinance failed for {ticker}: {e}")

        # 3. Fallback to stale cache
        if data:
            return {**data, "source_used": "cache_stale", "is_stale": True}

        # 4. Final fallback: Empty/Dummy
        return {"px": 0, "source_used": "none", "is_estimated": True}

    async def get_news(self, ticker: str, max_items: int = 10) -> list[dict]:
        """
        Deduplicated news from RSS and Web.
        """
        rss_news = rss_scraper.get_for_ticker(ticker)
        web_news = web_scraper.scrape_ticker_news(ticker)
        
        combined = rss_news + web_news
        # Dedupe by headline
        seen = set()
        unique = []
        for n in combined:
            if n['headline'] not in seen:
                seen.add(n['headline'])
                unique.append(n)
        
        return unique[:max_items]

    async def get_social_sentiment(self, ticker: str) -> dict:
        return social_scraper.get_sentiment(ticker)

    async def get_full_context(self, ticker: str) -> dict:
        """Aggregates everything for LLM reasoning."""
        price = await self.get_price_data(ticker)
        news = await self.get_news(ticker)
        sentiment = await self.get_social_sentiment(ticker)
        
        return {
            **price,
            "news": news,
            **sentiment,
            "news_freshness": datetime.now().isoformat()
        }

    async def get_price_move_reason(self, ticker: str) -> dict:
        """
        Placeholder - actually implemented via LLM in server.py/endpoints.
        """
        return {"reason_text": "Analyzing...", "confidence": 0}

# Global instance
data_engine = DataEngine()
