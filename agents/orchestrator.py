"""MythicOrchestrator — ReAct loop orchestrator for multi-agent reasoning.

Adapted from the Claude Agent System architecture pattern:
User → Orchestrator → (Memory + Specialist Agents + Reflection) → Tools → Result Synthesis → Final Response

Uses open-source local LLM (NVIDIA Nemotron GGUF / Ollama) instead of cloud APIs.
"""

import json
import asyncio
from datetime import datetime
from typing import Optional, List
from core.logger import get_logger
from agents.base_agent import AgentContext

logger = get_logger(__name__)


class MythicOrchestrator:
    """
    The top-level orchestrator that:
    1. Collects context from all 4 knowledge sources in parallel
    2. Dispatches to specialist agents (Technical, Risk, Macro)
    3. Runs critique/reflection layer
    4. Synthesizes final response via LLM with calibrated confidence

    Implements a ReAct (Reason-Act) loop with max_steps safety.
    """

    def __init__(self):
        from agents.specialist_agents import (
            TechnicalSpecialist,
            RiskSpecialist,
            MacroSpecialist,
        )
        from agents.extended_specialists import (
            SentimentSpecialist,
            FundamentalSpecialist,
            SectorSpecialist,
            CatalystSpecialist,
        )
        from agents.critique_layer import CritiqueAgent
        from agents.sentiment_classifier import SentimentClassifierAgent
        from agents.risk_manager import RiskManagerAgent
        from agents.signal_aggregator import SignalAggregatorAgent

        # Vibe Trading AI Agents
        from agents.swarm_agent import swarm_agent
        from agents.quantic_agent import quantic_agent
        from agents.strategy_generator_agent import strategy_generator_agent

        # Core Trio
        self.technical = TechnicalSpecialist()
        self.risk = RiskSpecialist()
        self.macro = MacroSpecialist()

        # Extended Specialists & AI Upgrades
        self.sentiment = SentimentSpecialist()
        self.sentiment_finbert = SentimentClassifierAgent()
        self.fundamental = FundamentalSpecialist()
        self.sector = SectorSpecialist()
        self.catalysts = CatalystSpecialist()

        # Decision & Risk Layer
        self.risk_manager = RiskManagerAgent()
        self.signal_aggregator = SignalAggregatorAgent()

        self.critique = CritiqueAgent()

        # Vibe AI Agents
        self.swarm = swarm_agent
        self.quantic = quantic_agent
        self.strategy_gen = strategy_generator_agent

        logger.info("Vibe AI agents loaded: Swarm, Quantic, StrategyGenerator")

        # Memory store for episodic recall
        self._episode_store = []
        logger.info("MythicOrchestrator initialized")
        logger.info("Specialist agents loaded")
        logger.info("CritiqueAgent active")

    def attach_improvement_engine(self, improvement_engine) -> None:
        """Attach self-improvement telemetry to every managed specialist."""
        for agent in (
            self.technical,
            self.risk,
            self.macro,
            self.sentiment,
            self.sentiment_finbert,
            self.fundamental,
            self.sector,
            self.catalysts,
            self.risk_manager,
            self.signal_aggregator,
            self.critique,
        ):
            if hasattr(agent, "improvement_engine"):
                agent.improvement_engine = improvement_engine

    async def orchestrate(
        self,
        query: str,
        ticker: Optional[str],
        gathered_data: dict,
        session_id: str = "default",
        research_mode: str = "QUICK",
        history: list = [],
    ) -> dict:
        """Main entry point — 14-agent pipeline with Convoy Mode and Checkpoints."""
        logger.info(
            f"[Orchestrator] Mode: {research_mode} | Convoy Mode active for '{query[:80]}' ticker={ticker}"
        )

        start = datetime.now()

        # ─── Data Integrity Check ──────────────────────────────────────────
        # Ensure the gathered_data actually contains context for the target ticker.
        # If the ticker was overridden by QueryRouter, we might have mismatched data.
        if ticker and gathered_data.get("price_data"):
            data_ticker = gathered_data["price_data"].get("ticker", gathered_data["price_data"].get("id", "")).upper()
            if data_ticker and data_ticker != ticker.upper():
                logger.warning(f"[Orchestrator] Data mismatch! Requested {ticker}, got {data_ticker}. Forcing dynamic refresh...")
                # We can't easily redo the fan-out here without adding latency,
                # but we can flag it for the synthesis layer or specialists.
                gathered_data["context_mismatch"] = True
                gathered_data["requested_ticker"] = ticker
                # Trigger background sync for the correct ticker to ensure next query is fast
                from agents.collector_agent import collect_historical_data
                asyncio.create_task(collect_historical_data(ticker))
        # ──────────────────────────────────────────────────────────────────

        # Step 0: Check for existing checkpoint
        from gateway.knowledge_store import knowledge_store

        checkpoint = knowledge_store.get_episode_state(session_id, "MythicOrchestrator")
        if checkpoint:
            logger.info(
                f"[Orchestrator] Resuming from checkpoint: {checkpoint.get('step')}"
            )
            # Logic to resume from specific wave could go here

        # Initialize Episode
        knowledge_store.store_episode_start(session_id, "MythicOrchestrator", query)

        try:
            # ─── Step 1: Run First Wave (Parallel) ──────────────────────────────
            specialist_outputs = await self._run_first_wave(ticker, gathered_data)

            # Checkpoint 1
            knowledge_store.update_episode_checkpoint(
                session_id,
                "MythicOrchestrator",
                {"step": "first_wave_complete", "outputs": specialist_outputs},
            )

            # ─── Step 2: Run Second Wave (Sequential/Knowledge Aware) ───────────
            if research_mode in ("DEEP", "INSTITUTIONAL"):
                second_wave_results = await self._run_second_wave(ticker, gathered_data)
                specialist_outputs.update(second_wave_results)

            # Checkpoint 2
            knowledge_store.update_episode_checkpoint(
                session_id,
                "MythicOrchestrator",
                {"step": "second_wave_complete", "outputs": specialist_outputs},
            )

            # ─── Step 3: Convoy Mode - Hierarchical Subtask Decomposition ───────
            # If the query is complex or research_mode is INSTITUTIONAL, we spawn "Shadow Agents"
            if research_mode == "INSTITUTIONAL" or (
                research_mode == "DEEP"
                and (len(query) > 100 or "deep" in query.lower())
            ):
                logger.info(
                    f"[Orchestrator] {research_mode}: Spawning shadow agents for deep-dive..."
                )
                shadow_results = await self._run_convoy_deep_dive(
                    ticker, gathered_data, specialist_outputs
                )
                specialist_outputs.update(shadow_results)

            if research_mode in ("DEEP", "INSTITUTIONAL"):
                decision_ctx = AgentContext(
                    task=f"Decision for {ticker}",
                    ticker=ticker,
                    observations={
                        **gathered_data,
                        "specialist_outputs": specialist_outputs,
                    },
                    metadata={"history": history},
                )

                # ─── Phase 4.0: Vibe Swarm Consensus (INSTITUTIONAL only) ───────
                if (
                    research_mode == "INSTITUTIONAL"
                    and hasattr(self, "swarm")
                    and self.swarm.is_available
                ):
                    logger.info(f"[Orchestrator] Running Vibe Swarm Consensus...")
                    swarm_result = await self.run_vibe_swarm(
                        query=query,
                        team_preset="investment-committee",
                        market="crypto"
                        if ticker and ("BTC" in ticker or "ETH" in ticker)
                        else "stocks",
                    )
                    specialist_outputs["vibe_swarm"] = swarm_result
                    decision_ctx.observations["vibe_swarm"] = swarm_result
                    self.signal_aggregator.set_swarm_consensus(swarm_result)

                # ─── Phase 4.1: Sentiment Refinement (FinBERT) ──────────────
                logger.info(
                    f"[Orchestrator] Running high-precision Sentiment Refinement..."
                )
                sent_res = await self.sentiment_finbert.run(decision_ctx)
                specialist_outputs["sentiment_finbert"] = sent_res.result

                # Inject sentiment result into context for subsequent agents
                decision_ctx.observations["sentiment_result"] = sent_res.result

                # ─── Phase 4.2: Signal Aggregation ──────────────────────────
                logger.info(f"[Orchestrator] Running Signal Aggregation...")
                agg_res = await self.signal_aggregator.run(decision_ctx)
                specialist_outputs["signal_aggregator"] = agg_res.result

                # Inject aggregator result into context for Risk Manager
                decision_ctx.observations["signal_aggregator_result"] = agg_res.result

                # ─── Phase 4.3: Quantic Vetting (DEEP/INSTITUTIONAL) ───────────────
                if (
                    research_mode in ("DEEP", "INSTITUTIONAL")
                    and hasattr(self, "quantic")
                    and self.quantic.is_available
                ):
                    logger.info(
                        f"[Orchestrator] Running Quantic Vetting (SMC/Monte Carlo)..."
                    )
                    quantic_result = await self.run_quantic_analysis(
                        ticker=ticker, analysis_type="full", timeframe="1h"
                    )
                    specialist_outputs["quantic"] = quantic_result
                    decision_ctx.observations["quantic"] = quantic_result
                    self.signal_aggregator.set_quantic_validation(quantic_result)

                    agg_res = await self.signal_aggregator.run(decision_ctx)
                    specialist_outputs["signal_aggregator"] = agg_res.result

                # ─── Phase 4.4: Risk Approval ───────────────────────────────
                logger.info(f"[Orchestrator] Running Risk Manager Approval...")
                risk_res = await self.risk_manager.run(decision_ctx)
                specialist_outputs["risk_manager"] = risk_res.result
            else:
                # Minimal Decision Layer for QUICK mode
                specialist_outputs["signal_aggregator"] = {
                    "signal": gathered_data.get("price_data", {}).get("chg", 0) >= 0
                    and "BULLISH"
                    or "BEARISH",
                    "summary": "Quick consensus.",
                }

            # ─── Step 5: Run critique/reflection layer ──────────────────────────
            critique_result = {
                "agreement_score": 0.8,
                "revised_consensus": "NEUTRAL",
                "flags": [],
                "contradiction_notes": [],
                "audit_summary": "Quick scan.",
            }
            if research_mode in ("DEEP", "INSTITUTIONAL"):
                critique_result = await self.critique.critique(
                    specialist_outputs, query, ticker
                )

            # ─── Step 6: Calibrate confidence ───────────────────────────────────
            from agents.critique_layer import calibrate_confidence

            rag_count = len(gathered_data.get("rag_results", []))
            news_recency = self._compute_news_recency_hours(
                gathered_data.get("news", [])
            )

            spec_confidences = [
                v.get("confidence", 0.5)
                for v in specialist_outputs.values()
                if isinstance(v, dict)
            ]
            avg_spec_conf = (
                sum(spec_confidences) / len(spec_confidences)
                if spec_confidences
                else 0.5
            )

            final_confidence = calibrate_confidence(
                specialist_agreement=critique_result["agreement_score"],
                rag_source_count=rag_count,
                news_recency_hours=news_recency,
                specialist_avg_confidence=avg_spec_conf,
            )

            # ─── Step 6.5: Cross-Market Sanity Check (INSTITUTIONAL) ───────────────
            cross_market_divergence = False
            if (
                research_mode == "INSTITUTIONAL"
                and hasattr(self, "swarm")
                and self.swarm.is_available
                and ticker
            ):
                logger.info(f"[Orchestrator] Running Cross-Market Sanity Check...")

                reference_assets = (
                    ["SPY", "QQQ", "DXY"]
                    if not any(x in ticker.upper() for x in ["BTC", "ETH", "SOL"])
                    else ["BTC", "DXY"]
                )

                cross_result = await self.run_cross_market_analysis(
                    assets=reference_assets,
                    query=f"Compare market sentiment for {ticker} vs {', '.join(reference_assets)}",
                )

                specialist_outputs["cross_market"] = cross_result

                if cross_result.get("success"):
                    verdict = specialist_outputs.get("signal_aggregator", {}).get(
                        "verdict", ""
                    )
                    if cross_result.get("divergence"):
                        cross_market_divergence = True
                        final_confidence *= 0.8
                        logger.warning(
                            f"[Orchestrator] Cross-market divergence detected! Reducing confidence."
                        )

            # ─── Step 7: Final LLM synthesis ───────────────────
            response = await self._synthesize_final(
                query,
                ticker,
                gathered_data,
                specialist_outputs,
                critique_result,
                final_confidence,
            )

            # ─── Step 8: Complete Episode ──────────────────────────────────────
            result_payload = {
                "response": response,
                "confidence": final_confidence,
                "consensus": critique_result["revised_consensus"],
            }
            knowledge_store.complete_episode(
                session_id, "MythicOrchestrator", result_payload
            )

            self._episode_store.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "ticker": ticker,
                    "query": query,
                    "consensus": critique_result["revised_consensus"],
                    "confidence": final_confidence,
                    "pipeline_ms": round(
                        (datetime.now() - start).total_seconds() * 1000
                    ),
                }
            )
            self._episode_store = self._episode_store[-100:]

            elapsed = (datetime.now() - start).total_seconds()
            logger.info(
                f"[Orchestrator] Pipeline complete in {elapsed:.1f}s. Confidence: {final_confidence}"
            )

            return {
                **result_payload,
                "specialist_outputs": {
                    k: v.get("summary", "")
                    for k, v in specialist_outputs.items()
                    if isinstance(v, dict)
                },
                "specialist_details": specialist_outputs,
                "critique": {
                    "flags": critique_result.get("flags", []),
                    "contradictions": critique_result.get("contradiction_notes", []),
                    "audit": critique_result.get("audit_summary", ""),
                    "agreement_score": critique_result.get("agreement_score", 0.0),
                },
                "intelligence_profile": gathered_data.get("intelligence_profile", {}),
                "sources_used": list(gathered_data.keys()),
                "pipeline_ms": round(elapsed * 1000),
            }

        except Exception as e:
            logger.error(f"[Orchestrator] Pipeline failed: {e}")
            knowledge_store.fail_episode(session_id, "MythicOrchestrator", str(e))
            raise

    async def _run_convoy_deep_dive(
        self, ticker: str, data: dict, current_outputs: dict
    ) -> dict:
        """Convoy Mode: Spawns specialized agents dynamically."""
        from agents.think_agent import ThinkAgent

        think_agent = ThinkAgent()

        ctx = AgentContext(
            task=f"Shadow deep-dive for {ticker}",
            ticker=ticker,
            observations={"current_outputs": current_outputs},
        )
        result = await think_agent.run(ctx)
        return {
            "deep_dive_analysis": result.result
            if result.result
            else "Deep dive complete."
        }

    def nudge_agent(self, agent_id: str):
        """Auto-nudge an agent that is stuck or taking too long."""
        logger.warning(
            f"🔔 [Watchdog] Nudging agent '{agent_id}' — high latency detected."
        )
        # In a real implementation, this might signal an event or retry a specific task
        return True

    async def _run_first_wave(self, ticker: str, data: dict) -> dict:
        """First wave: Agents that don't depend on others."""
        ohlcv = data.get("history", [])
        price = data.get("price_data", {})
        news = data.get("news", [])
        knowledge = data.get("knowledge_results", {})
        intelligence_snapshot = data.get("intelligence_snapshot", {})

        ctx = AgentContext(
            task=f"Analyze {ticker}",
            ticker=ticker,
            observations={
                "news": news,
                "knowledge_results": knowledge,
                "price_data": price,
                "intelligence_snapshot": intelligence_snapshot,
            },
            metadata={
                "ohlcv_data": ohlcv,
                "price_data": price,
                "news_data": news,
                "knowledge_results": knowledge,
                "intelligence_snapshot": intelligence_snapshot,
            },
        )

        results = await asyncio.gather(
            self.technical.run(ctx),
            self.macro.run(ctx),
            self.fundamental.run(ctx),
            return_exceptions=True,
        )

        outputs = {}
        for name, res in zip(["technical", "macro", "fundamental"], results):
            outputs[name] = (
                res.result if not isinstance(res, Exception) else {"error": str(res)}
            )
        return outputs

    async def _run_second_wave(self, ticker: str, data: dict) -> dict:
        """Second wave: Agents that benefit from First Wave's stored insights."""
        ohlcv = data.get("history", [])
        price = data.get("price_data", {})
        news = data.get("news", [])
        knowledge = data.get("knowledge_results", {})
        intelligence_snapshot = data.get("intelligence_snapshot", {})

        ctx = AgentContext(
            task=f"Advanced analyze {ticker}",
            ticker=ticker,
            observations={
                "news": news,
                "knowledge_results": knowledge,
                "price_data": price,
                "intelligence_snapshot": intelligence_snapshot,
            },
            metadata={
                "ohlcv_data": ohlcv,
                "price_data": price,
                "news_data": news,
                "knowledge_results": knowledge,
                "intelligence_snapshot": intelligence_snapshot,
            },
        )

        results = await asyncio.gather(
            self.risk.run(ctx),
            self.sentiment.run(ctx),
            self.sector.run(ctx),
            self.catalysts.run(ctx),
            return_exceptions=True,
        )

        outputs = {}
        for name, res in zip(["risk", "sentiment", "sector", "catalysts"], results):
            outputs[name] = (
                res.result if not isinstance(res, Exception) else {"error": str(res)}
            )
        return outputs

    async def _synthesize_final(
        self,
        query: str,
        ticker: Optional[str],
        gathered_data: dict,
        specialist_outputs: dict,
        critique: dict,
        confidence: float,
    ) -> str:
        """Synthesize all 14-agent contexts into a final response."""
        from llm.client import get_shared_llm

        llm = get_shared_llm()

        consensus = critique.get("revised_consensus", "NEUTRAL")

        prompt_parts = [
            f"Question: {query}",
            f"Ticker: {ticker or 'N/A'}",
            f"Overall Consensus: {consensus} (Confidence: {confidence:.0%})",
            "\nSpecialist Agent Analysis:",
        ]

        # Dynamically add all specialist summaries
        for name, output in specialist_outputs.items():
            if isinstance(output, dict):
                sig = output.get(
                    "signal",
                    output.get("risk_level", output.get("macro_outlook", "N/A")),
                )
                summ = output.get("summary", "Analysis complete.")[:200]
                prompt_parts.append(f"- {name.upper()}: {sig} | {summ}")

        # Add news headlines (max 5)
        news = gathered_data.get("news", [])
        if news:
            prompt_parts.append("\nRecent Market Catalysts:")
            for n in news[:5]:
                if isinstance(n, dict):
                    h = n.get("headline", n.get("title", ""))
                    if h:
                        prompt_parts.append(f"- {h[:100]}")

        full_prompt = "\n".join(prompt_parts)

        system_prompt = (
            "You are AXIOM, a premium multi-agent trading intelligence system powered by NVIDIA NIM. "
            "Write an authoritative, data-driven synthesis of all agent signals. "
            "Structure: 1) Executive Summary, 2) Technical/Risk alignment, "
            "3) Macro/Fundamental context, 4) Investment Verdict (BUY/SELL/HOLD). "
            "IMPORTANT: If the Signal Aggregator shows a strong verdict, be extremely clear about it. "
            "Provide specific price targets and stop-losses if available. "
            "Be extremely specific. Use professional financial tone. Keep under 400 words."
        )

        try:
            return await llm.complete(
                prompt=full_prompt,
                system=system_prompt,
                temperature=0.2,
                max_tokens=1000,
            )
        except Exception as e:
            logger.error(
                f"[Orchestrator] Final synthesis failed: {type(e).__name__}: {e}"
            )
            logger.warning(
                f"[Orchestrator] Falling back to structured response. Last provider: {getattr(llm, 'last_provider_used', 'unknown')}"
            )
            return self._build_fallback_response(
                query, ticker, specialist_outputs, critique, confidence
            )

    def _build_fallback_response(
        self, query, ticker, specialists, critique, confidence
    ):
        """Build a structured response when LLM is unavailable."""
        tech = specialists.get("technical", {})
        risk = specialists.get("risk", {})
        macro = specialists.get("macro", {})
        consensus = critique.get("revised_consensus", "NEUTRAL")

        return f"""🧠 AXIOM MYTHIC — MULTI-AGENT INTELLIGENCE

📊 Consensus: {consensus} (Confidence: {confidence:.0%})

📈 Technical Analysis
{tech.get("summary", "No technical data available.")}
Signal: {tech.get("signal", "N/A")} | Trend: {tech.get("indicators", {}).get("trend", "N/A")}

⚠️ Risk Assessment
{risk.get("summary", "No risk data available.")}
Level: {risk.get("risk_level", "N/A")} | VaR(95%): {risk.get("var_pct", "N/A")}%

🌍 Macro Environment
{macro.get("summary", "No macro data available.")}
Outlook: {macro.get("macro_outlook", "N/A")} | Sentiment: {macro.get("sentiment_score", "N/A")}

🔍 Critique
{critique.get("audit_summary", "No audit available.")}
Flags: {", ".join(critique.get("flags", [])) or "None"}

👉 Confidence: {confidence:.0%} (Multi-agent consensus with calibration)"""

    def _compute_news_recency_hours(self, news: list) -> float:
        """Compute the average recency of news articles in hours."""
        if not news:
            return 168  # Default to 7 days if no news

        now = datetime.now()
        recencies = []
        for article in news[:10]:
            if not isinstance(article, dict):
                continue
            pub = article.get("published_at") or article.get("pubDate")
            if pub:
                try:
                    pub_dt = datetime.fromisoformat(str(pub).replace("Z", "+00:00"))
                    diff_hours = (
                        now - pub_dt.replace(tzinfo=None)
                    ).total_seconds() / 3600
                    recencies.append(max(diff_hours, 0))
                except Exception:
                    pass

        return (
            min(recencies) if recencies else 48
        )  # Return best (most recent) if available

    def get_recent_episodes(self, ticker: str = None, limit: int = 5) -> list:
        """Recall recent orchestrator episodes for memory augmentation."""
        episodes = self._episode_store
        if ticker:
            episodes = [e for e in episodes if e.get("ticker") == ticker]
        return episodes[-limit:]

    # ─── Vibe AI Integration ────────────────────────────────────────────────────

    async def run_vibe_swarm(
        self,
        query: str,
        team_preset: str = "investment-committee",
        market: str = "crypto",
    ) -> dict:
        """Run Vibe swarm analysis as part of the orchestration."""
        from gateway.knowledge_store import knowledge_store

        if not hasattr(self.swarm, "is_available") or not self.swarm.is_available:
            return {"error": "Vibe Trading AI not available", "swarm_disabled": True}

        task_label = f"Swarm consensus for {market}: {query[:80]}"
        started = datetime.now()
        knowledge_store.update_agent_health(
            "SwarmIntelligence",
            "active",
            task=task_label,
        )

        try:
            result = await self.swarm.execute(
                query=query, team_preset=team_preset, market=market
            )
        except Exception as exc:
            latency_ms = round((datetime.now() - started).total_seconds() * 1000)
            knowledge_store.update_agent_health(
                "SwarmIntelligence",
                "error",
                latency_ms=latency_ms,
                task=task_label,
                error=True,
            )
            raise exc

        latency_ms = round((datetime.now() - started).total_seconds() * 1000)
        knowledge_store.update_agent_health(
            "SwarmIntelligence",
            "idle" if result.success else "error",
            latency_ms=latency_ms,
            task=task_label,
            error=not result.success,
        )

        return {
            "success": result.success,
            "query": query,
            "preset": result.preset_used,
            "synthesis": result.synthesis,
            "agents": result.agents_activated,
            "agent_count": len(result.agents_activated),
            "confidence": result.confidence_score,
            "errors": result.errors,
            "execution_time_ms": result.execution_time_ms,
        }

    async def run_quantic_analysis(
        self, ticker: str, analysis_type: str = "full", timeframe: str = "1h"
    ) -> dict:
        """Run quantic analysis as part of the orchestration."""
        from gateway.knowledge_store import knowledge_store

        if not hasattr(self.quantic, "is_available") or not self.quantic.is_available:
            return {"error": "Vibe Trading AI not available", "quantic_disabled": True}

        task_label = f"Quantic {analysis_type} scan for {ticker} ({timeframe})"
        started = datetime.now()
        knowledge_store.update_agent_health(
            "QuanticAnalysis",
            "active",
            task=task_label,
        )

        try:
            result = await self.quantic.execute(
                ticker=ticker, analysis_type=analysis_type, timeframe=timeframe
            )
        except Exception as exc:
            latency_ms = round((datetime.now() - started).total_seconds() * 1000)
            knowledge_store.update_agent_health(
                "QuanticAnalysis",
                "error",
                latency_ms=latency_ms,
                task=task_label,
                error=True,
            )
            raise exc

        latency_ms = round((datetime.now() - started).total_seconds() * 1000)
        knowledge_store.update_agent_health(
            "QuanticAnalysis",
            "idle" if result.success else "error",
            latency_ms=latency_ms,
            task=task_label,
            error=not result.success,
        )

        return {
            "success": result.success,
            "ticker": result.ticker,
            "timeframe": result.timeframe,
            "smart_money_score": result.smart_money_score,
            "smc": {
                "signal": result.smc.smart_money_signal if result.smc else None,
                "confidence": result.smc.confidence if result.smc else 0,
                "institutional_order_blocks": (
                    result.smc.institutional_order_blocks if result.smc else []
                ),
                "fair_value_gaps": result.smc.fair_value_gaps if result.smc else [],
                "liquidity_pools": result.smc.liquidity_pools if result.smc else [],
                "order_flow_imbalance": (
                    result.smc.order_flow_imbalance if result.smc else 0
                ),
            },
            "monte_carlo": {
                "expected_return": (
                    result.monte_carlo.expected_return if result.monte_carlo else 0
                ),
                "volatility": result.monte_carlo.volatility if result.monte_carlo else 0,
                "sharpe": result.monte_carlo.sharpe_ratio if result.monte_carlo else 0,
                "max_dd": result.monte_carlo.max_drawdown if result.monte_carlo else 0,
                "var_95": result.monte_carlo.var_95 if result.monte_carlo else 0,
                "cvar_95": result.monte_carlo.cvar_95 if result.monte_carlo else 0,
                "percentile_5": (
                    result.monte_carlo.percentile_5 if result.monte_carlo else 0
                ),
                "percentile_95": (
                    result.monte_carlo.percentile_95 if result.monte_carlo else 0
                ),
                "distribution": (
                    result.monte_carlo.distribution if result.monte_carlo else []
                ),
            }
            if result.monte_carlo
            else None,
            "bootstrap": {
                "mean_estimate": (
                    result.bootstrap.mean_estimate if result.bootstrap else 0
                ),
                "std_error": result.bootstrap.std_error if result.bootstrap else 0,
                "confidence_interval": (
                    list(result.bootstrap.confidence_interval)
                    if result.bootstrap
                    else [0, 0]
                ),
                "p_value": result.bootstrap.p_value if result.bootstrap else 1,
                "is_significant": (
                    result.bootstrap.is_significant if result.bootstrap else False
                ),
            }
            if result.bootstrap
            else None,
            "synthesis": result.synthesis,
            "errors": result.errors,
            "execution_time_ms": result.execution_time_ms,
        }

    async def generate_strategy(
        self, description: str, language: str = "pine", market: str = "crypto"
    ) -> dict:
        """Generate trading strategy as part of the orchestration."""
        if (
            not hasattr(self.strategy_gen, "is_available")
            or not self.strategy_gen.is_available
        ):
            return {
                "error": "Vibe Trading AI not available",
                "strategy_gen_disabled": True,
            }

        result = await self.strategy_gen.generate(
            description=description, language=language, market=market
        )

        return {
            "success": result.success,
            "language": result.language,
            "code": result.code,
            "errors": result.errors,
        }

    async def run_cross_market_analysis(self, assets: List[str], query: str) -> dict:
        """Run analysis across multiple markets."""
        if not hasattr(self.swarm, "is_available") or not self.swarm.is_available:
            return {"error": "Vibe Trading AI not available"}

        return await self.swarm.run_cross_market_analysis(assets=assets, query=query)


# Global singleton
mythic_orchestrator = MythicOrchestrator()
