import yfinance as yf
from datetime import datetime, timezone
import json
import asyncio
from agents.base_agent import BaseAgent, AgentContext

class DataAgent(BaseAgent):
    """Agent 1: Data Collector Agent - Fetches stock data daily using Claude Flow."""
    
    def __init__(self, memory=None, improvement_engine=None):
        super().__init__(name="DataCollectorAgent", memory=memory, improvement_engine=improvement_engine)

    async def observe(self, context: AgentContext) -> AgentContext:
        symbol = context.ticker or context.task.split()[-1] # Basic extraction
        context.ticker = symbol
        self._add_thought(context, f"Observing market data requirements for {symbol}")
        context.observations["target_symbol"] = symbol
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        symbol = context.observations["target_symbol"]
        self._add_thought(context, f"Deciding strategy for {symbol}. Prioritizing yfinance for equity data.")
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        symbol = context.observations["target_symbol"]
        context.plan = [
            f"Initialize yfinance Ticker for {symbol}",
            "Fetch global info and current price",
            "Validate data integrity (price, change, volume)",
            "Format result for downstream agents"
        ]
        self._add_thought(context, "Plan formulated for data retrieval.")
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        symbol = context.observations["target_symbol"]
        self._add_thought(context, f"Acting: Fetching live data for {symbol}...")
        
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Get latest close price if currentPrice is missing
            price = info.get("currentPrice") or info.get("regularMarketPrice")
            if price is None:
                hist = ticker.history(period="1d")
                if not hist.empty:
                    price = hist['Close'].iloc[-1]
            
            data = {
                "symbol": symbol,
                "name": info.get("longName"),
                "price": round(float(price), 2) if price else 0.0,
                "change_pct": round(float(info.get("regularMarketChangePercent", 0)), 2),
                "volume": info.get("regularMarketVolume") or info.get("volume"),
                "market_cap": info.get("marketCap"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "exchange": info.get("exchange"),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            context.result = data
            context.actions_taken.append({"action": "fetch_yfinance", "status": "success"})
        except Exception as e:
            context.errors.append(str(e))
            context.actions_taken.append({"action": "fetch_yfinance", "status": "failed", "error": str(e)})
            
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        if context.result and not context.errors:
            context.reflection = f"Successfully retrieved data for {context.ticker}. Data appears robust."
            context.confidence = 0.95
        else:
            context.reflection = f"Failed to retrieve high-quality data for {context.ticker}."
            context.confidence = 0.0
        return context

if __name__ == "__main__":
    async def test():
        agent = DataAgent()
        ctx = AgentContext(task="Fetch data for TSLA")
        result = await agent.run(ctx)
        print(json.dumps(result.result, indent=2))
        print(f"Thoughts: {result.thoughts}")
    
    asyncio.run(test())
