from datetime import datetime, timezone
import json
import asyncio
from agents.base_agent import BaseAgent, AgentContext


class DataAgent(BaseAgent):
    """Agent 1: decision-grade real-time market data collector."""

    def __init__(self, memory=None, improvement_engine=None):
        super().__init__(name="DataCollectorAgent", memory=memory, improvement_engine=improvement_engine)

    async def observe(self, context: AgentContext) -> AgentContext:
        symbol = context.ticker or context.task.split()[-1]
        context.ticker = symbol
        self._add_thought(context, f"Observing market data requirements for {symbol}")
        context.observations["target_symbol"] = symbol
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        symbol = context.observations["target_symbol"]
        self._add_thought(
            context,
            f"Using one configured real-time provider for {symbol}; no fallback or stale substitution is permitted.",
        )
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        symbol = context.observations["target_symbol"]
        context.plan = [
            f"Fetch {symbol} from the configured real-time provider",
            "Validate positive live price and provenance",
            "Reuse only inside the configured short validity window",
            "Fail closed when live data expires or the provider is unavailable",
        ]
        self._add_thought(context, "Strict real-time data plan formulated.")
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        symbol = context.observations["target_symbol"]
        self._add_thought(context, f"Acting: fetching decision-grade live data for {symbol}...")

        try:
            from gateway.live_price_session import live_price_session

            price_data = await live_price_session.get(symbol)
            px = float(price_data["px"])
            data = {
                "symbol": symbol,
                "name": symbol,
                "price": px,
                "change_pct": price_data.get("pct_chg", 0),
                "volume": price_data.get("volume", 0),
                "market_cap": price_data.get("mktcap", 0),
                "sector": "N/A",
                "industry": "N/A",
                "exchange": "N/A",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source_used": price_data.get("source_used"),
                "observed_at": price_data.get("observed_at"),
                "expires_at": price_data.get("expires_at"),
                "freshness_seconds": price_data.get("freshness_seconds"),
                "validity_seconds": price_data.get("validity_seconds"),
                "decision_grade": True,
                "fallback_used": False,
            }
            context.result = data
            context.actions_taken.append({"action": "fetch_strict_live_price", "status": "success"})
        except Exception as e:
            context.result = None
            context.confidence = 0.0
            context.errors.append(str(e))
            context.actions_taken.append({"action": "fetch_strict_live_price", "status": "blocked", "error": str(e)})

        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        if context.result and not context.errors:
            context.reflection = (
                f"Retrieved decision-grade real-time data for {context.ticker} from "
                f"{context.result.get('source_used')} with no fallback."
            )
            context.confidence = 0.95
        else:
            context.reflection = f"Live data unavailable for {context.ticker}; downstream qualification must remain blocked."
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
