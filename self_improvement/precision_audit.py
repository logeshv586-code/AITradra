"""Tamper-evident append-only audit chain for live precision evidence.

The directional evidence table is already insert-only through the application API.
This module adds a SHA-256 hash chain over canonical evidence rows so accidental or
manual database edits can be detected before evidence is trusted for live trading.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any

AUDIT_TABLE = "directional_precision_audit_v1"
GENESIS = "0" * 64


def canonical_payload(row: dict[str, Any]) -> str:
    keep = {
        key: row.get(key)
        for key in (
            "prediction_id", "ticker", "model", "provider", "upstream_provider",
            "direction", "correct", "continuous_accuracy", "prediction_timestamp",
            "horizon_hours", "evaluated_at", "observed_at", "scored_at",
            "live_gate_eligible", "created_at",
        )
    }
    return json.dumps(keep, sort_keys=True, separators=(",", ":"), default=str)


def digest(previous_hash: str, payload: str) -> str:
    return hashlib.sha256(f"{previous_hash}|{payload}".encode("utf-8")).hexdigest()


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {AUDIT_TABLE} (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            evidence_id INTEGER NOT NULL UNIQUE,
            previous_hash TEXT NOT NULL,
            evidence_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(evidence_id) REFERENCES directional_precision_evidence_v2(id)
        )
        """
    )


def append_evidence(conn: sqlite3.Connection, evidence_id: int, row: dict[str, Any]) -> str:
    ensure_schema(conn)
    existing = conn.execute(
        f"SELECT evidence_hash FROM {AUDIT_TABLE} WHERE evidence_id = ?",
        (int(evidence_id),),
    ).fetchone()
    if existing:
        return str(existing[0])
    previous = conn.execute(
        f"SELECT evidence_hash FROM {AUDIT_TABLE} ORDER BY sequence DESC LIMIT 1"
    ).fetchone()
    previous_hash = str(previous[0]) if previous else GENESIS
    evidence_hash = digest(previous_hash, canonical_payload(row))
    conn.execute(
        f"""
        INSERT INTO {AUDIT_TABLE} (evidence_id, previous_hash, evidence_hash, created_at)
        VALUES (?, ?, ?, datetime('now'))
        """,
        (int(evidence_id), previous_hash, evidence_hash),
    )
    return evidence_hash


def verify_chain(conn: sqlite3.Connection, evidence_table: str) -> dict[str, Any]:
    ensure_schema(conn)
    audit_rows = conn.execute(
        f"SELECT sequence, evidence_id, previous_hash, evidence_hash FROM {AUDIT_TABLE} ORDER BY sequence ASC"
    ).fetchall()
    if not audit_rows:
        evidence_count = conn.execute(f"SELECT COUNT(*) FROM {evidence_table}").fetchone()[0]
        return {
            "valid": evidence_count == 0,
            "audited_rows": 0,
            "evidence_rows": int(evidence_count),
            "reason": None if evidence_count == 0 else "Existing evidence has no audit chain",
        }

    previous_hash = GENESIS
    for audit in audit_rows:
        sequence, evidence_id, stored_previous, stored_hash = audit
        if str(stored_previous) != previous_hash:
            return {
                "valid": False,
                "audited_rows": int(sequence) - 1,
                "reason": f"Audit chain predecessor mismatch at sequence {sequence}",
            }
        row = conn.execute(f"SELECT * FROM {evidence_table} WHERE id = ?", (evidence_id,)).fetchone()
        if row is None:
            return {
                "valid": False,
                "audited_rows": int(sequence) - 1,
                "reason": f"Audited evidence row {evidence_id} is missing",
            }
        payload = dict(row)
        expected = digest(previous_hash, canonical_payload(payload))
        if expected != str(stored_hash):
            return {
                "valid": False,
                "audited_rows": int(sequence) - 1,
                "reason": f"Evidence hash mismatch at sequence {sequence}",
            }
        previous_hash = str(stored_hash)

    evidence_count = int(conn.execute(f"SELECT COUNT(*) FROM {evidence_table}").fetchone()[0])
    audited_count = len(audit_rows)
    if evidence_count != audited_count:
        return {
            "valid": False,
            "audited_rows": audited_count,
            "evidence_rows": evidence_count,
            "reason": "One or more precision evidence rows are outside the audit chain",
        }
    return {
        "valid": True,
        "audited_rows": audited_count,
        "evidence_rows": evidence_count,
        "head_hash": previous_hash,
        "reason": None,
    }
