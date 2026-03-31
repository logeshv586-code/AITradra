"""
Risk Manager Agent — Portfolio risk assessment and trade approval.
Ensures positions stay within defined limits and circuit breakers.
"""

from agents.base_agent import BaseAgent, AgentContext
from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

class RiskManagerAgent(BaseAgent):
    """
    Agent 6: Risk Manager
    Controls: MAX_POSITION_PCT, MAX_DAILY_LOSS_PCT, MAX_OPEN_POSITIONS.
    """
    
    def __init__(self):
        super().__init__(name="RiskManagerAgent", timeout_seconds=60)
        self.max_pos_pct = settings.MAX_POSITION_PCT
        self.max_daily_loss = settings.MAX_DAILY_LOSS_PCT
        self.max_open_pos = settings.MAX_OPEN_POSITIONS

    async def observe(self, context: AgentContext) -> AgentContext:
        """Fetch portfolio data from store."""
        if not context.observations.get("portfolio"):
            self._add_thought(context, "No portfolio data found. Fetching from storage.")
            # In real case might call a service
            pass
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        """Formulate risk hypothesis."""
        self._add_thought(context, f"Evaluating risk constraints for {context.ticker}.")
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        """Risk evaluation steps."""
        context.plan.append("1. Validate max open positions")
        context.plan.append("2. Check daily loss circuit breakers")
        context.plan.append("3. Calculate optimal position size")
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        ticker = context.ticker
        portfolio = context.observations.get("portfolio", {})
        current_data = context.observations.get("price_data", {})
        
        # 1. Check if we already have too many positions
        open_positions = portfolio.get("open_positions", [])
        if len(open_positions) >= self.max_open_pos:
            context.result = {
                "decision": "BLOCK",
                "reason": f"Max open positions ({self.max_open_pos}) reached.",
                "risk_score": 1.0
            }
            return context

        # 2. Check Daily Loss Circuit Breaker
        daily_pnl_pct = portfolio.get("daily_pnl_pct", 0.0)
        if daily_pnl_pct <= -self.max_daily_loss:
            context.result = {
                "decision": "BLOCK",
                "reason": f"Daily loss limit ({self.max_daily_loss*100}%) exceeded.",
                "risk_score": 1.0
            }
            return context

        # 3. Calculate Position Size
        total_value = portfolio.get("total_value", 100000.0) # Default to 100k if not provided
        suggested_pos_size = total_value * self.max_pos_pct
        
        context.result = {
            "decision": "APPROVE",
            "reason": f"Trade within risk parameters for {ticker}.",
            "suggested_position_size": round(suggested_pos_size, 2),
            "max_position_pct": self.max_pos_pct,
            "risk_score": 0.2
        }
        
        self._add_thought(context, f"Risk Manager approved {ticker}. Position size capped at {self.max_pos_pct*100}%.")
        
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        """Verify the risk assessment."""
        decision = context.result.get("decision", "BLOCK")
        context.reflection = f"Risk decision for {context.ticker}: {decision}."
        context.confidence = 1.0 # Risk logic is deterministic
        return context
