"""Local customer runtime state for AITradra.

The app intentionally keeps a single default history user so the customer UI can
remember research and trading activity without introducing an authentication
system. API/broker credentials are not tied to that history user; they are
machine-local connections and are encrypted at rest.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from core.config import BASE_DIR
from core.logger import get_logger

logger = get_logger(__name__)

DEFAULT_HISTORY_USER = "default"
DB_PATH = BASE_DIR / "data" / "customer_runtime.sqlite3"
KEY_PATH = BASE_DIR / "data" / ".customer_runtime.key"


class CustomerRuntimeStore:
    """Encrypted local connection registry plus lightweight customer history."""

    def __init__(self, db_path: Path = DB_PATH, key_path: Path = KEY_PATH):
        self.db_path = db_path
        self.key_path = key_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._fernet = Fernet(self._load_or_create_key())
        self._init_db()

    def _load_or_create_key(self) -> bytes:
        if self.key_path.exists():
            return self.key_path.read_bytes().strip()
        key = Fernet.generate_key()
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        self.key_path.write_bytes(key)
        try:
            os.chmod(self.key_path, 0o600)
        except OSError:
            pass
        return key

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS connections (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    config_json TEXT NOT NULL DEFAULT '{}',
                    secret_blob TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS history (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    ticker TEXT,
                    title TEXT NOT NULL,
                    details_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_history_user_time ON history(user_id, created_at DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_history_ticker ON history(ticker, created_at DESC)")

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _encrypt(self, payload: dict[str, Any]) -> str:
        return self._fernet.encrypt(json.dumps(payload or {}).encode("utf-8")).decode("utf-8")

    def _decrypt(self, blob: str) -> dict[str, Any]:
        if not blob:
            return {}
        try:
            raw = self._fernet.decrypt(blob.encode("utf-8"))
            payload = json.loads(raw.decode("utf-8"))
            return payload if isinstance(payload, dict) else {}
        except (InvalidToken, ValueError, TypeError, json.JSONDecodeError) as exc:
            logger.warning(f"Could not decrypt customer connection secret: {exc}")
            return {}

    def save_connection(
        self,
        *,
        name: str,
        category: str,
        provider: str,
        config: dict[str, Any] | None = None,
        secrets: dict[str, Any] | None = None,
        enabled: bool = True,
        connection_id: str | None = None,
    ) -> dict[str, Any]:
        connection_id = connection_id or uuid.uuid4().hex
        now = self._now()
        config = config or {}
        secrets = {k: v for k, v in (secrets or {}).items() if v not in (None, "")}
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT created_at, secret_blob FROM connections WHERE id = ?", (connection_id,)
            ).fetchone()
            created_at = existing["created_at"] if existing else now
            secret_blob = self._encrypt(secrets) if secrets else (existing["secret_blob"] if existing else self._encrypt({}))
            conn.execute(
                """
                INSERT INTO connections (
                    id, name, category, provider, enabled, config_json,
                    secret_blob, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    category=excluded.category,
                    provider=excluded.provider,
                    enabled=excluded.enabled,
                    config_json=excluded.config_json,
                    secret_blob=excluded.secret_blob,
                    updated_at=excluded.updated_at
                """,
                (
                    connection_id, name.strip(), category.strip().lower(), provider.strip().lower(),
                    1 if enabled else 0, json.dumps(config), secret_blob, created_at, now,
                ),
            )
        return self.get_connection(connection_id, include_secrets=False) or {}

    def list_connections(self, category: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM connections"
        params: tuple[Any, ...] = ()
        if category:
            query += " WHERE category = ?"
            params = (category.lower(),)
        query += " ORDER BY updated_at DESC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._public_connection(row) for row in rows]

    def get_connection(self, connection_id: str, include_secrets: bool = False) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM connections WHERE id = ?", (connection_id,)).fetchone()
        if row is None:
            return None
        payload = self._public_connection(row)
        if include_secrets:
            payload["secrets"] = self._decrypt(row["secret_blob"])
        return payload

    def enabled_connections(self, category: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM connections WHERE enabled = 1"
        params: tuple[Any, ...] = ()
        if category:
            query += " AND category = ?"
            params = (category.lower(),)
        query += " ORDER BY updated_at DESC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        results = []
        for row in rows:
            item = self._public_connection(row)
            item["secrets"] = self._decrypt(row["secret_blob"])
            results.append(item)
        return results

    def delete_connection(self, connection_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM connections WHERE id = ?", (connection_id,))
        return cursor.rowcount > 0

    def _public_connection(self, row: sqlite3.Row) -> dict[str, Any]:
        try:
            config = json.loads(row["config_json"] or "{}")
        except json.JSONDecodeError:
            config = {}
        secret_values = self._decrypt(row["secret_blob"])
        return {
            "id": row["id"], "name": row["name"], "category": row["category"],
            "provider": row["provider"], "enabled": bool(row["enabled"]),
            "config": config, "has_credentials": bool(secret_values),
            "created_at": row["created_at"], "updated_at": row["updated_at"],
        }

    def record_history(
        self,
        *,
        event_type: str,
        title: str,
        ticker: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event_id = uuid.uuid4().hex
        created_at = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO history (id, user_id, event_type, ticker, title, details_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (event_id, DEFAULT_HISTORY_USER, event_type, ticker.upper() if ticker else None,
                 title, json.dumps(details or {}), created_at),
            )
        return {
            "id": event_id, "user_id": DEFAULT_HISTORY_USER, "event_type": event_type,
            "ticker": ticker.upper() if ticker else None, "title": title,
            "details": details or {}, "created_at": created_at,
        }

    def get_history(self, *, limit: int = 50, ticker: str | None = None) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 200))
        query = "SELECT * FROM history WHERE user_id = ?"
        params: list[Any] = [DEFAULT_HISTORY_USER]
        if ticker:
            query += " AND ticker = ?"
            params.append(ticker.upper())
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        results = []
        for row in rows:
            try:
                details = json.loads(row["details_json"] or "{}")
            except json.JSONDecodeError:
                details = {}
            results.append({
                "id": row["id"], "user_id": row["user_id"], "event_type": row["event_type"],
                "ticker": row["ticker"], "title": row["title"], "details": details,
                "created_at": row["created_at"],
            })
        return results


customer_runtime = CustomerRuntimeStore()
