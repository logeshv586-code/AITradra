"""
Signal Aggregator Agent — Multi-signal fusion and consensus building.
Combines Technical, Sentiment, Volume, and Macro into a final trade verdict.
"""

from agents.base_agent import BaseAgent, AgentContext
from core.config import settings
from core.logger import get_logger
from core.scoring import calculate_consensus_verdict, calibrate_confidence

logger = get_logger(__name__)


def _ohlcv_get(bar: dict, key: str, default=0):
    """Retrieve a value from an OHLCV dict, tolerating both 'Close' and 'close' keys."""
    return bar.get(key, bar.get(key.lower(), bar.get(key[0].lower(), default)))

class SignalAggregatorAgent(BaseAgent):
    """
    Agent 5: Signal Aggregator
    Weighted vote — only trade if consensus > MIN_SIGNAL_CONFIDENCE.
    """
    
    def __init__(self):
        super().__init__(name="SignalAggregatorAgent", timeout_seconds=60)
        self.min_confidence = settings.MIN_SIGNAL_CONFIDENCE
        self.min_consensus_agents = settings.MIN_CONSENSUS_AGENTS

    async def observe(self, context: AgentContext) -> AgentContext:
        """Fetch historical price data and sentiment insights."""
        if not context.observations.get("history"):
            self._add_thought(context, "No price history found. Requesting market data.")
            # In a real scenario, this would call a data agent
            pass
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        """Formulate a consensus hypothesis."""
        self._add_thought(context, f"Aggregating signals for {context.ticker} from multiple sources.")
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        """Fusion strategy steps."""
        context.plan.append("1. Compute Technical indicators (RSI, MACD)")
        context.plan.append("2. Extract AI Sentiment score")
        context.plan.append("3. Analyze Volume anomalies")
        context.plan.append("4. Calculate Weighted Consensus verdict")
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        ticker = context.ticker
        ohlcv = context.observations.get("history", [])
        sentiment = context.observations.get("sentiment_result", {})
        spec_outputs = context.observations.get("specialist_outputs", {})
        
        # 1. Technical Signals - Try to reuse specialist output
        tech_spec = spec_outputs.get("technical", {})
        if isinstance(tech_spec, dict) and "score" in tech_spec:
             ta_score = tech_spec["score"]
             self._add_thought(context, "Using TechnicalSpecialist high-precision score.")
        else:
            # Fallback to simple TA logic
            ta_score = 0.5
            if ohlcv:
                try:
                    import pandas as pd
                    import pandas_ta  # noqa: F401 — registers .ta accessor on DataFrame

                    # Normalize keys to capitalized form expected by pandas_ta
                    normalized = [{
                        "Open": _ohlcv_get(bar, "Open"),
                        "High": _ohlcv_get(bar, "High"),
                        "Low": _ohlcv_get(bar, "Low"),
                        "Close": _ohlcv_get(bar, "Close"),
                        "Volume": _ohlcv_get(bar, "Volume"),
                    } for bar in ohlcv]
                    df = pd.DataFrame(normalized)
                    df.ta.rsi(append=True)
                    rsi = df.iloc[-1].get("RSI_14", 50)
                    ta_score = 0.8 if rsi < 30 else (0.2 if rsi > 70 else 0.5)
                except Exception as e:
                    logger.warning(f"TA fallback error: {e}")

        # 2. Sentiment Score
        news_score = sentiment.get("sentiment_score", 0.5)
        social_score = spec_outputs.get("sentiment", {}).get("sentiment_score", 0.5)
        
        # 3. Volume Anomaly
        vol_ratio = 1.0
        if ohlcv and len(ohlcv) > 20:
            try:
                volumes = [_ohlcv_get(bar, "Volume", 0) for bar in ohlcv]
                mean_vol = sum(volumes) / len(volumes) if volumes else 0
                last_vol = volumes[0] if volumes else 0  # Most recent first
                vol_ratio = last_vol / mean_vol if mean_vol > 0 else 1.0
            except Exception:
                vol_ratio = 1.0

        # 4. Multi-Signal Fusion via Shared Scoring
        consensus = calculate_consensus_verdict(
            tech_score=ta_score * 10 - 5, # Scale 0.5 center to 0.0 center
            news_sentiment=(news_score - 0.5) * 2,
            social_sentiment=(social_score - 0.5) * 2,
            vol_ratio=vol_ratio
        )
        
        confidence = calibrate_confidence(
            base_score=consensus["score"],
            data_points=len(ohlcv),
            headline_count=len(context.observations.get("news", [])),
            agreement_factor=1.1 if consensus["is_strong"] else 1.0
        )
        
        # 5. Determine Verdict
        verdict = consensus["direction"]
        if confidence < 50:
            verdict = "HOLD"

        last_price = _ohlcv_get(ohlcv[0], "Close", 0) if ohlcv else 0  # Index 0 = most recent (DESC order)
        
        context.result = {
            "symbol": ticker,
            "verdict": verdict,
            "final_score": consensus["score"],
            "confidence": confidence,
            "signals": {
                "technical": ta_score,
                "sentiment": news_score,
                "volume": round(vol_ratio, 2),
            },
            "entry_point": last_price,
            "target": round(last_price * (1 + abs(consensus["score"]) * 0.1), 2) if last_price else 0,
            "stop_loss": round(last_price * (1 - abs(consensus["score"]) * 0.05), 2) if last_price else 0
        }
        
        self._add_thought(context, f"Signal Fusion for {ticker}: Score {consensus['score']} → {verdict}")
        
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        """Evaluate the robustness of the consensus."""
        verdict = context.result.get("verdict", "HOLD")
        context.reflection = f"Consensus analysis for {context.ticker} yielded {verdict}."
        context.confidence = context.result.get("confidence", 0.0)
        return context
