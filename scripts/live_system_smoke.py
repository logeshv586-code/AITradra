"""Live-network smoke test for AITradra market collection, agents, and practice trading.

This script intentionally NEVER enables or submits a funded broker order. It uses
real public market/network data, runs deterministic agent logic on those exact
bars, verifies important quotes against an independent provider, and exercises a
practice buy/sell round trip with simulated money.
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import httpx

_TMP_ROOT = Path(tempfile.mkdtemp(prefix="aitradra-live-smoke-"))
_TMP_DATA_DIR = _TMP_ROOT / "data"
_TMP_CACHE_DIR = _TMP_ROOT / "collector-cache"
_TMP_DATA_DIR.mkdir(parents=True, exist_ok=True)
_TMP_CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ["DATA_CACHE_DIR"] = str(_TMP_CACHE_DIR)
os.environ["DATA_DIR"] = str(_TMP_DATA_DIR)
os.environ["KNOWLEDGE_DB_NAME"] = "smoke-knowledge.db"
os.environ["MARKET_DATA_DB_NAME"] = "smoke-market.sqlite3"
os.environ["PAPER_TRADE_MODE"] = "true"
os.environ["AUTOTRADE_ENABLED"] = "false"
os.environ["MANUAL_LIVE_TRADING_ENABLED"] = "false"

from agents.base_agent import AgentContext
from agents.collector_agent import _fetch_stooq, _fetch_yfinance, fetch_ticker
from agents.signal_aggregator import SignalAggregatorAgent
from agents.specialist_agents import TechnicalSpecialist
from gateway.data_engine import data_engine
from gateway.knowledge_store import knowledge_store
import gateway.simulation_engine as simulation_module
from gateway.simulation_engine import SimulationEngine

REAL_SOURCES = {
    "yfinance", "stooq", "alpha_vantage", "yahoo_scrape",
    "yahoo_scrape_html", "marketwatch_scrape",
}
TICKERS = ["AAPL", "SPY", "BTC-USD", "RELIANCE.NS"]
CYCLES = 3
CYCLE_DELAY_SECONDS = 15


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def latest_first(price_data: dict) -> list[dict]:
    bars = []
    for row in price_data.get("ohlcv", []) or []:
        bars.append({
            "timestamp": row.get("t", row.get("timestamp", row.get("date"))),
            "open": float(row.get("o", row.get("open", 0)) or 0),
            "high": float(row.get("h", row.get("high", 0)) or 0),
            "low": float(row.get("l", row.get("low", 0)) or 0),
            "close": float(row.get("c", row.get("close", 0)) or 0),
            "volume": float(row.get("v", row.get("volume", 0)) or 0),
        })
    return list(reversed(bars))


def assert_finite(value, label: str) -> None:
    if not math.isfinite(float(value)):
        raise AssertionError(f"{label} is not finite: {value}")


async def collect_cycle(cycle: int) -> dict:
    result = {"cycle": cycle, "started_at": utc_now(), "tickers": {}}
    for ticker in TICKERS:
        df, source = await fetch_ticker(ticker, period="1mo", use_cache=False, scrape_ok=True)
        if df is None or df.empty:
            raise AssertionError(f"No live public data returned for {ticker}")
        if source not in REAL_SOURCES:
            raise AssertionError(f"{ticker} returned non-live source {source!r}")
        latest = df.iloc[-1]
        price = float(latest.get("Close", 0) or 0)
        if price <= 0:
            raise AssertionError(f"{ticker} returned invalid close {price}")

        payload = await data_engine.get_price_data(ticker, allow_scrape=True)
        if float(payload.get("px", 0) or 0) <= 0:
            raise AssertionError(f"DataEngine returned no usable price for {ticker}")
        if payload.get("source_used") in {"none", "knowledge_store", "cache_stale", "stale_cache"}:
            raise AssertionError(f"DataEngine did not obtain current public data for {ticker}: {payload.get('source_used')}")
        if payload.get("is_stale") or payload.get("syncing"):
            raise AssertionError(f"DataEngine incorrectly marked the fresh {ticker} response stale")

        result["tickers"][ticker] = {
            "collector_source": source,
            "collector_close": price,
            "collector_rows": int(len(df)),
            "data_engine_source": payload.get("source_used"),
            "data_engine_price": float(payload.get("px", 0) or 0),
            "data_engine_change_pct": float(payload.get("pct_chg", 0) or 0),
            "bar_timestamp": str(df.index[-1]),
            "received_at": utc_now(),
        }
    result["finished_at"] = utc_now()
    return result


async def _marketwatch_aapl_quote() -> float | None:
    """Independent no-key quote fallback when Stooq is unavailable.

    MarketWatch is intentionally separate from Yahoo/yfinance. We parse only the
    displayed quote and reject missing/implausible values rather than guessing.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/123 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    url = "https://www.marketwatch.com/investing/stock/aapl"
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True, headers=headers) as client:
            response = await client.get(url)
        response.raise_for_status()
        text = response.text
        patterns = [
            r'class="value"[^>]*>\s*\$?([0-9][0-9,]*\.?[0-9]*)',
            r'"price"\s*:\s*"?\$?([0-9][0-9,]*\.?[0-9]*)',
            r'bg-quote[^>]*field="Last"[^>]*>\s*([0-9][0-9,]*\.?[0-9]*)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = float(match.group(1).replace(",", ""))
                if 10 < value < 10000:
                    return value
    except Exception:
        return None
    return None


async def independent_price_crosscheck() -> dict:
    """Require yfinance plus at least one independent public price provider."""
    yf_df = await asyncio.to_thread(_fetch_yfinance, "AAPL", "1mo")
    stooq_df = await _fetch_stooq("AAPL", "1mo")
    marketwatch_close = None if stooq_df is not None and not stooq_df.empty else await _marketwatch_aapl_quote()

    yf_available = bool(yf_df is not None and not yf_df.empty)
    if not yf_available:
        raise AssertionError("Primary yfinance source unavailable for independent price verification")
    yf_close = float(yf_df.iloc[-1]["Close"])

    independent_source = None
    independent_close = None
    if stooq_df is not None and not stooq_df.empty:
        independent_source = "stooq"
        independent_close = float(stooq_df.iloc[-1]["Close"])
    elif marketwatch_close is not None:
        independent_source = "marketwatch"
        independent_close = float(marketwatch_close)

    if independent_source is None or independent_close is None:
        raise AssertionError("No independent AAPL provider answered (tried Stooq and MarketWatch)")

    diff_pct = abs(yf_close - independent_close) / max(abs(yf_close), abs(independent_close), 1e-12) * 100
    # A daily yfinance close compared with an intraday MarketWatch quote can
    # legitimately differ modestly. 10% remains a deliberately conservative
    # smoke-test corruption/disagreement guard.
    if diff_pct > 10:
        raise AssertionError(
            f"Independent AAPL providers disagree by {diff_pct:.2f}%: yfinance={yf_close}, {independent_source}={independent_close}"
        )
    return {
        "status": "PASS",
        "primary_source": "yfinance",
        "primary_close": yf_close,
        "independent_source": independent_source,
        "independent_close": independent_close,
        "difference_pct": round(diff_pct, 4),
        "stooq_available": bool(stooq_df is not None and not stooq_df.empty),
        "marketwatch_fallback_used": independent_source == "marketwatch",
    }


async def test_agents_on_real_bars(ticker: str = "AAPL") -> dict:
    price_data = await data_engine.get_price_data(ticker, allow_scrape=True)
    history = latest_first(price_data)
    if len(history) < 3:
        raise AssertionError(f"Not enough live bars for agent test: {ticker}")
    latest_close = float(history[0]["close"])
    if abs(latest_close - float(price_data.get("close", price_data.get("px", 0)))) > max(latest_close * 0.02, 0.05):
        raise AssertionError(f"Latest-first agent history mismatch: history[0]={latest_close}, price={price_data.get('close')}")

    technical = TechnicalSpecialist()._compute_technicals(history, price_data)
    if technical.get("signal") not in {"BULLISH", "BEARISH", "NEUTRAL"}:
        raise AssertionError(f"Unexpected technical signal: {technical}")
    assert_finite(technical.get("confidence", 0), "technical confidence")

    context = AgentContext(task=f"Live smoke signal for {ticker}", ticker=ticker)
    context.metadata["ohlcv_data"] = history
    context.observations["specialist_outputs"] = {"technical": technical}
    signal = (await SignalAggregatorAgent().act(context)).result
    if signal.get("verdict") not in {"STRONG BUY", "BUY", "HOLD", "SELL", "STRONG SELL"}:
        raise AssertionError(f"Unexpected signal verdict: {signal}")
    assert_finite(signal.get("confidence", 0), "signal confidence")

    entry = float(signal.get("entry_point", 0) or 0)
    if entry and abs(entry - latest_close) > max(latest_close * 0.001, 0.01):
        raise AssertionError(f"Signal entry {entry} is not using latest real close {latest_close}")
    if signal.get("direction") == "BUY" and entry > 0 and not (float(signal["stop_loss"]) < entry < float(signal["take_profit"])):
        raise AssertionError(f"Invalid BUY stop/target from real bars: {signal}")
    if signal.get("direction") == "SELL" and entry > 0 and not (float(signal["take_profit"]) < entry < float(signal["stop_loss"])):
        raise AssertionError(f"Invalid SELL stop/target from real bars: {signal}")

    return {"ticker": ticker, "price_source": price_data.get("source_used"), "latest_close": latest_close,
            "bars_used": len(history), "technical": technical, "signal": signal}


async def practice_round_trip(agent_report: dict) -> dict:
    ticker = agent_report["ticker"]
    signal = agent_report["signal"]
    price_before = await data_engine.get_price_data(ticker, allow_scrape=True)
    reference_before = float(price_before.get("px", 0) or 0)
    if reference_before <= 0:
        raise AssertionError("Practice test has no real reference price")
    simulation_module.DATA_FILE = str(_TMP_ROOT / "practice-state.json")

    recommendation = signal.get("verdict", "HOLD")
    customer_recommendation = "BUY" if "BUY" in recommendation else "AVOID" if "SELL" in recommendation else "HOLD"
    direction = signal.get("direction", "HOLD")
    snapshot = {
        "ticker": ticker, "recommendation": customer_recommendation,
        "prediction_direction": direction, "confidence_score": float(signal.get("confidence", 0) or 0),
        "risk_level": signal.get("metadata", {}).get("risk_level", "MEDIUM"),
        "primary_driver": "technical", "updated_at": utc_now(), "as_of": utc_now(), "price_data": price_before,
    }
    knowledge_store.store_ticker_intelligence(ticker, snapshot)

    engine = SimulationEngine(data_engine)
    engine.initialize_account(10_000)
    bought = await engine.buy_stock(ticker, 0.1, prediction=direction, confidence_score=float(signal.get("confidence", 0) or 0))
    buy_trade = bought["history"][-1]
    if buy_trade["type"] != "BUY" or buy_trade["reference_price"] <= 0 or buy_trade["price"] <= buy_trade["reference_price"]:
        raise AssertionError(f"Practice buy validation failed: {buy_trade}")
    if buy_trade["fee"] <= 0 or buy_trade["signal_context"]["recommendation"] != customer_recommendation:
        raise AssertionError(f"Practice buy provenance/fee validation failed: {buy_trade}")

    sold = await engine.sell_stock(ticker)
    sell_trade = sold["history"][-1]
    if sell_trade["type"] != "SELL" or sell_trade["reference_price"] <= 0 or sell_trade["price"] >= sell_trade["reference_price"]:
        raise AssertionError(f"Practice sell validation failed: {sell_trade}")
    if sell_trade["fee"] <= 0 or sold["positions"]:
        raise AssertionError(f"Practice close validation failed: {sell_trade}")

    return {
        "uses_real_money": False, "ticker": ticker, "agent_recommendation": customer_recommendation,
        "agent_direction": direction, "agent_confidence": float(signal.get("confidence", 0) or 0),
        "buy": buy_trade, "sell": sell_trade, "ending_balance": sold["total_balance"],
        "total_profit_loss": sold["total_profit_loss"], "fees_paid": sold["fees_paid"],
    }


async def main() -> None:
    report = {"started_at": utc_now(), "real_money_orders_submitted": False, "cycles": [], "checks": {}}
    for cycle in range(1, CYCLES + 1):
        report["cycles"].append(await collect_cycle(cycle))
        if cycle < CYCLES:
            await asyncio.sleep(CYCLE_DELAY_SECONDS)

    report["checks"]["independent_price_crosscheck"] = await independent_price_crosscheck()
    agent_report = await test_agents_on_real_bars("AAPL")
    report["checks"]["agent_pipeline"] = agent_report
    report["checks"]["practice_round_trip"] = await practice_round_trip(agent_report)
    report["finished_at"] = utc_now()
    report["status"] = "PASS"

    out = Path(os.environ.get("LIVE_SMOKE_REPORT", "live-smoke-report.json"))
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
