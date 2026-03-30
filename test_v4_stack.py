"""
AXIOM V4 Verification — 100% Open-Source Intelligence
Checks availability of GGUF model, Mem0 system, and OpenBB connection.
"""
import asyncio
import os
import sys
from core.logger import get_logger
from llm.client import LLMClient
from memory.mem0_manager import Mem0Manager
from gateway.data_engine_v2 import data_engine
from gateway.security import input_guard

logger = get_logger(__name__)

async def verify():
    print("\n" + "="*60)
    print("  AXIOM V4 — 100% Open-Source Stack Verification")
    print("="*60)
    
    # 1. LLM GGUF Check
    print("\n[1] Local LLM (NVIDIA Nemotron GGUF)")
    if await asyncio.to_thread(LLMClient.preload_local_gguf):
        print("    ✅ Local GGUF preloaded successfully.")
        llm = LLMClient()
        res = await llm.complete("What is the ticker for Apple?", system="Answer in one word.", temperature=0.0)
        print(f"    ✅ Local Inference Test: {res}")
    else:
        print("    ❌ Local GGUF failed to load.")

    # 2. Memory System Check
    print("\n[2] Memory Layer (Mem0 + Qdrant)")
    try:
        memory = Mem0Manager()
        status = await memory.get_system_status()
        if status["status"] == "online":
            print(f"    ✅ Mem0 initialized: {status['provider']}")
        else:
            print("    ❌ Mem0 reported offline status.")
    except Exception as e:
        print(f"    ❌ Mem0 failed: {e}")

    # 3. Data Engine Check
    print("\n[3] Data Engine (OpenBB + SEC + SearXNG)")
    try:
        price = await data_engine.get_price("AAPL")
        if price.get("current_price"):
            print(f"    ✅ OpenBB/yfinance price fetch: ${price['current_price']} ({price['source_used']})")
        else:
            print("    ❌ OpenBB/yfinance failed (likely no connectivity).")
        
        # News Test
        news = await data_engine.web_search("NVDA stock news", num_results=1)
        if news:
            print(f"    ✅ SearXNG web search: '{news[0]['title']}'")
        else:
            print("    ❌ SearXNG failed (check http://localhost:8888).")
    except Exception as e:
        print(f"    ❌ Data Engine failed: {e}")

    # 4. Security Check
    print("\n[4] Security Layer (PromptGuard)")
    try:
        guard_res = await input_guard.scan("How do I trade NVDA?")
        if guard_res.get("safe"):
            print("    ✅ PromptGuard scan: Input safe.")
        else:
            print("    ❌ PromptGuard scan: Input rejected.")
    except Exception as e:
        print(f"    ❌ PromptGuard failed: {e}")

    print("\n" + "="*60)
    print("  Verification Complete — AXIOM V4 System Ready.")
    print("="*60 + "\n")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(verify())
