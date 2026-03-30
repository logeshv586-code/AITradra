"""
AXIOM V4 — Unified 100% Open-Source Intelligence Backend
Consolidates orchestration, preloading, and server startup into a single entry point.
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
from agents.collector_agent import (
    collect_news_data, index_knowledge_to_rag, collect_daily_data, collect_historical_data
)

logger = get_logger(__name__)

async def main():
    logger.info("Starting AXIOM V4 — Unified Backend Intelligence Stack")
    
    # 1. Preload Local LLM (NVIDIA Nemotron GGUF) from nvidia/Nemotron-3-Nano-4B-GGUF
    logger.info("🧠 Preloading LLM globally...")
    if not await asyncio.to_thread(LLMClient.preload_local_gguf):
        logger.warning("Local GGUF preload failed. Ensure model exists in /models/ or fall back to Ollama.")
    
    # 2. Initialize Memory System (Mem0 + Qdrant)
    logger.info("💾 Initializing Persistent Memory (Mem0 + Qdrant)...")
    memory = Mem0Manager()
    if not memory.initialized:
        logger.error("Memory system failed to initialize. Critical components (Qdrant) may be offline.")
    
    # 3. Setup Scheduler (Background Intelligence Processes)
    # These are already defined in gateway/server.py, but we ensure they run
    if not scheduler.running:
        logger.info("⏰ Starting Background Intelligence Scheduler...")
        scheduler.start()
    
    # 4. Trigger initial data collection in background (non-blocking)
    logger.info("📡 Triggering initial data collection and RAG indexing...")
    asyncio.create_task(collect_news_data())
    asyncio.create_task(collect_historical_data())
    
    # 5. Start Gateway API
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
        scheduler.shutdown()
        logger.info("AXIOM V4 system offline.")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
