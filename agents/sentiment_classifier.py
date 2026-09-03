"""Financial sentiment classifier backed by ProsusAI/finbert.

The previous implementation initialized a FinBERT pipeline but never used it;
headlines were instead sent to a general LLM. This module now performs actual
FinBERT inference. If the model cannot be loaded, the agent fails neutral with
zero confidence rather than substituting an unrelated model while still calling
the result "FinBERT".
"""

from __future__ import annotations

import asyncio
from typing import Any

from agents.base_agent import BaseAgent, AgentContext
from core.logger import get_logger

logger = get_logger(__name__)


class SentimentClassifierAgent(BaseAgent):
    """Domain-specific headline sentiment using ProsusAI/finbert."""

    _finbert_pipeline = None
    MODEL_ID = "ProsusAI/finbert"

    def __init__(self):
        super().__init__(name="SentimentClassifierAgent", timeout_seconds=60)

    @classmethod
    def _initialize_pipeline(cls) -> bool:
        """Load FinBERT lazily and return whether it is usable."""
        if cls._finbert_pipeline is not None:
            return True
        try:
            import torch
            from transformers import pipeline

            logger.info("Initializing FinBERT pipeline (%s)...", cls.MODEL_ID)
            device = 0 if torch.cuda.is_available() else -1
            cls._finbert_pipeline = pipeline(
                "sentiment-analysis",
                model=cls.MODEL_ID,
                tokenizer=cls.MODEL_ID,
                device=device,
                truncation=True,
            )
            logger.info("FinBERT pipeline initialized successfully")
            return True
        except Exception as exc:
            logger.error("Failed to initialize FinBERT: %s", exc)
            cls._finbert_pipeline = None
            return False

    @staticmethod
    def _neutral_result(ticker: str | None, *, label: str, error: str | None = None) -> dict[str, Any]:
        payload = {
            "symbol": ticker,
            "sentiment_score": 0.5,
            "score": 0.0,
            "label": label,
            "signal": "NEUTRAL",
            "confidence": 0.0,
            "headlines_analyzed": 0,
            "model": SentimentClassifierAgent.MODEL_ID,
            "model_verified": False,
            "execution_authority": False,
        }
        if error:
            payload["error"] = error
        return payload

    async def observe(self, context: AgentContext) -> AgentContext:
        if not context.observations.get("news"):
            self._add_thought(context, "No headlines available for FinBERT; sentiment will remain neutral")
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        news_count = len(context.observations.get("news", []))
        self._add_thought(context, f"Preparing FinBERT inference for {news_count} news items")
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan.extend(
            [
                "Extract and deduplicate recent headlines",
                "Run ProsusAI/finbert sentiment inference",
                "Aggregate signed FinBERT probabilities",
                "Fail neutral if the finance model is unavailable",
            ]
        )
        return context

    @classmethod
    def _infer(cls, headlines: list[str]) -> list[dict[str, Any]]:
        if not cls._initialize_pipeline() or cls._finbert_pipeline is None:
            raise RuntimeError("FinBERT model is unavailable")
        raw = cls._finbert_pipeline(headlines, batch_size=min(16, max(1, len(headlines))))
        if isinstance(raw, dict):
            raw = [raw]
        return [row for row in raw if isinstance(row, dict)]

    @staticmethod
    def _aggregate(rows: list[dict[str, Any]]) -> dict[str, float | str]:
        signed: list[float] = []
        certainties: list[float] = []
        for row in rows:
            label = str(row.get("label", "neutral")).lower()
            try:
                confidence = max(0.0, min(float(row.get("score", 0.0)), 1.0))
            except (TypeError, ValueError):
                confidence = 0.0
            if "positive" in label:
                value = confidence
            elif "negative" in label:
                value = -confidence
            else:
                value = 0.0
            signed.append(value)
            certainties.append(confidence)

        if not signed:
            return {"sentiment_score": 0.5, "directional_score": 0.0, "confidence": 0.0, "label": "neutral"}

        directional = sum(signed) / len(signed)
        sentiment_score = (directional + 1.0) / 2.0
        agreement = abs(directional)
        mean_certainty = sum(certainties) / len(certainties)
        sample_factor = min(1.0, len(rows) / 5.0)
        confidence = min(1.0, mean_certainty * (0.5 + 0.5 * agreement) * sample_factor)
        label = "positive" if directional > 0.10 else "negative" if directional < -0.10 else "neutral"
        return {
            "sentiment_score": round(sentiment_score, 6),
            "directional_score": round(directional, 6),
            "confidence": round(confidence, 6),
            "label": label,
        }

    async def act(self, context: AgentContext) -> AgentContext:
        ticker = context.ticker
        news = context.observations.get("news", []) or []
        headlines: list[str] = []
        seen: set[str] = set()
        for item in news[:20]:
            if not isinstance(item, dict):
                continue
            headline = str(item.get("headline", item.get("title", ""))).strip()
            key = headline.lower()
            if headline and key not in seen:
                seen.add(key)
                headlines.append(headline)
            if len(headlines) >= 10:
                break

        if not headlines:
            context.result = self._neutral_result(ticker, label="no_data")
            return context

        if not self._initialize_pipeline():
            context.result = self._neutral_result(
                ticker,
                label="model_unavailable",
                error="ProsusAI/finbert could not be loaded",
            )
            return context

        try:
            rows = await asyncio.wait_for(asyncio.to_thread(self._infer, headlines), timeout=55)
            aggregate = self._aggregate(rows)
            directional = float(aggregate["directional_score"])
            context.result = {
                "symbol": ticker,
                "sentiment_score": aggregate["sentiment_score"],
                "score": round(directional, 6),
                "directional_score": round(directional, 6),
                "label": aggregate["label"],
                "signal": "BULLISH" if directional > 0.10 else "BEARISH" if directional < -0.10 else "NEUTRAL",
                "confidence": aggregate["confidence"],
                "headlines_analyzed": len(rows),
                "model": self.MODEL_ID,
                "model_verified": True,
                "execution_authority": False,
            }
            self._add_thought(
                context,
                f"FinBERT analyzed {len(rows)} headlines: {aggregate['label']} score={directional:+.3f}",
            )
        except Exception as exc:
            logger.error("FinBERT sentiment analysis failed: %s", exc)
            context.result = self._neutral_result(
                ticker,
                label="inference_error",
                error=type(exc).__name__,
            )
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        result = context.result or {}
        context.reflection = (
            f"FinBERT sentiment for {context.ticker}: {result.get('label', 'neutral')} "
            f"({float(result.get('confidence', 0.0)):.0%} confidence)"
        )
        context.confidence = float(result.get("confidence", 0.0) or 0.0)
        return context
