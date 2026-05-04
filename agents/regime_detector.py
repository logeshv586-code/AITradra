"""
Regime Detector Agent — Market Regime Classification (ADAPT-001).

Classifies the current volatility regime into one of 6 states and provides
risk multipliers and strategy recommendations. Uses rolling volatility
windows (10, 21, 63 days) and trend+breadth analysis.

Regimes:
  BULL_TRENDING  — Low vol, rising prices, broad participation
  BULL_VOLATILE  — High vol, rising prices, narrow leadership
  BEAR_TRENDING  — High vol, falling prices, negative breadth
  BEAR_QUIET     — Low vol, falling prices, apathy
  RANGE_BOUND    — Low vol, sideways, mean reversion favorable
  CRISIS         — Extreme vol, correlation spike, liquidity dry-up
"""

from agents.base_agent import BaseAgent, AgentContext
from core.logger import get_logger

logger = get_logger(__name__)

# Regime → risk multiplier mapping
REGIME_PROFILES = {
    "BULL_TRENDING":  {"risk_mult": 1.20, "strategy": "trend_following", "description": "Low vol, rising trend"},
    "BULL_VOLATILE":  {"risk_mult": 0.70, "strategy": "momentum", "description": "High vol, rising with caution"},
    "BEAR_TRENDING":  {"risk_mult": 0.40, "strategy": "defensive", "description": "High vol, falling trend"},
    "BEAR_QUIET":     {"risk_mult": 0.60, "strategy": "mean_reversion", "description": "Low vol, drifting lower"},
    "RANGE_BOUND":    {"risk_mult": 0.90, "strategy": "mean_reversion", "description": "Sideways, low vol"},
    "CRISIS":         {"risk_mult": 0.20, "strategy": "cash", "description": "Extreme vol, preserve capital"},
}


class RegimeDetectorAgent(BaseAgent):
    """Classifies market regime using rolling volatility and trend analysis."""

    def __init__(self):
        super().__init__(name="RegimeDetectorAgent", timeout_seconds=30)

    async def observe(self, ctx: AgentContext) -> AgentContext:
        ctx.observations["has_ohlcv"] = bool(ctx.metadata.get("ohlcv_data"))
        return ctx

    async def think(self, ctx: AgentContext) -> AgentContext:
        self._add_thought(ctx, f"Classifying market regime for {ctx.ticker}")
        return ctx

    async def plan(self, ctx: AgentContext) -> AgentContext:
        ctx.plan = ["1. Compute rolling volatility", "2. Detect trend", "3. Classify regime"]
        return ctx

    async def act(self, ctx: AgentContext) -> AgentContext:
        ohlcv = ctx.metadata.get("ohlcv_data", [])

        if not ohlcv or len(ohlcv) < 21:
            ctx.result = {
                "signal": "NEUTRAL", "confidence": 0.3, "score": 0.0,
                "regime": "RANGE_BOUND",
                "risk_multiplier": 0.90,
                "strategy": "mean_reversion",
                "summary": "Insufficient data for regime detection",
                "key_factors": ["Need 21+ bars"],
            }
            return ctx

        # Extract close prices (most recent first)
        closes = []
        for bar in ohlcv:
            c = bar.get("close", bar.get("Close", bar.get("c", 0)))
            if c:
                closes.append(float(c))

        if len(closes) < 21:
            ctx.result = self._default_result()
            return ctx

        # ─── Rolling Returns ───────────────────────────────────
        returns = [(closes[i] - closes[i+1]) / closes[i+1]
                   for i in range(min(len(closes)-1, 63))]

        # ─── Volatility Windows ────────────────────────────────
        vol_10 = self._std(returns[:10]) * (252 ** 0.5) if len(returns) >= 10 else 0.15
        vol_21 = self._std(returns[:21]) * (252 ** 0.5) if len(returns) >= 21 else 0.15
        vol_63 = self._std(returns[:63]) * (252 ** 0.5) if len(returns) >= 63 else vol_21

        # ─── Trend Detection ──────────────────────────────────
        sma_short = sum(closes[:10]) / min(10, len(closes))
        sma_long = sum(closes[:50]) / min(50, len(closes))
        trend_pct = (sma_short - sma_long) / sma_long if sma_long > 0 else 0

        # ─── Regime Classification ─────────────────────────────
        is_trending_up = trend_pct > 0.02
        is_trending_down = trend_pct < -0.02
        is_high_vol = vol_21 > 0.25
        is_crisis_vol = vol_21 > 0.40
        vol_expanding = vol_10 > vol_21 * 1.2

        if is_crisis_vol or (is_high_vol and vol_expanding and is_trending_down):
            regime = "CRISIS"
        elif is_trending_up and not is_high_vol:
            regime = "BULL_TRENDING"
        elif is_trending_up and is_high_vol:
            regime = "BULL_VOLATILE"
        elif is_trending_down and is_high_vol:
            regime = "BEAR_TRENDING"
        elif is_trending_down and not is_high_vol:
            regime = "BEAR_QUIET"
        else:
            regime = "RANGE_BOUND"

        profile = REGIME_PROFILES[regime]

        # Score: bullish regimes positive, bearish negative
        if regime in ("BULL_TRENDING", "BULL_VOLATILE"):
            score = 0.3 if regime == "BULL_TRENDING" else 0.1
        elif regime in ("BEAR_TRENDING", "BEAR_QUIET", "CRISIS"):
            score = -0.4 if regime == "CRISIS" else (-0.3 if regime == "BEAR_TRENDING" else -0.1)
        else:
            score = 0.0

        signal = "BULLISH" if score > 0.05 else ("BEARISH" if score < -0.05 else "NEUTRAL")
        confidence = round(min(0.5 + abs(trend_pct) * 5 + min(len(closes)/100, 0.2), 0.90), 2)

        ctx.result = {
            "signal": signal,
            "confidence": confidence,
            "score": round(score, 3),
            "regime": regime,
            "risk_multiplier": profile["risk_mult"],
            "strategy": profile["strategy"],
            "volatility": {
                "vol_10d": round(vol_10, 4),
                "vol_21d": round(vol_21, 4),
                "vol_63d": round(vol_63, 4),
                "vol_expanding": vol_expanding,
            },
            "trend": {
                "direction": "UP" if is_trending_up else ("DOWN" if is_trending_down else "SIDEWAYS"),
                "strength_pct": round(trend_pct * 100, 2),
            },
            "summary": f"{regime}: {profile['description']}. Vol(21d)={vol_21:.1%}. "
                        f"Trend={trend_pct:+.1%}. Risk mult={profile['risk_mult']}×",
            "key_factors": [
                f"Regime: {regime}",
                f"21d vol: {vol_21:.1%}",
                f"Trend: {trend_pct:+.1%}",
                f"Strategy: {profile['strategy']}",
            ],
        }

        # Store insight
        try:
            from gateway.knowledge_store import knowledge_store
            if ctx.ticker:
                knowledge_store.store_insight(
                    ticker=ctx.ticker, agent_name=self.name,
                    insight_type="regime",
                    content=f"{regime} | vol={vol_21:.1%} | trend={trend_pct:+.1%}",
                    confidence=confidence,
                )
        except Exception:
            pass

        self._add_thought(ctx, f"Regime: {regime} (risk_mult={profile['risk_mult']})")
        return ctx

    async def reflect(self, ctx: AgentContext) -> AgentContext:
        r = ctx.result or {}
        ctx.reflection = f"Regime: {r.get('regime', 'UNKNOWN')}"
        ctx.confidence = r.get("confidence", 0.5)
        return ctx

    @staticmethod
    def _std(values: list) -> float:
        if not values or len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
        return variance ** 0.5

    def _default_result(self) -> dict:
        return {
            "signal": "NEUTRAL", "confidence": 0.3, "score": 0.0,
            "regime": "RANGE_BOUND", "risk_multiplier": 0.90,
            "strategy": "mean_reversion",
            "summary": "Insufficient data", "key_factors": [],
        }
