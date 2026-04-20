import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.query_router import query_router
from agents.base_agent import AgentContext

async def test_discovery():
    print("Starting Chat Ticker Discovery Verification...")
    
    # Test 1: Explicit mention of a new ticker (Google)
    print("\n[Test 1] Query: 'Is Google stock a buy right now?'")
    ctx = AgentContext(task="Is Google stock a buy right now?", ticker="AAPL") # Context is AAPL
    result = await query_router.run(ctx)
    
    found_ticker = ctx.ticker
    print(f"-> Discovered Ticker: {found_ticker}")
    if found_ticker == "GOOGL":
        print("Success: AAPL context overridden by GOOGL discovery.")
    else:
        print(f"Failure: Expected GOOGL, got {found_ticker}")

    # Test 2: Indian Ticker discovery
    print("\n[Test 2] Query: 'How is Tata Motors doing today?'")
    ctx2 = AgentContext(task="How is Tata Motors doing today?", ticker=None)
    await query_router.run(ctx2)
    print(f"-> Discovered Ticker: {ctx2.ticker}")
    if ctx2.ticker and ("TATOMOTORS" in ctx2.ticker or "TTM" in ctx2.ticker):
        print("Success: Tata Motors identified.")
    else:
        print(f"Failure: Expected a Tata symbol, got {ctx2.ticker}")

    # Test 3: General query (No ticker)
    print("\n[Test 3] Query: 'What are the best stocks to buy?'")
    ctx3 = AgentContext(task="What are the best stocks to buy?", ticker=None)
    await query_router.run(ctx3)
    print(f"-> Discovered Ticker: {ctx3.ticker}")
    if ctx3.ticker is None:
        print("Success: No ticker discovered for general query.")
    else:
        print(f"Failure: Unexpected ticker {ctx3.ticker} discovered.")

if __name__ == "__main__":
    asyncio.run(test_discovery())
