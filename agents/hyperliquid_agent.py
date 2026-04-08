"""
Hyperliquid Trading Agent — Specialized for Hyperliquid perp markets.
Analyzes market context and makes high-conviction trade decisions.
"""

import json
from typing import Dict, List, Optional
from agents.base_agent import BaseAgent, AgentContext
from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

class HyperliquidTradingAgent(BaseAgent):
    """
    Agent responsible for Hyperliquid trade decisions.
    Receives candle data and technical indicators.
    """
    
    def __init__(self):
        super().__init__(name="HyperliquidTradingAgent", timeout_seconds=60)

    async def observe(self, context: AgentContext) -> AgentContext:
        """Fetch market data from observations."""
        if not context.observations.get("indicators"):
            self._add_thought(context, "No technical indicators found in context.")
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        """Formulate a trading hypothesis based on indicators."""
        indicators = context.observations.get("indicators", {})
        ticker = context.ticker
        
        # Simple heuristic thought before LLM call
        rsi = indicators.get("RSI_14")
        if rsi and rsi > 70:
            self._add_thought(context, f"{ticker} RSI is {rsi:.2f} (Overbought). Considering bearish entry.")
        elif rsi and rsi < 30:
            self._add_thought(context, f"{ticker} RSI is {rsi:.2f} (Oversold). Considering bullish entry.")
        
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        """Plan the LLM analysis query."""
        context.plan.append(f"1. Analyze {context.ticker} market context (TA + Price Action)")
        context.plan.append("2. Determine direction (LONG/SHORT/HOLD)")
        context.plan.append("3. Suggest optimal leverage and allocation")
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        """Call LLM to get a structured trading decision."""
        indicators = context.observations.get("indicators", {})
        portfolio = context.observations.get("portfolio", {})
        ticker = context.ticker

        prompt = f"""
You are a professional Hyperliquid futures trader. Analyze the following data for {ticker}:

### Market Data (Latest Indicators)
{json.dumps(indicators, indent=2)}

### Portfolio Context
- Available Cash: {portfolio.get('cash', 0)}
- Total Balance: {portfolio.get('total_value', 0)}

### Rules
- Max Leverage allowed: {settings.MAX_LEVERAGE}x
- Max Position size: {settings.MAX_POSITION_PCT*100}% of portfolio
- Be decisive but risk-averse.

### Output Format (JSON)
{{
    "decision": "LONG" | "SHORT" | "HOLD",
    "reasoning": "Detailed explanation",
    "leverage": 1-10,
    "confidence": 0.0-1.0,
    "take_profit_price": float,
    "stop_loss_price": float
}}
"""
        try:
            # Using the BaseAgent's LLM capability (via Orchestrator or direct client)
            # For simplicity in this standalone agent, we'll assume the orchestrator calls this
            # or we can use the LLMClient directly if needed.
            
            # Since this is a specialized agent, we'll return the prompt in context.result for the orchestrator
            # or invoke it here if we want the agent to be self-contained.
            from llm.client import LLMClient
            llm_client = LLMClient()
            response = await llm_client.generate(prompt, system_prompt="You are an expert crypto trader.")
            
            # Extract JSON from response
            try:
                # Basic JSON extraction
                start = response.find('{')
                end = response.rfind('}') + 1
                result = json.loads(response[start:end])
                context.result = result
                context.confidence = result.get("confidence", 0.5)
            except Exception as e:
                logger.error(f"Failed to parse LLM response for {ticker}: {e}")
                context.result = {"decision": "HOLD", "reason": "LLM output parsing error"}
                
        except Exception as e:
            logger.error(f"Error in HyperliquidTradingAgent act: {e}")
            context.result = {"decision": "HOLD", "error": str(e)}

        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        """Reflect on the trading decision."""
        decision = context.result.get("decision", "HOLD")
        context.reflection = f"Hyperliquid agent decided to {decision} based on current indicators."
        context.confidence = context.result.get("confidence", 0.5)
        return context
