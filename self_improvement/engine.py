"""
Self-Improvement Engine — Full Prediction Loop + Agent Optimization.

From self-improvement.md:
  Every agent run -> process_agent_run() -> record telemetry
  Every directional signal -> store_prediction() -> score after 24h
  Low performers -> _trigger_optimization() -> adjust parameters
  Hourly loop -> _evaluate_pending_predictions() -> AccuracyStore
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from core.config import settings
from core.logger import get_logger
from self_improvement.scorer import PredictionScorer
from self_improvement.performance_tracker import PerformanceTracker
from self_improvement.accuracy_store import accuracy_store

logger = get_logger(__name__)


class SelfImprovementEngine:
    """The central nervous system for continuous learning and agent optimization."""

    def __init__(self, memory_manager):
        self.memory = memory_manager
        self.scorer = PredictionScorer()
        self.tracker = PerformanceTracker()
        self._optimization_loop_task = None
        self.last_prediction_scoring: Dict[str, Any] = {
            "evaluated": 0,
            "skipped": 0,
            "failed": 0,
            "average_accuracy": None,
            "updated_at": None,
        }
        # Agent weight adjustments based on historical accuracy
        self._agent_weight_adjustments: Dict[str, float] = {}

    async def start(self):
        """Start the background optimization loop."""
        if self._optimization_loop_task and not self._optimization_loop_task.done():
            return
        logger.info("Starting Self-Improvement Engine")
        self._optimization_loop_task = asyncio.create_task(self._optimization_loop())

    async def _optimization_loop(self):
        """Continuously evaluate pending predictions as market data arrives."""
        while True:
            try:
                await self._evaluate_pending_predictions()
                await self._compute_agent_weights()
                await asyncio.sleep(3600)  # Run hourly
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Self-improvement loop error: {e}")
                await asyncio.sleep(60)

    async def _evaluate_pending_predictions(self):
        """Check all past predictions whose resolution time has arrived."""
        prediction_store = getattr(self.memory, "structured", None)
        predictions = list(getattr(prediction_store, "_predictions", []) or [])

        # Also pull predictions from knowledge store (SignalAggregator, specialists)
        try:
            from gateway.knowledge_store import knowledge_store
            db_predictions = knowledge_store.get_recent_insights(
                insight_type="prediction", hours=72
            )
            if db_predictions:
                for p in db_predictions:
                    predictions.append({
                        "id": p.get("id", f"ks_{p.get('ticker', '')}_{p.get('timestamp', '')}"),
                        "ticker": p.get("ticker", ""),
                        "prediction": {
                            "prediction_direction": self._extract_direction(p.get("content", "")),
                            "price_at_prediction": self._extract_price(p.get("content", "")),
                        },
                        "created_at": p.get("timestamp"),
                        "source_agent": p.get("agent_name", "unknown"),
                    })
        except Exception as e:
            logger.debug(f"Could not fetch DB predictions: {e}")

        if not predictions:
            self.last_prediction_scoring = {
                "evaluated": 0,
                "skipped": 0,
                "failed": 0,
                "average_accuracy": None,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            return self.last_prediction_scoring

        from gateway.data_engine import data_engine

        evaluated = 0
        skipped = 0
        failed = 0
        scores: list[float] = []
        agent_scores: Dict[str, list] = {}
        now = datetime.now(timezone.utc)
        min_age_seconds = max(settings.PREDICTION_SCORE_DELAY_HOURS, 0) * 3600

        for prediction in predictions:
            pred_id = prediction.get("id")
            ticker = str(prediction.get("ticker", "")).upper()
            source_agent = prediction.get("source_agent", "unknown")
            if not pred_id or not ticker or prediction.get("resolved_at"):
                skipped += 1
                continue

            created_at = self._parse_timestamp(
                prediction.get("created_at") or prediction.get("timestamp")
            )
            if created_at and (now - created_at).total_seconds() < min_age_seconds:
                skipped += 1
                continue

            try:
                price_at_prediction = self._prediction_price(prediction)
                if price_at_prediction <= 0:
                    skipped += 1
                    continue

                price_payload = await data_engine.get_price_data(
                    ticker,
                    allow_scrape=False,
                )
                actual_price = self._safe_float(
                    price_payload.get("px") or price_payload.get("close")
                )
                if actual_price <= 0:
                    skipped += 1
                    continue

                raw_direction = self._prediction_direction(prediction)
                direction = self.scorer.normalize_direction(raw_direction)
                target_price = self._target_price(
                    prediction,
                    price_at_prediction,
                    direction,
                )
                accuracy = round(
                    self.scorer.calculate_accuracy(
                        prediction_price=price_at_prediction,
                        target_price=target_price,
                        actual_price=actual_price,
                        direction=direction,
                    ),
                    4,
                )

                await self.memory.update_prediction_outcome(
                    pred_id,
                    actual_price,
                    accuracy,
                    outcome={
                        "direction": direction,
                        "raw_direction": raw_direction,
                        "price_at_prediction": price_at_prediction,
                        "target_price": round(target_price, 4),
                        "actual_price": actual_price,
                        "price_source": price_payload.get("source_used", "unknown"),
                        "source_agent": source_agent,
                        "scored_at": now.isoformat(),
                    },
                )
                # Persist aggregate accuracy for long-term model comparison
                accuracy_store.record_outcome(
                    ticker=ticker,
                    model=source_agent,
                    provider=price_payload.get("source_used", "default"),
                    direction=direction,
                    accuracy=accuracy,
                )

                # Track per-agent accuracy
                if source_agent not in agent_scores:
                    agent_scores[source_agent] = []
                agent_scores[source_agent].append(accuracy)

                scores.append(accuracy)
                evaluated += 1
            except Exception as exc:
                failed += 1
                logger.warning(
                    "Prediction outcome scoring failed for %s: %s",
                    ticker,
                    exc,
                )

        average_accuracy = round(sum(scores) / len(scores), 4) if scores else None
        self.last_prediction_scoring = {
            "evaluated": evaluated,
            "skipped": skipped,
            "failed": failed,
            "average_accuracy": average_accuracy,
            "agent_accuracies": {
                agent: round(sum(s) / len(s), 4) for agent, s in agent_scores.items() if s
            },
            "updated_at": now.isoformat(),
        }

        if evaluated:
            await self.tracker.record_run(
                "PredictionOutcomeScorer",
                {
                    "latency_ms": 0,
                    "error_count": failed,
                    "confidence": average_accuracy or 0.0,
                    "success": failed == 0,
                },
            )
            logger.info(
                f"Predictions scored: {evaluated} evaluated, {skipped} skipped, "
                f"{failed} failed, avg_accuracy={average_accuracy}"
            )
        return self.last_prediction_scoring

    async def _compute_agent_weights(self):
        """
        Compute weight adjustments for agents based on historical accuracy.

        Agents with accuracy > 60% get a boost.
        Agents with accuracy < 40% get penalized.
        This feeds back into the SignalAggregator for dynamic weighting.
        """
        try:
            leaderboard = accuracy_store.get_leaderboard(group_by="model", limit=50)
            for entry in leaderboard:
                agent_name = entry.get("model", "")
                avg_acc = entry.get("avg_accuracy", 0.5)
                total = entry.get("total_scored", 0)

                if total < 5:
                    continue  # Not enough data to adjust

                # Weight multiplier: 0.5 (terrible) to 1.5 (excellent)
                if avg_acc > 0.7:
                    self._agent_weight_adjustments[agent_name] = 1.3
                elif avg_acc > 0.6:
                    self._agent_weight_adjustments[agent_name] = 1.1
                elif avg_acc > 0.5:
                    self._agent_weight_adjustments[agent_name] = 1.0
                elif avg_acc > 0.4:
                    self._agent_weight_adjustments[agent_name] = 0.8
                else:
                    self._agent_weight_adjustments[agent_name] = 0.6

            if self._agent_weight_adjustments:
                logger.info(f"Agent weight adjustments: {self._agent_weight_adjustments}")
        except Exception as e:
            logger.debug(f"Weight computation skipped: {e}")

    def get_agent_weight(self, agent_name: str) -> float:
        """Returns the weight adjustment for a specific agent (default 1.0)."""
        return self._agent_weight_adjustments.get(agent_name, 1.0)

    # ─── Helpers ────────────────────────────────────────────────

    def _extract_direction(self, content: str) -> str:
        """Extract direction from prediction content string."""
        content_upper = content.upper()
        if "STRONG BUY" in content_upper or "BULLISH" in content_upper:
            return "BULLISH"
        elif "BUY" in content_upper:
            return "BULLISH"
        elif "STRONG SELL" in content_upper or "BEARISH" in content_upper:
            return "BEARISH"
        elif "SELL" in content_upper:
            return "BEARISH"
        return "NEUTRAL"

    def _extract_price(self, content: str) -> float:
        """Extract price from prediction content string like 'BUY @ 182.50'."""
        import re
        match = re.search(r'@\s*([\d.]+)', content)
        if match:
            return self._safe_float(match.group(1))
        return 0.0

    def _parse_timestamp(self, value: Any) -> Optional[datetime]:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            if value in {None, ""}:
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    def _prediction_payload(self, prediction: dict) -> dict:
        payload = prediction.get("prediction", {})
        return payload if isinstance(payload, dict) else {"final_decision": payload}

    def _prediction_price(self, prediction: dict) -> float:
        payload = self._prediction_payload(prediction)
        return self._safe_float(
            prediction.get("price_at_prediction")
            or payload.get("price_at_prediction")
            or payload.get("current_price")
            or payload.get("prediction_price")
        )

    def _prediction_direction(self, prediction: dict) -> str:
        payload = self._prediction_payload(prediction)
        return (
            payload.get("prediction_direction")
            or payload.get("final_decision")
            or payload.get("consensus")
            or payload.get("recommendation")
            or "NEUTRAL"
        )

    def _target_price(
        self,
        prediction: dict,
        prediction_price: float,
        direction: str,
    ) -> float:
        payload = self._prediction_payload(prediction)
        explicit_target = self._safe_float(
            payload.get("target_price") or payload.get("predicted_price")
        )
        if explicit_target > 0:
            return explicit_target

        expected_move = self._safe_float(
            payload.get("expected_move_percent")
            or prediction.get("expected_move_percent")
        )
        if expected_move <= 0:
            expected_move = 3.0

        if direction == "BULLISH":
            return prediction_price * (1 + expected_move / 100)
        if direction == "BEARISH":
            return prediction_price * (1 - expected_move / 100)
        return prediction_price

    async def process_agent_run(self, agent_name: str, context: Any) -> None:
        """Called automatically at the end of every agent's Claude Flow loop."""
        elapsed_ms = 0.0
        try:
            start_time = context.start_time
            now = datetime.now(timezone.utc)
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)
            elapsed_ms = (now - start_time).total_seconds() * 1000
        except Exception:
            elapsed_ms = 0.0

        # Extract metadata, latency, error rates, and confidence
        metrics = {
            "latency_ms": elapsed_ms,
            "error_count": len(context.errors),
            "confidence": context.confidence,
            "success": len(context.errors) == 0
        }
        await self.tracker.record_run(agent_name, metrics)

        # Store prediction for directional signals from any agent
        result = context.result
        if isinstance(result, dict) and context.ticker:
            signal = result.get("signal", result.get("verdict", ""))
            if signal in ("BULLISH", "BEARISH", "BUY", "SELL", "STRONG BUY", "STRONG SELL"):
                try:
                    from gateway.knowledge_store import knowledge_store
                    entry_price = (
                        result.get("entry_point", 0) or
                        result.get("breakout_data", {}).get("current_close", 0) or
                        result.get("indicators", {}).get("sma20", 0)
                    )
                    knowledge_store.store_insight(
                        ticker=context.ticker,
                        agent_name=agent_name,
                        insight_type="prediction",
                        content=f"{signal} @ {entry_price} | conf={context.confidence:.2f}",
                        confidence=context.confidence,
                    )
                    logger.debug(f"Stored prediction: {agent_name} -> {signal} for {context.ticker}")
                except Exception as e:
                    logger.debug(f"Could not store prediction for {agent_name}: {e}")

        # If the agent failed or had low confidence, trigger optimization
        if metrics["error_count"] > 0 or context.confidence < 0.4:
            await self._trigger_optimization(agent_name, context)

    async def _trigger_optimization(self, agent_name: str, context: Any) -> None:
        """Adjusts agent parameters when performance drops."""
        logger.warning(f"Optimization triggered for {agent_name} due to poor performance/confidence.")

        # Record the failure for long-term tracking
        try:
            from gateway.knowledge_store import knowledge_store
            knowledge_store.store_insight(
                ticker=context.ticker or "SYSTEM",
                agent_name="SelfImprovementEngine",
                insight_type="optimization_trigger",
                content=f"{agent_name}: errors={len(context.errors)}, conf={context.confidence:.2f}",
                confidence=0.5,
            )
        except Exception:
            pass

    async def get_status(self) -> Dict[str, Any]:
        """Return current self-improvement health and telemetry."""
        return {
            "enabled": True,
            "loop_running": bool(
                self._optimization_loop_task
                and not self._optimization_loop_task.done()
            ),
            "agent_health": await self.tracker.get_system_health(),
            "prediction_scoring": self.last_prediction_scoring,
            "agent_weight_adjustments": self._agent_weight_adjustments,
            "feedback_loops": [
                "agent_run_telemetry",
                "prediction_outcome_scoring",
                "low_confidence_optimization",
                "dynamic_agent_weighting",
                "all_agent_prediction_storage",
            ],
        }
