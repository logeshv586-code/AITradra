"""
MACRO AGENT — Claude Flow Architecture (100% OSS)
Monitors macro-economic conditions using free open data (St Louis FED CSVs, World Bank).
No API keys required — parses publicly available CSVs and endpoints.

OBSERVE → Fetch VIX, yield curve, unemployment, inflation from public sources
THINK   → Assess macro headwinds/tailwinds for risk positioning
PLAN    → Determine macro regime (expansionary, recessionary, stagflation)
ACT     → Compute macro score and strategy implications
REFLECT → Confidence based on data freshness and signal clarity
"""

from agents.base_agent import BaseAgent, AgentContext
from core.logger import get_logger
import pandas as pd

logger = get_logger(__name__)


class MacroAgent(BaseAgent):
    """Assesses macro-economic environment using free public data sources."""

    # Free data endpoints (no API key needed)
    FRED_CSV_URLS = {
        "vix": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=VIXCLS",
        "fed_funds": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=FEDFUNDS",
        "unemployment": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=UNRATE",
        "cpi": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL",
        "yield_10y": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10",
        "yield_2y": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS2",
    }

    def __init__(self, memory=None):
        super().__init__("MacroAgent", memory)

    # ── OBSERVE ──────────────────────────────────────────────
    async def observe(self, context: AgentContext) -> AgentContext:
        context.observations["macro_sources"] = list(self.FRED_CSV_URLS.keys())
        self._add_thought(context, f"Will fetch {len(self.FRED_CSV_URLS)} macro indicators from FRED CSVs")
        return context

    # ── THINK ────────────────────────────────────────────────
    async def think(self, context: AgentContext) -> AgentContext:
        self._add_thought(context, "Key macro signals: VIX level, yield curve inversion, unemployment trend")
        self._add_thought(context, "High VIX (>25) = defensive. Inverted curve = recession risk. Rising unemployment = bearish")
        return context

    # ── PLAN ─────────────────────────────────────────────────
    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan = [
            "1. Download each FRED CSV (public, no key needed)",
            "2. Extract the latest value for each indicator",
            "3. Compute yield curve spread (10Y - 2Y)",
            "4. Classify macro regime: EXPANSIONARY / RECESSIONARY / STAGFLATION / NEUTRAL",
            "5. Generate risk multiplier and strategy recommendation",
        ]
        return context

    # ── ACT ──────────────────────────────────────────────────
    async def act(self, context: AgentContext) -> AgentContext:
        macro_data = {}

        for name, url in self.FRED_CSV_URLS.items():
            try:
                df = pd.read_csv(url, parse_dates=["DATE"])
                df.columns = ["date", "value"]
                df["value"] = pd.to_numeric(df["value"], errors="coerce")
                df = df.dropna()
                if not df.empty:
                    macro_data[name] = {
                        "latest_value": round(float(df["value"].iloc[-1]), 4),
                        "latest_date": df["date"].iloc[-1].isoformat(),
                        "3m_ago": round(float(df["value"].iloc[-60]), 4) if len(df) > 60 else None,
                    }
            except Exception as e:
                logger.warning(f"FRED CSV fetch failed for {name}: {e}")
                macro_data[name] = {"latest_value": None, "error": str(e)}

        # Yield Curve Spread
        y10 = macro_data.get("yield_10y", {}).get("latest_value")
        y2 = macro_data.get("yield_2y", {}).get("latest_value")
        yield_spread = round(y10 - y2, 4) if y10 is not None and y2 is not None else None
        inverted = yield_spread is not None and yield_spread < 0

        # VIX Level
        vix = macro_data.get("vix", {}).get("latest_value", 20)

        # Regime Classification
        regime, risk_mult, strategy = self._classify_regime(vix, yield_spread, inverted, macro_data)

        context.result = {
            "macro_indicators": macro_data,
            "yield_curve_spread": yield_spread,
            "yield_curve_inverted": inverted,
            "vix_level": vix,
            "macro_regime": regime,
            "risk_multiplier": risk_mult,
            "strategy_recommendation": strategy,
        }
        context.actions_taken.append({"action": "macro_scan", "indicators_fetched": len(macro_data)})
        return context

    # ── REFLECT ──────────────────────────────────────────────
    async def reflect(self, context: AgentContext) -> AgentContext:
        result = context.result or {}
        regime = result.get("macro_regime", "UNKNOWN")
        fetched = len([v for v in result.get("macro_indicators", {}).values() if v.get("latest_value") is not None])

        if fetched >= 4:
            context.reflection = f"Macro regime: {regime}. Data quality: {fetched}/6 indicators fetched."
            context.confidence = 0.8
        elif fetched >= 2:
            context.reflection = f"Partial data ({fetched}/6). Regime: {regime} — lower confidence."
            context.confidence = 0.5
        else:
            context.reflection = "Insufficient macro data. Cannot classify regime reliably."
            context.confidence = 0.2
        return context

    def _classify_regime(self, vix, yield_spread, inverted, macro_data):
        if vix and vix > 30:
            return "CRISIS", 0.25, "REDUCE_ALL — VIX extremely elevated"
        if vix and vix > 22:
            if inverted:
                return "RECESSIONARY", 0.4, "DEFENSIVE — high vol + inverted curve"
            return "HIGH_VOLATILITY", 0.5, "CAUTIOUS — reduce leverage, prefer puts"
        if inverted:
            return "LATE_CYCLE", 0.6, "SELECTIVE — curve inverted but vol calm. Be picky."
        if vix and vix < 15:
            return "EXPANSIONARY", 1.2, "AGGRESSIVE — low vol, add risk"
        return "NEUTRAL", 1.0, "BALANCED — normal sizing"

    def _add_thought(self, context: AgentContext, thought: str):
        context.thoughts.append(f"[{self.name}] {thought}")
