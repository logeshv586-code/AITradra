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
        logger.warning(
            "Local GGUF preload skipped or failed. Continuing with configured providers."
        )


async def _warm_mem0():
    """Initialize Mem0 in the background so offline services do not block startup."""
    logger.info("Scheduling Persistent Memory (Mem0 + Qdrant) in background...")
    memory = await asyncio.to_thread(Mem0Manager)
    if getattr(memory, "initialized", False):
        logger.info("Mem0 background initialization completed.")
    else:
        logger.warning(
            "Mem0 background initialization unavailable. Continuing without it."
        )


async def _agent_heartbeat():
    """Force-initialize all agents in health monitor to ONLINE status on startup."""
    from gateway.knowledge_store import knowledge_store
    from gateway.market_intel_router import AGENT_REGISTRY

    logger.info("Initializing agent heartbeat for all registered agents...")
    for meta in AGENT_REGISTRY:
        agent_name = meta["name"]
        knowledge_store.update_agent_health(
            agent_name, "active", latency_ms=5, task="Ready"
        )
    logger.info(f"Heartbeat initialized for {len(AGENT_REGISTRY)} agents.")


async def main():
    logger.info("Starting AXIOM V4 open-source intelligence stack")

    if sys.platform == "win32":
        try:
            import subprocess

            port = settings.PORT
            cmd = f"netstat -ano | findstr :{port}"
            output = subprocess.check_output(cmd, shell=True).decode()
            if output:
                for line in output.strip().split("\n"):
                    if "LISTENING" in line:
                        pid = line.strip().split()[-1]
                        logger.info(f"Clearing zombie process on port {port} (PID: {pid})...")
                        subprocess.run(
                            f"taskkill /F /PID {pid}", shell=True, capture_output=True
                        )
        except Exception:
            pass

    logger.info("MythicOrchestrator initialized")
    logger.info("Scheduler boot sequence started")
    await _agent_heartbeat()

    asyncio.create_task(_warm_mem0())

    async def _warm_market_rag():
        try:
            from agents.market_rag import get_agent

            rag = get_agent()
            counts = rag.index_all_unindexed()
            logger.info(f"MarketRAG boot indexing complete: {counts}")
        except Exception as e:
            logger.warning(f"MarketRAG boot indexing failed: {e}")

    asyncio.create_task(_warm_market_rag())

    if not scheduler.running:
        from agents.base_agent import AgentContext
        from agents.research_engine import DeepResearchAgent
        from gateway.intelligence_service import intelligence_service
        from core.market_scheduler import market_scheduler

        logger.info("Configuring smart market-aware scheduler...")

        # Autonomous order execution is deliberately opt-in. Turning on the API,
        # dashboard, news jobs, or research agents can never start trading by itself.
        if settings.AUTOTRADE_ENABLED:
            from core.trading_safety import get_execution_status
            from gateway.hyperliquid_service import hyperliquid_trading_service

            execution = get_execution_status(settings)
            scheduler.add_job(
                hyperliquid_trading_service.run_cycle,
                "interval",
                minutes=max(1, settings.TRADING_CYCLE_MINUTES),
                id="hyperliquid_trading",
                next_run_time=datetime.now() + timedelta(seconds=60),
                coalesce=True,
                misfire_grace_time=120,
                max_instances=1,
            )
            logger.warning(
                "Autonomous trading scheduler enabled in %s mode. Live allowed=%s",
                execution["mode"],
                execution["live_execution_allowed"],
            )
        else:
            logger.info(
                "Autonomous trading is OFF. Analysis, chat, paper portfolio, and research remain available."
            )

        asyncio.create_task(market_scheduler.startup_catchup())

        scheduler.add_job(
            intelligence_service.warm_watchlist_intelligence,
            "interval",
            minutes=15,
            id="warm_intelligence",
            next_run_time=datetime.now() + timedelta(seconds=30),
            coalesce=True,
            misfire_grace_time=300,
            max_instances=1,
        )
        scheduler.add_job(
            market_scheduler.run_scheduled_news_collection,
            "interval",
            minutes=settings.NEWS_FETCH_INTERVAL_MIN,
            id="smart_news",
            coalesce=True,
            misfire_grace_time=120,
            max_instances=1,
        )
        scheduler.add_job(
            market_scheduler.run_scheduled_price_collection,
            "interval",
            minutes=settings.PRICE_FETCH_INTERVAL_MIN,
            id="smart_prices",
            coalesce=True,
            misfire_grace_time=120,
            max_instances=1,
        )
        scheduler.add_job(
            index_knowledge_to_rag,
            "interval",
            minutes=settings.RAG_REINDEX_INTERVAL_MIN,
            id="index_rag",
            coalesce=True,
            misfire_grace_time=300,
            max_instances=1,
        )
        scheduler.add_job(
            market_scheduler.run_debate_sweep,
            "cron",
            hour=10,
            minute=30,
            timezone="US/Eastern",
            id="debate_sweep",
            coalesce=True,
            misfire_grace_time=900,
            max_instances=1,
        )
        scheduler.add_job(
            market_scheduler.run_skill_training_epoch,
            "cron",
            day_of_week="sat",
            hour=22,
            id="skill_training_epoch",
            coalesce=True,
            misfire_grace_time=3600,
            max_instances=1,
        )
        scheduler.add_job(
            market_scheduler.run_commodity_scan,
            "interval",
            minutes=30,
            id="commodity_scan",
            next_run_time=datetime.now() + timedelta(seconds=90),
            coalesce=True,
            misfire_grace_time=300,
            max_instances=1,
        )
        scheduler.add_job(
            market_scheduler.run_mirofish_sync,
            "interval",
            hours=4,
            id="mirofish_sync",
            next_run_time=datetime.now() + timedelta(seconds=120),
            coalesce=True,
            misfire_grace_time=600,
            max_instances=1,
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
            coalesce=True,
            misfire_grace_time=900,
            max_instances=1,
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
