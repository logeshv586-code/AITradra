"""AXIOM market-aware scheduler for collection, research and learning jobs."""

import asyncio
from datetime import datetime

from core.config import settings
from core.logger import get_logger
from core.market_manager import MarketManager
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
        self._last_research_evaluation = None
        self._startup_scrape_done = False
        self._running = False

    def is_indian_market_open(self) -> bool:
        return MarketManager.get_market_status("INDIA") == "OPEN"

    def is_us_market_open(self) -> bool:
        return MarketManager.get_market_status("US") == "OPEN"

    def any_market_open(self) -> bool:
        return any(
            MarketManager.get_market_status(key) == "OPEN"
            for key in MarketManager.MARKETS
        )

    def should_scrape_prices(self) -> bool:
        if not self.any_market_open():
            return False
        if self._last_price_update is None:
            return True
        interval = max(int(settings.PRICE_FETCH_INTERVAL_MIN), 1) * 60
        return (datetime.now() - self._last_price_update).total_seconds() > interval

    def should_scrape_news(self) -> bool:
        if self._last_news_scrape is None:
            return True
        elapsed = (datetime.now() - self._last_news_scrape).total_seconds()
        interval = (
            max(int(settings.NEWS_FETCH_INTERVAL_MIN), 5)
            if self.any_market_open()
            else max(int(settings.NEWS_FETCH_INTERVAL_MIN), 60)
        )
        return elapsed > interval * 60

    async def startup_catchup(self):
        if self._startup_scrape_done:
            return
        logger.info("Market Scheduler: checking data freshness on startup")
        try:
            from gateway.knowledge_store import knowledge_store

            status = knowledge_store.get_collection_status()
            if status.get("total_news_articles", 0) <= 0:
                await self._run_rss_catchup()
            else:
                logger.info(
                    "KnowledgeStore already has %s articles",
                    status["total_news_articles"],
                )
        except Exception as exc:
            logger.warning("Startup catchup check failed: %s", exc)
            await self._run_rss_catchup()
        self._startup_scrape_done = True

    async def _run_rss_catchup(self):
        try:
            from gateway.scrapers.rss_scraper import rss_scraper

            await asyncio.to_thread(rss_scraper.fetch_all)
            self._last_news_scrape = datetime.now()
        except Exception as exc:
            logger.error("RSS catch-up failed: %s", exc)

    async def run_scheduled_news_collection(self):
        if not self.should_scrape_news():
            return
        try:
            from gateway.scrapers.rss_scraper import rss_scraper

            await asyncio.to_thread(rss_scraper.fetch_all)
            self._last_news_scrape = datetime.now()
        except Exception as exc:
            logger.error("RSS news collection failed: %s", exc)

    async def run_scheduled_price_collection(self):
        if not self.should_scrape_prices():
            return
        try:
            from agents.collector_agent import collect_daily_data

            await collect_daily_data()
            self._last_price_update = datetime.now()
        except Exception as exc:
            logger.error("Price collection failed: %s", exc)

    async def run_commodity_scan(self):
        if self._last_commodity_scan is not None:
            elapsed = (datetime.now() - self._last_commodity_scan).total_seconds()
            interval = 3600 if self.any_market_open() else 21600
            if elapsed < interval:
                return
        try:
            from agents.commodity_impact_agent import get_agent

            events = await get_agent().run_scan(lookback_hours=48)
            self._last_commodity_scan = datetime.now()
            logger.info("Commodity scan completed with %s events", len(events or []))
        except Exception as exc:
            logger.error("Commodity scan failed: %s", exc)

    async def run_research_scorecard_evaluation(self):
        """Resolve later outcomes without blocking the event loop.

        Research scorecard metrics are deliberately separate from the empirical
        autonomous-live precision store.
        """
        try:
            from self_improvement.research_scorecard import research_scorecard

            result = await asyncio.to_thread(research_scorecard.evaluate_pending)
            self._last_research_evaluation = datetime.now()
            logger.info(
                "Research scorecard: evaluated=%s outcomes_added=%s skipped=%s",
                result.get("evaluated", 0),
                result.get("outcomes_added", 0),
                result.get("skipped", 0),
            )
            return result
        except Exception as exc:
            logger.error("Research scorecard evaluation failed: %s", exc)
            return {"evaluated": 0, "outcomes_added": 0, "error": type(exc).__name__}

    async def run_debate_sweep(self):
        """Challenge current suggestions through Research Council V2.

        The legacy method name is kept for scheduler compatibility. Research has
        no execution authority; order flow remains Signal Aggregator -> Risk
        Manager -> strategy validation -> empirical precision -> broker auth.
        """
        await self.run_research_scorecard_evaluation()
        try:
            from gateway.knowledge_store import knowledge_store
            from agents.research_council import get_research_council

            suggestions = knowledge_store.get_latest_research_suggestions(limit=8)
            tickers = list(dict.fromkeys(
                str(row["ticker"]).upper()
                for row in suggestions
                if row.get("ticker")
            ))
            if not tickers:
                logger.info("Research Council sweep: no suggestions to challenge")
                self._last_research_sweep = datetime.now()
                return

            council = get_research_council()
            for ticker in tickers:
                result = await council.analyze(
                    ticker,
                    use_llm_debate=True,
                    persist=True,
                )
                logger.info(
                    "Research %s: %s conf=%s quality=%.2f contradiction=%.2f "
                    "coverage=%.2f diversity=%.2f execution=%s",
                    ticker,
                    result.rating,
                    result.confidence,
                    result.evidence_quality,
                    result.contradiction_score,
                    result.coverage_score,
                    result.source_diversity_score,
                    result.execution_authority,
                )
            self._last_research_sweep = datetime.now()
        except Exception as exc:
            logger.error("Research Council sweep failed: %s", exc)

    async def run_skill_training_epoch(self):
        try:
            from self_improvement.skill_optimizer import get_optimizer

            results = await get_optimizer().run_epoch()
            logger.info(
                "Skill epoch: %s updated, %s validated, %s skipped",
                len(results["updated"]),
                len(results["validated"]),
                len(results["skipped"]),
            )
        except Exception as exc:
            logger.error("Skill training epoch failed: %s", exc)

    async def run_mirofish_sync(self):
        try:
            await world_collector.run_discovery_round()
            await simulation_engine.run_round(
                "automatic social and world trend monitoring"
            )
            report = await report_agent.generate_future_outcome_report()
            from gateway.knowledge_store import knowledge_store

            knowledge_store.store_insight(
                ticker="WORLD",
                agent_name="MiroFish",
                insight_type="WorldReport",
                content=report,
                confidence=0.9,
            )
        except Exception as exc:
            logger.error("MiroFish cycle failed: %s", exc)

    def get_status(self) -> dict:
        news_interval = (
            max(int(settings.NEWS_FETCH_INTERVAL_MIN), 5)
            if self.any_market_open()
            else max(int(settings.NEWS_FETCH_INTERVAL_MIN), 60)
        )
        return {
            "any_market_open": self.any_market_open(),
            "indian_market": MarketManager.get_market_status("INDIA"),
            "us_market": MarketManager.get_market_status("US"),
            "last_news_scrape": (
                self._last_news_scrape.isoformat() if self._last_news_scrape else None
            ),
            "last_commodity_scan": (
                self._last_commodity_scan.isoformat() if self._last_commodity_scan else None
            ),
            "last_price_update": (
                self._last_price_update.isoformat() if self._last_price_update else None
            ),
            "last_research_sweep": (
                self._last_research_sweep.isoformat() if self._last_research_sweep else None
            ),
            "last_research_evaluation": (
                self._last_research_evaluation.isoformat()
                if self._last_research_evaluation else None
            ),
            "research_engine": "ResearchCouncilV2",
            "research_scorecard": "forward_audit_v2",
            "research_execution_authority": False,
            "research_scorecard_live_gate_input": False,
            "startup_catchup_done": self._startup_scrape_done,
            "should_scrape_news_now": self.should_scrape_news(),
            "should_scrape_prices_now": self.should_scrape_prices(),
            "news_interval_minutes": news_interval,
            "price_interval_minutes": max(int(settings.PRICE_FETCH_INTERVAL_MIN), 1),
        }


market_scheduler = MarketScheduler()
