"""SynthesisAgent — Final reviewer and combiner using LLM Chain of Thought."""

from agents.base_agent import BaseAgent, AgentContext
from core.logger import get_logger
from core.config import settings

logger = get_logger(__name__)


class SynthesisAgent(BaseAgent):
    """The master node that takes all inputs, critiques them, and renders final verdict."""

    def __init__(self, memory=None, improvement_engine=None):
        super().__init__("synthesis_agent", memory, improvement_engine, timeout_seconds=45)

    async def observe(self, context: AgentContext) -> AgentContext:
        """Gather all other agent outputs from the orchestrator graph state."""
        keys = ["DataAgent", "NewsAgent", "TrendAgent", "RiskAgent", "MLAgent"]
        missing = []
        for key in keys:
            if key not in context.observations:
                missing.append(key)
        
        if missing:
            logger.warning(f"Synthesis running with missing observations: {missing}")

        return context

    async def think(self, context: AgentContext) -> AgentContext:
        context.thoughts = [
            "Synthesizing inputs from 5 previous cognitive engines",
            "Will apply chain-of-thought to resolve conflicting signals",
            "Will perform self-critique: 'What could be wrong with this thesis?'",
            "Will compile final confidence bounded by risk and data quality"
        ]
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan = [
            "1. Ingest all agent outputs via prompt generation",
            "2. Send to LLM (Ollama) with strict JSON schema instructions",
            "3. Parse LLM reasoning chain and final recommendation",
            "4. Adjust confidence based on risk ceiling"
        ]
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        import json
        
        obs = context.observations
        ticker = context.ticker
        
        # Build giant specific prompt
        sys_prompt = f"You are AXIOM, an elite AI hedge fund manager analyzing {ticker}. You will receive data from 5 specialized agents. Synthesize this data strictly into a JSON structure."
        
        user_prompt = f"""
        TICKER: {ticker}
        
        DATA AGENT:
        {json.dumps(obs.get('DataAgent', {}), indent=2)}
        
        NEWS AGENT:
        {json.dumps(obs.get('NewsAgent', {}), indent=2)}
        
        TREND AGENT (TA):
        {json.dumps(obs.get('TrendAgent', {}), indent=2)}
        
        RISK AGENT:
        {json.dumps(obs.get('RiskAgent', {}), indent=2)}
        
        ML AGENT:
        {json.dumps(obs.get('MLAgent', {}), indent=2)}
        
        Critique the data. Find misalignments. For example, if ML is Bullish but Trend is Bearish Cross, highlight this. 
        If Risk is High, cap your overall confidence. 
        
        Respond with ONLY this JSON structure (no markdown fences, just pure JSON):
        {{
            "recommendation": "STRONG BUY|BUY|HOLD|SELL|STRONG SELL",
            "confidence": 0.0 to 100.0,
            "chain_of_thought": ["step 1", "step 2", "step 3"],
            "self_critique": "What could be wrong with this call?",
            "final_summary": "1-2 sentence executive summary."
        }}
        """

        try:
            # We must import the global LLM client since it was initialized in lifespan,
            # or we could construct a fresh one. We'll construct a fresh one for the agent if needed.
            from llm.client import LLMClient
            llm = LLMClient()
            
            response_text = await llm.complete(
                prompt=user_prompt,
                system=sys_prompt,
                temperature=settings.LLM_TEMPERATURE
            )
            
            # Clean up potential markdown formatting from LLM
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            
            parsed = json.loads(clean_text)
            context.result = parsed
            context.actions_taken.append({"action": "llm_synthesis", "backend": settings.LLM_MODEL})
            
        except json.JSONDecodeError as dict_e:
            context.errors.append(f"Failed to parse LLM JSON: {str(dict_e)}")
            context.result = self._fallback_synthesis(obs)
            
        except Exception as e:
            context.errors.append(f"Synthesis failed: {str(e)}")
            context.result = self._fallback_synthesis(obs)

        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        res = context.result or {}
        confidence = float(res.get("confidence", 50.0)) / 100.0
        
        # Artificial cap based on risk
        risk_obs = context.observations.get("RiskAgent", {}).get("risk_rating", "")
        if "High" in risk_obs and confidence > 0.70:
            confidence = 0.70  # Cap confidence internally
            
        context.confidence = confidence
        context.reflection = res.get("self_critique", "Self critique completed.")
        return context

    def _fallback_synthesis(self, obs: dict) -> dict:
        """Procedural synthesis if LLM fails."""
        ml_dir = obs.get("MLAgent", {}).get("direction", "NEUTRAL")
        trend_score = obs.get("TrendAgent", {}).get("momentum_score", 0)
        
        rec = "HOLD"
        conf = 50.0
        
        if ml_dir == "BULLISH" and trend_score > 0:
            rec = "BUY"
            conf = 75.0
        elif ml_dir == "BEARISH" and trend_score < 0:
            rec = "SELL"
            conf = 75.0
            
        return {
            "recommendation": rec,
            "confidence": conf,
            "chain_of_thought": [
                "LLM backend failed. Procedurally synthesizing.",
                f"ML direction: {ml_dir}",
                f"Trend momentum: {trend_score}"
            ],
            "self_critique": "Procedural fallback lacks nuance of news sentiment and macro integration.",
            "final_summary": f"System defaults to {rec} based on strict ML + TA alignment due to LLM drop."
        }
