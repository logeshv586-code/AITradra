"""Benchmark-relative performance scorecard.

This module measures realized historical/paper returns; it does not forecast
future profitability. Strategy returns should already include execution costs.
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


def default_benchmark_symbol(ticker: str) -> str:
    """Choose a simple broad benchmark for the traded market."""
    symbol = str(ticker or "").upper()
    crypto_tokens = ("BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "DOGE")
    if any(token in symbol for token in crypto_tokens) or symbol.endswith("-USD"):
        return "BTC-USD"
    if symbol.endswith(".NS"):
        return "^NSEI"
    return "SPY"


class BenchmarkScorecard:
    """Compare realized strategy performance against a benchmark on identical dates."""

    @staticmethod
    def _status(strategy_metrics: dict[str, Any], benchmark_metrics: dict[str, Any]) -> tuple[str, dict[str, bool]]:
        beats_return = float(strategy_metrics.get("total_return_pct", 0.0)) > float(benchmark_metrics.get("total_return_pct", 0.0))
        beats_sharpe = float(strategy_metrics.get("sharpe_ratio", 0.0)) > float(benchmark_metrics.get("sharpe_ratio", 0.0))
        strategy_dd = float(strategy_metrics.get("max_drawdown_pct", 100.0))
        benchmark_dd = float(benchmark_metrics.get("max_drawdown_pct", 100.0))
        drawdown_not_worse = strategy_dd <= benchmark_dd * 1.10 + 1e-9
        status = "BEATS_BENCHMARK" if beats_return and beats_sharpe and drawdown_not_worse else "DOES_NOT_BEAT_BENCHMARK"
        return status, {
            "higher_total_return": beats_return,
            "higher_sharpe": beats_sharpe,
            "drawdown_not_materially_worse": drawdown_not_worse,
        }

    def evaluate_summary(
        self,
        strategy_metrics: dict[str, Any],
        benchmark_returns: Any,
        *,
        benchmark_name: str = "benchmark",
    ) -> dict[str, Any]:
        """Compare event-driven Backtrader summary metrics with benchmark daily returns."""
        benchmark_metrics = _metrics(_series(benchmark_returns))
        if benchmark_metrics["samples"] <= 0:
            return {
                "status": "insufficient_evidence",
                "benchmark": benchmark_name,
                "strategy": dict(strategy_metrics),
                "benchmark_metrics": benchmark_metrics,
                "execution_authority": False,
            }
        normalized_strategy = {
            "total_return_pct": round(float(strategy_metrics.get("total_return_pct", 0.0)), 6),
            "sharpe_ratio": round(float(strategy_metrics.get("sharpe_ratio", 0.0)), 6),
            "max_drawdown_pct": round(float(strategy_metrics.get("max_drawdown_pct", 100.0)), 6),
            "total_trades": int(strategy_metrics.get("total_trades", 0) or 0),
            "win_rate": round(float(strategy_metrics.get("win_rate", 0.0)), 6),
            "profit_factor": round(float(strategy_metrics.get("profit_factor", 0.0)), 6),
        }
        status, criteria = self._status(normalized_strategy, benchmark_metrics)
        return {
            "status": status,
            "benchmark": benchmark_name,
            "strategy": normalized_strategy,
            "benchmark_metrics": benchmark_metrics,
            "active_return_pct": round(
                normalized_strategy["total_return_pct"] - benchmark_metrics["total_return_pct"], 6
            ),
            "criteria": criteria,
            "execution_authority": False,
            "evidence_note": "Out-of-sample event-driven comparison; not a promise of future outperformance",
        }

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
            pairs: list[tuple[float, bool]] = []
            for raw_p, raw_y in zip(list(probabilities_up), list(actual_up)):
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
                strategy_regime = _metrics(group["strategy"])
                benchmark_regime = _metrics(group["benchmark"])
                regime_report[str(name)] = {
                    "strategy": strategy_regime,
                    "benchmark": benchmark_regime,
                    "active_return_pct": round(
                        strategy_regime["total_return_pct"] - benchmark_regime["total_return_pct"], 6
                    ),
                }

        status, criteria = self._status(strategy_metrics, benchmark_metrics)
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
            "criteria": criteria,
            "execution_authority": False,
            "evidence_note": "Historical/paper scorecard only; not a promise of future outperformance",
        }


benchmark_scorecard = BenchmarkScorecard()
