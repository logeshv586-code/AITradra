"""
agents/paper_autopilot.py
────────────────────────────────────────────────────────────────────────────────
PaperAutopilot — hands-free paper trading that proves (or disproves) the
system's profitability with zero real-money risk.

What it does on every cycle:

  EXITS FIRST (positions are managed before any new money goes out):
    - STOP LOSS      — close at -AUTOPILOT_STOP_LOSS_PCT
    - TAKE PROFIT    — close at +AUTOPILOT_TAKE_PROFIT_PCT
    - TIME EXIT      — close when the hold horizon expires
    - THESIS FLIP    — close when a fresh debate on the ticker says SELL
    Every close feeds ReflectionMemory, so the lesson loop and the
    SkillOptimizer train on the autopilot's real (paper) outcomes.

  ENTRIES (at most once per day, all risk gates enforced):
    - Candidates: recent Bull/Bear debate BUY verdicts above the confidence
      floor, plus commodity causal-chain BUY suggestions (which must pass a
      fresh debate before money moves).
    - Gates: max open positions, cash reserve, daily-loss circuit breaker,
      no doubling into an existing position, no ticker without a real price.
    - Sizing: the debate risk-bench blended size, capped at MAX_POSITION_PCT.

  REPORT — a daily P&L report card (equity, return, realized/unrealized,
  win rate, open positions with stops/targets, actions taken) persisted to
  agent_insights (ticker="PORTFOLIO") and exposed via the API.

Safety: this module talks ONLY to the PaperBroker. It has no code path to a
live broker — going live stays a deliberate, manual decision.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

AGENT_NAME = "PaperAutopilot"


class PaperAutopilot:
    """Automated paper-trading loop: enter on approved signals, manage exits, report."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.KNOWLEDGE_DB_PATH
        self._conn: Optional[sqlite3.Connection] = None
        self._broker = None
        self._ensure_tables()

    # ── Infrastructure ───────────────────────────────────────────────────────

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
        return self._conn

    def _ensure_tables(self) -> None:
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS autopilot_positions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker          TEXT NOT NULL,
                qty             REAL NOT NULL,
                entry_price     REAL NOT NULL,
                stop_price      REAL NOT NULL,
                target_price    REAL NOT NULL,
                hold_until      TEXT NOT NULL,
                thesis          TEXT,
                source          TEXT,
                confidence      INTEGER DEFAULT 0,
                status          TEXT DEFAULT 'open',   -- open | closed
                exit_price      REAL,
                exit_reason     TEXT,
                realized_pnl    REAL,
                opened_at       TEXT DEFAULT (datetime('now')),
                closed_at       TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_autopilot_status ON autopilot_positions(status, ticker);
        """)
        conn.commit()

    def _get_broker(self):
        if self._broker is None:
            from brokers.broker_router import PaperBroker
            self._broker = PaperBroker()
        return self._broker

    @staticmethod
    def _latest_price(ticker: str) -> Optional[float]:
        from brokers.broker_router import PaperBroker
        return PaperBroker._market_price(ticker)

    # ── Exit management ──────────────────────────────────────────────────────

    async def manage_exits(self) -> list[dict]:
        """Check every open autopilot position against its exit rules."""
        conn = self._get_conn()
        open_positions = conn.execute(
            "SELECT * FROM autopilot_positions WHERE status = 'open'"
        ).fetchall()
        actions: list[dict] = []
        now = datetime.now(timezone.utc)

        for pos in open_positions:
            ticker = pos["ticker"]
            price = self._latest_price(ticker)
            if price is None:
                continue  # no fresh price — check again next cycle

            reason = None
            if price <= pos["stop_price"]:
                reason = "STOP_LOSS"
            elif price >= pos["target_price"]:
                reason = "TAKE_PROFIT"
            elif now >= datetime.fromisoformat(pos["hold_until"]):
                reason = "TIME_EXIT"
            else:
                # Thesis flip: a fresh SELL debate verdict overrides the hold
                try:
                    from gateway.knowledge_store import knowledge_store
                    debates = knowledge_store.get_recent_debates(ticker=ticker, limit=1)
                    if debates:
                        d = debates[0]
                        opened = pos["opened_at"] or ""
                        if (d.get("verdict") == "SELL"
                                and d.get("confidence", 0) >= settings.AUTOPILOT_MIN_CONFIDENCE
                                and str(d.get("created_at", "")) > opened):
                            reason = "THESIS_FLIP"
                except Exception:
                    pass

            if reason:
                action = await self._close_position(pos, price, reason)
                if action:
                    actions.append(action)
        return actions

    async def _close_position(self, pos: sqlite3.Row, price: float, reason: str) -> Optional[dict]:
        from brokers.broker_router import Order, OrderSide, OrderType
        broker = self._get_broker()
        fill = await broker.place_order(Order(
            ticker=pos["ticker"], side=OrderSide.SELL, qty=pos["qty"],
            order_type=OrderType.MARKET,
        ))
        if fill.get("status") != "FILLED":
            logger.warning(f"[{AGENT_NAME}] Close failed for {pos['ticker']}: {fill.get('reason')}")
            return None

        realized = fill.get("realized_pnl", 0.0)
        conn = self._get_conn()
        conn.execute("""
            UPDATE autopilot_positions
            SET status='closed', exit_price=?, exit_reason=?, realized_pnl=?, closed_at=datetime('now')
            WHERE id=?
        """, (fill["fill_price"], reason, realized, pos["id"]))
        conn.commit()

        # Feed the outcome into the lesson loop
        try:
            from memory.reflection_memory import get_memory
            ret_pct = (fill["fill_price"] - pos["entry_price"]) / pos["entry_price"]
            accuracy = max(0.0, min(1.0, 0.5 + ret_pct * 5))  # ±10% move maps to 0..1
            await get_memory().reflect_on_outcome(
                ticker=pos["ticker"], source_agent=AGENT_NAME, direction="BULLISH",
                accuracy=accuracy,
                price_at_prediction=pos["entry_price"], actual_price=fill["fill_price"],
                context=f"Autopilot exit: {reason}. Thesis: {pos['thesis'] or ''}"[:400],
            )
        except Exception as e:
            logger.debug(f"[{AGENT_NAME}] Reflection skipped: {e}")

        action = {
            "action": "CLOSE", "ticker": pos["ticker"], "qty": pos["qty"],
            "exit_price": fill["fill_price"], "reason": reason,
            "realized_pnl": round(realized, 2),
        }
        logger.info(f"[{AGENT_NAME}] CLOSED {pos['ticker']} ({reason}) P&L {realized:+.2f}")
        return action

    # ── Entry pipeline ───────────────────────────────────────────────────────

    def _gather_candidates(self) -> list[dict]:
        """BUY candidates: Prime unified verdicts first, then debates, then commodity."""
        from gateway.knowledge_store import knowledge_store
        candidates: dict[str, dict] = {}

        # 0. AitradraPrime unified verdicts — every subsystem already weighed in
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=36)).isoformat()
        for snap in knowledge_store.get_all_ticker_intelligence(limit=50):
            if (snap.get("agent") == "AitradraPrime"
                    and snap.get("recommendation") == "BUY"
                    and str(snap.get("generated_at", "")) >= cutoff):
                conf = int((snap.get("confidence_score") or 0) * 100)
                if conf >= settings.AUTOPILOT_MIN_CONFIDENCE:
                    candidates[snap["ticker"]] = {
                        "ticker": snap["ticker"], "confidence": conf,
                        "size_pct": snap.get("position_size_pct", 0.0),
                        "thesis": str(snap.get("primary_driver", ""))[:400],
                        "source": "prime",
                        "needs_debate": False,  # Prime already ran the debate
                    }

        # 1. Recent debate BUY verdicts (already adversarially vetted)
        for d in knowledge_store.get_recent_debates(limit=30):
            if (d.get("verdict") == "BUY"
                    and d.get("confidence", 0) >= settings.AUTOPILOT_MIN_CONFIDENCE):
                t = d["ticker"]
                if t in candidates and candidates[t]["source"] == "prime":
                    continue  # Prime's unified verdict already includes the debate
                if t not in candidates or d["confidence"] > candidates[t]["confidence"]:
                    candidates[t] = {
                        "ticker": t, "confidence": d["confidence"],
                        "size_pct": (d.get("risk_bench") or {}).get("blended_size_pct", 0.0),
                        "thesis": d.get("key_reason", ""), "source": "debate",
                        "needs_debate": False,
                    }

        # 2. Commodity BUY suggestions — must pass a fresh debate before entry
        for event in knowledge_store.get_recent_commodity_events(hours=48, limit=20):
            for s in event.get("suggestions", []):
                if s.get("action") == "BUY" and s.get("confidence", 0) >= 0.6:
                    t = s["ticker"]
                    if t not in candidates:
                        candidates[t] = {
                            "ticker": t, "confidence": int(s["confidence"] * 100),
                            "size_pct": 0.0,
                            "thesis": s.get("why", ""), "source": "commodity",
                            "needs_debate": True,
                        }
        return list(candidates.values())

    async def open_entries(self) -> list[dict]:
        """Risk-gated entries from the candidate pool. At most one batch per day."""
        from gateway.knowledge_store import knowledge_store
        conn = self._get_conn()
        actions: list[dict] = []

        # Once-per-day gate for new entries
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        already = conn.execute(
            "SELECT COUNT(*) FROM autopilot_positions WHERE date(opened_at) = ?", (today,)
        ).fetchone()[0]
        if already:
            return actions

        broker = self._get_broker()
        balance = await broker.get_balance()

        # Daily-loss circuit breaker: realized losses today block new entries
        todays_pnl = conn.execute("""
            SELECT COALESCE(SUM(realized_pnl), 0) FROM autopilot_positions
            WHERE status='closed' AND date(closed_at) = ?
        """, (today,)).fetchone()[0]
        if todays_pnl <= -settings.MAX_DAILY_LOSS_PCT * balance["equity"]:
            logger.warning(f"[{AGENT_NAME}] Daily-loss breaker tripped ({todays_pnl:.2f}) — no entries today")
            return actions

        open_count = conn.execute(
            "SELECT COUNT(*) FROM autopilot_positions WHERE status='open'"
        ).fetchone()[0]

        for cand in sorted(self._gather_candidates(), key=lambda c: -c["confidence"]):
            if open_count >= settings.MAX_OPEN_POSITIONS:
                break
            ticker = cand["ticker"]

            # Never double into an existing position
            held = conn.execute(
                "SELECT COUNT(*) FROM autopilot_positions WHERE status='open' AND ticker=?",
                (ticker,),
            ).fetchone()[0]
            if held:
                continue

            # Commodity candidates face the bear before any money moves
            if cand["needs_debate"]:
                try:
                    from agents.debate_engine import get_engine
                    debate = await get_engine().run_debate(ticker)
                    if debate.verdict != "BUY" or debate.confidence < settings.AUTOPILOT_MIN_CONFIDENCE:
                        continue
                    cand["confidence"] = debate.confidence
                    cand["size_pct"] = debate.risk_bench.get("blended_size_pct", 0.0)
                except Exception as e:
                    logger.debug(f"[{AGENT_NAME}] Debate failed for {ticker}: {e}")
                    continue

            price = self._latest_price(ticker)
            if not price:
                continue

            # Sizing: debate risk bench capped by the platform's hard limit
            size_pct = min(cand["size_pct"] or 0.0, settings.MAX_POSITION_PCT * 100)
            if size_pct <= 0:
                continue
            budget = balance["equity"] * size_pct / 100
            qty = int(budget / price)
            if qty < 1:
                continue

            # Cash reserve gate
            reserve = balance["equity"] * settings.BALANCE_RESERVE_PCT
            if broker.cash - qty * price < reserve:
                continue

            from brokers.broker_router import Order, OrderSide, OrderType
            fill = await broker.place_order(Order(
                ticker=ticker, side=OrderSide.BUY, qty=qty, order_type=OrderType.MARKET,
            ))
            if fill.get("status") != "FILLED":
                continue

            entry = fill["fill_price"]
            hold_until = (datetime.now(timezone.utc)
                          + timedelta(days=settings.AUTOPILOT_MAX_HOLD_DAYS)).isoformat()
            conn.execute("""
                INSERT INTO autopilot_positions
                    (ticker, qty, entry_price, stop_price, target_price, hold_until,
                     thesis, source, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ticker, qty, entry,
                round(entry * (1 - settings.AUTOPILOT_STOP_LOSS_PCT), 4),
                round(entry * (1 + settings.AUTOPILOT_TAKE_PROFIT_PCT), 4),
                hold_until, cand["thesis"][:500], cand["source"], cand["confidence"],
            ))
            conn.commit()
            open_count += 1
            actions.append({
                "action": "OPEN", "ticker": ticker, "qty": qty,
                "entry_price": entry, "size_pct": size_pct,
                "stop": round(entry * (1 - settings.AUTOPILOT_STOP_LOSS_PCT), 2),
                "target": round(entry * (1 + settings.AUTOPILOT_TAKE_PROFIT_PCT), 2),
                "source": cand["source"], "confidence": cand["confidence"],
            })
            logger.info(
                f"[{AGENT_NAME}] OPENED {qty} {ticker} @ {entry:.2f} "
                f"({size_pct:.1f}% | stop -{settings.AUTOPILOT_STOP_LOSS_PCT:.0%} "
                f"| target +{settings.AUTOPILOT_TAKE_PROFIT_PCT:.0%})"
            )
        return actions

    # ── Cycle + reporting ────────────────────────────────────────────────────

    async def run_cycle(self) -> dict:
        """One full autopilot cycle: exits → entries → report."""
        if not settings.AUTOPILOT_ENABLED:
            return {"enabled": False}
        exits = await self.manage_exits()
        entries = await self.open_entries()
        report = await self.build_report(exits=exits, entries=entries)
        if exits or entries:
            self._persist_report(report)
        try:
            from gateway.knowledge_store import knowledge_store
            knowledge_store.update_agent_health(
                AGENT_NAME, status="active",
                task=f"Cycle: {len(entries)} opened, {len(exits)} closed, "
                     f"equity {report['balance']['equity']}",
            )
        except Exception:
            pass
        return report

    async def build_report(self, exits: list = None, entries: list = None) -> dict:
        """The daily report card: balance, open book, closed stats, actions."""
        broker = self._get_broker()
        balance = await broker.get_balance()
        conn = self._get_conn()

        open_rows = conn.execute(
            "SELECT * FROM autopilot_positions WHERE status='open' ORDER BY opened_at"
        ).fetchall()
        open_book = []
        for p in open_rows:
            mark = self._latest_price(p["ticker"]) or p["entry_price"]
            open_book.append({
                "ticker": p["ticker"], "qty": p["qty"],
                "entry": p["entry_price"], "mark": round(mark, 4),
                "unrealized_pct": round((mark - p["entry_price"]) / p["entry_price"] * 100, 2),
                "stop": p["stop_price"], "target": p["target_price"],
                "hold_until": p["hold_until"], "source": p["source"],
                "thesis": (p["thesis"] or "")[:150],
            })

        closed = conn.execute("""
            SELECT COUNT(*) AS n, COALESCE(SUM(realized_pnl), 0) AS pnl,
                   SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) AS wins
            FROM autopilot_positions WHERE status='closed'
        """).fetchone()

        return {
            "enabled": settings.AUTOPILOT_ENABLED,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "balance": balance,
            "open_positions": open_book,
            "closed_summary": {
                "count": closed["n"],
                "total_realized_pnl": round(closed["pnl"], 2),
                "win_rate": round(closed["wins"] / closed["n"], 3) if closed["n"] else None,
            },
            "actions_this_cycle": {"exits": exits or [], "entries": entries or []},
            "risk_limits": {
                "max_positions": settings.MAX_OPEN_POSITIONS,
                "max_position_pct": settings.MAX_POSITION_PCT * 100,
                "stop_loss_pct": settings.AUTOPILOT_STOP_LOSS_PCT * 100,
                "take_profit_pct": settings.AUTOPILOT_TAKE_PROFIT_PCT * 100,
                "daily_loss_breaker_pct": settings.MAX_DAILY_LOSS_PCT * 100,
                "cash_reserve_pct": settings.BALANCE_RESERVE_PCT * 100,
            },
        }

    def _persist_report(self, report: dict) -> None:
        try:
            from gateway.knowledge_store import knowledge_store
            knowledge_store.store_insight(
                ticker="PORTFOLIO", agent_name=AGENT_NAME,
                insight_type="autopilot_report",
                content=json.dumps(report, ensure_ascii=False),
                confidence=1.0,
            )
        except Exception as e:
            logger.debug(f"[{AGENT_NAME}] Report persistence skipped: {e}")

    def get_trade_history(self, limit: int = 50) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT * FROM autopilot_positions ORDER BY opened_at DESC LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]


# ── Module-level singleton ────────────────────────────────────────────────────

_autopilot_instance: Optional[PaperAutopilot] = None


def get_autopilot() -> PaperAutopilot:
    global _autopilot_instance
    if _autopilot_instance is None:
        _autopilot_instance = PaperAutopilot()
    return _autopilot_instance
