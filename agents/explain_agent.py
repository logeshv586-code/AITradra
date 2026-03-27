from llm.client import LLMClient
import json
import asyncio
from agents.base_agent import BaseAgent, AgentContext

class ExplainAgent(BaseAgent):
    """Agent 7: Explanation Agent - Human-readable explanation using NVIDIA NIM and Claude Flow."""
    
    def __init__(self, memory=None, improvement_engine=None):
        super().__init__(name="ExplanationAgent", memory=memory, improvement_engine=improvement_engine)
        self.llm = LLMClient()

    async def observe(self, context: AgentContext) -> AgentContext:
        symbol = context.ticker or context.task.split()[-1]
        context.ticker = symbol
        self._add_thought(context, f"Gathering multi-source signals for {symbol}")
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        self._add_thought(context, f"Synthesizing technical and semantic data points specifically for {context.ticker}.")
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan = [
            "Structure pricing, news, and historical context",
            "Construct high-fidelity prompt for NVIDIA Nemotron",
            "Execute LLM generation for market narrative",
            "Extract top 2 actionable catalysts"
        ]
        self._add_thought(context, "Synthesis plan finalized for NVIDIA NIM.")
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        symbol = context.ticker
        price_data = context.metadata.get("price_data", {})
        news_data = context.metadata.get("news_data", [])
        rag_context = context.metadata.get("rag_context", [])
        
        self._add_thought(context, f"Acting: Generating NVIDIA NIM explanation for {symbol}...")
        
        # Construct prompt
        news_summaries = "\n".join([f"- {n['title']} ({n['publisher']})" for n in news_data])
        rag_info = json.dumps(rag_context[:3], indent=2)
        
        prompt = f"""
        Analyze the price movement for {symbol}.
        Current Data: {json.dumps(price_data, indent=2)}
        Recent News:
        {news_summaries}
        
        Historical Context:
        {rag_info}
        
        Provide a concise, human-readable explanation of why the price moved (up/down/sideways) 
        and identify 2 major catalysts. Keep it professional and under 3 sentences.
        """
        
        system_msg = "You are AXIOM, a professional market intelligence analyst specializing in high-frequency data synthesis."
        
        try:
            explanation = await self.llm.complete(prompt, system=system_msg)
            context.result = {
                "symbol": symbol,
                "explanation": explanation.strip(),
                "catalysts": [n['title'] for n in news_data[:2]] if news_data else ["Market Volatility", "Technical Factors"]
            }
            context.actions_taken.append({"action": "nvidia_nim_synthesis", "status": "success"})
        except Exception as e:
            context.errors.append(f"Explanation error: {str(e)}")
            context.result = {"symbol": symbol, "explanation": "Unable to synthesize intelligence at this time."}
            
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        if context.result and not context.errors:
            context.reflection = f"Generated high-fidelity market narrative for {context.ticker}."
            context.confidence = 0.92
        return context

    # Legacy compatibility
    async def explain(self, symbol: str, price_data: dict, news_data: list, rag_context: list):
        ctx = AgentContext(task=f"Explain {symbol}", ticker=symbol, metadata={
            "price_data": price_data,
            "news_data": news_data,
            "rag_context": rag_context
        })
        res = await self.run(ctx)
        return res.result

if __name__ == "__main__":
    agent = ExplainAgent()
    async def test():
        res = await agent.explain("AAPL", {"day_change": -1.2}, [{"title": "Supply chain issues"}], [])
        print(res)
    asyncio.run(test())
