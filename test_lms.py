import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from llm.client import LLMClient
from core.config import settings

async def test_lms_integration():
    print(f"Testing LM Studio Integration...")
    print(f"URL: {settings.LM_STUDIO_URL}")
    print(f"Model: {settings.LM_STUDIO_MODEL}")
    
    llm = LLMClient()
    print(f"Provider: {llm.provider}")
    
    try:
        response = await llm.complete(
            prompt="Hello from AITradra test suite",
            system="You are a helpful assistant",
            expect_json=True
        )
        print(f"Response: {response}")
    except Exception as e:
        print(f"Error during completion: {e}")

if __name__ == "__main__":
    asyncio.run(test_lms_integration())
