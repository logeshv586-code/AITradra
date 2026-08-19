"""Adapters for customer-supplied market/news APIs.

Built-in public collection remains the default. These connections are optional
and are tried first so a customer can bring a preferred data provider without
editing Python or environment files. A generic JSON mode supports custom REST
APIs through a small field mapping.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import httpx

from core.logger import get_logger
from gateway.customer_runtime import customer_runtime

logger = get_logger(__name__)


def _dig(payload: Any, path: str | None, default: Any = None) -> Any:
    if not path:
        return payload
    current = payload
    for part in str(path).split("."):
        if isinstance(current, dict):
            current = current.get(part, default)
        elif isinstance(current, list) and part.isdigit():
            idx = int(part)
            current = current[idx] if 0 <= idx < len(current) else default
        else:
            return default
        if current is None:
            return default
    return current


def _float(value: Any, default: float = 0.0) -> float:
    try:
        text = str(value).replace("%", "").replace(",", "").strip()
        return float(text)
    except (TypeError, ValueError):
        return default


class ConnectedSourceAdapter:
    def __init__(self) -> None:
        self.timeout = httpx.Timeout(12.0, connect=6.0)

    async def get_price(self, ticker: str) -> dict[str, Any] | None:
        for connection in customer_runtime.enabled_connections("market_data"):
            try:
                result = await self._price_from_connection(connection, ticker.upper())
                if result and _float(result.get("px")) > 0:
                    result["source_used"] = f"connected:{connection['name']}"
                    result["connection_id"] = connection["id"]
                    return result
            except Exception as exc:
                logger.warning(
                    "Connected price source %s failed: %s",
                    connection.get("name"),
                    type(exc).__name__,
                )
        return None

    async def get_news(self, ticker: str, limit: int = 20) -> list[dict[str, Any]]:
        collected: list[dict[str, Any]] = []
        connections = customer_runtime.enabled_connections("news")
        # Finnhub can serve both quote and company news from one market-data key.
        connections += [
            c
            for c in customer_runtime.enabled_connections("market_data")
            if c.get("provider") == "finnhub"
        ]
        seen_connections: set[str] = set()
        for connection in connections:
            if connection["id"] in seen_connections:
                continue
            seen_connections.add(connection["id"])
            try:
                rows = await self._news_from_connection(connection, ticker.upper(), limit)
                for row in rows:
                    row.setdefault("source", connection["name"])
                    row["connected_source"] = True
                    collected.append(row)
            except Exception as exc:
                logger.warning(
                    "Connected news source %s failed: %s",
                    connection.get("name"),
                    type(exc).__name__,
                )

        seen: set[str] = set()
        unique = []
        for row in collected:
            headline = str(row.get("headline") or row.get("title") or "").strip()
            key = headline.lower()
            if headline and key not in seen:
                seen.add(key)
                unique.append(row)
        return unique[:limit]

    async def test_connection(self, connection_id: str, ticker: str = "AAPL") -> dict[str, Any]:
        connection = customer_runtime.get_connection(connection_id, include_secrets=True)
        if not connection:
            return {"ok": False, "message": "Connection not found"}
        try:
            if connection["category"] == "news":
                rows = await self._news_from_connection(connection, ticker.upper(), 3)
                return {
                    "ok": bool(rows),
                    "message": f"Received {len(rows)} news items" if rows else "API responded but no news items were found",
                }
            if connection["category"] == "market_data":
                row = await self._price_from_connection(connection, ticker.upper())
                price = _float((row or {}).get("px"))
                return {
                    "ok": price > 0,
                    "message": f"Live price received for {ticker.upper()}: {price:.2f}" if price > 0 else "API responded but no usable price was found",
                }
            # Broker and LLM connections are validated by their runtime consumers.
            return {"ok": True, "message": "Connection saved; validation occurs when this provider is used"}
        except Exception as exc:
            return {"ok": False, "message": f"Connection check failed: {type(exc).__name__}"}

    async def _price_from_connection(self, connection: dict[str, Any], ticker: str) -> dict[str, Any] | None:
        provider = connection.get("provider", "custom_json")
        secrets = connection.get("secrets", {})
        config = connection.get("config", {})
        key = secrets.get("api_key", "")

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            if provider == "alpha_vantage":
                response = await client.get(
                    "https://www.alphavantage.co/query",
                    params={"function": "GLOBAL_QUOTE", "symbol": ticker, "apikey": key},
                )
                payload = response.json().get("Global Quote", {})
                return {
                    "px": _float(payload.get("05. price")),
                    "chg": _float(payload.get("10. change percent")),
                    "pct_chg": _float(payload.get("10. change percent")),
                    "open": _float(payload.get("02. open")),
                    "high": _float(payload.get("03. high")),
                    "low": _float(payload.get("04. low")),
                    "close": _float(payload.get("05. price")),
                    "volume": int(_float(payload.get("06. volume"))),
                }

            if provider == "finnhub":
                response = await client.get(
                    "https://finnhub.io/api/v1/quote",
                    params={"symbol": ticker, "token": key},
                )
                payload = response.json()
                return {
                    "px": _float(payload.get("c")),
                    "chg": _float(payload.get("dp")),
                    "pct_chg": _float(payload.get("dp")),
                    "open": _float(payload.get("o")),
                    "high": _float(payload.get("h")),
                    "low": _float(payload.get("l")),
                    "close": _float(payload.get("c")),
                    "previous_close": _float(payload.get("pc")),
                }

            if provider == "twelve_data":
                response = await client.get(
                    "https://api.twelvedata.com/quote",
                    params={"symbol": ticker, "apikey": key},
                )
                payload = response.json()
                return {
                    "px": _float(payload.get("close")),
                    "chg": _float(payload.get("percent_change")),
                    "pct_chg": _float(payload.get("percent_change")),
                    "open": _float(payload.get("open")),
                    "high": _float(payload.get("high")),
                    "low": _float(payload.get("low")),
                    "close": _float(payload.get("close")),
                    "volume": int(_float(payload.get("volume"))),
                }

            return await self._custom_price(client, config, secrets, ticker)

    async def _custom_price(
        self,
        client: httpx.AsyncClient,
        config: dict[str, Any],
        secrets: dict[str, Any],
        ticker: str,
    ) -> dict[str, Any] | None:
        endpoint = str(config.get("endpoint", "")).replace("{ticker}", ticker)
        if not endpoint:
            return None
        params = dict(config.get("query_params") or {})
        headers = dict(config.get("headers") or {})
        api_key = secrets.get("api_key", "")
        key_name = config.get("api_key_name", "apikey")
        if api_key:
            if config.get("api_key_location", "header") == "query":
                params[key_name] = api_key
            else:
                headers[key_name] = api_key
        response = await client.get(endpoint, params=params, headers=headers)
        response.raise_for_status()
        payload = response.json()
        mapping = config.get("mapping") or {}
        root = _dig(payload, mapping.get("root")) if mapping.get("root") else payload
        price = _float(_dig(root, mapping.get("price", "price")))
        change = _float(_dig(root, mapping.get("change_pct", "change_pct")))
        return {
            "px": price,
            "chg": change,
            "pct_chg": change,
            "open": _float(_dig(root, mapping.get("open", "open"))),
            "high": _float(_dig(root, mapping.get("high", "high"))),
            "low": _float(_dig(root, mapping.get("low", "low"))),
            "close": price,
            "volume": int(_float(_dig(root, mapping.get("volume", "volume")))),
        }

    async def _news_from_connection(
        self, connection: dict[str, Any], ticker: str, limit: int
    ) -> list[dict[str, Any]]:
        provider = connection.get("provider", "custom_json")
        secrets = connection.get("secrets", {})
        config = connection.get("config", {})
        key = secrets.get("api_key", "")

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            if provider == "newsapi":
                response = await client.get(
                    "https://newsapi.org/v2/everything",
                    params={"q": ticker, "sortBy": "publishedAt", "pageSize": min(limit, 50), "apiKey": key},
                )
                rows = response.json().get("articles", [])
                return [
                    {
                        "headline": row.get("title", ""),
                        "summary": row.get("description", "") or "",
                        "url": row.get("url", ""),
                        "source": (row.get("source") or {}).get("name", connection["name"]),
                        "published_at": row.get("publishedAt", ""),
                    }
                    for row in rows
                ]

            if provider == "gnews":
                response = await client.get(
                    "https://gnews.io/api/v4/search",
                    params={"q": ticker, "max": min(limit, 10), "token": key},
                )
                rows = response.json().get("articles", [])
                return [
                    {
                        "headline": row.get("title", ""),
                        "summary": row.get("description", "") or "",
                        "url": row.get("url", ""),
                        "source": (row.get("source") or {}).get("name", connection["name"]),
                        "published_at": row.get("publishedAt", ""),
                    }
                    for row in rows
                ]

            if provider == "finnhub":
                today = date.today()
                response = await client.get(
                    "https://finnhub.io/api/v1/company-news",
                    params={
                        "symbol": ticker,
                        "from": (today - timedelta(days=7)).isoformat(),
                        "to": today.isoformat(),
                        "token": key,
                    },
                )
                rows = response.json() if isinstance(response.json(), list) else []
                return [
                    {
                        "headline": row.get("headline", ""),
                        "summary": row.get("summary", "") or "",
                        "url": row.get("url", ""),
                        "source": row.get("source", connection["name"]),
                        "published_at": row.get("datetime", ""),
                    }
                    for row in rows[:limit]
                ]

            return await self._custom_news(client, config, secrets, ticker, limit)

    async def _custom_news(
        self,
        client: httpx.AsyncClient,
        config: dict[str, Any],
        secrets: dict[str, Any],
        ticker: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        endpoint = str(config.get("endpoint", "")).replace("{ticker}", ticker)
        if not endpoint:
            return []
        params = dict(config.get("query_params") or {})
        headers = dict(config.get("headers") or {})
        api_key = secrets.get("api_key", "")
        key_name = config.get("api_key_name", "apikey")
        if api_key:
            if config.get("api_key_location", "header") == "query":
                params[key_name] = api_key
            else:
                headers[key_name] = api_key
        response = await client.get(endpoint, params=params, headers=headers)
        response.raise_for_status()
        payload = response.json()
        mapping = config.get("mapping") or {}
        rows = _dig(payload, mapping.get("items", "articles"), [])
        if not isinstance(rows, list):
            return []
        results = []
        for row in rows[:limit]:
            if not isinstance(row, dict):
                continue
            results.append(
                {
                    "headline": str(_dig(row, mapping.get("headline", "title"), "")),
                    "summary": str(_dig(row, mapping.get("summary", "description"), "")),
                    "url": str(_dig(row, mapping.get("url", "url"), "")),
                    "source": str(_dig(row, mapping.get("source", "source"), "Custom API")),
                    "published_at": str(_dig(row, mapping.get("published_at", "published_at"), "")),
                }
            )
        return results


connected_sources = ConnectedSourceAdapter()
