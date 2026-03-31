import asyncio
import os
from llm.client import LLMClient
from core.config import settings

async def verify_infrastructure():
    print("--- AXIOM Intelligence Infrastructure Verification V3 ---")
    
    # 1. Initialize Client
    client = LLMClient()
    print(f"Provider: {client.provider}")
    
    # 2. Preload Local Models
    print("\nPreloading Local GGUFs...")
    success = LLMClient.preload_local_gguf()
    print(f"Local Preload Success: {success}")
    print(f"Reasoning Model Loaded: {LLMClient._local_reasoning_llm is not None}")
    print(f"General Model Loaded: {LLMClient._local_general_llm is not None}")
    
    # 3. Test NIM - Reasoning (Nemotron)
    print("\nTesting NIM Reasoning (Nemotron)...")
    try:
        res = await client.complete("What is the current macro trend for NVIDIA?", role="reasoning")
        print(f"Response: {res[:200]}...")
    except Exception as e:
        print(f"NIM Reasoning Failed: {e}")

    # 4. Test NIM - Analysis (Moonshot)
    print("\nTesting NIM Analysis (Moonshot)...")
    try:
        res = await client.complete("Summarize the impact of FED rate cuts.", role="analysis")
        print(f"Response: {res[:200]}...")
    except Exception as e:
        print(f"NIM Analysis Failed: {e}")

    # 5. Test Local Fallback (Simulation)
    print("\nTesting Local Fallback (Forcing local)...")
    # Temporarily set provider to local to force it
    original_provider = client.provider
    client.provider = "local_gguf"
    try:
        res = await client.complete("Local inference test.", role="general")
        print(f"Local General Response: {res}")
        
        res = await client.complete("Local reasoning test.", role="reasoning")
        print(f"Local Reasoning Response: {res}")
    except Exception as e:
        print(f"Local Fallback Failed: {e}")
    finally:
        client.provider = original_provider

    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    asyncio.run(verify_infrastructure())
