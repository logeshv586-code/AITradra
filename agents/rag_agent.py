"""RagAgent — Enhanced Semantic Search Market Intelligence using Claude Flow.

Supports indexing:
- Stock data blobs (legacy)
- News articles from knowledge store
- Market snapshots and agent insights
- Time-filtered semantic queries
"""

import os
import faiss
import numpy as np
import json
from datetime import datetime
import asyncio
from agents.base_agent import BaseAgent, AgentContext

class RagAgent(BaseAgent):
    """Agent 3: Market RAG Agent - Semantic Search Market Intelligence using Claude Flow."""
    
    def __init__(self, memory=None, improvement_engine=None, index_path="gateway/market_rag_index"):
        super().__init__(name="MarketRagAgent", memory=memory, improvement_engine=improvement_engine)
        self.index_path = index_path
        if not os.path.exists(self.index_path):
            os.makedirs(self.index_path)
            
        self._model = None
        self.dimension = 384 # Dimension for all-MiniLM-L6-v2
        self.index = faiss.IndexFlatL2(self.dimension)
        self.metadata_store = []

    @property
    def model(self):
        """Lazy load the embedding model to save memory."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._add_thought(AgentContext(task="Lazy loading ST"), "Loading SentenceTransformer model for embeddings...")
            self._model = SentenceTransformer('all-MiniLM-L6-v2')
        return self._model

    async def observe(self, context: AgentContext) -> AgentContext:
        self._add_thought(context, f"Observing RAG requirement: {context.task}")
        if "query" in context.task.lower() or "search" in context.task.lower():
            context.observations["mode"] = "query"
        else:
            context.observations["mode"] = "index"
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        mode = context.observations.get("mode")
        self._add_thought(context, f"RAG mode: {mode}. Checking index status (total records: {self.index.ntotal}).")
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        mode = context.observations.get("mode")
        if mode == "index":
            context.plan = ["Format text from blob", "Generate embedding", "Add to FAISS index", "Save state"]
        else:
            context.plan = ["Embed search query", "Perform L2 similarity search", "Retrieve top-K metadata"]
        self._add_thought(context, "Semantic search plan finalized.")
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        mode = context.observations.get("mode")
        
        if mode == "index":
            blob_data = context.metadata.get("blob_data")
            if not blob_data: 
                context.errors.append("No blob data provided for indexing")
                return context
            
            symbol = blob_data.get("symbol", "UNKNOWN")
            data_type = blob_data.get("type", "stock")
            
            # Build text content based on data type
            if data_type == "news":
                text_content = f"News about {symbol}: {blob_data.get('name', '')}. {blob_data.get('text', '')}"
            elif data_type == "insight":
                text_content = f"Insight for {symbol}: {blob_data.get('text', '')}"
            elif data_type == "snapshot":
                text_content = (f"Market snapshot for {symbol}. "
                               f"Price: {blob_data.get('price')}. Change: {blob_data.get('change_pct')}%. "
                               f"Sector: {blob_data.get('sector')}.")
            else:
                # Legacy stock blob format
                text_content = (f"Stock: {symbol}. Name: {blob_data.get('name')}. "
                               f"Price: {blob_data.get('price')}. Sector: {blob_data.get('sector')}. "
                               f"Industry: {blob_data.get('industry')}.")
            
            self._add_thought(context, f"Indexing {data_type} for {symbol}")
            embedding = self.model.encode([text_content])[0]
            self.index.add(np.array([embedding]).astype('float32'))
            
            # Enhanced metadata with timestamps and type
            metadata_entry = {
                **blob_data,
                "indexed_at": datetime.now().isoformat(),
                "data_type": data_type,
                "text_indexed": text_content[:200],  # Store preview
            }
            self.metadata_store.append(metadata_entry)
            context.result = {"status": "indexed", "symbol": symbol, "type": data_type}
            
        elif mode == "query":
            query_text = context.task
            k = context.metadata.get("k", 5)
            ticker_filter = context.metadata.get("ticker_filter")
            
            if self.index.ntotal == 0:
                self._add_thought(context, "Index is empty, returning empty results.")
                context.result = []
                return context
                
            self._add_thought(context, f"Querying FAISS for: '{query_text}'")
            embedding = self.model.encode([query_text])[0]
            
            # Search more than k to allow filtering
            search_k = min(k * 3, self.index.ntotal)
            D, I = self.index.search(np.array([embedding]).astype('float32'), search_k)
            
            results = []
            for idx, i in enumerate(I[0]):
                if i != -1 and i < len(self.metadata_store):
                    entry = self.metadata_store[i]
                    # Apply ticker filter if specified
                    if ticker_filter and entry.get("symbol", "").upper() != ticker_filter.upper():
                        continue
                    entry_with_score = {**entry, "relevance_distance": float(D[0][idx])}
                    results.append(entry_with_score)
                    if len(results) >= k:
                        break
            
            context.result = results

        context.actions_taken.append({"action": f"rag_{mode}"})
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        if not context.errors:
            context.reflection = f"RAG operation ({context.observations.get('mode')}) completed successfully."
            context.confidence = 0.9
        return context

    # ─── Enhanced Methods for Knowledge Store Integration ─────────────────────

    async def index_news_article(self, article: dict) -> bool:
        """Index a single news article into FAISS."""
        blob_data = {
            "symbol": article.get("ticker", "GENERAL"),
            "name": article.get("headline", ""),
            "type": "news",
            "source": article.get("source", ""),
            "url": article.get("url", ""),
            "published_at": article.get("published_at", ""),
            "text": f"{article.get('headline', '')}. {article.get('summary', '')}"
        }
        ctx = AgentContext(task="Index blob", metadata={"blob_data": blob_data})
        result = await self.run(ctx)
        return not bool(result.errors)

    async def index_daily_snapshot(self, ticker: str, snapshot: dict) -> bool:
        """Index a market snapshot into FAISS."""
        blob_data = {
            "symbol": ticker,
            "type": "snapshot",
            "price": snapshot.get("px") or snapshot.get("price"),
            "change_pct": snapshot.get("chg") or snapshot.get("change_pct"),
            "sector": snapshot.get("sector"),
            "text": json.dumps(snapshot)[:500]
        }
        ctx = AgentContext(task="Index blob", metadata={"blob_data": blob_data})
        result = await self.run(ctx)
        return not bool(result.errors)

    async def index_market_event(self, ticker: str, event_text: str,
                                  source_url: str = None) -> bool:
        """Index a significant market event into FAISS."""
        blob_data = {
            "symbol": ticker,
            "name": event_text[:100],
            "type": "insight",
            "source": "market_event",
            "url": source_url or "",
            "text": event_text
        }
        ctx = AgentContext(task="Index blob", metadata={"blob_data": blob_data})
        result = await self.run(ctx)
        return not bool(result.errors)

    async def search_for_ticker(self, query: str, ticker: str, k: int = 5) -> list[dict]:
        """Search RAG with ticker filtering."""
        ctx = AgentContext(task=query, metadata={"k": k, "ticker_filter": ticker})
        ctx.observations["mode"] = "query"
        result = await self.act(ctx)
        return result.result if isinstance(result.result, list) else []

    # Legacy compatibility methods
    def index_stock_blob(self, blob_data: dict):
        loop = asyncio.get_event_loop()
        ctx = AgentContext(task="Index blob", metadata={"blob_data": blob_data})
        loop.run_until_complete(self.run(ctx))
        return True

    def query(self, text: str, k: int = 5):
        loop = asyncio.get_event_loop()
        ctx = AgentContext(task=text, metadata={"k": k})
        res = loop.run_until_complete(self.run(ctx))
        return res.result if isinstance(res.result, list) else []

    def save_index(self):
        faiss.write_index(self.index, os.path.join(self.index_path, "market.index"))
        with open(os.path.join(self.index_path, "metadata.json"), "w") as f:
            json.dump(self.metadata_store, f, default=str)

    def load_index(self):
        idx_file = os.path.join(self.index_path, "market.index")
        meta_file = os.path.join(self.index_path, "metadata.json")
        if os.path.exists(idx_file) and os.path.exists(meta_file):
            self.index = faiss.read_index(idx_file)
            with open(meta_file, "r") as f:
                self.metadata_store = json.load(f)

if __name__ == "__main__":
    async def test():
        agent = RagAgent()
        # Index news
        await agent.index_news_article({
            "ticker": "NVDA", "headline": "NVIDIA beats Q4 earnings",
            "summary": "Revenue up 265% year-over-year", "source": "Reuters",
            "url": "https://example.com/nvda"
        })
        # Query
        res = await agent.run(AgentContext(task="Query: GPU earnings"))
        print(f"Results: {res.result}")
    
    asyncio.run(test())
