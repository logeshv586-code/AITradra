"""MemoryManager — Central memory orchestrator for all agents (episodic, semantic, structured, working)."""

from datetime import datetime, timezone
from typing import Any, Optional
from core.logger import get_logger

logger = get_logger(__name__)


class EpisodicStore:
    """SQLite-backed episodic memory for agent run history."""
    def __init__(self):
        self._episodes = []

    async def save(self, episode: dict) -> None:
        self._episodes.append(episode)
        if len(self._episodes) > 1000:
            self._episodes = self._episodes[-500:]

    async def search(self, query: str, limit: int = 5) -> list:
        # Simple keyword matching fallback
        results = []
        for ep in reversed(self._episodes):
            if query.lower() in str(ep).lower():
                results.append(ep)
            if len(results) >= limit:
                break
        return results


class WorkingMemory:
    """In-memory context window for current session."""
    def __init__(self, max_items: int = 100):
        self._store: dict[str, Any] = {}
        self._max = max_items

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value
        if len(self._store) > self._max:
            oldest = next(iter(self._store))
            del self._store[oldest]

    def get(self, key: str) -> Any:
        return self._store.get(key)

    def clear(self) -> None:
        self._store.clear()


class PredictionStore:
    """In-memory prediction storage for scoring."""
    def __init__(self):
        self._predictions = []

    async def save_prediction(self, pred: dict) -> str:
        import uuid
        pred_id = str(uuid.uuid4())
        pred["id"] = pred_id
        self._predictions.append(pred)
        return pred_id

    async def get_predictions_for_ticker(self, ticker: str, limit: int = 10) -> list:
        return [p for p in reversed(self._predictions) if p.get("ticker") == ticker][:limit]

    async def update_outcome(self, pred_id: str, actual_price: float, accuracy_score: float) -> None:
        for p in self._predictions:
            if p.get("id") == pred_id:
                p["actual_price"] = actual_price
                p["accuracy_score"] = accuracy_score
                break


class MemoryManager:
    """Unified memory interface for all agents."""

    def __init__(self):
        self.episodic = EpisodicStore()
        self.working = WorkingMemory()
        self.structured = PredictionStore()

    async def initialize(self) -> None:
        logger.info("Memory system initialized")

    async def store_episode(self, agent: str, task: str, result: str,
                           reflection: str, confidence: float, errors: list) -> None:
        await self.episodic.save({
            "agent": agent, "task": task, "result": result,
            "reflection": reflection, "confidence": confidence,
            "errors": errors, "timestamp": datetime.now(timezone.utc).isoformat()
        })

    async def store_prediction(self, ticker: str, prediction: dict,
                              reasoning: str, confidence: float) -> str:
        return await self.structured.save_prediction({
            "ticker": ticker, "prediction": prediction,
            "reasoning": reasoning, "confidence": confidence,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    async def recall_relevant(self, query: str, limit: int = 5) -> list:
        return await self.episodic.search(query, limit)

    async def semantic_search(self, query: str, n_results: int = 5) -> list:
        return await self.episodic.search(query, n_results)

    async def get_past_predictions(self, ticker: str, limit: int = 10) -> list:
        return await self.structured.get_predictions_for_ticker(ticker, limit)

    async def update_prediction_outcome(self, prediction_id: str,
                                        actual_price: float, accuracy_score: float) -> None:
        await self.structured.update_outcome(prediction_id, actual_price, accuracy_score)

    def set_working_context(self, key: str, value: Any) -> None:
        self.working.set(key, value)

    def get_working_context(self, key: str) -> Any:
        return self.working.get(key)
