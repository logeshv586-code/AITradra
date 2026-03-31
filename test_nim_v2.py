import asyncio
import os
from llm.client import LLMClient
from core.config import settings

async def verify_nim():
    print(f"Testing NIM Connectivity...")
    print(f"Provider: {settings.LLM_PROVIDER}")
    print(f"Base URL: {settings.NVIDIA_BASE_URL}")
    
    client = LLMClient()
    
    test_prompt = "Say 'NIM is Active' if you can read this."
    try:
        # Test reasoning model (Nemotron)
        res = await client.complete(test_prompt, role="reasoning")
        print(f"NIM Reasoning Response: {res}")
        
        # Test sentiment model (Mistral)
        res_sent = await client.complete(test_prompt, role="sentiment")
        print(f"NIM Sentiment Response: {res_sent}")
        
        print("NIM Integration Verified.")
    except Exception as e:
        print(f"NIM Verification Failed: {e}")

if __name__ == "__main__":
    asyncio.run(verify_nim())
