"""Strict real-time price session for decision-grade market data.

There is no execution-provider fallback chain and no historical/cache substitution.
The first configured market-data connection is the authoritative execution source.
An optional second *live* connection may independently validate the authoritative
price, but its quote is never substituted for the primary quote. Observations are
reused only inside a short validity window and the session fails closed on stale,
missing, malformed, or materially disagreeing live data.
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
    def crosscheck_required() -> bool:
        return os.environ.get("LIVE_PRICE_REQUIRE_CROSSCHECK", "true").strip().lower() in {
            "1", "true", "yes", "on"
        }

    @staticmethod
    def max_crosscheck_difference_pct() -> float:
        raw = os.environ.get("LIVE_PRICE_MAX_CROSSCHECK_DIFF_PCT", "1.0")
        try:
            return max(0.05, min(float(raw), 10.0))
        except (TypeError, ValueError):
            return 1.0

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _connections() -> list[dict[str, Any]]:
        connections = list(customer_runtime.enabled_connections("market_data"))
        if not connections:
            raise LivePriceUnavailable(
                "No real-time market-data connection is enabled. Configure a live provider before qualification."
            )
        return connections

    def _cached(self, ticker: str) -> dict[str, Any] | None:
        item = self._cache.get(ticker)
        if not item:
            return None
        try:
            expires_at = datetime.fromisoformat(str(item["expires_at"]).replace("Z", "+00:00"))
            observed_at = datetime.fromisoformat(str(item["observed_at"]).replace("Z", "+00:00"))
        except (KeyError, TypeError, ValueError):
            self._cache.pop(ticker, None)
            return None
        now = self._now()
        if now >= expires_at:
            self._cache.pop(ticker, None)
            return None
        age_seconds = max((now - observed_at).total_seconds(), 0.0)
        return {
            **item,
            "freshness_seconds": round(age_seconds, 3),
            "reused_within_validity_window": True,
        }

    @staticmethod
    def _provider_name(connection: dict[str, Any]) -> str:
        return str(connection.get("name") or connection.get("provider") or "configured-provider")

    async def _fetch_exact_provider(self, connection: dict[str, Any], ticker: str) -> dict[str, Any]:
        provider_name = self._provider_name(connection)
        try:
            row = await connected_sources._price_from_connection(connection, ticker)
        except Exception as exc:
            logger.warning(
                "Strict live price provider %s failed for %s: %s",
                provider_name, ticker, type(exc).__name__,
            )
            raise LivePriceUnavailable(
                f"Real-time provider {provider_name} is unavailable for {ticker}; qualification is blocked."
            ) from exc
        price = float((row or {}).get("px", 0) or 0)
        if price <= 0:
            raise LivePriceUnavailable(
                f"Real-time provider {provider_name} returned no usable price for {ticker}; qualification is blocked."
            )
        return dict(row or {})

    async def get(self, ticker: str, *, force_refresh: bool = False) -> dict[str, Any]:
        ticker = ticker.upper().strip()
        if not ticker:
            raise LivePriceUnavailable("Ticker is required")

        if not force_refresh:
            cached = self._cached(ticker)
            if cached:
                return cached

        connections = self._connections()
        primary = connections[0]
        primary_name = self._provider_name(primary)
        primary_row = await self._fetch_exact_provider(primary, ticker)
        price = float(primary_row.get("px", 0) or 0)

        crosscheck = {
            "required": self.crosscheck_required(),
            "performed": False,
            "eligible": not self.crosscheck_required(),
            "provider": None,
            "price": None,
            "difference_pct": None,
            "maximum_difference_pct": self.max_crosscheck_difference_pct(),
        }
        if self.crosscheck_required():
            if len(connections) < 2:
                raise LivePriceUnavailable(
                    "A second independent real-time market-data connection is required for live price validation; "
                    "qualification is blocked."
                )
            verifier = connections[1]
            verifier_name = self._provider_name(verifier)
            verifier_row = await self._fetch_exact_provider(verifier, ticker)
            verifier_price = float(verifier_row.get("px", 0) or 0)
            difference_pct = abs(price - verifier_price) / max(abs(price), abs(verifier_price), 1e-12) * 100.0
            threshold = self.max_crosscheck_difference_pct()
            crosscheck.update({
                "performed": True,
                "eligible": difference_pct <= threshold,
                "provider": f"connected:{verifier_name}",
                "price": verifier_price,
                "difference_pct": round(difference_pct, 6),
            })
            if difference_pct > threshold:
                raise LivePriceUnavailable(
                    f"Independent live providers disagree for {ticker} by {difference_pct:.3f}% "
                    f"(maximum {threshold:.3f}%); qualification is blocked."
                )

        observed = self._now()
        validity = self.validity_seconds()
        payload = {
            "ticker": ticker,
            "px": price,
            "chg": float(primary_row.get("chg", primary_row.get("pct_chg", 0)) or 0),
            "pct_chg": float(primary_row.get("pct_chg", primary_row.get("chg", 0)) or 0),
            "open": float(primary_row.get("open", 0) or 0),
            "high": float(primary_row.get("high", 0) or 0),
            "low": float(primary_row.get("low", 0) or 0),
            "close": float(primary_row.get("close", price) or price),
            "volume": int(float(primary_row.get("volume", 0) or 0)),
            "source_used": f"connected:{primary_name}",
            "connection_id": primary.get("id"),
            "observed_at": observed.isoformat(),
            "expires_at": (observed + timedelta(seconds=validity)).isoformat(),
            "validity_seconds": validity,
            "freshness_seconds": 0.0,
            "is_estimated": False,
            "is_stale": False,
            "syncing": False,
            "decision_grade": True,
            "fallback_used": False,
            "crosscheck": crosscheck,
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
