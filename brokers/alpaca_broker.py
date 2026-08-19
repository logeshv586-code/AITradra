"""
ALPACA BROKER ADAPTER — safe execution routing for Alpaca Paper and Live trading.

Enforces AITradra safety model:
- Paper mode is the mandatory default (https://paper-api.alpaca.markets/v2).
- Live mode (https://api.alpaca.markets/v2) is fail-closed unless credentials & explicit live config are set.
- New entries require fresh price reference, qty > 0, stop-loss, and take-profit.
- Reduce-only exits bypass entry-only SL/TP requirements to allow risk reduction.
- API credentials are never logged or exposed in responses.
"""

from typing import Any
import httpx

from core.logger import get_logger
from brokers.broker_router import BaseBroker, Order, OrderSide, OrderType

logger = get_logger(__name__)

PAPER_BASE_URL = "https://paper-api.alpaca.markets/v2"
LIVE_BASE_URL = "https://api.alpaca.markets/v2"


class AlpacaBroker(BaseBroker):
    def __init__(
        self,
        api_key: str = "",
        secret_key: str = "",
        paper: bool = True,
        enable_live_trading: bool = False,
    ):
        super().__init__(paper=paper)
        self.api_key = api_key
        self.secret_key = secret_key
        self.enable_live_trading = enable_live_trading
        self.timeout = httpx.Timeout(12.0, connect=6.0)

    def _get_base_url(self) -> str:
        if self.paper:
            return PAPER_BASE_URL
        if not self.enable_live_trading:
            raise ValueError("Live trading is fail-closed and not explicitly enabled server-side")
        return LIVE_BASE_URL

    def _get_headers(self) -> dict[str, str]:
        if not self.api_key or not self.secret_key:
            raise ValueError("Missing Alpaca API credentials")
        return {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.secret_key,
            "Content-Type": "application/json",
        }

    async def place_order(self, order: Order) -> dict[str, Any]:
        """Places an order with safety validation."""
        if not self.api_key or not self.secret_key:
            return {
                "status": "REJECTED",
                "reason": "Missing Alpaca API credentials",
                "paper": self.paper,
            }

        if not self.paper and not self.enable_live_trading:
            return {
                "status": "REJECTED",
                "reason": "Live trading path is fail-closed unless explicitly enabled",
                "paper": False,
            }

        if order.qty <= 0:
            return {
                "status": "REJECTED",
                "reason": "Order quantity must be positive",
                "paper": self.paper,
            }

        # Entry order safety validations (reduce_only exits bypass entry checks)
        if not order.reduce_only:
            ref_price = order.reference_price or order.limit_price or 0.0
            if ref_price <= 0:
                return {
                    "status": "REJECTED",
                    "reason": "New entry requires a fresh, positive reference price",
                    "paper": self.paper,
                }
            if not order.stop_loss or order.stop_loss <= 0:
                return {
                    "status": "REJECTED",
                    "reason": "New entry requires an explicit stop-loss level",
                    "paper": self.paper,
                }
            if not order.take_profit or order.take_profit <= 0:
                return {
                    "status": "REJECTED",
                    "reason": "New entry requires an explicit take-profit level",
                    "paper": self.paper,
                }

        try:
            base_url = self._get_base_url()
            headers = self._get_headers()

            payload = {
                "symbol": order.ticker.upper(),
                "qty": str(order.qty),
                "side": order.side.value,
                "type": order.order_type.value,
                "time_in_force": "gtc",
            }

            if order.order_type == OrderType.LIMIT and order.limit_price:
                payload["limit_price"] = str(order.limit_price)

            if order.reduce_only:
                payload["type"] = "market"

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(f"{base_url}/orders", json=payload, headers=headers)
                res.raise_for_status()
                data = res.json()
                return {
                    "order_id": data.get("id", "unknown"),
                    "status": data.get("status", "submitted").upper(),
                    "ticker": order.ticker.upper(),
                    "side": order.side.value,
                    "qty": order.qty,
                    "broker": "alpaca",
                    "paper": self.paper,
                }
        except httpx.HTTPStatusError as exc:
            logger.error(f"[AlpacaBroker] HTTP error: {exc.response.status_code}")
            return {
                "status": "ERROR",
                "reason": f"Alpaca API HTTP {exc.response.status_code}",
                "paper": self.paper,
            }
        except Exception as exc:
            logger.error(f"[AlpacaBroker] Execution error: {exc}")
            return {
                "status": "ERROR",
                "reason": str(exc),
                "paper": self.paper,
            }

    async def get_positions(self) -> list[dict[str, Any]]:
        if not self.api_key or not self.secret_key:
            return []
        try:
            base_url = self._get_base_url()
            headers = self._get_headers()
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(f"{base_url}/positions", headers=headers)
                res.raise_for_status()
                data = res.json()
                return [
                    {
                        "ticker": item.get("symbol"),
                        "qty": float(item.get("qty", 0)),
                        "entry_price": float(item.get("avg_entry_price", 0)),
                    }
                    for item in data
                ]
        except Exception as exc:
            logger.warning(f"[AlpacaBroker] Failed to fetch positions: {exc}")
            return []

    async def get_balance(self) -> dict[str, Any]:
        if not self.api_key or not self.secret_key:
            return {"cash": 0.0, "buying_power": 0.0, "paper": self.paper}
        try:
            base_url = self._get_base_url()
            headers = self._get_headers()
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(f"{base_url}/account", headers=headers)
                res.raise_for_status()
                data = res.json()
                return {
                    "cash": float(data.get("cash", 0)),
                    "buying_power": float(data.get("buying_power", 0)),
                    "portfolio_value": float(data.get("portfolio_value", 0)),
                    "paper": self.paper,
                }
        except Exception as exc:
            logger.warning(f"[AlpacaBroker] Failed to fetch balance: {exc}")
            return {"cash": 0.0, "buying_power": 0.0, "paper": self.paper}
