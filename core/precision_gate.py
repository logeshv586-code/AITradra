"""Empirical precision gate for autonomous live trading.

This module does not claim or manufacture a 99% win rate.  It converts a
configured precision target into a fail-closed execution requirement based on
resolved directional predictions that were scored against later market data.

Paper trading remains available so the system can continue collecting evidence.
Autonomous live entries are blocked until the evidence is large enough, recent
enough, and statistically strong enough for the configured target.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)


def wilson_lower_bound(successes: int, total: int, z: float = 1.959963984540054) -> float:
    """Return the Wilson-score lower confidence bound for a binomial proportion."""
    if total <= 0:
        return 0.0
    successes = max(0, min(int(successes), int(total)))
    total = int(total)
    p = successes / total
    z2 = z * z
    denominator = 1.0 + z2 / total
    centre = p + z2 / (2.0 * total)
    margin = z * math.sqrt((p * (1.0 - p) + z2 / (4.0 * total)) / total)
    return max(0.0, min(1.0, (centre - margin) / denominator))


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


class EmpiricalPrecisionGate:
    """Fail-closed live-entry gate backed by resolved prediction outcomes."""

    def check(
        self,
        ticker: str,
        *,
        model: str = "SignalAggregatorAgent",
        direction: str | None = None,
        settings_obj=settings,
    ) -> dict[str, Any]:
        if not bool(getattr(settings_obj, "REQUIRE_EMPIRICAL_PRECISION_VALIDATION", True)):
            return {
                "eligible": True,
                "reasons": [],
                "stats": None,
                "target_precision": float(getattr(settings_obj, "AUTOTRADE_TARGET_PRECISION", 0.99)),
            }

        from self_improvement.accuracy_store import accuracy_store

        stats = accuracy_store.get_precision_stats(
            ticker=ticker,
            model=model,
            direction=direction,
        )

        total = int(stats.get("total_directional", 0) or 0)
        correct = int(stats.get("correct_scored", 0) or 0)
        observed = (correct / total) if total > 0 else 0.0
        lower_bound = wilson_lower_bound(correct, total)

        target = float(getattr(settings_obj, "AUTOTRADE_TARGET_PRECISION", 0.99))
        min_samples = int(getattr(settings_obj, "AUTOTRADE_MIN_EVALUATED_SIGNALS", 100))
        min_lower_bound = float(
            getattr(settings_obj, "AUTOTRADE_MIN_PRECISION_LOWER_BOUND", 0.95)
        )
        max_age_days = int(getattr(settings_obj, "PRECISION_VALIDATION_MAX_AGE_DAYS", 30))

        reasons: list[str] = []
        if total < min_samples:
            reasons.append(
                f"Only {total} resolved directional signals are available; {min_samples} are required"
            )
        if observed < target:
            reasons.append(
                f"Observed directional precision {observed * 100:.2f}% is below the configured {target * 100:.2f}% target"
            )
        if lower_bound < min_lower_bound:
            reasons.append(
                f"Statistical lower bound {lower_bound * 100:.2f}% is below the required {min_lower_bound * 100:.2f}%"
            )

        last_updated = _parse_timestamp(stats.get("last_updated"))
        if last_updated is None:
            reasons.append("Precision evidence has no valid update timestamp")
        else:
            age_days = (datetime.now(timezone.utc) - last_updated).total_seconds() / 86400
            if age_days > max_age_days:
                reasons.append(
                    f"Precision evidence is stale ({age_days:.1f} days > {max_age_days} days)"
                )

        enriched = {
            **stats,
            "observed_precision": round(observed, 6),
            "wilson_lower_bound": round(lower_bound, 6),
            "target_precision": target,
            "min_samples": min_samples,
            "min_lower_bound": min_lower_bound,
        }
        return {
            "eligible": not reasons,
            "reasons": reasons,
            "stats": enriched,
            "target_precision": target,
        }


empirical_precision_gate = EmpiricalPrecisionGate()
