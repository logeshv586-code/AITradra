"""LangGraph Orchestrator — Manages state and routes the execution of the 6 agents."""

from typing import TypedDict, Any, Dict, List
from langgraph.graph import StateGraph, END
from core.logger import get_logger
from agents.base_agent import AgentContext

logger = get_logger(__name__)


class TradingAgentState(TypedDict):
    """The state dictionary passed through the LangGraph nodes."""
    ticker: str
    query: str
    context: AgentContext  # Using the BaseAgent context across nodes
    agent_outputs: Dict[str, Any]
    final_result: Dict[str, Any]
    errors: List[str]


class AgentOrchestrator:
    """Builds and compiles the LangGraph workflow for the trading platform."""

    def __init__(self, data_agent, news_agent, trend_agent, risk_agent, ml_agent, synthesis_agent):
        self.data_agent = data_agent
        self.news_agent = news_agent
        self.trend_agent = trend_agent
        self.risk_agent = risk_agent
        self.ml_agent = ml_agent
        self.synthesis_agent = synthesis_agent
        self.graph = self._build_graph()

    def _build_graph(self):
        """Construct the directed acyclic graph (DAG) for agent execution."""
        workflow = StateGraph(TradingAgentState)

        # Add Nodes
        workflow.add_node("data_node", self._run_data)
        workflow.add_node("news_node", self._run_news)
        workflow.add_node("trend_node", self._run_trend)
        workflow.add_node("risk_node", self._run_risk)
        workflow.add_node("ml_node", self._run_ml)
        workflow.add_node("synthesis_node", self._run_synthesis)

        # Edges
        workflow.set_entry_point("data_node")
        workflow.add_edge("data_node", "news_node")
        workflow.add_edge("news_node", "trend_node")
        workflow.add_edge("trend_node", "risk_node")
        workflow.add_edge("risk_node", "ml_node")
        workflow.add_edge("ml_node", "synthesis_node")
        workflow.add_edge("synthesis_node", END)

        return workflow.compile()

    async def _run_agent(self, agent, state: TradingAgentState) -> TradingAgentState:
        """Helper to run an agent and update the global state."""
        ctx = state["context"]
        
        # Inject previous observations so the agent has full context
        ctx.observations.update(state["agent_outputs"])
        
        # Run Claude Flow
        ctx = await agent.run(ctx)
        
        # Update State
        state["agent_outputs"][agent.name] = ctx.result
        if ctx.errors:
            state["errors"].extend(ctx.errors)
        return state

    async def _run_data(self, state: TradingAgentState) -> TradingAgentState:
        return await self._run_agent(self.data_agent, state)

    async def _run_news(self, state: TradingAgentState) -> TradingAgentState:
        return await self._run_agent(self.news_agent, state)

    async def _run_trend(self, state: TradingAgentState) -> TradingAgentState:
        return await self._run_agent(self.trend_agent, state)

    async def _run_risk(self, state: TradingAgentState) -> TradingAgentState:
        return await self._run_agent(self.risk_agent, state)

    async def _run_ml(self, state: TradingAgentState) -> TradingAgentState:
        return await self._run_agent(self.ml_agent, state)

    async def _run_synthesis(self, state: TradingAgentState) -> TradingAgentState:
        state = await self._run_agent(self.synthesis_agent, state)
        # The SynthesisAgent dictates the final outcome
        state["final_result"] = state["agent_outputs"].get("synthesis_agent", {})
        return state

    async def analyze(self, ticker: str, query: str = "") -> dict:
        """Main entry point to execute the LangGraph workflow."""
        logger.info(f"Starting orchestrator graph for {ticker}")
        
        initial_context = AgentContext(task=f"analyze_market:{ticker}", ticker=ticker)
        initial_state = TradingAgentState({
            "ticker": ticker,
            "query": query,
            "context": initial_context,
            "agent_outputs": {},
            "final_result": {},
            "errors": []
        })

        try:
            # Execute the compiled graph
            final_state = await self.graph.ainvoke(initial_state)
            logger.info(f"Orchestrator graph complete for {ticker}")
            
            return {
                "ticker": ticker,
                "analysis": final_state.get("final_result", {}),
                "agent_data": final_state.get("agent_outputs", {}),
                "errors": final_state.get("errors", [])
            }
        except Exception as e:
            logger.error(f"Graph execution failed: {e}")
            return {
                "ticker": ticker,
                "analysis": {"error": "Graph execution failed", "details": str(e)},
                "agent_data": {},
                "errors": [str(e)]
            }
