"""Resolve matured shadow decisions against later measured market prices.

This is forward evidence collection only. It cannot authorize funded execution.
The resolver uses the existing DataEngine so the stored outcome carries the real
source label used at resolution time.
"""

from __future__ import annotations

from typing import Any

from core.logger import get_logger
from self_improvement.shadow_trade_store import shadow_trade_store

logger = get_logger(__name__)


def _price(payload: dict[str, Any]) -> float:
    for key in ("px", "close", "price"):
        try:
            value = float(payload.get(key, 0) or 0)
        except (TypeError, ValueError):
            value = 0.0
        if value > 0:
            return value
    return 0.0


async def resolve_due_shadow_decisions(*, limit: int = 100) -> dict[str, Any]:
    """Resolve due shadow rows; unresolved rows remain pending on data failure."""
    due = shadow_trade_store.pending_due(limit=limit)
    if not due:
        return {
            "due": 0,
            "resolved": 0,
            "failed": 0,
            "execution_authority": False,
        }

    from gateway.data_engine import data_engine

    price_cache: dict[str, dict[str, Any]] = {}
    resolved = 0
    failed = 0
    errors: list[dict[str, str]] = []

    for row in due:
        ticker = str(row.get("ticker", "")).upper()
        if not ticker:
            failed += 1
            continue
        try:
            if ticker not in price_cache:
                payload = await data_engine.get_price_data(ticker, allow_scrape=True)
                price_cache[ticker] = payload if isinstance(payload, dict) else {}
            payload = price_cache[ticker]
            exit_price = _price(payload)
            if exit_price <= 0:
                raise ValueError("No usable measured price")
            shadow_trade_store.resolve(
                str(row["id"]),
                exit_price=exit_price,
                price_source=str(payload.get("source_used") or "unknown"),
            )
            resolved += 1
        except Exception as exc:
            failed += 1
            errors.append({"ticker": ticker, "error": type(exc).__name__})
            logger.debug("Shadow resolution skipped for %s: %s", ticker, exc)

    return {
        "due": len(due),
        "resolved": resolved,
        "failed": failed,
        "errors": errors[:20],
        "audit": shadow_trade_store.audit_chain(),
        "execution_authority": False,
    }
