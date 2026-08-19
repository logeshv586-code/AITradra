"""DirectionalPrecisionStore — resolved prediction evidence for live precision gating.

Stores one row per resolved directional prediction.  This intentionally keeps
binary direction correctness separate from the existing continuous accuracy
score so a live-trading precision target cannot be satisfied by averaging
partial-credit scores.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)


class DirectionalPrecisionStore:
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
                """
                CREATE TABLE IF NOT EXISTS directional_precision_outcomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prediction_id TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    model TEXT NOT NULL,
                    provider TEXT NOT NULL DEFAULT '',
                    direction TEXT NOT NULL,
                    correct INTEGER NOT NULL,
                    continuous_accuracy REAL NOT NULL DEFAULT 0.0,
                    scored_at TEXT NOT NULL,
                    UNIQUE(prediction_id, model)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_precision_lookup
                ON directional_precision_outcomes(ticker, model, direction, scored_at)
                """
            )
            conn.commit()
            conn.close()
        except Exception as exc:
            logger.warning("DirectionalPrecisionStore init failed: %s", exc)

    def record_outcome(
        self,
        *,
        prediction_id: str,
        ticker: str,
        model: str,
        provider: str,
        direction: str,
        correct: bool,
        continuous_accuracy: float,
        scored_at: str | None = None,
    ) -> None:
        direction = str(direction or "").upper()
        if direction not in {"BULLISH", "BEARISH"}:
            return
        if not prediction_id or not ticker or not model:
            return
        scored_at = scored_at or datetime.now(timezone.utc).isoformat()
        try:
            conn = self._connect()
            conn.execute(
                """
                INSERT INTO directional_precision_outcomes
                    (prediction_id, ticker, model, provider, direction, correct,
                     continuous_accuracy, scored_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(prediction_id, model) DO UPDATE SET
                    ticker=excluded.ticker,
                    provider=excluded.provider,
                    direction=excluded.direction,
                    correct=excluded.correct,
                    continuous_accuracy=excluded.continuous_accuracy,
                    scored_at=excluded.scored_at
                """,
                (
                    str(prediction_id),
                    str(ticker).upper(),
                    str(model),
                    str(provider or "unknown"),
                    direction,
                    1 if correct else 0,
                    max(0.0, min(float(continuous_accuracy or 0.0), 1.0)),
                    scored_at,
                ),
            )
            conn.commit()
            conn.close()
        except Exception as exc:
            logger.warning("DirectionalPrecisionStore record failed: %s", exc)

    def get_precision_stats(
        self,
        *,
        ticker: str,
        model: str | None = None,
        direction: str | None = None,
        lookback_days: int = 90,
    ) -> dict[str, Any]:
        clauses = ["ticker = ?", "scored_at >= datetime('now', ?)"]
        params: list[Any] = [str(ticker).upper(), f"-{max(1, int(lookback_days))} days"]
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
                       COALESCE(AVG(continuous_accuracy), 0.0) AS avg_continuous_accuracy,
                       MAX(scored_at) AS last_updated
                FROM directional_precision_outcomes
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
            logger.warning("DirectionalPrecisionStore query failed: %s", exc)
            return {
                "total_directional": 0,
                "correct_scored": 0,
                "avg_continuous_accuracy": 0.0,
                "last_updated": None,
            }


precision_store = DirectionalPrecisionStore()
