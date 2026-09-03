"""Plugin Ablation Lab for AITradra.

The lab compares every optional plugin against the same resolved decisions used by
the core signal. It never grants execution permission. A plugin may increase
confidence only after enough out-of-sample observations show that adding it
improves calibration and/or directional accuracy without materially increasing
error.

Expected decision shape::

    {
      "actual_up": True,
      "core_probability_up": 0.61,
      "plugins": {
          "finbert": {"probability_up": 0.68},
          "quantic": {"probability_up": 0.55},
      },
      "regime": "BULL_TRENDING",
    }

Plugin probabilities are blended with the core probability using the configured
plugin weight. This mirrors the real question: did the plugin add signal beyond
what the core model already knew?
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from math import sqrt
from typing import Any, Iterable


@dataclass(frozen=True)
class PluginAblationResult:
    plugin: str
    samples: int
    core_hit_rate: float
    plugin_hit_rate: float
    hit_rate_delta: float
    core_brier: float
    plugin_brier: float
    brier_improvement: float
    policy: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _clip_probability(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number > 1.0 and number <= 100.0:
        number /= 100.0
    if not 0.0 <= number <= 1.0:
        return None
    return number


def _actual_up(row: dict[str, Any]) -> bool | None:
    if isinstance(row.get("actual_up"), bool):
        return bool(row["actual_up"])
    direction = str(row.get("actual_direction", "")).upper()
    if direction in {"UP", "BULLISH", "BUY", "LONG"}:
        return True
    if direction in {"DOWN", "BEARISH", "SELL", "SHORT"}:
        return False
    return None


def _brier(probabilities: list[float], actual: list[bool]) -> float:
    if not probabilities:
        return 1.0
    return sum((p - (1.0 if y else 0.0)) ** 2 for p, y in zip(probabilities, actual)) / len(probabilities)


def _hit_rate(probabilities: list[float], actual: list[bool]) -> float:
    if not probabilities:
        return 0.0
    correct = sum((p >= 0.5) == y for p, y in zip(probabilities, actual))
    return correct / len(probabilities)


class PluginAblationLab:
    """Measure whether optional plugins add out-of-sample value."""

    def __init__(
        self,
        *,
        min_samples: int = 50,
        plugin_weight: float = 0.25,
        min_brier_improvement: float = 0.005,
        min_hit_rate_delta: float = 0.005,
        disable_brier_regression: float = 0.01,
    ) -> None:
        self.min_samples = max(5, int(min_samples))
        self.plugin_weight = max(0.0, min(float(plugin_weight), 0.5))
        self.min_brier_improvement = float(min_brier_improvement)
        self.min_hit_rate_delta = float(min_hit_rate_delta)
        self.disable_brier_regression = float(disable_brier_regression)

    def evaluate(
        self,
        decisions: Iterable[dict[str, Any]],
        *,
        plugins: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        rows = [row for row in decisions if isinstance(row, dict)]
        discovered = set()
        for row in rows:
            payload = row.get("plugins") or row.get("plugin_snapshot") or {}
            if isinstance(payload, dict):
                discovered.update(str(name) for name in payload)
        names = sorted(set(plugins or discovered))

        results: dict[str, Any] = {}
        for plugin in names:
            result = self._evaluate_one(rows, plugin)
            results[plugin] = result.to_dict()

        keep = [name for name, row in results.items() if row["policy"] == "KEEP"]
        advisory = [name for name, row in results.items() if row["policy"] == "ADVISORY"]
        disabled = [name for name, row in results.items() if row["policy"] == "DISABLE"]
        return {
            "sample_rows": len(rows),
            "minimum_samples": self.min_samples,
            "plugin_weight": self.plugin_weight,
            "results": results,
            "keep": keep,
            "advisory": advisory,
            "disable": disabled,
            "execution_authority": False,
        }

    def _evaluate_one(self, rows: list[dict[str, Any]], plugin: str) -> PluginAblationResult:
        core_probs: list[float] = []
        plugin_probs: list[float] = []
        actual: list[bool] = []

        for row in rows:
            outcome = _actual_up(row)
            core = _clip_probability(
                row.get("core_probability_up", row.get("probability_up"))
            )
            payload = row.get("plugins") or row.get("plugin_snapshot") or {}
            plugin_payload = payload.get(plugin, {}) if isinstance(payload, dict) else {}
            if isinstance(plugin_payload, dict):
                candidate = plugin_payload.get("probability_up")
                if candidate is None:
                    direction = str(plugin_payload.get("direction", "")).upper()
                    confidence = _clip_probability(plugin_payload.get("confidence"))
                    if confidence is not None and direction:
                        if direction in {"BUY", "UP", "BULLISH", "LONG"}:
                            candidate = 0.5 + confidence * 0.5
                        elif direction in {"SELL", "DOWN", "BEARISH", "SHORT"}:
                            candidate = 0.5 - confidence * 0.5
            else:
                candidate = plugin_payload
            plugin_prob = _clip_probability(candidate)
            if outcome is None or core is None or plugin_prob is None:
                continue

            blended = (1.0 - self.plugin_weight) * core + self.plugin_weight * plugin_prob
            core_probs.append(core)
            plugin_probs.append(max(0.0, min(1.0, blended)))
            actual.append(outcome)

        samples = len(actual)
        core_hit = _hit_rate(core_probs, actual)
        plugin_hit = _hit_rate(plugin_probs, actual)
        core_brier = _brier(core_probs, actual)
        plugin_brier = _brier(plugin_probs, actual)
        hit_delta = plugin_hit - core_hit
        brier_improvement = core_brier - plugin_brier

        if samples < self.min_samples:
            policy = "ADVISORY"
            reason = f"Only {samples} resolved samples; {self.min_samples} required before confidence boosting"
        elif brier_improvement >= self.min_brier_improvement and hit_delta >= -0.002:
            policy = "KEEP"
            reason = "Improves probability calibration on the same resolved out-of-sample decisions"
        elif hit_delta >= self.min_hit_rate_delta and brier_improvement >= -0.002:
            policy = "KEEP"
            reason = "Improves directional hit rate without material calibration regression"
        elif brier_improvement <= -self.disable_brier_regression and hit_delta <= 0:
            policy = "DISABLE"
            reason = "Adds measurable calibration error without directional benefit"
        else:
            policy = "ADVISORY"
            reason = "No statistically convincing incremental edge yet"

        return PluginAblationResult(
            plugin=plugin,
            samples=samples,
            core_hit_rate=round(core_hit, 6),
            plugin_hit_rate=round(plugin_hit, 6),
            hit_rate_delta=round(hit_delta, 6),
            core_brier=round(core_brier, 6),
            plugin_brier=round(plugin_brier, 6),
            brier_improvement=round(brier_improvement, 6),
            policy=policy,
            reason=reason,
        )

    def confidence_multiplier(self, decisions: Iterable[dict[str, Any]], plugin: str) -> float:
        """Return a bounded plugin confidence multiplier derived from measured history."""
        result = self._evaluate_one(
            [row for row in decisions if isinstance(row, dict)], plugin
        )
        if result.policy != "KEEP":
            return 1.0
        # Incremental boosts are intentionally tiny. Measured plugins validate a
        # signal; they never manufacture high confidence from a successful call.
        benefit = max(0.0, result.brier_improvement) + max(0.0, result.hit_rate_delta)
        return round(min(1.05, 1.0 + benefit), 6)


plugin_ablation_lab = PluginAblationLab()
