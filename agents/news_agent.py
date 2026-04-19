"""NewsAgent — Simplified wrapper for news aggregation."""

from agents.base_agent import BaseAgent, AgentContext
from core.logger import get_logger
import random

logger = get_logger(__name__)

class NewsAgent(BaseAgent):
    """Collects news catalysts and scores sentiment."""

    def __init__(self, memory=None, improvement_engine=None):
        super().__init__("NewsAgent", memory, improvement_engine, timeout_seconds=20)

    async def observe(self, context: AgentContext) -> AgentContext:
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan = ["Fetch news from knowledge store"]
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        try:
            from gateway.knowledge_store import knowledge_store
            recent_news = knowledge_store.get_news_for_ticker(context.ticker, limit=10, days=7)
            
            if not recent_news:
                # Fallback to general news
                recent_news = knowledge_store.get_news_for_ticker("", limit=10, days=7)

            context.result = {
                "ticker": context.ticker,
                "news_count": len(recent_news),
                "articles": [
                    {
                        "title": n.get("headline"),
                        "source": n.get("source"),
                        "sentiment": n.get("sentiment_score", 0.5)
                    } for n in recent_news
                ]
            }
        except Exception as e:
            logger.error(f"NewsAgent failed: {e}")
            context.result = {"articles": [], "news_count": 0}

        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        return context

def get_agent():
    return NewsAgent()
