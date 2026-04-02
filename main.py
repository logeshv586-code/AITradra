"""
AXIOM unified entry point.
Starts the scheduler and gateway API, while warming optional heavy services in the background.
"""

import asyncio
import sys
from datetime import datetime, timedelta

import uvicorn

from agents.collector_agent import index_knowledge_to_rag
from core.config import settings
from core.logger import get_logger
from gateway.server import app, scheduler
from llm.client import LLMClient
from memory.mem0_manager import Mem0Manager

logger = get_logger(__name__)


async def _warm_local_llm():
    """Warm the optional local GGUF fallback without delaying API availability."""
    logger.info("Scheduling local GGUF preload in background...")
    ok = await asyncio.to_thread(LLMClient.preload_local_gguf)
    if ok:
        logger.info("Local GGUF preload completed.")
    else:
        logger.warning("Local GGUF preload skipped or failed. Continuing with configured providers.")


async def _warm_mem0():
    """Initialize Mem0 in the background so offline services do not block startup."""
    logger.info("Scheduling Persistent Memory (Mem0 + Qdrant) in background...")
    memory = await asyncio.to_thread(Mem0Manager)
    if getattr(memory, "initialized", False):
        logger.info("Mem0 background initialization completed.")
    else:
        logger.warning("Mem0 background initialization unavailable. Continuing without it.")


async def main():
    logger.info("Starting AXIOM V4 open-source intelligence stack")

    # Skip automatic GGUF warming to save memory/CPU on startup. 
    # Analysis will load models on-demand if local inference is requested.
    # asyncio.create_task(_warm_local_llm()) 
    asyncio.create_task(_warm_mem0())

    if not scheduler.running:
        from agents.base_agent import AgentContext
        from agents.research_engine import DeepResearchAgent
        from gateway.intelligence_service import intelligence_service
        from core.market_scheduler import market_scheduler
        
        logger.info("Configuring smart market-aware scheduler...")

        # One-time startup catch-up is now backgrounded to avoid delaying API availability.
        asyncio.create_task(market_scheduler.startup_catchup())

        # Phase 1: Heavy lifting in background - Delayed for 30s to allow server to stabilize
        scheduler.add_job(
            intelligence_service.warm_watchlist_intelligence,
            "interval",
            minutes=15,
            id="warm_intelligence",
            next_run_time=datetime.now() + timedelta(seconds=30)
        )
        
        scheduler.add_job(
            market_scheduler.run_scheduled_news_collection,
            "interval",
            minutes=settings.NEWS_FETCH_INTERVAL_MIN,
            id="smart_news",
        )
        scheduler.add_job(
            market_scheduler.run_scheduled_price_collection,
            "interval",
            minutes=settings.PRICE_FETCH_INTERVAL_MIN,
            id="smart_prices",
        )
        scheduler.add_job(
            index_knowledge_to_rag,
            "interval",
            minutes=settings.RAG_REINDEX_INTERVAL_MIN,
            id="index_rag",
        )

        deep_research_agent = DeepResearchAgent()
        scheduler.add_job(
            deep_research_agent.run,
            "cron",
            hour=9,
            minute=30,
            timezone="US/Eastern",
            args=[AgentContext(task="Daily deep stock research sweep")],
            id="deep_research",
        )

        scheduler.start()
        logger.info("Background scheduler started.")

    logger.info("Launching AXIOM Gateway API on %s:%s", settings.HOST, settings.PORT)

    config = uvicorn.Config(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower(),
        lifespan="on",
    )
    server = uvicorn.Server(config)

    try:
        await server.serve()
    except KeyboardInterrupt:
        logger.info("AXIOM shutting down gracefully...")
    finally:
        if scheduler.running:
            scheduler.shutdown()
        logger.info("AXIOM system offline.")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
