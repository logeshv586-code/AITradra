"""Performance Tracker — Records running metrics for all agents."""

from typing import Dict, Any
from core.logger import get_logger

logger = get_logger(__name__)


class PerformanceTracker:
    """Tracks latency, error rates, and confidence across the agent mesh."""

    def __init__(self):
        # In-memory store for Phase 1. Will move to SQLite/Redis.
        self._metrics: Dict[str, Dict[str, float]] = {}

    async def record_run(self, agent_name: str, metrics: Dict[str, Any]) -> None:
        """Records a single run's telemetry."""
        if agent_name not in self._metrics:
            self._metrics[agent_name] = {
                "runs": 0,
                "errors": 0,
                "avg_latency": 0.0,
                "avg_confidence": 0.0
            }

        stats = self._metrics[agent_name]
        runs = stats["runs"]
        
        # Incremental moving averages
        stats["avg_latency"] = ((stats["avg_latency"] * runs) + metrics.get("latency_ms", 0)) / (runs + 1)
        stats["avg_confidence"] = ((stats["avg_confidence"] * runs) + metrics.get("confidence", 0)) / (runs + 1)
        
        stats["runs"] += 1
        if not metrics.get("success", True):
            stats["errors"] += 1

    async def get_agent_health(self, agent_name: str) -> Dict[str, Any]:
        """Returns health profile for an agent."""
        return self._metrics.get(agent_name, {})

    async def get_system_health(self) -> Dict[str, Dict[str, Any]]:
        """Returns health profile for the whole system."""
        return self._metrics
