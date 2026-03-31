"""
AXIOM V4 — 100% Open-Source Unified Entry Point.
Preloads Local LLM, Starts Scheduler, and Runs Gateway API.
"""
import uvicorn
import asyncio
import os
import sys
from core.config import settings
from core.logger import get_logger
from llm.client import LLMClient
from memory.mem0_manager import Mem0Manager
from gateway.server import app, scheduler
from gateway.scrapers.rss_scraper import rss_scraper
from agents.collector_agent import (
    collect_news_data, index_knowledge_to_rag, collect_daily_data, collect_historical_data
)

logger = get_logger(__name__)

async def main():
    logger.info("Starting AXIOM V4 — 100% Open-Source Intelligence Stack")
    
    # 1. Preload Local LLM (NVIDIA Nemotron GGUF)
    logger.info("🧠 Preloading LLM globally...")
    if not await asyncio.to_thread(LLMClient.preload_local_gguf):
        logger.warning("Local GGUF preload failed. Falling back to Ollama API.")
    
    # 2. Initialize Memory System (Mem0 + Qdrant)
    logger.info("💾 Initializing Persistent Memory (Mem0 + Qdrant)...")
    memory = Mem0Manager()
    if not memory.initialized:
        logger.error("Memory system failed to initialize. Critical components may be offline.")
    
    # 3. Setup Scheduler (Background Intelligence)
    if not scheduler.running:
        from core.market_scheduler import market_scheduler
        logger.info("⏰ Configuring Smart Market-Aware Scheduler...")
        
        # One-time startup catch-up (if KnowledgeStore is empty)
        await market_scheduler.startup_catchup()

        # Smart News Collection (RSS-first, frequency based on market hours)
        scheduler.add_job(
            market_scheduler.run_scheduled_news_collection, 
            "interval", minutes=settings.NEWS_FETCH_INTERVAL_MIN, id="smart_news"
        )
        
        # Smart Price Collection (Only runs during market hours)
        scheduler.add_job(
            market_scheduler.run_scheduled_price_collection, 
            "interval", minutes=settings.PRICE_FETCH_INTERVAL_MIN, id="smart_prices"
        )
        
        # RAG Indexing (Always useful, frequency from settings)
        scheduler.add_job(
            index_knowledge_to_rag, 
            "interval", minutes=settings.RAG_REINDEX_INTERVAL_MIN, id="index_rag"
        )
        
        scheduler.start()
        logger.info("📡 Background scheduler started with smart, market-aware rules.")
    
    # 4. Start Gateway API
    logger.info(f"🌐 Launching AXIOM Gateway API on {settings.HOST}:{settings.PORT}")

    config = uvicorn.Config(
        app, 
        host=settings.HOST, 
        port=settings.PORT, 
        log_level=settings.LOG_LEVEL.lower(),
        lifespan="on"
    )
    server = uvicorn.Server(config)
    
    try:
        await server.serve()
    except KeyboardInterrupt:
        logger.info("AXIOM V4 shutting down gracefully...")
    finally:
        if scheduler.running:
            scheduler.shutdown()
        logger.info("AXIOM V4 system offline.")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
