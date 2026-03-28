import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

async def test_query_router():
    from agents.query_router import query_router
    from agents.base_agent import AgentContext
    
    print("Testing QueryRouter with LLM...")
    ctx = AgentContext(task='What is the current outlook for NVDA?', ticker='NVDA')
    
    # We expect this to call the LLMClient and return a synthesized response
    result = await query_router.run(ctx)
    
    print("\n--- LLM RESPONSE ---")
    response = result.result.get('response', '')
    print(response[:800])
    
    print("\n--- METADATA ---")
    print(f"Sources used: {result.result.get('sources_used')}")
    print(f"Confidence: {result.confidence}")
    
    if "Analysis engine is initializing" in response:
        print("\n[!] WARNING: Hit the initializing fallback. The model might still be loading.")
    elif response:
        print("\n[+] SUCCESS: End-to-end LLM synthesis verified.")
    else:
        print("\n[-] FAILED: No response received.")

if __name__ == "__main__":
    asyncio.run(test_query_router())
