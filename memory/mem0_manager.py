"""
Mem0 self-hosted memory manager.
Uses Qdrant vector DB + local LLM — zero cloud, zero cost.
"""
from mem0 import Memory
import os
import asyncio
from core.logger import get_logger

logger = get_logger(__name__)

class Mem0Manager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Mem0Manager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, 'initialized'):
            return
            
        # Full self-hosted config — no API key needed
        config = {
            "llm": {
                "provider": "ollama", # Using Ollama provider logic but pointing to our local GGUF/Ollama endpoint
                "config": {
                    "model": os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
                    "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                    "temperature": 0.1,
                    "max_tokens": 2000,
                }
            },
            "embedder": {
                "provider": "ollama",
                "config": {
                    "model": "nomic-embed-text", # Best free embedding model
                    "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                }
            },
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "host": os.getenv("QDRANT_HOST", "localhost"),
                    "port": 6333,
                    "collection_name": "aitradra_memories",
                    "embedding_model_dims": 768, # nomic-embed-text dims
                }
            },
            "history_db_path": os.path.join(os.path.dirname(os.path.abspath(__file__)), "mem0_history.db")
        }
        
        try:
            self.memory = Memory.from_config(config)
            self.initialized = True
            logger.info("Mem0 Manager initialized with Qdrant vector store.")
        except Exception as e:
            logger.error(f"Failed to initialize Mem0: {e}")
            self.memory = None

    async def store_analysis(self, ticker: str, analysis: dict, user_id: str = "axiom_agent"):
        """Store a completed analysis"""
        if not self.memory: return
        
        content = (
            f"Stock: {ticker} | Date: {analysis.get('timestamp', 'now')} | "
            f"Signal: {analysis.get('signal', 'N/A')} | "
            f"Confidence: {analysis.get('confidence', 0):.2f} | "
            f"Technical: {analysis.get('technical_summary', '')} | "
            f"Risk: {analysis.get('risk_summary', '')} | "
            f"Macro: {analysis.get('macro_summary', '')} | "
            f"Synthesis: {analysis.get('final_synthesis', '')[:500]}"
        )
        
        await asyncio.to_thread(
            self.memory.add, 
            content, 
            user_id=user_id, 
            metadata={
                "ticker": ticker,
                "type": "analysis",
                "signal": analysis.get("signal")
            }
        )

    async def recall_context(self, query: str, user_id: str = "axiom_agent", limit: int = 5) -> str:
        """Semantic search over past analyses — returns as context string"""
        if not self.memory: return "No memory system available."
        
        results = await asyncio.to_thread(self.memory.search, query=query, user_id=user_id, limit=limit)
        
        if not results or not results.get("results"):
            return "No prior context found."
            
        memories = [r["memory"] for r in results["results"]]
        return "\n---\n".join(memories)

    async def store_prediction_outcome(self, ticker: str, predicted: str, actual: str):
        """Track accuracy for AutoResearch loop"""
        if not self.memory: return
        
        correct = str(predicted).upper() == str(actual).upper()
        await asyncio.to_thread(
            self.memory.add,
            f"Prediction: {ticker} | Predicted: {predicted} | Actual: {actual} | Correct: {correct}",
            user_id="prediction_tracker",
            metadata={"ticker": ticker, "correct": correct, "type": "prediction"}
        )

    async def get_accuracy_stats(self) -> dict:
        """Pull prediction history for AutoResearch eval"""
        if not self.memory: return {"accuracy": 0, "total": 0}
        
        results = await asyncio.to_thread(
            self.memory.search, 
            "prediction correct wrong", 
            user_id="prediction_tracker", 
            limit=50
        )
        
        memories = results.get("results", [])
        correct = sum(1 for m in memories if "Correct: True" in m.get("memory", ""))
        total = len(memories)
        
        return {
            "accuracy": correct / total if total > 0 else 0,
            "total_predictions": total,
            "correct_count": correct
        }

    async def get_system_status(self) -> dict:
        if not self.memory: return {"status": "offline"}
        return {
            "status": "online",
            "provider": "mem0/qdrant",
            "initialized": self.initialized
        }
