"""
agents/debate_engine.py
────────────────────────────────────────────────────────────────────────────────
DebateEngine — Adversarial Bull vs Bear research debate + risk-stance sizing.

Inspired by TauricResearch/TradingAgents: instead of letting one synthesis
step average specialist opinions (which buries disagreement), two dedicated
researchers argue OPPOSITE sides of the trade across multiple rounds, each
forced to rebut the other's strongest points. A judge then issues the verdict.
This surfaces the strongest counter-argument to any trade BEFORE money moves.

Pipeline per ticker:
  1. EVIDENCE   — gather specialist insights, commodity impacts, news
                  sentiment, price trend, and past trade lessons.
  2. DEBATE     — N rounds of Bull argument → Bear rebuttal (LLM-driven,
                  with a deterministic evidence-scoring fallback).
  3. VERDICT    — judge weighs both cases → BUY/SELL/HOLD + confidence.
  4. RISK BENCH — three risk stances (aggressive / neutral / conservative)
                  each propose a position size; the bench blends them based
                  on debate confidence and evidence quality.
  5. PERSIST    — full transcript to debate_records, verdict to
                  agent_insights (auto-indexed into RAG for chat).

Everything works offline: without an LLM, arguments are built from the
evidence lists themselves and the verdict comes from the deterministic
evidence score, so the debate layer never blocks the pipeline.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from core.logger import get_logger

logger = get_logger(__name__)

AGENT_NAME = "DebateEngine"

BULL_SYSTEM = (
    "You are the BULL researcher on an institutional trading desk. Argue the "
    "strongest possible case FOR buying the asset using ONLY the evidence "
    "provided. Directly rebut the bear's latest points when given. Be concrete "
    "and cite the evidence items you rely on. 4-6 sentences, no fluff."
)
BEAR_SYSTEM = (
    "You are the BEAR researcher on an institutional trading desk. Argue the "
    "strongest possible case AGAINST buying (or for selling) the asset using "
    "ONLY the evidence provided. Directly rebut the bull's latest points. Be "
    "concrete and cite the evidence items you rely on. 4-6 sentences, no fluff."
)
JUDGE_SYSTEM = (
    "You are the research director judging a bull-vs-bear debate. Weigh the "
    "arguments strictly on evidence quality, not rhetoric. Return VALID JSON "
    'only: {"verdict": "BUY|SELL|HOLD", "confidence": <0-100>, '
    '"winning_side": "BULL|BEAR|DRAW", "key_reason": "<1-2 sentences>", '
    '"strongest_bull_point": "<sentence>", "strongest_bear_point": "<sentence>"}'
)


@dataclass
class DebateResult:
    ticker:         str
    verdict:        str                 # BUY | SELL | HOLD
    confidence:     int                 # 0-100
    winning_side:   str                 # BULL | BEAR | DRAW
    key_reason:     str
    bull_case:      list[str] = field(default_factory=list)
    bear_case:      list[str] = field(default_factory=list)
    transcript:     list[dict] = field(default_factory=list)   # [{round, side, argument}]
    risk_bench:     dict = field(default_factory=dict)
    evidence_score: float = 0.0         # deterministic score, -1 (bearish) .. +1 (bullish)
    evidence_count: int = 0
    mode:           str = "rule_based"  # llm | rule_based
    created_at:     str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "verdict": self.verdict,
            "confidence": self.confidence,
            "winning_side": self.winning_side,
            "key_reason": self.key_reason,
            "bull_case": self.bull_case,
            "bear_case": self.bear_case,
            "transcript": self.transcript,
            "risk_bench": self.risk_bench,
            "evidence_score": round(self.evidence_score, 3),
            "evidence_count": self.evidence_count,
            "mode": self.mode,
            "created_at": self.created_at,
        }


BULLISH_WORDS = ["BULLISH", "BUY", "STRONG BUY", "UPGRADE", "POSITIVE", "OUTPERFORM", "UP"]
BEARISH_WORDS = ["BEARISH", "SELL", "AVOID", "DOWNGRADE", "NEGATIVE", "UNDERPERFORM", "DOWN"]


class DebateEngine:
    """Runs adversarial research debates over the platform's collected evidence."""

    def __init__(self, max_rounds: int = 2):
        self.max_rounds = max_rounds

    # ── Evidence gathering ───────────────────────────────────────────────────

    def gather_evidence(self, ticker: str) -> dict:
        """Collect bull and bear evidence from everything the platform knows."""
        from gateway.knowledge_store import knowledge_store

        bull: list[str] = []
        bear: list[str] = []
        neutral: list[str] = []

        # 1. Specialist + commodity insights (last 48h)
        try:
            insights = knowledge_store.get_recent_insights(ticker, hours=48, limit=40)
        except Exception:
            insights = []
        for ins in insights:
            content = str(ins.get("content", ""))[:300]
            agent = ins.get("agent_name", "agent")
            upper = content.upper()
            item = f"[{agent}] {content}"
            if any(w in upper for w in BULLISH_WORDS):
                bull.append(item)
            elif any(w in upper for w in BEARISH_WORDS):
                bear.append(item)
            else:
                neutral.append(item)

        # 2. News sentiment
        try:
            news = knowledge_store.get_news_for_ticker(ticker, limit=15, days=3)
        except Exception:
            news = []
        for art in news:
            score = art.get("sentiment_score") or 0.0
            item = f"[news:{art.get('source', '?')}] {art.get('headline', '')[:200]}"
            if score > 0.15:
                bull.append(item)
            elif score < -0.15:
                bear.append(item)
            else:
                neutral.append(item)

        # 3. Price trend (20-bar momentum)
        try:
            bars = knowledge_store.get_ohlcv_history(ticker, days=45)
            if len(bars) >= 5:
                closes = [b["close"] for b in bars if b.get("close")]
                newest, oldest = closes[0], closes[min(len(closes) - 1, 20)]
                if oldest:
                    chg = (newest - oldest) / oldest * 100
                    item = f"[price] {ticker} moved {chg:+.1f}% over ~{min(len(closes), 20)} bars"
                    (bull if chg > 2 else bear if chg < -2 else neutral).append(item)
        except Exception:
            pass

        # 4. Past trade lessons (reflection memory)
        try:
            from memory.reflection_memory import get_memory
            for lesson in get_memory().get_lessons_for(ticker, limit=3):
                neutral.append(f"[lesson] {lesson.get('lesson', '')[:250]}")
        except Exception:
            pass

        return {"bull": bull[:12], "bear": bear[:12], "neutral": neutral[:8]}

    # ── Deterministic core (always available) ────────────────────────────────

    @staticmethod
    def score_evidence(evidence: dict) -> float:
        """Net evidence score in [-1, 1]: >0 bullish, <0 bearish."""
        n_bull, n_bear = len(evidence["bull"]), len(evidence["bear"])
        total = n_bull + n_bear
        if total == 0:
            return 0.0
        return (n_bull - n_bear) / total

    def _rule_based_verdict(self, ticker: str, evidence: dict) -> DebateResult:
        score = self.score_evidence(evidence)
        n = len(evidence["bull"]) + len(evidence["bear"])
        # Confidence needs both a clear skew AND enough evidence
        confidence = int(min(90, abs(score) * 60 + min(n, 10) * 3))
        if score >= 0.35 and confidence >= 50:
            verdict, side = "BUY", "BULL"
        elif score <= -0.35 and confidence >= 50:
            verdict, side = "SELL", "BEAR"
        else:
            verdict, side = "HOLD", "DRAW"
        return DebateResult(
            ticker=ticker,
            verdict=verdict,
            confidence=confidence,
            winning_side=side,
            key_reason=(
                f"Evidence skew {score:+.2f} across {n} directional items "
                f"({len(evidence['bull'])} bullish vs {len(evidence['bear'])} bearish)"
            ),
            bull_case=evidence["bull"][:5],
            bear_case=evidence["bear"][:5],
            evidence_score=score,
            evidence_count=n,
            mode="rule_based",
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    # ── LLM debate rounds ────────────────────────────────────────────────────

    async def _llm_debate(self, ticker: str, evidence: dict) -> Optional[DebateResult]:
        """Run the full multi-round debate with the LLM. Returns None on failure."""
        try:
            from llm.client import get_shared_llm
            llm = get_shared_llm()

            def fmt(items: list[str]) -> str:
                return "\n".join(f"- {i}" for i in items) or "- (none)"

            evidence_block = (
                f"TICKER: {ticker}\n\nBULLISH EVIDENCE:\n{fmt(evidence['bull'])}\n\n"
                f"BEARISH EVIDENCE:\n{fmt(evidence['bear'])}\n\n"
                f"CONTEXT / LESSONS:\n{fmt(evidence['neutral'])}"
            )

            transcript: list[dict] = []
            bull_last, bear_last = "", ""
            for rnd in range(1, self.max_rounds + 1):
                bull_prompt = evidence_block + (
                    f"\n\nBEAR'S LATEST ARGUMENT TO REBUT:\n{bear_last}" if bear_last else
                    "\n\nOpen the debate with your strongest bull case."
                )
                bull_last = await llm.complete(
                    prompt=bull_prompt, system=BULL_SYSTEM,
                    temperature=0.4, max_tokens=400, role="reasoning",
                )
                if not (bull_last or "").strip():
                    return None
                transcript.append({"round": rnd, "side": "BULL", "argument": bull_last.strip()})

                bear_prompt = evidence_block + f"\n\nBULL'S LATEST ARGUMENT TO REBUT:\n{bull_last}"
                bear_last = await llm.complete(
                    prompt=bear_prompt, system=BEAR_SYSTEM,
                    temperature=0.4, max_tokens=400, role="reasoning",
                )
                if not (bear_last or "").strip():
                    return None
                transcript.append({"round": rnd, "side": "BEAR", "argument": bear_last.strip()})

            debate_text = "\n\n".join(
                f"ROUND {t['round']} — {t['side']}:\n{t['argument']}" for t in transcript
            )
            raw = await llm.complete(
                prompt=f"{evidence_block}\n\nDEBATE TRANSCRIPT:\n{debate_text}\n\nJudge the debate now.",
                system=JUDGE_SYSTEM, expect_json=True,
                temperature=0.1, max_tokens=400, role="analysis",
            )
            data = json.loads(raw) if isinstance(raw, str) else raw
            verdict = str(data.get("verdict", "HOLD")).upper()
            if verdict not in ("BUY", "SELL", "HOLD"):
                verdict = "HOLD"
            return DebateResult(
                ticker=ticker,
                verdict=verdict,
                confidence=max(0, min(100, int(data.get("confidence", 50)))),
                winning_side=str(data.get("winning_side", "DRAW")).upper(),
                key_reason=str(data.get("key_reason", "")),
                bull_case=[str(data.get("strongest_bull_point", ""))] + evidence["bull"][:4],
                bear_case=[str(data.get("strongest_bear_point", ""))] + evidence["bear"][:4],
                transcript=transcript,
                evidence_score=self.score_evidence(evidence),
                evidence_count=len(evidence["bull"]) + len(evidence["bear"]),
                mode="llm",
                created_at=datetime.now(timezone.utc).isoformat(),
            )
        except Exception as e:
            logger.debug(f"[{AGENT_NAME}] LLM debate unavailable for {ticker}: {e}")
            return None

    # ── Risk bench (aggressive / neutral / conservative) ─────────────────────

    @staticmethod
    def run_risk_bench(result: DebateResult) -> dict:
        """
        Three risk stances propose position sizes; the bench blends them.
        Sizes are % of portfolio, capped by the platform's MAX_POSITION_PCT.
        """
        conf = result.confidence / 100.0
        if result.verdict == "HOLD":
            stances = {
                "aggressive":   {"size_pct": 0.0, "note": "No edge — even aggressive stance passes"},
                "neutral":      {"size_pct": 0.0, "note": "HOLD verdict — stay flat"},
                "conservative": {"size_pct": 0.0, "note": "Stay flat, keep cash reserve"},
            }
            blended = 0.0
        else:
            aggressive = round(min(10.0, conf * 12.0), 1)
            neutral_sz = round(min(10.0, conf * 8.0), 1)
            conservative = round(min(5.0, conf * 4.0) if conf >= 0.6 else 0.0, 1)
            stances = {
                "aggressive": {
                    "size_pct": aggressive,
                    "note": "Debate winner is clear — press the edge while the catalyst is fresh",
                },
                "neutral": {
                    "size_pct": neutral_sz,
                    "note": "Standard conviction-weighted sizing",
                },
                "conservative": {
                    "size_pct": conservative,
                    "note": ("Bear case unresolved — half size with tight stop"
                             if conservative > 0 else
                             "Confidence below 60% — conservative stance blocks the trade"),
                },
            }
            # Blend: low evidence count drags the blend toward conservative
            evidence_quality = min(result.evidence_count, 10) / 10.0
            w_aggr = 0.2 * evidence_quality
            w_cons = 0.4 - 0.2 * evidence_quality
            blended = round(
                aggressive * w_aggr + neutral_sz * 0.4 + conservative * (w_cons + 0.2), 1
            )
        return {
            "stances": stances,
            "blended_size_pct": blended,
            "recommendation": (
                f"{result.verdict} with {blended}% of portfolio"
                if blended > 0 else "No position — verdict or confidence too weak"
            ),
        }

    # ── Public API ───────────────────────────────────────────────────────────

    async def run_debate(self, ticker: str, use_llm: bool = True) -> DebateResult:
        """Full pipeline: evidence → debate → verdict → risk bench → persist."""
        ticker = ticker.upper()
        evidence = self.gather_evidence(ticker)

        result: Optional[DebateResult] = None
        if use_llm:
            result = await self._llm_debate(ticker, evidence)
        if result is None:
            result = self._rule_based_verdict(ticker, evidence)

        result.risk_bench = self.run_risk_bench(result)
        self._persist(result)
        logger.info(
            f"[{AGENT_NAME}] {ticker}: {result.verdict} ({result.confidence}%) "
            f"winner={result.winning_side} mode={result.mode}"
        )
        return result

    def _persist(self, result: DebateResult) -> None:
        from gateway.knowledge_store import knowledge_store
        try:
            knowledge_store.store_debate_record(result.to_dict())
        except Exception as e:
            logger.warning(f"[{AGENT_NAME}] Failed to persist debate record: {e}")
        try:
            knowledge_store.store_insight(
                ticker=result.ticker,
                agent_name=AGENT_NAME,
                insight_type="debate_verdict",
                content=json.dumps({
                    "verdict": result.verdict,
                    "confidence": result.confidence,
                    "winning_side": result.winning_side,
                    "key_reason": result.key_reason,
                    "position_size_pct": result.risk_bench.get("blended_size_pct"),
                }, ensure_ascii=False),
                confidence=result.confidence / 100.0,
            )
        except Exception as e:
            logger.debug(f"[{AGENT_NAME}] Verdict insight store skipped: {e}")
        try:
            knowledge_store.update_agent_health(
                AGENT_NAME, status="active",
                task=f"Debate {result.ticker}: {result.verdict} ({result.confidence}%)",
            )
        except Exception:
            pass


# ── Module-level singleton ────────────────────────────────────────────────────

_engine_instance: Optional[DebateEngine] = None


def get_engine() -> DebateEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = DebateEngine()
    return _engine_instance
