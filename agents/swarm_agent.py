"""Swarm Intelligence Agent — Multi-agent swarm powered by Vibe Trading AI.

Spawns coordinated teams of specialist agents (29 presets) to tackle
complex trading research tasks with collective intelligence.
"""

import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from agents.base_agent import BaseAgent, AgentContext
from core.vibe_gateway import vibe_gateway
from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SwarmConfig:
    """Configuration for a swarm operation."""

    team_preset: str = "investment-committee"
    query: str = ""
    market: str = "crypto"
    timeout_seconds: int = 180
    parallel_agents: int = 5
    include_insights: bool = True


@dataclass
class SwarmResult:
    """Result from a swarm operation."""

    success: bool
    preset_used: str
    query: str
    agents_activated: List[str] = field(default_factory=list)
    synthesis: str = ""
    individual_responses: List[Dict[str, Any]] = field(default_factory=list)
    confidence_score: float = 0.0
    execution_time_ms: float = 0.0
    errors: List[str] = field(default_factory=list)


class SwarmIntelligenceAgent(BaseAgent):
    """Agent that spawns multi-agent swarms for complex trading research.

    Leverages Vibe Trading AI's 29 team presets to coordinate multiple
    specialist agents in parallel, synthesizing their findings into
    actionable insights.
    """

    def __init__(self, memory=None):
        super().__init__(name="SwarmIntelligence", memory=memory)
        self.vibe = vibe_gateway
        self._available = self.vibe.is_available

        self._preset_capabilities = {
            "investment-committee": {
                "description": "Multi-asset portfolio analysis with risk budgeting",
                "agents": [
                    "portfolio_manager",
                    "risk_analyst",
                    "macro_strategist",
                    "asset_allocator",
                    "performance_tracker",
                ],
            },
            "crypto-trading-desk": {
                "description": "On-chain analytics, order flow, and derivatives positioning",
                "agents": [
                    "on_chain_analyst",
                    "order_flow_trader",
                    "derivatives_specialist",
                    "liquidity_mapper",
                    "sentiment_tracker",
                ],
            },
            "macro-research": {
                "description": "Global macro analysis across currencies, bonds, and commodities",
                "agents": [
                    "fx_strategist",
                    "bond_analyst",
                    "commodity_specialist",
                    "macro_indicator_tracker",
                    "policy_analyst",
                ],
            },
            "technical-analysis-team": {
                "description": "Multi-timeframe technical analysis with pattern recognition",
                "agents": [
                    "chart_pattern_analyst",
                    "indicator_specialist",
                    "wave_analyst",
                    "pivot_point_tracker",
                    "trend_strength_evaluator",
                ],
            },
            "risk-management-desk": {
                "description": "Portfolio-level risk analysis and hedging strategies",
                "agents": [
                    "var_analyst",
                    "correlation_tracker",
                    "stress_tester",
                    "hedging_strategist",
                    "risk_alert_monitor",
                ],
            },
            "news-sentiment-squad": {
                "description": "Real-time news parsing and sentiment scoring",
                "agents": [
                    "news_parser",
                    "sentiment_scorer",
                    "catalyst_detector",
                    "social_media_monitor",
                    "earnings_calendar_tracker",
                ],
            },
            "earnings-whisperers": {
                "description": "Earnings preview, whisper numbers, and guidance analysis",
                "agents": [
                    "earnings_forecaster",
                    "guidance_analyst",
                    "whisper_number_tracker",
                    "beat_miss_analyst",
                    "management_sentiment_tracker",
                ],
            },
            "options-flow-desk": {
                "description": "Options order flow, gamma exposure, and volatility surface",
                "agents": [
                    "options_flow_analyst",
                    "gamma_exposure_tracker",
                    "vol_surface_maper",
                    "unusual_activity_detector",
                    "expiry_planner",
                ],
            },
            "portfolio-optimizers": {
                "description": "Mean-variance optimization and factor investing",
                "agents": [
                    "mean_variance_optimizer",
                    "factor_exposure_analyzer",
                    "rebalancing_automator",
                    "risk_budget_allocator",
                    "tax_loss_harvester",
                ],
            },
            "regime-detectors": {
                "description": "Market regime identification and regime-switching strategies",
                "agents": [
                    "regime_classifier",
                    "volatility_regime_tracker",
                    "trend_regime_analyst",
                    "correlation_regime_monitor",
                    "regime_switch_predictor",
                ],
            },
        }

    @property
    def is_available(self) -> bool:
        return self._available

    async def observe(self, context: AgentContext) -> AgentContext:
        context.observations["swarm_available"] = self._available
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        self._add_thought(
            context,
            f"Selecting swarm preset for market={context.metadata.get('market', 'crypto')}",
        )
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan.append("Select or infer the optimal swarm preset")
        context.plan.append("Execute the multi-agent swarm through Vibe")
        context.plan.append("Return synthesized committee output")
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
            "errors": result.errors,
        }
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        context.confidence = context.result.get("confidence", 0.0)
        context.reflection = (
            f"Swarm preset {context.result.get('preset', 'unknown')} completed."
        )
        return context

    async def execute(
        self,
        query: str,
        team_preset: str = "investment-committee",
        market: str = "crypto",
        context: Optional[AgentContext] = None,
    ) -> SwarmResult:
        """Execute a swarm operation.

        Args:
            query: Research question or task description
            team_preset: Pre-configured team preset to use
            market: Target market (crypto, stocks, forex, macro)
            context: Optional agent context for state tracking

        Returns:
            SwarmResult with synthesized findings
        """
        import time

        start_time = time.time()

        if not self._available:
            return SwarmResult(
                success=False,
                preset_used=team_preset,
                query=query,
                errors=[
                    "Vibe Trading AI not available. Install with: pip install vibe-trading-ai"
                ],
            )

        self._add_thought(
            context or AgentContext(task=query),
            f"Spawning {team_preset} swarm for: {query[:50]}...",
        )

        try:
            response = await asyncio.wait_for(
                self.vibe.spawn_swarm(
                    team_preset=team_preset, query=query, market=market
                ),
                timeout=180,
            )

            execution_time = (time.time() - start_time) * 1000

            if response.get("error"):
                return SwarmResult(
                    success=False,
                    preset_used=team_preset,
                    query=query,
                    execution_time_ms=execution_time,
                    errors=[response["error"]],
                )

            agents = self._preset_capabilities.get(team_preset, {}).get("agents", [])

            return SwarmResult(
                success=True,
                preset_used=team_preset,
                query=query,
                agents_activated=agents,
                synthesis=response.get("output", ""),
                confidence_score=0.85,
                execution_time_ms=execution_time,
            )

        except asyncio.TimeoutError:
            return SwarmResult(
                success=False,
                preset_used=team_preset,
                query=query,
                errors=["Swarm operation timed out after 180s"],
            )
        except Exception as e:
            logger.error(f"Swarm execution failed: {e}")
            return SwarmResult(
                success=False, preset_used=team_preset, query=query, errors=[str(e)]
            )

    async def run_cross_market_analysis(
        self, assets: List[str], query: str
    ) -> Dict[str, Any]:
        """Run analysis across multiple markets simultaneously.

        Args:
            assets: List of tickers (e.g., ["BTC-USD", "SPY", "NIFTY"])
            query: Analysis question

        Returns:
            Cross-market insights
        """
        if not self._available:
            return {"error": "Vibe Trading AI not available"}

        return await self.vibe.cross_market_analysis(assets=assets, query=query)

    def list_available_presets(self) -> List[Dict[str, Any]]:
        """List all available swarm presets with descriptions."""
        return [{"preset": k, **v} for k, v in self._preset_capabilities.items()]

    async def recommend_preset(self, query: str) -> str:
        """Recommend the best preset based on query keywords."""
        query_lower = query.lower()

        if any(k in query_lower for k in ["crypto", "btc", "eth", "defi", "on-chain"]):
            return "crypto-trading-desk"
        elif any(
            k in query_lower
            for k in ["macro", "fed", "inflation", "gdp", "central bank"]
        ):
            return "macro-research"
        elif any(k in query_lower for k in ["earnings", "revenue", "eps", "guidance"]):
            return "earnings-whisperers"
        elif any(k in query_lower for k in ["options", "volatility", "gamma", "iv"]):
            return "options-flow-desk"
        elif any(k in query_lower for k in ["risk", "var", "hedge", "drawdown"]):
            return "risk-management-desk"
        elif any(
            k in query_lower for k in ["technical", "pattern", "indicator", "chart"]
        ):
            return "technical-analysis-team"
        elif any(k in query_lower for k in ["news", "sentiment", "social", "catalyst"]):
            return "news-sentiment-squad"
        elif any(
            k in query_lower for k in ["optimize", "portfolio", "allocate", "diversify"]
        ):
            return "portfolio-optimizers"
        elif any(
            k in query_lower for k in ["regime", "market condition", "bull", "bear"]
        ):
            return "regime-detectors"
        else:
            return "investment-committee"


swarm_agent = SwarmIntelligenceAgent()
