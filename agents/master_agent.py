"""
agents/master_agent.py
────────────────────────────────────────────────────────────────────────────────
AitradraPrime — the ONE agent the user talks to.

Every subsystem in the platform is an organ; Prime is the brain stem that
makes them speak with a single voice. For any ticker it:

  1. FANS OUT to every intelligence source the platform has:
       • Specialist insights   (Technical / Risk / Macro / Sentiment / …)
       • Commodity causal      (supply-chain events touching the ticker)
       • Bull/Bear debate      (fresh adversarial verdict + risk bench)
       • Price momentum        (stored OHLCV trend)
       • News sentiment        (recent headlines)
       • Trade lessons         (reflection memory — past mistakes/wins)
  2. WEIGHS each source. Specialist voices are scaled by their REAL measured
     accuracy (AccuracyStore leaderboard) — an agent that has been wrong
     loses influence automatically.
  3. SPEAKS ONCE: a single verdict (BUY/SELL/HOLD), one confidence number,
     one trade plan (entry / stop / target / size / hold horizon), the
     primary driver, and a component breakdown showing how every sub-agent
     voted — full transparency, single voice.
  4. PERSISTS the verdict to ticker_intelligence (the UI's snapshot table)
     and agent_insights, and the PaperAutopilot trades directly from it.

The daily Prime sweep replaces scattered per-agent runs: it analyzes the
watchlist + research candidates each morning, and a portfolio briefing rolls
everything (autopilot P&L, commodity events, lessons) into one report.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from core.logger import get_logger

logger = get_logger(__name__)

AGENT_NAME = "AitradraPrime"

# How much each intelligence source contributes to the unified score.
COMPONENT_WEIGHTS = {
    "debate":     0.40,   # adversarially-tested — the strongest single signal
    "specialists": 0.25,  # accuracy-weighted consensus of the specialist fleet
    "commodity":  0.15,   # real-world causal chains (floods → prices → stocks)
    "momentum":   0.10,   # price trend
    "news":       0.10,   # headline sentiment
}

BULLISH_WORDS = ["BULLISH", "BUY", "STRONG BUY", "UPGRADE", "POSITIVE", "OUTPERFORM"]
BEARISH_WORDS = ["BEARISH", "SELL", "AVOID", "DOWNGRADE", "NEGATIVE", "UNDERPERFORM"]


@dataclass
class UnifiedVerdict:
    ticker:            str
    verdict:           str                    # BUY | SELL | HOLD
    confidence:        int                    # 0-100
    score:             float                  # -1 .. +1 unified signal
    components:        dict = field(default_factory=dict)
    entry_price:       Optional[float] = None
    stop_price:        Optional[float] = None
    target_price:      Optional[float] = None
    position_size_pct: float = 0.0
    hold_horizon:      str = ""
    primary_driver:    str = ""
    narrative:         str = ""
    risks:             list[str] = field(default_factory=list)
    generated_at:      str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": AGENT_NAME,
            "ticker": self.ticker,
            "verdict": self.verdict,
            "confidence": self.confidence,
            "score": round(self.score, 3),
            "components": self.components,
            "trade_plan": {
                "entry_price": self.entry_price,
                "stop_price": self.stop_price,
                "target_price": self.target_price,
                "position_size_pct": self.position_size_pct,
                "hold_horizon": self.hold_horizon,
            },
            "primary_driver": self.primary_driver,
            "narrative": self.narrative,
            "risks": self.risks,
            "generated_at": self.generated_at,
        }


class MasterAgent:
    """The unified intelligence: every sub-agent reports in, one voice reports out."""

    # ── Component analyzers (each returns signal −1..+1, detail string) ──────

    @staticmethod
    def _agent_accuracy_weight(agent_name: str) -> float:
        """Scale a specialist's vote by its measured real-world accuracy."""
        try:
            from self_improvement.accuracy_store import accuracy_store
            for entry in accuracy_store.get_leaderboard(group_by="model", limit=100):
                if entry.get("model") == agent_name and entry.get("total_scored", 0) >= 5:
                    acc = entry.get("avg_accuracy", 0.5)
                    return max(0.4, min(1.4, 0.4 + 2.0 * acc))  # 0.4 (bad) .. 1.4 (great)
        except Exception:
            pass
        return 1.0

    def _component_specialists(self, ticker: str) -> tuple[float, str]:
        from gateway.knowledge_store import knowledge_store
        insights = knowledge_store.get_recent_insights(ticker, hours=48, limit=50)
        weighted, total_weight, votes = 0.0, 0.0, 0
        per_agent: dict[str, float] = {}
        for ins in insights:
            agent = ins.get("agent_name", "")
            if agent in (AGENT_NAME, "DebateEngine", "CommodityImpactAgent"):
                continue  # counted by their own components
            upper = str(ins.get("content", "")).upper()
            if any(w in upper for w in BULLISH_WORDS):
                vote = 1.0
            elif any(w in upper for w in BEARISH_WORDS):
                vote = -1.0
            else:
                continue
            weight = self._agent_accuracy_weight(agent)
            # one vote per agent — newest wins (insights come newest-first)
            if agent not in per_agent:
                per_agent[agent] = vote * weight
                total_weight += weight
                votes += 1
        if not votes:
            return 0.0, "no directional specialist insights in the last 48h"
        weighted = sum(per_agent.values())
        signal = max(-1.0, min(1.0, weighted / total_weight))
        bulls = sum(1 for v in per_agent.values() if v > 0)
        return signal, f"{bulls}/{votes} specialists bullish (accuracy-weighted)"

    @staticmethod
    def _component_commodity(ticker: str) -> tuple[float, str]:
        from gateway.knowledge_store import knowledge_store
        events = knowledge_store.get_recent_commodity_events(hours=72, limit=30)
        signal, details = 0.0, []
        for event in events:
            for impact in event.get("impacts", []):
                if impact.get("ticker") == ticker:
                    s = event.get("confidence", 0.5)
                    signal += s if impact["impact"] == "BULLISH" else -s
                    details.append(
                        f"{event['commodity']} {event['direction']} → {impact['impact']}"
                    )
        if not details:
            return 0.0, "no commodity causal events touch this ticker"
        return max(-1.0, min(1.0, signal)), "; ".join(details[:3])

    @staticmethod
    def _component_momentum(ticker: str) -> tuple[float, str, Optional[float]]:
        from gateway.knowledge_store import knowledge_store
        bars = knowledge_store.get_ohlcv_history(ticker, days=45)
        closes = [b["close"] for b in bars if b.get("close")]
        if len(closes) < 3:
            return 0.0, "insufficient price history", closes[0] if closes else None
        newest = closes[0]
        oldest = closes[min(len(closes) - 1, 20)]
        chg = (newest - oldest) / oldest * 100 if oldest else 0.0
        signal = max(-1.0, min(1.0, chg / 10.0))  # ±10% over window saturates
        return signal, f"{chg:+.1f}% over ~{min(len(closes), 20)} bars", newest

    @staticmethod
    def _component_news(ticker: str) -> tuple[float, str]:
        from gateway.knowledge_store import knowledge_store
        articles = knowledge_store.get_news_for_ticker(ticker, limit=20, days=3)
        scores = [a.get("sentiment_score") or 0.0 for a in articles]
        scored = [s for s in scores if s]
        if not scored:
            return 0.0, f"{len(articles)} headlines, none scored"
        avg = sum(scored) / len(scored)
        return max(-1.0, min(1.0, avg * 2)), f"avg sentiment {avg:+.2f} over {len(scored)} headlines"

    # ── The unified analysis ─────────────────────────────────────────────────

    async def analyze(self, ticker: str, use_llm: bool = True) -> UnifiedVerdict:
        """Fan out to every subsystem, weigh the votes, speak with one voice."""
        ticker = ticker.upper()

        # Debate runs fresh — it already folds in lessons, insights, and news
        from agents.debate_engine import get_engine
        debate = await get_engine().run_debate(ticker, use_llm=use_llm)
        debate_signal = (
            (1.0 if debate.verdict == "BUY" else -1.0 if debate.verdict == "SELL" else 0.0)
            * (debate.confidence / 100.0)
        )

        spec_signal, spec_detail = self._component_specialists(ticker)
        comm_signal, comm_detail = self._component_commodity(ticker)
        mom_signal, mom_detail, last_price = self._component_momentum(ticker)
        news_signal, news_detail = self._component_news(ticker)

        components = {
            "debate": {
                "signal": round(debate_signal, 3), "weight": COMPONENT_WEIGHTS["debate"],
                "detail": f"{debate.verdict} ({debate.confidence}%) — {debate.key_reason[:120]}",
            },
            "specialists": {
                "signal": round(spec_signal, 3), "weight": COMPONENT_WEIGHTS["specialists"],
                "detail": spec_detail,
            },
            "commodity": {
                "signal": round(comm_signal, 3), "weight": COMPONENT_WEIGHTS["commodity"],
                "detail": comm_detail,
            },
            "momentum": {
                "signal": round(mom_signal, 3), "weight": COMPONENT_WEIGHTS["momentum"],
                "detail": mom_detail,
            },
            "news": {
                "signal": round(news_signal, 3), "weight": COMPONENT_WEIGHTS["news"],
                "detail": news_detail,
            },
        }

        score = sum(c["signal"] * c["weight"] for c in components.values())

        # Agreement raises confidence; a lone loud voice does not.
        active = [c for c in components.values() if abs(c["signal"]) > 0.05]
        agreeing = sum(
            1 for c in active
            if (c["signal"] > 0) == (score > 0) and score != 0
        )
        agreement = agreeing / len(active) if active else 0.0
        confidence = int(min(95, abs(score) * 70 + agreement * 25))

        if score >= 0.30 and confidence >= 55:
            verdict = "BUY"
        elif score <= -0.30 and confidence >= 55:
            verdict = "SELL"
        else:
            verdict = "HOLD"

        # Trade plan — the debate's risk bench sizes it, platform limits cap it
        from core.config import settings
        size_pct = 0.0
        if verdict != "HOLD":
            size_pct = min(
                debate.risk_bench.get("blended_size_pct", 0.0) or (confidence / 100 * 8),
                settings.MAX_POSITION_PCT * 100,
            )
        stop = target = None
        if last_price and verdict == "BUY":
            stop = round(last_price * (1 - settings.AUTOPILOT_STOP_LOSS_PCT), 4)
            target = round(last_price * (1 + settings.AUTOPILOT_TAKE_PROFIT_PCT), 4)
        elif last_price and verdict == "SELL":
            stop = round(last_price * (1 + settings.AUTOPILOT_STOP_LOSS_PCT), 4)
            target = round(last_price * (1 - settings.AUTOPILOT_TAKE_PROFIT_PCT), 4)

        primary = max(components.items(), key=lambda kv: abs(kv[1]["signal"]) * kv[1]["weight"])
        risks = self._collect_risks(components, debate)

        verdict_obj = UnifiedVerdict(
            ticker=ticker,
            verdict=verdict,
            confidence=confidence,
            score=score,
            components=components,
            entry_price=last_price,
            stop_price=stop,
            target_price=target,
            position_size_pct=round(size_pct, 1),
            hold_horizon=f"up to {settings.AUTOPILOT_MAX_HOLD_DAYS} days (stop/target managed)",
            primary_driver=f"{primary[0]}: {primary[1]['detail'][:150]}",
            narrative="",
            risks=risks,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
        verdict_obj.narrative = await self._narrative(verdict_obj, use_llm)
        self._persist(verdict_obj)
        logger.info(
            f"[{AGENT_NAME}] {ticker}: {verdict} ({confidence}%) score={score:+.2f} "
            f"driver={primary[0]}"
        )
        return verdict_obj

    @staticmethod
    def _collect_risks(components: dict, debate) -> list[str]:
        risks = []
        # Any component fighting the consensus is a named risk, not buried noise
        score_sign = 1 if sum(c["signal"] * c["weight"] for c in components.values()) >= 0 else -1
        for name, c in components.items():
            if abs(c["signal"]) > 0.2 and (c["signal"] > 0) != (score_sign > 0):
                risks.append(f"{name} disagrees with the consensus: {c['detail'][:100]}")
        if debate.bear_case and debate.verdict == "BUY":
            risks.append(f"Bear's best point: {str(debate.bear_case[0])[:150]}")
        if debate.bull_case and debate.verdict == "SELL":
            risks.append(f"Bull's best point: {str(debate.bull_case[0])[:150]}")
        return risks[:4]

    async def _narrative(self, v: UnifiedVerdict, use_llm: bool) -> str:
        # Expert chart context makes even the offline narrative desk-grade
        expert_line = ""
        try:
            from gateway.knowledge_store import knowledge_store
            from core.quant_engine import expert_view
            bars = knowledge_store.get_ohlcv_history(v.ticker, days=365)
            if bars and len(bars) >= 20:
                ev = expert_view(bars)
                expert_line = f" Chart: {ev['commentary']}"
        except Exception:
            pass
        fallback = (
            f"{v.ticker}: {v.verdict} at {v.confidence}% confidence. "
            f"Primary driver — {v.primary_driver}. "
            + (f"Plan: size {v.position_size_pct}% of portfolio, stop {v.stop_price}, "
               f"target {v.target_price}. " if v.verdict != "HOLD" else "No position warranted. ")
            + (f"Key risk: {v.risks[0]}" if v.risks else "No major dissent among sources.")
            + expert_line
        )
        if not use_llm:
            return fallback
        try:
            from llm.client import get_shared_llm
            text = await get_shared_llm().complete(
                prompt=(
                    f"Unified analysis for {v.ticker}:\n{json.dumps(v.components, indent=1)}\n"
                    f"Verdict: {v.verdict} ({v.confidence}%). Risks: {v.risks}\n\n"
                    "Write a 3-4 sentence investor-facing summary in ONE voice: what "
                    "to do, why (the causal story), and the main risk. No hedging boilerplate."
                ),
                system="You are AITradra Prime, the single unified voice of a multi-agent trading platform.",
                temperature=0.3, max_tokens=250, role="analysis",
            )
            return text.strip() if text and text.strip() else fallback
        except Exception:
            return fallback

    def _persist(self, v: UnifiedVerdict) -> None:
        from gateway.knowledge_store import knowledge_store
        snapshot = v.to_dict()
        snapshot.update({
            "recommendation": v.verdict,
            "should_invest": v.verdict == "BUY",
            "prediction_direction": (
                "UP" if v.verdict == "BUY" else "DOWN" if v.verdict == "SELL" else "FLAT"
            ),
            "confidence_score": v.confidence / 100.0,
            "expected_move_percent": round(v.score * 10, 2),
            "risk_level": "LOW" if len(v.risks) <= 1 else "MEDIUM" if len(v.risks) <= 2 else "HIGH",
            "primary_driver": v.primary_driver[:200],
            "position_size_pct": v.position_size_pct,
        })
        try:
            knowledge_store.store_ticker_intelligence(v.ticker, snapshot)
        except Exception as e:
            logger.warning(f"[{AGENT_NAME}] ticker_intelligence persist failed: {e}")
        try:
            knowledge_store.store_insight(
                ticker=v.ticker, agent_name=AGENT_NAME, insight_type="prime_verdict",
                content=json.dumps({
                    "verdict": v.verdict, "confidence": v.confidence,
                    "score": round(v.score, 3), "primary_driver": v.primary_driver,
                    "narrative": v.narrative,
                }, ensure_ascii=False),
                confidence=v.confidence / 100.0,
            )
        except Exception:
            pass
        try:
            knowledge_store.update_agent_health(
                AGENT_NAME, status="active",
                task=f"{v.ticker}: {v.verdict} ({v.confidence}%)",
            )
        except Exception:
            pass

    # ── Portfolio-level briefing: everything, one report ─────────────────────

    async def daily_briefing(self, tickers: Optional[list[str]] = None) -> dict:
        """One report: verdicts, autopilot P&L, commodity events, lessons."""
        from gateway.knowledge_store import knowledge_store

        if tickers is None:
            snaps = knowledge_store.get_all_ticker_intelligence(limit=25)
            tickers = [s.get("ticker") for s in snaps if s.get("ticker")]

        verdicts = knowledge_store.get_all_ticker_intelligence(tickers=tickers or None, limit=25)
        top_buys = sorted(
            (s for s in verdicts if s.get("recommendation") == "BUY"),
            key=lambda s: -(s.get("confidence_score") or 0),
        )[:5]

        autopilot_report = None
        try:
            from agents.paper_autopilot import get_autopilot
            autopilot_report = await get_autopilot().build_report()
        except Exception as e:
            logger.debug(f"[{AGENT_NAME}] Autopilot report unavailable: {e}")

        commodity_events = knowledge_store.get_recent_commodity_events(hours=48, limit=5)

        lessons_stats, recent_lessons = {}, []
        try:
            from memory.reflection_memory import get_memory
            mem = get_memory()
            lessons_stats = mem.stats()
            recent_lessons = mem.get_recent(limit=3)
        except Exception:
            pass

        briefing = {
            "agent": AGENT_NAME,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "headline": self._briefing_headline(top_buys, autopilot_report),
            "top_picks": [
                {
                    "ticker": s.get("ticker"),
                    "verdict": s.get("recommendation"),
                    "confidence": int((s.get("confidence_score") or 0) * 100),
                    "primary_driver": s.get("primary_driver"),
                    "position_size_pct": s.get("position_size_pct", 0),
                }
                for s in top_buys
            ],
            "portfolio": autopilot_report and {
                "equity": autopilot_report["balance"]["equity"],
                "total_return_pct": autopilot_report["balance"]["total_return_pct"],
                "win_rate": autopilot_report["closed_summary"]["win_rate"],
                "open_positions": len(autopilot_report["open_positions"]),
                "realized_pnl": autopilot_report["closed_summary"]["total_realized_pnl"],
            },
            "commodity_watch": [
                {
                    "commodity": e["commodity"], "direction": e["direction"],
                    "cause": e.get("cause_type"), "confidence": e.get("confidence"),
                }
                for e in commodity_events
            ],
            "learning": {"stats": lessons_stats, "latest_lessons": [
                l.get("lesson", "")[:150] for l in recent_lessons
            ]},
        }
        try:
            knowledge_store.store_insight(
                ticker="PORTFOLIO", agent_name=AGENT_NAME, insight_type="prime_briefing",
                content=json.dumps(briefing, ensure_ascii=False), confidence=1.0,
            )
        except Exception:
            pass
        return briefing

    @staticmethod
    def _briefing_headline(top_buys: list, autopilot_report: Optional[dict]) -> str:
        parts = []
        if top_buys:
            best = top_buys[0]
            parts.append(
                f"Top pick: {best.get('ticker')} "
                f"({int((best.get('confidence_score') or 0) * 100)}% conviction)"
            )
        else:
            parts.append("No BUY conviction today — staying patient")
        if autopilot_report:
            bal = autopilot_report["balance"]
            parts.append(
                f"Paper portfolio {bal['total_return_pct']:+.2f}% "
                f"(equity {bal['equity']:,.0f})"
            )
        return ". ".join(parts) + "."


# ── Module-level singleton ────────────────────────────────────────────────────

_master_instance: Optional[MasterAgent] = None


def get_master() -> MasterAgent:
    global _master_instance
    if _master_instance is None:
        _master_instance = MasterAgent()
    return _master_instance
