"""Research Council V2 — point-in-time, provenance-weighted adversarial research.

Architectural ideas are informed by TradingAgents, Qlib, Freqtrade and
NautilusTrader, but this is original AITradra integration code. The council is
strictly advisory: it cannot place orders, enable live trading or bypass Risk
Manager, strategy validation, empirical precision validation or broker auth.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)
AGENT_NAME = "ResearchCouncilV2"
EXPECTED_CATEGORIES = {
    "technical", "fundamental", "macro", "sentiment", "price", "risk"
}

_BULL_PATTERNS = (
    r"\bSTRONG\s+BUY\b", r"\bBULLISH\b", r"\bBUY\b", r"\bLONG\b",
    r"\bUPGRADE(?:D)?\b", r"\bOUTPERFORM\b",
)
_BEAR_PATTERNS = (
    r"\bSTRONG\s+SELL\b", r"\bBEARISH\b", r"\bSELL\b", r"\bSHORT\b",
    r"\bDOWNGRADE(?:D)?\b", r"\bUNDERPERFORM\b", r"\bAVOID\b",
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if value in {None, ""}:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _clamp(value: Any, low: float = 0.0, high: float = 1.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = low
    return max(low, min(high, number))


def _normalize_confidence(value: Any, default: float = 0.5) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return _clamp(number / 100.0 if number > 1.0 else number)


def _direction_from_text(text: str) -> str:
    upper = str(text or "").upper()
    bull = any(re.search(pattern, upper) for pattern in _BULL_PATTERNS)
    bear = any(re.search(pattern, upper) for pattern in _BEAR_PATTERNS)
    if bull and not bear:
        return "BULLISH"
    if bear and not bull:
        return "BEARISH"
    return "NEUTRAL"


def _category_for(agent_name: str, insight_type: str) -> str:
    value = f"{agent_name} {insight_type}".lower()
    if any(word in value for word in ("technical", "trend", "indicator", "chart")):
        return "technical"
    if any(word in value for word in ("fundamental", "valuation", "earnings", "financial")):
        return "fundamental"
    if any(word in value for word in ("macro", "econom", "rates", "commodity")):
        return "macro"
    if any(word in value for word in ("sentiment", "social", "news", "catalyst")):
        return "sentiment"
    if any(word in value for word in ("risk", "var", "drawdown", "volatility")):
        return "risk"
    if any(word in value for word in ("sector", "industry")):
        return "sector"
    return "other"


def _freshness_score(observed_at: datetime, as_of: datetime, half_life_hours: float) -> float:
    age_hours = max(0.0, (as_of - observed_at).total_seconds() / 3600.0)
    if half_life_hours <= 0:
        return 1.0
    return round(
        max(0.05, math.exp(-math.log(2.0) * age_hours / half_life_hours)), 6
    )


def _json_urls(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if str(v).startswith(("http://", "https://"))]
    try:
        parsed = json.loads(str(value))
        if isinstance(parsed, list):
            return [
                str(v) for v in parsed
                if str(v).startswith(("http://", "https://"))
            ]
    except Exception:
        pass
    text = str(value)
    return [text] if text.startswith(("http://", "https://")) else []


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    ticker: str
    category: str
    direction: str
    text: str
    source: str
    source_type: str
    observed_at: str
    url: str = ""
    confidence: float = 0.5
    relevance: float = 0.5
    provenance_score: float = 0.5
    freshness_score: float = 0.5
    weight: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ResearchDecision:
    ticker: str
    as_of: str
    rating: str
    verdict: str
    confidence: int
    directional_score: float
    evidence_quality: float
    contradiction_score: float
    coverage_score: float
    provenance_score: float
    freshness_score: float
    source_diversity_score: float
    evidence_count: int
    directional_evidence_count: int
    decision_id: str = ""
    missing_categories: list[str] = field(default_factory=list)
    benchmark_context: dict[str, Any] = field(default_factory=dict)
    top_bull: list[dict[str, Any]] = field(default_factory=list)
    top_bear: list[dict[str, Any]] = field(default_factory=list)
    neutral_context: list[dict[str, Any]] = field(default_factory=list)
    adversarial_review: dict[str, Any] = field(default_factory=dict)
    risk_advisory: dict[str, Any] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)
    mode: str = "research_council_v2"
    execution_authority: bool = False
    live_gate_eligible: bool = False
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ResearchCouncil:
    """Build leakage-safe evidence and produce a structured research decision."""

    def __init__(self, evidence_hours: int = 72, news_days: int = 5):
        self.evidence_hours = max(1, int(evidence_hours))
        self.news_days = max(1, int(news_days))

    @staticmethod
    def _make_id(*parts: Any) -> str:
        raw = "|".join(str(part or "").strip().lower() for part in parts)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]

    @staticmethod
    def _dedupe(items: list[EvidenceItem]) -> list[EvidenceItem]:
        seen: set[str] = set()
        result: list[EvidenceItem] = []
        for item in sorted(items, key=lambda row: row.weight, reverse=True):
            normalized = re.sub(r"\W+", " ", item.text.lower()).strip()[:220]
            key = item.url.lower().strip() if item.url else f"{item.source_type}:{normalized}"
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
        return result

    @staticmethod
    def _item(
        *, ticker: str, category: str, direction: str, text: str, source: str,
        source_type: str, observed_at: datetime, as_of: datetime, url: str = "",
        confidence: float = 0.5, relevance: float = 0.5,
        provenance: float = 0.5, half_life_hours: float = 72.0,
        source_weight: float = 1.0,
    ) -> EvidenceItem:
        freshness = _freshness_score(observed_at, as_of, half_life_hours)
        confidence = _clamp(confidence)
        relevance = _clamp(relevance)
        provenance = _clamp(provenance)
        weight = (
            source_weight
            * confidence
            * (0.55 + 0.45 * provenance)
            * (0.40 + 0.60 * freshness)
            * (0.60 + 0.40 * relevance)
        )
        return EvidenceItem(
            evidence_id=ResearchCouncil._make_id(
                ticker, source_type, source, url, observed_at.isoformat(), text
            ),
            ticker=ticker.upper(),
            category=category,
            direction=direction,
            text=str(text)[:500],
            source=str(source or "unknown")[:120],
            source_type=source_type,
            observed_at=observed_at.isoformat(),
            url=str(url or "")[:600],
            confidence=round(confidence, 6),
            relevance=round(relevance, 6),
            provenance_score=round(provenance, 6),
            freshness_score=freshness,
            weight=round(weight, 6),
        )

    def _query_insights(self, ticker: str, as_of: datetime) -> list[EvidenceItem]:
        from gateway.knowledge_store import knowledge_store

        cutoff = as_of - timedelta(hours=self.evidence_hours)
        rows = knowledge_store._get_conn().execute(
            """
            SELECT agent_name, insight_type, content, confidence, source_urls, created_at
            FROM agent_insights
            WHERE ticker = ?
              AND datetime(created_at) <= datetime(?)
              AND datetime(created_at) >= datetime(?)
            ORDER BY datetime(created_at) DESC LIMIT 80
            """,
            (
                ticker.upper(), as_of.strftime("%Y-%m-%d %H:%M:%S"),
                cutoff.strftime("%Y-%m-%d %H:%M:%S"),
            ),
        ).fetchall()
        items: list[EvidenceItem] = []
        for row in rows:
            observed = _parse_timestamp(row["created_at"])
            if observed is None or observed > as_of:
                continue
            urls = _json_urls(row["source_urls"])
            text = str(row["content"] or "")
            items.append(self._item(
                ticker=ticker,
                category=_category_for(row["agent_name"], row["insight_type"]),
                direction=_direction_from_text(text),
                text=f"[{row['agent_name']}] {text}",
                source=row["agent_name"],
                source_type="agent_insight",
                observed_at=observed,
                as_of=as_of,
                url=urls[0] if urls else "",
                confidence=_normalize_confidence(row["confidence"], 0.5),
                relevance=0.75,
                provenance=0.95 if urls else 0.65,
                half_life_hours=48.0,
            ))
        return items

    def _query_news(self, ticker: str, as_of: datetime) -> list[EvidenceItem]:
        from gateway.knowledge_store import knowledge_store

        cutoff = as_of - timedelta(days=self.news_days)
        rows = knowledge_store._get_conn().execute(
            """
            SELECT ticker, headline, url, source, published_at, created_at,
                   sentiment_score, relevance_score
            FROM news_articles
            WHERE (ticker = ? OR headline LIKE ?)
              AND datetime(created_at) <= datetime(?)
              AND datetime(COALESCE(NULLIF(published_at, ''), created_at)) <= datetime(?)
              AND datetime(COALESCE(NULLIF(published_at, ''), created_at)) >= datetime(?)
            ORDER BY datetime(COALESCE(NULLIF(published_at, ''), created_at)) DESC
            LIMIT 50
            """,
            (
                ticker.upper(), f"%{ticker.upper()}%",
                as_of.strftime("%Y-%m-%d %H:%M:%S"),
                as_of.strftime("%Y-%m-%d %H:%M:%S"),
                cutoff.strftime("%Y-%m-%d %H:%M:%S"),
            ),
        ).fetchall()
        items: list[EvidenceItem] = []
        for row in rows:
            observed = _parse_timestamp(row["published_at"] or row["created_at"])
            if observed is None or observed > as_of:
                continue
            sentiment = max(-1.0, min(1.0, float(row["sentiment_score"] or 0.0)))
            direction = (
                "BULLISH" if sentiment > 0.15
                else "BEARISH" if sentiment < -0.15
                else "NEUTRAL"
            )
            relevance = _clamp(row["relevance_score"])
            relevance = relevance if relevance > 0 else 0.55
            url = str(row["url"] or "")
            source = str(row["source"] or "unknown")
            items.append(self._item(
                ticker=ticker,
                category="sentiment",
                direction=direction,
                text=f"[news:{source}] {row['headline']}",
                source=source,
                source_type="news",
                observed_at=observed,
                as_of=as_of,
                url=url,
                confidence=0.55 + min(abs(sentiment), 1.0) * 0.35,
                relevance=relevance,
                provenance=(
                    1.0 if url.startswith(("http://", "https://")) and source != "unknown"
                    else 0.55
                ),
                half_life_hours=36.0,
                source_weight=0.95,
            ))
        return items

    @staticmethod
    def _price_rows(ticker: str, as_of: datetime, days: int = 90) -> list[dict[str, Any]]:
        """Return only *completed prior-session* daily bars.

        `daily_ohlcv.date` does not contain an intraday observation timestamp. A
        same-date candle can therefore contain an end-of-day close that was not
        known at an intraday historical `as_of`. The conservative invariant is
        `date < as_of.date()`; timestamped snapshots handle same-day prices.
        """
        from gateway.knowledge_store import knowledge_store

        start = (as_of - timedelta(days=days)).date().isoformat()
        rows = knowledge_store._get_conn().execute(
            """
            SELECT date, close, volume, source
            FROM daily_ohlcv
            WHERE ticker = ? AND date < ? AND date >= ? AND close > 0
            ORDER BY date DESC LIMIT 90
            """,
            (ticker.upper(), as_of.date().isoformat(), start),
        ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _latest_snapshot(ticker: str, as_of: datetime) -> Optional[dict[str, Any]]:
        """Return a timestamped market snapshot only when it existed by `as_of`."""
        from gateway.knowledge_store import knowledge_store

        row = knowledge_store._get_conn().execute(
            """
            SELECT price, signal, metadata_json, created_at
            FROM market_snapshots
            WHERE ticker = ? AND price > 0 AND datetime(created_at) <= datetime(?)
            ORDER BY datetime(created_at) DESC LIMIT 1
            """,
            (ticker.upper(), as_of.strftime("%Y-%m-%d %H:%M:%S")),
        ).fetchone()
        if not row:
            return None
        observed = _parse_timestamp(row["created_at"])
        if observed is None or observed > as_of:
            return None
        # Very old snapshots are not useful as a same-day reference.
        if (as_of - observed).total_seconds() > 36 * 3600:
            return None
        result = dict(row)
        result["observed_at"] = observed
        return result

    @staticmethod
    def _benchmark_for(ticker: str) -> str:
        upper = ticker.upper()
        if upper.endswith((".NS", ".BO")):
            return "^NSEI"
        if upper.endswith("-USD"):
            return "BTC-USD" if upper != "BTC-USD" else ""
        if upper == "SPY":
            return "QQQ"
        return "SPY"

    def _price_context(self, ticker: str, as_of: datetime) -> dict[str, Any]:
        rows = self._price_rows(ticker, as_of)
        snapshot = self._latest_snapshot(ticker, as_of)
        if len(rows) < 5:
            return {"available": False, "reason": "insufficient completed prior-session history"}

        span = min(20, len(rows) - 1)
        base_price = float(rows[span]["close"])
        if snapshot:
            reference_price = float(snapshot["price"])
            observed = snapshot["observed_at"]
            reference_kind = "timestamped_snapshot"
            source = "market_snapshot"
        else:
            reference_price = float(rows[0]["close"])
            observed = _parse_timestamp(rows[0]["date"]) or as_of
            reference_kind = "prior_session_close"
            source = str(rows[0].get("source") or "market_db")

        period_return = (
            (reference_price - base_price) / base_price * 100.0 if base_price else 0.0
        )
        return {
            "available": True,
            "rows": rows,
            "span": span,
            "return_pct": period_return,
            "reference_price": reference_price,
            "reference_observed_at": observed,
            "reference_kind": reference_kind,
            "source": source,
        }

    def _price_and_benchmark(
        self, ticker: str, as_of: datetime
    ) -> tuple[list[EvidenceItem], dict[str, Any]]:
        asset = self._price_context(ticker, as_of)
        if not asset.get("available"):
            return [], {"available": False, "reason": asset.get("reason")}

        asset_return = float(asset["return_pct"])
        direction = (
            "BULLISH" if asset_return > 2
            else "BEARISH" if asset_return < -2
            else "NEUTRAL"
        )
        items = [self._item(
            ticker=ticker,
            category="price",
            direction=direction,
            text=(
                f"[price] {ticker.upper()} point-in-time return over "
                f"{asset['span']} completed bars: {asset_return:+.2f}%"
            ),
            source=asset["source"],
            source_type="price",
            observed_at=asset["reference_observed_at"],
            as_of=as_of,
            confidence=0.85,
            relevance=1.0,
            provenance=1.0,
            half_life_hours=168.0,
            source_weight=1.05,
        )]

        benchmark = self._benchmark_for(ticker)
        context: dict[str, Any] = {
            "available": False,
            "benchmark": benchmark or None,
            "asset_return_pct": round(asset_return, 4),
            "bars": asset["span"],
            "reference_price": round(float(asset["reference_price"]), 8),
            "reference_observed_at": asset["reference_observed_at"].isoformat(),
            "reference_kind": asset["reference_kind"],
        }
        if not benchmark:
            return items, context

        bench = self._price_context(benchmark, as_of)
        if not bench.get("available"):
            context["reason"] = "benchmark point-in-time history unavailable"
            return items, context

        benchmark_return = float(bench["return_pct"])
        alpha = asset_return - benchmark_return
        context.update({
            "available": True,
            "benchmark_return_pct": round(benchmark_return, 4),
            "alpha_pct": round(alpha, 4),
            "benchmark_reference_price": round(float(bench["reference_price"]), 8),
            "benchmark_reference_observed_at": bench["reference_observed_at"].isoformat(),
        })
        alpha_direction = (
            "BULLISH" if alpha > 2 else "BEARISH" if alpha < -2 else "NEUTRAL"
        )
        items.append(self._item(
            ticker=ticker,
            category="price",
            direction=alpha_direction,
            text=(
                f"[benchmark] {ticker.upper()} alpha vs {benchmark}: {alpha:+.2f}% "
                f"({asset_return:+.2f}% vs {benchmark_return:+.2f}%)"
            ),
            source="point_in_time_market_db",
            source_type="benchmark",
            observed_at=asset["reference_observed_at"],
            as_of=as_of,
            confidence=0.85,
            relevance=1.0,
            provenance=1.0,
            half_life_hours=168.0,
        ))
        return items, context

    def _query_lessons(self, ticker: str, as_of: datetime) -> list[EvidenceItem]:
        from gateway.knowledge_store import knowledge_store

        try:
            rows = knowledge_store._get_conn().execute(
                """
                SELECT ticker, source_agent, direction, accuracy, was_correct,
                       lesson, created_at
                FROM trade_lessons
                WHERE ticker = ? AND datetime(created_at) <= datetime(?)
                ORDER BY datetime(created_at) DESC LIMIT 5
                """,
                (ticker.upper(), as_of.strftime("%Y-%m-%d %H:%M:%S")),
            ).fetchall()
        except Exception:
            return []
        items: list[EvidenceItem] = []
        for row in rows:
            observed = _parse_timestamp(row["created_at"])
            if observed is None or observed > as_of:
                continue
            items.append(self._item(
                ticker=ticker,
                category="lesson",
                direction="NEUTRAL",
                text=f"[lesson:{row['source_agent']}] {row['lesson']}",
                source=row["source_agent"] or "reflection_memory",
                source_type="lesson",
                observed_at=observed,
                as_of=as_of,
                confidence=0.55,
                relevance=0.65,
                provenance=0.8,
                half_life_hours=24.0 * 30.0,
                source_weight=0.55,
            ))
        return items

    def build_evidence_pack(self, ticker: str, as_of: Any = None) -> dict[str, Any]:
        ticker = ticker.upper()
        requested = _parse_timestamp(as_of) if as_of else _utc_now()
        if requested is None:
            raise ValueError("as_of must be an ISO-8601 timestamp")
        if requested > _utc_now() + timedelta(minutes=5):
            raise ValueError("as_of cannot be materially in the future")

        items: list[EvidenceItem] = []
        items.extend(self._query_insights(ticker, requested))
        items.extend(self._query_news(ticker, requested))
        price_items, benchmark_context = self._price_and_benchmark(ticker, requested)
        items.extend(price_items)
        items.extend(self._query_lessons(ticker, requested))
        items = self._dedupe(items)
        return {
            "ticker": ticker,
            "as_of": requested.isoformat(),
            "items": items,
            "bull": [i for i in items if i.direction == "BULLISH"],
            "bear": [i for i in items if i.direction == "BEARISH"],
            "neutral": [i for i in items if i.direction == "NEUTRAL"],
            "benchmark_context": benchmark_context,
        }

    @staticmethod
    def _metrics(pack: dict[str, Any]) -> dict[str, Any]:
        items: list[EvidenceItem] = pack["items"]
        bull: list[EvidenceItem] = pack["bull"]
        bear: list[EvidenceItem] = pack["bear"]
        directional = bull + bear
        bull_weight = sum(i.weight for i in bull)
        bear_weight = sum(i.weight for i in bear)
        total_directional_weight = bull_weight + bear_weight
        score = (
            (bull_weight - bear_weight) / total_directional_weight
            if total_directional_weight > 0 else 0.0
        )
        contradiction = (
            2.0 * min(bull_weight, bear_weight) / total_directional_weight
            if total_directional_weight > 0 else 0.0
        )
        covered = {i.category for i in items} & EXPECTED_CATEGORIES
        coverage = len(covered) / len(EXPECTED_CATEGORIES)
        missing = sorted(EXPECTED_CATEGORIES - covered)
        directional_sources = {
            (i.source_type, i.source.lower().strip())
            for i in directional if i.source
        }
        diversity = min(1.0, len(directional_sources) / 4.0)

        if items:
            base = [max(i.confidence * i.relevance, 0.05) for i in items]
            denom = sum(base)
            provenance = sum(i.provenance_score * w for i, w in zip(items, base)) / denom
            freshness = sum(i.freshness_score * w for i, w in zip(items, base)) / denom
        else:
            provenance = freshness = 0.0
        quantity = min(1.0, len(items) / 12.0)
        quality = (
            0.30 * provenance + 0.25 * freshness + 0.25 * coverage
            + 0.10 * diversity + 0.10 * quantity
        )
        confidence = int(max(0, min(
            95,
            abs(score) * 60.0 + quality * 30.0 + coverage * 10.0
            + diversity * 5.0 - contradiction * 25.0,
        )))
        if len(directional) < 3:
            confidence = min(confidence, 40)

        return {
            "directional_score": round(score, 6),
            "contradiction_score": round(contradiction, 6),
            "coverage_score": round(coverage, 6),
            "provenance_score": round(provenance, 6),
            "freshness_score": round(freshness, 6),
            "source_diversity_score": round(diversity, 6),
            "evidence_quality": round(quality, 6),
            "confidence": confidence,
            "missing_categories": missing,
            "directional_count": len(directional),
            "directional_sources": len(directional_sources),
        }

    @staticmethod
    def _base_rating(metrics: dict[str, Any]) -> tuple[str, list[str]]:
        score = float(metrics["directional_score"])
        confidence = int(metrics["confidence"])
        quality = float(metrics["evidence_quality"])
        coverage = float(metrics["coverage_score"])
        contradiction = float(metrics["contradiction_score"])
        reasons: list[str] = []
        if int(metrics["directional_count"]) < 3:
            reasons.append("Fewer than 3 independent directional evidence items")
        if int(metrics["directional_sources"]) < 2:
            reasons.append("Directional evidence lacks independent source diversity")
        if quality < 0.45:
            reasons.append(f"Evidence quality {quality:.2f} is below the 0.45 research floor")
        if coverage < (2.0 / 6.0):
            reasons.append("Research coverage is too narrow across specialist categories")
        if contradiction > 0.85:
            reasons.append("Bull and bear evidence are nearly balanced; conviction is not justified")
        if reasons:
            return "HOLD", reasons
        if score >= 0.55 and confidence >= 70:
            return "BUY", reasons
        if score >= 0.25 and confidence >= 50:
            return "OVERWEIGHT", reasons
        if score <= -0.55 and confidence >= 70:
            return "SELL", reasons
        if score <= -0.25 and confidence >= 50:
            return "UNDERWEIGHT", reasons
        return "HOLD", ["Directional edge is not strong enough for an active rating"]

    @staticmethod
    def _verdict_for_rating(rating: str) -> str:
        if rating in {"BUY", "OVERWEIGHT"}:
            return "BUY"
        if rating in {"SELL", "UNDERWEIGHT"}:
            return "SELL"
        return "HOLD"

    @staticmethod
    def _debate_evidence(pack: dict[str, Any]) -> dict[str, list[str]]:
        def render(item: EvidenceItem) -> str:
            return (
                f"[{item.evidence_id}] [{item.category}] [{item.source}] "
                f"[{item.observed_at}] [weight={item.weight:.3f}] {item.text}"
            )
        return {
            "bull": [render(i) for i in pack["bull"][:12]],
            "bear": [render(i) for i in pack["bear"][:12]],
            "neutral": [render(i) for i in pack["neutral"][:10]],
        }

    @staticmethod
    def _risk_advisory(
        rating: str, confidence: int, metrics: dict[str, Any]
    ) -> dict[str, Any]:
        max_pct = max(0.0, float(settings.MAX_POSITION_PCT) * 100.0)
        if rating == "HOLD" or max_pct <= 0:
            return {
                "research_exposure_ceiling_pct": 0.0,
                "note": "Research does not justify new exposure",
                "execution_authority": False,
            }
        uncertainty = max(0.0, 1.0 - float(metrics["contradiction_score"]) * 0.65)
        ceiling = (
            max_pct * _clamp(confidence / 100.0)
            * float(metrics["evidence_quality"]) * uncertainty
        )
        if rating in {"OVERWEIGHT", "UNDERWEIGHT"}:
            ceiling *= 0.65
        return {
            "research_exposure_ceiling_pct": round(min(max_pct, ceiling), 3),
            "configured_max_position_pct": round(max_pct, 3),
            "note": "Advisory only; Risk Manager and execution gates remain authoritative",
            "execution_authority": False,
        }

    async def analyze(
        self, ticker: str, *, as_of: Any = None,
        use_llm_debate: bool = True, persist: bool = True,
    ) -> ResearchDecision:
        pack = self.build_evidence_pack(ticker, as_of=as_of)
        metrics = self._metrics(pack)
        rating, reasons = self._base_rating(metrics)
        confidence = int(metrics["confidence"])
        review: dict[str, Any] = {"used": False, "alignment": "not_run"}

        if use_llm_debate and pack["items"]:
            try:
                from agents.debate_engine import DebateEngine
                debate = await DebateEngine(max_rounds=2)._llm_debate(
                    pack["ticker"], self._debate_evidence(pack)
                )
                if debate is not None:
                    debate_verdict = debate.verdict
                    base_verdict = self._verdict_for_rating(rating)
                    if base_verdict == "HOLD":
                        alignment = "research_floor_blocks_override"
                    elif debate_verdict == base_verdict:
                        alignment = "aligned"
                        ceiling = int(45 + float(metrics["evidence_quality"]) * 50)
                        confidence = min(95, ceiling, confidence + 5)
                    elif debate_verdict == "HOLD":
                        alignment = "debate_cautious"
                        confidence = max(0, confidence - 10)
                    else:
                        alignment = "conflict"
                        reasons.append(
                            "Adversarial debate conflicts with weighted evidence; fail-closed to HOLD"
                        )
                        rating = "HOLD"
                        confidence = min(confidence, 45)
                    review = {
                        "used": True,
                        "alignment": alignment,
                        "verdict": debate_verdict,
                        "confidence": debate.confidence,
                        "winning_side": debate.winning_side,
                        "key_reason": debate.key_reason,
                        "mode": debate.mode,
                    }
            except Exception as exc:
                review = {
                    "used": False, "alignment": "unavailable",
                    "reason": type(exc).__name__,
                }

        verdict = self._verdict_for_rating(rating)
        if rating == "HOLD" and not reasons:
            reasons.append("Research Council selected HOLD")
        evidence_ids = sorted(i.evidence_id for i in pack["items"])
        decision_id = self._make_id(
            pack["ticker"], pack["as_of"], rating, confidence, *evidence_ids
        )
        decision = ResearchDecision(
            ticker=pack["ticker"],
            as_of=pack["as_of"],
            rating=rating,
            verdict=verdict,
            confidence=confidence,
            directional_score=float(metrics["directional_score"]),
            evidence_quality=float(metrics["evidence_quality"]),
            contradiction_score=float(metrics["contradiction_score"]),
            coverage_score=float(metrics["coverage_score"]),
            provenance_score=float(metrics["provenance_score"]),
            freshness_score=float(metrics["freshness_score"]),
            source_diversity_score=float(metrics["source_diversity_score"]),
            evidence_count=len(pack["items"]),
            directional_evidence_count=int(metrics["directional_count"]),
            decision_id=decision_id,
            missing_categories=list(metrics["missing_categories"]),
            benchmark_context=pack["benchmark_context"],
            top_bull=[i.to_dict() for i in sorted(pack["bull"], key=lambda x: x.weight, reverse=True)[:5]],
            top_bear=[i.to_dict() for i in sorted(pack["bear"], key=lambda x: x.weight, reverse=True)[:5]],
            neutral_context=[i.to_dict() for i in sorted(pack["neutral"], key=lambda x: x.weight, reverse=True)[:5]],
            adversarial_review=review,
            risk_advisory=self._risk_advisory(rating, confidence, metrics),
            reasons=reasons,
            execution_authority=False,
            live_gate_eligible=False,
            created_at=_utc_now().isoformat(),
        )
        if persist:
            self._persist(decision)
        return decision

    @staticmethod
    def _persist(decision: ResearchDecision) -> None:
        from gateway.knowledge_store import knowledge_store

        payload = decision.to_dict()
        try:
            knowledge_store.store_debate_record({
                **payload,
                "winning_side": (
                    "BULL" if decision.directional_score > 0.05
                    else "BEAR" if decision.directional_score < -0.05
                    else "DRAW"
                ),
                "key_reason": "; ".join(decision.reasons[:2])
                or "Weighted point-in-time evidence review",
                "mode": "research_council_v2",
                "evidence_score": decision.directional_score,
            })
        except Exception as exc:
            logger.warning("[%s] research record persistence failed: %s", AGENT_NAME, exc)
        try:
            knowledge_store.store_insight(
                ticker=decision.ticker,
                agent_name=AGENT_NAME,
                insight_type="research_council_v2",
                content=json.dumps({
                    "decision_id": decision.decision_id,
                    "rating": decision.rating,
                    "verdict": decision.verdict,
                    "confidence": decision.confidence,
                    "evidence_quality": decision.evidence_quality,
                    "contradiction_score": decision.contradiction_score,
                    "coverage_score": decision.coverage_score,
                    "source_diversity_score": decision.source_diversity_score,
                    "benchmark_context": decision.benchmark_context,
                    "execution_authority": False,
                }, ensure_ascii=False),
                confidence=decision.confidence / 100.0,
            )
        except Exception as exc:
            logger.debug("[%s] insight persistence skipped: %s", AGENT_NAME, exc)

        # Research scorecard is intentionally separate from live precision evidence.
        try:
            from self_improvement.research_scorecard import research_scorecard
            research_scorecard.record_decision(payload)
        except Exception as exc:
            logger.debug("[%s] scorecard persistence skipped: %s", AGENT_NAME, exc)


_instance: Optional[ResearchCouncil] = None


def get_research_council() -> ResearchCouncil:
    global _instance
    if _instance is None:
        _instance = ResearchCouncil()
    return _instance
