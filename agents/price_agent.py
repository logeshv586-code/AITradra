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
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1mo")
            if hist.empty:
                context.errors.append(f"No price history found for {symbol}")
                return context
                
            current_price = hist['Close'].iloc[-1]
            
            # 1 Day Change
            prev_day_price = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
            day_change = ((current_price - prev_day_price) / prev_day_price) * 100
            
            # 1 Week Change
            prev_week_price = hist['Close'].iloc[-5] if len(hist) > 5 else hist['Close'].iloc[0]
            week_change = ((current_price - prev_week_price) / prev_week_price) * 100
            
            # 1 Month Change
            prev_month_price = hist['Close'].iloc[0]
            month_change = ((current_price - prev_month_price) / prev_month_price) * 100
            
            data = {
                "symbol": symbol,
                "current_price": round(current_price, 2),
                "day_change": round(day_change, 2),
                "week_change": round(week_change, 2),
                "month_change": round(month_change, 2),
                "summary": f"{symbol} is {'up' if week_change > 0 else 'down'} {abs(round(week_change, 2))}% this week."
            }
            context.result = data
            context.actions_taken.append({"action": "calculate_returns", "symbol": symbol})
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
