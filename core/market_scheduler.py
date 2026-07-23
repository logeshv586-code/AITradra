"""
AXIOM Market-Aware Scheduler — Smart data collection based on market hours.

Rules:
  1. During market hours (9:15 AM - 3:30 PM IST): collect every 5 minutes
  2. Outside market hours: collect news every 12 hours (12 AM / 12 PM)
  3. On startup: if no data exists, do a one-time catch-up scrape immediately
  4. Stock price data: only update during market hours (no point scraping stale prices)
  5. News data: always available via RSS (lightweight, no browser needed)

This replaces the blind "scrape every 5 minutes 24/7" approach that was
crashing Playwright and wasting resources.
"""

import asyncio
from datetime import datetime, timedelta
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
        self._startup_scrape_done = False
        self._running = False

    def is_indian_market_open(self) -> bool:
        """Check if NSE/BSE is currently open."""
        return MarketManager.get_market_status("INDIA") == "OPEN"

    def is_us_market_open(self) -> bool:
        """Check if NYSE/NASDAQ is currently open."""
        return MarketManager.get_market_status("US") == "OPEN"

    def any_market_open(self) -> bool:
        """Check if any major market (including 24/7 Crypto) is open."""
        for key in MarketManager.MARKETS:
            if MarketManager.get_market_status(key) == "OPEN":
                return True
        return False

    def should_scrape_prices(self) -> bool:
        """Only scrape prices during market hours."""
        if self.any_market_open():
            # During market hours: every 5 minutes
            if self._last_price_update is None:
                return True
            return (datetime.now() - self._last_price_update).total_seconds() > 300
        return False

    def should_scrape_news(self) -> bool:
        """Scrape news every 12 hours, or immediately if no data exists."""
        if self._last_news_scrape is None:
            return True
        elapsed = (datetime.now() - self._last_news_scrape).total_seconds()
        if self.any_market_open():
            # During market hours: every 30 minutes for news
            return elapsed > 1800
        else:
            # Outside market hours: every 12 hours
            return elapsed > 43200

    async def startup_catchup(self):
        """
        Called on server startup. Checks if we have any recent data.
        If not, does a one-time RSS fetch (lightweight, no Playwright needed).
        """
        if self._startup_scrape_done:
            return

        logger.info("🔍 Market Scheduler: Checking data freshness on startup...")

        try:
            from gateway.knowledge_store import knowledge_store
            status = knowledge_store.get_collection_status()
            has_news = status.get("total_news_articles", 0) > 0

            if not has_news:
                logger.info("⚠️  No news data found! Running one-time RSS catch-up scrape...")
                await self._run_rss_catchup()
            else:
                logger.info(f"✅ KnowledgeStore has {status['total_news_articles']} articles. Skipping catch-up.")

        except Exception as e:
            logger.warning(f"Startup catchup check failed: {e}. Running RSS fetch anyway.")
            await self._run_rss_catchup()

        self._startup_scrape_done = True

    async def _run_rss_catchup(self):
        """Use feedparser-based RSS scraper (fast, no browser, no crashes)."""
        try:
            from gateway.scrapers.rss_scraper import rss_scraper
            await asyncio.to_thread(rss_scraper.fetch_all)
            self._last_news_scrape = datetime.now()
            logger.info("✅ RSS catch-up complete. News data is now available.")
        except Exception as e:
            logger.error(f"RSS catch-up failed: {e}")

    async def run_scheduled_news_collection(self):
        """Called by the APScheduler job. Market-aware news collection."""
        if not self.should_scrape_news():
            return

        logger.info(f"📰 Scheduled news collection (market_open={self.any_market_open()})")

        # Always use RSS first (lightweight, reliable)
        try:
            from gateway.scrapers.rss_scraper import rss_scraper
            await asyncio.to_thread(rss_scraper.fetch_all)
            self._last_news_scrape = datetime.now()
        except Exception as e:
            logger.error(f"RSS news collection failed: {e}")

    async def run_scheduled_price_collection(self):
        """Called by the APScheduler job. Only during market hours."""
        if not self.should_scrape_prices():
            now = datetime.now()
            logger.info(f"⏸️  Price collection skipped (no markets open at {now.strftime('%H:%M')} IST)")
            return

        logger.info("📈 Price collection triggered (market is OPEN)")

        try:
            from agents.collector_agent import collect_daily_data
            await collect_daily_data()
            self._last_price_update = datetime.now()
        except Exception as e:
            logger.error(f"Price collection failed: {e}")

    async def run_commodity_scan(self):
        """
        Commodity causal-chain scan — runs after news collection so it sees
        fresh headlines. Market-aware cadence: hourly while any market is
        open, every 6 hours otherwise (commodity news flows around the clock).
        """
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
        """
        Daily adversarial review: run a bull/bear debate on every ticker the
        DeepResearch layer flagged, so no suggestion reaches the user without
        having survived a structured bear rebuttal.
        """
        logger.info("⚖️ Debate sweep: challenging current research suggestions...")
        try:
            from gateway.knowledge_store import knowledge_store
            from agents.debate_engine import get_engine

            suggestions = knowledge_store.get_latest_research_suggestions(limit=5)
            tickers = list({s["ticker"] for s in suggestions if s.get("ticker")})
            if not tickers:
                logger.info("⚖️ Debate sweep: no research suggestions to challenge")
                return
            engine = get_engine()
            for ticker in tickers:
                result = await engine.run_debate(ticker)
                logger.info(
                    f"⚖️ Debate {ticker}: {result.verdict} ({result.confidence}%) "
                    f"— {result.winning_side} won"
                )
        except Exception as e:
            logger.error(f"Debate sweep failed: {e}")

    async def run_autopilot_cycle(self):
        """
        Paper-trading autopilot cycle. Exits are checked on every run (they
        must react to price moves); the autopilot internally limits new
        entries to one batch per day. Skipped entirely when no market is
        open, because stored prices cannot have changed.
        """
        if not self.any_market_open():
            return
        try:
            from agents.paper_autopilot import get_autopilot
            report = await get_autopilot().run_cycle()
            actions = report.get("actions_this_cycle", {})
            n_open, n_close = len(actions.get("entries", [])), len(actions.get("exits", []))
            if n_open or n_close:
                logger.info(
                    f"🤖 Autopilot: {n_open} opened, {n_close} closed — "
                    f"equity {report['balance']['equity']} "
                    f"({report['balance']['total_return_pct']:+.2f}%)"
                )
        except Exception as e:
            logger.error(f"Autopilot cycle failed: {e}")

    async def run_skill_training_epoch(self):
        """Weekly SkillOpt-style epoch: validate active skill versions, then train."""
        logger.info("🎓 Skill training epoch starting...")
        try:
            from self_improvement.skill_optimizer import get_optimizer
            results = await get_optimizer().run_epoch()
            logger.info(
                f"🎓 Skill epoch complete: {len(results['updated'])} updated, "
                f"{len(results['validated'])} validated, {len(results['skipped'])} skipped"
            )
        except Exception as e:
            logger.error(f"Skill training epoch failed: {e}")

    async def run_mirofish_sync(self):
        """MiroFish 4-hour background cycle: Collect, Simulate, Report."""
        logger.info("🌊 MiroFish: Starting 4-hour World Intelligence cycle...")
        try:
            # 1. Discovery (Collector)
            await world_collector.run_discovery_round()
            
            # 2. Simulation (Engine)
            await simulation_engine.run_round("automatic social and world trend monitoring")
            
            # 3. Reporting (Agent)
            report = await report_agent.generate_future_outcome_report()
            logger.info("✅ MiroFish: 4-hour cycle complete. New report available.")
            
            # Optional: Store report in Agent Insights
            from gateway.knowledge_store import knowledge_store
            knowledge_store.store_insight(
                ticker="WORLD", 
                agent_name="MiroFish", 
                insight_type="WorldReport", 
                content=report, 
                confidence=0.9
            )
        except Exception as e:
            logger.error(f"MiroFish cycle failed: {e}")

    def get_status(self) -> dict:
        """Return scheduler status for the diagnostic endpoint."""
        return {
            "any_market_open": self.any_market_open(),
            "indian_market": MarketManager.get_market_status("INDIA"),
            "us_market": MarketManager.get_market_status("US"),
            "last_news_scrape": self._last_news_scrape.isoformat() if self._last_news_scrape else None,
            "last_commodity_scan": self._last_commodity_scan.isoformat() if self._last_commodity_scan else None,
            "last_price_update": self._last_price_update.isoformat() if self._last_price_update else None,
            "startup_catchup_done": self._startup_scrape_done,
            "should_scrape_news_now": self.should_scrape_news(),
            "should_scrape_prices_now": self.should_scrape_prices(),
        }


# Global singleton
market_scheduler = MarketScheduler()
