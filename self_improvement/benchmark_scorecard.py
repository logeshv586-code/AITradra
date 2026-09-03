"""Benchmark-relative performance scorecard.

This module measures realized historical/paper returns; it does not forecast
future profitability. Strategy returns should already include the execution
assumptions being evaluated (fees/slippage). Optional turnover can be supplied to
charge friction here as well.
"""

from __future__ import annotations

from math import sqrt
from typing import Any

import numpy as np
import pandas as pd


def _series(values: Any) -> pd.Series:
    if isinstance(values, pd.Series):
        result = values.copy()
    else:
        result = pd.Series(values, dtype=float)
    return pd.to_numeric(result, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna().astype(float)


def _metrics(returns: pd.Series) -> dict[str, float]:
    values = _series(returns)
    if values.empty:
        return {
            "samples": 0,
            "total_return_pct": 0.0,
            "annualized_return_pct": 0.0,
            "annualized_volatility_pct": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "max_drawdown_pct": 100.0,
        }
    equity = (1.0 + values).cumprod()
    total = float(equity.iloc[-1] - 1.0)
    years = max(len(values) / 252.0, 1.0 / 252.0)
    annualized = float(equity.iloc[-1] ** (1.0 / years) - 1.0) if equity.iloc[-1] > 0 else -1.0
    std = float(values.std(ddof=1)) if len(values) > 1 else 0.0
    vol = std * sqrt(252.0)
    sharpe = float(values.mean() / std * sqrt(252.0)) if std > 1e-12 else 0.0
    downside = values[values < 0]
    downside_std = float(downside.std(ddof=1)) if len(downside) > 1 else 0.0
    sortino = float(values.mean() / downside_std * sqrt(252.0)) if downside_std > 1e-12 else 0.0
    drawdown = equity / equity.cummax() - 1.0
    max_dd = abs(float(drawdown.min())) if not drawdown.empty else 0.0
    return {
        "samples": int(len(values)),
        "total_return_pct": round(total * 100.0, 6),
        "annualized_return_pct": round(annualized * 100.0, 6),
        "annualized_volatility_pct": round(vol * 100.0, 6),
        "sharpe_ratio": round(sharpe, 6),
        "sortino_ratio": round(sortino, 6),
        "max_drawdown_pct": round(max_dd * 100.0, 6),
    }


def _probability(value: Any) -> float | None:
    try:
        p = float(value)
    except (TypeError, ValueError):
        return None
    if 1 < p <= 100:
        p /= 100.0
    return p if 0 <= p <= 1 else None


class BenchmarkScorecard:
    """Compare realized strategy performance against a benchmark on identical dates."""

    def evaluate(
        self,
        strategy_returns: Any,
        benchmark_returns: Any,
        *,
        turnover: Any | None = None,
        fee_bps: float = 0.0,
        slippage_bps: float = 0.0,
        probabilities_up: Any | None = None,
        actual_up: Any | None = None,
        regimes: Any | None = None,
        benchmark_name: str = "benchmark",
    ) -> dict[str, Any]:
        strategy = _series(strategy_returns)
        benchmark = _series(benchmark_returns)
        aligned = pd.concat([strategy.rename("strategy"), benchmark.rename("benchmark")], axis=1).dropna()
        if aligned.empty:
            return {
                "status": "insufficient_evidence",
                "benchmark": benchmark_name,
                "execution_authority": False,
                "reasons": ["No overlapping realized strategy and benchmark returns"],
            }

        if turnover is not None:
            turn = _series(turnover).reindex(aligned.index).fillna(0.0).abs()
            friction = max(0.0, float(fee_bps) + float(slippage_bps)) / 10_000.0
            aligned["strategy"] = aligned["strategy"] - turn * friction

        strategy_metrics = _metrics(aligned["strategy"])
        benchmark_metrics = _metrics(aligned["benchmark"])
        active = aligned["strategy"] - aligned["benchmark"]
        active_std = float(active.std(ddof=1)) if len(active) > 1 else 0.0
        information_ratio = float(active.mean() / active_std * sqrt(252.0)) if active_std > 1e-12 else 0.0

        benchmark_var = float(aligned["benchmark"].var(ddof=1)) if len(aligned) > 1 else 0.0
        covariance = float(aligned[["strategy", "benchmark"]].cov().iloc[0, 1]) if len(aligned) > 1 else 0.0
        beta = covariance / benchmark_var if benchmark_var > 1e-12 else 0.0
        alpha_daily = float(aligned["strategy"].mean() - beta * aligned["benchmark"].mean())
        alpha_annualized_pct = alpha_daily * 252.0 * 100.0

        directional_hit_rate = None
        brier_score = None
        if probabilities_up is not None and actual_up is not None:
            probs = list(probabilities_up)
            outcomes = list(actual_up)
            pairs: list[tuple[float, bool]] = []
            for raw_p, raw_y in zip(probs, outcomes):
                p = _probability(raw_p)
                if p is None:
                    continue
                if isinstance(raw_y, bool):
                    y = raw_y
                elif str(raw_y).upper() in {"1", "TRUE", "UP", "BUY", "BULLISH"}:
                    y = True
                elif str(raw_y).upper() in {"0", "FALSE", "DOWN", "SELL", "BEARISH"}:
                    y = False
                else:
                    continue
                pairs.append((p, y))
            if pairs:
                directional_hit_rate = sum((p >= 0.5) == y for p, y in pairs) / len(pairs)
                brier_score = sum((p - (1.0 if y else 0.0)) ** 2 for p, y in pairs) / len(pairs)

        regime_report: dict[str, Any] = {}
        if regimes is not None:
            regime_series = pd.Series(regimes).reindex(aligned.index)
            frame = aligned.copy()
            frame["regime"] = regime_series
            for name, group in frame.dropna(subset=["regime"]).groupby("regime"):
                if len(group) < 5:
                    continue
                regime_report[str(name)] = {
                    "strategy": _metrics(group["strategy"]),
                    "benchmark": _metrics(group["benchmark"]),
                    "active_return_pct": round(
                        _metrics(group["strategy"])["total_return_pct"]
                        - _metrics(group["benchmark"])["total_return_pct"],
                        6,
                    ),
                }

        beats_return = strategy_metrics["total_return_pct"] > benchmark_metrics["total_return_pct"]
        beats_sharpe = strategy_metrics["sharpe_ratio"] > benchmark_metrics["sharpe_ratio"]
        drawdown_not_worse = strategy_metrics["max_drawdown_pct"] <= benchmark_metrics["max_drawdown_pct"] * 1.10 + 1e-9
        status = "BEATS_BENCHMARK" if beats_return and beats_sharpe and drawdown_not_worse else "DOES_NOT_BEAT_BENCHMARK"

        return {
            "status": status,
            "benchmark": benchmark_name,
            "strategy": strategy_metrics,
            "benchmark_metrics": benchmark_metrics,
            "active_return_pct": round(
                strategy_metrics["total_return_pct"] - benchmark_metrics["total_return_pct"], 6
            ),
            "annualized_alpha_pct": round(alpha_annualized_pct, 6),
            "beta": round(beta, 6),
            "information_ratio": round(information_ratio, 6),
            "directional_hit_rate": None if directional_hit_rate is None else round(directional_hit_rate, 6),
            "brier_score": None if brier_score is None else round(brier_score, 6),
            "regimes": regime_report,
            "criteria": {
                "higher_total_return": beats_return,
                "higher_sharpe": beats_sharpe,
                "drawdown_not_materially_worse": drawdown_not_worse,
            },
            "execution_authority": False,
            "evidence_note": "Historical/paper scorecard only; not a promise of future outperformance",
        }


benchmark_scorecard = BenchmarkScorecard()
