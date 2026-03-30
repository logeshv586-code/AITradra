"""
AXIOM V4 — 100% Open-Source Unified Entry Point.
Preloads Local LLM, Starts Scheduler, and Runs Gateway API.
"""
import uvicorn
import asyncio
import os
import sys
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
    logger.info("⏰ Configuring Background Intelligence Scheduler...")
    # RSS Scraper
    scheduler.add_job(rss_scraper.fetch_all, "interval", minutes=5, id="rss_sync")
    # News Intel
    scheduler.add_job(collect_news_data, "interval", minutes=5, id="collect_news")
    # RAG Indexing
    scheduler.add_job(index_knowledge_to_rag, "interval", minutes=15, id="index_rag")
    # Daily OHLCV
    scheduler.add_job(collect_daily_data, "interval", hours=24, id="collect_daily")
    
    # Trigger initial data collection in background (non-blocking)
    asyncio.create_task(collect_news_data())
    asyncio.create_task(collect_historical_data())
    
    logger.info("📡 Background tasks scheduled and initial collection triggered.")
    
    # 4. Start Gateway API
    logger.info("🌐 Launching AXIOM Gateway API...")
    config = uvicorn.Config(
        app, 
        host="0.0.0.0", 
        port=8000, 
        log_level="info",
        lifespan="on"
    )
    server = uvicorn.Server(config)
    
    try:
        await server.serve()
    except KeyboardInterrupt:
        logger.info("AXIOM V4 shutting down gracefully...")
    finally:
        scheduler.shutdown()
        logger.info("AXIOM V4 system offline.")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
