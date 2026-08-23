"""Forward-only Research Council scorecard.

This ledger measures research decisions; it is intentionally NOT the empirical
live-entry precision store and NOT a profitability claim.  Only decisions with
a timestamped market reference that existed at/before the decision timestamp are
eligible for audited outcome scoring.  Prior-session-only context remains useful
for research but is excluded from audit-grade scorecard metrics.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)


def _parse(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


class ResearchScorecardStore:
    """Immutable decision registry plus forward observed research outcomes."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or settings.KNOWLEDGE_DB_PATH
        self._init_tables()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self) -> None:
        try:
            conn = self._connect()
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS research_decisions_v2 (
                    decision_id TEXT PRIMARY KEY,
                    ticker TEXT NOT NULL,
                    as_of TEXT NOT NULL,
                    rating TEXT NOT NULL,
                    verdict TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    directional_score REAL NOT NULL,
                    evidence_quality REAL NOT NULL,
                    evidence_count INTEGER NOT NULL,
                    source_diversity_score REAL NOT NULL DEFAULT 0,
                    benchmark TEXT,
                    reference_price REAL NOT NULL DEFAULT 0,
                    reference_observed_at TEXT,
                    reference_kind TEXT,
                    benchmark_reference_price REAL NOT NULL DEFAULT 0,
                    benchmark_reference_observed_at TEXT,
                    audit_eligible INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS research_outcomes_v2 (
                    decision_id TEXT NOT NULL,
                    horizon_sessions INTEGER NOT NULL,
                    ticker TEXT NOT NULL,
                    target_date TEXT NOT NULL,
                    target_price REAL NOT NULL,
                    return_pct REAL NOT NULL,
                    benchmark TEXT,
                    benchmark_target_price REAL,
                    benchmark_return_pct REAL,
                    alpha_pct REAL,
                    direction_correct INTEGER NOT NULL,
                    alpha_direction_correct INTEGER,
                    brier_score REAL NOT NULL,
                    resolved_at TEXT NOT NULL,
                    PRIMARY KEY(decision_id, horizon_sessions)
                );

                CREATE INDEX IF NOT EXISTS idx_research_decision_ticker
                    ON research_decisions_v2(ticker, as_of);
                CREATE INDEX IF NOT EXISTS idx_research_outcome_horizon
                    ON research_outcomes_v2(horizon_sessions, resolved_at);
                """
            )
            conn.commit()
            conn.close()
        except Exception as exc:
            logger.warning("ResearchScorecard init failed: %s", exc)

    @staticmethod
    def _is_audit_eligible(decision: dict[str, Any]) -> bool:
        context = decision.get("benchmark_context") or {}
        if context.get("reference_kind") != "timestamped_snapshot":
            return False
        as_of = _parse(decision.get("as_of"))
        observed = _parse(context.get("reference_observed_at"))
        price = _float(context.get("reference_price"))
        if as_of is None or observed is None or price <= 0:
            return False
        return observed <= as_of

    def record_decision(self, decision: dict[str, Any]) -> bool:
        """Record one immutable research decision; reruns cannot rewrite it."""
        decision_id = str(decision.get("decision_id") or "").strip()
        ticker = str(decision.get("ticker") or "").upper().strip()
        as_of = _parse(decision.get("as_of"))
        if not decision_id or not ticker or as_of is None:
            return False

        context = decision.get("benchmark_context") or {}
        audit_eligible = self._is_audit_eligible(decision)
        created_at = str(decision.get("created_at") or datetime.now(timezone.utc).isoformat())
        try:
            conn = self._connect()
            before = conn.total_changes
            conn.execute(
                """
                INSERT INTO research_decisions_v2 (
                    decision_id, ticker, as_of, rating, verdict, confidence,
                    directional_score, evidence_quality, evidence_count,
                    source_diversity_score, benchmark, reference_price,
                    reference_observed_at, reference_kind,
                    benchmark_reference_price, benchmark_reference_observed_at,
                    audit_eligible, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(decision_id) DO NOTHING
                """,
                (
                    decision_id,
                    ticker,
                    as_of.isoformat(),
                    str(decision.get("rating") or "HOLD").upper(),
                    str(decision.get("verdict") or "HOLD").upper(),
                    _float(decision.get("confidence")),
                    _float(decision.get("directional_score")),
                    _float(decision.get("evidence_quality")),
                    int(decision.get("evidence_count") or 0),
                    _float(decision.get("source_diversity_score")),
                    str(context.get("benchmark") or "") or None,
                    _float(context.get("reference_price")),
                    context.get("reference_observed_at"),
                    context.get("reference_kind"),
                    _float(context.get("benchmark_reference_price")),
                    context.get("benchmark_reference_observed_at"),
                    1 if audit_eligible else 0,
                    created_at,
                ),
            )
            inserted = conn.total_changes > before
            conn.commit()
            conn.close()
            return inserted
        except Exception as exc:
            logger.warning("ResearchScorecard record failed: %s", exc)
            return False

    def _future_bars(
        self, conn: sqlite3.Connection, ticker: str, after_date: str, limit: int
    ) -> list[sqlite3.Row]:
        return conn.execute(
            """
            SELECT date, close FROM daily_ohlcv
            WHERE ticker = ? AND date > ? AND close > 0
            ORDER BY date ASC LIMIT ?
            """,
            (ticker.upper(), after_date, max(1, int(limit))),
        ).fetchall()

    @staticmethod
    def _direction_correct(rating: str, return_pct: float) -> bool:
        rating = str(rating).upper()
        if rating in {"BUY", "OVERWEIGHT"}:
            return return_pct > 0
        if rating in {"SELL", "UNDERWEIGHT"}:
            return return_pct < 0
        return False

    @staticmethod
    def _brier(confidence: float, correct: bool) -> float:
        probability = max(0.0, min(float(confidence) / 100.0, 1.0))
        return round((probability - (1.0 if correct else 0.0)) ** 2, 6)

    def evaluate_pending(
        self,
        *,
        horizons: Iterable[int] = (1, 5, 20),
        now: datetime | None = None,
        limit: int = 500,
    ) -> dict[str, Any]:
        """Resolve audit-eligible active ratings using only later daily closes.

        Horizon is measured in later market sessions, not calendar days. A
        decision made on date D can only use rows where `date > D`.
        """
        now = now or datetime.now(timezone.utc)
        horizons = sorted({max(1, int(value)) for value in horizons})
        if not horizons:
            return {"evaluated": 0, "outcomes_added": 0, "skipped": 0}

        evaluated = outcomes_added = skipped = 0
        try:
            conn = self._connect()
            decisions = conn.execute(
                """
                SELECT * FROM research_decisions_v2
                WHERE audit_eligible = 1
                  AND rating IN ('BUY', 'OVERWEIGHT', 'SELL', 'UNDERWEIGHT')
                  AND datetime(as_of) < datetime(?)
                ORDER BY datetime(as_of) ASC LIMIT ?
                """,
                (now.isoformat(), max(1, int(limit))),
            ).fetchall()

            for decision in decisions:
                as_of = _parse(decision["as_of"])
                reference = _float(decision["reference_price"])
                if as_of is None or reference <= 0:
                    skipped += 1
                    continue
                future = self._future_bars(
                    conn,
                    decision["ticker"],
                    as_of.date().isoformat(),
                    max(horizons),
                )
                if not future:
                    skipped += 1
                    continue

                for horizon in horizons:
                    exists = conn.execute(
                        """
                        SELECT 1 FROM research_outcomes_v2
                        WHERE decision_id = ? AND horizon_sessions = ?
                        """,
                        (decision["decision_id"], horizon),
                    ).fetchone()
                    if exists or len(future) < horizon:
                        continue

                    target = future[horizon - 1]
                    target_price = _float(target["close"])
                    if target_price <= 0:
                        continue
                    return_pct = (target_price - reference) / reference * 100.0
                    correct = self._direction_correct(decision["rating"], return_pct)

                    benchmark = str(decision["benchmark"] or "")
                    benchmark_reference = _float(decision["benchmark_reference_price"])
                    benchmark_target = benchmark_return = alpha = None
                    alpha_correct = None
                    if benchmark and benchmark_reference > 0:
                        row = conn.execute(
                            """
                            SELECT close FROM daily_ohlcv
                            WHERE ticker = ? AND date >= ? AND close > 0
                            ORDER BY date ASC LIMIT 1
                            """,
                            (benchmark, target["date"]),
                        ).fetchone()
                        if row and _float(row["close"]) > 0:
                            benchmark_target = _float(row["close"])
                            benchmark_return = (
                                (benchmark_target - benchmark_reference)
                                / benchmark_reference * 100.0
                            )
                            alpha = return_pct - benchmark_return
                            alpha_correct = self._direction_correct(decision["rating"], alpha)

                    conn.execute(
                        """
                        INSERT INTO research_outcomes_v2 (
                            decision_id, horizon_sessions, ticker, target_date,
                            target_price, return_pct, benchmark,
                            benchmark_target_price, benchmark_return_pct, alpha_pct,
                            direction_correct, alpha_direction_correct, brier_score,
                            resolved_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(decision_id, horizon_sessions) DO NOTHING
                        """,
                        (
                            decision["decision_id"],
                            horizon,
                            decision["ticker"],
                            target["date"],
                            target_price,
                            round(return_pct, 6),
                            benchmark or None,
                            benchmark_target,
                            round(benchmark_return, 6) if benchmark_return is not None else None,
                            round(alpha, 6) if alpha is not None else None,
                            1 if correct else 0,
                            (1 if alpha_correct else 0) if alpha_correct is not None else None,
                            self._brier(decision["confidence"], correct),
                            now.isoformat(),
                        ),
                    )
                    outcomes_added += 1
                evaluated += 1

            conn.commit()
            conn.close()
        except Exception as exc:
            logger.warning("ResearchScorecard evaluation failed: %s", exc)
            return {
                "evaluated": evaluated,
                "outcomes_added": outcomes_added,
                "skipped": skipped,
                "error": type(exc).__name__,
            }
        return {
            "evaluated": evaluated,
            "outcomes_added": outcomes_added,
            "skipped": skipped,
        }

    def summary(self, *, horizon_sessions: int = 5) -> dict[str, Any]:
        """Return calibration and benchmark-aware outcome metrics."""
        horizon = max(1, int(horizon_sessions))
        try:
            conn = self._connect()
            decision_counts = conn.execute(
                """
                SELECT COUNT(*) total,
                       COALESCE(SUM(audit_eligible), 0) audit_eligible
                FROM research_decisions_v2
                """
            ).fetchone()
            row = conn.execute(
                """
                SELECT COUNT(*) resolved,
                       COALESCE(AVG(direction_correct), 0) hit_rate,
                       COALESCE(AVG(alpha_direction_correct), 0) alpha_hit_rate,
                       COALESCE(AVG(return_pct), 0) avg_return_pct,
                       COALESCE(AVG(alpha_pct), 0) avg_alpha_pct,
                       COALESCE(AVG(brier_score), 0) brier_score
                FROM research_outcomes_v2
                WHERE horizon_sessions = ?
                """,
                (horizon,),
            ).fetchone()
            confidence = conn.execute(
                """
                SELECT COALESCE(AVG(d.confidence), 0) avg_confidence
                FROM research_outcomes_v2 o
                JOIN research_decisions_v2 d ON d.decision_id = o.decision_id
                WHERE o.horizon_sessions = ?
                """,
                (horizon,),
            ).fetchone()
            conn.close()
            hit_rate = float(row["hit_rate"] or 0)
            avg_conf = float(confidence["avg_confidence"] or 0) / 100.0
            return {
                "horizon_sessions": horizon,
                "decisions_recorded": int(decision_counts["total"] or 0),
                "audit_eligible_decisions": int(decision_counts["audit_eligible"] or 0),
                "resolved_active_decisions": int(row["resolved"] or 0),
                "directional_hit_rate": round(hit_rate, 6),
                "alpha_direction_hit_rate": round(float(row["alpha_hit_rate"] or 0), 6),
                "average_return_pct": round(float(row["avg_return_pct"] or 0), 6),
                "average_alpha_pct": round(float(row["avg_alpha_pct"] or 0), 6),
                "average_confidence": round(avg_conf, 6),
                "calibration_gap": round(abs(avg_conf - hit_rate), 6),
                "brier_score": round(float(row["brier_score"] or 0), 6),
                "live_gate_input": False,
                "profitability_claim": False,
            }
        except Exception as exc:
            logger.warning("ResearchScorecard summary failed: %s", exc)
            return {
                "horizon_sessions": horizon,
                "decisions_recorded": 0,
                "audit_eligible_decisions": 0,
                "resolved_active_decisions": 0,
                "live_gate_input": False,
                "profitability_claim": False,
                "error": type(exc).__name__,
            }

    def recent_outcomes(self, *, limit: int = 50) -> list[dict[str, Any]]:
        try:
            conn = self._connect()
            rows = conn.execute(
                """
                SELECT d.decision_id, d.ticker, d.as_of, d.rating, d.confidence,
                       d.evidence_quality, d.source_diversity_score,
                       o.horizon_sessions, o.target_date, o.return_pct,
                       o.benchmark, o.benchmark_return_pct, o.alpha_pct,
                       o.direction_correct, o.alpha_direction_correct,
                       o.brier_score, o.resolved_at
                FROM research_outcomes_v2 o
                JOIN research_decisions_v2 d ON d.decision_id = o.decision_id
                ORDER BY datetime(o.resolved_at) DESC LIMIT ?
                """,
                (max(1, min(int(limit), 500)),),
            ).fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as exc:
            logger.warning("ResearchScorecard recent query failed: %s", exc)
            return []


research_scorecard = ResearchScorecardStore()
