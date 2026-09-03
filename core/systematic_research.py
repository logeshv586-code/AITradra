"""Systematic strategy discovery and robustness validation for AITradra.

This module is intentionally research-only. It can discover candidate rule-based
strategies and produce dated signals, but it never authorizes a funded order.
The existing BacktestAgent, deterministic risk controls, empirical precision gate,
and trade-qualification firewall remain the authority for execution eligibility.

The engine is designed to reduce common quantitative-research failure modes:

* parameter selection is performed on an initial training window only;
* the winner is selected with a separate validation window;
* a final test window remains untouched until after selection;
* expanding walk-forward blocks test temporal stability;
* block-bootstrap Sharpe bounds expose unstable estimates;
* a sign-flip null test checks whether positive mean returns are distinguishable
  from random direction;
* a probabilistic Sharpe calculation is penalized for the number of candidates
  screened;
* regime segmentation checks whether performance depends on one market state;
* fees/slippage are charged through turnover in every vectorized evaluation.

The implementation uses NumPy/Pandas so it remains deterministic and lightweight.
AITradra can continue to use vectorbt/Backtrader elsewhere: this layer is the fast
candidate screen before the existing event-driven realistic replay.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, log, sqrt
from statistics import NormalDist
from typing import Any, Iterable

import numpy as np
import pandas as pd

from core.config import settings


@dataclass(frozen=True)
class CandidateSpec:
    family: str
    params: tuple[tuple[str, float | int], ...]

    @classmethod
    def make(cls, family: str, **params: float | int) -> "CandidateSpec":
        return cls(family=family, params=tuple(sorted(params.items())))

    @property
    def parameter_dict(self) -> dict[str, float | int]:
        return dict(self.params)

    @property
    def strategy_id(self) -> str:
        suffix = "-".join(f"{key}{value}" for key, value in self.params)
        return f"systematic-{self.family}-{suffix}" if suffix else f"systematic-{self.family}"


class SystematicResearchEngine:
    """Discover and statistically challenge systematic trading candidates."""

    def __init__(
        self,
        *,
        min_history: int | None = None,
        max_candidates: int | None = None,
        top_k: int | None = None,
        min_robustness_score: float | None = None,
        bootstrap_samples: int | None = None,
        signflip_samples: int | None = None,
        seed: int = 42,
    ) -> None:
        self.min_history = int(
            min_history
            if min_history is not None
            else getattr(settings, "SYSTEMATIC_RESEARCH_MIN_HISTORY", 260)
        )
        self.max_candidates = int(
            max_candidates
            if max_candidates is not None
            else getattr(settings, "SYSTEMATIC_RESEARCH_MAX_CANDIDATES", 40)
        )
        self.top_k = int(
            top_k
            if top_k is not None
            else getattr(settings, "SYSTEMATIC_RESEARCH_TOP_K", 5)
        )
        self.min_robustness_score = float(
            min_robustness_score
            if min_robustness_score is not None
            else getattr(settings, "SYSTEMATIC_RESEARCH_MIN_ROBUSTNESS_SCORE", 60.0)
        )
        self.bootstrap_samples = int(
            bootstrap_samples
            if bootstrap_samples is not None
            else getattr(settings, "SYSTEMATIC_BOOTSTRAP_SAMPLES", 400)
        )
        self.signflip_samples = int(
            signflip_samples
            if signflip_samples is not None
            else getattr(settings, "SYSTEMATIC_SIGNFLIP_SAMPLES", 400)
        )
        self.seed = int(seed)

    @staticmethod
    def _close_series(df: pd.DataFrame) -> pd.Series:
        if df is None or df.empty or "Close" not in df.columns:
            return pd.Series(dtype=float)
        close = pd.to_numeric(df["Close"], errors="coerce")
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        close = close.astype(float).replace([np.inf, -np.inf], np.nan).dropna()
        close = close[~close.index.duplicated(keep="last")].sort_index()
        return close

    @staticmethod
    def _candidate_specs() -> list[CandidateSpec]:
        specs: list[CandidateSpec] = []

        for lookback in (10, 20, 40, 60):
            for threshold in (0.0, 0.01):
                specs.append(
                    CandidateSpec.make(
                        "momentum", lookback=lookback, threshold=threshold
                    )
                )

        for fast in (5, 10, 20):
            for slow in (30, 50, 100):
                if fast < slow:
                    specs.append(CandidateSpec.make("sma_cross", fast=fast, slow=slow))

        for window in (10, 20, 30):
            for z_entry in (1.0, 1.5, 2.0):
                specs.append(
                    CandidateSpec.make(
                        "mean_reversion", window=window, z_entry=z_entry
                    )
                )

        for window in (20, 40, 60):
            specs.append(CandidateSpec.make("breakout", window=window))

        return specs

    @staticmethod
    def _position(close: pd.Series, spec: CandidateSpec) -> pd.Series:
        p = spec.parameter_dict
        position = pd.Series(0.0, index=close.index, dtype=float)

        if spec.family == "momentum":
            lookback = int(p["lookback"])
            threshold = float(p["threshold"])
            momentum = close.pct_change(lookback)
            position = pd.Series(
                np.where(momentum > threshold, 1.0, np.where(momentum < -threshold, -1.0, 0.0)),
                index=close.index,
                dtype=float,
            )

        elif spec.family == "sma_cross":
            fast = int(p["fast"])
            slow = int(p["slow"])
            fast_ma = close.rolling(fast, min_periods=fast).mean()
            slow_ma = close.rolling(slow, min_periods=slow).mean()
            ready = fast_ma.notna() & slow_ma.notna()
            position.loc[ready & (fast_ma > slow_ma)] = 1.0
            position.loc[ready & (fast_ma < slow_ma)] = -1.0

        elif spec.family == "mean_reversion":
            window = int(p["window"])
            z_entry = float(p["z_entry"])
            mean = close.rolling(window, min_periods=window).mean()
            std = close.rolling(window, min_periods=window).std(ddof=0).replace(0, np.nan)
            zscore = (close - mean) / std
            position.loc[zscore <= -z_entry] = 1.0
            position.loc[zscore >= z_entry] = -1.0

        elif spec.family == "breakout":
            window = int(p["window"])
            previous_high = close.rolling(window, min_periods=window).max().shift(1)
            previous_low = close.rolling(window, min_periods=window).min().shift(1)
            events = pd.Series(np.nan, index=close.index, dtype=float)
            events.loc[close > previous_high] = 1.0
            events.loc[close < previous_low] = -1.0
            position = events.ffill().fillna(0.0)

        return position.fillna(0.0).clip(-1.0, 1.0)

    @staticmethod
    def _strategy_returns(
        close: pd.Series,
        position: pd.Series,
        *,
        fee_bps: float,
        slippage_bps: float,
    ) -> pd.Series:
        market_returns = close.pct_change().fillna(0.0)
        executed_position = position.reindex(close.index).fillna(0.0).shift(1).fillna(0.0)
        turnover = executed_position.diff().abs().fillna(executed_position.abs())
        friction = max(0.0, fee_bps + slippage_bps) / 10_000.0
        result = executed_position * market_returns - turnover * friction
        return result.replace([np.inf, -np.inf], np.nan).fillna(0.0)

    @staticmethod
    def _metrics(returns: pd.Series, position: pd.Series | None = None) -> dict[str, Any]:
        clean = pd.to_numeric(returns, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        if clean.empty:
            return {
                "samples": 0,
                "total_return_pct": 0.0,
                "annualized_return_pct": 0.0,
                "annualized_volatility_pct": 0.0,
                "sharpe_ratio": 0.0,
                "sortino_ratio": 0.0,
                "max_drawdown_pct": 100.0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "total_trades": 0,
            }

        equity = (1.0 + clean).cumprod()
        total_return = float(equity.iloc[-1] - 1.0)
        years = max(len(clean) / 252.0, 1.0 / 252.0)
        annualized_return = float(equity.iloc[-1] ** (1.0 / years) - 1.0) if equity.iloc[-1] > 0 else -1.0
        daily_std = float(clean.std(ddof=1)) if len(clean) > 1 else 0.0
        annualized_vol = daily_std * sqrt(252.0)
        sharpe = float(clean.mean() / daily_std * sqrt(252.0)) if daily_std > 1e-12 else 0.0
        downside = clean[clean < 0]
        downside_std = float(downside.std(ddof=1)) if len(downside) > 1 else 0.0
        sortino = float(clean.mean() / downside_std * sqrt(252.0)) if downside_std > 1e-12 else 0.0
        drawdown = equity / equity.cummax() - 1.0
        max_drawdown = abs(float(drawdown.min())) if not drawdown.empty else 0.0
        active = clean[clean != 0]
        win_rate = float((active > 0).mean()) if len(active) else 0.0
        gross_profit = float(clean[clean > 0].sum())
        gross_loss = abs(float(clean[clean < 0].sum()))
        profit_factor = gross_profit / gross_loss if gross_loss > 1e-12 else (999.0 if gross_profit > 0 else 0.0)

        trade_count = 0
        if position is not None and not position.empty:
            aligned = position.reindex(clean.index).fillna(0.0).shift(1).fillna(0.0)
            previous = aligned.shift(1).fillna(0.0)
            trade_count = int(((aligned != previous) & (aligned != 0.0)).sum())

        return {
            "samples": int(len(clean)),
            "total_return_pct": round(total_return * 100.0, 4),
            "annualized_return_pct": round(annualized_return * 100.0, 4),
            "annualized_volatility_pct": round(annualized_vol * 100.0, 4),
            "sharpe_ratio": round(sharpe, 4),
            "sortino_ratio": round(sortino, 4),
            "max_drawdown_pct": round(max_drawdown * 100.0, 4),
            "win_rate": round(win_rate, 4),
            "profit_factor": round(min(profit_factor, 999.0), 4),
            "total_trades": trade_count,
        }

    @staticmethod
    def _clip01(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    def _screen_score(self, metrics: dict[str, Any]) -> float:
        sharpe = self._clip01(float(metrics.get("sharpe_ratio", 0.0)) / 2.0)
        profit_factor = self._clip01((float(metrics.get("profit_factor", 0.0)) - 1.0) / 1.0)
        win_rate = self._clip01(float(metrics.get("win_rate", 0.0)) / 0.60)
        total_return = self._clip01(float(metrics.get("total_return_pct", 0.0)) / 30.0)
        drawdown = 1.0 - self._clip01(float(metrics.get("max_drawdown_pct", 100.0)) / 30.0)
        trades = self._clip01(float(metrics.get("total_trades", 0)) / 20.0)
        return round(
            30.0 * sharpe
            + 20.0 * profit_factor
            + 15.0 * win_rate
            + 15.0 * total_return
            + 10.0 * drawdown
            + 10.0 * trades,
            4,
        )

    @staticmethod
    def _slice(series: pd.Series, start: int, end: int) -> pd.Series:
        return series.iloc[max(0, start):max(0, end)].copy()

    def _evaluate_slice(
        self,
        close: pd.Series,
        spec: CandidateSpec,
        *,
        start: int,
        end: int,
        fee_bps: float,
        slippage_bps: float,
    ) -> tuple[dict[str, Any], pd.Series, pd.Series]:
        subset = self._slice(close, start, end)
        position = self._position(subset, spec)
        returns = self._strategy_returns(
            subset,
            position,
            fee_bps=fee_bps,
            slippage_bps=slippage_bps,
        )
        return self._metrics(returns, position), returns, position

    def _block_bootstrap_sharpe(self, returns: pd.Series) -> dict[str, float]:
        values = np.asarray(returns.dropna(), dtype=float)
        if len(values) < 30 or self.bootstrap_samples <= 0:
            return {"samples": 0, "sharpe_p05": 0.0, "sharpe_median": 0.0, "sharpe_p95": 0.0}

        rng = np.random.default_rng(self.seed)
        block = max(3, min(10, int(round(sqrt(len(values))))))
        blocks_needed = ceil(len(values) / block)
        sharpes: list[float] = []

        for _ in range(self.bootstrap_samples):
            sampled: list[float] = []
            for _block_index in range(blocks_needed):
                start = int(rng.integers(0, len(values)))
                indices = (np.arange(start, start + block) % len(values)).astype(int)
                sampled.extend(values[indices].tolist())
            sample = np.asarray(sampled[: len(values)], dtype=float)
            std = float(sample.std(ddof=1)) if len(sample) > 1 else 0.0
            sharpe = float(sample.mean() / std * sqrt(252.0)) if std > 1e-12 else 0.0
            sharpes.append(sharpe)

        return {
            "samples": int(self.bootstrap_samples),
            "block_size": int(block),
            "sharpe_p05": round(float(np.percentile(sharpes, 5)), 4),
            "sharpe_median": round(float(np.percentile(sharpes, 50)), 4),
            "sharpe_p95": round(float(np.percentile(sharpes, 95)), 4),
        }

    def _signflip_p_value(self, returns: pd.Series) -> float:
        values = np.asarray(returns.dropna(), dtype=float)
        if len(values) < 20 or self.signflip_samples <= 0:
            return 1.0
        observed = float(values.mean())
        if observed <= 0:
            return 1.0

        rng = np.random.default_rng(self.seed + 17)
        exceed = 0
        for _ in range(self.signflip_samples):
            signs = rng.choice(np.array([-1.0, 1.0]), size=len(values), replace=True)
            if float((values * signs).mean()) >= observed:
                exceed += 1
        return round((exceed + 1.0) / (self.signflip_samples + 1.0), 6)

    @staticmethod
    def _probabilistic_sharpe(returns: pd.Series, *, trials: int) -> dict[str, float]:
        values = pd.Series(returns, dtype=float).replace([np.inf, -np.inf], np.nan).dropna()
        n = len(values)
        if n < 30:
            return {
                "probabilistic_sharpe": 0.0,
                "trial_adjusted_probability": 0.0,
                "trial_penalty_daily_sharpe": 0.0,
            }

        std = float(values.std(ddof=1))
        if std <= 1e-12:
            return {
                "probabilistic_sharpe": 0.0,
                "trial_adjusted_probability": 0.0,
                "trial_penalty_daily_sharpe": 0.0,
            }

        daily_sr = float(values.mean() / std)
        skew = float(values.skew()) if n > 2 else 0.0
        kurtosis = float(values.kurtosis() + 3.0) if n > 3 else 3.0
        normal = NormalDist()

        def probability(benchmark_sr: float) -> float:
            denominator_sq = 1.0 - skew * daily_sr + ((kurtosis - 1.0) / 4.0) * daily_sr * daily_sr
            denominator = sqrt(max(denominator_sq, 1e-12))
            z = (daily_sr - benchmark_sr) * sqrt(max(n - 1, 1)) / denominator
            return float(normal.cdf(z))

        trial_count = max(1, int(trials))
        # Expected maximum noise Sharpe approximation. The daily-Sharpe standard
        # error under the null is roughly 1/sqrt(T); the extreme-value term grows
        # with the number of candidate strategies screened.
        penalty = sqrt(2.0 * log(max(trial_count, 2))) / sqrt(float(n)) if trial_count > 1 else 0.0
        return {
            "probabilistic_sharpe": round(probability(0.0), 6),
            "trial_adjusted_probability": round(probability(penalty), 6),
            "trial_penalty_daily_sharpe": round(float(penalty), 6),
        }

    def _walk_forward(
        self,
        close: pd.Series,
        spec: CandidateSpec,
        *,
        fee_bps: float,
        slippage_bps: float,
        folds: int = 3,
    ) -> dict[str, Any]:
        n = len(close)
        initial_train = max(100, int(n * 0.50))
        remaining = max(0, n - initial_train)
        block = max(1, remaining // max(1, folds))
        rows: list[dict[str, Any]] = []

        cursor = initial_train
        fold_number = 1
        while cursor < n and fold_number <= folds:
            end = n if fold_number == folds else min(n, cursor + block)
            metrics, _, _ = self._evaluate_slice(
                close,
                spec,
                start=cursor,
                end=end,
                fee_bps=fee_bps,
                slippage_bps=slippage_bps,
            )
            rows.append(
                {
                    "fold": fold_number,
                    "train_bars_available_before_test": cursor,
                    "test_start": close.index[cursor].date().isoformat(),
                    "test_end": close.index[end - 1].date().isoformat(),
                    **metrics,
                }
            )
            cursor = end
            fold_number += 1

        positive = sum(
            1
            for row in rows
            if float(row.get("total_return_pct", 0.0)) > 0
            and float(row.get("sharpe_ratio", 0.0)) > 0
        )
        positive_fraction = positive / len(rows) if rows else 0.0
        return {
            "folds": rows,
            "positive_folds": positive,
            "fold_count": len(rows),
            "positive_fold_fraction": round(positive_fraction, 6),
        }

    def _regime_report(
        self,
        close: pd.Series,
        strategy_returns: pd.Series,
    ) -> dict[str, Any]:
        trend = close.pct_change(60)
        realized_vol = close.pct_change().rolling(20).std(ddof=1) * sqrt(252.0)
        vol_median = float(realized_vol.dropna().median()) if not realized_vol.dropna().empty else 0.0

        trend_label = pd.Series("SIDEWAYS", index=close.index, dtype=object)
        trend_label.loc[trend >= 0.05] = "BULL"
        trend_label.loc[trend <= -0.05] = "BEAR"
        vol_label = pd.Series("NORMAL_VOL", index=close.index, dtype=object)
        if vol_median > 0:
            vol_label.loc[realized_vol > vol_median] = "HIGH_VOL"
        labels = trend_label.astype(str) + "::" + vol_label.astype(str)

        aligned = pd.DataFrame(
            {
                "returns": strategy_returns.reindex(close.index).fillna(0.0),
                "regime": labels,
            }
        ).dropna()

        regimes: dict[str, Any] = {}
        eligible_regimes = 0
        positive_regimes = 0
        for regime, group in aligned.groupby("regime"):
            if len(group) < 10:
                continue
            eligible_regimes += 1
            metrics = self._metrics(group["returns"])
            if float(metrics.get("total_return_pct", 0.0)) > 0:
                positive_regimes += 1
            regimes[str(regime)] = metrics

        stability = positive_regimes / eligible_regimes if eligible_regimes else 0.0
        return {
            "regimes": regimes,
            "eligible_regimes": eligible_regimes,
            "positive_regimes": positive_regimes,
            "positive_regime_fraction": round(stability, 6),
        }

    def _robustness_score(
        self,
        *,
        test_metrics: dict[str, Any],
        bootstrap: dict[str, Any],
        signflip_p: float,
        probabilistic: dict[str, Any],
        walk_forward: dict[str, Any],
        regimes: dict[str, Any],
    ) -> float:
        test_sharpe = self._clip01(float(test_metrics.get("sharpe_ratio", 0.0)) / 1.5)
        bootstrap_floor = self._clip01((float(bootstrap.get("sharpe_p05", -1.0)) + 0.25) / 1.25)
        trial_probability = self._clip01(float(probabilistic.get("trial_adjusted_probability", 0.0)))
        significance = self._clip01(1.0 - float(signflip_p))
        fold_stability = self._clip01(float(walk_forward.get("positive_fold_fraction", 0.0)))
        regime_stability = self._clip01(float(regimes.get("positive_regime_fraction", 0.0)))
        drawdown_resilience = 1.0 - self._clip01(float(test_metrics.get("max_drawdown_pct", 100.0)) / 30.0)

        score = (
            20.0 * test_sharpe
            + 15.0 * bootstrap_floor
            + 15.0 * trial_probability
            + 15.0 * significance
            + 15.0 * fold_stability
            + 10.0 * regime_stability
            + 10.0 * drawdown_resilience
        )
        return round(score, 2)

    @staticmethod
    def _signals_from_position(
        position: pd.Series,
        *,
        confidence: float,
        strategy_id: str,
    ) -> list[dict[str, Any]]:
        signals: list[dict[str, Any]] = []
        previous = 0.0
        for timestamp, raw_value in position.fillna(0.0).items():
            value = 1.0 if raw_value > 0 else -1.0 if raw_value < 0 else 0.0
            if value == previous:
                continue
            if value > 0:
                action = "BUY"
            elif value < 0:
                action = "SELL"
            else:
                action = "EXIT"
            signals.append(
                {
                    "date": timestamp.date().isoformat(),
                    "action": action,
                    "confidence": round(confidence, 4),
                    "source": "systematic_research",
                    "strategy_id": strategy_id,
                }
            )
            previous = value
        return signals

    def discover(
        self,
        df: pd.DataFrame,
        *,
        ticker: str = "",
        fee_bps: float | None = None,
        slippage_bps: float | None = None,
    ) -> dict[str, Any]:
        """Screen candidates and return one challenged strategy plus dated signals."""
        close = self._close_series(df)
        if len(close) < self.min_history:
            return {
                "status": "insufficient_history",
                "ticker": ticker.upper(),
                "bars": int(len(close)),
                "required_bars": int(self.min_history),
                "systematic_gate_passed": False,
                "gate_failures": ["Insufficient history for systematic discovery"],
                "signals": [],
            }

        fee = float(
            fee_bps if fee_bps is not None else getattr(settings, "PAPER_FEE_BPS", 4.0)
        )
        slippage = float(
            slippage_bps
            if slippage_bps is not None
            else getattr(settings, "PAPER_SLIPPAGE_BPS", 5.0)
        )

        n = len(close)
        train_end = max(1, int(n * 0.60))
        validation_end = max(train_end + 1, int(n * 0.80))
        candidates = self._candidate_specs()[: max(1, self.max_candidates)]

        screened: list[dict[str, Any]] = []
        for spec in candidates:
            train_metrics, _, _ = self._evaluate_slice(
                close,
                spec,
                start=0,
                end=train_end,
                fee_bps=fee,
                slippage_bps=slippage,
            )
            screened.append(
                {
                    "spec": spec,
                    "train": train_metrics,
                    "train_score": self._screen_score(train_metrics),
                }
            )

        screened.sort(key=lambda row: row["train_score"], reverse=True)
        finalists = screened[: max(1, min(self.top_k, len(screened)))]

        for row in finalists:
            spec = row["spec"]
            validation_metrics, _, _ = self._evaluate_slice(
                close,
                spec,
                start=train_end,
                end=validation_end,
                fee_bps=fee,
                slippage_bps=slippage,
            )
            row["validation"] = validation_metrics
            row["validation_score"] = self._screen_score(validation_metrics)
            row["selection_score"] = round(
                0.35 * float(row["train_score"])
                + 0.65 * float(row["validation_score"]),
                4,
            )

        finalists.sort(key=lambda row: row["selection_score"], reverse=True)
        winner = finalists[0]
        spec: CandidateSpec = winner["spec"]

        test_metrics, test_returns, _ = self._evaluate_slice(
            close,
            spec,
            start=validation_end,
            end=n,
            fee_bps=fee,
            slippage_bps=slippage,
        )
        full_position = self._position(close, spec)
        full_returns = self._strategy_returns(
            close,
            full_position,
            fee_bps=fee,
            slippage_bps=slippage,
        )
        full_metrics = self._metrics(full_returns, full_position)
        bootstrap = self._block_bootstrap_sharpe(test_returns)
        signflip_p = self._signflip_p_value(test_returns)
        probabilistic = self._probabilistic_sharpe(test_returns, trials=len(candidates))
        walk_forward = self._walk_forward(
            close,
            spec,
            fee_bps=fee,
            slippage_bps=slippage,
        )
        regimes = self._regime_report(close, full_returns)
        robustness_score = self._robustness_score(
            test_metrics=test_metrics,
            bootstrap=bootstrap,
            signflip_p=signflip_p,
            probabilistic=probabilistic,
            walk_forward=walk_forward,
            regimes=regimes,
        )

        failures: list[str] = []
        min_test_sharpe = float(
            getattr(settings, "SYSTEMATIC_RESEARCH_MIN_TEST_SHARPE", 0.25)
        )
        max_drawdown = float(
            getattr(settings, "SYSTEMATIC_RESEARCH_MAX_TEST_DRAWDOWN_PCT", 25.0)
        )
        min_probability = float(
            getattr(settings, "SYSTEMATIC_RESEARCH_MIN_TRIAL_ADJUSTED_PROBABILITY", 0.70)
        )
        max_signflip_p = float(
            getattr(settings, "SYSTEMATIC_RESEARCH_MAX_SIGNFLIP_P_VALUE", 0.20)
        )

        if float(winner["validation"].get("total_return_pct", 0.0)) <= 0:
            failures.append("Validation return is not positive")
        if float(test_metrics.get("total_return_pct", 0.0)) <= 0:
            failures.append("Untouched test return is not positive")
        if float(test_metrics.get("sharpe_ratio", 0.0)) < min_test_sharpe:
            failures.append("Untouched test Sharpe is below threshold")
        if float(test_metrics.get("max_drawdown_pct", 100.0)) > max_drawdown:
            failures.append("Untouched test drawdown is above threshold")
        if float(probabilistic.get("trial_adjusted_probability", 0.0)) < min_probability:
            failures.append("Multiple-testing-adjusted Sharpe probability is too low")
        if signflip_p > max_signflip_p:
            failures.append("Sign-flip null test is not sufficiently significant")
        if float(walk_forward.get("positive_fold_fraction", 0.0)) < 0.50:
            failures.append("Fewer than half of walk-forward folds are positive")
        if robustness_score < self.min_robustness_score:
            failures.append("Composite robustness score is below threshold")

        gate_passed = not failures
        confidence = max(0.65, min(0.95, 0.65 + robustness_score / 333.34))
        signals = self._signals_from_position(
            full_position,
            confidence=confidence,
            strategy_id=spec.strategy_id,
        )

        finalist_summary = [
            {
                "strategy_id": row["spec"].strategy_id,
                "family": row["spec"].family,
                "params": row["spec"].parameter_dict,
                "train_score": row["train_score"],
                "validation_score": row.get("validation_score", 0.0),
                "selection_score": row.get("selection_score", 0.0),
                "train": row["train"],
                "validation": row.get("validation", {}),
            }
            for row in finalists
        ]

        return {
            "status": "ok",
            "ticker": ticker.upper(),
            "strategy_id": spec.strategy_id,
            "family": spec.family,
            "params": spec.parameter_dict,
            "candidate_count": len(candidates),
            "top_k": len(finalists),
            "data_split": {
                "train_bars": train_end,
                "validation_bars": validation_end - train_end,
                "test_bars": n - validation_end,
                "train_end": close.index[train_end - 1].date().isoformat(),
                "validation_end": close.index[validation_end - 1].date().isoformat(),
                "test_end": close.index[-1].date().isoformat(),
            },
            "friction": {"fee_bps": fee, "slippage_bps": slippage},
            "train": winner["train"],
            "validation": winner["validation"],
            "untouched_test": test_metrics,
            "full_history": full_metrics,
            "statistics": {
                "block_bootstrap": bootstrap,
                "signflip_p_value": signflip_p,
                **probabilistic,
            },
            "walk_forward": walk_forward,
            "regime_stability": regimes,
            "robustness_score": robustness_score,
            "minimum_robustness_score": self.min_robustness_score,
            "systematic_gate_passed": gate_passed,
            "gate_failures": failures,
            "finalists": finalist_summary,
            "signals": signals,
        }
