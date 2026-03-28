"""CollectorAgent — Background data collection agent using Claude Flow.

Continuously collects market data (OHLCV, news, snapshots) and indexes it 
into the Knowledge Store + FAISS for RAG retrieval.
"""

import asyncio
import json
from datetime import datetime, timezone
from agents.base_agent import BaseAgent, AgentContext
from core.logger import get_logger

logger = get_logger(__name__)


class CollectorAgent(BaseAgent):
    """
    Agent: Data Collector — runs on scheduler to populate the Knowledge Store.
    
    Tasks:
    - collect_historical: Fetch 5-year OHLCV for all tickers (first-run)
    - collect_daily: Fetch today's OHLCV for all tickers
    - collect_news: Scrape RSS/web news and store
    - index_to_rag: Push unindexed knowledge store data into FAISS
    """

    def __init__(self, memory=None, improvement_engine=None):
        super().__init__(name="CollectorAgent", memory=memory, improvement_engine=improvement_engine,
                         timeout_seconds=300)  # 5 min timeout for large collections

    async def observe(self, context: AgentContext) -> AgentContext:
        task = context.task.lower()
        if "historical" in task:
            context.observations["mode"] = "historical"
        elif "daily" in task:
            context.observations["mode"] = "daily"
        elif "news" in task:
            context.observations["mode"] = "news"
        elif "index" in task or "rag" in task:
            context.observations["mode"] = "index_rag"
        elif "snapshot" in task:
            context.observations["mode"] = "snapshot"
        else:
            context.observations["mode"] = "daily"
        self._add_thought(context, f"Collection mode: {context.observations['mode']}")
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        mode = context.observations["mode"]
        self._add_thought(context, f"Preparing {mode} data collection pipeline")
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        mode = context.observations["mode"]
        if mode == "historical":
            context.plan = ["Fetch 5-year OHLCV for each ticker", "Store in knowledge_store", "Update collection status"]
        elif mode == "daily":
            context.plan = ["Fetch today's data for each ticker", "Store new OHLCV records", "Take market snapshot"]
        elif mode == "news":
            context.plan = ["Fetch RSS feeds", "Scrape web articles", "Store in knowledge_store"]
        elif mode == "index_rag":
            context.plan = ["Fetch unindexed news/insights", "Generate embeddings", "Add to FAISS index"]
        elif mode == "snapshot":
            context.plan = ["Capture price/volume/sentiment for each ticker", "Store snapshots"]
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        mode = context.observations["mode"]
        try:
            if mode == "historical":
                context.result = await self._collect_historical(context)
            elif mode == "daily":
                context.result = await self._collect_daily(context)
            elif mode == "news":
                context.result = await self._collect_news(context)
            elif mode == "index_rag":
                context.result = await self._index_to_rag(context)
            elif mode == "snapshot":
                context.result = await self._collect_snapshots(context)
        except Exception as e:
            context.errors.append(f"Collection failed: {str(e)}")
            logger.error(f"CollectorAgent act failed: {e}")
            context.result = {"status": "partial", "error": str(e)}

        context.actions_taken.append({"action": f"collect_{mode}"})
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        if not context.errors:
            context.reflection = f"Collection ({context.observations['mode']}) completed successfully."
            context.confidence = 0.95
        else:
            context.reflection = f"Collection had errors: {context.errors}"
            context.confidence = 0.4
        return context

    # ─── Collection Methods ───────────────────────────────────────────────────

    async def _collect_historical(self, context: AgentContext) -> dict:
        """Fetch 5-year OHLCV history for all watchlist tickers."""
        from gateway.knowledge_store import knowledge_store
        from core.config import settings
        import yfinance as yf

        tickers = context.metadata.get("tickers", settings.DEFAULT_WATCHLIST)
        total_inserted = 0
        success = 0
        failed = []

        for ticker in tickers:
            try:
                self._add_thought(context, f"Fetching 5y history for {ticker}")
                data = await asyncio.to_thread(self._yf_fetch_history, ticker, "5y")
                if data:
                    count = knowledge_store.store_daily_ohlcv(ticker, data)
                    total_inserted += count
                    success += 1
                    logger.info(f"[Collector] {ticker}: {count} OHLCV records stored")
                # Small delay to avoid rate limits
                await asyncio.sleep(0.5)
            except Exception as e:
                failed.append(ticker)
                logger.warning(f"[Collector] Historical fetch failed for {ticker}: {e}")

        return {"status": "complete", "success": success, "failed": len(failed),
                "total_records": total_inserted, "failed_tickers": failed}

    async def _collect_daily(self, context: AgentContext) -> dict:
        """Fetch today's OHLCV for all watchlist tickers."""
        from gateway.knowledge_store import knowledge_store
        from core.config import settings
        import yfinance as yf

        tickers = context.metadata.get("tickers", settings.DEFAULT_WATCHLIST)
        total_inserted = 0

        for ticker in tickers:
            try:
                data = await asyncio.to_thread(self._yf_fetch_history, ticker, "5d")
                if data:
                    count = knowledge_store.store_daily_ohlcv(ticker, data)
                    total_inserted += count
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.warning(f"[Collector] Daily fetch failed for {ticker}: {e}")

        return {"status": "complete", "records_added": total_inserted}

    async def _collect_news(self, context: AgentContext) -> dict:
        """Collect news from RSS scrapers and store in knowledge store."""
        from gateway.knowledge_store import knowledge_store
        from gateway.scrapers.rss_scraper import rss_scraper

        # Trigger RSS fetch
        await asyncio.to_thread(rss_scraper.fetch_all)

        # Store all cached articles into knowledge store
        articles = []
        for art in rss_scraper.cache.values():
            articles.append({
                "ticker": None,  # Will be matched by headline search
                "headline": art.get("headline", ""),
                "summary": art.get("summary", ""),
                "url": art.get("url", ""),
                "source": art.get("source", ""),
                "published_at": art.get("published_at", ""),
            })

        inserted = knowledge_store.store_news(articles)
        return {"status": "complete", "articles_stored": inserted, "total_fetched": len(articles)}

    async def _collect_snapshots(self, context: AgentContext) -> dict:
        """Take a market snapshot for all tickers."""
        from gateway.knowledge_store import knowledge_store
        from gateway.data_engine import data_engine

        tickers = context.metadata.get("tickers", [])
        stored = 0
        for ticker in tickers:
            try:
                data = await data_engine.get_price_data(ticker)
                if data and data.get("px", 0) > 0:
                    knowledge_store.store_snapshot(ticker, data)
                    stored += 1
            except Exception as e:
                logger.warning(f"[Collector] Snapshot failed for {ticker}: {e}")

        return {"status": "complete", "snapshots_stored": stored}

    async def _index_to_rag(self, context: AgentContext) -> dict:
        """Index unindexed news and insights into FAISS for RAG queries."""
        from gateway.knowledge_store import knowledge_store

        # Get the RAG agent from context or create one
        rag_agent = context.metadata.get("rag_agent")
        if not rag_agent:
            from agents.rag_agent import RagAgent
            rag_agent = RagAgent()

        # Index unindexed news
        unindexed_news = knowledge_store.get_unindexed_news(limit=50)
        news_indexed = 0
        indexed_ids = []
        for article in unindexed_news:
            try:
                text = f"{article['headline']}. {article.get('summary', '')}"
                blob_data = {
                    "symbol": article.get("ticker", "GENERAL"),
                    "name": article["headline"],
                    "type": "news",
                    "source": article.get("source", ""),
                    "url": article.get("url", ""),
                    "published_at": article.get("published_at", ""),
                    "text": text
                }
                ctx = AgentContext(task="Index blob", metadata={"blob_data": blob_data})
                await rag_agent.run(ctx)
                indexed_ids.append(article["id"])
                news_indexed += 1
            except Exception as e:
                logger.warning(f"RAG indexing failed for article {article.get('id')}: {e}")

        if indexed_ids:
            knowledge_store.mark_news_indexed(indexed_ids)

        # Index unindexed insights
        unindexed_insights = knowledge_store.get_unindexed_insights(limit=50)
        insights_indexed = 0
        insight_ids = []
        for insight in unindexed_insights:
            try:
                blob_data = {
                    "symbol": insight.get("ticker", "GENERAL"),
                    "name": f"{insight['agent_name']} insight",
                    "type": "insight",
                    "text": insight["content"]
                }
                ctx = AgentContext(task="Index blob", metadata={"blob_data": blob_data})
                await rag_agent.run(ctx)
                insight_ids.append(insight["id"])
                insights_indexed += 1
            except Exception as e:
                logger.warning(f"RAG indexing failed for insight {insight.get('id')}: {e}")

        if insight_ids:
            knowledge_store.mark_insights_indexed(insight_ids)

        # Persist FAISS index
        try:
            rag_agent.save_index()
        except Exception:
            pass

        return {"status": "complete", "news_indexed": news_indexed, "insights_indexed": insights_indexed}

    # ─── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _yf_fetch_history(ticker: str, period: str = "5y") -> list[dict]:
        """Synchronous yfinance history fetch."""
        import yfinance as yf
        import math

        t = yf.Ticker(ticker)
        hist = t.history(period=period)
        if hist.empty:
            return []

        records = []
        for idx, row in hist.iterrows():
            date_str = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)[:10]
            
            def safe(v, default=0.0):
                if v is None: return default
                try:
                    f = float(v)
                    return default if (math.isnan(f) or math.isinf(f)) else round(f, 4)
                except:
                    return default

            records.append({
                "date": date_str,
                "open": safe(row.get("Open")),
                "high": safe(row.get("High")),
                "low": safe(row.get("Low")),
                "close": safe(row.get("Close")),
                "volume": int(safe(row.get("Volume"), 0)),
                "adj_close": safe(row.get("Close")),
            })
        return records


# ─── Standalone Collection Functions (for scheduler) ──────────────────────────

async def collect_historical_data():
    """One-time historical data collection (5 years)."""
    agent = CollectorAgent()
    ctx = AgentContext(task="Collect historical OHLCV data")
    result = await agent.run(ctx)
    logger.info(f"[Scheduler] Historical collection result: {result.result}")
    return result.result


async def collect_daily_data():
    """Daily data collection."""
    agent = CollectorAgent()
    ctx = AgentContext(task="Collect daily OHLCV data")
    result = await agent.run(ctx)
    logger.info(f"[Scheduler] Daily collection result: {result.result}")
    return result.result


async def collect_news_data():
    """Periodic news collection."""
    agent = CollectorAgent()
    ctx = AgentContext(task="Collect news articles")
    result = await agent.run(ctx)
    logger.info(f"[Scheduler] News collection result: {result.result}")
    return result.result


async def index_knowledge_to_rag():
    """Index unindexed knowledge store data into FAISS."""
    agent = CollectorAgent()
    ctx = AgentContext(task="Index to RAG")
    result = await agent.run(ctx)
    logger.info(f"[Scheduler] RAG indexing result: {result.result}")
    return result.result
