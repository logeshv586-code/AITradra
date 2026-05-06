"""
AXIOM Extended Specialists — Structured Signal Output.
Every specialist returns: {signal, confidence, score, summary, key_factors}
"""

import json
from agents.base_agent import BaseAgent, AgentContext
from llm.client import get_shared_llm
from core.logger import get_logger

logger = get_logger(__name__)

SIGNAL_SCHEMA = """\nReturn ONLY valid JSON:
{
  "signal": "BULLISH|BEARISH|NEUTRAL",
  "confidence": 0.0-1.0,
  "score": -1.0 to +1.0,
  "summary": "One sentence",
  "key_factors": ["factor1", "factor2"]
}"""


class _SpecialistBase(BaseAgent):
    """Base with default observe/think/plan/reflect + cross-agent + insight storage."""

    async def observe(self, ctx: AgentContext) -> AgentContext:
        if ctx.ticker:
            insights = await self._get_cross_agent_insights(ctx.ticker, hours=24)
            if insights:
                ctx.observations["other_insights"] = insights
                self._add_thought(ctx, f"Found {len(insights)} peer insights")
        return ctx

    async def think(self, ctx: AgentContext) -> AgentContext:
        self._add_thought(ctx, f"{self.name}: Analyzing {ctx.ticker}")
        return ctx

    async def plan(self, ctx: AgentContext) -> AgentContext:
        ctx.plan = [f"1. LLM analysis", "2. Fallback if LLM fails", "3. Store insight"]
        return ctx

    async def reflect(self, ctx: AgentContext) -> AgentContext:
        r = ctx.result or {}
        conf = r.get("confidence", 0.3)
        ctx.confidence = conf if not ctx.errors else max(0.2, conf * 0.6)
        ctx.reflection = f"{self.name}: {r.get('signal','N/A')} ({ctx.confidence:.0%})"
        return ctx

    def _store_insight(self, ctx: AgentContext, insight_type: str):
        try:
            from gateway.knowledge_store import knowledge_store
            if ctx.ticker and ctx.result:
                knowledge_store.store_insight(
                    ticker=ctx.ticker, agent_name=self.name,
                    insight_type=insight_type,
                    content=str(ctx.result.get("summary", "")),
                    confidence=ctx.result.get("confidence", 0.5),
                )
        except Exception:
            pass

    def _build_insight_ctx(self, insights: list) -> str:
        if not insights:
            return ""
        lines = ["\nPeer agent insights:"]
        for i in insights[:5]:
            lines.append(f"- {i['agent_name']}: {i['content'][:120]}")
        return "\n".join(lines)

    def _neutral_fallback(self, reason: str = "Insufficient data") -> dict:
        return {"signal": "NEUTRAL", "confidence": 0.3, "score": 0.0,
                "summary": reason, "key_factors": [reason]}


class SentimentSpecialist(_SpecialistBase):
    def __init__(self):
        super().__init__(name="SentimentSpecialist", timeout_seconds=60)
        self.system_prompt = ("You are a Sentiment Analysis Specialist. "
            "Evaluate market psychology from news headlines." + SIGNAL_SCHEMA)

    async def act(self, ctx: AgentContext) -> AgentContext:
        news = ctx.observations.get("news") or ctx.metadata.get("news_data", [])
        headlines = [n.get("headline", n.get("title", "")) for n in news[:10] if isinstance(n, dict)]
        ic = self._build_insight_ctx(ctx.observations.get("other_insights", []))

        if not headlines:
            ctx.result = self._neutral_fallback("No news available")
            return ctx

        prompt = f"TICKER: {ctx.ticker}\nHeadlines:\n" + "\n".join(f"- {h}" for h in headlines) + ic
        try:
            llm = get_shared_llm()
            res = await llm.complete(prompt=prompt, system=self._build_skill_enhanced_prompt(self.system_prompt),
                                     expect_json=True, temperature=0.1, role="sentiment")
            if isinstance(res, dict) and "signal" in res:
                ctx.result = res
            else:
                ctx.result = self._keyword_fallback(headlines)
        except Exception:
            ctx.result = self._keyword_fallback(headlines)

        self._store_insight(ctx, "sentiment")
        return ctx

    def _keyword_fallback(self, headlines: list) -> dict:
        bull = ["surge","beat","record","growth","rally","upgrade","bullish","buy","soar","breakout"]
        bear = ["crash","miss","decline","cut","risk","warning","bearish","sell","plunge","downgrade"]
        scores = []
        for h in headlines:
            hl = h.lower()
            s = sum(0.15 for k in bull if k in hl) - sum(0.15 for k in bear if k in hl)
            scores.append(max(min(s, 1.0), -1.0))
        avg = sum(scores) / len(scores) if scores else 0
        signal = "BULLISH" if avg > 0.15 else ("BEARISH" if avg < -0.15 else "NEUTRAL")
        return {"signal": signal, "confidence": round(0.4 + min(len(headlines)*0.05, 0.3), 2),
                "score": round(avg, 3), "summary": f"Sentiment {signal} from {len(headlines)} headlines",
                "key_factors": [f"Avg sentiment: {avg:+.2f}"]}


class FundamentalSpecialist(_SpecialistBase):
    def __init__(self):
        super().__init__(name="FundamentalSpecialist", timeout_seconds=60)
        self.system_prompt = ("You are a Fundamental Analysis Specialist. "
            "Focus on valuation, earnings quality, growth." + SIGNAL_SCHEMA)

    async def act(self, ctx: AgentContext) -> AgentContext:
        knowledge = ctx.observations.get("knowledge_results") or ctx.metadata.get("knowledge_results", {})
        price = ctx.metadata.get("price_data", {})
        ic = self._build_insight_ctx(ctx.observations.get("other_insights", []))

        # Extract only the most trading-relevant fundamental fields
        fundamental_data = {
            "ticker": ctx.ticker,
            "price": price.get("px"),
            "change_pct": price.get("pct_chg"),
            "pe_ratio": price.get("pe_ratio") or price.get("pe"),
            "forward_pe": price.get("forward_pe"),
            "market_cap": price.get("market_cap") or price.get("mktcap"),
            "eps": price.get("eps"),
            "revenue_growth": price.get("revenue_growth"),
            "profit_margin": price.get("profit_margin"),
            "debt_equity": price.get("debt_equity"),
            "roe": price.get("roe"),
            "dividend_yield": price.get("dividend_yield"),
            "52w_high": price.get("week52_high"),
            "52w_low": price.get("week52_low"),
            "volume_ratio": price.get("volume_ratio"),
            "sector": price.get("sector"),
            "knowledge_context": str(knowledge)[:400] if knowledge else None,
        }
        # Remove None values for cleaner prompt
        fundamental_data = {k: v for k, v in fundamental_data.items() if v is not None}
        data_str = json.dumps(fundamental_data, default=str)
        prompt = f"TICKER: {ctx.ticker}\nFundamental Data: {data_str}{ic}"

        try:
            llm = get_shared_llm()
            res = await llm.complete(prompt=prompt, system=self._build_skill_enhanced_prompt(self.system_prompt),
                                     expect_json=True, temperature=0.1, role="analysis")
            if isinstance(res, dict) and "signal" in res:
                ctx.result = res
            else:
                ctx.result = self._fundamental_fallback(price)
        except Exception:
            ctx.result = self._fundamental_fallback(price)

        self._store_insight(ctx, "fundamental")
        return ctx

    def _fundamental_fallback(self, price: dict) -> dict:
        pe = price.get("pe_ratio") or price.get("pe", 0)
        mc = price.get("market_cap") or price.get("mktcap", 0)
        rev_growth = price.get("revenue_growth", 0)
        profit_margin = price.get("profit_margin", 0)

        score = 0.0
        factors = []

        if pe and float(pe) > 0:
            pe = float(pe)
            if pe < 15:
                score += 0.3
                factors.append(f"Low P/E ({pe:.1f}) — undervaluation")
            elif pe > 35:
                score -= 0.2
                factors.append(f"High P/E ({pe:.1f}) — overvaluation risk")
            else:
                factors.append(f"P/E {pe:.1f} — fair value range")

        if rev_growth and float(rev_growth) > 0.10:
            score += 0.2
            factors.append(f"Strong revenue growth ({float(rev_growth):.0%})")
        elif rev_growth and float(rev_growth) < 0:
            score -= 0.15
            factors.append(f"Revenue declining ({float(rev_growth):.0%})")

        if profit_margin and float(profit_margin) > 0.15:
            score += 0.1
            factors.append(f"Healthy profit margin ({float(profit_margin):.0%})")

        score = max(min(score, 1.0), -1.0)
        if score > 0.1:
            signal = "BULLISH"
        elif score < -0.1:
            signal = "BEARISH"
        else:
            signal = "NEUTRAL"

        return {
            "signal": signal,
            "confidence": round(0.4 + min(len(factors) * 0.1, 0.35), 2),
            "score": round(score, 3),
            "summary": f"{signal} fundamentals. " + ". ".join(factors[:2]) if factors else "Limited fundamental data",
            "key_factors": factors or ["No fundamental data available"],
        }


class SectorSpecialist(_SpecialistBase):
    def __init__(self):
        super().__init__(name="SectorSpecialist", timeout_seconds=60)
        self.system_prompt = ("You are a Sector & Industry Specialist. "
            "Evaluate relative performance and sector rotation." + SIGNAL_SCHEMA)

    async def act(self, ctx: AgentContext) -> AgentContext:
        ic = self._build_insight_ctx(ctx.observations.get("other_insights", []))
        prompt = f"TICKER: {ctx.ticker}\nEvaluate sector positioning.{ic}"
        try:
            llm = get_shared_llm()
            res = await llm.complete(prompt=prompt, system=self._build_skill_enhanced_prompt(self.system_prompt),
                                     expect_json=True, temperature=0.2, role="analysis")
            if isinstance(res, dict) and "signal" in res:
                ctx.result = res
            else:
                ctx.result = self._neutral_fallback("Sector analysis requires more context")
        except Exception:
            ctx.result = self._neutral_fallback("Sector analysis unavailable")

        self._store_insight(ctx, "sector")
        return ctx


class CatalystSpecialist(_SpecialistBase):
    def __init__(self):
        super().__init__(name="CatalystSpecialist", timeout_seconds=60)
        self.system_prompt = ("You are a Catalyst Identification Specialist. "
            "Find upcoming events: earnings, FDA, mergers, lawsuits." + SIGNAL_SCHEMA)

    async def act(self, ctx: AgentContext) -> AgentContext:
        news = ctx.observations.get("news") or ctx.metadata.get("news_data", [])
        headlines = [n.get("headline", n.get("title", "")) for n in news[:10] if isinstance(n, dict)]
        ic = self._build_insight_ctx(ctx.observations.get("other_insights", []))
        prompt = (f"TICKER: {ctx.ticker}\nHeadlines:\n" +
                  "\n".join(f"- {h}" for h in headlines) + ic)
        try:
            llm = get_shared_llm()
            res = await llm.complete(prompt=prompt, system=self._build_skill_enhanced_prompt(self.system_prompt),
                                     expect_json=True, temperature=0.1, role="analysis")
            if isinstance(res, dict) and "signal" in res:
                ctx.result = res
            else:
                ctx.result = self._catalyst_fallback(headlines)
        except Exception:
            ctx.result = self._catalyst_fallback(headlines)

        self._store_insight(ctx, "catalyst")
        return ctx

    def _catalyst_fallback(self, headlines: list) -> dict:
        catalyst_kw = ["earnings","fda","merger","acquisition","buyback","dividend","split","lawsuit","ipo"]
        found = []
        for h in headlines:
            hl = h.lower()
            for kw in catalyst_kw:
                if kw in hl:
                    found.append(kw)
                    break
        if found:
            return {"signal": "NEUTRAL", "confidence": 0.5, "score": 0.1,
                    "summary": f"Catalysts detected: {', '.join(set(found))}",
                    "key_factors": list(set(found))}
        return self._neutral_fallback("No catalysts identified")
