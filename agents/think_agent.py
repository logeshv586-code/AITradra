import asyncio
import json
from agents.base_agent import BaseAgent, AgentContext

class ThinkAgent(BaseAgent):
    """
    Agent 9: Think Agent - The Model Tuning Layer for multi-step reasoning.
    Synthesizes current price, historical trends, news sentiment, and RAG context.
    """
    
    def __init__(self, memory=None, improvement_engine=None):
        super().__init__(name="ThinkAgent", memory=memory, improvement_engine=improvement_engine)
        self.system_prompt = """
        You are AXIOM Market Intelligence Think Engine.
        Your goal is professional-grade financial reasoning and synthesis.

        Analyze:
        1. Current price movement and volatility.
        2. Historical movement (1d, 1w, 1m).
        3. News sentiment and catalysts.
        4. Market and Sector trends.
        5. RAG-indexed historical intelligence.

        Return a structured JSON report:
        {
          "summary": "Short explanation",
          "detailed_reasoning": "Long explanation",
          "bull_case": ["point1", "point2"],
          "bear_case": ["point1", "point2"],
          "confidence_score": 0.0-1.0,
          "signal": "BULLISH/BEARISH/NEUTRAL",
          "catalysts": ["catalyst1", "catalyst2"]
        }

        Use financial reasoning and avoid hallucination.
        """

    async def observe(self, context: AgentContext) -> AgentContext:
        self._add_thought(context, f"Observing multi-dimensional data for {context.ticker}")
        context.observations["has_price"] = "price_data" in context.metadata
        context.observations["has_news"] = "news_data" in context.metadata
        context.observations["has_history"] = "history_data" in context.metadata
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        self._add_thought(context, "Synthesizing confluence between price action and news catalysts.")
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan = [
            "Correlate news sentiment with recent price spikes",
            "Evaluate historical resistance/support from RAG data",
            "Assess sector-wide momentum",
            "Generate institutional-grade synthesis"
        ]
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        self._add_thought(context, "Running Chain-of-Thought synthesis via LLM backend...")
        
        # Prepare the reasoning prompt
        meta = context.metadata
        prompt = f"""
        TICKER: {context.ticker}
        PRICE DATA: {json.dumps(meta.get('price_data', {}))}
        NEWS DATA: {json.dumps(meta.get('news_data', {}))}
        HISTORY: {json.dumps(meta.get('history_data', {}))}
        RAG CONTEXT: {json.dumps(meta.get('rag_context', []))}
        
        Execute your thinking process now.
        """
        
        # In a real scenario, this would call the LLMClient
        # For this implementation, we simulate the high-fidelity synthesis
        # result = await self.llm.complete(prompt, system=self.system_prompt)
        
        # Mock result for logic path verification
        context.result = {
            "summary": f"Strong bullish confluence detected for {context.ticker} based on earnings beat and sector rotation.",
            "detailed_reasoning": "The synthesis engine detects a 4% deviation from the 200-day moving average coinciding with high-volume news sentiment. RAG historical data suggests this pattern precedes a breakout in 72% of cases.",
            "bull_case": ["Record margins", "Sector tailwinds"],
            "bear_case": ["Macro rate uncertainty"],
            "confidence_score": 0.88,
            "signal": "BULLISH",
            "catalysts": ["Q4 Earnings", "New product launch"]
        }
        
        context.actions_taken.append({"action": "deep_reasoning_synthesis"})
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        if context.result and context.result.get("confidence_score", 0) > 0.8:
            context.reflection = "High-confidence reasoning complete. Signal strength is robust."
        else:
            context.reflection = "Analysis complete, but macro volatility suggests caution."
        return context

if __name__ == "__main__":
    async def test():
        agent = ThinkAgent()
        ctx = AgentContext(task="Analyze AAPL", ticker="AAPL", metadata={
            "price_data": {"price": 180, "change": 2.5},
            "news_data": [{"title": "Apple hits record high", "sentiment": 0.9}]
        })
        res = await agent.run(ctx)
        print(json.dumps(res.result, indent=2))
    
    asyncio.run(test())
