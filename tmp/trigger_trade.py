import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from gateway.hyperliquid_service import hyperliquid_trading_service
from core.logger import get_logger

logger = get_logger("TradeExecution")

async def execute_trade():
    print(f"\n{'='*60}")
    print(f"💰 TRIGGERING LIVE HYPERLIQUID TRADING CYCLE")
    print(f"{'='*60}\n")

    try:
        # Run the full trading logic cycle
        # This will:
        # 1. Fetch current positions
        # 2. Close losers (if any)
        # 3. Analyze active assets (BTC-USD, etc.)
        # 4. Execute approved trades via the optimized Risk Manager
        await hyperliquid_trading_service.run_cycle()
        
        print(f"\n{'='*60}")
        print(f"✅ TRADING CYCLE COMPLETE")
        print(f"{'='*60}\n")

    except Exception as e:
        print(f"❌ EXECUTION FAILED: {e}")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(execute_trade())
