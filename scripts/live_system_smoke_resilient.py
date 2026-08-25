"""Resilient wrapper around the live-system smoke.

The authoritative price source is never substituted.  If the primary provider is
transiently unavailable, this wrapper records the rejected source/error evidence,
retries with bounded backoff, and only hands a cycle to the normal smoke after
both collector and DataEngine provenance resolve to the required primary source.
"""

from __future__ import annotations

import asyncio
import contextlib
import io
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

import scripts.live_system_smoke as smoke
from core.primary_source_retry import PrimarySourceUnavailable, retry_primary_row
from gateway.cache import cache


PRIMARY_TICKER = os.environ.get("LIVE_SMOKE_PRIMARY_TICKER", "AAPL").upper()
REQUIRED_SOURCE = os.environ.get(
    "LIVE_SMOKE_REQUIRED_PRIMARY_SOURCE", smoke.PRIMARY_SMOKE_SOURCE
).strip().lower()
MAX_ATTEMPTS = max(int(os.environ.get("LIVE_SMOKE_PRIMARY_MAX_ATTEMPTS", "4")), 1)
BASE_DELAY_SECONDS = max(
    float(os.environ.get("LIVE_SMOKE_PRIMARY_RETRY_BASE_SECONDS", "5")), 0.0
)
MAX_DELAY_SECONDS = max(
    float(os.environ.get("LIVE_SMOKE_PRIMARY_RETRY_MAX_SECONDS", "20")),
    BASE_DELAY_SECONDS,
)
ERROR_REPORT = Path(
    os.environ.get("LIVE_SMOKE_ERROR_REPORT", "live-smoke-error-report.json")
)

RUN_TELEMETRY: dict[str, Any] = {
    "started_at": smoke.utc_now(),
    "required_primary_ticker": PRIMARY_TICKER,
    "required_primary_source": REQUIRED_SOURCE,
    "fallback_accepted": False,
    "retry_policy": {
        "max_attempts": MAX_ATTEMPTS,
        "base_delay_seconds": BASE_DELAY_SECONDS,
        "max_delay_seconds": MAX_DELAY_SECONDS,
        "policy": "retry authoritative source; observe but never accept provider substitution",
    },
    "cycles": [],
}


def _write_telemetry() -> None:
    ERROR_REPORT.write_text(
        json.dumps(RUN_TELEMETRY, indent=2, default=str),
        encoding="utf-8",
    )


def _delete_price_cache(ticker: str) -> None:
    """Remove a smoke-run cache entry so rejected fallback evidence cannot stick."""
    try:
        with sqlite3.connect(cache.db_path) as conn:
            conn.execute(
                "DELETE FROM cache WHERE key = ? AND data_type = ?",
                (ticker.upper(), "price"),
            )
    except Exception as exc:
        RUN_TELEMETRY.setdefault("cache_cleanup_warnings", []).append(
            {
                "ticker": ticker,
                "at": smoke.utc_now(),
                "error_type": type(exc).__name__,
                "error_message": str(exc)[-1000:],
            }
        )


def _purge_non_primary_price_cache(ticker: str) -> None:
    """Reuse a fresh primary observation, but purge any cached substitute."""
    try:
        metadata = cache.get_metadata(ticker.upper(), "price")
        source = str(metadata.get("source") or "").strip().lower()
    except Exception:
        source = ""
    if source and source != REQUIRED_SOURCE:
        _delete_price_cache(ticker)


async def _collect_ticker_row(ticker: str, *, require_primary: bool) -> dict[str, Any]:
    """Collect one row with full numeric/provenance validation.

    For the required primary ticker, HTML scraping is disabled during retries.
    Other public providers may still answer and are recorded as rejected evidence;
    they are never accepted as the authoritative source.
    """
    stderr_capture = io.StringIO()
    try:
        with contextlib.redirect_stderr(stderr_capture):
            df, source = await smoke.fetch_ticker(
                ticker,
                period="1mo",
                use_cache=False,
                scrape_ok=not require_primary,
            )
    finally:
        diagnostic = stderr_capture.getvalue().strip()

    if df is None or df.empty:
        suffix = f"; provider diagnostic: {diagnostic[-1000:]}" if diagnostic else ""
        raise AssertionError(f"No live public data returned for {ticker}{suffix}")
    if source not in smoke.REAL_SOURCES:
        raise AssertionError(f"{ticker} returned non-live source {source!r}")

    latest = df.iloc[-1]
    collector_price = smoke.require_positive_finite(
        latest.get("Close", 0), f"{ticker} collector close"
    )

    # If the authoritative collector source itself did not answer, do not make a
    # second provider request merely to manufacture a passing DataEngine row.
    # Return the rejected provenance to the retry policy instead.
    if require_primary and str(source).lower() != REQUIRED_SOURCE:
        return {
            "collector_source": source,
            "collector_close": collector_price,
            "collector_rows": int(len(df)),
            "data_engine_source": "not_checked_primary_unavailable",
            "data_engine_price": None,
            "data_engine_change_pct": None,
            "bar_timestamp": str(df.index[-1]),
            "received_at": smoke.utc_now(),
            "primary_fetch_diagnostic": diagnostic[-2000:] if diagnostic else None,
        }

    if require_primary:
        # A previously rejected fallback must never be reused.  A fresh cache row
        # whose provenance is already the authoritative source may be reused inside
        # the normal DataEngine TTL, reducing duplicate provider calls/rate pressure.
        _purge_non_primary_price_cache(ticker)

    payload = await smoke.data_engine.get_price_data(ticker, allow_scrape=True)
    engine_price = smoke.require_positive_finite(
        payload.get("px", 0), f"{ticker} DataEngine price"
    )
    engine_change_pct = smoke.require_finite_number(
        payload.get("pct_chg", 0), f"{ticker} DataEngine change percentage"
    )
    if payload.get("source_used") in {
        "none",
        "knowledge_store",
        "cache_stale",
        "stale_cache",
    }:
        raise AssertionError(
            f"DataEngine did not obtain current public data for {ticker}: "
            f"{payload.get('source_used')}"
        )
    if payload.get("is_stale") or payload.get("syncing"):
        raise AssertionError(f"DataEngine incorrectly marked the fresh {ticker} response stale")

    return {
        "collector_source": source,
        "collector_close": collector_price,
        "collector_rows": int(len(df)),
        "data_engine_source": payload.get("source_used"),
        "data_engine_price": engine_price,
        "data_engine_change_pct": engine_change_pct,
        "data_engine_freshness_minutes": payload.get("freshness_minutes"),
        "bar_timestamp": str(df.index[-1]),
        "received_at": smoke.utc_now(),
        "primary_fetch_diagnostic": diagnostic[-2000:] if diagnostic else None,
    }


async def _before_primary_retry(_attempt: int, record: dict[str, Any]) -> None:
    """Prevent a rejected fallback response from surviving into the next attempt."""
    _delete_price_cache(PRIMARY_TICKER)
    record["cache_action"] = "deleted price cache before retry"


async def resilient_collect_cycle(cycle: int) -> dict[str, Any]:
    result: dict[str, Any] = {
        "cycle": cycle,
        "started_at": smoke.utc_now(),
        "tickers": {},
    }

    async def fetch_primary_row() -> dict[str, Any]:
        return await _collect_ticker_row(PRIMARY_TICKER, require_primary=True)

    try:
        primary_row, retry_telemetry = await retry_primary_row(
            fetch_primary_row,
            required_source=REQUIRED_SOURCE,
            max_attempts=MAX_ATTEMPTS,
            base_delay_seconds=BASE_DELAY_SECONDS,
            max_delay_seconds=MAX_DELAY_SECONDS,
            before_retry=_before_primary_retry,
        )
    except PrimarySourceUnavailable as exc:
        cycle_telemetry = {
            "cycle": cycle,
            "status": "FAIL",
            "primary_retry": exc.telemetry,
        }
        RUN_TELEMETRY["cycles"].append(cycle_telemetry)
        RUN_TELEMETRY["status"] = "FAIL"
        RUN_TELEMETRY["failure"] = {
            "cycle": cycle,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }
        RUN_TELEMETRY["finished_at"] = smoke.utc_now()
        _write_telemetry()
        raise

    result["tickers"][PRIMARY_TICKER] = primary_row
    result["primary_retry"] = retry_telemetry

    for ticker in smoke.TICKERS:
        if ticker == PRIMARY_TICKER:
            continue
        result["tickers"][ticker] = await _collect_ticker_row(
            ticker,
            require_primary=False,
        )

    result["finished_at"] = smoke.utc_now()
    RUN_TELEMETRY["cycles"].append(
        {
            "cycle": cycle,
            "status": "PASS",
            "primary_retry": retry_telemetry,
        }
    )
    _write_telemetry()
    return result


async def main() -> None:
    smoke.collect_cycle = resilient_collect_cycle
    try:
        await smoke.main()
        recovered = sum(
            1
            for item in RUN_TELEMETRY["cycles"]
            if (item.get("primary_retry") or {}).get("recovered_after_transient_failure")
        )
        RUN_TELEMETRY["status"] = "PASS"
        RUN_TELEMETRY["recovered_transient_cycles"] = recovered
    except Exception as exc:
        RUN_TELEMETRY.setdefault("status", "FAIL")
        RUN_TELEMETRY.setdefault(
            "failure",
            {
                "error_type": type(exc).__name__,
                "error_message": str(exc)[-2000:],
            },
        )
        raise
    finally:
        RUN_TELEMETRY["finished_at"] = smoke.utc_now()
        _write_telemetry()


if __name__ == "__main__":
    asyncio.run(main())
