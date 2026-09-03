"""Swarm Intelligence Agent — advisory Vibe Trading AI research.

A successful swarm call is not evidence of predictive accuracy. Swarm output is
therefore advisory by default and carries neutral 0.5 confidence until AITradra's
Plugin Ablation Lab has enough resolved forward observations to calibrate its
incremental contribution.
"""

from __future__ import annotations

import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from agents.base_agent import BaseAgent, AgentContext
from core.vibe_gateway import vibe_gateway
from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SwarmConfig:
    team_preset: str = "investment-committee"
    query: str = ""
    market: str = "crypto"
    timeout_seconds: int = 180
    parallel_agents: int = 5
    include_insights: bool = True


@dataclass
class SwarmResult:
    success: bool
    preset_used: str
    query: str
    agents_activated: List[str] = field(default_factory=list)
    synthesis: str = ""
    individual_responses: List[Dict[str, Any]] = field(default_factory=list)
    confidence_score: float = 0.5
    calibrated: bool = False
    execution_time_ms: float = 0.0
    errors: List[str] = field(default_factory=list)


class SwarmIntelligenceAgent(BaseAgent):
    """Use Vibe teams for research breadth without manufacturing confidence."""

    def __init__(self, memory=None):
        super().__init__(name="SwarmIntelligence", memory=memory)
        self.vibe = vibe_gateway
        self._available = self.vibe.is_available
        self._preset_capabilities = {
            "investment-committee": {
                "description": "Multi-asset portfolio analysis with risk budgeting",
                "agents": ["portfolio_manager", "risk_analyst", "macro_strategist", "asset_allocator", "performance_tracker"],
            },
            "crypto-trading-desk": {
                "description": "On-chain analytics, order flow, and derivatives positioning",
                "agents": ["on_chain_analyst", "order_flow_trader", "derivatives_specialist", "liquidity_mapper", "sentiment_tracker"],
            },
            "macro-research": {
                "description": "Global macro analysis across currencies, bonds, and commodities",
                "agents": ["fx_strategist", "bond_analyst", "commodity_specialist", "macro_indicator_tracker", "policy_analyst"],
            },
            "technical-analysis-team": {
                "description": "Multi-timeframe technical analysis with pattern recognition",
                "agents": ["chart_pattern_analyst", "indicator_specialist", "wave_analyst", "pivot_point_tracker", "trend_strength_evaluator"],
            },
            "risk-management-desk": {
                "description": "Portfolio-level risk analysis and hedging strategies",
                "agents": ["var_analyst", "correlation_tracker", "stress_tester", "hedging_strategist", "risk_alert_monitor"],
            },
            "news-sentiment-squad": {
                "description": "Real-time news parsing and sentiment scoring",
                "agents": ["news_parser", "sentiment_scorer", "catalyst_detector", "social_media_monitor", "earnings_calendar_tracker"],
            },
            "earnings-whisperers": {
                "description": "Earnings preview, guidance and beat/miss analysis",
                "agents": ["earnings_forecaster", "guidance_analyst", "whisper_number_tracker", "beat_miss_analyst", "management_sentiment_tracker"],
            },
            "options-flow-desk": {
                "description": "Options flow, gamma exposure, and volatility surface",
                "agents": ["options_flow_analyst", "gamma_exposure_tracker", "vol_surface_mapper", "unusual_activity_detector", "expiry_planner"],
            },
            "portfolio-optimizers": {
                "description": "Portfolio construction and risk budgeting",
                "agents": ["mean_variance_optimizer", "factor_exposure_analyzer", "rebalancing_automator", "risk_budget_allocator", "tax_loss_harvester"],
            },
            "regime-detectors": {
                "description": "Market regime identification and regime-switching research",
                "agents": ["regime_classifier", "volatility_regime_tracker", "trend_regime_analyst", "correlation_regime_monitor", "regime_switch_predictor"],
            },
        }

    @property
    def is_available(self) -> bool:
        return self._available

    async def observe(self, context: AgentContext) -> AgentContext:
        context.observations["swarm_available"] = self._available
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        self._add_thought(context, "Vibe swarm is advisory until forward ablation evidence calibrates it")
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan.extend(
            [
                "Select a relevant swarm preset",
                "Execute the research swarm",
                "Return synthesis as advisory evidence",
                "Do not boost confidence from call success alone",
            ]
        )
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        result = await self.execute(
            query=context.task,
            team_preset=context.metadata.get("team_preset", "investment-committee"),
            market=context.metadata.get("market", "crypto"),
            context=context,
        )
        context.result = {
            "success": result.success,
            "preset": result.preset_used,
            "agents": result.agents_activated,
            "synthesis": result.synthesis,
            "confidence": result.confidence_score,
            "calibrated": result.calibrated,
            "advisory_only": True,
            "execution_authority": False,
            "errors": result.errors,
        }
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        context.confidence = 0.5 if context.result.get("success") else 0.0
        context.reflection = (
            f"Swarm preset {context.result.get('preset', 'unknown')} completed as advisory research; no confidence boost applied."
        )
        return context

    async def execute(
        self,
        query: str,
        team_preset: str = "investment-committee",
        market: str = "crypto",
        context: Optional[AgentContext] = None,
    ) -> SwarmResult:
        import time

        start_time = time.time()
        if not self._available:
            return SwarmResult(
                success=False,
                preset_used=team_preset,
                query=query,
                confidence_score=0.0,
                errors=["Vibe Trading AI not available"],
            )
        self._add_thought(
            context or AgentContext(task=query),
            f"Spawning advisory {team_preset} swarm for: {query[:50]}...",
        )
        try:
            response = await asyncio.wait_for(
                self.vibe.spawn_swarm(team_preset=team_preset, query=query, market=market),
                timeout=180,
            )
            execution_time = (time.time() - start_time) * 1000
            if response.get("error"):
                return SwarmResult(
                    success=False,
                    preset_used=team_preset,
                    query=query,
                    confidence_score=0.0,
                    execution_time_ms=execution_time,
                    errors=[str(response["error"])],
                )
            agents = self._preset_capabilities.get(team_preset, {}).get("agents", [])
            return SwarmResult(
                success=True,
                preset_used=team_preset,
                query=query,
                agents_activated=agents,
                synthesis=str(response.get("output", "") or ""),
                confidence_score=0.5,
                calibrated=False,
                execution_time_ms=execution_time,
            )
        except asyncio.TimeoutError:
            return SwarmResult(
                success=False,
                preset_used=team_preset,
                query=query,
                confidence_score=0.0,
                errors=["Swarm operation timed out after 180s"],
            )
        except Exception as exc:
            logger.error("Swarm execution failed: %s", exc)
            return SwarmResult(
                success=False,
                preset_used=team_preset,
                query=query,
                confidence_score=0.0,
                errors=[str(exc)],
            )

    async def run_cross_market_analysis(self, assets: List[str], query: str) -> Dict[str, Any]:
        if not self._available:
            return {"error": "Vibe Trading AI not available"}
        result = await self.vibe.cross_market_analysis(assets=assets, query=query)
        if isinstance(result, dict):
            result.setdefault("advisory_only", True)
            result.setdefault("execution_authority", False)
        return result

    def list_available_presets(self) -> List[Dict[str, Any]]:
        return [{"preset": key, **value} for key, value in self._preset_capabilities.items()]

    async def recommend_preset(self, query: str) -> str:
        q = query.lower()
        if any(k in q for k in ["crypto", "btc", "eth", "defi", "on-chain"]):
            return "crypto-trading-desk"
        if any(k in q for k in ["macro", "fed", "inflation", "gdp", "central bank"]):
            return "macro-research"
        if any(k in q for k in ["earnings", "revenue", "eps", "guidance"]):
            return "earnings-whisperers"
        if any(k in q for k in ["options", "volatility", "gamma", "iv"]):
            return "options-flow-desk"
        if any(k in q for k in ["risk", "var", "hedge", "drawdown"]):
            return "risk-management-desk"
        if any(k in q for k in ["technical", "pattern", "indicator", "chart"]):
            return "technical-analysis-team"
        if any(k in q for k in ["news", "sentiment", "social", "catalyst"]):
            return "news-sentiment-squad"
        if any(k in q for k in ["optimize", "portfolio", "allocate", "diversify"]):
            return "portfolio-optimizers"
        if any(k in q for k in ["regime", "market condition", "bull", "bear"]):
            return "regime-detectors"
        return "investment-committee"


swarm_agent = SwarmIntelligenceAgent()
