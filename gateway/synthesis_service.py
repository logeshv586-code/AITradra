import asyncio
import json
from datetime import datetime
from core.logger import get_logger
from gateway.data_engine import data_engine
from llm.client import LLMClient

logger = get_logger(__name__)

class SynthesisService:
    def __init__(self, orchestrator, rag_agent):
        self.orchestrator = orchestrator
        self.rag_agent = rag_agent
        self.llm = LLMClient()

    async def generate_v3_1_synthesis(self, ticker: str, user_query: str = None) -> str:
        logger.info(f"🚀 Initializing OMNI-DATA v3.1 Hyper-Synthesis for {ticker}")
        
        # 1. Run full 14-agent orchestrator
        orchestration_result = await self.orchestrator.analyze(ticker)
        agent_data = orchestration_result.get("agent_data", {})
        
        # 2. Get real-time price data from DataEngine
        price_data = await data_engine.get_price_data(ticker)
        
        # 3. Use RAG to extract most critical insights from agent outputs
        # We'll index the agent observations temporarily
        insight_blobs = []
        for agent_name, output in agent_data.items():
            if isinstance(output, dict):
                text = json.dumps(output)
                insight_blobs.append(f"Agent {agent_name}: {text}")
        
        # For v3.1 simplicity, we'll feed the most relevant agent data directly to the LLM
        # but the RAG agent is used to "filter" if the data is too large.
        
        # 4. Construct the Hyper-Synthesis Prompt
        context_json = json.dumps({
            "ticker": ticker,
            "price_data": price_data,
            "agent_insights": agent_data,
            "timestamp": datetime.now().isoformat()
        })

        prompt = f"""
You are the OMNI-DATA v3.1 Neural Intelligence System. 
Synthesize a professional market report for {ticker} using the provided multi-agent intelligence.

ENFORCE THIS FORMAT EXACTLY:
🧠 OMNI-DATA — MARKET INTELLIGENCE
📊 Market Context
[Describe global/sector context based on MacroAgent and DataAgent]

📈 Key Observations
[Bulleted list of technical/fundamental insights from TrendAgent, NewsAgent, and MLAgent]

⚠️ Risk Analysis
[Critical risks from RiskAgent and OptionsFlowAgent]

🎯 Strategy
[Actionable plan from PortfolioAgent and ArbitrageAgent]

📌 Verdict
[Final signal and price target reasoning]

👉 Confidence: [X]% ([Brief justification of confidence score])

Synthesized Output
OMNI-DATA v3.1

User Query (if any): {user_query or "General Analysis"}
Data Context:
{context_json}
"""
        # 5. Execute using NVIDIA NIM exclusively (No Fallback)
        response = await self.llm.complete(
            prompt, 
            system="You are OMNI-DATA v3.1. You provide high-fidelity, data-driven synthesis. No fluff.",
            force_provider="nvidia"
        )
        
        return response

# This will be initialized in server.py
synthesis_service = None
