from datetime import datetime, timedelta, timezone
import sqlite3

from self_improvement.precision_store import DirectionalPrecisionStore


def _record(store: DirectionalPrecisionStore, prediction_id: str = "audit-1") -> None:
    now = datetime.now(timezone.utc)
    assert store.record_outcome(
        prediction_id=prediction_id,
        ticker="BTC",
        model="SignalAggregatorAgent",
        provider="live_primary",
        upstream_provider="live_primary",
        direction="BULLISH",
        correct=True,
        continuous_accuracy=1.0,
        prediction_timestamp=(now - timedelta(hours=25)).isoformat(),
        horizon_hours=24,
        evaluated_at=now.isoformat(),
        observed_at=(now - timedelta(minutes=1)).isoformat(),
        live_gate_eligible=True,
    )


def test_precision_audit_chain_is_valid_for_append_only_evidence(tmp_path):
    store = DirectionalPrecisionStore(str(tmp_path / "precision.db"))
    _record(store, "audit-1")
    _record(store, "audit-2")
    result = store.verify_audit_integrity()
    assert result["valid"] is True
    assert result["audited_rows"] == 2
    assert result["evidence_rows"] == 2
    assert len(result["head_hash"]) == 64


def test_precision_audit_detects_mutated_evidence(tmp_path):
    db = str(tmp_path / "precision.db")
    store = DirectionalPrecisionStore(db)
    _record(store)
    with sqlite3.connect(db) as conn:
        conn.execute(
            f"UPDATE {store.TABLE} SET correct = 0 WHERE prediction_id = ?",
            ("audit-1",),
        )
    result = store.verify_audit_integrity()
    assert result["valid"] is False
    assert "hash mismatch" in str(result["reason"]).lower()


def test_precision_audit_detects_unaudited_insert(tmp_path):
    db = str(tmp_path / "precision.db")
    store = DirectionalPrecisionStore(db)
    _record(store)
    with sqlite3.connect(db) as conn:
        row = conn.execute(f"SELECT * FROM {store.TABLE} LIMIT 1").fetchone()
        values = list(row)[1:]
        values[0] = "rogue-row"
        conn.execute(
            f"""
            INSERT INTO {store.TABLE}
                (prediction_id, ticker, model, provider, upstream_provider, direction,
                 correct, continuous_accuracy, prediction_timestamp, horizon_hours,
                 evaluated_at, observed_at, scored_at, live_gate_eligible, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            values,
        )
    result = store.verify_audit_integrity()
    assert result["valid"] is False
    assert "outside the audit chain" in str(result["reason"]).lower()
