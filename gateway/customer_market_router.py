"""Customer-facing market intelligence, connections, history, and manual trading.

The endpoints deliberately hide agent/provider implementation details. Customers
receive one normalized view: what happened, why, prediction, risk, evidence,
agent agreement, and what to watch next. Real-money orders are separately gated.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agents.orchestrator import mythic_orchestrator
from brokers.broker_router import Order, OrderSide, OrderType
from brokers.customer_hyperliquid_broker import CustomerHyperliquidBroker
from core.config import settings
from core.logger import get_logger
from core.trading_safety import DailyEquityTracker, get_execution_status
from gateway.connected_source_adapter import connected_sources
from gateway.customer_runtime import DEFAULT_HISTORY_USER, customer_runtime
from gateway.data_engine import data_engine
from gateway.intelligence_service import intelligence_service
from gateway.knowledge_store import knowledge_store

logger = get_logger(__name__)
router = APIRouter(prefix="/api/customer", tags=["Customer Experience"])


PROVIDER_CATALOG = [
    {"id": "alpha_vantage", "name": "Alpha Vantage", "category": "market_data", "description": "Quotes and market data. Enter your API key.", "needs_api_key": True},
    {"id": "finnhub", "name": "Finnhub", "category": "market_data", "description": "Quotes plus company news using one API key.", "needs_api_key": True},
    {"id": "twelve_data", "name": "Twelve Data", "category": "market_data", "description": "Market quotes and price statistics.", "needs_api_key": True},
    {"id": "newsapi", "name": "NewsAPI", "category": "news", "description": "Searchable global news feed.", "needs_api_key": True},
    {"id": "gnews", "name": "GNews", "category": "news", "description": "Searchable current news feed.", "needs_api_key": True},
    {"id": "custom_json", "name": "Custom JSON API", "category": "market_data", "description": "Connect another REST API using an endpoint and simple JSON field mapping.", "needs_api_key": False},
    {"id": "hyperliquid", "name": "Hyperliquid", "category": "broker", "description": "Real crypto/perpetual trading. Live execution remains server safety-gated.", "needs_api_key": False},
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


class ManualOrderRequest(BaseModel):
    connection_id: str
    ticker: str = Field(min_length=1, max_length=20)
    side: Literal["buy", "sell"]
    qty: float = Field(gt=0)
    stop_loss: float | None = Field(default=None, gt=0)
    take_profit: float | None = Field(default=None, gt=0)
    leverage: int = Field(default=1, ge=1, le=10)
    reduce_only: bool = False
    confirm_live: bool = False


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value if value not in (None, "") else default)
    except (TypeError, ValueError):
        return default


def _price_is_actionable(price: dict[str, Any]) -> bool:
    """Only current, directly usable prices may drive BUY/entry decisions."""
    source = str(price.get("source_used", "")).lower()
    stale_source = source in {"none", "knowledge_store", "cache_stale", "stale_cache"}
    return (
        _safe_float(price.get("px")) > 0
        and not stale_source
        and not bool(price.get("is_stale"))
        and not bool(price.get("is_estimated"))
        and not bool(price.get("syncing"))
    )


def _agent_view(name: str, payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"name": name.replace("_", " ").title(), "signal": "N/A", "summary": str(payload or "")}
    signal = payload.get("signal") or payload.get("verdict") or payload.get("risk_level") or payload.get("macro_outlook") or payload.get("decision") or "N/A"
    summary = payload.get("summary") or payload.get("reasoning") or payload.get("reason") or payload.get("audit_summary") or "Analysis complete."
    return {
        "name": name.replace("_", " ").replace("agent", "").strip().title(),
        "signal": str(signal),
        "summary": str(summary)[:700],
        "confidence": payload.get("confidence", payload.get("confidence_score")),
    }


def _normalized_history(price_data: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for row in price_data.get("ohlcv", []) or []:
        if isinstance(row, dict):
            result.append({
                "timestamp": row.get("timestamp", row.get("t", row.get("date"))),
                "open": _safe_float(row.get("open", row.get("o"))),
                "high": _safe_float(row.get("high", row.get("h"))),
                "low": _safe_float(row.get("low", row.get("l"))),
                "close": _safe_float(row.get("close", row.get("c"))),
                "volume": _safe_float(row.get("volume", row.get("v"))),
            })
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
        {"label": "Price move", "impact": "positive" if change > 0 else "negative" if change < 0 else "neutral", "detail": f"The latest session is {direction_word} {abs(change):.2f}%."},
        {"label": "Trend", "impact": "positive" if change_20d > 0 else "negative" if change_20d < 0 else "neutral", "detail": f"The asset is {change_5d:+.2f}% over 5 sessions and {change_20d:+.2f}% over 20 sessions."},
    ]
    if volume_ratio > 0:
        drivers.append({"label": "Trading activity", "impact": "high" if volume_ratio >= 1.5 else "normal", "detail": f"Volume is about {volume_ratio:.2f}× its recent average."})
    if top_headline:
        drivers.append({"label": "Latest catalyst", "impact": "news", "detail": top_headline.get("headline", ""), "source": top_headline.get("source", ""), "url": top_headline.get("url", "")})
    drivers.append({"label": "Risk backdrop", "impact": str(risk.get("risk_level", snapshot.get("risk_level", "MEDIUM"))).lower(), "detail": f"Current model risk is {risk.get('risk_level', snapshot.get('risk_level', 'MEDIUM'))} with estimated volatility of {_safe_float(risk.get('annualized_volatility')):.1f}%."})

    summary = f"{snapshot.get('ticker', '')} is {direction_word} {abs(change):.2f}% in the latest session. AITradra currently identifies {primary} as the main driver."
    if top_headline:
        summary += f" The freshest related catalyst is “{top_headline.get('headline', '')}”."
    if not _price_is_actionable(price):
        summary += " The latest quote is currently cached/stale, so no new trade action should be taken until a fresh price arrives."
    return {"summary": summary, "primary_driver": primary, "drivers": drivers, "confidence": snapshot.get("confidence_score", 0)}


def _customer_brief(snapshot: dict[str, Any], news: list[dict[str, Any]], deep_result: dict[str, Any] | None = None) -> dict[str, Any]:
    price = snapshot.get("price_data", {})
    risk = snapshot.get("risk", {})
    profile = snapshot.get("intelligence_profile", {})
    quality = profile.get("data_quality", {}) if isinstance(profile, dict) else {}
    plan = snapshot.get("adaptive_plan", profile.get("adaptive_plan", {}) if isinstance(profile, dict) else {})
    prediction = intelligence_service.to_prediction_record(snapshot)
    price_actionable = _price_is_actionable(price)
    if not price_actionable:
        prediction = {
            **prediction,
            "recommendation": "HOLD",
            "should_invest": False,
            "reasoning_summary": "Fresh market data is unavailable. The last real observation may be shown for context, but AITradra will not recommend a new entry until a current price is confirmed.",
        }
    agent_payloads = snapshot.get("agents", {}) if isinstance(snapshot.get("agents"), dict) else {}
    if deep_result and isinstance(deep_result.get("specialist_details"), dict):
        agent_payloads = deep_result["specialist_details"]

    return {
        "ticker": snapshot.get("ticker"),
        "name": snapshot.get("name", snapshot.get("ticker")),
        "as_of": snapshot.get("as_of") or snapshot.get("updated_at"),
        "price": {
            "current": _safe_float(price.get("px")), "change_pct": _safe_float(price.get("pct_chg", price.get("chg"))),
            "open": _safe_float(price.get("open")), "high": _safe_float(price.get("high")), "low": _safe_float(price.get("low")),
            "volume": _safe_float(price.get("volume")), "source": price.get("source_used", "unknown"),
            "fresh": price_actionable, "freshness_minutes": price.get("freshness_minutes"),
        },
        "why_it_moved": _why_it_moved(snapshot, news),
        "prediction": {
            "direction": prediction.get("prediction_direction", "SIDEWAYS"), "recommendation": prediction.get("recommendation", "HOLD"),
            "confidence": prediction.get("confidence_score", 0), "current_price": prediction.get("current_price", 0),
            "target_price": prediction.get("predicted_price", 0), "expected_move_pct": prediction.get("expected_move_percent", 0),
            "primary_driver": prediction.get("primary_driver", "technical"), "reason": prediction.get("reasoning_summary", ""),
            "actionable": price_actionable,
        },
        "risk": {
            "level": snapshot.get("risk_level", risk.get("risk_level", "MEDIUM")),
            "annualized_volatility": _safe_float(risk.get("annualized_volatility")),
            "max_drawdown": _safe_float(risk.get("max_drawdown")), "var_95": _safe_float(risk.get("var_95")),
        },
        "agent_consensus": {
            "summary": (deep_result or {}).get("response") or snapshot.get("reasoning_summary", ""),
            "confidence": (deep_result or {}).get("confidence", snapshot.get("confidence_score", 0)),
            "consensus": (deep_result or {}).get("consensus", snapshot.get("prediction_direction", "SIDEWAYS")),
            "agents": [_agent_view(name, payload) for name, payload in agent_payloads.items()],
            "critique": (deep_result or {}).get("critique", {}),
        },
        "what_to_watch_next": plan.get("next_actions", []),
        "news": news[:12], "data_quality": quality,
        "sources": {"price": price.get("source_used", "unknown"), "news_count": len(news), "customer_connections": len(customer_runtime.list_connections())},
    }


async def _run_customer_research(ticker: str, request: ResearchRequest, record_history: bool = True) -> dict[str, Any]:
    ticker = ticker.upper().strip()
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
    if record_history:
        customer_runtime.record_history(
            event_type="research", ticker=ticker, title=f"Researched {ticker}",
            details={
                "recommendation": brief["prediction"]["recommendation"], "direction": brief["prediction"]["direction"],
                "confidence": brief["prediction"]["confidence"], "price": brief["price"]["current"],
                "summary": brief["why_it_moved"]["summary"],
            },
        )
    return brief


def _broker_connection(connection_id: str) -> dict[str, Any]:
    connection = customer_runtime.get_connection(connection_id, include_secrets=True)
    if not connection or connection.get("category") != "broker":
        raise HTTPException(status_code=404, detail="Broker connection not found")
    if connection.get("provider") != "hyperliquid":
        raise HTTPException(status_code=400, detail="Manual real trading currently supports Hyperliquid connections")
    if not connection.get("secrets", {}).get("private_key"):
        raise HTTPException(status_code=400, detail="Broker private key is missing")
    return connection


def _hl_ticker(ticker: str) -> str:
    return ticker.upper().replace("-USD", "").replace("/USDT", "").replace("/USD", "")


@router.get("/providers")
async def provider_catalog():
    return {"providers": PROVIDER_CATALOG}


@router.get("/connections")
async def list_connections():
    return {"connections": customer_runtime.list_connections()}


@router.post("/connections")
async def save_connection(request: ConnectionRequest):
    result = customer_runtime.save_connection(
        connection_id=request.id, name=request.name, category=request.category, provider=request.provider,
        config=request.config,
        secrets={"api_key": request.api_key, "api_secret": request.api_secret, "private_key": request.private_key, "password": request.password},
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
    connection = customer_runtime.get_connection(connection_id, include_secrets=False)
    if connection and connection.get("category") == "broker" and connection.get("provider") == "hyperliquid":
        full = _broker_connection(connection_id)
        broker = CustomerHyperliquidBroker(full["secrets"]["private_key"], full.get("config", {}).get("vault_address"))
        if not broker.info:
            return {"ok": False, "message": "Hyperliquid market connection is unavailable"}
        return {"ok": True, "message": "Hyperliquid connection saved. Real-money execution remains controlled by server safety settings."}
    return await connected_sources.test_connection(connection_id, ticker=ticker)


@router.get("/history")
async def customer_history(limit: int = 50, ticker: str | None = None):
    return {"user_id": DEFAULT_HISTORY_USER, "history": customer_runtime.get_history(limit=limit, ticker=ticker)}


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
    if not ticker.strip():
        raise HTTPException(status_code=400, detail="Ticker is required")
    return await _run_customer_research(ticker, request)


@router.get("/daily-brief")
async def daily_market_brief(limit: int = 12):
    limit = max(3, min(limit, 30))
    snapshots = await intelligence_service.get_watchlist_intelligence(
        tickers=settings.DEFAULT_WATCHLIST[: max(limit * 2, 20)], max_age_minutes=180,
    )
    predictions = []
    for snapshot in snapshots:
        row = intelligence_service.to_prediction_record(snapshot)
        if not _price_is_actionable(snapshot.get("price_data", {})):
            row = {**row, "recommendation": "HOLD", "should_invest": False, "actionable": False}
        else:
            row = {**row, "actionable": True}
        predictions.append(row)
    movers = sorted(predictions, key=lambda row: abs(_safe_float(row.get("chg"))), reverse=True)[:limit]
    opportunities = sorted(
        predictions,
        key=lambda row: (row.get("actionable") is True, row.get("recommendation") == "BUY", _safe_float(row.get("confidence_score"))),
        reverse=True,
    )[:limit]
    return {
        "summary": f"AITradra is tracking {len(predictions)} assets with public and connected data sources. New-entry recommendations require a fresh price.",
        "top_movers": movers, "opportunities": opportunities, "history_user": DEFAULT_HISTORY_USER,
    }


@router.get("/trading/status")
async def manual_trading_status():
    broker_connections = [c for c in customer_runtime.list_connections("broker") if c.get("provider") == "hyperliquid" and c.get("enabled")]
    has_key = any(c.get("has_credentials") for c in broker_connections)
    manual = get_execution_status(settings, purpose="manual", has_private_key=has_key)
    automated = get_execution_status(settings, purpose="automation")
    return {
        "manual": manual,
        "automation": automated,
        "broker_connections": broker_connections,
        "real_money_ready": manual["live_execution_allowed"],
        "message": "Manual real-money trading is ready." if manual["live_execution_allowed"] else "Real-money trading is locked until the server owner enables every live safety setting.",
    }


@router.get("/trading/account")
async def manual_trading_account(connection_id: str):
    connection = _broker_connection(connection_id)
    broker = CustomerHyperliquidBroker(connection["secrets"]["private_key"], connection.get("config", {}).get("vault_address"))
    status = get_execution_status(settings, purpose="manual", has_private_key=True)
    if not status["live_execution_allowed"]:
        return {"ready": False, "blockers": status["blockers"], "balance": {}, "positions": []}
    balance = await broker.get_balance()
    positions = await broker.get_positions()
    return {"ready": True, "balance": balance, "positions": positions}


@router.post("/trading/order")
async def manual_trading_order(request: ManualOrderRequest):
    if not request.confirm_live:
        raise HTTPException(status_code=400, detail="Real-money confirmation is required for every order")
    connection = _broker_connection(request.connection_id)
    status = get_execution_status(settings, purpose="manual", has_private_key=True)
    if not status["live_execution_allowed"]:
        raise HTTPException(status_code=403, detail={"message": "Manual live execution is locked", "blockers": status["blockers"]})
    if not request.reduce_only and (request.stop_loss is None or request.take_profit is None):
        raise HTTPException(status_code=400, detail="Stop-loss and take-profit are required for a new real-money position")

    research_ticker = request.ticker.upper()
    normalized = _hl_ticker(request.ticker)
    leverage = max(1, min(request.leverage, settings.MAX_LEVERAGE))
    broker = CustomerHyperliquidBroker(connection["secrets"]["private_key"], connection.get("config", {}).get("vault_address"))

    # Explicit risk-reducing exits do not depend on AI/research availability,
    # current-price collection, daily-loss gates, or entry-sizing limits. They
    # still require the live safety gate and per-order customer confirmation.
    if request.reduce_only:
        order = Order(
            ticker=normalized,
            side=OrderSide.BUY if request.side == "buy" else OrderSide.SELL,
            qty=request.qty,
            order_type=OrderType.MARKET,
            leverage=leverage,
            reduce_only=True,
            reference_price=None,
        )
        result = await broker.place_order(order)
        customer_runtime.record_history(
            event_type="live_trade",
            ticker=research_ticker,
            title=f"CLOSE {request.qty} {research_ticker}",
            details={
                "status": result.get("status"), "broker": "hyperliquid", "order_id": result.get("order_id"),
                "reduce_only": True, "leverage": leverage,
            },
        )
        return {"order": result, "pre_trade_analysis": None, "daily_pnl_pct": None, "risk_reducing_exit": True}

    brief = await _run_customer_research(
        research_ticker,
        ResearchRequest(query=f"Analyze {research_ticker} immediately before a customer considers a {request.side.upper()} trade. Explain current evidence, risks, contradictions and what could invalidate the setup.", mode="DEEP"),
        record_history=False,
    )
    current_price = _safe_float(brief.get("price", {}).get("current"))
    if current_price <= 0 or not bool(brief.get("price", {}).get("fresh")):
        raise HTTPException(status_code=503, detail="A fresh current market price is required before a new real-money position")

    balance = await broker.get_balance()
    total_equity = _safe_float(balance.get("total"))
    daily_pnl = DailyEquityTracker(scope=f"manual:{request.connection_id}").update(total_equity)
    if daily_pnl <= -settings.MAX_DAILY_LOSS_PCT:
        raise HTTPException(status_code=403, detail=f"Daily loss stop is active ({daily_pnl * 100:.2f}%)")

    positions = await broker.get_positions()
    existing = next((p for p in positions if str(p.get("ticker", "")).upper() == normalized), None)
    if not existing and len(positions) >= settings.MAX_OPEN_POSITIONS:
        raise HTTPException(status_code=403, detail="Maximum number of open positions has been reached")

    estimated_notional = current_price * request.qty
    estimated_margin = estimated_notional / leverage
    max_margin = total_equity * settings.MAX_POSITION_PCT
    if total_equity > 0 and estimated_margin > max_margin:
        raise HTTPException(status_code=403, detail=f"Order exceeds the {settings.MAX_POSITION_PCT * 100:.1f}% per-position margin limit")

    order = Order(
        ticker=normalized,
        side=OrderSide.BUY if request.side == "buy" else OrderSide.SELL,
        qty=request.qty,
        order_type=OrderType.MARKET,
        stop_loss=request.stop_loss,
        take_profit=request.take_profit,
        leverage=leverage,
        reduce_only=False,
        reference_price=current_price,
    )
    result = await broker.place_order(order)
    customer_runtime.record_history(
        event_type="live_trade",
        ticker=research_ticker,
        title=f"{request.side.upper()} {request.qty} {research_ticker}",
        details={
            "status": result.get("status"), "broker": "hyperliquid", "order_id": result.get("order_id"),
            "stop_loss": request.stop_loss, "take_profit": request.take_profit, "leverage": leverage,
            "ai_recommendation": brief.get("prediction", {}).get("recommendation"),
            "ai_confidence": brief.get("prediction", {}).get("confidence"),
            "data_actionable": brief.get("prediction", {}).get("actionable"),
        },
    )
    return {"order": result, "pre_trade_analysis": brief, "daily_pnl_pct": daily_pnl * 100}
