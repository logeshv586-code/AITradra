"""TrendAgent — Calculates technical indicators using pandas-ta."""

from agents.base_agent import BaseAgent, AgentContext
from core.logger import get_logger

logger = get_logger(__name__)


class TrendAgent(BaseAgent):
    """Calculates RSI, MACD, and Bollinger Bands based on OHLCV data."""

    def __init__(self, memory=None, improvement_engine=None):
        super().__init__("TrendAgent", memory, improvement_engine, timeout_seconds=10)

    async def observe(self, context: AgentContext) -> AgentContext:
        ohlcv = context.observations.get("ohlcv_data")
        if not ohlcv:
            context.errors.append("No OHLCV data provided in context observations.")
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        context.thoughts = [
            "Need to identify momentum and trend direction",
            "Will calculate 14-day RSI for overbought/oversold conditions",
            "Will calculate MACD (12,26,9) for trend reversals",
            "Will analyze price relative to Bollinger Bands"
        ]
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan = [
            "1. Extract close prices from OHLCV array",
            "2. Compute RSI",
            "3. Compute MACD histogram",
            "4. Compute Bollinger Bands penetration",
            "5. Synthesize composite trend score"
        ]
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        ohlcv = context.observations.get("ohlcv_data", [])
        if not ohlcv or len(ohlcv) < 30:
            context.errors.append("Insufficient data for technical analysis.")
            context.result = self._fallback_result()
            return context

        try:
            import pandas as pd
            import pandas_ta as ta

            df = pd.DataFrame(ohlcv)
            # Ensure columns are named correctly for pandas_ta
            df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"}, inplace=True)

            # Calculate indicators
            df.ta.rsi(length=14, append=True)
            df.ta.macd(fast=12, slow=26, signal=9, append=True)
            df.ta.bbands(length=20, std=2, append=True)

            latest = df.iloc[-1]
            prev = df.iloc[-2]

            # RSI State
            rsi = latest.get("RSI_14", 50)
            if pd.isna(rsi): rsi = 50.0

            # MACD State
            macd_line = latest.get("MACD_12_26_9", 0)
            macd_signal = latest.get("MACDs_12_26_9", 0)
            macd_hist = latest.get("MACDh_12_26_9", 0)
            prev_hist = prev.get("MACDh_12_26_9", 0)
            
            if pd.isna(macd_line): macd_line = 0.0
            if pd.isna(macd_signal): macd_signal = 0.0
            if pd.isna(macd_hist): macd_hist = 0.0
            if pd.isna(prev_hist): prev_hist = 0.0

            macd_cross = "None"
            if prev_hist < 0 and macd_hist > 0:
                macd_cross = "Bullish Cross"
            elif prev_hist > 0 and macd_hist < 0:
                macd_cross = "Bearish Cross"

            # Bollinger Bands State
            price = latest["Close"]
            bb_upper = latest.get("BBU_20_2.0", price * 1.05)
            bb_lower = latest.get("BBL_20_2.0", price * 0.95)
            
            if pd.isna(bb_upper): bb_upper = price * 1.05
            if pd.isna(bb_lower): bb_lower = price * 0.95

            bb_state = "Neutral"
            if price > bb_upper:
                bb_state = "Over Upper Band (Overbought)"
            elif price < bb_lower:
                bb_state = "Under Lower Band (Oversold)"

            context.result = {
                "rsi": round(float(rsi), 2),
                "rsi_state": "Overbought" if rsi > 70 else "Oversold" if rsi < 30 else "Neutral",
                "macd_line": round(float(macd_line), 4),
                "macd_signal": round(float(macd_signal), 4),
                "macd_histogram": round(float(macd_hist), 4),
                "macd_cross": macd_cross,
                "bb_state": bb_state,
                "momentum_score": self._calculate_momentum(rsi, macd_hist, price, bb_upper, bb_lower)
            }
            context.actions_taken.append({"action": "compute_ta", "indicators": ["RSI", "MACD", "BBANDS"]})

        except Exception as e:
            context.errors.append(f"TA computation failed: {str(e)}")
            context.result = self._fallback_result()

        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        res = context.result or {}
        m_score = res.get("momentum_score", 0)
        
        context.confidence = 0.9  # Math doesn't lie, high confidence in the output
        if m_score > 0.6:
            context.reflection = f"Strong bullish momentum alignment across indicators (RSI: {res.get('rsi')})."
        elif m_score < -0.6:
            context.reflection = f"Strong bearish momentum alignment. Proceed with caution."
        else:
            context.reflection = "Mixed technical signals, trend is indeterminate or consolidating."
            context.confidence = 0.7
            
        return context

    def _calculate_momentum(self, rsi, macd_hist, price, upper, lower) -> float:
        score = 0
        # RSI contribution
        if rsi < 30: score += 0.4  # Oversold buildup
        elif rsi > 70: score -= 0.4 # Overbought extreme
        elif rsi > 50: score += 0.1
        else: score -= 0.1
        
        # MACD contribution
        if macd_hist > 0: score += 0.3
        else: score -= 0.3
        
        # Normalize
        return max(-1.0, min(1.0, score))

    def _fallback_result(self) -> dict:
        return {
            "rsi": 50.0,
            "rsi_state": "Neutral",
            "macd_line": 0.0,
            "macd_signal": 0.0,
            "macd_histogram": 0.0,
            "macd_cross": "None",
            "bb_state": "Neutral",
            "momentum_score": 0.0
        }
