"""
MiroFish World Collector — Hybrid scraper for novels, news, and real-world data.
Supports local directories, SearXNG search, and RSS feeds.
"""

import os
import asyncio
import glob
from typing import List, Dict, Any
import httpx
from playwright.async_api import async_playwright

from core.logger import get_logger
from core.graph_memory import graph_memory

logger = get_logger(__name__)

class WorldCollector:
    """
    Ingests 'everything' to build the Digital Parallel World background.
    """

    def __init__(self):
        self.novels_dir = os.getenv("DATA_NOVELS_DIR", "data/novels")
        self.news_dir = os.getenv("DATA_NEWS_DIR", "data/news")
        self.searxng_url = os.getenv("SEARXNG_URL", "http://localhost:8082")
        
        # Ensure directories exist
        os.makedirs(self.novels_dir, exist_ok=True)
        os.makedirs(self.news_dir, exist_ok=True)

    async def collect_local(self):
        """Ingest books/documents from local folders."""
        logger.info(f"Scanning local directories: {self.novels_dir}, {self.news_dir}")
        files = glob.glob(f"{self.novels_dir}/**/*", recursive=True) + \
                glob.glob(f"{self.news_dir}/**/*", recursive=True)
        
        extracted_data = []
        for file_path in files:
            if os.path.isdir(file_path): continue
            
            ext = os.path.splitext(file_path)[1].lower()
            try:
                content = ""
                if ext == ".txt" or ext == ".md":
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                # Basic support for JSON/CSV could go here
                
                if content:
                    extracted_data.append({
                        "text": content,
                        "meta": {"source": file_path, "type": "local_file"}
                    })
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {e}")
        
        if extracted_data:
            await graph_memory.add_documents(
                [d["text"] for d in extracted_data],
                [d["meta"] for d in extracted_data]
            )

    async def collect_web_search(self, query: str):
        """Use SearXNG to gather recent world developments."""
        logger.info(f"Running SearXNG collector for: {query}")
        try:
            async with httpx.AsyncClient() as client:
                # SearXNG API (format=json)
                resp = await client.get(
                    f"{self.searxng_url}/search",
                    params={"q": query, "format": "json"}
                )
                data = resp.json()
                results = data.get("results", [])
                
                texts = [r.get("content", "") for r in results if r.get("content")]
                metas = [{"source": r.get("url"), "title": r.get("title")} for r in results]
                
                if texts:
                    await graph_memory.add_documents(texts, metas)
        except Exception as e:
            logger.error(f"SearXNG collection failed: {e}")

    async def run_discovery_round(self):
        """Automated discovery round for global monitoring."""
        topics = ["global economy", "geopolitical shifts", "emerging technology", "social trends"]
        for topic in topics:
            await self.collect_web_search(topic)
            await asyncio.sleep(2) # Avoid spamming local SearXNG
        
        await self.collect_local()

world_collector = WorldCollector()
