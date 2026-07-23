"""
memory/reflection_memory.py
────────────────────────────────────────────────────────────────────────────────
ReflectionMemory — the platform's trade-lesson decision log.

Inspired by TauricResearch/TradingAgents' reflection mechanism: every time a
prediction RESOLVES (the SelfImprovementEngine scores it against real price
action), we don't just record a number — we write down the LESSON: what the
call was, what the context was, whether it worked, and what to do differently.

Lessons are then retrieved before new decisions:
  - same-ticker lessons  ("last two BULLISH calls on TSLA during earnings
                           week failed — demand confirmation")
  - cross-ticker lessons ("commodity-driven calls have been our most
                           accurate category this month")

The DebateEngine injects these into its evidence pack, so past mistakes argue
in the room alongside fresh signals. LLM writes richer lessons when
available; the template fallback still captures the essential pattern.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

DB_PATH = settings.KNOWLEDGE_DB_PATH


class ReflectionMemory:
    """SQLite-backed store of lessons learned from resolved predictions."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._ensure_table()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
        return self._conn

    def _ensure_table(self) -> None:
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS trade_lessons (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker        TEXT NOT NULL,
                source_agent  TEXT,
                direction     TEXT,
                accuracy      REAL,
                was_correct   INTEGER,
                context       TEXT,
                lesson        TEXT NOT NULL,
                created_at    TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_lessons_ticker ON trade_lessons(ticker, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_lessons_correct ON trade_lessons(was_correct, created_at DESC);
        """)
        conn.commit()

    # ── Writing lessons ──────────────────────────────────────────────────────

    async def reflect_on_outcome(
        self,
        ticker: str,
        source_agent: str,
        direction: str,
        accuracy: float,
        price_at_prediction: float,
        actual_price: float,
        context: str = "",
        use_llm: bool = True,
    ) -> dict:
        """
        Turn one resolved prediction into a lesson and persist it.
        accuracy is the scorer's 0-1 score; >= 0.5 counts as correct.
        """
        was_correct = accuracy >= 0.5
        realized_pct = (
            (actual_price - price_at_prediction) / price_at_prediction * 100
            if price_at_prediction else 0.0
        )

        lesson_text = ""
        if use_llm:
            lesson_text = await self._llm_lesson(
                ticker, source_agent, direction, was_correct, realized_pct, context
            )
        if not lesson_text:
            outcome_word = "was CORRECT" if was_correct else "FAILED"
            lesson_text = (
                f"{source_agent}'s {direction} call on {ticker} {outcome_word} "
                f"(price moved {realized_pct:+.2f}%, accuracy {accuracy:.2f}). "
                + ("Reinforce: similar setups from this agent deserve weight."
                   if was_correct else
                   "Caution: demand stronger confirmation before trusting similar "
                   f"{direction} calls from {source_agent} on {ticker}.")
            )

        record = {
            "ticker": ticker.upper(),
            "source_agent": source_agent,
            "direction": direction,
            "accuracy": round(accuracy, 4),
            "was_correct": 1 if was_correct else 0,
            "context": context[:1000],
            "lesson": lesson_text[:1500],
        }
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO trade_lessons (ticker, source_agent, direction, accuracy, was_correct, context, lesson)
            VALUES (:ticker, :source_agent, :direction, :accuracy, :was_correct, :context, :lesson)
        """, record)
        conn.commit()
        record["created_at"] = datetime.now(timezone.utc).isoformat()
        return record

    async def _llm_lesson(
        self, ticker: str, source_agent: str, direction: str,
        was_correct: bool, realized_pct: float, context: str,
    ) -> str:
        try:
            from llm.client import get_shared_llm
            llm = get_shared_llm()
            outcome = "was correct" if was_correct else "was wrong"
            text = await llm.complete(
                prompt=(
                    f"A trading prediction just resolved.\n"
                    f"Agent: {source_agent}\nTicker: {ticker}\nCall: {direction}\n"
                    f"Outcome: the call {outcome}; price moved {realized_pct:+.2f}%.\n"
                    f"Context at prediction time: {context or '(none recorded)'}\n\n"
                    "Write ONE concise lesson (2-3 sentences) a trading desk should "
                    "remember from this outcome. Focus on the transferable pattern, "
                    "not the specific numbers."
                ),
                system="You are the post-trade review analyst of a trading desk. Extract reusable lessons.",
                temperature=0.3,
                max_tokens=200,
                role="analysis",
            )
            return (text or "").strip()
        except Exception as e:
            logger.debug(f"[ReflectionMemory] LLM lesson skipped: {e}")
            return ""

    # ── Retrieving lessons ───────────────────────────────────────────────────

    def get_lessons_for(self, ticker: str, limit: int = 5) -> list[dict]:
        """Same-ticker recent lessons + the most instructive cross-ticker failures."""
        conn = self._get_conn()
        same = conn.execute("""
            SELECT ticker, source_agent, direction, accuracy, was_correct, lesson, created_at
            FROM trade_lessons WHERE ticker = ?
            ORDER BY created_at DESC LIMIT ?
        """, (ticker.upper(), limit)).fetchall()
        lessons = [dict(r) for r in same]

        remaining = limit - len(lessons)
        if remaining > 0:
            cross = conn.execute("""
                SELECT ticker, source_agent, direction, accuracy, was_correct, lesson, created_at
                FROM trade_lessons
                WHERE ticker != ? AND was_correct = 0
                ORDER BY created_at DESC LIMIT ?
            """, (ticker.upper(), remaining)).fetchall()
            lessons.extend(dict(r) for r in cross)
        return lessons

    def get_recent(self, limit: int = 20) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT ticker, source_agent, direction, accuracy, was_correct, lesson, created_at
            FROM trade_lessons ORDER BY created_at DESC LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]

    def get_agent_report_card(self, source_agent: str) -> dict:
        """Summarize an agent's track record — consumed by the SkillOptimizer."""
        conn = self._get_conn()
        row = conn.execute("""
            SELECT COUNT(*) AS total,
                   SUM(was_correct) AS correct,
                   AVG(accuracy) AS avg_accuracy
            FROM trade_lessons WHERE source_agent = ?
        """, (source_agent,)).fetchone()
        total = row["total"] or 0
        failures = conn.execute("""
            SELECT ticker, direction, lesson FROM trade_lessons
            WHERE source_agent = ? AND was_correct = 0
            ORDER BY created_at DESC LIMIT 5
        """, (source_agent,)).fetchall()
        return {
            "agent": source_agent,
            "total_lessons": total,
            "correct": row["correct"] or 0,
            "hit_rate": round((row["correct"] or 0) / total, 3) if total else None,
            "avg_accuracy": round(row["avg_accuracy"], 4) if row["avg_accuracy"] is not None else None,
            "recent_failures": [dict(f) for f in failures],
        }

    def stats(self) -> dict:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT COUNT(*) AS total, SUM(was_correct) AS correct FROM trade_lessons"
        ).fetchone()
        total = row["total"] or 0
        return {
            "total_lessons": total,
            "correct": row["correct"] or 0,
            "hit_rate": round((row["correct"] or 0) / total, 3) if total else None,
        }


# ── Module-level singleton ────────────────────────────────────────────────────

_memory_instance: Optional[ReflectionMemory] = None


def get_memory() -> ReflectionMemory:
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = ReflectionMemory()
    return _memory_instance
