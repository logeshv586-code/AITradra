"""Specialist Agents — Focused sub-agents for the Mythic Orchestrator.

Each specialist receives a tightly scoped data slice and returns structured JSON.
Adapted from the Claude Agent System pattern using open-source local LLM.

Specialists:
- TechnicalSpecialist: OHLCV patterns, indicators, support/resistance
- RiskSpecialist: VaR, beta, drawdown, stress scenarios
- MacroSpecialist: News sentiment, earnings, rates, sector rotation
"""

import json
import asyncio
from agents.base_agent import BaseAgent, AgentContext
from core.logger import get_logger

logger = get_logger(__name__)


class TechnicalSpecialist(BaseAgent):
    """Specialist: Technical chart pattern analysis on OHLCV data."""

    def __init__(self, memory=None):
        super().__init__(name="TechnicalSpecialist", memory=memory, timeout_seconds=60)
        self.system_prompt = """You are a Technical Analysis Specialist Agent.
You ONLY analyze price action, chart patterns, and technical indicators.

Given OHLCV data, analyze and return ONLY valid JSON:
{
  "signal": "BULLISH|BEARISH|NEUTRAL",
  "confidence": 0.0-1.0,
  "patterns": ["pattern1", "pattern2"],
  "support_levels": [price1, price2],
  "resistance_levels": [price1, price2],
  "indicators": {
    "trend": "UP|DOWN|SIDEWAYS",
    "momentum": "STRONG|WEAK|FADING",
    "volume_signal": "ACCUMULATION|DISTRIBUTION|NEUTRAL"
  },
  "summary": "One-sentence technical summary"
}

Be precise with price levels. Use data-driven analysis only."""

    async def observe(self, context: AgentContext) -> AgentContext:
        context.observations["has_ohlcv"] = bool(context.metadata.get("ohlcv_data"))
        context.observations["has_price"] = bool(context.metadata.get("price_data"))
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        self._add_thought(context, "Analyzing price action and chart patterns")
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan = ["Analyze OHLCV trend", "Identify support/resistance", "Compute momentum", "Return structured JSON"]
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        meta = context.metadata
        ohlcv = meta.get("ohlcv_data", [])
        price_data = meta.get("price_data", {})

        # Compute basic technical signals from raw data
        tech_analysis = self._compute_technicals(ohlcv, price_data)

        # LLM synthesis for deeper pattern recognition
        prompt = f"""TICKER: {context.ticker}
CURRENT PRICE DATA: {json.dumps(price_data, default=str)[:500]}
RECENT OHLCV ({len(ohlcv)} bars): {json.dumps(ohlcv[:15], default=str)[:800]}
COMPUTED TECHNICALS: {json.dumps(tech_analysis, default=str)}

Analyze and return ONLY valid JSON with your technical analysis."""

        try:
            from llm.client import LLMClient
            llm = LLMClient()
            result = await llm.complete(prompt, system=self.system_prompt, temperature=0.15, max_tokens=800, expect_json=True)
            if isinstance(result, dict):
                context.result = result
            else:
                context.result = tech_analysis
        except Exception as e:
            logger.warning(f"TechnicalSpecialist LLM failed: {e}, using computed fallback")
            context.result = tech_analysis

        context.actions_taken.append({"action": "technical_analysis"})
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        if context.result and context.result.get("confidence", 0) > 0.6:
            context.reflection = "Technical analysis complete with good confidence."
            context.confidence = context.result.get("confidence", 0.6)
        else:
            context.reflection = "Technical analysis complete but data may be limited."
            context.confidence = 0.5
        return context

    def _compute_technicals(self, ohlcv: list, price_data: dict) -> dict:
        """Compute basic technical indicators from raw data."""
        if not ohlcv or len(ohlcv) < 3:
            pct = price_data.get("chg", price_data.get("pct_chg", 0))
            signal = "BULLISH" if pct and float(pct) > 1 else ("BEARISH" if pct and float(pct) < -1 else "NEUTRAL")
            return {
                "signal": signal, "confidence": 0.4,
                "patterns": ["Insufficient data"], "support_levels": [], "resistance_levels": [],
                "indicators": {"trend": "UNKNOWN", "momentum": "UNKNOWN", "volume_signal": "NEUTRAL"},
                "summary": f"Limited data. Current change: {pct}%"
            }

        closes = [bar.get("close", bar.get("c", 0)) for bar in ohlcv if bar.get("close") or bar.get("c")]
        volumes = [bar.get("volume", bar.get("v", 0)) for bar in ohlcv if bar.get("volume") or bar.get("v")]

        if not closes:
            return {"signal": "NEUTRAL", "confidence": 0.3, "patterns": [], "support_levels": [],
                    "resistance_levels": [], "indicators": {}, "summary": "No price data"}

        # Simple trend detection
        recent = closes[:5] if len(closes) >= 5 else closes
        older = closes[5:15] if len(closes) >= 15 else closes[len(recent):]

        avg_recent = sum(recent) / len(recent) if recent else 0
        avg_older = sum(older) / len(older) if older else avg_recent

        if avg_recent > avg_older * 1.02:
            trend, signal = "UP", "BULLISH"
        elif avg_recent < avg_older * 0.98:
            trend, signal = "DOWN", "BEARISH"
        else:
            trend, signal = "SIDEWAYS", "NEUTRAL"

        # Support / Resistance from recent extremes
        support = round(min(closes[:20]) if len(closes) >= 20 else min(closes), 2)
        resistance = round(max(closes[:20]) if len(closes) >= 20 else max(closes), 2)

        # Volume analysis
        avg_vol = sum(volumes) / len(volumes) if volumes else 0
        recent_vol = sum(volumes[:3]) / min(3, len(volumes)) if volumes else 0
        vol_signal = "ACCUMULATION" if recent_vol > avg_vol * 1.3 else (
            "DISTRIBUTION" if recent_vol < avg_vol * 0.7 else "NEUTRAL"
        )

        # Momentum
        if len(closes) >= 5:
            pct_5d = ((closes[0] - closes[4]) / closes[4] * 100) if closes[4] else 0
        else:
            pct_5d = 0
        momentum = "STRONG" if abs(pct_5d) > 5 else ("WEAK" if abs(pct_5d) < 1 else "FADING")

        return {
            "signal": signal,
            "confidence": round(0.5 + min(abs(avg_recent - avg_older) / (avg_older or 1) * 5, 0.4), 2),
            "patterns": [f"{trend} trend over {len(closes)} bars"],
            "support_levels": [support],
            "resistance_levels": [resistance],
            "indicators": {"trend": trend, "momentum": momentum, "volume_signal": vol_signal},
            "summary": f"{signal} bias. {trend} trend with {momentum.lower()} momentum. Volume: {vol_signal.lower()}."
        }


class RiskSpecialist(BaseAgent):
    """Specialist: Risk analysis — VaR, beta, drawdown, stress scenarios."""

    def __init__(self, memory=None):
        super().__init__(name="RiskSpecialist", memory=memory, timeout_seconds=60)
        self.system_prompt = """You are a Risk Analysis Specialist Agent.
You ONLY analyze risk metrics: volatility, drawdown, and stress scenarios.

Given price/portfolio data, return ONLY valid JSON:
{
  "risk_level": "LOW|MEDIUM|HIGH|EXTREME",
  "confidence": 0.0-1.0,
  "var_pct": 2.5,
  "max_drawdown_pct": 15.0,
  "beta": 1.2,
  "volatility_regime": "LOW|NORMAL|HIGH|CRISIS",
  "stress_scenarios": [
    {"scenario": "description", "impact_pct": -10.0}
  ],
  "risk_flags": ["flag1", "flag2"],
  "summary": "One-sentence risk assessment"
}"""

    async def observe(self, context: AgentContext) -> AgentContext:
        context.observations["has_price"] = bool(context.metadata.get("price_data"))
        context.observations["has_ohlcv"] = bool(context.metadata.get("ohlcv_data"))
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        self._add_thought(context, "Computing risk metrics and stress scenarios")
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan = ["Compute VaR and beta", "Analyze drawdown", "Generate stress scenarios"]
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        meta = context.metadata
        ohlcv = meta.get("ohlcv_data", [])
        price_data = meta.get("price_data", {})

        risk_analysis = self._compute_risk(ohlcv, price_data)

        prompt = f"""TICKER: {context.ticker}
PRICE DATA: {json.dumps(price_data, default=str)[:500]}
OHLCV BARS: {len(ohlcv)}
COMPUTED RISK METRICS: {json.dumps(risk_analysis, default=str)}

Provide a comprehensive risk analysis. Return ONLY valid JSON."""

        try:
            from llm.client import LLMClient
            llm = LLMClient()
            result = await llm.complete(prompt, system=self.system_prompt, temperature=0.15, max_tokens=800, expect_json=True)
            if isinstance(result, dict):
                context.result = result
            else:
                context.result = risk_analysis
        except Exception as e:
            logger.warning(f"RiskSpecialist LLM failed: {e}")
            context.result = risk_analysis

        context.actions_taken.append({"action": "risk_analysis"})
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        risk = context.result.get("risk_level", "MEDIUM") if context.result else "UNKNOWN"
        context.reflection = f"Risk assessment complete. Level: {risk}"
        context.confidence = context.result.get("confidence", 0.6) if context.result else 0.4
        return context

    def _compute_risk(self, ohlcv: list, price_data: dict) -> dict:
        """Compute risk metrics from raw data."""
        closes = [bar.get("close", bar.get("c", 0)) for bar in ohlcv if bar.get("close") or bar.get("c")]

        if not closes or len(closes) < 5:
            beta = price_data.get("risk", {}).get("beta", 1.0) if isinstance(price_data.get("risk"), dict) else 1.0
            return {
                "risk_level": "MEDIUM", "confidence": 0.4, "var_pct": 2.5,
                "max_drawdown_pct": 10.0, "beta": beta, "volatility_regime": "NORMAL",
                "stress_scenarios": [{"scenario": "Market correction -10%", "impact_pct": round(-10 * beta, 1)}],
                "risk_flags": ["Limited historical data"], "summary": "Insufficient data for thorough risk analysis."
            }

        # Daily returns
        returns = [(closes[i] - closes[i + 1]) / closes[i + 1] * 100 for i in range(min(len(closes) - 1, 50))]
        if not returns:
            return {"risk_level": "MEDIUM", "confidence": 0.3, "var_pct": 2.5,
                    "max_drawdown_pct": 10.0, "beta": 1.0, "volatility_regime": "NORMAL",
                    "stress_scenarios": [], "risk_flags": [], "summary": "Minimal data."}

        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std_dev = variance ** 0.5

        # VaR (95% — approximate as 1.65 * std_dev)
        var_95 = round(1.65 * std_dev, 2)

        # Max drawdown
        peak = closes[0]
        max_dd = 0
        for c in closes:
            if c > peak:
                peak = c
            dd = (peak - c) / peak * 100
            if dd > max_dd:
                max_dd = dd

        # Volatility regime
        if std_dev > 4:
            vol_regime, risk_level = "CRISIS", "EXTREME"
        elif std_dev > 2.5:
            vol_regime, risk_level = "HIGH", "HIGH"
        elif std_dev > 1.2:
            vol_regime, risk_level = "NORMAL", "MEDIUM"
        else:
            vol_regime, risk_level = "LOW", "LOW"

        beta = price_data.get("risk", {}).get("beta", 1.0) if isinstance(price_data.get("risk"), dict) else 1.0

        return {
            "risk_level": risk_level,
            "confidence": round(min(0.5 + len(returns) * 0.01, 0.9), 2),
            "var_pct": var_95,
            "max_drawdown_pct": round(max_dd, 2),
            "beta": round(float(beta), 2),
            "volatility_regime": vol_regime,
            "stress_scenarios": [
                {"scenario": "Market crash -20%", "impact_pct": round(-20 * float(beta), 1)},
                {"scenario": "Sector rotation -10%", "impact_pct": round(-10 * float(beta) * 0.8, 1)},
                {"scenario": "Rate hike shock", "impact_pct": round(-5 * float(beta), 1)},
            ],
            "risk_flags": [f"{'High' if std_dev > 2 else 'Normal'} volatility ({std_dev:.1f}% daily std)"],
            "summary": f"{risk_level} risk. VaR(95%): {var_95}%. Max drawdown: {max_dd:.1f}%. Regime: {vol_regime}."
        }


class MacroSpecialist(BaseAgent):
    """Specialist: Macro analysis — news sentiment, earnings, rates, sector rotation."""

    def __init__(self, memory=None):
        super().__init__(name="MacroSpecialist", memory=memory, timeout_seconds=60)
        self.system_prompt = """You are a Macro Analysis Specialist Agent.
You ONLY analyze macro factors: news sentiment, earnings, rates, and sector trends.

Given news data and market context, return ONLY valid JSON:
{
  "macro_outlook": "BULLISH|BEARISH|NEUTRAL",
  "confidence": 0.0-1.0,
  "sentiment_score": -1.0 to 1.0,
  "rate_impact": "POSITIVE|NEGATIVE|NEUTRAL",
  "earnings_signal": "BEAT|MISS|IN_LINE|NO_DATA",
  "sector_rotation": "INTO|OUT_OF|NEUTRAL",
  "catalysts": ["catalyst1", "catalyst2"],
  "news_summary": "Key news themes in one sentence",
  "summary": "One-sentence macro assessment"
}"""

    async def observe(self, context: AgentContext) -> AgentContext:
        context.observations["has_news"] = bool(context.metadata.get("news_data"))
        context.observations["has_insights"] = bool(context.metadata.get("insights_data"))
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        self._add_thought(context, "Analyzing macro environment and news sentiment")
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan = ["Analyze news sentiment", "Assess macro factors", "Identify catalysts"]
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        meta = context.metadata
        news = meta.get("news_data", [])
        insights = meta.get("insights_data", [])
        price_data = meta.get("price_data", {})

        macro_analysis = self._compute_macro(news, insights, price_data)

        prompt = f"""TICKER: {context.ticker}
RECENT NEWS ({len(news)} articles): {json.dumps(news[:5], default=str)[:800]}
PRIOR INSIGHTS: {json.dumps(insights[:3], default=str)[:400]}
COMPUTED MACRO: {json.dumps(macro_analysis, default=str)}

Provide macro analysis. Return ONLY valid JSON."""

        try:
            from llm.client import LLMClient
            llm = LLMClient()
            result = await llm.complete(prompt, system=self.system_prompt, temperature=0.2, max_tokens=800, expect_json=True)
            if isinstance(result, dict):
                context.result = result
            else:
                context.result = macro_analysis
        except Exception as e:
            logger.warning(f"MacroSpecialist LLM failed: {e}")
            context.result = macro_analysis

        context.actions_taken.append({"action": "macro_analysis"})
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        outlook = context.result.get("macro_outlook", "NEUTRAL") if context.result else "UNKNOWN"
        context.reflection = f"Macro analysis complete. Outlook: {outlook}"
        context.confidence = context.result.get("confidence", 0.5) if context.result else 0.4
        return context

    def _compute_macro(self, news: list, insights: list, price_data: dict) -> dict:
        """Compute macro signals from news and insights."""
        bullish_kw = ["surge", "high", "beat", "record", "growth", "rally", "upgrade", "outperform", "bullish", "buy"]
        bearish_kw = ["fall", "drop", "miss", "decline", "cut", "risk", "warning", "underperform", "bearish", "sell"]

        sentiment_scores = []
        catalysts = []

        for article in news[:10]:
            if not isinstance(article, dict):
                continue
            headline = (article.get("headline", "") or article.get("title", "") or article.get("txt", "")).lower()
            if not headline:
                continue

            score = 0
            for kw in bullish_kw:
                if kw in headline:
                    score += 0.15
            for kw in bearish_kw:
                if kw in headline:
                    score -= 0.15
            sentiment_scores.append(max(min(score, 1.0), -1.0))

            if abs(score) > 0.1:
                catalysts.append(article.get("headline", article.get("title", article.get("txt", "")))[:80])

        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0

        if avg_sentiment > 0.15:
            outlook = "BULLISH"
        elif avg_sentiment < -0.15:
            outlook = "BEARISH"
        else:
            outlook = "NEUTRAL"

        earnings_signal = "NO_DATA"
        for article in news[:10]:
            if not isinstance(article, dict):
                continue
            headline = (article.get("headline", "") or article.get("txt", "")).lower()
            if "earnings" in headline or "revenue" in headline:
                if any(w in headline for w in ["beat", "exceeded", "strong"]):
                    earnings_signal = "BEAT"
                elif any(w in headline for w in ["miss", "below", "weak"]):
                    earnings_signal = "MISS"
                else:
                    earnings_signal = "IN_LINE"
                break

        return {
            "macro_outlook": outlook,
            "confidence": round(0.4 + min(len(news) * 0.05, 0.4), 2),
            "sentiment_score": round(avg_sentiment, 3),
            "rate_impact": "NEUTRAL",
            "earnings_signal": earnings_signal,
            "sector_rotation": "NEUTRAL",
            "catalysts": catalysts[:5] or ["No strong catalysts identified"],
            "news_summary": f"{len(news)} articles analyzed. Average sentiment: {avg_sentiment:.2f}",
            "summary": f"{outlook} macro outlook. Sentiment: {avg_sentiment:+.2f}. {earnings_signal} earnings signal."
        }
