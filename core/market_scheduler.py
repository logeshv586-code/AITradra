"""
AXIOM Market-Aware Scheduler — continuous background market/news collection.

The scheduler uses configurable cadences rather than UI-driven refreshes:
  * prices refresh while any tracked market is open;
  * news refreshes continuously from lightweight public RSS feeds;
  * startup performs an immediate catch-up if the local knowledge store is empty;
  * heavier browser work remains outside the high-frequency scheduler path;
  * research sweeps use Research Council V2 for point-in-time/provenance checks.
"""

import asyncio
from datetime import datetime
from core.config import settings
from core.logger import get_logger
from core.market_manager import MarketManager
from core.graph_memory import graph_memory
from scrapers.world_collector import world_collector
from agents.simulation_engine import simulation_engine
from agents.report_agent import report_agent

logger = get_logger(__name__)


class MarketScheduler:
    """Intelligent scheduler that respects market hours and data freshness."""

    def __init__(self):
        self._last_news_scrape = None
        self._last_price_update = None
        self._last_commodity_scan = None
        self._last_research_sweep = None
        self._startup_scrape_done = False
        self._running = False

    def is_indian_market_open(self) -> bool:
        return MarketManager.get_market_status("INDIA") == "OPEN"

    def is_us_market_open(self) -> bool:
        return MarketManager.get_market_status("US") == "OPEN"

    def any_market_open(self) -> bool:
        for key in MarketManager.MARKETS:
            if MarketManager.get_market_status(key) == "OPEN":
                return True
        return False

    def should_scrape_prices(self) -> bool:
        if self.any_market_open():
            if self._last_price_update is None:
                return True
            interval = max(int(settings.PRICE_FETCH_INTERVAL_MIN), 1) * 60
            return (datetime.now() - self._last_price_update).total_seconds() > interval
        return False

    def should_scrape_news(self) -> bool:
        if self._last_news_scrape is None:
            return True
        elapsed = (datetime.now() - self._last_news_scrape).total_seconds()
        # RSS is lightweight. Use the configured cadence while markets are open,
        # and keep an hourly pulse outside market hours so overnight catalysts are
        # already present when customers open the app the next morning.
        interval_minutes = max(int(settings.NEWS_FETCH_INTERVAL_MIN), 5) if self.any_market_open() else max(int(settings.NEWS_FETCH_INTERVAL_MIN), 60)
        return elapsed > interval_minutes * 60

    async def startup_catchup(self):
        if self._startup_scrape_done:
            return
        logger.info("🔍 Market Scheduler: Checking data freshness on startup...")
        try:
            from gateway.knowledge_store import knowledge_store
            status = knowledge_store.get_collection_status()
            has_news = status.get("total_news_articles", 0) > 0
            if not has_news:
                logger.info("⚠️ No news data found. Running RSS catch-up...")
                await self._run_rss_catchup()
            else:
                logger.info(f"✅ KnowledgeStore has {status['total_news_articles']} articles.")
        except Exception as e:
            logger.warning(f"Startup catchup check failed: {e}. Running RSS fetch anyway.")
            await self._run_rss_catchup()
        self._startup_scrape_done = True

    async def _run_rss_catchup(self):
        try:
            from gateway.scrapers.rss_scraper import rss_scraper
            await asyncio.to_thread(rss_scraper.fetch_all)
            self._last_news_scrape = datetime.now()
            logger.info("✅ RSS catch-up complete.")
        except Exception as e:
            logger.error(f"RSS catch-up failed: {e}")

    async def run_scheduled_news_collection(self):
        if not self.should_scrape_news():
            return
        logger.info(f"📰 Scheduled news collection (market_open={self.any_market_open()})")
        try:
            from gateway.scrapers.rss_scraper import rss_scraper
            await asyncio.to_thread(rss_scraper.fetch_all)
            self._last_news_scrape = datetime.now()
        except Exception as e:
            logger.error(f"RSS news collection failed: {e}")

    async def run_scheduled_price_collection(self):
        if not self.should_scrape_prices():
            logger.info("⏸️ Price collection skipped because no tracked market requires a refresh")
            return
        logger.info("📈 Price collection triggered")
        try:
            from agents.collector_agent import collect_daily_data
            await collect_daily_data()
            self._last_price_update = datetime.now()
        except Exception as e:
            logger.error(f"Price collection failed: {e}")

    async def run_commodity_scan(self):
        if self._last_commodity_scan is not None:
            elapsed = (datetime.now() - self._last_commodity_scan).total_seconds()
            interval = 3600 if self.any_market_open() else 21600
            if elapsed < interval:
                return
        logger.info("🌾 Commodity causal-chain scan starting...")
        try:
            from agents.commodity_impact_agent import get_agent
            events = await get_agent().run_scan(lookback_hours=48)
            self._last_commodity_scan = datetime.now()
            if events:
                top = ", ".join(f"{e['commodity']} {e['direction']}" for e in events[:5])
                logger.info(f"🌾 Commodity scan: {len(events)} events detected ({top})")
            else:
                logger.info("🌾 Commodity scan: no commodity events in recent news")
        except Exception as e:
            logger.error(f"Commodity scan failed: {e}")

    async def run_debate_sweep(self):
        """Challenge research suggestions through the provenance-aware council.

        The method name is kept for scheduler compatibility, but the scheduled
        path now uses Research Council V2.  The council may recommend research
        exposure or HOLD, yet it has no execution authority; actual order flow
        remains Signal Aggregator -> Risk Manager -> strategy/precision gates.
        """
        logger.info("⚖️ Research Council sweep: challenging current suggestions...")
        try:
            from gateway.knowledge_store import knowledge_store
            from agents.research_council import get_research_council

            suggestions = knowledge_store.get_latest_research_suggestions(limit=8)
            tickers = list(dict.fromkeys(
                str(s["ticker"]).upper()
                for s in suggestions
                if s.get("ticker")
            ))
            if not tickers:
                logger.info("⚖️ Research Council sweep: no research suggestions to challenge")
                return

            council = get_research_council()
            for ticker in tickers:
                result = await council.analyze(
                    ticker,
                    use_llm_debate=True,
                    persist=True,
                )
                logger.info(
                    "⚖️ Research %s: %s (%s%%), quality=%.2f contradiction=%.2f "
                    "coverage=%.2f execution_authority=%s",
                    ticker,
                    result.rating,
                    result.confidence,
                    result.evidence_quality,
                    result.contradiction_score,
                    result.coverage_score,
                    result.execution_authority,
                )
            self._last_research_sweep = datetime.now()
        except Exception as e:
            logger.error(f"Research Council sweep failed: {e}")

    async def run_skill_training_epoch(self):
        logger.info("🎓 Skill training epoch starting...")
        try:
            from self_improvement.skill_optimizer import get_optimizer
            results = await get_optimizer().run_epoch()
            logger.info(f"🎓 Skill epoch complete: {len(results['updated'])} updated, {len(results['validated'])} validated, {len(results['skipped'])} skipped")
        except Exception as e:
            logger.error(f"Skill training epoch failed: {e}")

    async def run_mirofish_sync(self):
        logger.info("🌊 MiroFish: Starting World Intelligence cycle...")
        try:
            await world_collector.run_discovery_round()
            await simulation_engine.run_round("automatic social and world trend monitoring")
            report = await report_agent.generate_future_outcome_report()
            logger.info("✅ MiroFish cycle complete. New report available.")
            from gateway.knowledge_store import knowledge_store
            knowledge_store.store_insight(
                ticker="WORLD", agent_name="MiroFish", insight_type="WorldReport",
                content=report, confidence=0.9,
            )
        except Exception as e:
            logger.error(f"MiroFish cycle failed: {e}")

    def get_status(self) -> dict:
        return {
            "any_market_open": self.any_market_open(),
            "indian_market": MarketManager.get_market_status("INDIA"),
            "us_market": MarketManager.get_market_status("US"),
            "last_news_scrape": self._last_news_scrape.isoformat() if self._last_news_scrape else None,
            "last_commodity_scan": self._last_commodity_scan.isoformat() if self._last_commodity_scan else None,
            "last_price_update": self._last_price_update.isoformat() if self._last_price_update else None,
            "last_research_sweep": self._last_research_sweep.isoformat() if self._last_research_sweep else None,
            "research_engine": "ResearchCouncilV2",
            "research_execution_authority": False,
            "startup_catchup_done": self._startup_scrape_done,
            "should_scrape_news_now": self.should_scrape_news(),
            "should_scrape_prices_now": self.should_scrape_prices(),
            "news_interval_minutes": max(int(settings.NEWS_FETCH_INTERVAL_MIN), 5) if self.any_market_open() else max(int(settings.NEWS_FETCH_INTERVAL_MIN), 60),
            "price_interval_minutes": max(int(settings.PRICE_FETCH_INTERVAL_MIN), 1),
        }


market_scheduler = MarketScheduler()
