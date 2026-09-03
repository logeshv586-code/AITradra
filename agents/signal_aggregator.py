"""Signal Aggregator Agent — evidence-aware multi-signal fusion.

Optional plugins do not receive positive confidence credit merely because they
returned successfully. FinBERT/Quantic/Swarm outputs are captured into the shadow
ledger for forward ablation. Mature shadow decisions are resolved against later
measured prices before plugin policies are recalculated. Until a plugin has enough
resolved evidence and the Plugin Ablation Lab marks it KEEP, it is advisory-only.
"""

from __future__ import annotations

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
    return bar.get(key, bar.get(key.lower(), bar.get(key[0].lower(), default)))


def _extract_score(output: dict, fallback: float = 0.0) -> float:
    if not isinstance(output, dict):
        return fallback
    if "score" in output:
        try:
            return max(min(float(output["score"]), 1.0), -1.0)
        except (TypeError, ValueError):
            return fallback
    signal = str(output.get("signal", output.get("macro_outlook", "NEUTRAL"))).upper()
    try:
        confidence = float(output.get("confidence", 0.5) or 0.5)
    except (TypeError, ValueError):
        confidence = 0.5
    if confidence > 1:
        confidence /= 100
    if signal in ("BULLISH", "BUY", "LONG", "STRONG BUY"):
        return max(min(confidence * 0.8, 1.0), 0.0)
    if signal in ("BEARISH", "SELL", "SHORT", "STRONG SELL"):
        return -max(min(confidence * 0.8, 1.0), 0.0)
    return 0.0


def _confidence_pct(value: float) -> float:
    try:
        value = float(value or 0)
    except (TypeError, ValueError):
        return 0.0
    return value * 100 if value <= 1 else value


def _probability_from_direction(direction: str, confidence: float) -> float | None:
    direction = str(direction or "").upper()
    conf = max(0.0, min(_confidence_pct(confidence) / 100.0, 1.0))
    if direction in {"BUY", "BULLISH", "LONG", "UP"}:
        return round(0.5 + conf * 0.5, 6)
    if direction in {"SELL", "BEARISH", "SHORT", "DOWN"}:
        return round(0.5 - conf * 0.5, 6)
    return None


class SignalAggregatorAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="SignalAggregatorAgent", timeout_seconds=60)
        self.min_confidence = settings.MIN_SIGNAL_CONFIDENCE
        self._quantic_validation = None
        self._swarm_consensus = None

    def set_quantic_validation(self, quantic_result: dict):
        self._quantic_validation = quantic_result

    def set_swarm_consensus(self, swarm_result: dict):
        self._swarm_consensus = swarm_result

    @staticmethod
    def _plugin_report() -> dict:
        try:
            from self_improvement.plugin_ablation import plugin_ablation_lab
            from self_improvement.shadow_trade_store import shadow_trade_store

            rows = shadow_trade_store.resolved_decisions(limit=1000)
            return plugin_ablation_lab.evaluate(
                rows, plugins=["finbert", "quantic", "swarm"]
            )
        except Exception as exc:
            logger.debug("Plugin ablation report unavailable: %s", exc)
            return {
                "results": {
                    name: {"policy": "ADVISORY", "samples": 0}
                    for name in ("finbert", "quantic", "swarm")
                }
            }

    async def observe(self, context: AgentContext) -> AgentContext:
        if not (context.metadata.get("ohlcv_data") or context.observations.get("history")):
            self._add_thought(context, "No price history. Signal quality will be reduced.")
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        self._add_thought(context, f"Fusing measured signals for {context.ticker}")
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan = [
            "Resolve matured shadow decisions against later measured prices",
            "Normalize core specialist signals",
            "Read empirical plugin-ablation policy",
            "Keep unproven plugins advisory-only",
            "Apply conservative contradiction vetoes",
            "Calibrate confidence and write active decisions to the immutable shadow ledger",
        ]
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        ticker = context.ticker
        ohlcv = context.metadata.get("ohlcv_data") or context.observations.get("history") or []
        finbert = context.observations.get("sentiment_result", {}) or {}
        spec_outputs = (
            context.observations.get("specialist_outputs")
            or context.metadata.get("specialist_outputs")
            or {}
        )
        news_items = context.observations.get("news", []) or []

        shadow_resolution = {
            "due": 0,
            "resolved": 0,
            "failed": 0,
            "execution_authority": False,
        }
        try:
            from self_improvement.shadow_resolver import resolve_due_shadow_decisions

            shadow_resolution = await resolve_due_shadow_decisions(limit=50)
        except Exception as exc:
            logger.debug("Shadow resolution unavailable: %s", exc)

        plugin_report = self._plugin_report()
        plugin_results = plugin_report.get("results", {})

        technical_output = spec_outputs.get("technical", {}) or {}
        tech_score = _extract_score(technical_output)
        news_score = _extract_score(spec_outputs.get("macro", {}))
        legacy_social_score = _extract_score(spec_outputs.get("sentiment", {}))
        fund_score = _extract_score(spec_outputs.get("fundamental", {}))
        catalyst_score = _extract_score(spec_outputs.get("catalyst", {}))
        sector_score = _extract_score(spec_outputs.get("sector", {}))

        finbert_verified = bool(finbert.get("model_verified"))
        finbert_score = _extract_score(finbert) if finbert_verified else 0.0
        finbert_policy = str(plugin_results.get("finbert", {}).get("policy", "ADVISORY"))
        social_score = legacy_social_score
        if finbert_verified and finbert_policy == "KEEP":
            social_score = legacy_social_score * 0.70 + finbert_score * 0.30
            self._add_thought(context, "FinBERT has measured incremental value and receives bounded signal weight")
        elif finbert_verified:
            self._add_thought(context, "FinBERT captured for shadow ablation; no live confidence credit yet")

        non_technical_present = any(
            bool(spec_outputs.get(name))
            for name in ("macro", "sentiment", "fundamental", "catalyst", "sector")
        ) or bool(news_items)
        technical_only = bool(technical_output) and not non_technical_present

        technical_confidence = _confidence_pct(technical_output.get("confidence", 0.5))
        technical_signal = str(technical_output.get("signal", "NEUTRAL")).upper()
        if technical_only:
            directional_floor = max(0.0, min(technical_confidence / 100 * 0.8, 1.0))
            if technical_signal in ("BULLISH", "BUY", "LONG", "STRONG BUY"):
                tech_score = max(tech_score, directional_floor)
            elif technical_signal in ("BEARISH", "SELL", "SHORT", "STRONG SELL"):
                tech_score = min(tech_score, -directional_floor)

        blended_social = social_score * 0.5 + catalyst_score * 0.25 + sector_score * 0.25
        blended_news = news_score * 0.6 + fund_score * 0.4

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
        all_scores = [tech_score] if technical_only else [tech_score, blended_news, blended_social]
        same_sign = all(score >= 0 for score in all_scores) or all(score <= 0 for score in all_scores)
        agreement = (
            1.0 if technical_only else 1.2 if same_sign and consensus["is_strong"] else 1.0 if same_sign else 0.8
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
        quantic_snapshot: dict = {}
        if self._quantic_validation and self._quantic_validation.get("success"):
            quantic = self._quantic_validation
            smc = quantic.get("smc", {}) or {}
            smc_signal = str(smc.get("signal", "NEUTRAL")).upper()
            smc_conf = _confidence_pct(smc.get("confidence", 0.5)) / 100.0
            smc_dir = 1 if smc_signal == "BULLISH" else -1 if smc_signal == "BEARISH" else 0
            consensus_dir = 1 if consensus["direction"] == "BUY" else -1 if consensus["direction"] == "SELL" else 0
            institutional_alignment = smc_dir == consensus_dir and smc_dir != 0
            quantic_snapshot = {
                "direction": smc_signal,
                "confidence": round(smc_conf, 6),
                "probability_up": _probability_from_direction(smc_signal, smc_conf),
                "policy": plugin_results.get("quantic", {}).get("policy", "ADVISORY"),
            }
            if smc_dir != 0 and consensus_dir != 0 and smc_dir != consensus_dir:
                confidence *= 0.65
                self._add_thought(context, f"Quantic/SMC contradiction: {smc_signal} vs {consensus['direction']} — confidence reduced")
            elif institutional_alignment and quantic_snapshot["policy"] == "KEEP":
                confidence *= 1.02
            context.metadata["quantic_validated"] = True
            context.metadata["smart_money_score"] = smc_conf

        swarm_snapshot: dict = {}
        if self._swarm_consensus and self._swarm_consensus.get("success"):
            swarm_snapshot = {
                "confidence": 0.5,
                "policy": plugin_results.get("swarm", {}).get("policy", "ADVISORY"),
                "advisory_only": True,
            }
            if self._swarm_consensus.get("divergence"):
                confidence *= 0.80
                self._add_thought(context, "Swarm divergence reported — confidence reduced")
            context.metadata["swarm_consensus"] = True

        confidence = max(10.0, min(95.0, confidence))
        risk_level = spec_outputs.get("risk", {}).get("risk_level", "MEDIUM")
        verdict = get_recommendation(consensus["direction"], confidence, risk_level)
        configured_min = self.min_confidence * 100 if self.min_confidence <= 1 else self.min_confidence
        if confidence < configured_min:
            verdict = "HOLD"

        last_price = _ohlcv_get(ohlcv[0], "Close", 0) if ohlcv else 0
        atr = calculate_atr(ohlcv) if ohlcv else 0
        if consensus["direction"] in ("BUY", "SELL") and last_price > 0:
            levels = calculate_stop_target(last_price, atr, consensus["direction"])
        else:
            levels = {"stop_loss": 0, "take_profit": 0, "risk_reward_ratio": 0}

        core_probability_up = max(0.0, min(1.0, (float(consensus["score"]) + 1.0) / 2.0))
        plugin_snapshot: dict[str, dict] = {}
        if finbert_verified:
            plugin_snapshot["finbert"] = {
                "probability_up": float(finbert.get("sentiment_score", 0.5)),
                "direction": finbert.get("signal", "NEUTRAL"),
                "confidence": float(finbert.get("confidence", 0.0) or 0.0),
                "policy": finbert_policy,
                "model": finbert.get("model"),
            }
        if quantic_snapshot:
            plugin_snapshot["quantic"] = quantic_snapshot
        if swarm_snapshot:
            plugin_snapshot["swarm"] = swarm_snapshot

        sizing = get_sizing_multiplier(confidence) if verdict != "HOLD" else 0.0
        context.result = {
            "symbol": ticker,
            "verdict": verdict,
            "direction": consensus["direction"],
            "final_score": consensus["score"],
            "core_probability_up": round(core_probability_up, 6),
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
            "plugin_snapshot": plugin_snapshot,
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
                "plugin_policies": {name: data.get("policy", "ADVISORY") for name, data in plugin_results.items()},
                "shadow_resolution": shadow_resolution,
            },
            "execution_authority": False,
        }
        self._add_thought(context, f"Fusion: {consensus['score']:+.4f} -> {verdict} (conf={confidence:.0f}%)")
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        result = context.result or {}
        verdict = result.get("verdict", "HOLD")
        confidence = float(result.get("confidence", 0.0) or 0.0)
        context.reflection = f"Consensus for {context.ticker}: {verdict} ({confidence:.0f}%)"
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
                        f"target={result.get('take_profit', 0)} stop={result.get('stop_loss', 0)}"
                    ),
                    confidence=int(confidence),
                )
            except Exception:
                pass

            try:
                entry = float(result.get("entry_point", 0) or 0)
                if entry > 0:
                    from self_improvement.shadow_trade_store import shadow_trade_store

                    shadow_trade_store.record_decision(
                        ticker=context.ticker,
                        direction=str(result.get("direction") or verdict),
                        confidence=confidence,
                        entry_price=entry,
                        strategy_id=self.name,
                        evidence={
                            "core_probability_up": result.get("core_probability_up"),
                            "signals": result.get("signals", {}),
                            "stop_loss": result.get("stop_loss"),
                            "take_profit": result.get("take_profit"),
                            "risk_reward_ratio": result.get("risk_reward_ratio"),
                        },
                        plugins=result.get("plugin_snapshot", {}),
                    )
            except Exception as exc:
                logger.debug("Shadow decision recording skipped: %s", exc)

        self._quantic_validation = None
        self._swarm_consensus = None
        return context
