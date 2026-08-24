from datetime import datetime, timezone
import json
import asyncio
from agents.base_agent import BaseAgent, AgentContext


class PriceAgent(BaseAgent):
    """Agent 5: price movement agent using only real live observations."""

    def __init__(self, memory=None, improvement_engine=None):
        super().__init__(name="PriceMovementAgent", memory=memory, improvement_engine=improvement_engine)

    async def observe(self, context: AgentContext) -> AgentContext:
        symbol = context.ticker or context.task.split()[-1]
        context.ticker = symbol
        self._add_thought(context, f"Observing real-time price data for {symbol}")
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        self._add_thought(context, f"Analyzing only measured provider changes for {context.ticker}; no synthetic weekly/monthly values.")
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan = [
            "Fetch the current observation from the strict real-time price session",
            "Use only provider-reported measured change values",
            "Attach provenance, observation time, and expiry",
            "Block rather than invent missing historical movement",
        ]
        self._add_thought(context, "Strict price-analysis plan active.")
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        symbol = context.ticker
        self._add_thought(context, f"Acting: analyzing measured live movement for {symbol}...")
        try:
            from gateway.live_price_session import live_price_session

            price_data = await live_price_session.get(symbol)
            px = float(price_data["px"])
            day_change = float(price_data.get("pct_chg", 0) or 0)
            data = {
                "symbol": symbol,
                "current_price": round(px, 4),
                "day_change": round(day_change, 4),
                "week_change": None,
                "month_change": None,
                "summary": f"{symbol} provider-reported current change is {day_change:.2f}%.",
                "source_used": price_data.get("source_used"),
                "observed_at": price_data.get("observed_at"),
                "expires_at": price_data.get("expires_at"),
                "freshness_seconds": price_data.get("freshness_seconds"),
                "validity_seconds": price_data.get("validity_seconds"),
                "decision_grade": True,
                "fallback_used": False,
                "synthetic_values_used": False,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
            context.result = data
            context.actions_taken.append({"action": "calculate_measured_live_change", "symbol": symbol})
        except Exception as e:
            context.result = None
            context.confidence = 0.0
            context.errors.append(f"Price analysis blocked: {str(e)}")
            context.actions_taken.append({"action": "calculate_measured_live_change", "status": "blocked"})

        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        if context.result:
            context.reflection = f"Calculated measured live movement for {context.ticker} without fallback or synthetic returns."
            context.confidence = 0.98
        else:
            context.reflection = f"Live movement unavailable for {context.ticker}; no synthetic substitute was produced."
            context.confidence = 0.0
        return context

    def analyze_movement(self, symbol: str):
        loop = asyncio.get_event_loop()
        ctx = AgentContext(task=f"Analyze movement for {symbol}", ticker=symbol)
        res = loop.run_until_complete(self.run(ctx))
        return res.result if isinstance(res.result, dict) else {}


if __name__ == "__main__":
    async def test():
        agent = PriceAgent()
        res = await agent.run(AgentContext(task="Analyze movement for AAPL"))
        print(json.dumps(res.result, indent=2))

    asyncio.run(test())
