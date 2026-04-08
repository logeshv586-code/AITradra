"""
Risk Manager Agent — Portfolio risk assessment and trade approval.
Ensures positions stay within defined limits and circuit breakers.
"""

from agents.base_agent import BaseAgent, AgentContext
from core.config import settings
from core.logger import get_logger
from core.scoring import get_recommendation

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

        # 2. Daily Loss Circuit Breaker
        daily_pnl_pct = portfolio.get("daily_pnl_pct", 0.0)
        if daily_pnl_pct <= -self.max_daily_loss:
            context.result = {
                "decision": "BLOCK",
                "reason": f"Daily loss limit ({self.max_daily_loss*100}%) exceeded.",
                "risk_score": 1.0
            }
            return context

        # 3. Hyperliquid Specific: Force Close at Threshold
        # Check current positions for any that exceed the force close loss threshold
        for pos in open_positions:
            unrealized_pnl_pct = pos.get("unrealized_pnl_pct", 0.0)
            if unrealized_pnl_pct <= -settings.FORCE_CLOSE_LOSS_PCT:
                self._add_thought(context, f"FORCE CLOSE TRIGGERED for {pos['ticker']} at {unrealized_pnl_pct*100}% loss.")
                context.result = {
                    "decision": "FORCE_CLOSE",
                    "ticker": pos["ticker"],
                    "reason": f"Position hit {settings.FORCE_CLOSE_LOSS_PCT*100}% loss threshold.",
                    "risk_score": 1.0
                }
                return context

        # 4. Balance Reserve Protection
        total_balance = portfolio.get("total_value", 0.0)
        available_cash = portfolio.get("cash", 0.0)
        reserve_amount = total_balance * settings.BALANCE_RESERVE_PCT
        
        if available_cash < reserve_amount:
             context.result = {
                "decision": "BLOCK",
                "reason": f"Available cash ({available_cash}) below reserved threshold ({reserve_amount}).",
                "risk_score": 0.95
            }
             return context

        # 5. Leverage Verification
        requested_leverage = context.observations.get("requested_leverage", 1)
        if requested_leverage > settings.MAX_LEVERAGE:
            self._add_thought(context, f"Capping leverage from {requested_leverage}x to {settings.MAX_LEVERAGE}x.")
            requested_leverage = settings.MAX_LEVERAGE

        # 6. Calculate Conviction-Based Position Size
        # Use results from Aggregator if available in context
        agg_result = context.observations.get("signal_aggregator_result", {})
        consensus = agg_result.get("verdict", "HOLD")
        confidence = agg_result.get("confidence", 0.5)
        
        # Determine risk-adjusted recommendation
        risk_level = "LOW"
        stats = context.observations.get("historical_stats", {})
        vol = stats.get("annualized_volatility", 20.0)
        if vol > 50: risk_level = "HIGH"
        elif vol > 30: risk_level = "MEDIUM"
        
        rec = get_recommendation(
            direction="UP" if consensus == "BUY" else "DOWN" if consensus == "SELL" else "SIDEWAYS",
            confidence=confidence,
            risk_level=risk_level
        )

        multiplier = 0.0
        if rec == "BUY":
            multiplier = 1.0 if confidence >= 80 else 0.6 if confidence >= 65 else 0.3
        
        if multiplier == 0 and rec != "BUY":
             context.result = {
                "decision": "BLOCK",
                "reason": f"System recommendation is {rec} (Confidence: {confidence}%).",
                "risk_score": 0.8
            }
             return context

        base_pos_size = total_balance * self.max_pos_pct
        suggested_pos_size = base_pos_size * multiplier
        
        context.result = {
            "decision": "APPROVE",
            "reason": f"Risk validated. Recommendation: {rec}. Sizing: {suggested_pos_size}.",
            "suggested_position_size": round(suggested_pos_size, 2),
            "leverage": requested_leverage,
            "sizing_multiplier": multiplier,
            "confidence": confidence,
            "risk_score": round(0.2 + (1.0 - confidence/100) * 0.5, 2)
        }
        
        return context


    async def reflect(self, context: AgentContext) -> AgentContext:
        """Verify the risk assessment."""
        decision = context.result.get("decision", "BLOCK")
        context.reflection = f"Risk decision for {context.ticker}: {decision}."
        context.confidence = 1.0 # Risk logic is deterministic
        return context
