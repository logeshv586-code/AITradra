"""Self-Improvement Engine — Evaluates past predictions to optimize agent parameters."""

import asyncio
from typing import Dict, Any
from core.logger import get_logger
from self_improvement.scorer import PredictionScorer
from self_improvement.performance_tracker import PerformanceTracker

logger = get_logger(__name__)


class SelfImprovementEngine:
    """The central nervous system for continuous learning and agent optimization."""

    def __init__(self, memory_manager):
        self.memory = memory_manager
        self.scorer = PredictionScorer()
        self.tracker = PerformanceTracker()
        self._optimization_loop_task = None

    async def start(self):
        """Start the background optimization loop."""
        logger.info("Starting Self-Improvement Engine")
        self._optimization_loop_task = asyncio.create_task(self._optimization_loop())

    async def _optimization_loop(self):
        """Continuously evaluate pending predictions as market data arrives."""
        while True:
            try:
                # In production, this would query pending predictions from DB,
                # fetch current actual prices, and score them.
                await self._evaluate_pending_predictions()
                await asyncio.sleep(3600)  # Run hourly
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Self-improvement loop error: {e}")
                await asyncio.sleep(60)

    async def _evaluate_pending_predictions(self):
        """Check all past predictions whose resolution time has arrived."""
        # Stub implementation. The architecture relies on the Scorer.
        pass

    async def process_agent_run(self, agent_name: str, context: Any) -> None:
        """Called automatically at the end of every agent's Claude Flow loop."""
        # Extract metadata, latency, error rates, and confidence
        metrics = {
            "latency_ms": (context.start_time.timestamp() - context.start_time.timestamp()) * 1000, # Mocked latency
            "error_count": len(context.errors),
            "confidence": context.confidence,
            "success": len(context.errors) == 0
        }
        await self.tracker.record_run(agent_name, metrics)
        
        # If the agent failed or had low confidence recursively, trigger prompt/parameter optimization
        if metrics["error_count"] > 0 or context.confidence < 0.4:
            await self._trigger_optimization(agent_name, context)

    async def _trigger_optimization(self, agent_name: str, context: Any) -> None:
        """Adjusts agent parameters when performance drops."""
        logger.warning(f"Optimization triggered for {agent_name} due to poor performance/confidence.")
        # E.g., instructing the LLM to rewrite its own prompt based on failure history
        # or tuning TA parameters (RSI length 14 -> 10 in higher volatility).
