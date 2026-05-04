"""
Signal Aggregator Agent — Precision Multi-Signal Fusion.

Implements the canonical formula from signal-architecture.md:
  Score = Tech×0.40 + News×0.35 + Social×0.15 + Vol×0.10
  Conviction Multiplier = 1.2× when volume > 1.5× average

Every specialist output is normalized to -1.0/+1.0 before fusion.
Stores predictions for self-improvement accuracy tracking.
"""

from agents.base_agent import BaseAgent, AgentContext
from core.config import settings
from core.logger import get_logger
from core.scoring import (
    calculate_consensus_verdict,
    calibrate_confidence,
    calculate_atr,
    calculate_stop_target,
    get_recommendation,
    get_sizing_multiplier,
)

logger = get_logger(__name__)


def _ohlcv_get(bar: dict, key: str, default=0):
    """Retrieve a value from an OHLCV dict, tolerating both 'Close' and 'close' keys."""
    return bar.get(key, bar.get(key.lower(), bar.get(key[0].lower(), default)))


def _extract_score(output: dict, fallback: float = 0.0) -> float:
    """Extract a normalized score from a specialist output dict."""
    if not isinstance(output, dict):
        return fallback
    # Prefer canonical 'score' field (-1 to +1)
    if "score" in output:
        return max(min(float(output["score"]), 1.0), -1.0)
    # Fall back to signal-based mapping
    sig = output.get("signal", output.get("macro_outlook", "NEUTRAL"))
    conf = output.get("confidence", 0.5)
    if sig in ("BULLISH", "BUY"):
        return conf * 0.8
    elif sig in ("BEARISH", "SELL"):
        return -conf * 0.8
    return 0.0


class SignalAggregatorAgent(BaseAgent):
    """
    Agent: Signal Aggregator — weighted consensus with prediction storage.
    Only trades if consensus > MIN_SIGNAL_CONFIDENCE.
    """

    def __init__(self):
        super().__init__(name="SignalAggregatorAgent", timeout_seconds=60)
        self.min_confidence = settings.MIN_SIGNAL_CONFIDENCE
        self._quantic_validation = None
        self._swarm_consensus = None

    def set_quantic_validation(self, quantic_result: dict):
        self._quantic_validation = quantic_result

    def set_swarm_consensus(self, swarm_result: dict):
        self._swarm_consensus = swarm_result

    async def observe(self, context: AgentContext) -> AgentContext:
        if not context.observations.get("history"):
            self._add_thought(context, "No price history. Signal quality will be reduced.")
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        self._add_thought(context, f"Fusing signals for {context.ticker}")
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan = [
            "1. Extract normalized scores from all specialists",
            "2. Apply weighted consensus formula",
            "3. Calibrate confidence",
            "4. Generate verdict + entry/stop/target",
            "5. Store prediction for accuracy tracking",
        ]
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        ticker = context.ticker
        ohlcv = context.observations.get("history", [])
        sentiment = context.observations.get("sentiment_result", {})
        spec_outputs = context.observations.get("specialist_outputs", {})

        # ─── 1. Extract Normalized Scores ──────────────────────
        tech_score = _extract_score(spec_outputs.get("technical", {}))
        news_score = _extract_score(spec_outputs.get("macro", {}))
        social_score = _extract_score(spec_outputs.get("sentiment", sentiment))
        fund_score = _extract_score(spec_outputs.get("fundamental", {}))
        catalyst_score = _extract_score(spec_outputs.get("catalyst", {}))
        sector_score = _extract_score(spec_outputs.get("sector", {}))

        # Blend social with catalyst and sector for richer social signal
        blended_social = (social_score * 0.5 + catalyst_score * 0.25 + sector_score * 0.25)
        # Blend news with fundamental for richer news signal
        blended_news = (news_score * 0.6 + fund_score * 0.4)

        self._add_thought(context, f"Scores — Tech:{tech_score:+.3f} News:{blended_news:+.3f} "
                          f"Social:{blended_social:+.3f}")

        # ─── 2. Volume Ratio ───────────────────────────────────
        vol_ratio = 1.0
        if ohlcv and len(ohlcv) > 20:
            try:
                volumes = [_ohlcv_get(bar, "Volume", 0) for bar in ohlcv]
                mean_vol = sum(volumes) / len(volumes) if volumes else 0
                last_vol = volumes[0] if volumes else 0
                vol_ratio = last_vol / mean_vol if mean_vol > 0 else 1.0
            except Exception:
                vol_ratio = 1.0

        # ─── 3. Consensus Fusion (canonical formula) ───────────
        consensus = calculate_consensus_verdict(
            tech_score=tech_score,
            news_sentiment=blended_news,
            social_sentiment=blended_social,
            vol_ratio=vol_ratio,
        )

        # ─── 4. Agreement Factor ──────────────────────────────
        all_scores = [tech_score, blended_news, blended_social]
        same_sign = all(s >= 0 for s in all_scores) or all(s <= 0 for s in all_scores)
        agreement = 1.2 if same_sign and consensus["is_strong"] else (1.0 if same_sign else 0.8)

        # ─── 5. Confidence Calibration ─────────────────────────
        confidence = calibrate_confidence(
            base_score=consensus["score"],
            data_points=len(ohlcv),
            headline_count=len(context.observations.get("news", [])),
            agreement_factor=agreement,
        )

        # ─── 6. Quantic Validation ─────────────────────────────
        institutional_alignment = False
        if self._quantic_validation and self._quantic_validation.get("success"):
            q = self._quantic_validation
            smc_signal = q.get("smc", {}).get("signal", "NEUTRAL")
            smc_conf = q.get("smc", {}).get("confidence", 0.5)
            confidence += (smc_conf - 0.5) * 15
            smc_dir = 1 if smc_signal == "BULLISH" else (-1 if smc_signal == "BEARISH" else 0)
            con_dir = 1 if consensus["direction"] == "BUY" else (-1 if consensus["direction"] == "SELL" else 0)
            institutional_alignment = (smc_dir == con_dir and smc_dir != 0)
            if smc_dir != 0 and smc_dir != con_dir:
                confidence *= 0.65
                self._add_thought(context, f"⚠️ SMC divergence: {smc_signal} vs {consensus['direction']}")
            context.metadata["quantic_validated"] = True
            context.metadata["smart_money_score"] = smc_conf

        # ─── 7. Swarm Validation ───────────────────────────────
        if self._swarm_consensus and self._swarm_consensus.get("success"):
            swarm_conf = self._swarm_consensus.get("confidence", 0.5)
            confidence = confidence * 0.75 + swarm_conf * 100 * 0.25
            context.metadata["swarm_consensus"] = True

        # ─── 8. Final Verdict ──────────────────────────────────
        confidence = max(10.0, min(95.0, confidence))

        # Risk level from risk specialist
        risk_level = spec_outputs.get("risk", {}).get("risk_level", "MEDIUM")
        verdict = get_recommendation(consensus["direction"], confidence, risk_level)

        # ─── 9. Entry / Stop / Target ──────────────────────────
        last_price = _ohlcv_get(ohlcv[0], "Close", 0) if ohlcv else 0
        atr = calculate_atr(ohlcv) if ohlcv else 0
        levels = calculate_stop_target(last_price, atr, "BUY" if "BUY" in verdict else "SELL")

        sizing = get_sizing_multiplier(confidence)

        context.result = {
            "symbol": ticker,
            "verdict": verdict,
            "final_score": consensus["score"],
            "confidence": confidence,
            "institutional_alignment": institutional_alignment,
            "sizing_multiplier": sizing,
            "signals": {
                "technical": round(tech_score, 3),
                "news": round(blended_news, 3),
                "social": round(blended_social, 3),
                "volume": round(vol_ratio, 2),
            },
            "entry_point": last_price,
            "stop_loss": levels["stop_loss"],
            "take_profit": levels["take_profit"],
            "risk_reward_ratio": levels["risk_reward_ratio"],
            "metadata": {
                "quantic_validated": context.metadata.get("quantic_validated", False),
                "smart_money_score": context.metadata.get("smart_money_score", 0),
                "institutional_alignment": institutional_alignment,
                "swarm_consensus": context.metadata.get("swarm_consensus", False),
                "agreement_factor": agreement,
                "risk_level": risk_level,
            },
        }

        self._add_thought(context, f"Fusion: {consensus['score']:+.4f} → {verdict} (conf={confidence:.0f}%)")
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        """Store prediction for accuracy tracking, then reflect."""
        v = context.result or {}
        verdict = v.get("verdict", "HOLD")
        confidence = v.get("confidence", 0.0)

        context.reflection = f"Consensus for {context.ticker}: {verdict} ({confidence:.0f}%)"
        context.confidence = confidence

        if v.get("institutional_alignment"):
            context.reflection += " ✓ Institutional Alignment"

        # ─── Store prediction for self-improvement ─────────────
        if context.ticker and verdict not in ("HOLD",):
            try:
                from gateway.knowledge_store import knowledge_store
                knowledge_store.store_insight(
                    ticker=context.ticker,
                    agent_name=self.name,
                    insight_type="prediction",
                    content=f"{verdict} @ {v.get('entry_point', 0)} | "
                            f"target={v.get('take_profit', 0)} stop={v.get('stop_loss', 0)}",
                    confidence=int(confidence),
                )
            except Exception:
                pass

        # Reset validation state
        self._quantic_validation = None
        self._swarm_consensus = None
        return context
