import os
import faiss
import numpy as np
import json
from sentence_transformers import SentenceTransformer
from datetime import datetime

class RagAgent:
    """Agent 3: Market RAG Agent - Semantic Search Market Intelligence."""
    
    def __init__(self, index_path="gateway/market_rag_index"):
        self.name = "MarketRagAgent"
        self.index_path = index_path
        if not os.path.exists(self.index_path):
            os.makedirs(self.index_path)
            
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.dimension = 384 # Dimension for all-MiniLM-L6-v2
        self.index = faiss.IndexFlatL2(self.dimension)
        self.metadata = []

    def index_stock_blob(self, blob_data: dict):
        """Indexes a single stock blob."""
        symbol = blob_data.get("symbol")
        text_content = f"Stock: {symbol}. Name: {blob_data.get('name')}. Price: {blob_data.get('price')}. Sector: {blob_data.get('sector')}. Industry: {blob_data.get('industry')}."
        
        embedding = self.model.encode([text_content])[0]
        self.index.add(np.array([embedding]).astype('float32'))
        self.metadata.append(blob_data)
        
        # Save index
        # faiss.write_index(self.index, os.path.join(self.index_path, "market.index"))
        return True

    def query(self, text: str, k: int = 5):
        """Query the RAG index."""
        if self.index.ntotal == 0:
            return []
            
        embedding = self.model.encode([text])[0]
        D, I = self.index.search(np.array([embedding]).astype('float32'), k)
        
        results = []
        for i in I[0]:
            if i != -1 and i < len(self.metadata):
                results.append(self.metadata[i])
        return results

    def save_index(self):
        faiss.write_index(self.index, os.path.join(self.index_path, "market.index"))
        with open(os.path.join(self.index_path, "metadata.json"), "w") as f:
            json.dump(self.metadata, f)

    def load_index(self):
        idx_file = os.path.join(self.index_path, "market.index")
        meta_file = os.path.join(self.index_path, "metadata.json")
        if os.path.exists(idx_file) and os.path.exists(meta_file):
            self.index = faiss.read_index(idx_file)
            with open(meta_file, "r") as f:
                self.metadata = json.load(f)

if __name__ == "__main__":
    agent = RagAgent()
    agent.index_stock_blob({"symbol": "AAPL", "name": "Apple Inc.", "price": 190.22, "sector": "Technology"})
    print(f"Results: {len(agent.query('iPhone company'))}")
