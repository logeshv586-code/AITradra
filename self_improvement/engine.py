"""
Self-Improvement Engine — Full Prediction Loop + Agent Optimization.

Every agent run -> telemetry
Every directional signal -> prediction history
Mature predictions -> research/history scoring
Only fresh, provenance-complete, horizon-valid outcomes -> live precision evidence
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

from core.config import settings
from core.logger import get_logger
from self_improvement.scorer import PredictionScorer
from self_improvement.performance_tracker import PerformanceTracker
from self_improvement.accuracy_store import accuracy_store
from self_improvement.precision_store import precision_store

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
            "live_gate_eligible": 0,
            "live_gate_rejected": 0,
            "updated_at": None,
        }
        self._agent_weight_adjustments: Dict[str, float] = {}

    async def start(self):
        if self._optimization_loop_task and not self._optimization_loop_task.done():
            return
        logger.info("Starting Self-Improvement Engine")
        self._optimization_loop_task = asyncio.create_task(self._optimization_loop())

    async def _optimization_loop(self):
        while True:
            try:
                await self._evaluate_pending_predictions()
                await self._compute_agent_weights()
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Self-improvement loop error: {e}")
                await asyncio.sleep(60)

    async def _evaluate_pending_predictions(self):
        """Score matured predictions, but promote only audited evidence to the live gate."""
        prediction_store = getattr(self.memory, "structured", None)
        predictions = list(getattr(prediction_store, "_predictions", []) or [])

        try:
            from gateway.knowledge_store import knowledge_store

            db_predictions = knowledge_store.get_recent_insights(
                insight_type="prediction", hours=72
            )
            if db_predictions:
                for p in db_predictions:
                    predictions.append(
                        {
                            "id": p.get(
                                "id",
                                f"ks_{p.get('ticker', '')}_{p.get('timestamp', '')}",
                            ),
                            "ticker": p.get("ticker", ""),
                            "prediction": {
                                "prediction_direction": self._extract_direction(
                                    p.get("content", "")
                                ),
                                "price_at_prediction": self._extract_price(
                                    p.get("content", "")
                                ),
                            },
                            "created_at": p.get("timestamp"),
                            "source_agent": p.get("agent_name", "unknown"),
                        }
                    )
        except Exception as e:
            logger.debug(f"Could not fetch DB predictions: {e}")

        if not predictions:
            self.last_prediction_scoring = {
                "evaluated": 0,
                "skipped": 0,
                "failed": 0,
                "average_accuracy": None,
                "live_gate_eligible": 0,
                "live_gate_rejected": 0,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            return self.last_prediction_scoring

        from gateway.data_engine import data_engine

        evaluated = 0
        skipped = 0
        failed = 0
        live_gate_eligible = 0
        live_gate_rejected = 0
        scores: list[float] = []
        agent_scores: Dict[str, list] = {}
        now = datetime.now(timezone.utc)
        horizon_hours = max(float(settings.PREDICTION_SCORE_DELAY_HOURS), 0.0)
        min_age_seconds = horizon_hours * 3600

        for prediction in predictions:
            pred_id = prediction.get("id")
            ticker = str(prediction.get("ticker", "")).upper()
            source_agent = str(prediction.get("source_agent", "unknown") or "unknown")
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
                    allow_scrape=True,
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

                evidence = self._live_gate_evidence(
                    price_payload=price_payload,
                    prediction_created_at=created_at,
                    evaluated_at=now,
                    horizon_hours=horizon_hours,
                    source_agent=source_agent,
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
                        "live_gate_evidence": evidence,
                    },
                )

                accuracy_store.record_outcome(
                    ticker=ticker,
                    model=source_agent,
                    provider=price_payload.get("source_used", "default"),
                    direction=direction,
                    accuracy=accuracy,
                )

                if direction in {"BULLISH", "BEARISH"}:
                    if evidence["eligible"] and created_at is not None:
                        inserted = precision_store.record_outcome(
                            prediction_id=str(pred_id),
                            ticker=ticker,
                            model=source_agent,
                            provider=str(
                                price_payload.get("source_used", "unknown")
                            ),
                            upstream_provider=evidence["upstream_provider"],
                            direction=direction,
                            correct=accuracy > 0.0,
                            continuous_accuracy=accuracy,
                            prediction_timestamp=created_at.isoformat(),
                            horizon_hours=horizon_hours,
                            evaluated_at=now.isoformat(),
                            observed_at=evidence["observed_at"],
                            live_gate_eligible=True,
                            scored_at=now.isoformat(),
                        )
                        if inserted:
                            live_gate_eligible += 1
                    else:
                        live_gate_rejected += 1

                try:
                    from memory.reflection_memory import get_memory as _get_reflection

                    await _get_reflection().reflect_on_outcome(
                        ticker=ticker,
                        source_agent=source_agent,
                        direction=direction,
                        accuracy=accuracy,
                        price_at_prediction=price_at_prediction,
                        actual_price=actual_price,
                        context=str(self._prediction_payload(prediction))[:500],
                    )
                except Exception as exc:
                    logger.debug(f"Reflection lesson skipped for {ticker}: {exc}")

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
            "live_gate_eligible": live_gate_eligible,
            "live_gate_rejected": live_gate_rejected,
            "agent_accuracies": {
                agent: round(sum(s) / len(s), 4)
                for agent, s in agent_scores.items()
                if s
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
                "Predictions scored: %s evaluated, %s skipped, %s failed, "
                "%s live-gate eligible, %s rejected, avg_accuracy=%s",
                evaluated,
                skipped,
                failed,
                live_gate_eligible,
                live_gate_rejected,
                average_accuracy,
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
                    continue

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
                logger.info(
                    f"Agent weight adjustments: {self._agent_weight_adjustments}"
                )
        except Exception as e:
            logger.debug(f"Weight computation skipped: {e}")

    def get_agent_weight(self, agent_name: str) -> float:
        return self._agent_weight_adjustments.get(agent_name, 1.0)

    def _latest_observed_at(self, price_payload: dict) -> Optional[datetime]:
        explicit = self._parse_timestamp(price_payload.get("observed_at"))
        if explicit is not None:
            return explicit

        candidates: list[datetime] = []
        for row in price_payload.get("ohlcv", []) or []:
            if not isinstance(row, dict):
                continue
            parsed = self._parse_timestamp(
                row.get("t") or row.get("timestamp") or row.get("date")
            )
            if parsed is not None:
                candidates.append(parsed)
        return max(candidates) if candidates else None

    def _live_gate_evidence(
        self,
        *,
        price_payload: dict,
        prediction_created_at: Optional[datetime],
        evaluated_at: datetime,
        horizon_hours: float,
        source_agent: str,
    ) -> dict[str, Any]:
        """Validate whether one scored observation may count toward live precision."""
        def rejected(
            reason: str,
            observed: Optional[datetime] = None,
            provider: str = "",
        ):
            return {
                "eligible": False,
                "reason": reason,
                "observed_at": observed.isoformat() if observed else None,
                "upstream_provider": provider,
            }

        if prediction_created_at is None:
            return rejected("prediction timestamp missing")
        if not source_agent or source_agent.lower() == "unknown":
            return rejected("prediction source agent is unknown")
        if price_payload.get("is_stale") is not False:
            return rejected("market observation is stale or freshness is unverified")
        if price_payload.get("syncing") is not False:
            return rejected("market observation is still syncing")
        if price_payload.get("is_estimated") is not False:
            return rejected("market observation is estimated or provenance is unverified")

        source = str(price_payload.get("source_used", "") or "").strip()
        source_lower = source.lower()
        blocked = {
            "",
            "none",
            "unknown",
            "default",
            "fallback",
            "cache_stale",
            "stale_cache",
            "knowledge_store",
        }
        upstream = source

        if source_lower == "cache":
            upstream = str(
                price_payload.get("upstream_provider")
                or price_payload.get("origin_source")
                or price_payload.get("provider")
                or ""
            ).strip()
            if upstream.lower() in blocked | {"cache"}:
                return rejected("cache observation does not preserve upstream provider")
        elif source_lower == "connected_api":
            upstream = str(
                price_payload.get("upstream_provider")
                or price_payload.get("provider")
                or price_payload.get("connection_id")
                or ""
            ).strip()
            if not upstream:
                return rejected("connected API observation lacks provider traceability")
        elif source_lower in blocked:
            return rejected(
                f"market provider '{source or 'none'}' is not live-gate eligible"
            )

        observed_at = self._latest_observed_at(price_payload)
        if observed_at is None:
            return rejected(
                "market observation timestamp missing",
                provider=upstream,
            )

        horizon_end = prediction_created_at + timedelta(hours=horizon_hours)
        if observed_at < horizon_end:
            return rejected(
                "market observation occurred before the prediction horizon",
                observed_at,
                upstream,
            )
        if observed_at > evaluated_at + timedelta(minutes=5):
            return rejected(
                "market observation timestamp is unexpectedly in the future",
                observed_at,
                upstream,
            )

        max_age_minutes = max(
            float(
                getattr(
                    settings,
                    "PRECISION_EVIDENCE_MAX_PRICE_AGE_MINUTES",
                    30,
                )
            ),
            1.0,
        )
        age_minutes = (evaluated_at - observed_at).total_seconds() / 60.0
        if age_minutes > max_age_minutes:
            return rejected(
                f"market observation is too old ({age_minutes:.1f}m > "
                f"{max_age_minutes:.1f}m)",
                observed_at,
                upstream,
            )

        declared_freshness = price_payload.get("freshness_minutes")
        if declared_freshness is not None:
            try:
                if float(declared_freshness) > max_age_minutes:
                    return rejected(
                        "provider freshness metadata exceeds live-gate limit",
                        observed_at,
                        upstream,
                    )
            except (TypeError, ValueError):
                return rejected(
                    "provider freshness metadata is invalid",
                    observed_at,
                    upstream,
                )

        return {
            "eligible": True,
            "reason": None,
            "observed_at": observed_at.isoformat(),
            "upstream_provider": upstream,
        }

    def _extract_direction(self, content: str) -> str:
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
        import re

        match = re.search(r"@\s*([\d.]+)", content)
        if match:
            return self._safe_float(match.group(1))
        return 0.0

    def _parse_timestamp(self, value: Any) -> Optional[datetime]:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
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
        elapsed_ms = 0.0
        try:
            start_time = context.start_time
            now = datetime.now(timezone.utc)
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)
            elapsed_ms = (now - start_time).total_seconds() * 1000
        except Exception:
            elapsed_ms = 0.0

        metrics = {
            "latency_ms": elapsed_ms,
            "error_count": len(context.errors),
            "confidence": context.confidence,
            "success": len(context.errors) == 0,
        }
        await self.tracker.record_run(agent_name, metrics)

        result = context.result
        if isinstance(result, dict) and context.ticker:
            signal = result.get("signal", result.get("verdict", ""))
            if signal in (
                "BULLISH",
                "BEARISH",
                "BUY",
                "SELL",
                "STRONG BUY",
                "STRONG SELL",
            ):
                try:
                    from gateway.knowledge_store import knowledge_store

                    entry_price = (
                        result.get("entry_point", 0)
                        or result.get("breakout_data", {}).get("current_close", 0)
                        or result.get("indicators", {}).get("sma20", 0)
                    )
                    knowledge_store.store_insight(
                        ticker=context.ticker,
                        agent_name=agent_name,
                        insight_type="prediction",
                        content=f"{signal} @ {entry_price} | conf={context.confidence:.2f}",
                        confidence=context.confidence,
                    )
                    logger.debug(
                        f"Stored prediction: {agent_name} -> {signal} for {context.ticker}"
                    )
                except Exception as e:
                    logger.debug(f"Could not store prediction for {agent_name}: {e}")

        if metrics["error_count"] > 0 or context.confidence < 0.4:
            await self._trigger_optimization(agent_name, context)

    async def _trigger_optimization(self, agent_name: str, context: Any) -> None:
        logger.warning(
            f"Optimization triggered for {agent_name} due to poor performance/confidence."
        )
        try:
            from gateway.knowledge_store import knowledge_store

            knowledge_store.store_insight(
                ticker=context.ticker or "SYSTEM",
                agent_name="SelfImprovementEngine",
                insight_type="optimization_trigger",
                content=(
                    f"{agent_name}: errors={len(context.errors)}, "
                    f"conf={context.confidence:.2f}"
                ),
                confidence=0.5,
            )
        except Exception:
            pass

    async def get_status(self) -> Dict[str, Any]:
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
                "live_gate_evidence_validation",
                "low_confidence_optimization",
                "dynamic_agent_weighting",
                "all_agent_prediction_storage",
            ],
        }
