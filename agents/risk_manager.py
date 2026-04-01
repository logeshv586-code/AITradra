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

        # 3. Calculate Conviction-Based Position Size
        # Determine conviction from orchestrator context
        consensus = context.observations.get("consensus", "NEUTRAL")
        confidence = context.observations.get("confidence", 0.7) # Static default fallback
        
        # Sizing multiplier based on confidence
        if confidence >= 0.85:
            multiplier = 1.0   # Full sizing for high conviction
        elif confidence >= 0.70:
            multiplier = 0.6   # Conservative sizing
        elif confidence >= 0.50:
            multiplier = 0.25  # Experimental sizing
        else:
            multiplier = 0.0   # Block if very low confidence

        if multiplier == 0:
             context.result = {
                "decision": "BLOCK",
                "reason": f"Conviction threshold too low ({confidence*100}%) for trade approval.",
                "risk_score": 0.9
            }
             return context

        total_value = portfolio.get("total_value", 100000.0)
        base_pos_size = total_value * self.max_pos_pct
        suggested_pos_size = base_pos_size * multiplier
        
        context.result = {
            "decision": "APPROVE",
            "reason": f"Conviction-based sizing approved for {ticker} (Conf: {confidence*100}%).",
            "suggested_position_size": round(suggested_pos_size, 2),
            "sizing_multiplier": multiplier,
            "max_position_pct": self.max_pos_pct,
            "confidence": confidence,
            "risk_score": 0.2 + (1.0 - confidence) * 0.5
        }
        
        self._add_thought(context, f"Risk Manager applied conviction multiplier of {multiplier*100}% for {ticker} based on {confidence*100}% confidence.")
        
        return context


    async def reflect(self, context: AgentContext) -> AgentContext:
        """Verify the risk assessment."""
        decision = context.result.get("decision", "BLOCK")
        context.reflection = f"Risk decision for {context.ticker}: {decision}."
        context.confidence = 1.0 # Risk logic is deterministic
        return context
