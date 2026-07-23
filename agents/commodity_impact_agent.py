"""
agents/commodity_impact_agent.py
────────────────────────────────────────────────────────────────────────────────
CommodityImpactAgent — AITradra's real-world causal-chain research engine.

The idea (the "tomato principle"):
  Real-world commodity events move stocks BEFORE the stock-specific news cycle
  catches up. If tomato/onion prices spike because a flood wiped out a crop,
  the companies that BUY tomatoes (QSR chains, FMCG food processors) get margin
  pressure, while upstream players (agri supply, cold chains, alternative
  producers) benefit. Same logic scales to crude oil vs airlines/paints,
  metals vs autos, sugar vs beverages, etc.

What this agent does on every scan:
  1. Reads recent headlines from news_articles (all tickers + generic feeds).
  2. Detects commodity mentions and the price DIRECTION (surge vs crash).
  3. Classifies the ROOT CAUSE: weather/disaster, supply shock, demand surge,
     policy (export bans / tariffs / duty changes), or logistics disruption.
  4. Builds the causal chain: event → commodity → affected tickers, tagging
     each ticker BULLISH (benefits) or BEARISH (hurt) with a plain-English
     reason ("input cost pressure: milk is a key input for Nestlé India").
  5. Generates trade suggestions with timing: action, entry style, hold
     horizon (derived from how long each cause type historically persists),
     and an explicit exit rule ("sell when commodity price normalizes").
  6. Optionally deep-dives with the LLM for a richer narrative; the
     rule-based result always stands on its own if no LLM is reachable.
  7. Persists events to commodity_events and per-ticker impacts to
     agent_insights (which auto-indexes into the RAG for chat retrieval).

No external API calls are required — it mines the news the platform already
collects, which keeps it free and offline-friendly.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from core.logger import get_logger

logger = get_logger(__name__)

AGENT_NAME = "CommodityImpactAgent"

# ─────────────────────────────────────────────────────────────────────────────
# Commodity knowledge map
#
# For each commodity:
#   keywords   — matched (case-insensitive, word-boundary) against headlines
#   producers  — tickers that BENEFIT when the commodity price RISES
#   consumers  — tickers HURT when the commodity price RISES (input cost)
# Each ticker entry: (symbol, why-it-is-exposed)
# Direction flips automatically when the commodity price FALLS.
# ─────────────────────────────────────────────────────────────────────────────

COMMODITY_MAP: dict[str, dict[str, Any]] = {
    "tomato": {
        "keywords": ["tomato", "tomatoes"],
        "producers": [
            ("KRBL.NS", "diversified agri processor benefits from agri inflation cycles"),
        ],
        "consumers": [
            ("JUBLFOOD.NS", "tomatoes are a core pizza input for Domino's India"),
            ("WESTLIFE.NS", "McDonald's India operator, fresh produce input costs"),
            ("DEVYANI.NS", "KFC/Pizza Hut operator, food input cost pressure"),
            ("NESTLEIND.NS", "ketchup and prepared foods use tomato paste"),
            ("HINDUNILVR.NS", "packaged foods portfolio exposed to vegetable inflation"),
        ],
    },
    "onion": {
        "keywords": ["onion", "onions"],
        "producers": [],
        "consumers": [
            ("JUBLFOOD.NS", "onion is a universal QSR input"),
            ("DEVYANI.NS", "QSR food input cost pressure"),
            ("WESTLIFE.NS", "QSR food input cost pressure"),
        ],
    },
    "potato": {
        "keywords": ["potato", "potatoes"],
        "producers": [],
        "consumers": [
            ("WESTLIFE.NS", "french fries are a core McDonald's menu item"),
            ("HINDUNILVR.NS", "packaged snacks input"),
            ("NESTLEIND.NS", "packaged foods input"),
        ],
    },
    "wheat": {
        "keywords": ["wheat", "atta", "flour price"],
        "producers": [
            ("ADM", "global grain trader benefits from grain price rallies"),
            ("BG", "Bunge — grain origination margins expand with volatility"),
        ],
        "consumers": [
            ("BRITANNIA.NS", "wheat flour is the primary biscuit input"),
            ("NESTLEIND.NS", "noodles and cereals use wheat"),
            ("ITC.NS", "Aashirvaad atta + biscuits, partial pass-through"),
            ("GIS", "General Mills cereal input costs"),
        ],
    },
    "rice": {
        "keywords": ["rice", "basmati", "paddy"],
        "producers": [
            ("KRBL.NS", "leading basmati exporter, realizations rise with rice prices"),
            ("LTFOODS.NS", "Daawat basmati exporter"),
        ],
        "consumers": [],
    },
    "sugar": {
        "keywords": ["sugar", "sugarcane"],
        "producers": [
            ("BALRAMCHIN.NS", "pure-play sugar miller"),
            ("EIDPARRY.NS", "sugar and nutraceuticals producer"),
            ("SHREERENUKA.NS", "sugar refiner with export leverage"),
        ],
        "consumers": [
            ("BRITANNIA.NS", "sugar is a key biscuit/cake input"),
            ("NESTLEIND.NS", "confectionery input costs"),
            ("VBL.NS", "Varun Beverages — sweetener input for PepsiCo bottling"),
            ("KO", "Coca-Cola sweetener input costs"),
        ],
    },
    "milk": {
        "keywords": ["milk", "dairy price", "dairy prices", "skimmed milk powder"],
        "producers": [
            ("HATSUN.NS", "dairy processor with procurement leverage"),
            ("DODLA.NS", "south-India dairy processor"),
        ],
        "consumers": [
            ("NESTLEIND.NS", "milk is the single largest input for Nestlé India"),
            ("BRITANNIA.NS", "dairy input for cheese and drinks"),
            ("HINDUNILVR.NS", "ice-cream and beverages dairy input"),
        ],
    },
    "edible_oil": {
        "keywords": ["palm oil", "edible oil", "sunflower oil", "soybean oil", "soyoil"],
        "producers": [
            ("PATANJALI.NS", "Patanjali Foods — edible oil refiner, inventory gains"),
        ],
        "consumers": [
            ("BRITANNIA.NS", "baking fats input"),
            ("NESTLEIND.NS", "processed foods input"),
            ("HINDUNILVR.NS", "soaps (palm derivatives) + foods input"),
            ("JUBLFOOD.NS", "frying oil input"),
        ],
    },
    "coffee": {
        "keywords": ["coffee", "arabica", "robusta"],
        "producers": [
            ("TATACONSUM.NS", "owns coffee plantations and brands"),
            ("CCLPRODUCTS.NS", "instant coffee manufacturer-exporter"),
        ],
        "consumers": [
            ("SBUX", "Starbucks green coffee input costs"),
        ],
    },
    "tea": {
        "keywords": ["tea price", "tea prices", "tea auction"],
        "producers": [
            ("TATACONSUM.NS", "Tata Tea brands with plantation exposure"),
        ],
        "consumers": [],
    },
    "cotton": {
        "keywords": ["cotton", "kapas"],
        "producers": [],
        "consumers": [
            ("PAGEIND.NS", "Jockey licensee — cotton yarn input"),
            ("ARVIND.NS", "denim and textiles cotton input"),
            ("NKE", "apparel cotton input costs"),
        ],
    },
    "crude_oil": {
        "keywords": ["crude oil", "crude price", "brent", "wti", "opec", "oil price", "oil prices"],
        "producers": [
            ("ONGC.NS", "upstream producer — realizations track crude"),
            ("OIL.NS", "upstream producer"),
            ("XOM", "integrated major, upstream leverage"),
            ("CVX", "integrated major, upstream leverage"),
        ],
        "consumers": [
            ("INDIGO.NS", "jet fuel is ~40% of airline operating cost"),
            ("DAL", "US airline jet fuel exposure"),
            ("UAL", "US airline jet fuel exposure"),
            ("ASIANPAINT.NS", "crude derivatives are key paint raw materials"),
            ("BERGEPAINT.NS", "crude-derivative input costs"),
            ("PIDILITIND.NS", "VAM/adhesive chemistry tracks crude"),
            ("IOC.NS", "refiner — marketing margins compress when crude spikes"),
        ],
    },
    "natural_gas": {
        "keywords": ["natural gas", "lng", "gas price", "gas prices", "henry hub"],
        "producers": [
            ("GAIL.NS", "gas transmission and trading"),
            ("ONGC.NS", "gas producer"),
        ],
        "consumers": [
            ("GUJGASLTD.NS", "city gas distributor — spot LNG input costs"),
            ("TATACHEM.NS", "chemicals energy input"),
            ("CHAMBLFERT.NS", "gas is the primary urea feedstock"),
        ],
    },
    "gold": {
        "keywords": ["gold price", "gold prices", "gold rally", "bullion", "gold hits", "gold surge"],
        "producers": [
            ("NEM", "gold miner — direct price leverage"),
            ("GOLD", "Barrick — gold miner"),
        ],
        "consumers": [
            ("TITAN.NS", "jewellery demand softens when gold spikes suddenly"),
            ("KALYANKJIL.NS", "jewellery retailer input costs"),
        ],
    },
    "copper": {
        "keywords": ["copper"],
        "producers": [
            ("HINDCOPPER.NS", "pure-play copper miner"),
            ("FCX", "Freeport — copper miner"),
        ],
        "consumers": [
            ("HAVELLS.NS", "cables and wires copper input"),
            ("POLYCAB.NS", "wires & cables — copper is the dominant input"),
            ("KEI.NS", "cables copper input"),
        ],
    },
    "steel": {
        "keywords": ["steel price", "steel prices", "iron ore", "hrc price", "steel demand"],
        "producers": [
            ("TATASTEEL.NS", "integrated steel producer"),
            ("JSWSTEEL.NS", "steel producer"),
            ("SAIL.NS", "state-owned steel producer"),
            ("NUE", "Nucor — US steel producer"),
        ],
        "consumers": [
            ("TATAMOTORS.NS", "auto body steel input"),
            ("MARUTI.NS", "auto steel input"),
            ("LT.NS", "construction steel input costs"),
        ],
    },
    "aluminium": {
        "keywords": ["aluminium", "aluminum", "alumina"],
        "producers": [
            ("HINDALCO.NS", "aluminium producer"),
            ("NATIONALUM.NS", "state-owned aluminium producer"),
            ("AA", "Alcoa — aluminium producer"),
        ],
        "consumers": [
            ("MARUTI.NS", "auto lightweighting input"),
        ],
    },
    "lithium": {
        "keywords": ["lithium"],
        "producers": [
            ("ALB", "Albemarle — lithium producer"),
            ("SQM", "lithium producer"),
        ],
        "consumers": [
            ("TSLA", "battery cell input costs"),
            ("TATAMOTORS.NS", "EV battery input costs"),
        ],
    },
    "fertilizer": {
        "keywords": ["fertilizer", "fertiliser", "urea", "dap price", "potash"],
        "producers": [
            ("CHAMBLFERT.NS", "urea manufacturer"),
            ("COROMANDEL.NS", "phosphatic fertilizer producer"),
            ("MOS", "Mosaic — potash/phosphate producer"),
            ("NTR", "Nutrien — global fertilizer major"),
        ],
        "consumers": [],
    },
    "corn": {
        "keywords": ["corn", "maize"],
        "producers": [
            ("ADM", "grain trading margins"),
            ("BG", "grain origination"),
        ],
        "consumers": [
            ("VENKEYS.NS", "poultry feed is corn-heavy"),
            ("TSN", "Tyson Foods animal feed costs"),
        ],
    },
    "rubber": {
        "keywords": ["rubber price", "rubber prices", "natural rubber"],
        "producers": [],
        "consumers": [
            ("MRF.NS", "tyre maker — rubber is the dominant input"),
            ("APOLLOTYRE.NS", "tyre rubber input"),
            ("CEATLTD.NS", "tyre rubber input"),
        ],
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Cause classification — WHY did the commodity move?
# Ordered by specificity: the first class with a hit wins.
# ─────────────────────────────────────────────────────────────────────────────

CAUSE_PATTERNS: list[tuple[str, list[str]]] = [
    ("weather_disaster", [
        "flood", "flooding", "drought", "monsoon deficit", "deficient monsoon",
        "poor monsoon", "delayed monsoon", "no rain", "rain deficit", "rainfall deficit",
        "heatwave", "heat wave", "cyclone", "hurricane", "typhoon", "hailstorm",
        "unseasonal rain", "untimely rain", "excess rain", "frost", "el nino",
        "el niño", "la nina", "la niña", "crop damage", "crop failure", "crop loss",
        "wildfire", "landslide", "earthquake",
    ]),
    ("policy", [
        "export ban", "import ban", "export duty", "import duty", "tariff",
        "sanction", "export restriction", "import restriction", "stock limit",
        "msp", "minimum support price", "subsidy", "windfall tax", "gst",
        "export curb", "import curb", "quota",
    ]),
    ("supply_shock", [
        "shortage", "supply crunch", "supply disruption", "supply cut",
        "production cut", "output cut", "opec cut", "opec+ cut", "mine closure",
        "plant shutdown", "strike", "lockout", "low arrivals", "supply squeeze",
        "inventory drawdown", "stockpile drop", "low stocks", "supply deficit",
        "bumper crop", "bumper harvest", "record harvest", "record output",
        "oversupply", "glut", "surplus",
    ]),
    ("logistics", [
        "port congestion", "shipping", "freight", "red sea", "suez",
        "container shortage", "supply chain disruption", "transport strike",
        "rail disruption", "trucker",
    ]),
    ("demand_surge", [
        "demand surge", "demand spike", "record demand", "strong demand",
        "festive demand", "festival demand", "wedding season", "restocking",
        "demand recovery", "china demand", "demand boom", "buying spree",
        "demand slump", "weak demand", "demand destruction",
    ]),
]

# Direction detection — did the commodity price go UP or DOWN?
DIRECTION_UP = [
    "surge", "surges", "surged", "soar", "soars", "soared", "spike", "spikes",
    "spiked", "jump", "jumps", "jumped", "rally", "rallies", "rallied", "rise",
    "rises", "risen", "rising", "climb", "climbs", "climbed", "hits record",
    "record high", "all-time high", "costlier", "shoots up", "shot up",
    "skyrocket", "skyrockets", "skyrocketed", "double", "doubles", "doubled",
    "gain", "gains", "gained", "higher", "up ", "expensive", "inflation",
]
DIRECTION_DOWN = [
    "fall", "falls", "fell", "fallen", "falling", "drop", "drops", "dropped",
    "plunge", "plunges", "plunged", "crash", "crashes", "crashed", "slump",
    "slumps", "slumped", "decline", "declines", "declined", "cools", "cooled",
    "eases", "eased", "easing", "cheaper", "tumble", "tumbles", "tumbled",
    "slide", "slides", "slid", "lower", "down ", "record low", "multi-month low",
]

# Causes that imply price direction even without an explicit price verb
CAUSE_IMPLIES_UP = {"weather_disaster", "supply_shock", "logistics"}
_SUPPLY_DOWN_HINTS = ["bumper", "record harvest", "record output", "oversupply", "glut", "surplus"]
_DEMAND_DOWN_HINTS = ["slump", "weak demand", "demand destruction"]

# How long each cause type historically keeps prices dislocated.
HOLD_HORIZON = {
    "weather_disaster": ("2-6 weeks", "sell when fresh supply arrives / next harvest news turns positive"),
    "supply_shock":     ("1-2 months", "sell when production/output normalizes or inventories rebuild"),
    "policy":           ("1-3 months", "sell on policy rollback or when markets fully price the change"),
    "logistics":        ("2-4 weeks", "sell when shipping routes/freight rates normalize"),
    "demand_surge":     ("2-8 weeks", "sell when demand indicators cool or seasonality ends"),
    "unknown":          ("2-4 weeks", "sell when the commodity price mean-reverts or news flow fades"),
}


@dataclass
class CommodityEvent:
    """A detected real-world commodity price event with its causal chain."""
    commodity:      str
    direction:      str                 # UP | DOWN
    cause_type:     str                 # weather_disaster | supply_shock | demand_surge | policy | logistics | unknown
    cause_detail:   str                 # human-readable why
    headlines:      list[dict] = field(default_factory=list)
    impacts:        list[dict] = field(default_factory=list)   # per-ticker causal impacts
    suggestions:    list[dict] = field(default_factory=list)   # actionable trade ideas
    confidence:     float = 0.5
    detected_at:    str = ""
    llm_narrative:  str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "commodity":     self.commodity,
            "direction":     self.direction,
            "cause_type":    self.cause_type,
            "cause_detail":  self.cause_detail,
            "headlines":     self.headlines,
            "impacts":       self.impacts,
            "suggestions":   self.suggestions,
            "confidence":    round(self.confidence, 2),
            "detected_at":   self.detected_at,
            "llm_narrative": self.llm_narrative,
        }


def _contains_keyword(text: str, keyword: str) -> bool:
    """Word-boundary keyword match so 'corn' doesn't hit 'corner'."""
    if " " in keyword:
        return keyword in text
    return re.search(rf"\b{re.escape(keyword)}\b", text) is not None


def detect_commodities(headline: str) -> list[str]:
    """Return all commodity keys mentioned in a headline."""
    text = headline.lower()
    hits = []
    for commodity, spec in COMMODITY_MAP.items():
        if any(_contains_keyword(text, kw) for kw in spec["keywords"]):
            hits.append(commodity)
    return hits


def detect_direction(headline: str) -> Optional[str]:
    """Detect the commodity price direction implied by a headline."""
    text = headline.lower()
    up = sum(1 for kw in DIRECTION_UP if kw in text)
    down = sum(1 for kw in DIRECTION_DOWN if kw in text)
    if up > down:
        return "UP"
    if down > up:
        return "DOWN"
    return None


def classify_cause(headline: str) -> tuple[str, str]:
    """Classify the root cause of a commodity move. Returns (cause_type, matched_phrase)."""
    text = headline.lower()
    for cause_type, patterns in CAUSE_PATTERNS:
        for pattern in patterns:
            if pattern in text:
                return cause_type, pattern
    return "unknown", ""


def _direction_from_cause(cause_type: str, matched_phrase: str) -> Optional[str]:
    """Infer price direction when the headline states a cause but no price verb."""
    if cause_type == "supply_shock":
        if any(h in matched_phrase for h in _SUPPLY_DOWN_HINTS):
            return "DOWN"
        return "UP"
    if cause_type in CAUSE_IMPLIES_UP:
        return "UP"
    if cause_type == "demand_surge":
        if any(h in matched_phrase for h in _DEMAND_DOWN_HINTS):
            return "DOWN"
        return "UP"
    return None


CAUSE_LABEL = {
    "weather_disaster": "weather / natural disaster",
    "supply_shock": "supply shock",
    "demand_surge": "demand shift",
    "policy": "government policy",
    "logistics": "logistics disruption",
    "unknown": "unclassified market move",
}


class CommodityImpactAgent:
    """
    Scans collected news for commodity price events, researches the root
    cause, maps the causal chain to listed equities, and produces trade
    suggestions with explicit entry/exit timing.
    """

    def __init__(self):
        self._last_scan: Optional[datetime] = None
        self._last_events: list[CommodityEvent] = []

    # ── Detection ────────────────────────────────────────────────────────────

    def detect_events(self, articles: list[dict]) -> list[CommodityEvent]:
        """
        Group commodity-tagged headlines into events.
        articles: [{headline, source, url, published_at, sentiment_score}, ...]
        """
        buckets: dict[str, list[dict]] = {}
        for art in articles:
            headline = art.get("headline") or ""
            if not headline:
                continue
            for commodity in detect_commodities(headline):
                buckets.setdefault(commodity, []).append(art)

        events: list[CommodityEvent] = []
        for commodity, arts in buckets.items():
            up_votes, down_votes = 0, 0
            cause_votes: dict[str, int] = {}
            cause_phrases: dict[str, str] = {}

            for art in arts:
                headline = art["headline"]
                cause_type, phrase = classify_cause(headline)
                direction = detect_direction(headline)
                if direction is None:
                    direction = _direction_from_cause(cause_type, phrase)
                if direction == "UP":
                    up_votes += 1
                elif direction == "DOWN":
                    down_votes += 1
                if cause_type != "unknown":
                    cause_votes[cause_type] = cause_votes.get(cause_type, 0) + 1
                    cause_phrases.setdefault(cause_type, phrase)

            if up_votes == 0 and down_votes == 0:
                continue  # commodity mentioned but no price action detected
            direction = "UP" if up_votes >= down_votes else "DOWN"

            if cause_votes:
                cause_type = max(cause_votes, key=cause_votes.get)
                phrase = cause_phrases[cause_type]
                cause_detail = (
                    f"{CAUSE_LABEL[cause_type]} — headlines cite '{phrase}'"
                )
            else:
                cause_type, cause_detail = "unknown", "no explicit cause found in headlines yet"

            # Confidence: corroboration + direction clarity + cause clarity
            corroboration = min(len(arts), 5) / 5.0                       # 0.2–1.0
            clarity = abs(up_votes - down_votes) / max(up_votes + down_votes, 1)
            cause_bonus = 0.15 if cause_type != "unknown" else 0.0
            confidence = min(0.95, 0.30 + 0.35 * corroboration + 0.20 * clarity + cause_bonus)

            event = CommodityEvent(
                commodity=commodity,
                direction=direction,
                cause_type=cause_type,
                cause_detail=cause_detail,
                headlines=[
                    {
                        "headline": a.get("headline"),
                        "source": a.get("source"),
                        "url": a.get("url"),
                        "published_at": a.get("published_at"),
                    }
                    for a in arts[:8]
                ],
                confidence=confidence,
                detected_at=datetime.now(timezone.utc).isoformat(),
            )
            event.impacts = self.build_impacts(event)
            event.suggestions = self.build_suggestions(event)
            events.append(event)

        events.sort(key=lambda e: e.confidence, reverse=True)
        return events

    # ── Causal chain ─────────────────────────────────────────────────────────

    def build_impacts(self, event: CommodityEvent) -> list[dict]:
        """Map a commodity event to per-ticker directional impacts."""
        spec = COMMODITY_MAP.get(event.commodity)
        if not spec:
            return []
        price_up = event.direction == "UP"
        impacts = []
        for symbol, reason in spec["producers"]:
            impacts.append({
                "ticker": symbol,
                "relation": "producer/beneficiary",
                "impact": "BULLISH" if price_up else "BEARISH",
                "reasoning": (
                    f"{event.commodity.replace('_', ' ')} prices {'rising' if price_up else 'falling'} "
                    f"({event.cause_detail}); {reason}"
                ),
            })
        for symbol, reason in spec["consumers"]:
            impacts.append({
                "ticker": symbol,
                "relation": "input-cost consumer",
                "impact": "BEARISH" if price_up else "BULLISH",
                "reasoning": (
                    f"{'Input cost pressure' if price_up else 'Input cost relief'}: {reason} "
                    f"({event.cause_detail})"
                ),
            })
        return impacts

    def build_suggestions(self, event: CommodityEvent) -> list[dict]:
        """Turn impacts into actionable suggestions with timing and exit rules."""
        horizon, exit_rule = HOLD_HORIZON.get(event.cause_type, HOLD_HORIZON["unknown"])
        suggestions = []
        for impact in event.impacts:
            bullish = impact["impact"] == "BULLISH"
            if event.confidence >= 0.60:
                action = "BUY" if bullish else "AVOID/SELL"
                entry = ("enter now — event is fresh and corroborated"
                         if bullish else "exit or hedge before margin impact is priced in")
            else:
                action = "WATCH"
                entry = "wait for confirmation (more headlines or a price gap)"
            suggestions.append({
                "ticker": impact["ticker"],
                "action": action,
                "direction": impact["impact"],
                "entry_timing": entry,
                "hold_horizon": horizon,
                "exit_rule": exit_rule,
                "confidence": round(event.confidence, 2),
                "why": impact["reasoning"],
                "trigger_event": (
                    f"{event.commodity.replace('_', ' ')} {event.direction} "
                    f"({CAUSE_LABEL[event.cause_type]})"
                ),
            })
        # Highest-conviction first, BUYs before WATCHes
        order = {"BUY": 0, "AVOID/SELL": 1, "WATCH": 2}
        suggestions.sort(key=lambda s: (order.get(s["action"], 3), -s["confidence"]))
        return suggestions

    # ── LLM enrichment (optional) ────────────────────────────────────────────

    async def enrich_with_llm(self, event: CommodityEvent) -> CommodityEvent:
        """Ask the LLM for a deeper narrative. Rule-based output survives any failure."""
        try:
            from llm.client import get_shared_llm
            llm = get_shared_llm()
            headlines = "\n".join(f"- {h['headline']}" for h in event.headlines[:6])
            prompt = (
                f"Commodity event detected: {event.commodity.replace('_', ' ')} prices moved "
                f"{event.direction}. Suspected cause: {event.cause_detail}.\n"
                f"Headlines:\n{headlines}\n\n"
                "In 3-4 sentences: explain the most likely root cause chain (e.g. flood → "
                "crop loss → supply shortage → price spike), how long the dislocation "
                "typically lasts, and which side of the trade (producers vs consumers) "
                "has the cleaner setup. Be specific and direct."
            )
            narrative = await llm.complete(
                prompt=prompt,
                system="You are a commodity supply-chain analyst for an institutional trading desk.",
                temperature=0.2,
                max_tokens=400,
                role="analysis",
            )
            if narrative and narrative.strip():
                event.llm_narrative = narrative.strip()
        except Exception as e:
            logger.debug(f"[{AGENT_NAME}] LLM enrichment skipped: {e}")
        return event

    # ── Full scan pipeline ───────────────────────────────────────────────────

    async def run_scan(self, lookback_hours: int = 48, use_llm: bool = True) -> list[dict]:
        """
        Full pipeline: read recent news → detect events → build causal chains
        → enrich with LLM → persist. Returns the event dicts.
        """
        from gateway.knowledge_store import knowledge_store

        started = datetime.now(timezone.utc)
        try:
            articles = knowledge_store.get_recent_headlines(hours=lookback_hours, limit=500)
        except Exception as e:
            logger.error(f"[{AGENT_NAME}] Could not read news: {e}")
            articles = []

        events = self.detect_events(articles)
        logger.info(f"[{AGENT_NAME}] Scanned {len(articles)} headlines → {len(events)} commodity events")

        for event in events:
            if use_llm:
                await self.enrich_with_llm(event)
            try:
                knowledge_store.store_commodity_event(event.to_dict())
            except Exception as e:
                logger.warning(f"[{AGENT_NAME}] Failed to persist event {event.commodity}: {e}")

            # Feed per-ticker impacts into agent_insights → consensus + RAG
            for impact in event.impacts:
                try:
                    knowledge_store.store_insight(
                        ticker=impact["ticker"],
                        agent_name=AGENT_NAME,
                        insight_type="commodity_impact",
                        content=json.dumps({
                            "commodity": event.commodity,
                            "direction": event.direction,
                            "cause": event.cause_detail,
                            "impact": impact["impact"],
                            "reasoning": impact["reasoning"],
                        }, ensure_ascii=False),
                        confidence=event.confidence,
                    )
                except Exception as e:
                    logger.debug(f"[{AGENT_NAME}] Insight store skipped: {e}")

        latency_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        try:
            knowledge_store.update_agent_health(
                AGENT_NAME, status="active", latency_ms=latency_ms,
                task=f"Commodity scan: {len(events)} events from {len(articles)} headlines",
            )
        except Exception:
            pass

        self._last_scan = started
        self._last_events = events
        return [e.to_dict() for e in events]

    def get_exposure(self, ticker: str) -> list[dict]:
        """Return a ticker's commodity exposures (static causal map)."""
        ticker = ticker.upper()
        exposures = []
        for commodity, spec in COMMODITY_MAP.items():
            for symbol, reason in spec["producers"]:
                if symbol == ticker:
                    exposures.append({
                        "commodity": commodity, "relation": "producer/beneficiary",
                        "effect_when_price_rises": "BULLISH", "reason": reason,
                    })
            for symbol, reason in spec["consumers"]:
                if symbol == ticker:
                    exposures.append({
                        "commodity": commodity, "relation": "input-cost consumer",
                        "effect_when_price_rises": "BEARISH", "reason": reason,
                    })
        return exposures

    def status(self) -> dict:
        return {
            "agent": AGENT_NAME,
            "last_scan": self._last_scan.isoformat() if self._last_scan else None,
            "events_in_last_scan": len(self._last_events),
            "commodities_tracked": len(COMMODITY_MAP),
            "tickers_mapped": len({
                sym for spec in COMMODITY_MAP.values()
                for sym, _ in spec["producers"] + spec["consumers"]
            }),
        }


# ── Module-level singleton ────────────────────────────────────────────────────

_agent_instance: Optional[CommodityImpactAgent] = None


def get_agent() -> CommodityImpactAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = CommodityImpactAgent()
    return _agent_instance
