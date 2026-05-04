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
        ticker = context.ticker

        self._add_thought(context, f"Analyzing technical data for {ticker} using LLM")

        # ─── Step 1: Get insights from other agents ─────────────────────────
        other_insights = await self._get_cross_agent_insights(ticker) if ticker else []
        insight_context = ""
        if other_insights:
            self._add_thought(context, f"Factoring in {len(other_insights)} insights from other agents")
            insight_context = "\nInsights from other specialists:\n" + "\n".join(
                [f"- {i['agent_name']} ({i['insight_type']}): {i['content'][:200]}" for i in other_insights[:5]]
            )

        # ─── Step 2: Prepare LLM Prompt ─────────────────────────────────────
        from llm.client import get_shared_llm
        llm = get_shared_llm()

        # Prepare a concise data summary for the LLM
        recent_bars = ohlcv[:10] if ohlcv else []
        data_summary = f"Recent Close Prices: {[b.get('close', b.get('c')) for b in recent_bars]}\n"
        data_summary += f"Current Price Change: {price_data.get('chg', 0)}%"

        prompt = f"""TICKER: {ticker}
{data_summary}
{insight_context}

Analyze the technical chart patterns and indicators for this asset.
Consider the insights from other agents if provided.

Return ONLY valid JSON:
{{
  "signal": "BULLISH|BEARISH|NEUTRAL",
  "confidence": 0.0-1.0,
  "patterns": ["identified pattern1", "pattern2"],
  "support_levels": [price1, price2],
  "resistance_levels": [price1, price2],
  "indicators": {{
    "trend": "UP|DOWN|SIDEWAYS",
    "momentum": "STRONG|WEAK|FADING",
    "volume_signal": "ACCUMULATION|DISTRIBUTION|NEUTRAL"
  }},
  "summary": "Technical analysis summary explaining the reasoning."
}}"""

        try:
            res = await llm.complete(prompt=prompt, system=self._build_skill_enhanced_prompt(self.system_prompt), expect_json=True, temperature=0.2)
            if isinstance(res, dict) and "signal" in res:
                context.result = res
            else:
                context.result = self._compute_technicals(ohlcv, price_data)
        except Exception:
            context.result = self._compute_technicals(ohlcv, price_data)

        context.actions_taken.append({"action": "technical_analysis_llm"})

        # Store insight in knowledge store
        try:
            from gateway.knowledge_store import knowledge_store
            if ticker and context.result:
                knowledge_store.store_insight(
                    ticker=ticker, agent_name=self.name,
                    insight_type="technical", content=str(context.result.get("summary", "")),
                    confidence=context.result.get("confidence", 0.5)
                )
        except Exception:
            pass

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
        """Compute full indicator suite: RSI, MACD, Bollinger, ADX, SMA, Volume."""
        from core.scoring import calculate_technical_score, calculate_atr

        if not ohlcv or len(ohlcv) < 3:
            pct = price_data.get("chg", price_data.get("pct_chg", 0))
            signal = "BULLISH" if pct and float(pct) > 1 else ("BEARISH" if pct and float(pct) < -1 else "NEUTRAL")
            return {
                "signal": signal, "confidence": 0.35, "score": 0.0,
                "patterns": ["Insufficient data"], "support_levels": [], "resistance_levels": [],
                "indicators": {"trend": "UNKNOWN", "momentum": "UNKNOWN", "volume_signal": "NEUTRAL"},
                "summary": f"Limited data. Current change: {pct}%"
            }

        closes = [bar.get("close", bar.get("c", 0)) for bar in ohlcv if bar.get("close") or bar.get("c")]
        highs = [bar.get("high", bar.get("h", 0)) for bar in ohlcv if bar.get("high") or bar.get("h")]
        lows = [bar.get("low", bar.get("l", 0)) for bar in ohlcv if bar.get("low") or bar.get("l")]
        volumes = [bar.get("volume", bar.get("v", 0)) for bar in ohlcv if bar.get("volume") or bar.get("v")]

        if not closes or len(closes) < 3:
            return {"signal": "NEUTRAL", "confidence": 0.3, "score": 0.0, "patterns": [],
                    "support_levels": [], "resistance_levels": [], "indicators": {},
                    "summary": "No price data"}

        # ─── RSI(14) ──────────────────────────────────────────
        rsi = 50.0
        if len(closes) >= 15:
            gains, losses = [], []
            for i in range(min(14, len(closes) - 1)):
                diff = closes[i] - closes[i + 1]  # Most recent first
                gains.append(max(diff, 0))
                losses.append(abs(min(diff, 0)))
            avg_gain = sum(gains) / len(gains) if gains else 0
            avg_loss = sum(losses) / len(losses) if losses else 0.001
            rs = avg_gain / avg_loss if avg_loss > 0 else 100
            rsi = 100 - (100 / (1 + rs))

        # ─── SMA20, SMA50 ──────────────────────────────────────
        sma20 = sum(closes[:20]) / min(20, len(closes)) if closes else 0
        sma50 = sum(closes[:50]) / min(50, len(closes)) if len(closes) >= 20 else sma20

        # ─── MACD(12,26,9) — simplified EMA approximation ─────
        macd_hist = 0.0
        if len(closes) >= 26:
            ema12 = sum(closes[:12]) / 12
            ema26 = sum(closes[:26]) / 26
            macd_line = ema12 - ema26
            signal_line = macd_line * 0.8  # Simplified
            macd_hist = macd_line - signal_line

        # ─── Bollinger %B ──────────────────────────────────────
        bb_pct_b = 0.5
        if len(closes) >= 20:
            bb_mean = sum(closes[:20]) / 20
            variance = sum((c - bb_mean) ** 2 for c in closes[:20]) / 20
            bb_std = variance ** 0.5
            if bb_std > 0:
                upper = bb_mean + 2 * bb_std
                lower = bb_mean - 2 * bb_std
                bb_pct_b = (closes[0] - lower) / (upper - lower) if upper != lower else 0.5

        # ─── ADX(14) — simplified ──────────────────────────────
        adx = 20.0
        if len(highs) >= 15 and len(lows) >= 15:
            plus_dm, minus_dm = 0, 0
            for i in range(min(14, len(highs) - 1)):
                up = highs[i] - highs[i + 1]
                down = lows[i + 1] - lows[i]
                if up > down and up > 0:
                    plus_dm += up
                if down > up and down > 0:
                    minus_dm += down
            total_dm = plus_dm + minus_dm
            if total_dm > 0:
                adx = min(50, (abs(plus_dm - minus_dm) / total_dm) * 50 + 10)

        # ─── Volume Ratio ──────────────────────────────────────
        avg_vol = sum(volumes) / len(volumes) if volumes else 0
        recent_vol = sum(volumes[:3]) / min(3, len(volumes)) if volumes else 0
        vol_ratio = recent_vol / avg_vol if avg_vol > 0 else 1.0
        vol_signal = "ACCUMULATION" if vol_ratio > 1.3 else ("DISTRIBUTION" if vol_ratio < 0.7 else "NEUTRAL")

        # ─── Composite Score via scoring.py ────────────────────
        score = calculate_technical_score(
            price=closes[0], sma20=sma20, sma50=sma50,
            rsi=rsi, macd_hist=macd_hist, adx=adx,
            bb_pct_b=bb_pct_b, vol_ratio=vol_ratio,
        )

        # ─── Signal from score ─────────────────────────────────
        if score > 0.15:
            signal = "BULLISH"
        elif score < -0.15:
            signal = "BEARISH"
        else:
            signal = "NEUTRAL"

        trend = "UP" if score > 0.1 else ("DOWN" if score < -0.1 else "SIDEWAYS")
        momentum = "STRONG" if abs(score) > 0.35 else ("WEAK" if abs(score) < 0.1 else "MODERATE")

        # ─── Support / Resistance ──────────────────────────────
        support = round(min(closes[:20]) if len(closes) >= 20 else min(closes), 2)
        resistance = round(max(closes[:20]) if len(closes) >= 20 else max(closes), 2)

        # ─── ATR for stop/target ───────────────────────────────
        atr = calculate_atr(ohlcv)
        confidence = round(min(0.4 + abs(score) * 0.8 + min(len(closes) / 100, 0.2), 0.92), 2)

        return {
            "signal": signal,
            "confidence": confidence,
            "score": score,
            "patterns": [f"{trend} trend, RSI={rsi:.0f}, ADX={adx:.0f}"],
            "support_levels": [support],
            "resistance_levels": [resistance],
            "indicators": {
                "trend": trend, "momentum": momentum, "volume_signal": vol_signal,
                "rsi": round(rsi, 1), "macd_hist": round(macd_hist, 4),
                "adx": round(adx, 1), "bb_pct_b": round(bb_pct_b, 3),
                "sma20": round(sma20, 2), "sma50": round(sma50, 2),
                "vol_ratio": round(vol_ratio, 2), "atr": round(atr, 4),
            },
            "summary": f"{signal} bias (score={score:+.3f}). RSI={rsi:.0f}, MACD hist={macd_hist:+.4f}, ADX={adx:.0f}. Volume: {vol_signal.lower()}."
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
        ticker = context.ticker

        self._add_thought(context, f"Assessing risk for {ticker} using LLM")

        # ─── Step 1: Get insights from other agents (especially Technical) ──
        other_insights = await self._get_cross_agent_insights(ticker) if ticker else []
        insight_context = ""
        if other_insights:
            self._add_thought(context, f"Factoring in {len(other_insights)} insights from other agents")
            insight_context = "\nInsights from other specialists:\n" + "\n".join(
                [f"- {i['agent_name']} ({i['insight_type']}): {i['content'][:200]}" for i in other_insights[:5]]
            )

        # ─── Step 2: Prepare LLM Prompt ─────────────────────────────────────
        from llm.client import get_shared_llm
        llm = get_shared_llm()

        prompt = f"""TICKER: {ticker}
Current Data: {str(price_data)[:500]}
{insight_context}

Perform a deep risk analysis. Assess volatility, potential drawdown, and stress scenarios.
Consider technical signals from other agents if available.

Return ONLY valid JSON:
{{
  "risk_level": "LOW|MEDIUM|HIGH|EXTREME",
  "confidence": 0.0-1.0,
  "var_pct": 2.5,
  "max_drawdown_pct": 15.0,
  "beta": 1.2,
  "volatility_regime": "LOW|NORMAL|HIGH|CRISIS",
  "stress_scenarios": [
    {{"scenario": "description", "impact_pct": -10.0}}
  ],
  "risk_flags": ["flag1", "flag2"],
  "summary": "Risk assessment reasoning summary."
}}"""

        try:
            res = await llm.complete(prompt=prompt, system=self._build_skill_enhanced_prompt(self.system_prompt), expect_json=True, temperature=0.1)
            if isinstance(res, dict) and "risk_level" in res:
                context.result = res
            else:
                context.result = self._compute_risk(ohlcv, price_data)
        except Exception:
            context.result = self._compute_risk(ohlcv, price_data)

        context.actions_taken.append({"action": "risk_analysis_llm"})

        # Store insight
        try:
            from gateway.knowledge_store import knowledge_store
            if ticker and context.result:
                knowledge_store.store_insight(
                    ticker=ticker, agent_name=self.name,
                    insight_type="risk", content=str(context.result.get("summary", "")),
                    confidence=context.result.get("confidence", 0.5)
                )
        except Exception:
            pass

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
        ticker = context.ticker

        self._add_thought(context, f"Analyzing macro context for {ticker} using LLM")

        # ─── Step 1: Get recent insights from other agents ───────────────────
        other_insights = await self._get_cross_agent_insights(ticker) if ticker else []
        insight_context = ""
        if other_insights:
            self._add_thought(context, f"Factoring in {len(other_insights)} insights from other agents")
            insight_context = "\nInsights from other specialists:\n" + "\n".join(
                [f"- {i['agent_name']} ({i['insight_type']}): {i['content'][:200]}" for i in other_insights[:5]]
            )

        # ─── Step 2: Prepare LLM Prompt ─────────────────────────────────────
        from llm.client import get_shared_llm
        llm = get_shared_llm()

        headlines = [n.get('headline', n.get('title', '')) for n in news[:8] if isinstance(n, dict)]
        
        prompt = f"""TICKER: {ticker}
Recent News: {headlines}
{insight_context}

Analyze the macro environment, news sentiment, and upcoming catalysts.
Incorporate insights from other agents to see how macro aligns with technicals/risk.

Return ONLY valid JSON:
{{
  "macro_outlook": "BULLISH|BEARISH|NEUTRAL",
  "confidence": 0.0-1.0,
  "sentiment_score": -1.0 to 1.0,
  "rate_impact": "POSITIVE|NEGATIVE|NEUTRAL",
  "earnings_signal": "BEAT|MISS|IN_LINE|NO_DATA",
  "sector_rotation": "INTO|OUT_OF|NEUTRAL",
  "catalysts": ["catalyst1", "catalyst2"],
  "news_summary": "Summary of news themes",
  "summary": "Macro assessment reasoning summary."
}}"""

        try:
            res = await llm.complete(prompt=prompt, system=self._build_skill_enhanced_prompt(self.system_prompt), expect_json=True, temperature=0.3)
            if isinstance(res, dict) and "macro_outlook" in res:
                context.result = res
            else:
                context.result = self._compute_macro(news, insights, price_data)
        except Exception:
            context.result = self._compute_macro(news, insights, price_data)

        context.actions_taken.append({"action": "macro_analysis_llm"})

        # Store insight
        try:
            from gateway.knowledge_store import knowledge_store
            if ticker and context.result:
                knowledge_store.store_insight(
                    ticker=ticker, agent_name=self.name,
                    insight_type="macro", content=str(context.result.get("summary", "")),
                    confidence=context.result.get("confidence", 0.5)
                )
        except Exception:
            pass

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
