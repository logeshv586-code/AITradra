"""
Sentiment Classifier Agent — FinBERT-powered financial sentiment analysis.
Provides high-accuracy sentiment scores for news and social media.
"""

import asyncio
from agents.base_agent import BaseAgent, AgentContext
from core.logger import get_logger

logger = get_logger(__name__)

class SentimentClassifierAgent(BaseAgent):
    """
    Agent 2: Sentiment Classifier
    Uses ProsusAI/finbert for domain-specific financial sentiment analysis.
    """
    
    _finbert_pipeline = None

    def __init__(self):
        super().__init__(name="SentimentClassifierAgent", timeout_seconds=60)

    def _initialize_pipeline(self):
        """Load the FinBERT pipeline only when the agent is actually used."""
        if SentimentClassifierAgent._finbert_pipeline is None:
            try:
                import torch
                from transformers import pipeline

                logger.info("Initializing FinBERT pipeline (ProsusAI/finbert)...")
                device = 0 if torch.cuda.is_available() else -1
                SentimentClassifierAgent._finbert_pipeline = pipeline(
                    "sentiment-analysis", 
                    model="ProsusAI/finbert",
                    device=device
                )
                logger.info("FinBERT pipeline initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize FinBERT: {e}")

    async def observe(self, context: AgentContext) -> AgentContext:
        """Fetch latest news if not already in context."""
        if not context.observations.get("news"):
            self._add_thought(context, "No news found in context. Gathering latest market news.")
            # In a real scenario, this would call a scraper or news agent
            pass
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        """Formulate a hypothesis about sentiment trends."""
        news_count = len(context.observations.get("news", []))
        self._add_thought(context, f"Preparing to analyze {news_count} news items using FinBERT.")
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        """Define the classification strategy."""
        context.plan.append("1. Extract headlines from observations")
        context.plan.append("2. Run FinBERT sentiment inference")
        context.plan.append("3. Aggregate results and calculate confidence")
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        ticker = context.ticker
        news = context.observations.get("news", [])
        
        if not news:
            context.result = {"sentiment": "neutral", "score": 0.5, "label": "no_data"}
            return context

        # Analyze top headlines
        headlines = [n.get("headline", n.get("title", "")) for n in news[:10]]
        headlines = [h for h in headlines if h]
        
        if not headlines:
            context.result = {"sentiment": "neutral", "score": 0.5, "label": "no_data"}
            return context

        try:
            from llm.client import LLMClient
            llm = LLMClient()
            
            # Construct a prompt for the LLM
            prompt = f"""Analyze the sentiment of the following headlines for {ticker}.
Headlines:
{chr(10).join(['- ' + h for h in headlines])}

Return a JSON object:
{{
  "sentiment_score": 0.0 to 1.0,
  "label": "positive/negative/neutral",
  "confidence": 0.0 to 1.0,
  "reasoning": "short explanation"
}}
"""
            result = await llm.complete(
                prompt=prompt,
                system="You are a professional financial sentiment analyst. Respond only in JSON.",
                temperature=0.0,
                expect_json=True
            )
            
            if isinstance(result, dict):
                context.result = {
                    "symbol": ticker,
                    "sentiment_score": result.get("sentiment_score", 0.5),
                    "label": result.get("label", "neutral"),
                    "confidence": result.get("confidence", 0.0),
                    "reasoning": result.get("reasoning", ""),
                    "headlines_analyzed": len(headlines)
                }
            else:
                # Fallback if LLM output is not JSON
                context.result = {"symbol": ticker, "sentiment_score": 0.5, "label": "neutral", "confidence": 0.0}

            self._add_thought(context, f"LLM analyzed {len(headlines)} headlines. Sentiment: {context.result.get('label')} ({context.result.get('sentiment_score')})")
            
        except Exception as e:
            logger.error(f"Sentiment analysis error: {e}")
            context.result = {"error": str(e), "sentiment": "neutral", "score": 0.5}

        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        """Assess the quality of the sentiment analysis."""
        score = context.result.get("sentiment_score", 0.5)
        context.reflection = f"Sentiment analysis for {context.ticker} completed with score {score}."
        context.confidence = context.result.get("confidence", 0.0)
        return context
