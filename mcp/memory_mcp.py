"""
mcp/memory_mcp.py  —  Institutional Memory MCP (Layer 5)
=====================================================
Standardized tool set for agents to query long-term memory and RAG.
Connects directly to MarketRAGAgent for semantic retrieval.
"""

import logging
from typing import List, Dict, Any, Optional
from agents.market_rag import get_agent as get_rag_agent
from core.logger import get_logger

logger = get_logger(__name__)

class MemoryMCP:
    """
    Standardized interface for agents to query semantic memory.
    """
    def __init__(self):
        self.rag = get_rag_agent()
        logger.info("MemoryMCP initialized with MarketRAG.")

    async def query_memory(self, question: str, symbol: Optional[str] = None, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Semantic search over agent insights and news history.
        """
        try:
            chunks = self.rag.retrieve(question, symbol=symbol, top_k=top_k)
            return [
                {
                    "text": c.text,
                    "score": c.score,
                    "symbol": c.symbol,
                    "type": c.source_type,
                    "created_at": c.created_at
                } for c in chunks
            ]
        except Exception as e:
            logger.error(f"MemoryMCP query failed: {e}")
            return []

    async def get_summary(self, ticker: str) -> Optional[str]:
        """
        Get a quick RAG-based summary of the current status for a ticker.
        """
        try:
            return self.rag.ask_sync(f"Summarize the current situation for {ticker} based on recent news and insights.", ticker)
        except Exception as e:
            logger.error(f"MemoryMCP summary failed for {ticker}: {e}")
            return None

# Global instance
_mcp_instance = None

def get_memory_mcp():
    global _mcp_instance
    if _mcp_instance is None:
        _mcp_instance = MemoryMCP()
    return _mcp_instance
