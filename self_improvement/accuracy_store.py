"""AccuracyStore — SQLite-backed aggregate accuracy persistence.

Tracks rolling accuracy by ticker, model, provider, and direction for
long-term model comparison and auto-improvement decisions.
"""

import sqlite3
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

DB_PATH = settings.KNOWLEDGE_DB_PATH


class AccuracyStore:
    """Persists aggregate prediction accuracy keyed by (ticker, model, provider, direction)."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_table()

    def _init_table(self) -> None:
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS accuracy_aggregate (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker      TEXT NOT NULL DEFAULT '',
                    model       TEXT NOT NULL DEFAULT '',
                    provider    TEXT NOT NULL DEFAULT '',
                    direction   TEXT NOT NULL DEFAULT 'NEUTRAL',
                    total_scored INTEGER NOT NULL DEFAULT 0,
                    sum_accuracy REAL NOT NULL DEFAULT 0.0,
                    avg_accuracy REAL NOT NULL DEFAULT 0.0,
                    best_score   REAL NOT NULL DEFAULT 0.0,
                    worst_score  REAL NOT NULL DEFAULT 1.0,
                    last_updated TEXT NOT NULL DEFAULT '',
                    UNIQUE(ticker, model, provider, direction)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_acc_ticker
                ON accuracy_aggregate(ticker)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_acc_provider
                ON accuracy_aggregate(provider)
            """)
            conn.commit()
            conn.close()
            logger.info("AccuracyStore table initialized")
        except Exception as e:
            logger.warning(f"AccuracyStore init warning: {e}")

    def record_outcome(
        self,
        ticker: str,
        model: str,
        provider: str,
        direction: str,
        accuracy: float,
    ) -> None:
        """Upsert a new accuracy data point into the aggregate table."""
        try:
            now = datetime.now(timezone.utc).isoformat()
            conn = sqlite3.connect(self.db_path)
            # Try to fetch existing row
            row = conn.execute(
                """SELECT total_scored, sum_accuracy, best_score, worst_score
                   FROM accuracy_aggregate
                   WHERE ticker=? AND model=? AND provider=? AND direction=?""",
                (ticker, model, provider, direction),
            ).fetchone()

            if row:
                total = row[0] + 1
                new_sum = row[1] + accuracy
                avg = round(new_sum / total, 6)
                best = max(row[2], accuracy)
                worst = min(row[3], accuracy)
                conn.execute(
                    """UPDATE accuracy_aggregate
                       SET total_scored=?, sum_accuracy=?, avg_accuracy=?,
                           best_score=?, worst_score=?, last_updated=?
                       WHERE ticker=? AND model=? AND provider=? AND direction=?""",
                    (total, new_sum, avg, best, worst, now,
                     ticker, model, provider, direction),
                )
            else:
                conn.execute(
                    """INSERT INTO accuracy_aggregate
                       (ticker, model, provider, direction, total_scored,
                        sum_accuracy, avg_accuracy, best_score, worst_score, last_updated)
                       VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?)""",
                    (ticker, model, provider, direction,
                     accuracy, accuracy, accuracy, accuracy, now),
                )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"AccuracyStore record_outcome failed: {e}")

    def get_leaderboard(
        self,
        group_by: str = "ticker",
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Return top performers grouped by the chosen dimension.

        group_by can be 'ticker', 'model', 'provider', or 'direction'.
        """
        valid_columns = {"ticker", "model", "provider", "direction"}
        if group_by not in valid_columns:
            group_by = "ticker"

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"""SELECT {group_by},
                           SUM(total_scored) AS total_scored,
                           ROUND(SUM(sum_accuracy) / MAX(SUM(total_scored), 1), 4) AS avg_accuracy,
                           MAX(best_score)   AS best_score,
                           MIN(worst_score)  AS worst_score,
                           MAX(last_updated) AS last_updated
                    FROM accuracy_aggregate
                    GROUP BY {group_by}
                    HAVING total_scored > 0
                    ORDER BY avg_accuracy DESC
                    LIMIT ?""",
                (limit,),
            ).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.warning(f"AccuracyStore leaderboard failed: {e}")
            return []

    def get_ticker_breakdown(self, ticker: str) -> List[Dict[str, Any]]:
        """Return all rows for a specific ticker."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT * FROM accuracy_aggregate
                   WHERE ticker=?
                   ORDER BY avg_accuracy DESC""",
                (ticker,),
            ).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.warning(f"AccuracyStore ticker_breakdown failed: {e}")
            return []

    def get_summary(self) -> Dict[str, Any]:
        """Global summary stats across all rows."""
        try:
            conn = sqlite3.connect(self.db_path)
            row = conn.execute(
                """SELECT COUNT(DISTINCT ticker)   AS tickers,
                          COUNT(DISTINCT provider) AS providers,
                          COUNT(DISTINCT model)    AS models,
                          SUM(total_scored)         AS total_scored,
                          ROUND(SUM(sum_accuracy) / MAX(SUM(total_scored), 1), 4)
                                                    AS global_avg_accuracy
                   FROM accuracy_aggregate"""
            ).fetchone()
            conn.close()
            if not row:
                return {}
            return {
                "tickers": row[0],
                "providers": row[1],
                "models": row[2],
                "total_scored": row[3] or 0,
                "global_avg_accuracy": row[4] or 0.0,
            }
        except Exception as e:
            logger.warning(f"AccuracyStore summary failed: {e}")
            return {}


# Singleton
accuracy_store = AccuracyStore()

