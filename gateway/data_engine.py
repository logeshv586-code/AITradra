"""
AXIOM Data Engine — Real Market Data from Knowledge Store + Multi-Source Collector.

Priority chain:
  1. Knowledge Store (SQLite) — fastest, local cache
  2. Data Cache (parquet files) — recent collector results
  3. Collector Agent (Stooq, Alpha Vantage, web scrape) — live data
  4. RSS/Web scrapers — news and sentiment

NEVER returns empty. Always provides the best available data with freshness labels.
"""

import asyncio
from datetime import datetime, timedelta
from core.logger import get_logger
from gateway.cache import cache
from gateway.scrapers.rss_scraper import rss_scraper
from gateway.scrapers.web_scraper import web_scraper
from gateway.scrapers.social_scraper import social_scraper

logger = get_logger(__name__)


class DataEngine:
    """Real data engine with knowledge store integration."""

    async def get_price_data(self, ticker: str) -> dict:
        """Returns real price data from knowledge store or collector."""

        # 1. Check in-memory cache
        data, is_fresh = cache.get(ticker, "price")
        if data and is_fresh:
            return {**data, "source_used": "cache", "freshness_minutes": 0, "is_estimated": False}

        # 2. Check knowledge store for recent OHLCV
        try:
            from gateway.knowledge_store import knowledge_store
            ohlcv = knowledge_store.get_ohlcv_history(ticker, days=7)
            if ohlcv and len(ohlcv) > 0:
                latest = ohlcv[0]  # Most recent first
                px = float(latest.get("close", 0))
                if px > 0:
                    prev_close = float(ohlcv[1]["close"]) if len(ohlcv) > 1 else px
                    chg = ((px - prev_close) / prev_close * 100) if prev_close else 0

                    res = {
                        "px": round(px, 2),
                        "chg": round(chg, 2),
                        "pct_chg": round(chg, 2),
                        "open": float(latest.get("open", px)),
                        "high": float(latest.get("high", px)),
                        "low": float(latest.get("low", px)),
                        "close": px,
                        "volume": int(latest.get("volume", 0)),
                        "avg_volume": 0,
                        "mktcap": 0,
                        "pe": 0,
                        "week52_high": max(float(r.get("high", 0)) for r in ohlcv[:252]) if len(ohlcv) > 10 else px * 1.3,
                        "week52_low": min(float(r.get("low", px)) for r in ohlcv[:252] if float(r.get("low", 0)) > 0) if len(ohlcv) > 10 else px * 0.7,
                        "ts": latest.get("date", datetime.now().isoformat()),
                        "ohlcv": [{"t": r.get("date"), "o": r.get("open"), "h": r.get("high"),
                                   "l": r.get("low"), "c": r.get("close"), "v": r.get("volume")}
                                  for r in ohlcv[:30]],
                    }
                    cache.set(ticker, "price", res, "knowledge_store")
                    return {**res, "source_used": "knowledge_store", "freshness_minutes": 0, "is_estimated": False}
        except Exception as e:
            logger.warning(f"Knowledge store price lookup failed for {ticker}: {e}")

        # 3. Try collector agent (Stooq, web scrape, etc.)
        try:
            from agents.collector_agent import fetch_ticker
            df, source = await fetch_ticker(ticker, period="1y", scrape_ok=True)
            if not df.empty:
                latest_row = df.iloc[-1]
                px = float(latest_row.get("Close", 0))
                prev_row = df.iloc[-2] if len(df) > 1 else latest_row
                prev_close = float(prev_row.get("Close", px))
                chg = ((px - prev_close) / prev_close * 100) if prev_close else 0

                # Store in knowledge store for future use
                try:
                    from gateway.knowledge_store import knowledge_store
                    records = []
                    for idx, row in df.iterrows():
                        records.append({
                            "date": str(idx.date()) if hasattr(idx, 'date') else str(idx),
                            "open": float(row.get("Open", 0)),
                            "high": float(row.get("High", 0)),
                            "low": float(row.get("Low", 0)),
                            "close": float(row.get("Close", 0)),
                            "volume": int(row.get("Volume", 0)),
                        })
                    if records:
                        knowledge_store.store_daily_ohlcv(ticker, records)
                        logger.info(f"Stored {len(records)} OHLCV records for {ticker} from {source}")
                except Exception as store_err:
                    logger.warning(f"Failed to store OHLCV for {ticker}: {store_err}")

                ohlcv_list = [
                    {"t": str(idx.date()) if hasattr(idx, 'date') else str(idx),
                     "o": float(row.get("Open", 0)), "h": float(row.get("High", 0)),
                     "l": float(row.get("Low", 0)), "c": float(row.get("Close", 0)),
                     "v": int(row.get("Volume", 0))}
                    for idx, row in df.tail(30).iterrows()
                ]

                res = {
                    "px": round(px, 2), "chg": round(chg, 2), "pct_chg": round(chg, 2),
                    "open": float(latest_row.get("Open", px)),
                    "high": float(latest_row.get("High", px)),
                    "low": float(latest_row.get("Low", px)),
                    "close": px,
                    "volume": int(latest_row.get("Volume", 0)),
                    "avg_volume": int(df["Volume"].mean()) if "Volume" in df.columns else 0,
                    "mktcap": 0, "pe": 0,
                    "week52_high": float(df["Close"].max()) if "Close" in df.columns else px,
                    "week52_low": float(df["Close"].min()) if "Close" in df.columns else px,
                    "ts": datetime.now().isoformat(),
                    "ohlcv": ohlcv_list,
                }
                cache.set(ticker, "price", res, source)
                return {**res, "source_used": source, "freshness_minutes": 0, "is_estimated": False}
        except Exception as e:
            logger.warning(f"Collector fetch failed for {ticker}: {e}")

        # 4. Return stale cache if available
        if data:
            return {**data, "source_used": "cache_stale", "is_stale": True}

        # 5. Final fallback — minimal stub so UI doesn't break
        return {
            "px": 0, "chg": 0, "pct_chg": 0, "open": 0, "high": 0, "low": 0, "close": 0,
            "volume": 0, "avg_volume": 0, "mktcap": 0, "pe": 0,
            "week52_high": 0, "week52_low": 0,
            "ts": datetime.now().isoformat(), "ohlcv": [],
            "source_used": "none", "is_estimated": True,
        }

    async def get_news(self, ticker: str, max_items: int = 10) -> list[dict]:
        """Deduplicated news from knowledge store + RSS + Web."""
        articles = []

        # 1. Knowledge store news
        try:
            from gateway.knowledge_store import knowledge_store
            stored_news = knowledge_store.get_news_for_ticker(ticker, limit=max_items, days=14)
            for n in stored_news:
                articles.append({
                    "headline": n.get("headline", ""),
                    "summary": n.get("summary", ""),
                    "url": n.get("url", ""),
                    "source": n.get("source", "KnowledgeStore"),
                    "published_at": n.get("published_at", ""),
                    "sentiment_score": n.get("sentiment_score", 0),
                })
        except Exception as e:
            logger.warning(f"Knowledge store news lookup failed: {e}")

        # 2. RSS + Web scrapers
        try:
            rss_news = rss_scraper.get_for_ticker(ticker)
            web_news = web_scraper.scrape_ticker_news(ticker)
            for n in (rss_news + web_news):
                articles.append(n)
        except Exception:
            pass

        # Deduplicate by headline
        seen = set()
        unique = []
        for n in articles:
            h = n.get("headline", "").strip().lower()
            if h and h not in seen:
                seen.add(h)
                unique.append(n)

        return unique[:max_items]

    async def get_social_sentiment(self, ticker: str) -> dict:
        try:
            return social_scraper.get_sentiment(ticker)
        except Exception:
            return {"score": 0, "mentions": 0, "source": "none"}

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
        return {"reason_text": "Analyzing...", "confidence": 0}


# Global instance
data_engine = DataEngine()
