"""
Manual Trigger Script for MiroFish World Simulation.
Use this to run a simulation round and generate a report immediately.
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.market_scheduler import market_scheduler

async def main():
    print("🌊 Starting Manual MiroFish Simulation...")
    await market_scheduler.run_mirofish_sync()
    print("✅ Simulation complete. Check logs and KnowledgeStore for reports.")

if __name__ == "__main__":
    asyncio.run(main())
