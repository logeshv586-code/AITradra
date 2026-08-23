"""Immutable, provenance-aware directional evidence for live precision gating.

Research/history accuracy is stored elsewhere. This store contains only evidence
that is eligible to influence autonomous live-entry gating. Legacy precision rows
remain in their old table and are intentionally excluded from v2 statistics.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

_BLOCKED_PROVIDERS = {
    "",
    "none",
    "unknown",
    "default",
    "fallback",
    "cache_stale",
    "stale_cache",
    "knowledge_store",
}


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


class DirectionalPrecisionStore:
    """Store one immutable live-gate evidence row per prediction/model/horizon."""

    TABLE = "directional_precision_evidence_v2"

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or settings.KNOWLEDGE_DB_PATH
        self._init_table()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_table(self) -> None:
        try:
            conn = self._connect()
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self.TABLE} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prediction_id TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    model TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    upstream_provider TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    correct INTEGER NOT NULL,
                    continuous_accuracy REAL NOT NULL DEFAULT 0.0,
                    prediction_timestamp TEXT NOT NULL,
                    horizon_hours REAL NOT NULL,
                    evaluated_at TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    scored_at TEXT NOT NULL,
                    live_gate_eligible INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    UNIQUE(prediction_id, model, horizon_hours)
                )
                """
            )
            conn.execute(
                f"""
                CREATE INDEX IF NOT EXISTS idx_precision_v2_lookup
                ON {self.TABLE}
                    (ticker, model, direction, live_gate_eligible, evaluated_at)
                """
            )
            conn.commit()
            conn.close()
        except Exception as exc:
            logger.warning("DirectionalPrecisionStore v2 init failed: %s", exc)

    @staticmethod
    def _effective_provider(provider: str, upstream_provider: str) -> str:
        raw = str(provider or "").strip().lower()
        upstream = str(upstream_provider or "").strip()
        if raw == "cache":
            return upstream
        return str(provider or "").strip()

    def record_outcome(
        self,
        *,
        prediction_id: str,
        ticker: str,
        model: str,
        provider: str,
        upstream_provider: str,
        direction: str,
        correct: bool,
        continuous_accuracy: float,
        prediction_timestamp: str,
        horizon_hours: float,
        evaluated_at: str,
        observed_at: str,
        live_gate_eligible: bool,
        scored_at: str | None = None,
    ) -> bool:
        """Insert immutable, independently valid live-gate evidence.

        The store re-validates chronology and provenance rather than trusting a
        caller-provided eligibility flag. Returns True only when a new compliant
        row is inserted.
        """
        normalized_direction = str(direction or "").upper()
        if normalized_direction not in {"BULLISH", "BEARISH"}:
            return False
        if not live_gate_eligible or not prediction_id or not ticker or not model:
            return False

        prediction_dt = _parse_timestamp(prediction_timestamp)
        evaluated_dt = _parse_timestamp(evaluated_at)
        observed_dt = _parse_timestamp(observed_at)
        try:
            horizon = float(horizon_hours)
        except (TypeError, ValueError):
            return False

        effective_provider = self._effective_provider(provider, upstream_provider)
        if (
            prediction_dt is None
            or evaluated_dt is None
            or observed_dt is None
            or horizon < 0
            or effective_provider.lower() in _BLOCKED_PROVIDERS
        ):
            return False

        horizon_end = prediction_dt + timedelta(hours=horizon)
        if evaluated_dt < horizon_end or observed_dt < horizon_end:
            return False
        if observed_dt > evaluated_dt + timedelta(minutes=5):
            return False

        scored_at = scored_at or evaluated_at
        scored_dt = _parse_timestamp(scored_at)
        if scored_dt is None or scored_dt < horizon_end:
            return False

        created_at = datetime.now(timezone.utc).isoformat()
        try:
            conn = self._connect()
            before = conn.total_changes
            conn.execute(
                f"""
                INSERT INTO {self.TABLE}
                    (prediction_id, ticker, model, provider, upstream_provider,
                     direction, correct, continuous_accuracy,
                     prediction_timestamp, horizon_hours, evaluated_at,
                     observed_at, scored_at, live_gate_eligible, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                ON CONFLICT(prediction_id, model, horizon_hours) DO NOTHING
                """,
                (
                    str(prediction_id),
                    str(ticker).upper(),
                    str(model),
                    str(provider or ""),
                    str(upstream_provider or effective_provider),
                    normalized_direction,
                    1 if correct else 0,
                    max(0.0, min(float(continuous_accuracy or 0.0), 1.0)),
                    prediction_dt.isoformat(),
                    horizon,
                    evaluated_dt.isoformat(),
                    observed_dt.isoformat(),
                    scored_dt.isoformat(),
                    created_at,
                ),
            )
            inserted = conn.total_changes > before
            conn.commit()
            conn.close()
            return inserted
        except Exception as exc:
            logger.warning("DirectionalPrecisionStore v2 record failed: %s", exc)
            return False

    def get_precision_stats(
        self,
        *,
        ticker: str,
        model: str | None = None,
        direction: str | None = None,
        lookback_days: int = 90,
    ) -> dict[str, Any]:
        clauses = [
            "ticker = ?",
            "live_gate_eligible = 1",
            "datetime(evaluated_at) >= datetime('now', ?)",
        ]
        params: list[Any] = [
            str(ticker).upper(),
            f"-{max(1, int(lookback_days))} days",
        ]
        if model:
            clauses.append("model = ?")
            params.append(str(model))
        if direction:
            normalized = str(direction).upper()
            if normalized in {"BUY", "LONG"}:
                normalized = "BULLISH"
            elif normalized in {"SELL", "SHORT"}:
                normalized = "BEARISH"
            clauses.append("direction = ?")
            params.append(normalized)

        try:
            conn = self._connect()
            row = conn.execute(
                f"""
                SELECT COUNT(*) AS total_directional,
                       COALESCE(SUM(correct), 0) AS correct_scored,
                       COALESCE(AVG(continuous_accuracy), 0.0)
                           AS avg_continuous_accuracy,
                       MAX(evaluated_at) AS last_updated
                FROM {self.TABLE}
                WHERE {' AND '.join(clauses)}
                """,
                params,
            ).fetchone()
            conn.close()
            if not row:
                return {
                    "total_directional": 0,
                    "correct_scored": 0,
                    "avg_continuous_accuracy": 0.0,
                    "last_updated": None,
                }
            return dict(row)
        except Exception as exc:
            logger.warning("DirectionalPrecisionStore v2 query failed: %s", exc)
            return {
                "total_directional": 0,
                "correct_scored": 0,
                "avg_continuous_accuracy": 0.0,
                "last_updated": None,
            }

    def export_evidence(
        self,
        *,
        ticker: str | None = None,
        model: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """Return audit-ready immutable evidence rows."""
        clauses = ["live_gate_eligible = 1"]
        params: list[Any] = []
        if ticker:
            clauses.append("ticker = ?")
            params.append(str(ticker).upper())
        if model:
            clauses.append("model = ?")
            params.append(str(model))
        params.append(max(1, min(int(limit), 10_000)))

        try:
            conn = self._connect()
            rows = conn.execute(
                f"""
                SELECT prediction_id, ticker, model, provider,
                       upstream_provider, direction, correct,
                       continuous_accuracy, prediction_timestamp,
                       horizon_hours, evaluated_at, observed_at, scored_at
                FROM {self.TABLE}
                WHERE {' AND '.join(clauses)}
                ORDER BY datetime(evaluated_at) DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as exc:
            logger.warning("DirectionalPrecisionStore v2 export failed: %s", exc)
            return []


precision_store = DirectionalPrecisionStore()
