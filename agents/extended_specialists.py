"""
AXIOM Extended Specialists — Sentiment, Fundamental, Sector, and Catalyst Agents.
V4 Mythic Architecture.
"""

import json
import asyncio
from datetime import datetime
from agents.base_agent import BaseAgent, AgentContext
from llm.client import get_shared_llm
from core.logger import get_logger

logger = get_logger(__name__)

class SentimentSpecialist(BaseAgent):
    def __init__(self):
        super().__init__(name="SentimentSpecialist", timeout_seconds=60)

    async def act(self, context: AgentContext) -> AgentContext:
        llm = get_shared_llm()
        ticker = context.ticker
        news = context.observations.get("news", [])
        
        system = "You are a Sentiment Analysis Specialist. Evaluate market psychology and retail/institutional sentiment."
        prompt = f"Analyze sentiment for {ticker} based on these headlines:\n" + \
                 "\n".join([f"- {n.get('headline')}" for n in news[:10]])
        
        res = await llm.complete(prompt, system=system, temperature=0.2)
        context.result = {"sentiment_analysis": res}
        return context

class FundamentalSpecialist(BaseAgent):
    def __init__(self):
        super().__init__(name="FundamentalSpecialist", timeout_seconds=60)

    async def act(self, context: AgentContext) -> AgentContext:
        llm = get_shared_llm()
        ticker = context.ticker
        knowledge = context.observations.get("knowledge_results", {})
        
        system = "You are a Fundamental Analysis Specialist. Focus on valuation, earnings quality, and growth prospects."
        prompt = f"Perform a fundamental deep-dive for {ticker}. Use context:\n{json.dumps(knowledge, default=str)[:2000]}"
        
        res = await llm.complete(prompt, system=system, temperature=0.1)
        context.result = {"fundamental_analysis": res}
        return context

class SectorSpecialist(BaseAgent):
    def __init__(self):
        super().__init__(name="SectorSpecialist", timeout_seconds=60)

    async def act(self, context: AgentContext) -> AgentContext:
        llm = get_shared_llm()
        ticker = context.ticker
        
        system = "You are a Sector & Industry Specialist. Evaluate relative performance and macro-sector rotation."
        prompt = f"Evaluate the sector positioning for {ticker} in the current market environment."
        
        res = await llm.complete(prompt, system=system, temperature=0.3)
        context.result = {"sector_analysis": res}
        return context

class CatalystSpecialist(BaseAgent):
    def __init__(self):
        super().__init__(name="CatalystSpecialist", timeout_seconds=60)

    async def act(self, context: AgentContext) -> AgentContext:
        llm = get_shared_llm()
        ticker = context.ticker
        news = context.observations.get("news", [])
        
        system = "You are a Catalyst Identification Specialist. Find upcoming events (earnings, FDA, lawsuits, mergers)."
        prompt = f"Identify key upcoming catalysts for {ticker} from news:\n" + \
                 "\n".join([f"- {n.get('headline')}" for n in news[:10]])
        
        res = await llm.complete(prompt, system=system, temperature=0.1)
        context.result = {"catalyst_events": res}
        return context
