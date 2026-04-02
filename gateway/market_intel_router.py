"""Unified market-intelligence overview endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Request

from core.logger import get_logger
from gateway.intelligence_service import intelligence_service
from gateway.knowledge_store import knowledge_store
from gateway.local_plugin_registry import local_plugin_registry

logger = get_logger(__name__)
router = APIRouter(prefix="/api/intel", tags=["Market Intelligence"])


AGENT_REGISTRY = [
    {
        "id": "datacollector",
        "name": "DataCollector",
        "aliases": ["DataCollector", "DataAgent"],
        "tier": "v3_intelligence",
        "role": "Local market data collection and normalization",
        "cadence_hours": 24,
    },
    {
        "id": "blobstorage",
        "name": "BlobStorageAgent",
        "aliases": ["BlobStorageAgent", "BlobAgent"],
        "tier": "v3_intelligence",
        "role": "Daily blob persistence for replayable market state",
        "cadence_hours": 24,
    },
    {
        "id": "marketrag",
        "name": "MarketRagAgent",
        "aliases": ["MarketRagAgent", "RagAgent"],
        "tier": "v3_intelligence",
        "role": "Semantic retrieval over historical market context",
        "cadence_hours": 24,
    },
    {
        "id": "newsintel",
        "name": "NewsIntelAgent",
        "aliases": ["NewsIntelAgent", "NewsAgent"],
        "tier": "v3_intelligence",
        "role": "Headline aggregation and catalyst analysis",
        "cadence_hours": 6,
    },
    {
        "id": "pricemove",
        "name": "PriceMoveAgent",
        "aliases": ["PriceMoveAgent", "PriceAgent"],
        "tier": "v3_intelligence",
        "role": "Short-term move analysis and volatility clustering",
        "cadence_hours": 6,
    },
    {
        "id": "forecast",
        "name": "ForecastAgent",
        "aliases": ["ForecastAgent"],
        "tier": "v3_intelligence",
        "role": "Technical projection and target estimation",
        "cadence_hours": 6,
    },
    {
        "id": "explanation",
        "name": "ExplainAgent",
        "aliases": ["ExplainAgent"],
        "tier": "v3_intelligence",
        "role": "Readable synthesis for the final desk narrative",
        "cadence_hours": 6,
    },
    {
        "id": "think",
        "name": "ThinkAgent",
        "aliases": ["ThinkAgent"],
        "tier": "v3_intelligence",
        "role": "Reasoning layer across technical and news evidence",
        "cadence_hours": 6,
    },
    {
        "id": "mcpnews",
        "name": "McpNewsAgent",
        "aliases": ["McpNewsAgent"],
        "tier": "v3_intelligence",
        "role": "Multi-source news retrieval and consolidation",
        "cadence_hours": 6,
    },
    {
        "id": "batch",
        "name": "BatchAgent",
        "aliases": ["BatchAgent"],
        "tier": "v3_intelligence",
        "role": "Nightly batch warmups across the watchlist universe",
        "cadence_hours": 24,
    },
    {
        "id": "uiapi",
        "name": "UIApiAgent",
        "aliases": ["UIApiAgent"],
        "tier": "v3_intelligence",
        "role": "Gateway coordination for UI-facing market requests",
        "cadence_hours": 2,
    },
    {
        "id": "queryrouter",
        "name": "QueryRouter",
        "aliases": ["QueryRouter"],
        "tier": "v4_mythic",
        "role": "User intent routing into the mythic pipeline",
        "cadence_hours": 2,
    },
    {
        "id": "orchestrator",
        "name": "MythicOrchestrator",
        "aliases": ["MythicOrchestrator"],
        "tier": "v4_mythic",
        "role": "Fan-out orchestration and final consensus shaping",
        "cadence_hours": 2,
    },
    {
        "id": "techspec",
        "name": "TechnicalSpecialist",
        "aliases": ["TechnicalSpecialist"],
        "tier": "v4_mythic",
        "role": "OHLCV structure, momentum, and trend detection",
        "cadence_hours": 6,
    },
    {
        "id": "fundamental",
        "name": "FundamentalSpecialist",
        "aliases": ["FundamentalSpecialist"],
        "tier": "v4_mythic",
        "role": "Balance sheet and valuation context",
        "cadence_hours": 24,
    },
    {
        "id": "catalyst",
        "name": "CatalystSpecialist",
        "aliases": ["CatalystSpecialist"],
        "tier": "v4_mythic",
        "role": "Event-driven catalysts and earnings triggers",
        "cadence_hours": 24,
    },
    {
        "id": "sector",
        "name": "SectorSpecialist",
        "aliases": ["SectorSpecialist"],
        "tier": "v4_mythic",
        "role": "Cross-asset and sector-relative positioning",
        "cadence_hours": 24,
    },
    {
        "id": "riskspec",
        "name": "RiskSpecialist",
        "aliases": ["RiskSpecialist"],
        "tier": "v4_mythic",
        "role": "Volatility, drawdown, VaR, and stress analysis",
        "cadence_hours": 6,
    },
    {
        "id": "riskmanager",
        "name": "RiskManagerAgent",
        "aliases": ["RiskManagerAgent"],
        "tier": "v4_mythic",
        "role": "Execution-time risk gating and guardrails",
        "cadence_hours": 6,
    },
    {
        "id": "macrospec",
        "name": "MacroSpecialist",
        "aliases": ["MacroSpecialist"],
        "tier": "v4_mythic",
        "role": "Macro, rates, and broader news regime context",
        "cadence_hours": 6,
    },
    {
        "id": "sentiment",
        "name": "SentimentClassifierAgent",
        "aliases": ["SentimentClassifierAgent"],
        "tier": "specialist",
        "role": "Sentiment scoring and social/news polarity",
        "cadence_hours": 6,
    },
    {
        "id": "aggregator",
        "name": "SignalAggregatorAgent",
        "aliases": ["SignalAggregatorAgent"],
        "tier": "specialist",
        "role": "Signal weighting and ensemble alignment",
        "cadence_hours": 6,
    },
    {
        "id": "critique",
        "name": "CritiqueAgent",
        "aliases": ["CritiqueAgent"],
        "tier": "v4_mythic",
        "role": "Confidence calibration and contradiction checks",
        "cadence_hours": 6,
    },
    {
        "id": "deepresearch",
        "name": "DeepResearchAgent",
        "aliases": ["DeepResearchAgent"],
        "tier": "research",
        "role": "Long-form investigation and thesis generation",
        "cadence_hours": 24,
    },
]


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _minutes_since(value: str | None) -> int | None:
    ts = _parse_ts(value)
    if ts is None:
        return None
    return max(int((datetime.now() - ts).total_seconds() // 60), 0)


def _health_score(status: str, freshness_minutes: int | None, error_count: int, latency_ms: int) -> int:
    score = 100
    score -= min(error_count * 8, 40)
    score -= min(latency_ms // 5000, 12)
    if freshness_minutes is None:
        score -= 18
    elif freshness_minutes > 1440:
        score -= 28
    elif freshness_minutes > 360:
        score -= 14
    if status == "error":
        score -= 20
    return max(score, 18)


def build_agent_status_payload() -> dict:
    health_rows = knowledge_store.get_all_agent_health()
    health_by_name = {row["agent_name"]: row for row in health_rows}
    agents: list[dict] = []

    for meta in AGENT_REGISTRY:
        row = next((health_by_name.get(alias) for alias in meta["aliases"] if health_by_name.get(alias)), None)
        freshness_minutes = _minutes_since(row.get("last_seen") if row else None)
        cadence_hours = meta.get("cadence_hours", 24)

        if row is None:
            status = "standby"
            status_label = "NO DATA"
        else:
            raw_status = str(row.get("status", "idle")).lower()
            if raw_status == "error":
                status = "error"
                status_label = "ERROR"
            elif freshness_minutes is not None and freshness_minutes > cadence_hours * 60:
                status = "stale"
                status_label = "STALE"
            elif raw_status == "active":
                status = "active"
                status_label = "ACTIVE"
            else:
                status = "idle"
                status_label = "ONLINE"

        latency_ms = int(row.get("latency_ms", 0) if row else 0)
        error_count = int(row.get("error_count", 0) if row else 0)
        agents.append(
            {
                "id": meta["id"],
                "name": meta["name"],
                "type": meta["tier"],
                "role": meta["role"],
                "status": status,
                "status_label": status_label,
                "last_seen": row.get("last_seen") if row else None,
                "freshness_minutes": freshness_minutes,
                "freshness_label": (
                    "No heartbeat"
                    if freshness_minutes is None
                    else f"{freshness_minutes}m ago"
                    if freshness_minutes < 60
                    else f"{freshness_minutes // 60}h ago"
                    if freshness_minutes < 1440
                    else f"{freshness_minutes // 1440}d ago"
                ),
                "cadence_hours": cadence_hours,
                "latency_ms": latency_ms,
                "error_count": error_count,
                "current_task": row.get("current_task") if row else None,
                "health_score": _health_score(status, freshness_minutes, error_count, latency_ms),
            }
        )

    summary = {
        "total": len(agents),
        "active": sum(1 for agent in agents if agent["status"] == "active"),
        "online": sum(1 for agent in agents if agent["status"] in {"active", "idle"}),
        "stale": sum(1 for agent in agents if agent["status"] == "stale"),
        "error": sum(1 for agent in agents if agent["status"] == "error"),
        "median_latency_ms": 0,
    }
    latencies = sorted(agent["latency_ms"] for agent in agents if agent["latency_ms"] > 0)
    if latencies:
        mid = len(latencies) // 2
        if len(latencies) % 2 == 0:
            summary["median_latency_ms"] = int((latencies[mid - 1] + latencies[mid]) / 2)
        else:
            summary["median_latency_ms"] = int(latencies[mid])
    return {"agents": agents, "summary": summary, "generated_at": datetime.now().isoformat()}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in {None, ""}:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _time_horizon(snapshot: dict) -> str:
    risk_level = snapshot.get("risk_level", "MEDIUM")
    sector = snapshot.get("sector", "")
    change_20d = abs(_safe_float(snapshot.get("historical_stats", {}).get("change_20d")))
    if sector == "Cryptocurrency" or risk_level == "HIGH":
        return "Intraday to 3 days"
    if change_20d >= 8:
        return "1 to 2 weeks"
    return "2 to 6 weeks"


def _timing_window(snapshot: dict, held: bool) -> tuple[str, str]:
    stats = snapshot.get("historical_stats", {})
    rsi = stats.get("rsi14")
    change_5d = _safe_float(stats.get("change_5d"))
    direction = snapshot.get("prediction_direction", "SIDEWAYS")
    recommendation = snapshot.get("recommendation", "HOLD")

    if held and (recommendation == "AVOID" or direction == "DOWN"):
        return "Defensive exit", "Momentum and recommendation have turned defensive. Reducing exposure is reasonable."
    if held and recommendation == "BUY":
        return "Hold and trail", "The held position still has supportive trend conditions. Tighten stops instead of forcing an exit."
    if rsi is not None and rsi >= 70:
        return "Wait for pullback", "The move is extended. Let price cool before adding fresh capital."
    if rsi is not None and rsi <= 42 and direction == "UP":
        return "Accumulation window", "Momentum is constructive without looking overheated, which favors staged entries."
    if change_5d >= 2 and direction == "UP":
        return "Momentum continuation", "Recent strength is aligned with the current signal, which suits short swing entries."
    if direction == "DOWN":
        return "Risk-off watch", "Trend confirmation is weak. Capital preservation matters more than forcing a trade."
    return "Monitor setup", "The setup is balanced. Wait for stronger confirmation before changing position size."


def _action_for_snapshot(snapshot: dict, held: bool) -> str:
    recommendation = snapshot.get("recommendation", "HOLD")
    direction = snapshot.get("prediction_direction", "SIDEWAYS")
    confidence = _safe_float(snapshot.get("confidence_score"))
    risk_level = snapshot.get("risk_level", "MEDIUM")

    if held:
        if recommendation == "AVOID" or (direction == "DOWN" and confidence >= 55):
            return "SELL"
        if risk_level == "HIGH" and direction != "UP":
            return "TRIM"
        if recommendation == "BUY" and confidence >= 65:
            return "HOLD / ADD"
        return "HOLD"

    if recommendation == "BUY" and confidence >= 60 and risk_level != "HIGH":
        return "BUY"
    if recommendation == "AVOID" or direction == "DOWN":
        return "WAIT"
    return "WATCH"


def _priority(snapshot: dict, action: str, plugin_alignment: int) -> float:
    score = _safe_float(snapshot.get("confidence_score"))
    risk_level = snapshot.get("risk_level", "MEDIUM")
    stale = bool(snapshot.get("freshness", {}).get("stale"))

    if action == "BUY":
        score += 8
    elif action in {"SELL", "TRIM"}:
        score += 6

    if risk_level == "LOW":
        score += 6
    elif risk_level == "HIGH":
        score -= 10

    score += plugin_alignment * 4
    if stale:
        score -= 12
    return round(score, 1)


def _plugin_alignment(snapshot: dict, plugin_signals: list[dict]) -> tuple[int, list[dict]]:
    desired = snapshot.get("recommendation", "HOLD").upper()
    aligned = []
    for signal in plugin_signals:
        plugin_signal = str(signal.get("signal", "HOLD")).upper()
        if plugin_signal == desired or (desired == "BUY" and plugin_signal == "UP"):
            aligned.append(signal)
    return len(aligned), aligned[:3]


def _build_action_card(snapshot: dict, held_position: dict | None, plugin_signals: list[dict]) -> dict:
    price_data = snapshot.get("price_data", {})
    headlines = snapshot.get("top_headlines", [])
    held = held_position is not None
    action = _action_for_snapshot(snapshot, held)
    timing_window, timing_note = _timing_window(snapshot, held)
    alignment_count, aligned_signals = _plugin_alignment(snapshot, plugin_signals)
    priority = _priority(snapshot, action, alignment_count)

    return {
        "ticker": snapshot["ticker"],
        "name": snapshot.get("name", snapshot["ticker"]),
        "sector": snapshot.get("sector", "Global Equity"),
        "price": round(_safe_float(price_data.get("px")), 2),
        "change_pct": round(_safe_float(price_data.get("pct_chg"), _safe_float(price_data.get("chg"))), 2),
        "recommendation": snapshot.get("recommendation", "HOLD"),
        "action": action,
        "confidence_score": round(_safe_float(snapshot.get("confidence_score")), 1),
        "risk_level": snapshot.get("risk_level", "MEDIUM"),
        "expected_move_percent": round(_safe_float(snapshot.get("expected_move_percent")), 2),
        "primary_driver": snapshot.get("primary_driver", "technical"),
        "time_horizon": _time_horizon(snapshot),
        "timing_window": timing_window,
        "timing_note": timing_note,
        "reasoning_summary": snapshot.get("reasoning_summary", ""),
        "freshness_minutes": _minutes_since(snapshot.get("updated_at") or snapshot.get("as_of")),
        "stale": bool(snapshot.get("freshness", {}).get("stale")),
        "priority": priority,
        "held": held,
        "position": held_position,
        "top_headline": headlines[0]["headline"] if headlines else "",
        "plugin_alignment": alignment_count,
        "plugin_signals": aligned_signals,
    }


def _merge_news_feed(snapshots: list[dict]) -> list[dict]:
    seen: set[str] = set()
    feed: list[dict] = []
    for snapshot in snapshots:
        for item in snapshot.get("top_headlines", [])[:3]:
            headline = str(item.get("headline", "")).strip()
            if not headline:
                continue
            key = headline.lower()
            if key in seen:
                continue
            seen.add(key)
            score = _safe_float(item.get("sentiment_score"))
            impact = "HIGH" if abs(score) >= 0.45 else "MEDIUM" if abs(score) >= 0.2 else "LOW"
            feed.append(
                {
                    "ticker": snapshot["ticker"],
                    "headline": headline,
                    "source": item.get("source", "market_feed"),
                    "published_at": item.get("published_at", ""),
                    "sentiment_score": round(score, 2),
                    "impact": impact,
                }
            )
    impact_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    feed.sort(key=lambda item: (impact_order.get(item["impact"], 3), item.get("published_at", "")), reverse=False)
    return feed[:30]


@router.get("/plugins")
async def get_local_plugins():
    return {
        "plugins": local_plugin_registry.get_plugins(),
        "summary": local_plugin_registry.get_summary(),
        "signal_count": len(local_plugin_registry.load_signals(limit=500)),
    }


@router.get("/overview")
async def market_intel_overview(request: Request):
    snapshots = await intelligence_service.get_watchlist_intelligence(max_age_minutes=240)
    watchlist = [intelligence_service.to_watchlist_record(snapshot) for snapshot in snapshots]

    simulation = getattr(request.app.state, "simulation", None)
    portfolio_state = simulation.get_status() if simulation else {"positions": [], "initialized": False}
    positions = portfolio_state.get("positions", []) or []
    positions_by_ticker = {str(position.get("ticker", "")).upper(): position for position in positions}

    plugin_signals = local_plugin_registry.load_signals(limit=2000)
    plugin_signals_by_ticker: dict[str, list[dict]] = {}
    for signal in plugin_signals:
        plugin_signals_by_ticker.setdefault(signal["ticker"], []).append(signal)

    action_cards = [
        _build_action_card(
            snapshot,
            positions_by_ticker.get(snapshot["ticker"].upper()),
            plugin_signals_by_ticker.get(snapshot["ticker"].upper(), []),
        )
        for snapshot in snapshots
    ]

    top_opportunities = sorted(
        [card for card in action_cards if card["action"] == "BUY"],
        key=lambda card: (-card["priority"], -card["confidence_score"]),
    )[:8]
    sell_candidates = sorted(
        [card for card in action_cards if card["action"] in {"SELL", "TRIM"}],
        key=lambda card: (-card["priority"], -card["confidence_score"]),
    )[:8]
    watch_candidates = sorted(
        [card for card in action_cards if card["action"] in {"WATCH", "WAIT"}],
        key=lambda card: (-card["priority"], -card["confidence_score"]),
    )[:8]
    portfolio_actions = sorted(
        [card for card in action_cards if card["held"]],
        key=lambda card: (-card["priority"], -card["confidence_score"]),
    )[:10]

    bullish = sum(1 for snapshot in snapshots if snapshot.get("prediction_direction") == "UP")
    bearish = sum(1 for snapshot in snapshots if snapshot.get("prediction_direction") == "DOWN")
    stale = sum(1 for snapshot in snapshots if snapshot.get("freshness", {}).get("stale"))
    low_risk = sum(1 for snapshot in snapshots if snapshot.get("risk_level") == "LOW")
    high_risk = sum(1 for snapshot in snapshots if snapshot.get("risk_level") == "HIGH")
    buy_count = sum(1 for snapshot in snapshots if snapshot.get("recommendation") == "BUY")

    freshness_values = [
        _minutes_since(snapshot.get("updated_at") or snapshot.get("as_of"))
        for snapshot in snapshots
        if _minutes_since(snapshot.get("updated_at") or snapshot.get("as_of")) is not None
    ]

    movers = sorted(
        [
            {
                "ticker": record["id"],
                "price": record["px"],
                "change_pct": record["chg"],
                "recommendation": record.get("recommendation", "HOLD"),
                "sector": record.get("sector", "Global Equity"),
            }
            for record in watchlist
        ],
        key=lambda item: abs(_safe_float(item.get("change_pct"))),
        reverse=True,
    )[:10]

    agent_network = build_agent_status_payload()
    plugin_summary = local_plugin_registry.get_summary()

    return {
        "generated_at": datetime.now().isoformat(),
        "universe": {
            "tracked_assets": len(snapshots),
            "bullish": bullish,
            "bearish": bearish,
            "buy_setups": buy_count,
            "low_risk": low_risk,
            "high_risk": high_risk,
            "stale_assets": stale,
        },
        "freshness": {
            "average_age_minutes": round(sum(freshness_values) / len(freshness_values), 1) if freshness_values else None,
            "fresh_assets": max(len(snapshots) - stale, 0),
            "stale_assets": stale,
        },
        "market_pulse": {
            "top_movers": movers,
            "plugin_signal_count": len(plugin_signals),
        },
        "top_opportunities": top_opportunities,
        "sell_candidates": sell_candidates,
        "watch_candidates": watch_candidates,
        "portfolio_actions": portfolio_actions,
        "news_feed": _merge_news_feed(snapshots),
        "plugins": {
            "summary": plugin_summary,
            "sources": local_plugin_registry.get_plugins(),
        },
        "agent_network": agent_network,
        "portfolio": {
            "initialized": bool(portfolio_state.get("initialized")),
            "positions": len(positions),
            "total_balance": portfolio_state.get("total_balance", 0),
            "available_cash": portfolio_state.get("available_cash", 0),
            "invested_amount": portfolio_state.get("invested_amount", 0),
            "total_profit_loss": portfolio_state.get("total_profit_loss", 0),
            "profit_loss_percentage": portfolio_state.get("profit_loss_percentage", 0),
        },
    }
