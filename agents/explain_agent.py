from llm.client import LLMClient
import json

class ExplanationAgent:
    """Agent 7: Explanation Agent - Human-readable explanation of price movement."""
    
    def __init__(self):
        self.name = "ExplanationAgent"
        self.llm = LLMClient()

    async def explain(self, symbol: str, price_data: dict, news_data: list, rag_context: list):
        print(f"[{self.name}] Generating explanation for {symbol}...")
        
        # Construct prompt
        news_summaries = "\n".join([f"- {n['title']} ({n['publisher']})" for n in news_data])
        rag_info = json.dumps(rag_context, indent=2)
        
        prompt = f"""
        Analyze the price movement for {symbol}.
        Current Data: {json.dumps(price_data, indent=2)}
        Recent News:
        {news_summaries}
        
        Historical Context:
        {rag_info}
        
        Provide a concise, human-readable explanation of why the price moved (up/down/sideways) 
        and any major catalysts. Keep it under 3 sentences.
        """
        
        try:
            explanation = await self.llm.generate(prompt)
            return {
                "symbol": symbol,
                "explanation": explanation.strip(),
                "catalysts": [n['title'] for n in news_data[:2]]
            }
        except Exception as e:
            print(f"[{self.name}] Error generating explanation: {e}")
            return {"symbol": symbol, "explanation": f"Unable to generate explanation for {symbol} at this time."}

if __name__ == "__main__":
    import asyncio
    agent = ExplanationAgent()
    async def test():
        print(await agent.explain("AAPL", {"day_change": -2.5}, [{"title": "Earnings warning"}], []))
    asyncio.run(test())
