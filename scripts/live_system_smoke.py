"""Live-network smoke test for AITradra market collection, agents, and practice trading.

This script intentionally NEVER enables or submits a funded broker order. It uses
real public market/network data, runs deterministic agent logic on those exact
bars, verifies that the same primary public source answers repeatedly over a
measured observation window without stale/cache substitution, and exercises a
practice buy/sell round trip with simulated money.

Independent execution-grade cross-checking is tested separately by
``tests/test_strict_live_price_session.py``. This smoke intentionally does not
turn Stooq/MarketWatch into a fallback requirement for the public research feed.
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

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
from agents.collector_agent import fetch_ticker
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
PRIMARY_SMOKE_SOURCE = "yfinance"


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


def verify_primary_source_window(cycles: list[dict], ticker: str = "AAPL") -> dict:
    """Prove one real primary provider answered repeatedly over the smoke window.

    This is deliberately *not* a provider-fallback test. The smoke requires the
    selected primary public source (yfinance) to answer in every cycle for AAPL.
    If it changes to Stooq, scraping, cache, or stored history, this check fails.
    Execution-grade independent validation remains a separate strict-live-price
    contract and never substitutes its verifier for the authoritative provider.
    """
    if len(cycles) < 2:
        raise AssertionError("At least two live collection cycles are required")

    observations: list[dict] = []
    for cycle in cycles:
        row = (cycle.get("tickers") or {}).get(ticker) or {}
        collector_source = str(row.get("collector_source") or "")
        engine_source = str(row.get("data_engine_source") or "")
        collector_price = float(row.get("collector_close", 0) or 0)
        engine_price = float(row.get("data_engine_price", 0) or 0)

        if collector_source != PRIMARY_SMOKE_SOURCE:
            raise AssertionError(
                f"{ticker} primary-source continuity failed: collector used {collector_source!r}, "
                f"expected {PRIMARY_SMOKE_SOURCE!r}; no fallback is accepted by this check"
            )
        if engine_source != PRIMARY_SMOKE_SOURCE:
            raise AssertionError(
                f"{ticker} DataEngine continuity failed: used {engine_source!r}, "
                f"expected {PRIMARY_SMOKE_SOURCE!r}; stale/public fallback is not accepted"
            )
        if collector_price <= 0 or engine_price <= 0:
            raise AssertionError(f"{ticker} returned a non-positive price during the observation window")

        same_source_diff_pct = (
            abs(collector_price - engine_price)
            / max(abs(collector_price), abs(engine_price), 1e-12)
            * 100.0
        )
        if same_source_diff_pct > 5.0:
            raise AssertionError(
                f"{ticker} same-source observations differ by {same_source_diff_pct:.2f}% "
                "within one smoke cycle"
            )

        observations.append({
            "cycle": cycle.get("cycle"),
            "source": collector_source,
            "collector_price": collector_price,
            "data_engine_price": engine_price,
            "same_source_difference_pct": round(same_source_diff_pct, 6),
            "bar_timestamp": row.get("bar_timestamp"),
            "received_at": row.get("received_at"),
        })

    first = datetime.fromisoformat(str(observations[0]["received_at"]).replace("Z", "+00:00"))
    last = datetime.fromisoformat(str(observations[-1]["received_at"]).replace("Z", "+00:00"))
    window_seconds = max((last - first).total_seconds(), 0.0)
    minimum_window = CYCLE_DELAY_SECONDS * (len(cycles) - 1) * 0.8
    if window_seconds < minimum_window:
        raise AssertionError(
            f"Live observation window was too short ({window_seconds:.1f}s < {minimum_window:.1f}s)"
        )

    prices = [item["collector_price"] for item in observations]
    observed_range_pct = (
        (max(prices) - min(prices)) / max(abs(prices[-1]), 1e-12) * 100.0
        if prices else 0.0
    )
    return {
        "status": "PASS",
        "ticker": ticker,
        "primary_source": PRIMARY_SMOKE_SOURCE,
        "fallback_used": False,
        "cycles_verified": len(observations),
        "observation_window_seconds": round(window_seconds, 3),
        "observed_price_range_pct": round(observed_range_pct, 6),
        "observations": observations,
        "policy": "same real primary provider must answer every cycle; no provider substitution accepted",
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

    report["checks"]["primary_source_window"] = verify_primary_source_window(report["cycles"], "AAPL")
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
