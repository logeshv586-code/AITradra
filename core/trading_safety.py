"""Centralized execution safety, daily-loss tracking, and strategy validation.

This module is intentionally dependency-light so the same guardrails can be used by
brokers, schedulers, tests, and customer-facing status endpoints.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from core.config import BASE_DIR, settings
from core.logger import get_logger

logger = get_logger(__name__)

LIVE_ACK_PHRASE = "I_UNDERSTAND_LIVE_TRADING"


def get_execution_status(settings_obj=settings) -> dict[str, Any]:
    """Return the single authoritative paper/live execution state.

    Live execution is fail-closed. A private key by itself is never enough to place
    real orders. All live prerequisites must be explicitly satisfied.
    """

    paper_requested = bool(settings_obj.PAPER_TRADE_MODE)
    automation_enabled = bool(settings_obj.AUTOTRADE_ENABLED)
    has_private_key = bool(settings_obj.HYPERLIQUID_PRIVATE_KEY)
    live_acknowledged = settings_obj.LIVE_TRADING_ACK == LIVE_ACK_PHRASE
    protective_orders_required = bool(settings_obj.REQUIRE_PROTECTIVE_ORDERS)

    blockers: list[str] = []
    if paper_requested:
        blockers.append("PAPER_TRADE_MODE is enabled")
    if not automation_enabled:
        blockers.append("AUTOTRADE_ENABLED is disabled")
    if not has_private_key:
        blockers.append("Hyperliquid private key is not configured")
    if not live_acknowledged:
        blockers.append("Live-trading acknowledgement is not configured")
    if not protective_orders_required:
        blockers.append("Protective-order enforcement must remain enabled for live mode")

    live_allowed = (
        not paper_requested
        and automation_enabled
        and has_private_key
        and live_acknowledged
        and protective_orders_required
    )

    return {
        "mode": "live" if live_allowed else "paper",
        "paper_mode": not live_allowed,
        "live_execution_allowed": live_allowed,
        "automation_enabled": automation_enabled,
        "protective_orders_required": protective_orders_required,
        "strategy_validation_required": bool(settings_obj.REQUIRE_STRATEGY_VALIDATION),
        "blockers": blockers,
    }


def normalize_candles_latest_first(candles: Iterable[dict]) -> list[dict]:
    """Normalize OHLCV bars to the ordering expected by signal/scoring agents.

    Hyperliquid returns chronological candles in practice while the signal stack uses
    index 0 as the latest bar. Sorting here makes that contract explicit.
    """

    rows = [dict(row) for row in candles if isinstance(row, dict)]

    def _timestamp(row: dict) -> float:
        raw = row.get("timestamp", row.get("t", row.get("time", 0)))
        try:
            return float(raw)
        except (TypeError, ValueError):
            return 0.0

    return sorted(rows, key=_timestamp, reverse=True)


@dataclass
class DailyEquityTracker:
    """Persist a UTC day-start equity baseline for the daily loss circuit breaker."""

    path: Path = BASE_DIR / "data" / "trading_daily_equity.json"

    def _load(self) -> dict[str, Any]:
        try:
            if self.path.exists():
                return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning(f"Unable to read daily equity state: {exc}")
        return {}

    def _save(self, payload: dict[str, Any]) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.warning(f"Unable to persist daily equity state: {exc}")

    def update(self, current_equity: float) -> float:
        """Return daily P&L as a decimal fraction, e.g. -0.02 for -2%."""

        try:
            equity = float(current_equity or 0)
        except (TypeError, ValueError):
            return 0.0
        if equity <= 0:
            return 0.0

        today = datetime.now(timezone.utc).date().isoformat()
        state = self._load()
        baseline = float(state.get("baseline_equity", 0) or 0)

        if state.get("date") != today or baseline <= 0:
            baseline = equity
            state = {"date": today, "baseline_equity": baseline, "last_equity": equity}
            self._save(state)
            return 0.0

        state["last_equity"] = equity
        self._save(state)
        return (equity - baseline) / baseline


class StrategyValidationStore:
    """Small JSON registry that makes backtest approval an enforceable live gate."""

    def __init__(self, path: Path | None = None):
        self.path = path or (BASE_DIR / "data" / "strategy_validation.json")

    def _load(self) -> dict[str, Any]:
        try:
            if self.path.exists():
                payload = json.loads(self.path.read_text(encoding="utf-8"))
                return payload if isinstance(payload, dict) else {}
        except Exception as exc:
            logger.warning(f"Unable to read strategy validation state: {exc}")
        return {}

    def _save(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @staticmethod
    def _key(ticker: str, strategy_id: str) -> str:
        return f"{ticker.upper()}::{strategy_id}"

    def record(
        self,
        ticker: str,
        strategy_id: str,
        metrics: dict[str, Any],
        approved: bool,
        out_of_sample_passed: bool,
    ) -> dict[str, Any]:
        state = self._load()
        record = {
            "ticker": ticker.upper(),
            "strategy_id": strategy_id,
            "approved": bool(approved),
            "out_of_sample_passed": bool(out_of_sample_passed),
            "validated_at": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics,
        }
        state[self._key(ticker, strategy_id)] = record
        self._save(state)
        return record

    def check(self, ticker: str, strategy_id: str) -> dict[str, Any]:
        if not settings.REQUIRE_STRATEGY_VALIDATION:
            return {"eligible": True, "reasons": [], "record": None}

        record = self._load().get(self._key(ticker, strategy_id))
        if not record:
            return {
                "eligible": False,
                "reasons": ["No approved out-of-sample backtest is registered for this strategy"],
                "record": None,
            }

        reasons: list[str] = []
        metrics = record.get("metrics", {}) if isinstance(record.get("metrics"), dict) else {}
        if not record.get("approved"):
            reasons.append("Latest backtest is not approved")
        if not record.get("out_of_sample_passed"):
            reasons.append("Out-of-sample validation did not pass")

        validated_at = record.get("validated_at")
        try:
            age_days = (
                datetime.now(timezone.utc) - datetime.fromisoformat(validated_at)
            ).total_seconds() / 86400
            if age_days > settings.STRATEGY_VALIDATION_MAX_AGE_DAYS:
                reasons.append("Backtest validation is stale")
        except Exception:
            reasons.append("Backtest validation timestamp is invalid")

        if float(metrics.get("sharpe_ratio", 0) or 0) < settings.MIN_BACKTEST_SHARPE:
            reasons.append("Sharpe ratio is below the live threshold")
        if float(metrics.get("max_drawdown_pct", 100) or 100) > settings.MAX_BACKTEST_DRAWDOWN_PCT:
            reasons.append("Maximum drawdown exceeds the live threshold")
        if float(metrics.get("win_rate", 0) or 0) < settings.MIN_BACKTEST_WIN_RATE:
            reasons.append("Win rate is below the live threshold")
        if int(metrics.get("total_trades", 0) or 0) < settings.MIN_BACKTEST_TRADES:
            reasons.append("Backtest trade count is too small")
        if float(metrics.get("profit_factor", 0) or 0) < settings.MIN_BACKTEST_PROFIT_FACTOR:
            reasons.append("Profit factor is below the live threshold")

        return {"eligible": not reasons, "reasons": reasons, "record": record}


strategy_validation_store = StrategyValidationStore()
