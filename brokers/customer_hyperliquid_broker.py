"""Manual Hyperliquid broker for customer-confirmed real-money orders.

This deliberately does not share the autonomous authorization switch. It uses the
same fail-closed safety policy and the same exchange-side TP/SL protection rules,
but requires MANUAL_LIVE_TRADING_ENABLED on the server.
"""

from __future__ import annotations

import asyncio
from typing import Any

try:
    from eth_account import Account
    import hyperliquid.utils
    from hyperliquid.info import Info
    from hyperliquid.exchange import Exchange
    HAS_HL = True
except ImportError:
    Account = None
    Info = None
    Exchange = None
    HAS_HL = False

from brokers.broker_router import Order, OrderSide, OrderType
from brokers.hyperliquid_broker import HyperliquidBroker
from core.config import settings
from core.logger import get_logger
from core.trading_safety import get_execution_status

logger = get_logger(__name__)


class CustomerHyperliquidBroker(HyperliquidBroker):
    """Hyperliquid account adapter scoped to manually confirmed customer orders."""

    def __init__(self, private_key: str, vault_address: str | None = None):
        # Explicit placeholder prevents parent initialization from ever falling
        # back to the separate automation private key in settings.
        super().__init__(
            private_key="__manual_customer_broker_no_parent_signing__",
            vault_address=vault_address,
        )
        self.private_key = private_key
        self.vault_address = vault_address
        self.execution_status = get_execution_status(
            settings,
            purpose="manual",
            has_private_key=bool(private_key),
        )
        self.paper = not self.execution_status["live_execution_allowed"]
        self.account = None
        self.exchange = None

        if not HAS_HL:
            return
        if self.info is None:
            self.info = Info(hyperliquid.utils.constants.MAINNET_API_URL, skip_ws=True)

        if self.execution_status["live_execution_allowed"]:
            try:
                self.account = Account.from_key(private_key)
                self.exchange = Exchange(
                    self.account,
                    hyperliquid.utils.constants.MAINNET_API_URL,
                    vault_address=vault_address,
                )
            except Exception as exc:
                logger.error(f"Customer Hyperliquid signing client failed: {exc}")
                self.exchange = None
                self.paper = True

    async def get_balance(self) -> dict[str, Any]:
        if not self.execution_status["live_execution_allowed"]:
            return {
                "total": 0.0,
                "available": 0.0,
                "cash": 0.0,
                "paper": True,
                "blockers": self.execution_status.get("blockers", []),
            }
        return await super().get_balance()

    async def get_positions(self) -> list[dict[str, Any]]:
        if not self.execution_status["live_execution_allowed"]:
            return []
        return await super().get_positions()

    async def place_order(self, order: Order) -> dict[str, Any]:
        """Place only a manually authorized live order; never fall back to paper."""
        current_status = get_execution_status(
            settings,
            purpose="manual",
            has_private_key=bool(self.private_key),
        )
        if not current_status["live_execution_allowed"]:
            return {
                "status": "REJECTED",
                "error": "Manual live execution safety gate is closed",
                "blockers": current_status.get("blockers", []),
                "paper": True,
            }
        if not self.exchange:
            return {"status": "ERROR", "error": "Live exchange is unavailable", "paper": False}
        if order.qty <= 0:
            return {"status": "REJECTED", "reason": "Quantity must be positive", "paper": False}

        reference = await self._reference_price(order)
        protection_error = self._validate_protection(order, reference)
        if protection_error:
            return {"status": "REJECTED", "reason": protection_error, "paper": False}

        try:
            if order.reduce_only:
                if order.order_type != OrderType.MARKET:
                    return {"status": "REJECTED", "reason": "Reduce-only close must use market execution", "paper": False}
                result = await asyncio.to_thread(
                    self.exchange.market_close,
                    order.ticker,
                    order.qty,
                    None,
                    settings.HYPERLIQUID_MAX_SLIPPAGE_PCT,
                )
                return {
                    "status": "FILLED" if result.get("status") == "ok" else "ERROR",
                    "order_id": self._extract_order_id(result),
                    "broker": "hyperliquid",
                    "paper": False,
                    "raw_status": result.get("status"),
                }

            if order.order_type != OrderType.MARKET:
                return {"status": "REJECTED", "reason": "Protected live entries currently use market execution", "paper": False}

            leverage = max(1, min(int(order.leverage or 1), settings.MAX_LEVERAGE))
            await asyncio.to_thread(self.exchange.update_leverage, leverage, order.ticker, True)
            entry_result = await asyncio.to_thread(
                self.exchange.market_open,
                order.ticker,
                order.side == OrderSide.BUY,
                order.qty,
                None,
                settings.HYPERLIQUID_MAX_SLIPPAGE_PCT,
            )
            if entry_result.get("status") != "ok":
                return {"status": "ERROR", "error": str(entry_result), "broker": "hyperliquid", "paper": False}

            protection_result = await self._place_live_protection(order)
            if protection_result.get("status") != "ok":
                logger.critical(
                    "Customer protective order placement failed for %s; submitting emergency flatten.",
                    order.ticker,
                )
                rollback = await asyncio.to_thread(
                    self.exchange.market_close,
                    order.ticker,
                    order.qty,
                    None,
                    settings.HYPERLIQUID_MAX_SLIPPAGE_PCT,
                )
                return {
                    "status": "ROLLED_BACK",
                    "error": "Entry filled but stop/target placement failed; emergency close submitted",
                    "entry_order_id": self._extract_order_id(entry_result),
                    "protection_result": protection_result,
                    "rollback_status": rollback.get("status"),
                    "broker": "hyperliquid",
                    "paper": False,
                }

            return {
                "status": "FILLED",
                "order_id": self._extract_order_id(entry_result),
                "broker": "hyperliquid",
                "paper": False,
                "ticker": order.ticker,
                "side": order.side.value,
                "qty": order.qty,
                "leverage": leverage,
                "stop_loss": order.stop_loss,
                "take_profit": order.take_profit,
                "protection_status": "ACTIVE",
            }
        except Exception as exc:
            logger.error(f"Customer live order failed: {exc}", exc_info=True)
            return {"status": "ERROR", "error": str(exc), "broker": "hyperliquid", "paper": False}
