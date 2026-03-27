"""
LangGraph V2 Orchestrator — Routes 14 agents through the Claude Flow pipeline.

Flow:
  DataAgent → [NewsAgent, ArbitrageAgent, MacroAgent, SocialSentimentAgent] (parallel intelligence)
  → TrendAgent → EarningsAgent → OptionsFlowAgent → RegimeDetectorAgent
  → RiskAgent → PortfolioAgent → MLAgent → SynthesisAgent → END
"""

from typing import TypedDict, Any, Dict, List
from langgraph.graph import StateGraph, END
from core.logger import get_logger
from agents.base_agent import AgentContext

logger = get_logger(__name__)


class TradingAgentState(TypedDict):
    """The state dictionary passed through the LangGraph nodes."""
    ticker: str
    query: str
    context: AgentContext
    agent_outputs: Dict[str, Any]
    final_result: Dict[str, Any]
    errors: List[str]


class AgentOrchestrator:
    """Builds and compiles the LangGraph V2 workflow for 14 agents."""

    def __init__(
        self,
        # V1 Core Agents
        data_agent, news_agent, trend_agent, risk_agent, ml_agent, synthesis_agent,
        # V2 Profit Agents (all optional — graceful degradation)
        arbitrage_agent=None, portfolio_agent=None, macro_agent=None,
        social_sentiment_agent=None, earnings_agent=None, options_flow_agent=None,
        regime_detector_agent=None, backtest_agent=None,
    ):
        # V1
        self.data_agent = data_agent
        self.news_agent = news_agent
        self.trend_agent = trend_agent
        self.risk_agent = risk_agent
        self.ml_agent = ml_agent
        self.synthesis_agent = synthesis_agent
        # V2
        self.arbitrage_agent = arbitrage_agent
        self.portfolio_agent = portfolio_agent
        self.macro_agent = macro_agent
        self.social_sentiment_agent = social_sentiment_agent
        self.earnings_agent = earnings_agent
        self.options_flow_agent = options_flow_agent
        self.regime_detector_agent = regime_detector_agent
        self.backtest_agent = backtest_agent

        self.graph = self._build_graph()

    def _build_graph(self):
        """Construct the V2 DAG with all 14 agent nodes."""
        workflow = StateGraph(TradingAgentState)

        # ── Core V1 Nodes ────────────────────────────────────
        workflow.add_node("data_node", self._run_data)
        workflow.add_node("news_node", self._run_news)
        workflow.add_node("trend_node", self._run_trend)
        workflow.add_node("risk_node", self._run_risk)
        workflow.add_node("ml_node", self._run_ml)
        workflow.add_node("synthesis_node", self._run_synthesis)

        # ── V2 Profit Nodes ──────────────────────────────────
        workflow.add_node("arbitrage_node", self._run_arbitrage)
        workflow.add_node("portfolio_node", self._run_portfolio)
        workflow.add_node("macro_node", self._run_macro)
        workflow.add_node("social_node", self._run_social)
        workflow.add_node("earnings_node", self._run_earnings)
        workflow.add_node("options_node", self._run_options)
        workflow.add_node("regime_node", self._run_regime)
        workflow.add_node("backtest_node", self._run_backtest)

        # ── Edge Wiring (Sequential Pipeline) ────────────────
        # Phase 1: Data collection
        workflow.set_entry_point("data_node")

        # Phase 2: Intelligence gathering (sequential chain for stability)
        workflow.add_edge("data_node", "news_node")
        workflow.add_edge("news_node", "arbitrage_node")
        workflow.add_edge("arbitrage_node", "macro_node")
        workflow.add_edge("macro_node", "social_node")

        # Phase 3: Technical analysis
        workflow.add_edge("social_node", "trend_node")
        workflow.add_edge("trend_node", "earnings_node")
        workflow.add_edge("earnings_node", "options_node")
        workflow.add_edge("options_node", "regime_node")

        # Phase 4: Risk & Sizing
        workflow.add_edge("regime_node", "risk_node")
        workflow.add_edge("risk_node", "portfolio_node")

        # Phase 5: ML & Synthesis
        workflow.add_edge("portfolio_node", "ml_node")
        workflow.add_edge("ml_node", "backtest_node")
        workflow.add_edge("backtest_node", "synthesis_node")
        workflow.add_edge("synthesis_node", END)

        return workflow.compile()

    # ── Agent Runner (Core Helper) ───────────────────────────
    async def _run_agent(self, agent, state: TradingAgentState, fallback_name: str = "unknown") -> TradingAgentState:
        """Run a single agent through the Claude Flow loop and update the shared state."""
        if agent is None:
            # Graceful skip — agent not initialized
            state["agent_outputs"][fallback_name] = {"status": "skipped", "reason": "Agent not configured"}
            return state

        ctx = state["context"]
        # Inject all previous agent outputs as observations
        ctx.observations.update(state["agent_outputs"])
        # Pass price data through for agents that need it
        data_result = state["agent_outputs"].get("DataAgent", {})
        if "prices" in data_result and "prices" not in ctx.observations:
            ctx.observations["prices"] = data_result["prices"]

        # Run the full Claude Flow: OBSERVE → THINK → PLAN → ACT → REFLECT → IMPROVE
        ctx = await agent.run(ctx)

        state["agent_outputs"][agent.name] = ctx.result
        if ctx.errors:
            state["errors"].extend(ctx.errors)
        return state

    # ── V1 Core Agent Runners ────────────────────────────────
    async def _run_data(self, state: TradingAgentState) -> TradingAgentState:
        return await self._run_agent(self.data_agent, state, "DataAgent")

    async def _run_news(self, state: TradingAgentState) -> TradingAgentState:
        return await self._run_agent(self.news_agent, state, "NewsAgent")

    async def _run_trend(self, state: TradingAgentState) -> TradingAgentState:
        return await self._run_agent(self.trend_agent, state, "TrendAgent")

    async def _run_risk(self, state: TradingAgentState) -> TradingAgentState:
        return await self._run_agent(self.risk_agent, state, "RiskAgent")

    async def _run_ml(self, state: TradingAgentState) -> TradingAgentState:
        return await self._run_agent(self.ml_agent, state, "MLAgent")

    async def _run_synthesis(self, state: TradingAgentState) -> TradingAgentState:
        state = await self._run_agent(self.synthesis_agent, state, "SynthesisAgent")
        state["final_result"] = state["agent_outputs"].get(self.synthesis_agent.name if self.synthesis_agent else "SynthesisAgent", {})
        return state

    # ── V2 Profit Agent Runners ──────────────────────────────
    async def _run_arbitrage(self, state: TradingAgentState) -> TradingAgentState:
        return await self._run_agent(self.arbitrage_agent, state, "ArbitrageAgent")

    async def _run_portfolio(self, state: TradingAgentState) -> TradingAgentState:
        return await self._run_agent(self.portfolio_agent, state, "PortfolioAgent")

    async def _run_macro(self, state: TradingAgentState) -> TradingAgentState:
        return await self._run_agent(self.macro_agent, state, "MacroAgent")

    async def _run_social(self, state: TradingAgentState) -> TradingAgentState:
        return await self._run_agent(self.social_sentiment_agent, state, "SocialSentimentAgent")

    async def _run_earnings(self, state: TradingAgentState) -> TradingAgentState:
        return await self._run_agent(self.earnings_agent, state, "EarningsAgent")

    async def _run_options(self, state: TradingAgentState) -> TradingAgentState:
        return await self._run_agent(self.options_flow_agent, state, "OptionsFlowAgent")

    async def _run_regime(self, state: TradingAgentState) -> TradingAgentState:
        return await self._run_agent(self.regime_detector_agent, state, "RegimeDetectorAgent")

    async def _run_backtest(self, state: TradingAgentState) -> TradingAgentState:
        return await self._run_agent(self.backtest_agent, state, "BacktestAgent")

    # ── Main Entry Point ─────────────────────────────────────
    async def analyze(self, ticker: str, query: str = "") -> dict:
        """Execute the full 14-agent LangGraph V2 pipeline."""
        logger.info(f"[AXIOM V2] Starting 14-agent orchestrator for {ticker}")

        initial_context = AgentContext(task=f"analyze_market:{ticker}", ticker=ticker)
        initial_state = TradingAgentState({
            "ticker": ticker,
            "query": query,
            "context": initial_context,
            "agent_outputs": {},
            "final_result": {},
            "errors": [],
        })

        try:
            final_state = await self.graph.ainvoke(initial_state)
            logger.info(f"[AXIOM V2] 14-agent pipeline complete for {ticker}")

            return {
                "ticker": ticker,
                "analysis": final_state.get("final_result", {}),
                "agent_data": final_state.get("agent_outputs", {}),
                "errors": final_state.get("errors", []),
                "agents_executed": list(final_state.get("agent_outputs", {}).keys()),
            }
        except Exception as e:
            logger.error(f"[AXIOM V2] Graph execution failed: {e}")
            return {
                "ticker": ticker,
                "analysis": {"error": "Graph execution failed", "details": str(e)},
                "agent_data": {},
                "errors": [str(e)],
            }
