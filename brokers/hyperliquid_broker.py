"""
HYPERLIQUID BROKER — Integration with Hyperliquid SDK.
Supports Crypto and HIP-3 assets (Stocks, Commodities, etc.).
"""

import os
import asyncio
from typing import Optional, List, Dict
from eth_account import Account
import hyperliquid.utils
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from brokers.broker_router import BaseBroker, Order, OrderSide, OrderType
from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)


class HyperliquidBroker(BaseBroker):
    """
    Broker implementation for Hyperliquid.
    Uses hyperliquid-python-sdk for interaction.
    """

    def __init__(
        self, private_key: Optional[str] = None, vault_address: Optional[str] = None
    ):
        super().__init__(paper=settings.PAPER_TRADE_MODE)
        self.private_key = private_key or settings.HYPERLIQUID_PRIVATE_KEY
        self.vault_address = vault_address or settings.HYPERLIQUID_VAULT_ADDRESS

        if not self.private_key:
            logger.warning(
                "Hyperliquid private key not provided. Broker will operate in observation mode only."
            )
            self.exchange = None
        else:
            self.account = Account.from_key(self.private_key)
            self.exchange = Exchange(
                self.account,
                hyperliquid.utils.constants.MAINNET_API_URL,
                vault_address=self.vault_address,
            )

        self.info = Info(hyperliquid.utils.constants.MAINNET_API_URL, skip_ws=True)

    async def get_balance(self) -> Dict:
        """Fetch account balance (USDC in Hyperliquid)."""
        if not self.vault_address:
            # Fallback to signing account address if no vault
            address = self.account.address if hasattr(self, "account") else None
        else:
            address = self.vault_address

        if not address:
            return {"total": 0.0, "available": 0.0}

        try:
            # Info methods are synchronous in the SDK, wrapping in to_thread
            user_state = await asyncio.to_thread(self.info.user_state, address)
            margin_summary = user_state.get("withdrawable", 0)
            return {
                "total": float(
                    user_state.get("marginSummary", {}).get("accountValue", 0)
                ),
                "withdrawable": float(user_state.get("withdrawable", 0)),
                "cash": float(user_state.get("withdrawable", 0)),
            }
        except Exception as e:
            logger.error(f"Error fetching Hyperliquid balance: {e}")
            return {"total": 0.0, "error": str(e)}

    async def get_positions(self) -> List[Dict]:
        """Fetch current open positions."""
        address = self.vault_address or (
            self.account.address if hasattr(self, "account") else None
        )
        if not address:
            return []

        try:
            user_state = await asyncio.to_thread(self.info.user_state, address)
            positions = []
            for pos in user_state.get("assetPositions", []):
                p = pos.get("position", {})
                if float(p.get("szi", 0)) != 0:
                    positions.append(
                        {
                            "ticker": p.get("coin"),
                            "qty": float(p.get("szi", 0)),
                            "entry_price": float(p.get("entryPx", 0)),
                            "unrealized_pnl": float(p.get("unrealizedPnl", 0)),
                            "limit_price": float(p.get("entryPx", 0)),  # Fallback
                        }
                    )
            return positions
        except Exception as e:
            logger.error(f"Error fetching Hyperliquid positions: {e}")
            return []

    async def place_order(self, order: Order) -> Dict:
        """Place an order (Market or Limit)."""
        if self.paper:
            logger.info(
                f"[PAPER] Hyperliquid Order: {order.side.value} {order.qty} {order.ticker}"
            )
            return {"status": "FILLED", "order_id": "PAPER_HL_123", "paper": True}

        if not self.exchange:
            return {"status": "ERROR", "error": "No private key provided"}

        try:
            is_buy = order.side == OrderSide.BUY
            # Hyperliquid uses 'order_type' in its own way, we'll map MARKET to a high/low slippage lid
            # or just use their dedicated market open helper.

            # Note: For simplicity, we use market orders for now, matching the ref repo's likely behavior
            # if order_type is MARKET.

            if order.order_type == OrderType.MARKET:
                # Market order implementation
                # The SDK might need a specific helper or just a limit order with slippage
                result = await asyncio.to_thread(
                    self.exchange.market_open,
                    order.ticker,
                    is_buy,
                    order.qty,
                    None,  # Slippage px
                )
            else:
                # Limit order
                result = await asyncio.to_thread(
                    self.exchange.order,
                    order.ticker,
                    is_buy,
                    order.qty,
                    order.limit_price,
                    {"limit": {"tif": "Gtc"}},
                )

            if result.get("status") == "ok":
                return {
                    "status": "FILLED",
                    "order_id": result.get("response", {})
                    .get("data", {})
                    .get("statuses", [{}])[0]
                    .get("resting", {})
                    .get("oid", "unknown"),
                    "broker": "hyperliquid",
                }
            else:
                return {"status": "ERROR", "error": str(result)}

        except Exception as e:
            logger.error(f"Hyperliquid order failed: {e}")
            return {"status": "ERROR", "error": str(e)}

    async def get_candles(
        self, ticker: str, interval: str = "5m", limit: int = 100
    ) -> List[Dict]:
        """Fetch historical candle data for TA indicators."""
        try:
            import time

            end_time = int(time.time() * 1000)
            start_time = (
                end_time - (limit * 60 * 1000)
                if interval == "5m"
                else end_time - (limit * 60 * 1000)
            )

            candles = await asyncio.to_thread(
                self.info.candles_snapshot, ticker, interval, start_time, end_time
            )
            formatted = []
            for c in candles:
                formatted.append(
                    {
                        "timestamp": c["t"],
                        "open": float(c["o"]),
                        "high": float(c["h"]),
                        "low": float(c["l"]),
                        "close": float(c["c"]),
                        "volume": float(c["v"]),
                    }
                )
            return formatted
        except Exception as e:
            logger.error(f"Error fetching candles for {ticker}: {e}")
            return []
