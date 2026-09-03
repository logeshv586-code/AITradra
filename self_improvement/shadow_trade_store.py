"""Append-only shadow paper decision ledger.

Shadow decisions collect forward evidence before any autonomous funded trade is
eligible. They never authorize execution. Each row is chained with SHA-256 so
later edits are detectable. Resolutions append outcome fields through a separate
resolution table rather than mutating the original decision payload.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core.config import BASE_DIR, settings


DEFAULT_DB_PATH = BASE_DIR / "data" / "shadow_trading.sqlite3"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


class ShadowTradeStore:
    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS shadow_decisions (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    strategy_id TEXT NOT NULL,
                    horizon_hours REAL NOT NULL,
                    evidence_json TEXT NOT NULL,
                    plugins_json TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    row_hash TEXT NOT NULL UNIQUE
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS shadow_resolutions (
                    decision_id TEXT PRIMARY KEY,
                    resolved_at TEXT NOT NULL,
                    exit_price REAL NOT NULL,
                    return_pct REAL NOT NULL,
                    actual_direction TEXT NOT NULL,
                    correct INTEGER NOT NULL,
                    price_source TEXT NOT NULL,
                    resolution_hash TEXT NOT NULL,
                    FOREIGN KEY(decision_id) REFERENCES shadow_decisions(id)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_shadow_ticker_time ON shadow_decisions(ticker, created_at DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_shadow_created ON shadow_decisions(created_at)"
            )

    def _last_hash(self) -> str:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT row_hash FROM shadow_decisions ORDER BY rowid DESC LIMIT 1"
            ).fetchone()
        return str(row["row_hash"]) if row else "GENESIS"

    def record_decision(
        self,
        *,
        ticker: str,
        direction: str,
        confidence: float,
        entry_price: float,
        strategy_id: str = "SignalAggregatorAgent",
        horizon_hours: float | None = None,
        evidence: dict[str, Any] | None = None,
        plugins: dict[str, Any] | None = None,
        created_at: str | None = None,
        decision_id: str | None = None,
    ) -> dict[str, Any]:
        direction = str(direction).upper()
        if direction not in {"BUY", "SELL", "BULLISH", "BEARISH", "LONG", "SHORT"}:
            raise ValueError("Shadow decisions must be directional")
        entry = float(entry_price)
        if entry <= 0:
            raise ValueError("Shadow decision entry price must be positive")
        conf = float(confidence)
        if conf > 1.0:
            conf /= 100.0
        conf = max(0.0, min(1.0, conf))
        horizon = float(
            horizon_hours
            if horizon_hours is not None
            else getattr(settings, "PREDICTION_SCORE_DELAY_HOURS", 24)
        )
        created = created_at or _now()
        if _parse_time(created) is None:
            raise ValueError("Invalid shadow decision timestamp")
        decision_id = decision_id or uuid.uuid4().hex
        previous_hash = self._last_hash()
        immutable = {
            "id": decision_id,
            "created_at": created,
            "ticker": str(ticker).upper(),
            "direction": direction,
            "confidence": round(conf, 8),
            "entry_price": round(entry, 12),
            "strategy_id": str(strategy_id),
            "horizon_hours": round(max(0.0, horizon), 6),
            "evidence": evidence or {},
            "plugins": plugins or {},
            "previous_hash": previous_hash,
        }
        row_hash = hashlib.sha256(_canonical(immutable).encode("utf-8")).hexdigest()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO shadow_decisions (
                    id, created_at, ticker, direction, confidence, entry_price,
                    strategy_id, horizon_hours, evidence_json, plugins_json,
                    previous_hash, row_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision_id,
                    created,
                    immutable["ticker"],
                    direction,
                    conf,
                    entry,
                    str(strategy_id),
                    max(0.0, horizon),
                    _canonical(evidence or {}),
                    _canonical(plugins or {}),
                    previous_hash,
                    row_hash,
                ),
            )
        return {**immutable, "row_hash": row_hash, "execution_authority": False}

    def pending_due(self, *, now: datetime | None = None, limit: int = 200) -> list[dict[str, Any]]:
        current = now or datetime.now(timezone.utc)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT d.* FROM shadow_decisions d
                LEFT JOIN shadow_resolutions r ON r.decision_id = d.id
                WHERE r.decision_id IS NULL
                ORDER BY d.created_at ASC
                LIMIT ?
                """,
                (max(1, min(int(limit), 1000)),),
            ).fetchall()
        due = []
        for row in rows:
            created = _parse_time(row["created_at"])
            if created is None:
                continue
            if current < created + timedelta(hours=float(row["horizon_hours"])):
                continue
            due.append(self._row_to_dict(row))
        return due

    def resolve(
        self,
        decision_id: str,
        *,
        exit_price: float,
        price_source: str,
        resolved_at: str | None = None,
    ) -> dict[str, Any]:
        exit_value = float(exit_price)
        if exit_value <= 0:
            raise ValueError("Shadow exit price must be positive")
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM shadow_decisions WHERE id = ?", (decision_id,)
            ).fetchone()
            if row is None:
                raise KeyError(decision_id)
            existing = conn.execute(
                "SELECT * FROM shadow_resolutions WHERE decision_id = ?", (decision_id,)
            ).fetchone()
            if existing is not None:
                return self._resolution_to_dict(existing)

            entry = float(row["entry_price"])
            direction = str(row["direction"]).upper()
            bullish = direction in {"BUY", "BULLISH", "LONG"}
            raw_return = (exit_value - entry) / entry
            directional_return = raw_return if bullish else -raw_return
            actual_direction = "UP" if raw_return > 0 else "DOWN" if raw_return < 0 else "FLAT"
            correct = directional_return > 0
            resolved = resolved_at or _now()
            payload = {
                "decision_id": decision_id,
                "resolved_at": resolved,
                "exit_price": round(exit_value, 12),
                "return_pct": round(directional_return * 100.0, 8),
                "actual_direction": actual_direction,
                "correct": bool(correct),
                "price_source": str(price_source or "unknown"),
                "decision_hash": row["row_hash"],
            }
            resolution_hash = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()
            conn.execute(
                """
                INSERT INTO shadow_resolutions (
                    decision_id, resolved_at, exit_price, return_pct,
                    actual_direction, correct, price_source, resolution_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision_id,
                    resolved,
                    exit_value,
                    payload["return_pct"],
                    actual_direction,
                    1 if correct else 0,
                    str(price_source or "unknown"),
                    resolution_hash,
                ),
            )
        return {**payload, "resolution_hash": resolution_hash, "execution_authority": False}

    def resolved_decisions(self, *, ticker: str | None = None, limit: int = 1000) -> list[dict[str, Any]]:
        query = """
            SELECT d.*, r.resolved_at, r.exit_price, r.return_pct,
                   r.actual_direction, r.correct, r.price_source, r.resolution_hash
            FROM shadow_decisions d
            JOIN shadow_resolutions r ON r.decision_id = d.id
        """
        params: list[Any] = []
        if ticker:
            query += " WHERE d.ticker = ?"
            params.append(str(ticker).upper())
        query += " ORDER BY d.created_at DESC LIMIT ?"
        params.append(max(1, min(int(limit), 5000)))
        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [self._joined_to_dict(row) for row in rows]

    def stats(self, *, ticker: str | None = None) -> dict[str, Any]:
        rows = self.resolved_decisions(ticker=ticker, limit=5000)
        total = len(rows)
        correct = sum(1 for row in rows if row.get("correct"))
        avg_return = sum(float(row.get("return_pct", 0.0)) for row in rows) / total if total else 0.0
        return {
            "ticker": str(ticker).upper() if ticker else None,
            "resolved": total,
            "correct": correct,
            "directional_hit_rate": round(correct / total, 6) if total else 0.0,
            "average_directional_return_pct": round(avg_return, 6),
            "execution_authority": False,
        }

    def audit_chain(self) -> dict[str, Any]:
        previous = "GENESIS"
        checked = 0
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM shadow_decisions ORDER BY rowid ASC").fetchall()
        for row in rows:
            payload = {
                "id": row["id"],
                "created_at": row["created_at"],
                "ticker": row["ticker"],
                "direction": row["direction"],
                "confidence": round(float(row["confidence"]), 8),
                "entry_price": round(float(row["entry_price"]), 12),
                "strategy_id": row["strategy_id"],
                "horizon_hours": round(float(row["horizon_hours"]), 6),
                "evidence": json.loads(row["evidence_json"] or "{}"),
                "plugins": json.loads(row["plugins_json"] or "{}"),
                "previous_hash": row["previous_hash"],
            }
            expected = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()
            if row["previous_hash"] != previous or row["row_hash"] != expected:
                return {
                    "valid": False,
                    "checked": checked,
                    "failed_id": row["id"],
                    "reason": "Shadow decision hash chain mismatch",
                }
            previous = row["row_hash"]
            checked += 1
        return {"valid": True, "checked": checked, "head_hash": previous}

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "created_at": row["created_at"],
            "ticker": row["ticker"],
            "direction": row["direction"],
            "confidence": float(row["confidence"]),
            "entry_price": float(row["entry_price"]),
            "strategy_id": row["strategy_id"],
            "horizon_hours": float(row["horizon_hours"]),
            "evidence": json.loads(row["evidence_json"] or "{}"),
            "plugins": json.loads(row["plugins_json"] or "{}"),
            "row_hash": row["row_hash"],
        }

    @staticmethod
    def _resolution_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "decision_id": row["decision_id"],
            "resolved_at": row["resolved_at"],
            "exit_price": float(row["exit_price"]),
            "return_pct": float(row["return_pct"]),
            "actual_direction": row["actual_direction"],
            "correct": bool(row["correct"]),
            "price_source": row["price_source"],
            "resolution_hash": row["resolution_hash"],
            "execution_authority": False,
        }

    @classmethod
    def _joined_to_dict(cls, row: sqlite3.Row) -> dict[str, Any]:
        base = cls._row_to_dict(row)
        base.update(
            {
                "resolved_at": row["resolved_at"],
                "exit_price": float(row["exit_price"]),
                "return_pct": float(row["return_pct"]),
                "actual_direction": row["actual_direction"],
                "actual_up": str(row["actual_direction"]).upper() == "UP",
                "correct": bool(row["correct"]),
                "price_source": row["price_source"],
                "resolution_hash": row["resolution_hash"],
                "plugin_snapshot": base.get("plugins", {}),
            }
        )
        return base


shadow_trade_store = ShadowTradeStore()
