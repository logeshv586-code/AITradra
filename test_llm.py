import asyncio
from llm.client import LLMClient

async def main():
    llm = LLMClient()
    print("Provider:", llm.provider_type)
    res = await llm.complete("Hello", max_tokens=10)
    print("Response Length:", len(res))
    if "OMNI-DATA" in res:
        print("Fell back to dummy response.")
        
asyncio.run(main())
