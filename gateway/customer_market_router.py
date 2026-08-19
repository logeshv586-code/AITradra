"""Customer-facing market intelligence APIs.

These endpoints deliberately hide agent/provider implementation details. The UI
receives one normalized answer: what happened, why it happened, the current
prediction, risk, evidence, and what to watch next.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agents.orchestrator import mythic_orchestrator
from core.config import settings
from core.logger import get_logger
from gateway.connected_source_adapter import connected_sources
from gateway.customer_runtime import customer_runtime, DEFAULT_HISTORY_USER
from gateway.data_engine import data_engine
from gateway.intelligence_service import intelligence_service
from gateway.knowledge_store import knowledge_store

logger = get_logger(__name__)
router = APIRouter(prefix="/api/customer", tags=["Customer Experience"])


PROVIDER_CATALOG = [
    {
        "id": "alpha_vantage",
        "name": "Alpha Vantage",
        "category": "market_data",
        "description": "Quotes and market data. Enter only your API key.",
        "needs_api_key": True,
    },
    {
        "id": "finnhub",
        "name": "Finnhub",
        "category": "market_data",
        "description": "Quotes plus company news using one API key.",
        "needs_api_key": True,
    },
    {
        "id": "twelve_data",
        "name": "Twelve Data",
        "category": "market_data",
        "description": "Market quotes and price statistics.",
        "needs_api_key": True,
    },
    {
        "id": "newsapi",
        "name": "NewsAPI",
        "category": "news",
        "description": "Searchable global news feed.",
        "needs_api_key": True,
    },
    {
        "id": "gnews",
        "name": "GNews",
        "category": "news",
        "description": "Searchable current news feed.",
        "needs_api_key": True,
    },
    {
        "id": "custom_json",
        "name": "Custom JSON API",
        "category": "market_data",
        "description": "Connect another REST API using an endpoint and simple JSON field mapping.",
        "needs_api_key": False,
    },
    {
        "id": "hyperliquid",
        "name": "Hyperliquid",
        "category": "broker",
        "description": "Real crypto/perpetual trading connection. Live execution remains safety-gated.",
        "needs_api_key": False,
    },
    {
        "id": "ccxt",
        "name": "CCXT Exchange",
        "category": "broker",
        "description": "Binance, Bybit, OKX and other CCXT-compatible exchanges.",
        "needs_api_key": True,
    },
]


class ConnectionRequest(BaseModel):
    id: str | None = None
    name: str = Field(min_length=1, max_length=80)
    category: Literal["market_data", "news", "broker", "llm"]
    provider: str = Field(min_length=1, max_length=80)
    enabled: bool = True
    api_key: str = ""
    api_secret: str = ""
    private_key: str = ""
    password: str = ""
    config: dict[str, Any] = Field(default_factory=dict)


class ResearchRequest(BaseModel):
    query: str = "Give me a complete customer-friendly analysis. What happened, why, prediction, risk and what should I watch next?"
    mode: Literal["QUICK", "DEEP", "INSTITUTIONAL"] = "DEEP"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value if value not in (None, "") else default)
    except (TypeError, ValueError):
        return default


def _agent_view(name: str, payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"name": name.replace("_", " ").title(), "signal": "N/A", "summary": str(payload or "")}
    signal = (
        payload.get("signal")
        or payload.get("verdict")
        or payload.get("risk_level")
        or payload.get("macro_outlook")
        or payload.get("decision")
        or "N/A"
    )
    summary = (
        payload.get("summary")
        or payload.get("reasoning")
        or payload.get("reason")
        or payload.get("audit_summary")
        or "Analysis complete."
    )
    confidence = payload.get("confidence", payload.get("confidence_score"))
    return {
        "name": name.replace("_", " ").replace("agent", "").strip().title(),
        "signal": str(signal),
        "summary": str(summary)[:700],
        "confidence": confidence,
    }


def _normalized_history(price_data: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for row in price_data.get("ohlcv", []) or []:
        if not isinstance(row, dict):
            continue
        result.append(
            {
                "timestamp": row.get("timestamp", row.get("t", row.get("date"))),
                "open": _safe_float(row.get("open", row.get("o"))),
                "high": _safe_float(row.get("high", row.get("h"))),
                "low": _safe_float(row.get("low", row.get("l"))),
                "close": _safe_float(row.get("close", row.get("c"))),
                "volume": _safe_float(row.get("volume", row.get("v"))),
            }
        )
    return result


def _why_it_moved(snapshot: dict[str, Any], news: list[dict[str, Any]]) -> dict[str, Any]:
    price = snapshot.get("price_data", {})
    stats = snapshot.get("historical_stats", {})
    risk = snapshot.get("risk", {})
    change = _safe_float(price.get("pct_chg", price.get("chg")))
    direction_word = "up" if change > 0 else "down" if change < 0 else "mostly unchanged"
    primary = str(snapshot.get("primary_driver", "technical")).replace("_", " ")
    top_headline = next((n for n in news if n.get("headline")), None)
    volume_ratio = _safe_float(stats.get("volume_ratio"), 1.0)
    change_5d = _safe_float(stats.get("change_5d"))
    change_20d = _safe_float(stats.get("change_20d"))

    drivers: list[dict[str, Any]] = [
        {
            "label": "Price move",
            "impact": "positive" if change > 0 else "negative" if change < 0 else "neutral",
            "detail": f"The latest session is {direction_word} {abs(change):.2f}%.",
        },
        {
            "label": "Trend",
            "impact": "positive" if change_20d > 0 else "negative" if change_20d < 0 else "neutral",
            "detail": f"The asset is {change_5d:+.2f}% over 5 sessions and {change_20d:+.2f}% over 20 sessions.",
        },
    ]
    if volume_ratio > 0:
        drivers.append(
            {
                "label": "Trading activity",
                "impact": "high" if volume_ratio >= 1.5 else "normal",
                "detail": f"Volume is about {volume_ratio:.2f}× its recent average.",
            }
        )
    if top_headline:
        drivers.append(
            {
                "label": "Latest catalyst",
                "impact": "news",
                "detail": top_headline.get("headline", ""),
                "source": top_headline.get("source", ""),
                "url": top_headline.get("url", ""),
            }
        )
    drivers.append(
        {
            "label": "Risk backdrop",
            "impact": str(risk.get("risk_level", snapshot.get("risk_level", "MEDIUM"))).lower(),
            "detail": f"Current model risk is {risk.get('risk_level', snapshot.get('risk_level', 'MEDIUM'))} with estimated volatility of {_safe_float(risk.get('annualized_volatility')):.1f}%.",
        }
    )

    summary = (
        f"{snapshot.get('ticker', '')} is {direction_word} {abs(change):.2f}% in the latest session. "
        f"AITradra currently identifies {primary} as the main driver."
    )
    if top_headline:
        summary += f" The freshest related catalyst is “{top_headline.get('headline', '')}”."

    return {
        "summary": summary,
        "primary_driver": primary,
        "drivers": drivers,
        "confidence": snapshot.get("confidence_score", 0),
    }


def _customer_brief(
    snapshot: dict[str, Any],
    news: list[dict[str, Any]],
    deep_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    price = snapshot.get("price_data", {})
    risk = snapshot.get("risk", {})
    profile = snapshot.get("intelligence_profile", {})
    quality = profile.get("data_quality", {}) if isinstance(profile, dict) else {}
    plan = snapshot.get("adaptive_plan", profile.get("adaptive_plan", {}) if isinstance(profile, dict) else {})
    prediction = intelligence_service.to_prediction_record(snapshot)

    agent_payloads = snapshot.get("agents", {}) if isinstance(snapshot.get("agents"), dict) else {}
    if deep_result and isinstance(deep_result.get("specialist_details"), dict):
        agent_payloads = deep_result["specialist_details"]
    agents = [_agent_view(name, payload) for name, payload in agent_payloads.items()]

    return {
        "ticker": snapshot.get("ticker"),
        "name": snapshot.get("name", snapshot.get("ticker")),
        "as_of": snapshot.get("as_of") or snapshot.get("updated_at"),
        "price": {
            "current": _safe_float(price.get("px")),
            "change_pct": _safe_float(price.get("pct_chg", price.get("chg"))),
            "open": _safe_float(price.get("open")),
            "high": _safe_float(price.get("high")),
            "low": _safe_float(price.get("low")),
            "volume": _safe_float(price.get("volume")),
            "source": price.get("source_used", "unknown"),
            "fresh": not bool(price.get("is_stale") or price.get("is_estimated")),
        },
        "why_it_moved": _why_it_moved(snapshot, news),
        "prediction": {
            "direction": prediction.get("prediction_direction", "SIDEWAYS"),
            "recommendation": prediction.get("recommendation", "HOLD"),
            "confidence": prediction.get("confidence_score", 0),
            "current_price": prediction.get("current_price", 0),
            "target_price": prediction.get("predicted_price", 0),
            "expected_move_pct": prediction.get("expected_move_percent", 0),
            "primary_driver": prediction.get("primary_driver", "technical"),
            "reason": prediction.get("reasoning_summary", ""),
        },
        "risk": {
            "level": snapshot.get("risk_level", risk.get("risk_level", "MEDIUM")),
            "annualized_volatility": _safe_float(risk.get("annualized_volatility")),
            "max_drawdown": _safe_float(risk.get("max_drawdown")),
            "var_95": _safe_float(risk.get("var_95")),
        },
        "agent_consensus": {
            "summary": (deep_result or {}).get("response") or snapshot.get("reasoning_summary", ""),
            "confidence": (deep_result or {}).get("confidence", snapshot.get("confidence_score", 0)),
            "consensus": (deep_result or {}).get("consensus", snapshot.get("prediction_direction", "SIDEWAYS")),
            "agents": agents,
            "critique": (deep_result or {}).get("critique", {}),
        },
        "what_to_watch_next": plan.get("next_actions", []),
        "news": news[:12],
        "data_quality": quality,
        "sources": {
            "price": price.get("source_used", "unknown"),
            "news_count": len(news),
            "customer_connections": len(customer_runtime.list_connections()),
        },
    }


@router.get("/providers")
async def provider_catalog():
    return {"providers": PROVIDER_CATALOG}


@router.get("/connections")
async def list_connections():
    return {"connections": customer_runtime.list_connections()}


@router.post("/connections")
async def save_connection(request: ConnectionRequest):
    secrets = {
        "api_key": request.api_key,
        "api_secret": request.api_secret,
        "private_key": request.private_key,
        "password": request.password,
    }
    result = customer_runtime.save_connection(
        connection_id=request.id,
        name=request.name,
        category=request.category,
        provider=request.provider,
        config=request.config,
        secrets=secrets,
        enabled=request.enabled,
    )
    return {"connection": result}


@router.delete("/connections/{connection_id}")
async def delete_connection(connection_id: str):
    if not customer_runtime.delete_connection(connection_id):
        raise HTTPException(status_code=404, detail="Connection not found")
    return {"deleted": True}


@router.post("/connections/{connection_id}/test")
async def test_connection(connection_id: str, ticker: str = "AAPL"):
    return await connected_sources.test_connection(connection_id, ticker=ticker)


@router.get("/history")
async def customer_history(limit: int = 50, ticker: str | None = None):
    return {
        "user_id": DEFAULT_HISTORY_USER,
        "history": customer_runtime.get_history(limit=limit, ticker=ticker),
    }


@router.get("/brief/{ticker}")
async def ticker_brief(ticker: str):
    ticker = ticker.upper().strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker is required")
    snapshot = await intelligence_service.refresh_ticker_intelligence(ticker, allow_scrape=True)
    news = await data_engine.get_news(ticker, max_items=12, allow_scrape=True)
    return _customer_brief(snapshot, news)


@router.post("/research/{ticker}")
async def deep_research(ticker: str, request: ResearchRequest):
    ticker = ticker.upper().strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker is required")

    snapshot = await intelligence_service.refresh_ticker_intelligence(ticker, allow_scrape=True)
    price_data = snapshot.get("price_data", {})
    news = await data_engine.get_news(ticker, max_items=16, allow_scrape=True)
    try:
        recent_insights = knowledge_store.get_recent_insights(ticker=ticker, hours=48)
    except Exception:
        recent_insights = []

    gathered_data = {
        "price_data": price_data,
        "history": _normalized_history(price_data),
        "news": news,
        "knowledge_results": {"recent_agent_insights": recent_insights},
        "intelligence_snapshot": snapshot,
        "intelligence_profile": snapshot.get("intelligence_profile", {}),
    }

    deep_result: dict[str, Any] | None = None
    try:
        deep_result = await mythic_orchestrator.orchestrate(
            query=request.query,
            ticker=ticker,
            gathered_data=gathered_data,
            session_id=f"customer:{DEFAULT_HISTORY_USER}:{ticker}",
            research_mode=request.mode,
            history=[],
        )
    except Exception as exc:
        logger.error(f"Customer deep research failed for {ticker}: {exc}")

    brief = _customer_brief(snapshot, news, deep_result=deep_result)
    customer_runtime.record_history(
        event_type="research",
        ticker=ticker,
        title=f"Researched {ticker}",
        details={
            "recommendation": brief["prediction"]["recommendation"],
            "direction": brief["prediction"]["direction"],
            "confidence": brief["prediction"]["confidence"],
            "price": brief["price"]["current"],
            "summary": brief["why_it_moved"]["summary"],
        },
    )
    return brief


@router.get("/daily-brief")
async def daily_market_brief(limit: int = 12):
    limit = max(3, min(limit, 30))
    snapshots = await intelligence_service.get_watchlist_intelligence(
        tickers=settings.DEFAULT_WATCHLIST[: max(limit * 2, 20)],
        max_age_minutes=180,
    )
    predictions = [intelligence_service.to_prediction_record(item) for item in snapshots]
    movers = sorted(predictions, key=lambda row: abs(_safe_float(row.get("chg"))), reverse=True)[:limit]
    opportunities = sorted(
        predictions,
        key=lambda row: (
            row.get("recommendation") == "BUY",
            _safe_float(row.get("confidence_score")),
        ),
        reverse=True,
    )[:limit]
    return {
        "summary": f"AITradra is tracking {len(predictions)} assets with public and connected data sources.",
        "top_movers": movers,
        "opportunities": opportunities,
        "history_user": DEFAULT_HISTORY_USER,
    }
