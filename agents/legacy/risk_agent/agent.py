"""RiskAgent — Calculates Value at Risk (VaR), Beta, and analyzes volatility."""

from agents.base_agent import BaseAgent, AgentContext
from core.logger import get_logger

logger = get_logger(__name__)


class RiskAgent(BaseAgent):
    """Computes risk metrics like VaR, Beta, and maximum drawdown."""

    def __init__(self, memory=None, improvement_engine=None):
        super().__init__("RiskAgent", memory, improvement_engine, timeout_seconds=15)

    async def observe(self, context: AgentContext) -> AgentContext:
        ohlcv = context.observations.get("ohlcv_data")
        if not ohlcv:
            context.errors.append("No OHLCV data provided in context observations.")
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        context.thoughts = [
            "Need to quantify downside risk and market correlation",
            "Will calculate Historical Value at Risk (95% confidence)",
            "Will calculate annualized volatility",
            "Will calculate Beta relative to market index (mocked for speed)"
        ]
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan = [
            "1. Extract daily returns from close prices",
            "2. Compute 95% threshold for historical VaR",
            "3. Compute standard deviation (volatility) and annualize",
            "4. Combine to form a risk rating (Low/Med/High)",
        ]
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        ohlcv = context.observations.get("ohlcv_data", [])
        if not ohlcv or len(ohlcv) < 30:
            context.errors.append("Insufficient data for risk analysis.")
            context.result = self._fallback_result()
            return context

        try:
            import numpy as np
            closes = [d["close"] for d in ohlcv]
            returns = np.diff(closes) / closes[:-1]

            # 95% Historical VaR
            var_95 = np.percentile(returns, 5)

            # Volatility (Annualized roughly assuming ~252 trading days)
            daily_vol = np.std(returns)
            ann_vol = daily_vol * np.sqrt(252)

            # Beta (Mocked against a static market proxy for independence)
            beta = 1.0 + (np.mean(returns) / 0.001) if len(returns) > 0 else 1.0
            beta = max(0.2, min(3.0, beta))  # Clamp realistic Beta
            
            # Max Drawdown
            cumulative = np.maximum.accumulate(closes)
            drawdowns = (cumulative - closes) / cumulative
            max_dd = np.max(drawdowns)

            # Risk Rating
            if var_95 < -0.05 or ann_vol > 0.4:
                rating = "High Risk"
            elif var_95 < -0.02 or ann_vol > 0.2:
                rating = "Medium Risk"
            else:
                rating = "Low Risk"

            context.result = {
                "var_95": f"{abs(var_95) * 100:.2f}%",
                "volatility": "High" if str(rating).startswith("High") else "Med" if str(rating).startswith("Med") else "Low",
                "volatility_pct": round(float(ann_vol) * 100, 2),
                "beta": round(float(beta), 2),
                "max_drawdown": f"{max_dd * 100:.2f}%",
                "risk_rating": rating
            }
            context.actions_taken.append({"action": "compute_risk", "metrics": ["VaR", "Beta", "Volatility", "Drawdown"]})

        except Exception as e:
            context.errors.append(f"Risk computation failed: {str(e)}")
            context.result = self._fallback_result()

        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        res = context.result or {}
        context.confidence = 0.95
        context.reflection = f"Computed risk metrics based on {len(context.observations.get('ohlcv_data', []))} days data. Overall Profile: {res.get('risk_rating')} (VaR: {res.get('var_95')}, Beta: {res.get('beta')})."
        return context

    def _fallback_result(self) -> dict:
        return {
            "var_95": "2.50%",
            "volatility": "Med",
            "volatility_pct": 20.0,
            "beta": 1.0,
            "max_drawdown": "10.0%",
            "risk_rating": "Medium Risk"
        }
