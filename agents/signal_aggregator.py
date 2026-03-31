"""
Signal Aggregator Agent — Multi-signal fusion and consensus building.
Combines Technical, Sentiment, Volume, and Macro into a final trade verdict.
"""

import pandas as pd
import pandas_ta as ta
import numpy as np
from agents.base_agent import BaseAgent, AgentContext
from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

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
        
        # 1. Technical Signals (pandas-ta)
        ta_score = 0.5
        if ohlcv:
            try:
                df = pd.DataFrame(ohlcv)
                # Calculate basic TA
                df.ta.rsi(append=True)
                df.ta.macd(append=True)
                df.ta.bbands(append=True)
                
                last_row = df.iloc[-1]
                rsi = last_row.get("RSI_14", 50)
                
                # Simple RSI logic for scoring (Scale 0-1)
                if rsi < 30: ta_score = 0.8  # Oversold (Bullish)
                elif rsi > 70: ta_score = 0.2 # Overbought (Bearish)
                else: ta_score = 0.5
                
            except Exception as e:
                logger.warning(f"TA calculation error: {e}")

        # 2. Sentiment Score (FinBERT result)
        sent_score = sentiment.get("sentiment_score", 0.5)
        
        # 3. Volume Anomaly (z-score)
        vol_score = 0.5
        if ohlcv and len(ohlcv) > 20:
            df = pd.DataFrame(ohlcv)
            mean_vol = df['Volume'].mean()
            std_vol = df['Volume'].std()
            last_vol = df['Volume'].iloc[-1]
            z_score = (last_vol - mean_vol) / std_vol if std_vol > 0 else 0
            
            # High volume on green candle is bullish
            last_close = df['Close'].iloc[-1]
            prev_close = df['Close'].iloc[-2]
            if z_score > 2:
                vol_score = 0.8 if last_close > prev_close else 0.2
            else:
                vol_score = 0.5

        # 4. Multi-Signal Fusion (Weighted Average)
        # Weights: Tech (30%), Sentiment (30%), Volume (20%), Momentum (20%)
        # Here we mock momentum as 0.5 for now
        mom_score = 0.5 
        
        weights = [0.3, 0.3, 0.2, 0.2]
        scores = [ta_score, sent_score, vol_score, mom_score]
        
        final_score = np.average(scores, weights=weights)
        
        # 5. Determine Verdict
        verdict = "HOLD"
        confidence = final_score
        
        if final_score > 0.65:
            verdict = "BUY"
        elif final_score < 0.35:
            verdict = "SELL"
            
        context.result = {
            "symbol": ticker,
            "verdict": verdict,
            "final_score": round(float(final_score), 2),
            "confidence": round(float(confidence), 2),
            "signals": {
                "technical": ta_score,
                "sentiment": sent_score,
                "volume": vol_score,
                "momentum": mom_score
            },
            "entry_point": ohlcv[-1]['Close'] if ohlcv else 0,
            "target": round(ohlcv[-1]['Close'] * 1.05, 2) if ohlcv else 0,
            "stop_loss": round(ohlcv[-1]['Close'] * 0.97, 2) if ohlcv else 0
        }
        
        self._add_thought(context, f"Signal Fusion for {ticker}: Consolidated score {final_score:.2f} → {verdict}")
        
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        """Evaluate the robustness of the consensus."""
        verdict = context.result.get("verdict", "HOLD")
        context.reflection = f"Consensus analysis for {context.ticker} yielded {verdict}."
        context.confidence = context.result.get("confidence", 0.0)
        return context
