import asyncio
from llm.client import LLMClient

async def main():
    llm = LLMClient()
    print("Provider:", llm.provider_type)
    res = await llm._try_lmstudio("Hello", "You are an AI", 0.1, 100)
    print("LM Studio output:", res)
    
asyncio.run(main())
