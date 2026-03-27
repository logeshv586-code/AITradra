import yfinance as yf
import pandas as pd
from datetime import datetime, timezone
import json
import asyncio
from agents.base_agent import BaseAgent, AgentContext

class ForecastAgent(BaseAgent):
    """Agent 6: Forecast Agent - Predict future price using technical indicators and Claude Flow."""
    
    def __init__(self, memory=None, improvement_engine=None):
        super().__init__(name="ForecastAgent", memory=memory, improvement_engine=improvement_engine)

    async def observe(self, context: AgentContext) -> AgentContext:
        symbol = context.ticker or context.task.split()[-1]
        context.ticker = symbol
        self._add_thought(context, f"Observing technical patterns for {symbol} (6-month horizon)")
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        self._add_thought(context, f"Analyzing moving average crossovers and trend strength for {context.ticker}.")
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan = [
            "Fetch 6-month historical Close price data",
            "Calculate 20-day Simple Moving Average (SMA)",
            "Determine Bullish/Bearish trend based on price-to-MA distance",
            "Generate confidence score and 7-day outlook"
        ]
        self._add_thought(context, "Forecast modelling plan active.")
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        symbol = context.ticker
        self._add_thought(context, f"Acting: Generating technical forecast for {symbol}...")
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="6mo")
            if len(hist) < 20:
                context.result = {"symbol": symbol, "forecast": "Neutral", "confidence": 50}
                return context
                
            # Simple Moving Average based trend
            ma20 = hist['Close'].rolling(window=20).mean()
            current_price = hist['Close'].iloc[-1]
            current_ma20 = ma20.iloc[-1]
            
            trend = "Bullish" if current_price > current_ma20 else "Bearish"
            
            # Simple confidence based on MA crossover distance
            diff = abs(current_price - current_ma20) / current_ma20
            confidence = min(int(50 + (diff * 500)), 85) # Caps at 85% for simple logic
            
            data = {
                "symbol": symbol,
                "forecast": trend,
                "confidence": confidence,
                "period": "Next 7 days",
                "indicators": {
                    "current_price": round(current_price, 2),
                    "ma20": round(current_ma20, 2)
                }
            }
            context.result = data
            context.actions_taken.append({"action": "calculate_sma_trend", "symbol": symbol})
        except Exception as e:
            context.errors.append(f"Forecast error: {str(e)}")
            
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        if context.result:
            context.reflection = f"Forecast generated with {context.result['confidence']}% confidence. Bias: {context.result['forecast']}."
            context.confidence = 0.82
        return context

    # Legacy compatibility
    def predict(self, symbol: str):
        loop = asyncio.get_event_loop()
        ctx = AgentContext(task=f"Predict for {symbol}", ticker=symbol)
        res = loop.run_until_complete(self.run(ctx))
        return res.result if isinstance(res.result, dict) else {}

if __name__ == "__main__":
    async def test():
        agent = ForecastAgent()
        res = await agent.run(AgentContext(task="Predict for TSLA"))
        print(json.dumps(res.result, indent=2))
    
    asyncio.run(test())
