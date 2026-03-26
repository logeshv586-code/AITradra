"""Semantic Memory — ChromaDB vector store wrapper for agent episodic search."""

from core.logger import get_logger
from core.config import settings
import json

logger = get_logger(__name__)


class SemanticVectorStore:
    """Manages embedding and semantic search over agent past episodes."""

    def __init__(self):
        self.host = settings.CHROMADB_HOST
        self.port = settings.CHROMADB_PORT
        self.collection_name = settings.CHROMADB_COLLECTION
        self._client = None
        self._collection = None
        self._initialized = False

    async def initialize(self):
        """Connect to ChromaDB (non-blocking in async context)."""
        try:
            import chromadb
            self._client = chromadb.HttpClient(host=self.host, port=self.port)
            self._collection = self._client.get_or_create_collection(name=self.collection_name)
            self._initialized = True
            logger.info(f"Connected to ChromaDB: {self.collection_name}")
        except Exception as e:
            logger.warning(f"ChromaDB connection skipped/failed (expected if Chroma not running): {e}")

    async def add_episode(self, episode_id: str, text: str, metadata: dict):
        """Embed and store an episode."""
        if not self._initialized:
            return
        
        try:
            # We strictly serialize metadata values to strings/ints to satisfy Chroma
            clean_metadata = {k: str(v) for k, v in metadata.items()}
            self._collection.add(
                documents=[text],
                metadatas=[clean_metadata],
                ids=[episode_id]
            )
        except Exception as e:
            logger.error(f"Failed to add document to ChromaDB: {e}")

    async def search(self, query: str, n_results: int = 5) -> list:
        """Perform semantic search for relevance."""
        if not self._initialized:
            return []
            
        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            structured_results = []
            for i in range(len(results['ids'][0])):
                structured_results.append({
                    "id": results['ids'][0][i],
                    "text": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i] if 'distances' in results else None
                })
            return structured_results
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
