"""
mcp/news_mcp.py  —  Institutional News MCP (Layer 5)
===================================================
Standardized tool set for agents to fetch and filter news catalysts.
Connects to KnowledgeStore and NewsIntelAgent sources.
"""

import logging
from typing import List, Dict, Any, Optional
from gateway.knowledge_store import knowledge_store
from core.logger import get_logger

logger = get_logger(__name__)

class NewsMCP:
    """
    Standardized interface for agents to query news data.
    """
    def __init__(self):
        logger.info("NewsMCP initialized.")

    async def search_news(self, ticker: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for news headlines for a specific ticker in the KnowledgeStore.
        """
        try:
            # Filters news from the SQLite DB
            articles = knowledge_store.get_news_for_ticker(ticker, limit=limit)
            return articles
        except Exception as e:
            logger.error(f"NewsMCP search failed for {ticker}: {e}")
            return []

    async def get_drivers(self, ticker: str) -> Optional[str]:
        """
        Get the primary drivers extracted by the NewsIntelAgent for a ticker.
        """
        # Logic to fetch from agent_insights where architect=NewsIntelAgent
        try:
            insights = knowledge_store.get_latest_insights(ticker, agent_name="NewsIntelAgent", limit=1)
            if insights:
                return insights[0].get("payload", {}).get("primary_driver")
            return None
        except Exception as e:
            logger.error(f"NewsMCP failed to get drivers for {ticker}: {e}")
            return None

# Global instance
_mcp_instance = None

def get_news_mcp():
    global _mcp_instance
    if _mcp_instance is None:
        _mcp_instance = NewsMCP()
    return _mcp_instance
