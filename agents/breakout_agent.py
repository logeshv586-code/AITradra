"""
Breakout Momentum Agent — Detects volume-confirmed price breakouts (STRAT-002).

Breakout detection logic:
  1. Donchian Channel: N-period high/low as breakout levels
  2. Volume confirmation: breakout bar volume > 1.5× average
  3. ATR expansion: range expansion confirms momentum
  4. False breakout filter: close must be beyond level (not just wick)

Outputs canonical signal schema for SignalAggregator fusion.
"""

from agents.base_agent import BaseAgent, AgentContext
from core.scoring import calculate_atr
from core.logger import get_logger

logger = get_logger(__name__)


class BreakoutMomentumAgent(BaseAgent):
    """Detects price breakouts above/below key levels with volume confirmation."""

    def __init__(self, lookback: int = 20):
        super().__init__(name="BreakoutMomentumAgent", timeout_seconds=30)
        self.lookback = lookback  # Donchian channel period

    async def observe(self, ctx: AgentContext) -> AgentContext:
        ohlcv = ctx.metadata.get("ohlcv_data", [])
        ctx.observations["bar_count"] = len(ohlcv) if ohlcv else 0
        if ctx.ticker:
            insights = await self._get_cross_agent_insights(ctx.ticker, hours=24)
            if insights:
                ctx.observations["peer_insights"] = insights
                self._add_thought(ctx, f"Found {len(insights)} peer insights")
        return ctx

    async def think(self, ctx: AgentContext) -> AgentContext:
        bars = ctx.observations.get("bar_count", 0)
        if bars < self.lookback + 1:
            self._add_thought(ctx, f"Need {self.lookback+1} bars, have {bars}. Will return neutral.")
        else:
            self._add_thought(ctx, f"Scanning {bars} bars for breakout on {ctx.ticker}")
        return ctx

    async def plan(self, ctx: AgentContext) -> AgentContext:
        ctx.plan = [
            "1. Compute Donchian Channel (N-period high/low)",
            "2. Check if current close breaks above/below channel",
            "3. Validate with volume confirmation (>1.5x avg)",
            "4. Calculate ATR expansion for momentum strength",
            "5. Return structured signal",
        ]
        return ctx

    async def act(self, ctx: AgentContext) -> AgentContext:
        ohlcv = ctx.metadata.get("ohlcv_data", [])

        if not ohlcv or len(ohlcv) < self.lookback + 1:
            ctx.result = self._neutral("Insufficient data for breakout detection")
            return ctx

        # Extract price arrays (most recent first)
        closes, highs, lows, volumes = [], [], [], []
        for bar in ohlcv:
            c = bar.get("close", bar.get("Close", bar.get("c", 0)))
            h = bar.get("high", bar.get("High", bar.get("h", 0)))
            l = bar.get("low", bar.get("Low", bar.get("l", 0)))
            v = bar.get("volume", bar.get("Volume", bar.get("v", 0)))
            if c: closes.append(float(c))
            if h: highs.append(float(h))
            if l: lows.append(float(l))
            if v: volumes.append(float(v))

        if len(closes) < self.lookback + 1:
            ctx.result = self._neutral("Not enough valid bars")
            return ctx

        # ─── 1. Donchian Channel ───────────────────────────────
        # Channel is computed over lookback bars EXCLUDING the current bar
        channel_highs = highs[1:self.lookback + 1]
        channel_lows = lows[1:self.lookback + 1]
        donchian_high = max(channel_highs) if channel_highs else highs[0]
        donchian_low = min(channel_lows) if channel_lows else lows[0]
        donchian_mid = (donchian_high + donchian_low) / 2

        current_close = closes[0]
        current_high = highs[0]
        current_low = lows[0]

        # ─── 2. Breakout Detection ────────────────────────────
        bullish_breakout = current_close > donchian_high
        bearish_breakout = current_close < donchian_low

        # False breakout filter: check if close (not just wick) is beyond level
        # A wick-only breach is not a breakout
        if bullish_breakout and current_close < donchian_high * 1.001:
            bullish_breakout = False  # Marginal, likely noise
        if bearish_breakout and current_close > donchian_low * 0.999:
            bearish_breakout = False

        # ─── 3. Volume Confirmation ───────────────────────────
        avg_vol = sum(volumes[1:self.lookback + 1]) / self.lookback if len(volumes) > self.lookback else 1
        current_vol = volumes[0] if volumes else 0
        vol_ratio = current_vol / avg_vol if avg_vol > 0 else 1.0
        volume_confirmed = vol_ratio > 1.5

        # ─── 4. ATR Expansion (momentum strength) ─────────────
        atr = calculate_atr(ohlcv, period=14)
        current_range = current_high - current_low
        range_expansion = (current_range / atr) if atr > 0 else 1.0
        momentum_strong = range_expansion > 1.2

        # ─── 5. Score Calculation ──────────────────────────────
        if bullish_breakout:
            base_score = 0.4
            signal = "BULLISH"
            if volume_confirmed:
                base_score += 0.25
            if momentum_strong:
                base_score += 0.15
            # Proximity bonus: how far above the channel
            breakout_pct = (current_close - donchian_high) / donchian_high if donchian_high > 0 else 0
            base_score += min(breakout_pct * 5, 0.2)  # Max +0.2 for strong breakout

        elif bearish_breakout:
            base_score = -0.4
            signal = "BEARISH"
            if volume_confirmed:
                base_score -= 0.25
            if momentum_strong:
                base_score -= 0.15
            breakdown_pct = (donchian_low - current_close) / donchian_low if donchian_low > 0 else 0
            base_score -= min(breakdown_pct * 5, 0.2)

        else:
            # No breakout — check proximity to channel boundaries
            if donchian_high != donchian_low:
                position = (current_close - donchian_low) / (donchian_high - donchian_low)
            else:
                position = 0.5

            if position > 0.9:
                signal = "BULLISH"
                base_score = 0.15  # Near resistance, potential breakout setup
            elif position < 0.1:
                signal = "BEARISH"
                base_score = -0.15
            else:
                signal = "NEUTRAL"
                base_score = 0.0

        score = round(max(min(base_score, 1.0), -1.0), 3)

        # Confidence: higher for confirmed breakouts
        confidence = 0.35
        if bullish_breakout or bearish_breakout:
            confidence = 0.55
            if volume_confirmed:
                confidence += 0.15
            if momentum_strong:
                confidence += 0.10
        confidence = round(min(confidence, 0.92), 2)

        key_factors = []
        if bullish_breakout:
            key_factors.append(f"Bullish breakout above {donchian_high:.2f}")
        elif bearish_breakout:
            key_factors.append(f"Bearish breakdown below {donchian_low:.2f}")
        else:
            key_factors.append(f"Inside channel [{donchian_low:.2f} - {donchian_high:.2f}]")

        if volume_confirmed:
            key_factors.append(f"Volume confirmed ({vol_ratio:.1f}x avg)")
        if momentum_strong:
            key_factors.append(f"Range expansion ({range_expansion:.1f}x ATR)")

        ctx.result = {
            "signal": signal,
            "confidence": confidence,
            "score": score,
            "summary": f"{signal} — {key_factors[0]}. Vol={vol_ratio:.1f}x, ATR_exp={range_expansion:.1f}x",
            "key_factors": key_factors,
            "breakout_data": {
                "donchian_high": round(donchian_high, 2),
                "donchian_low": round(donchian_low, 2),
                "donchian_mid": round(donchian_mid, 2),
                "current_close": round(current_close, 2),
                "vol_ratio": round(vol_ratio, 2),
                "range_expansion": round(range_expansion, 2),
                "volume_confirmed": volume_confirmed,
                "momentum_strong": momentum_strong,
                "atr": round(atr, 4),
            },
        }

        # Store insight for cross-agent consumption
        try:
            from gateway.knowledge_store import knowledge_store
            if ctx.ticker:
                knowledge_store.store_insight(
                    ticker=ctx.ticker, agent_name=self.name,
                    insight_type="breakout",
                    content=f"{signal} | score={score:+.3f} | {key_factors[0]}",
                    confidence=confidence,
                )
        except Exception:
            pass

        self._add_thought(ctx, f"Breakout: {signal} (score={score:+.3f}, conf={confidence:.0%})")
        return ctx

    async def reflect(self, ctx: AgentContext) -> AgentContext:
        r = ctx.result or {}
        ctx.confidence = r.get("confidence", 0.3)
        signal = r.get("signal", "NEUTRAL")
        ctx.reflection = f"Breakout scan for {ctx.ticker}: {signal}"

        # Store prediction for self-improvement if directional
        if signal != "NEUTRAL" and ctx.ticker:
            try:
                from gateway.knowledge_store import knowledge_store
                knowledge_store.store_insight(
                    ticker=ctx.ticker, agent_name=self.name,
                    insight_type="prediction",
                    content=f"Breakout {signal} @ {r.get('breakout_data', {}).get('current_close', 0)}",
                    confidence=ctx.confidence,
                )
            except Exception:
                pass

        return ctx

    def _neutral(self, reason: str) -> dict:
        return {
            "signal": "NEUTRAL", "confidence": 0.3, "score": 0.0,
            "summary": reason, "key_factors": [reason],
            "breakout_data": {},
        }
