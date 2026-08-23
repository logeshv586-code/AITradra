"""Research Robustness Lab — walk-forward, regime and ablation diagnostics.

This module evaluates the *stability* of Research Council decisions. It is not a
trading engine, not a backtest approval store and not an input to the autonomous
live precision gate.

Design goals inspired by Qlib/vectorbt/Freqtrade/LEAN research practice:
- expanding-window validation instead of one fixed holdout;
- regime-segmented performance rather than one blended average;
- source/category ablation to detect fragile research dependence;
- confidence calibration and Wilson intervals;
- explicit insufficient-evidence states instead of optimizing tiny samples.
"""

from __future__ import annotations

import itertools
import math
import sqlite3
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from core.config import settings
from core.logger import get_logger
from core.precision_gate import wilson_lower_bound

logger = get_logger(__name__)

_LONG = {"BUY", "OVERWEIGHT"}
_SHORT = {"SELL", "UNDERWEIGHT"}
_ACTIVE = _LONG | _SHORT


def _float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _parse(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _signed(value: Any, rating: str) -> float:
    number = _float(value)
    return -number if str(rating).upper() in _SHORT else number


def _safe_mean(values: Iterable[float]) -> float:
    rows = [float(value) for value in values]
    return sum(rows) / len(rows) if rows else 0.0


class ResearchRobustnessLab:
    """Run evidence-aware robustness diagnostics on the forward scorecard."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or settings.KNOWLEDGE_DB_PATH

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _resolved_rows(self, horizon_sessions: int) -> list[dict[str, Any]]:
        horizon = max(1, int(horizon_sessions))
        try:
            conn = self._connect()
            rows = conn.execute(
                """
                SELECT d.decision_id, d.ticker, d.as_of, d.rating, d.verdict,
                       d.confidence, d.directional_score, d.evidence_quality,
                       d.evidence_count, d.source_diversity_score, d.benchmark,
                       o.horizon_sessions, o.target_date, o.return_pct,
                       o.benchmark_return_pct, o.alpha_pct,
                       o.direction_correct, o.alpha_direction_correct,
                       o.brier_score, o.resolved_at
                FROM research_outcomes_v2 o
                JOIN research_decisions_v2 d ON d.decision_id = o.decision_id
                WHERE o.horizon_sessions = ?
                  AND d.audit_eligible = 1
                  AND d.rating IN ('BUY','OVERWEIGHT','SELL','UNDERWEIGHT')
                ORDER BY datetime(d.as_of) ASC, d.decision_id ASC
                """,
                (horizon,),
            ).fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as exc:
            logger.warning("ResearchRobustness resolved query failed: %s", exc)
            return []

    @staticmethod
    def _stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
        total = len(rows)
        correct = sum(int(row.get("direction_correct", 0) or 0) for row in rows)
        alpha_rows = [
            row for row in rows if row.get("alpha_direction_correct") is not None
        ]
        alpha_correct = sum(
            int(row.get("alpha_direction_correct", 0) or 0) for row in alpha_rows
        )
        hit_rate = correct / total if total else 0.0
        alpha_hit = alpha_correct / len(alpha_rows) if alpha_rows else 0.0
        confidence = _safe_mean(_float(row.get("confidence")) / 100.0 for row in rows)
        signed_return = _safe_mean(
            _signed(row.get("return_pct"), row.get("rating", "")) for row in rows
        )
        signed_alpha_values = [
            _signed(row.get("alpha_pct"), row.get("rating", ""))
            for row in rows if row.get("alpha_pct") is not None
        ]
        return {
            "samples": total,
            "correct": correct,
            "hit_rate": round(hit_rate, 6),
            "wilson_lower_bound": round(wilson_lower_bound(correct, total), 6),
            "alpha_samples": len(alpha_rows),
            "alpha_hit_rate": round(alpha_hit, 6),
            "average_signed_return_pct": round(signed_return, 6),
            "average_signed_alpha_pct": round(_safe_mean(signed_alpha_values), 6),
            "average_confidence": round(confidence, 6),
            "calibration_gap": round(abs(confidence - hit_rate), 6),
            "average_brier_score": round(
                _safe_mean(_float(row.get("brier_score")) for row in rows), 6
            ),
        }

    def _pre_decision_prices(
        self, ticker: str, as_of: datetime, limit: int = 41
    ) -> list[float]:
        try:
            conn = self._connect()
            rows = conn.execute(
                """
                SELECT close FROM daily_ohlcv
                WHERE ticker = ? AND date < ? AND close > 0
                ORDER BY date DESC LIMIT ?
                """,
                (ticker.upper(), as_of.date().isoformat(), max(5, int(limit))),
            ).fetchall()
            conn.close()
            return [float(row["close"]) for row in rows]
        except Exception:
            return []

    def classify_regime(self, row: dict[str, Any]) -> dict[str, Any]:
        """Classify regime from information strictly prior to decision date."""
        as_of = _parse(row.get("as_of"))
        if as_of is None:
            return {"trend": "UNKNOWN", "volatility": "UNKNOWN", "available": False}
        symbol = str(row.get("benchmark") or row.get("ticker") or "").upper()
        prices_desc = self._pre_decision_prices(symbol, as_of, limit=41)
        if len(prices_desc) < 21:
            return {
                "trend": "UNKNOWN",
                "volatility": "UNKNOWN",
                "available": False,
                "symbol": symbol,
                "bars": len(prices_desc),
            }

        latest = prices_desc[0]
        oldest = prices_desc[20]
        trend_return = (latest - oldest) / oldest * 100.0 if oldest > 0 else 0.0
        if trend_return >= 5.0:
            trend = "BULL"
        elif trend_return <= -5.0:
            trend = "BEAR"
        else:
            trend = "SIDEWAYS"

        chronological = list(reversed(prices_desc[:21]))
        daily_returns: list[float] = []
        for previous, current in zip(chronological, chronological[1:]):
            if previous > 0:
                daily_returns.append((current - previous) / previous)
        realized_vol = (
            statistics.pstdev(daily_returns) * math.sqrt(252.0) * 100.0
            if len(daily_returns) >= 2 else 0.0
        )
        volatility = "HIGH_VOL" if realized_vol >= 30.0 else "NORMAL_VOL"
        return {
            "trend": trend,
            "volatility": volatility,
            "available": True,
            "symbol": symbol,
            "bars": len(prices_desc),
            "trend_return_pct": round(trend_return, 6),
            "annualized_realized_vol_pct": round(realized_vol, 6),
        }

    def regime_report(
        self, *, horizon_sessions: int = 5, min_samples: int = 5
    ) -> dict[str, Any]:
        rows = self._resolved_rows(horizon_sessions)
        buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
        unknown = 0
        for row in rows:
            regime = self.classify_regime(row)
            if not regime.get("available"):
                unknown += 1
                continue
            key = f"{regime['trend']}::{regime['volatility']}"
            buckets[key].append(row)

        result = {}
        for key, bucket in sorted(buckets.items()):
            stats = self._stats(bucket)
            stats["sufficient"] = len(bucket) >= max(1, int(min_samples))
            result[key] = stats
        return {
            "horizon_sessions": max(1, int(horizon_sessions)),
            "resolved_decisions": len(rows),
            "classified_decisions": sum(len(value) for value in buckets.values()),
            "unknown_regime": unknown,
            "min_samples_per_regime": max(1, int(min_samples)),
            "regimes": result,
            "live_gate_input": False,
        }

    @staticmethod
    def _accepts(row: dict[str, Any], policy: dict[str, float]) -> bool:
        return (
            _float(row.get("confidence")) >= policy["min_confidence"]
            and _float(row.get("evidence_quality")) >= policy["min_quality"]
            and _float(row.get("source_diversity_score")) >= policy["min_diversity"]
            and abs(_float(row.get("directional_score"))) >= policy["min_directional_score"]
        )

    @staticmethod
    def _candidate_policies() -> list[dict[str, float]]:
        return [
            {
                "min_confidence": float(confidence),
                "min_quality": float(quality),
                "min_diversity": float(diversity),
                "min_directional_score": float(score),
            }
            for confidence, quality, diversity, score in itertools.product(
                (50, 60, 70, 80),
                (0.45, 0.55, 0.65, 0.75),
                (0.50, 0.75, 1.00),
                (0.25, 0.40, 0.55),
            )
        ]

    def _policy_score(
        self,
        rows: list[dict[str, Any]],
        policy: dict[str, float],
        min_accepted: int,
    ) -> tuple[float, dict[str, Any]]:
        accepted = [row for row in rows if self._accepts(row, policy)]
        if len(accepted) < min_accepted:
            return -1e9, {"samples": len(accepted), "eligible": False}
        stats = self._stats(accepted)
        signed_return_component = max(
            -1.0, min(1.0, stats["average_signed_return_pct"] / 5.0)
        )
        objective = (
            0.35 * stats["hit_rate"]
            + 0.25 * stats["wilson_lower_bound"]
            + 0.20 * (1.0 - min(1.0, stats["calibration_gap"]))
            + 0.10 * (signed_return_component + 1.0) / 2.0
            + 0.10 * min(1.0, len(accepted) / max(min_accepted * 2.0, 1.0))
        )
        return objective, {**stats, "eligible": True, "objective": round(objective, 6)}

    def walk_forward(
        self,
        *,
        horizon_sessions: int = 5,
        min_train: int = 30,
        test_size: int = 10,
        min_train_accepted: int = 10,
    ) -> dict[str, Any]:
        """Expanding-window admission-threshold validation.

        Candidate policies are selected only on each fold's past training rows,
        then frozen before evaluating the next chronological test block. This is
        a robustness diagnostic for *stricter admission among existing active
        decisions*; it does not infer whether historical HOLDs should have traded.
        """
        rows = self._resolved_rows(horizon_sessions)
        min_train = max(10, int(min_train))
        test_size = max(1, int(test_size))
        min_train_accepted = max(3, int(min_train_accepted))
        required = min_train + test_size
        if len(rows) < required:
            return {
                "status": "insufficient_evidence",
                "horizon_sessions": max(1, int(horizon_sessions)),
                "resolved_decisions": len(rows),
                "required_for_first_fold": required,
                "reason": (
                    "Walk-forward threshold selection is disabled until enough "
                    "forward-resolved research decisions exist."
                ),
                "live_gate_input": False,
            }

        policies = self._candidate_policies()
        folds: list[dict[str, Any]] = []
        cursor = min_train
        while cursor < len(rows):
            train = rows[:cursor]
            test = rows[cursor : cursor + test_size]
            if not test:
                break

            best_policy = None
            best_score = -1e9
            best_train_stats: dict[str, Any] = {}
            for policy in policies:
                score, train_stats = self._policy_score(
                    train, policy, min_train_accepted
                )
                if score > best_score:
                    best_score = score
                    best_policy = policy
                    best_train_stats = train_stats

            if best_policy is None or best_score <= -1e8:
                folds.append({
                    "train_samples": len(train),
                    "test_samples": len(test),
                    "status": "no_train_policy_with_enough_samples",
                    "train_end_as_of": train[-1].get("as_of"),
                    "test_start_as_of": test[0].get("as_of"),
                    "test_end_as_of": test[-1].get("as_of"),
                })
                cursor += test_size
                continue

            accepted_test = [row for row in test if self._accepts(row, best_policy)]
            test_stats = self._stats(accepted_test)
            folds.append({
                "status": "evaluated",
                "train_samples": len(train),
                "test_samples": len(test),
                "test_accepted": len(accepted_test),
                "train_end_as_of": train[-1].get("as_of"),
                "test_start_as_of": test[0].get("as_of"),
                "test_end_as_of": test[-1].get("as_of"),
                "selected_policy": best_policy,
                "train_objective": round(best_score, 6),
                "train_stats": best_train_stats,
                "test_stats": test_stats,
            })
            cursor += test_size

        evaluated = [fold for fold in folds if fold.get("status") == "evaluated"]
        accepted_test_rows = sum(int(fold.get("test_accepted", 0)) for fold in evaluated)
        policy_counter = Counter(
            tuple(sorted(fold["selected_policy"].items())) for fold in evaluated
        )
        dominant_share = (
            max(policy_counter.values()) / len(evaluated)
            if evaluated and policy_counter else 0.0
        )
        weighted_hit_numerator = sum(
            fold["test_stats"]["hit_rate"] * fold.get("test_accepted", 0)
            for fold in evaluated
        )
        aggregate_hit = (
            weighted_hit_numerator / accepted_test_rows if accepted_test_rows else 0.0
        )
        return {
            "status": "evaluated" if evaluated else "insufficient_evidence",
            "horizon_sessions": max(1, int(horizon_sessions)),
            "resolved_decisions": len(rows),
            "folds": folds,
            "evaluated_folds": len(evaluated),
            "accepted_out_of_sample_decisions": accepted_test_rows,
            "out_of_sample_hit_rate": round(aggregate_hit, 6),
            "policy_stability_share": round(dominant_share, 6),
            "policy_stable": dominant_share >= 0.60 if evaluated else False,
            "scope_note": (
                "Policies only make the existing active-research admission stricter. "
                "They do not retroactively convert HOLD decisions into trades."
            ),
            "live_gate_input": False,
        }

    @staticmethod
    def _filtered_pack(pack: dict[str, Any], predicate) -> dict[str, Any]:
        items = [item for item in pack["items"] if predicate(item)]
        return {
            **pack,
            "items": items,
            "bull": [item for item in items if item.direction == "BULLISH"],
            "bear": [item for item in items if item.direction == "BEARISH"],
            "neutral": [item for item in items if item.direction == "NEUTRAL"],
        }

    def ablation(
        self,
        ticker: str,
        *,
        as_of: Any = None,
        max_sources: int = 8,
    ) -> dict[str, Any]:
        """Recompute one point-in-time decision after removing evidence slices."""
        from agents.research_council import ResearchCouncil

        council = ResearchCouncil()
        pack = council.build_evidence_pack(ticker, as_of=as_of)
        baseline_metrics = council._metrics(pack)
        baseline_rating, baseline_reasons = council._base_rating(baseline_metrics)

        category_rows = []
        categories = sorted({item.category for item in pack["items"]})
        for category in categories:
            filtered = self._filtered_pack(
                pack, lambda item, category=category: item.category != category
            )
            metrics = council._metrics(filtered)
            rating, reasons = council._base_rating(metrics)
            category_rows.append({
                "removed_category": category,
                "remaining_evidence": len(filtered["items"]),
                "rating": rating,
                "rating_flipped": rating != baseline_rating,
                "directional_score": metrics["directional_score"],
                "evidence_quality": metrics["evidence_quality"],
                "confidence": metrics["confidence"],
                "reasons": reasons,
            })

        source_weights: dict[tuple[str, str], float] = defaultdict(float)
        for item in pack["items"]:
            source_weights[(item.source_type, item.source)] += item.weight
        top_sources = sorted(
            source_weights.items(), key=lambda pair: pair[1], reverse=True
        )[: max(1, min(int(max_sources), 20))]
        source_rows = []
        for (source_type, source), weight in top_sources:
            filtered = self._filtered_pack(
                pack,
                lambda item, source_type=source_type, source=source: not (
                    item.source_type == source_type and item.source == source
                ),
            )
            metrics = council._metrics(filtered)
            rating, reasons = council._base_rating(metrics)
            source_rows.append({
                "removed_source_type": source_type,
                "removed_source": source,
                "removed_weight": round(weight, 6),
                "remaining_evidence": len(filtered["items"]),
                "rating": rating,
                "rating_flipped": rating != baseline_rating,
                "directional_score": metrics["directional_score"],
                "evidence_quality": metrics["evidence_quality"],
                "confidence": metrics["confidence"],
                "reasons": reasons,
            })

        category_flips = sum(1 for row in category_rows if row["rating_flipped"])
        source_flips = sum(1 for row in source_rows if row["rating_flipped"])
        return {
            "ticker": pack["ticker"],
            "as_of": pack["as_of"],
            "baseline": {
                "rating": baseline_rating,
                "metrics": baseline_metrics,
                "reasons": baseline_reasons,
                "evidence_count": len(pack["items"]),
            },
            "category_ablation": category_rows,
            "source_ablation": source_rows,
            "category_flip_rate": round(
                category_flips / len(category_rows), 6
            ) if category_rows else 0.0,
            "source_flip_rate": round(
                source_flips / len(source_rows), 6
            ) if source_rows else 0.0,
            "fragile": category_flips > 0 or source_flips > 0,
            "execution_authority": False,
            "live_gate_input": False,
        }

    def report(
        self,
        *,
        horizon_sessions: int = 5,
        min_train: int = 30,
        test_size: int = 10,
    ) -> dict[str, Any]:
        rows = self._resolved_rows(horizon_sessions)
        overall = self._stats(rows)
        walk_forward = self.walk_forward(
            horizon_sessions=horizon_sessions,
            min_train=min_train,
            test_size=test_size,
        )
        regimes = self.regime_report(horizon_sessions=horizon_sessions)
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "horizon_sessions": max(1, int(horizon_sessions)),
            "overall_forward_scorecard": overall,
            "regime_analysis": regimes,
            "walk_forward": walk_forward,
            "evidence_sufficient_for_walk_forward": (
                walk_forward.get("status") == "evaluated"
            ),
            "live_gate_input": False,
            "execution_authority": False,
            "profitability_claim": False,
            "note": (
                "Robustness diagnostics measure research stability only. They do not "
                "authorize live trading and do not guarantee future returns."
            ),
        }


research_robustness_lab = ResearchRobustnessLab()
