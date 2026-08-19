"""
AXIOM Data Engine — Real Market Data from customer APIs + open/public sources.

Priority chain:
  1. In-memory cache — fastest recent result
  2. Customer-connected market/news APIs — optional and configurable from UI
  3. Knowledge Store (SQLite) — local historical cache
  4. Collector Agent (yfinance/Stooq/Alpha Vantage/web fallback) — live public data
  5. RSS/Web/social collectors — news and sentiment

NEVER fabricates a live price. When no source is available it returns a clear
syncing payload so customer screens can explain that data is unavailable.
"""

import asyncio
from datetime import datetime
from core.config import settings
from core.logger import get_logger
from gateway.cache import cache
from gateway.scrapers.rss_scraper import rss_scraper
from gateway.scrapers.web_scraper import web_scraper
from gateway.scrapers.social_scraper import social_scraper

logger = get_logger(__name__)


class DataEngine:
    """Real data engine with connected-provider and knowledge-store integration."""

    def _df_to_ohlcv(self, df, tail: int = 120) -> list[dict]:
        rows = []
        if df is None or df.empty:
            return rows
        for idx, row in df.tail(tail).iterrows():
            rows.append({
                "t": str(idx.isoformat()) if hasattr(idx, "isoformat") else str(idx),
                "o": float(row.get("Open", 0) or 0),
                "h": float(row.get("High", 0) or 0),
                "l": float(row.get("Low", 0) or 0),
                "c": float(row.get("Close", 0) or 0),
                "v": int(row.get("Volume", 0) or 0),
            })
        return rows

    async def get_price_data(self, ticker: str, allow_scrape: bool = False) -> dict:
        """Return the best current price payload without inventing values."""
        ticker = ticker.upper()
        data, is_fresh = cache.get(ticker, "price")
        if data and (is_fresh or not allow_scrape):
            return {
                **data,
                "source_used": data.get("source_used", "cache"),
                "freshness_minutes": 0,
                "is_estimated": False,
            }

        if allow_scrape or ticker in settings.DEFAULT_WATCHLIST:
            try:
                from gateway.connected_source_adapter import connected_sources

                connected = await connected_sources.get_price(ticker)
                if connected and float(connected.get("px", 0) or 0) > 0:
                    px = float(connected.get("px", 0))
                    res = {
                        "px": round(px, 4),
                        "chg": float(connected.get("chg", connected.get("pct_chg", 0)) or 0),
                        "pct_chg": float(connected.get("pct_chg", connected.get("chg", 0)) or 0),
                        "open": float(connected.get("open", 0) or 0),
                        "high": float(connected.get("high", 0) or 0),
                        "low": float(connected.get("low", 0) or 0),
                        "close": float(connected.get("close", px) or px),
                        "volume": int(float(connected.get("volume", 0) or 0)),
                        "avg_volume": int(float(connected.get("avg_volume", 0) or 0)),
                        "mktcap": float(connected.get("mktcap", 0) or 0),
                        "pe": float(connected.get("pe", 0) or 0),
                        "week52_high": float(connected.get("week52_high", 0) or 0),
                        "week52_low": float(connected.get("week52_low", 0) or 0),
                        "ts": datetime.now().isoformat(),
                        "ohlcv": connected.get("ohlcv", []),
                        "source_used": connected.get("source_used", "connected_api"),
                        "connection_id": connected.get("connection_id"),
                        "freshness_minutes": 0,
                        "is_estimated": False,
                    }
                    cache.set(ticker, "price", res, res["source_used"])
                    return res
            except Exception as exc:
                logger.warning(f"Connected market data lookup failed for {ticker}: {type(exc).__name__}")

        if allow_scrape or ticker in settings.DEFAULT_WATCHLIST:
            try:
                from agents.collector_agent import fetch_ticker

                df, source = await fetch_ticker(ticker, period="1mo", scrape_ok=True)
                if not df.empty:
                    latest_row = df.iloc[-1]
                    px = float(latest_row.get("Close", 0))
                    prev_row = df.iloc[-2] if len(df) > 1 else latest_row
                    prev_close = float(prev_row.get("Close", px))
                    chg = ((px - prev_close) / prev_close * 100) if prev_close else 0
                    try:
                        from gateway.knowledge_store import knowledge_store

                        records = [
                            {
                                "date": str(idx.date()) if hasattr(idx, "date") else str(idx),
                                "open": float(row.get("Open", 0)),
                                "high": float(row.get("High", 0)),
                                "low": float(row.get("Low", 0)),
                                "close": float(row.get("Close", 0)),
                                "volume": int(row.get("Volume", 0)),
                                "mktcap": df.attrs.get("mktcap", 0),
                                "pe": df.attrs.get("pe", 0),
                            }
                            for idx, row in df.iterrows()
                        ]
                        if records:
                            knowledge_store.store_daily_ohlcv(ticker, records)
                    except Exception as store_err:
                        logger.warning(f"Failed to store OHLCV for {ticker}: {store_err}")

                    ohlcv_list = self._df_to_ohlcv(df, tail=120)
                    res = {
                        "px": round(px, 2),
                        "chg": round(chg, 2),
                        "pct_chg": round(chg, 2),
                        "open": float(latest_row.get("Open", px)),
                        "high": float(latest_row.get("High", px)),
                        "low": float(latest_row.get("Low", px)),
                        "close": px,
                        "volume": int(latest_row.get("Volume", 0)),
                        "avg_volume": int(df["Volume"].mean()) if "Volume" in df.columns else 0,
                        "mktcap": df.attrs.get("mktcap", 0),
                        "pe": df.attrs.get("pe", 0),
                        "week52_high": float(df["Close"].max()) if "Close" in df.columns else px,
                        "week52_low": float(df["Close"].min()) if "Close" in df.columns else px,
                        "ts": datetime.now().isoformat(),
                        "ohlcv": ohlcv_list,
                    }
                    cache.set(ticker, "price", res, source)
                    return {
                        **res,
                        "source_used": source,
                        "freshness_minutes": 0,
                        "is_estimated": False,
                    }
            except Exception as e:
                logger.warning(f"Collector fetch failed for {ticker}: {e}")

        try:
            from gateway.knowledge_store import knowledge_store

            ohlcv = knowledge_store.get_ohlcv_history(ticker, days=100)
            if ohlcv:
                latest = ohlcv[0]
                px = float(latest.get("close", 0))
                if px > 0:
                    prev_close = float(ohlcv[1]["close"]) if len(ohlcv) > 1 else px
                    chg = ((px - prev_close) / prev_close * 100) if prev_close else 0
                    lows = [float(r.get("low", 0) or 0) for r in ohlcv[:252]]
                    lows = [value for value in lows if value > 0]
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
                        "mktcap": latest.get("market_cap", 0),
                        "pe": latest.get("pe_ratio", 0),
                        "week52_high": max(float(r.get("high", 0) or 0) for r in ohlcv[:252]),
                        "week52_low": min(lows) if lows else 0,
                        "ts": latest.get("date", datetime.now().isoformat()),
                        "ohlcv": [
                            {"t": r.get("date"), "o": r.get("open"), "h": r.get("high"),
                             "l": r.get("low"), "c": r.get("close"), "v": r.get("volume")}
                            for r in ohlcv[:30]
                        ],
                    }
                    cache.set(ticker, "price", res, "knowledge_store")
                    return {
                        **res,
                        "source_used": "knowledge_store",
                        "freshness_minutes": 0,
                        "is_estimated": False,
                    }
        except Exception as e:
            logger.warning(f"Knowledge store price lookup failed for {ticker}: {e}")

        if data:
            return {**data, "source_used": "cache_stale", "is_stale": True}

        return {
            "px": 0, "chg": 0, "pct_chg": 0, "open": 0, "high": 0, "low": 0,
            "close": 0, "volume": 0, "avg_volume": 0, "mktcap": 0, "pe": 0,
            "week52_high": 0, "week52_low": 0, "ts": datetime.now().isoformat(),
            "ohlcv": [], "source_used": "none", "is_estimated": True, "syncing": True,
        }

    async def get_live_chart_data(self, ticker: str, period: str = "1d") -> dict:
        ticker = ticker.upper()
        period = period if period in {"1d", "5d", "1mo", "3mo", "6mo", "1y"} else "1d"
        cache_key = f"{ticker}:{period}"
        cached, is_fresh = cache.get(cache_key, "chart")
        if cached and is_fresh:
            return {**cached, "source_used": cached.get("source_used", "chart_cache")}
        try:
            from agents.collector_agent import fetch_ticker
            df, source = await fetch_ticker(ticker, period=period, use_cache=period != "1d", scrape_ok=True)
            bars = self._df_to_ohlcv(df, tail=160)
            if bars:
                payload = {
                    "ticker": ticker, "period": period, "ohlcv": bars,
                    "source_used": source, "updated_at": datetime.now().isoformat(),
                    "live": period == "1d" and source not in {"stale_cache", "none"},
                }
                cache.set(cache_key, "chart", payload, source)
                return payload
        except Exception as e:
            logger.warning(f"Live chart fetch failed for {ticker}: {e}")
        price = await self.get_price_data(ticker, allow_scrape=True)
        return {
            "ticker": ticker, "period": period, "ohlcv": price.get("ohlcv", []),
            "source_used": price.get("source_used", "fallback"),
            "updated_at": datetime.now().isoformat(), "live": False,
        }

    async def _trigger_background_fetch(self, ticker: str):
        try:
            from agents.collector_agent import fetch_ticker
            await fetch_ticker(ticker, period="1d", scrape_ok=True)
            logger.info(f"Background warming complete for {ticker}")
        except Exception:
            pass

    async def get_news(self, ticker: str, max_items: int = 10, allow_scrape: bool = False) -> list[dict]:
        """Combine customer APIs, stored history, RSS and web news."""
        ticker = ticker.upper()
        articles: list[dict] = []
        try:
            from gateway.connected_source_adapter import connected_sources
            articles.extend(await connected_sources.get_news(ticker, limit=max_items))
        except Exception as exc:
            logger.warning(f"Connected news lookup failed for {ticker}: {type(exc).__name__}")

        try:
            from gateway.knowledge_store import knowledge_store
            stored_news = knowledge_store.get_news_for_ticker(ticker, limit=max_items, days=14)
            for n in stored_news:
                articles.append({
                    "headline": n.get("headline", ""), "summary": n.get("summary", ""),
                    "url": n.get("url", ""), "source": n.get("source", "KnowledgeStore"),
                    "published_at": n.get("published_at", ""),
                    "sentiment_score": n.get("sentiment_score", 0),
                })
        except Exception as e:
            logger.warning(f"Knowledge store news lookup failed: {e}")

        if allow_scrape or not articles:
            try:
                articles.extend(rss_scraper.get_for_ticker(ticker))
                if allow_scrape:
                    web_news = web_scraper.scrape_ticker_news(ticker)
                    if asyncio.iscoroutine(web_news):
                        web_news = await web_news
                    articles.extend(web_news or [])
                if articles:
                    try:
                        from gateway.knowledge_store import knowledge_store
                        knowledge_store.store_news(articles)
                    except Exception as store_err:
                        logger.warning(f"Failed to persist news for {ticker}: {store_err}")
            except Exception as exc:
                logger.warning(f"Public news crawl failed for {ticker}: {type(exc).__name__}")

        seen = set()
        unique = []
        for n in articles:
            headline = str(n.get("headline", "")).strip()
            key = headline.lower()
            if headline and key not in seen:
                seen.add(key)
                unique.append(n)
        if not allow_scrape and len(unique) < 3:
            asyncio.create_task(self._trigger_news_warmup(ticker))
        return unique[:max_items]

    async def _trigger_news_warmup(self, ticker: str):
        try:
            result = web_scraper.scrape_ticker_news(ticker)
            if asyncio.iscoroutine(result):
                await result
        except Exception:
            pass

    async def get_social_sentiment(self, ticker: str, allow_scrape: bool = False) -> dict:
        try:
            return social_scraper.get_sentiment(ticker)
        except Exception:
            if allow_scrape:
                try:
                    return await asyncio.to_thread(social_scraper.get_sentiment, ticker)
                except Exception:
                    pass
            return {"score": 0, "mentions": 0, "source": "none"}

    async def get_full_context(self, ticker: str, allow_scrape: bool = False) -> dict:
        price = await self.get_price_data(ticker, allow_scrape=allow_scrape)
        news = await self.get_news(ticker, allow_scrape=allow_scrape)
        sentiment = await self.get_social_sentiment(ticker, allow_scrape=allow_scrape)
        return {**price, "news": news, **sentiment, "news_freshness": datetime.now().isoformat()}

    async def get_price_move_reason(self, ticker: str) -> dict:
        context = await self.get_full_context(ticker, allow_scrape=False)
        change = float(context.get("pct_chg", context.get("chg", 0)) or 0)
        headlines = [n.get("headline") for n in context.get("news", [])[:3] if n.get("headline")]
        direction = "higher" if change > 0 else "lower" if change < 0 else "sideways"
        reason = f"{ticker.upper()} is trading {direction} by {abs(change):.2f}% in the latest session."
        if headlines:
            reason += f" The newest related headline is: {headlines[0]}"
        return {"reason_text": reason, "confidence": 55 if headlines else 35, "headlines": headlines}


data_engine = DataEngine()
