"""
MiroFish Graph Memory — Zep-backed Knowledge Graph store for world events and entities.
Provides entity linking, relationship management, and GraphRAG.
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
from zep_python import ZepClient
from zep_python.document import Document, DocumentCollection
from core.logger import get_logger
from core.config import settings

logger = get_logger(__name__)

class GraphMemory:
    """
    Manages high-fidelity memory using Zep Graph.
    Converts unstructured data (news, novels) into persistent entities and relationships.
    """

    def __init__(self, api_url: str = None):
        self.api_url = api_url or os.getenv("ZEP_API_URL", "http://localhost:8001")
        self.client = None
        self.collection_name = "mirofish_world"
        
        try:
            # The ZepClient constructor performs a health check. 
            # We catch errors here to allow the system to boot without Docker.
            self.client = ZepClient(self.api_url)
            self._ensure_collection()
        except Exception as e:
            logger.warning(f"Zep initialization failed (offline mode): {e}. GraphMemory features will be disabled.")

    def _ensure_collection(self):
        """Internal initialization of Zep collection."""
        if not self.client:
            return
        try:
            # Check if exists or create
            collections = self.client.document.list_collections()
            if not any(c.name == self.collection_name for c in collections):
                self.client.document.add_collection(
                    name=self.collection_name,
                    description="MiroFish Digital World Knowledge Base",
                    embedding_dimensions=1536, # Standard for most local/API models
                    is_auto_embedded=True
                )
                logger.info(f"Created Zep collection: {self.collection_name}")
        except Exception as e:
            logger.warning(f"Zep initialization warning (check if Zep is running): {e}")

    async def add_documents(self, texts: List[str], metadata: List[Dict[str, Any]]):
        """Add world data to the graph memory."""
        docs = [
            Document(content=text, metadata=meta)
            for text, meta in zip(texts, metadata)
        ]
        if not self.client:
            logger.warning("Zep client offline. Skipping document storage.")
            return

        try:
            await asyncio.to_thread(
                self.client.document.add_documents,
                self.collection_name,
                docs
            )
            logger.info(f"Added {len(docs)} documents to Graph Memory")
        except Exception as e:
            logger.error(f"Failed to add documents to Zep: {e}")

    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Semantic and graph-based search for world state retrieval."""
        if not self.client:
            return []

        try:
            results = await asyncio.to_thread(
                self.client.document.search,
                self.collection_name,
                text=query,
                limit=limit
            )
            return [
                {
                    "content": r.content,
                    "metadata": r.metadata,
                    "score": r.score
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Zep search failed: {e}")
            return []

    async def extract_entities(self, text: str):
        """
        Placeholder for advanced entity extraction. 
        Zep handles some of this natively in its graph layer.
        """
        # In a full implementation, we might use Spacy here too.
        pass

graph_memory = GraphMemory()
