"""Verify live news/social provenance and the decision-to-order safety gate.

No funded order is possible in this script. It requires real RSS/news data,
requires a real supported social provider, and verifies that a HOLD signal cannot
pass the autonomous RiskManager into an entry order.
"""
from __future__ import annotations

import asyncio
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

_TMP_ROOT = Path(tempfile.mkdtemp(prefix="aitradra-news-decision-smoke-"))
_TMP_DATA = _TMP_ROOT / "data"
_TMP_CACHE = _TMP_ROOT / "collector-cache"
_TMP_DATA.mkdir(parents=True, exist_ok=True)
_TMP_CACHE.mkdir(parents=True, exist_ok=True)
os.environ["DATA_DIR"] = str(_TMP_DATA)
os.environ["DATA_CACHE_DIR"] = str(_TMP_CACHE)
os.environ["KNOWLEDGE_DB_NAME"] = "news-decision-knowledge.db"
os.environ["MARKET_DATA_DB_NAME"] = "news-decision-market.sqlite3"
os.environ["PAPER_TRADE_MODE"] = "true"
os.environ["AUTOTRADE_ENABLED"] = "false"
os.environ["MANUAL_LIVE_TRADING_ENABLED"] = "false"

from agents.base_agent import AgentContext
from agents.risk_manager import RiskManagerAgent
from agents.signal_aggregator import SignalAggregatorAgent
from agents.specialist_agents import TechnicalSpecialist
from gateway.data_engine import data_engine
from gateway.scrapers.rss_scraper import RSS_FEEDS, rss_scraper

SUPPORTED_SOCIAL_SOURCES = {"reddit", "stocktwits"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def latest_first(price_data: dict) -> list[dict]:
    rows = []
    for row in price_data.get("ohlcv", []) or []:
        rows.append({
            "timestamp": row.get("t", row.get("timestamp", row.get("date"))),
            "open": float(row.get("o", row.get("open", 0)) or 0),
            "high": float(row.get("h", row.get("high", 0)) or 0),
            "low": float(row.get("l", row.get("low", 0)) or 0),
            "close": float(row.get("c", row.get("close", 0)) or 0),
            "volume": float(row.get("v", row.get("volume", 0)) or 0),
        })
    return list(reversed(rows))


def verify_news() -> dict:
    rss_scraper.fetch_all()
    cached = list(rss_scraper.cache.values())
    valid = [row for row in cached if str(row.get("headline", "")).strip()
             and str(row.get("url", "")).startswith(("http://", "https://"))
             and str(row.get("source", "")).strip()]
    if not valid:
        raise AssertionError("No verifiable live RSS/news records were collected")
    configured_hosts = sorted({url.split("//", 1)[-1].split("/", 1)[0] for feeds in RSS_FEEDS.values() for url in feeds})
    observed_sources = sorted({str(row.get("source")) for row in valid})
    return {
        "collected_at": now(), "configured_feed_hosts": configured_hosts,
        "article_count": len(valid), "observed_sources": observed_sources[:20],
        "sample": [{"headline": row.get("headline"), "source": row.get("source"),
                    "url": row.get("url"), "published_at": row.get("published_at")} for row in valid[:5]],
    }


async def verify_social() -> dict:
    social = await data_engine.get_social_sentiment("AAPL", allow_scrape=True)
    source = str(social.get("source") or "none")
    available = bool(social.get("data_available"))
    estimated = bool(social.get("is_estimated"))

    # Production smoke now requires one genuine social provider to answer. Reddit
    # is primary and Stocktwits is the independent fallback; neither may be
    # represented as estimated data.
    if not available or estimated or source not in SUPPORTED_SOCIAL_SOURCES:
        raise AssertionError(f"No verified live social provider answered: {social}")
    if int(social.get("mentions", -1)) < 0:
        raise AssertionError(f"Invalid social mention count: {social}")

    return {
        "checked_at": now(), "status": "PASS", "provider_available": True,
        "source": source, "is_estimated": False,
        "mentions": int(social.get("mentions", 0) or 0),
        "score": float(social.get("score", 0) or 0),
        "sentiment": social.get("reddit_sentiment"),
        "bull_bear_ratio": social.get("bull_bear_ratio"),
    }


async def verify_hold_cannot_autobuy() -> dict:
    price = await data_engine.get_price_data("AAPL", allow_scrape=True)
    if float(price.get("px", 0) or 0) <= 0 or price.get("is_stale") or price.get("syncing"):
        raise AssertionError(f"Fresh AAPL price unavailable for decision guard test: {price}")
    history = latest_first(price)
    if len(history) < 3:
        raise AssertionError("Insufficient AAPL OHLCV for decision guard test")

    technical = TechnicalSpecialist()._compute_technicals(history, price)
    aggregate_context = AgentContext(task="Verify live AAPL decision guard", ticker="AAPL")
    aggregate_context.metadata["ohlcv_data"] = history
    aggregate_context.observations["specialist_outputs"] = {"technical": technical}
    aggregate = (await SignalAggregatorAgent().act(aggregate_context)).result

    risk_context = AgentContext(task="Verify autonomous risk gate", ticker="AAPL")
    risk_context.observations.update({
        "portfolio": {"total_value": 10_000.0, "cash": 10_000.0, "available": 10_000.0,
                      "daily_pnl_pct": 0.0, "open_positions": [], "paper": True},
        "confidence": float(aggregate.get("confidence", 0) or 0),
        "requested_leverage": 1,
        "signal_aggregator_result": aggregate,
        "specialist_outputs": {"risk": {"risk_level": "MEDIUM", "annualized_volatility": 0.20,
                                         "max_drawdown_pct": 10.0, "var_pct": 2.5}},
    })
    risk = (await RiskManagerAgent().act(risk_context)).result
    verdict = str(aggregate.get("verdict", "HOLD")).upper()
    if verdict == "HOLD" and risk.get("decision") != "BLOCK":
        raise AssertionError(f"HOLD signal incorrectly passed autonomous entry gate: signal={aggregate}, risk={risk}")
    if risk.get("decision") == "APPROVE" and str(risk.get("recommendation", "HOLD")).upper() == "HOLD":
        raise AssertionError(f"Risk manager approved a HOLD recommendation: {risk}")
    return {
        "checked_at": now(), "price_source": price.get("source_used"), "price": float(price.get("px", 0) or 0),
        "technical_signal": technical.get("signal"), "technical_confidence": technical.get("confidence"),
        "aggregate_verdict": aggregate.get("verdict"), "aggregate_direction": aggregate.get("direction"),
        "aggregate_confidence": aggregate.get("confidence"), "risk_decision": risk.get("decision"),
        "risk_reason": risk.get("reason"), "would_submit_entry": risk.get("decision") == "APPROVE",
    }


async def main() -> None:
    report = {
        "started_at": now(), "real_money_orders_submitted": False,
        "news": verify_news(), "social": await verify_social(),
        "decision_guard": await verify_hold_cannot_autobuy(),
        "finished_at": now(), "status": "PASS",
    }
    out = Path(os.environ.get("LIVE_NEWS_DECISION_REPORT", "live-news-decision-report.json"))
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
