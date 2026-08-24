"""Strict real-time price session for decision-grade market data.

This module intentionally has no provider fallback chain and no historical/cache
substitution. It fetches from one configured customer market-data connection,
reuses that exact real observation only for a short validity window, and fails
closed when the provider is unavailable or the observation expires.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

from core.logger import get_logger
from gateway.connected_source_adapter import connected_sources
from gateway.customer_runtime import customer_runtime

logger = get_logger(__name__)


class LivePriceUnavailable(RuntimeError):
    """Raised when decision-grade live price data cannot be obtained."""


class LivePriceSession:
    def __init__(self) -> None:
        self._cache: dict[str, dict[str, Any]] = {}

    @staticmethod
    def validity_seconds() -> int:
        raw = os.environ.get("LIVE_PRICE_VALIDITY_SECONDS", "120")
        try:
            return max(5, min(int(raw), 900))
        except (TypeError, ValueError):
            return 120

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _connection() -> dict[str, Any]:
        connections = customer_runtime.enabled_connections("market_data")
        if not connections:
            raise LivePriceUnavailable(
                "No real-time market-data connection is enabled. Configure one live provider before qualification."
            )
        # Deliberately select one provider only. Do not silently fall back to another.
        return connections[0]

    def _cached(self, ticker: str) -> dict[str, Any] | None:
        item = self._cache.get(ticker)
        if not item:
            return None
        try:
            expires_at = datetime.fromisoformat(str(item["expires_at"]).replace("Z", "+00:00"))
        except (KeyError, TypeError, ValueError):
            return None
        if self._now() >= expires_at:
            self._cache.pop(ticker, None)
            return None
        age_seconds = max((self._now() - datetime.fromisoformat(item["observed_at"])).total_seconds(), 0.0)
        return {
            **item,
            "freshness_seconds": round(age_seconds, 3),
            "reused_within_validity_window": True,
        }

    async def get(self, ticker: str, *, force_refresh: bool = False) -> dict[str, Any]:
        ticker = ticker.upper().strip()
        if not ticker:
            raise LivePriceUnavailable("Ticker is required")

        if not force_refresh:
            cached = self._cached(ticker)
            if cached:
                return cached

        connection = self._connection()
        provider_name = str(connection.get("name") or connection.get("provider") or "configured-provider")
        try:
            # Call exactly the selected provider. Do not use ConnectedSourceAdapter.get_price(),
            # because that method intentionally iterates/falls back across connections.
            row = await connected_sources._price_from_connection(connection, ticker)
        except Exception as exc:
            logger.warning("Strict live price provider %s failed for %s: %s", provider_name, ticker, type(exc).__name__)
            raise LivePriceUnavailable(
                f"Real-time provider {provider_name} is unavailable for {ticker}; qualification is blocked."
            ) from exc

        price = float((row or {}).get("px", 0) or 0)
        if price <= 0:
            raise LivePriceUnavailable(
                f"Real-time provider {provider_name} returned no usable price for {ticker}; qualification is blocked."
            )

        observed = self._now()
        validity = self.validity_seconds()
        payload = {
            "ticker": ticker,
            "px": price,
            "chg": float((row or {}).get("chg", (row or {}).get("pct_chg", 0)) or 0),
            "pct_chg": float((row or {}).get("pct_chg", (row or {}).get("chg", 0)) or 0),
            "open": float((row or {}).get("open", 0) or 0),
            "high": float((row or {}).get("high", 0) or 0),
            "low": float((row or {}).get("low", 0) or 0),
            "close": float((row or {}).get("close", price) or price),
            "volume": int(float((row or {}).get("volume", 0) or 0)),
            "source_used": f"connected:{provider_name}",
            "connection_id": connection.get("id"),
            "observed_at": observed.isoformat(),
            "expires_at": (observed + timedelta(seconds=validity)).isoformat(),
            "validity_seconds": validity,
            "freshness_seconds": 0.0,
            "is_estimated": False,
            "is_stale": False,
            "syncing": False,
            "decision_grade": True,
            "fallback_used": False,
            "reused_within_validity_window": False,
        }
        self._cache[ticker] = payload
        return dict(payload)

    def invalidate(self, ticker: str | None = None) -> None:
        if ticker is None:
            self._cache.clear()
        else:
            self._cache.pop(ticker.upper().strip(), None)


live_price_session = LivePriceSession()
