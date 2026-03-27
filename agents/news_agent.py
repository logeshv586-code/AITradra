import yfinance as yf
from datetime import datetime, timezone
import json
import asyncio
from agents.base_agent import BaseAgent, AgentContext

class NewsAgent(BaseAgent):
    """Agent 4: News Intelligence Agent - Explains 'Why price moved' using Claude Flow."""
    
    def __init__(self, memory=None, improvement_engine=None):
        super().__init__(name="NewsIntelligenceAgent", memory=memory, improvement_engine=improvement_engine)

    async def observe(self, context: AgentContext) -> AgentContext:
        symbol = context.ticker or context.task.split()[-1]
        context.ticker = symbol
        self._add_thought(context, f"Observing recent news catalysts for {symbol}")
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        self._add_thought(context, f"Analyzing news impact for {context.ticker}. Identifying top titles and publishers.")
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan = [
            "Access yfinance news feed",
            "Extract title, publisher, and timestamp",
            "Prepare for sentiment analysis batching"
        ]
        self._add_thought(context, "News retrieval plan active.")
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        symbol = context.ticker
        self._add_thought(context, f"Acting: Fetching news for {symbol}...")
        try:
            ticker = yf.Ticker(symbol)
            news = ticker.news
            
            processed_news = []
            for item in news[:5]:
                processed_news.append({
                    "title": item.get("title"),
                    "publisher": item.get("publisher"),
                    "link": item.get("link"),
                    "timestamp": datetime.fromtimestamp(item.get("providerPublishTime"), timezone.utc).isoformat() if item.get("providerPublishTime") else None,
                    "sentiment": "Neutral" # Initial state
                })
            context.result = processed_news
            context.actions_taken.append({"action": "fetch_news", "count": len(processed_news)})
        except Exception as e:
            context.errors.append(f"News fetch error: {str(e)}")
            
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        if context.result:
            context.reflection = f"Collected {len(context.result)} news items for {context.ticker}."
            context.confidence = 0.85
        return context

    # Legacy compatibility
    def fetch_news(self, symbol: str):
        loop = asyncio.get_event_loop()
        ctx = AgentContext(task=f"Fetch news for {symbol}", ticker=symbol)
        res = loop.run_until_complete(self.run(ctx))
        return res.result if isinstance(res.result, list) else []

if __name__ == "__main__":
    async def test():
        agent = NewsAgent()
        res = await agent.run(AgentContext(task="Fetch news for TSLA"))
        print(json.dumps(res.result, indent=2))
    
    asyncio.run(test())
