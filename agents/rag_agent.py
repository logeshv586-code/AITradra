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
            
            symbol = blob_data.get("symbol")
            text_content = f"Stock: {symbol}. Name: {blob_data.get('name')}. Price: {blob_data.get('price')}. Sector: {blob_data.get('sector')}. Industry: {blob_data.get('industry')}."
            
            self._add_thought(context, f"Indexing metadata for {symbol}")
            embedding = self.model.encode([text_content])[0]
            self.index.add(np.array([embedding]).astype('float32'))
            self.metadata_store.append(blob_data)
            context.result = {"status": "indexed", "symbol": symbol}
            
        elif mode == "query":
            query_text = context.task
            k = context.metadata.get("k", 5)
            
            if self.index.ntotal == 0:
                self._add_thought(context, "Index is empty, returning empty results.")
                context.result = []
                return context
                
            self._add_thought(context, f"Querying FAISS for: '{query_text}'")
            embedding = self.model.encode([query_text])[0]
            D, I = self.index.search(np.array([embedding]).astype('float32'), k)
            
            results = []
            for i in I[0]:
                if i != -1 and i < len(self.metadata_store):
                    results.append(self.metadata_store[i])
            context.result = results

        context.actions_taken.append({"action": f"rag_{mode}"})
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        if not context.errors:
            context.reflection = f"RAG operation ({context.observations.get('mode')}) completed successfully."
            context.confidence = 0.9
        return context

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
            json.dump(self.metadata_store, f)

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
        # Index
        await agent.run(AgentContext(task="Index", metadata={"blob_data": {"symbol": "NVDA", "name": "NVIDIA"}}))
        # Query
        res = await agent.run(AgentContext(task="GPU manufacturer"))
        print(f"Results: {res.result}")
    
    asyncio.run(test())
