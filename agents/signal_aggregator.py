"""Signal Aggregator Agent — precision multi-signal and technical-only fusion."""

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
    """Retrieve a value from an OHLCV dict, tolerating upper/lower-case keys."""
    return bar.get(key, bar.get(key.lower(), bar.get(key[0].lower(), default)))


def _extract_score(output: dict, fallback: float = 0.0) -> float:
    if not isinstance(output, dict):
        return fallback
    if "score" in output:
        return max(min(float(output["score"]), 1.0), -1.0)
    signal = str(output.get("signal", output.get("macro_outlook", "NEUTRAL"))).upper()
    confidence = float(output.get("confidence", 0.5) or 0.5)
    if confidence > 1:
        confidence /= 100
    if signal in ("BULLISH", "BUY", "LONG", "STRONG BUY"):
        return max(min(confidence * 0.8, 1.0), 0.0)
    if signal in ("BEARISH", "SELL", "SHORT", "STRONG SELL"):
        return -max(min(confidence * 0.8, 1.0), 0.0)
    return 0.0


def _confidence_pct(value: float) -> float:
    value = float(value or 0)
    return value * 100 if value <= 1 else value


class SignalAggregatorAgent(BaseAgent):
    """Fuse available evidence while respecting the type of strategy being run."""

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
        if not (
            context.metadata.get("ohlcv_data")
            or context.observations.get("history")
        ):
            self._add_thought(context, "No price history. Signal quality will be reduced.")
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        self._add_thought(context, f"Fusing available signals for {context.ticker}")
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan = [
            "1. Normalize available specialist signals",
            "2. Detect multi-source versus technical-only strategy context",
            "3. Calculate directional consensus",
            "4. Calibrate confidence for the evidence actually available",
            "5. Apply configured confidence gate",
            "6. Generate entry, stop and target levels",
        ]
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        ticker = context.ticker
        ohlcv = (
            context.metadata.get("ohlcv_data")
            or context.observations.get("history")
            or []
        )
        sentiment = context.observations.get("sentiment_result", {}) or {}
        spec_outputs = (
            context.observations.get("specialist_outputs")
            or context.metadata.get("specialist_outputs")
            or {}
        )
        news_items = context.observations.get("news", []) or []

        technical_output = spec_outputs.get("technical", {}) or {}
        tech_score = _extract_score(technical_output)
        news_score = _extract_score(spec_outputs.get("macro", {}))
        social_score = _extract_score(spec_outputs.get("sentiment", sentiment))
        fund_score = _extract_score(spec_outputs.get("fundamental", {}))
        catalyst_score = _extract_score(spec_outputs.get("catalyst", {}))
        sector_score = _extract_score(spec_outputs.get("sector", {}))

        non_technical_present = any(
            bool(spec_outputs.get(name))
            for name in ("macro", "sentiment", "fundamental", "catalyst", "sector")
        ) or bool(news_items)
        technical_only = bool(technical_output) and not non_technical_present

        # A technical-only strategy must not be treated as if missing news were bad
        # news. If an upstream technical agent supplied an overly weak placeholder
        # score, derive direction strength from its actual confidence instead.
        technical_confidence = _confidence_pct(technical_output.get("confidence", 0.5))
        technical_signal = str(technical_output.get("signal", "NEUTRAL")).upper()
        if technical_only:
            directional_floor = max(0.0, min(technical_confidence / 100 * 0.8, 1.0))
            if technical_signal in ("BULLISH", "BUY", "LONG", "STRONG BUY"):
                tech_score = max(tech_score, directional_floor)
            elif technical_signal in ("BEARISH", "SELL", "SHORT", "STRONG SELL"):
                tech_score = min(tech_score, -directional_floor)

        blended_social = (
            social_score * 0.5 + catalyst_score * 0.25 + sector_score * 0.25
        )
        blended_news = news_score * 0.6 + fund_score * 0.4

        self._add_thought(
            context,
            f"Scores — Tech:{tech_score:+.3f} News:{blended_news:+.3f} "
            f"Social:{blended_social:+.3f} mode={'technical-only' if technical_only else 'multi-source'}",
        )

        vol_ratio = 1.0
        if ohlcv and len(ohlcv) > 20:
            try:
                volumes = [_ohlcv_get(bar, "Volume", 0) for bar in ohlcv]
                mean_vol = sum(volumes) / len(volumes) if volumes else 0
                last_vol = volumes[0] if volumes else 0
                vol_ratio = last_vol / mean_vol if mean_vol > 0 else 1.0
            except Exception:
                vol_ratio = 1.0

        consensus = calculate_consensus_verdict(
            tech_score=tech_score,
            news_sentiment=0.0 if technical_only else blended_news,
            social_sentiment=0.0 if technical_only else blended_social,
            vol_ratio=vol_ratio,
        )

        all_scores = [tech_score] if technical_only else [
            tech_score,
            blended_news,
            blended_social,
        ]
        same_sign = (
            all(score >= 0 for score in all_scores)
            or all(score <= 0 for score in all_scores)
        )
        agreement = (
            1.0
            if technical_only
            else 1.2
            if same_sign and consensus["is_strong"]
            else 1.0
            if same_sign
            else 0.8
        )

        if technical_only:
            data_quality_pct = min(100.0, len(ohlcv))
            confidence = technical_confidence * 0.75 + data_quality_pct * 0.25
            confidence = max(10.0, min(95.0, confidence))
        else:
            confidence = calibrate_confidence(
                base_score=consensus["score"],
                data_points=len(ohlcv),
                headline_count=len(news_items),
                agreement_factor=agreement,
            )

        institutional_alignment = False
        if self._quantic_validation and self._quantic_validation.get("success"):
            quantic = self._quantic_validation
            smc_signal = quantic.get("smc", {}).get("signal", "NEUTRAL")
            smc_conf = quantic.get("smc", {}).get("confidence", 0.5)
            confidence += (smc_conf - 0.5) * 15
            smc_dir = 1 if smc_signal == "BULLISH" else -1 if smc_signal == "BEARISH" else 0
            consensus_dir = 1 if consensus["direction"] == "BUY" else -1 if consensus["direction"] == "SELL" else 0
            institutional_alignment = smc_dir == consensus_dir and smc_dir != 0
            if smc_dir != 0 and smc_dir != consensus_dir:
                confidence *= 0.65
                self._add_thought(
                    context,
                    f"SMC divergence: {smc_signal} vs {consensus['direction']}",
                )
            context.metadata["quantic_validated"] = True
            context.metadata["smart_money_score"] = smc_conf

        if self._swarm_consensus and self._swarm_consensus.get("success"):
            swarm_conf = self._swarm_consensus.get("confidence", 0.5)
            confidence = confidence * 0.75 + _confidence_pct(swarm_conf) * 0.25
            context.metadata["swarm_consensus"] = True

        confidence = max(10.0, min(95.0, confidence))
        risk_level = spec_outputs.get("risk", {}).get("risk_level", "MEDIUM")
        verdict = get_recommendation(
            consensus["direction"], confidence, risk_level
        )

        configured_min = (
            self.min_confidence * 100
            if self.min_confidence <= 1
            else self.min_confidence
        )
        if confidence < configured_min:
            verdict = "HOLD"

        last_price = _ohlcv_get(ohlcv[0], "Close", 0) if ohlcv else 0
        atr = calculate_atr(ohlcv) if ohlcv else 0
        if consensus["direction"] in ("BUY", "SELL") and last_price > 0:
            levels = calculate_stop_target(
                last_price,
                atr,
                consensus["direction"],
            )
        else:
            levels = {
                "stop_loss": 0,
                "take_profit": 0,
                "risk_reward_ratio": 0,
            }

        sizing = get_sizing_multiplier(confidence) if verdict != "HOLD" else 0.0
        context.result = {
            "symbol": ticker,
            "verdict": verdict,
            "direction": consensus["direction"],
            "final_score": consensus["score"],
            "confidence": round(confidence, 1),
            "institutional_alignment": institutional_alignment,
            "sizing_multiplier": sizing,
            "signal_mode": "technical_only" if technical_only else "multi_source",
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
                "configured_min_confidence": configured_min,
            },
        }

        self._add_thought(
            context,
            f"Fusion: {consensus['score']:+.4f} -> {verdict} (conf={confidence:.0f}%)",
        )
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        result = context.result or {}
        verdict = result.get("verdict", "HOLD")
        confidence = result.get("confidence", 0.0)
        context.reflection = (
            f"Consensus for {context.ticker}: {verdict} ({confidence:.0f}%)"
        )
        context.confidence = confidence

        if result.get("institutional_alignment"):
            context.reflection += " - institutional alignment"

        if context.ticker and verdict != "HOLD":
            try:
                from gateway.knowledge_store import knowledge_store

                knowledge_store.store_insight(
                    ticker=context.ticker,
                    agent_name=self.name,
                    insight_type="prediction",
                    content=(
                        f"{verdict} @ {result.get('entry_point', 0)} | "
                        f"target={result.get('take_profit', 0)} "
                        f"stop={result.get('stop_loss', 0)}"
                    ),
                    confidence=int(confidence),
                )
            except Exception:
                pass

        self._quantic_validation = None
        self._swarm_consensus = None
        return context
