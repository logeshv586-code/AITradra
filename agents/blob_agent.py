import os
import json
from datetime import datetime, timezone
import asyncio
from agents.base_agent import BaseAgent, AgentContext

class BlobAgent(BaseAgent):
    """Agent 2: Blob Storage Agent - Persists market intelligence using Claude Flow."""
    
    def __init__(self, memory=None, improvement_engine=None, base_path="gateway/market_blob"):
        super().__init__(name="BlobStorageAgent", memory=memory, improvement_engine=improvement_engine)
        self.base_path = base_path
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path)

    async def observe(self, context: AgentContext) -> AgentContext:
        self._add_thought(context, f"Observing blob storage requirement for task: {context.task}")
        # Detect if we are saving or loading
        if "save" in context.task.lower():
            context.observations["mode"] = "save"
        else:
            context.observations["mode"] = "load"
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        mode = context.observations.get("mode")
        self._add_thought(context, f"Blob mode: {mode}. Ensuring directory structure is valid.")
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        mode = context.observations.get("mode")
        if mode == "save":
            context.plan = ["Validate symbol", "Create symbol directory", "Serialize JSON to disk"]
        else:
            context.plan = ["Detect symbol/date", "Check file existence", "Deserialize JSON"]
        self._add_thought(context, "Storage plan finalized.")
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        mode = context.observations.get("mode")
        data = context.metadata.get("blob_data")
        symbol = context.ticker or (data.get("symbol") if data else None)
        
        if not symbol:
            context.errors.append("Missing symbol for blob operation")
            return context

        symbol_path = os.path.join(self.base_path, symbol)
        if not os.path.exists(symbol_path):
            os.makedirs(symbol_path)

        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        file_path = os.path.join(symbol_path, f"{date_str}.json")

        if mode == "save" and data:
            self._add_thought(context, f"Saving snapshot for {symbol} to {file_path}")
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
            context.result = {"file_path": file_path, "status": "saved"}
        elif mode == "load":
            self._add_thought(context, f"Loading snapshot for {symbol} from {file_path}")
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    context.result = json.load(f)
            else:
                context.errors.append(f"No blob found for {symbol} on {date_str}")
        
        context.actions_taken.append({"action": f"blob_{mode}", "symbol": symbol})
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        if context.result and not context.errors:
            context.reflection = "Persistence operation successful. Disk I/O verified."
            context.confidence = 1.0
        else:
            context.reflection = "Persistence operation failed or incomplete."
            context.confidence = 0.0
        return context

    # Helper methods for direct call (keeping legacy compatibility)
    def save_blob(self, data: dict):
        # Wraps the async run for legacy calls if needed
        loop = asyncio.get_event_loop()
        ctx = AgentContext(task="Save blob", ticker=data.get("symbol"), metadata={"blob_data": data})
        res = loop.run_until_complete(self.run(ctx))
        return res.result.get("file_path") if res.result else None

    def load_blob(self, symbol: str):
        loop = asyncio.get_event_loop()
        ctx = AgentContext(task="Load blob", ticker=symbol)
        res = loop.run_until_complete(self.run(ctx))
        return res.result if isinstance(res.result, dict) else None

if __name__ == "__main__":
    async def test():
        agent = BlobAgent()
        # Test Save
        save_ctx = AgentContext(task="Save blob for AAPL", ticker="AAPL", metadata={"blob_data": {"symbol": "AAPL", "price": 180}})
        await agent.run(save_ctx)
        # Test Load
        load_ctx = AgentContext(task="Load blob for AAPL", ticker="AAPL")
        res = await agent.run(load_ctx)
        print(f"Loaded: {res.result}")
    
    asyncio.run(test())
