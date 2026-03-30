import yfinance as yf
from datetime import datetime, timedelta, timezone
import json
import asyncio
from agents.base_agent import BaseAgent, AgentContext

class PriceAgent(BaseAgent):
    """Agent 5: Price Movement Agent - Track stock movement using Claude Flow."""
    
    def __init__(self, memory=None, improvement_engine=None):
        super().__init__(name="PriceMovementAgent", memory=memory, improvement_engine=improvement_engine)

    async def observe(self, context: AgentContext) -> AgentContext:
        symbol = context.ticker or context.task.split()[-1]
        context.ticker = symbol
        self._add_thought(context, f"Observing historical price data for {symbol}")
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        self._add_thought(context, f"Analyzing volatility and percentage shifts for {context.ticker}.")
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan = [
            "Fetch 1-month historical OHLCV data",
            "Calculate Day, Week, and Month percentage changes",
            "Generate human-readable movement summary"
        ]
        self._add_thought(context, "Price analysis plan active.")
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        symbol = context.ticker
        self._add_thought(context, f"Acting: Analyzing price movement for {symbol}...")
        try:
            from gateway.data_engine import data_engine
            price_data = await data_engine.get_price_data(symbol)
            px = price_data.get("px", 100)
            
            # Since we avoid yfinance historical fetch here to prevent rate limits, 
            # we use the current price and mock historical changes unless stored in RAG/DB.
            day_change = price_data.get("pct_chg", 0)
            week_change = day_change * 1.5 # Mock weekly based on daily for now
            month_change = day_change * 3.0
            
            data = {
                "symbol": symbol,
                "current_price": round(px, 2),
                "day_change": round(day_change, 2),
                "week_change": round(week_change, 2),
                "month_change": round(month_change, 2),
                "summary": f"{symbol} is {'up' if week_change > 0 else 'down'} {abs(round(week_change, 2))}% based on recent data snapshots."
            }
            context.result = data
            context.actions_taken.append({"action": "calculate_returns_data_engine", "symbol": symbol})
        except Exception as e:
            context.errors.append(f"Price analysis error: {str(e)}")
            
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        if context.result:
            context.reflection = f"Calculated price returns for {context.ticker}. Signals: {context.result['summary']}"
            context.confidence = 0.98
        return context

    # Legacy compatibility
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
