import asyncio
import os
import sys
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.api_agent import agent_instance
from agents.base_agent import AgentContext

async def test_v3_intelligence():
    print("--- [V3.1] Testing Intelligence Flow for AAPL ---")
    
    # 1. Fetch Stock Detail (Observe + Act)
    print("\n[Step 1] Fetching Stock Detail...")
    # Manually extract the nested function or call the instance method if exposed
    # For testing, we'll just mock the context or use the router endpoints indirectly
    # But since they are local functions in _setup_routes, we'll just test the agents directly
    
    ticker = "AAPL"
    ctx = AgentContext(task=f"Test {ticker}", ticker=ticker)
    
    print("Testing DataAgent...")
    res = await agent_instance.data_agent.run(ctx)
    print(f"Data OK: {res.result.get('name')}")
    
    print("\nTesting ExplainAgent (NVIDIA NIM)...")
    res = await agent_instance.explain_agent.run(ctx)
    print(f"Explanation: {res.result[:100]}...")
    
    print("\n--- [V3.1] Intelligence Trace Complete ---")

if __name__ == "__main__":
    try:
        asyncio.run(test_v3_intelligence())
    except RuntimeError:
        # Fallback for environments with running loops
        loop = asyncio.get_event_loop()
        loop.create_task(test_v3_intelligence())
