"""Broker router with explicit, fail-closed execution venues.

Crypto execution never silently falls from one funded venue to another. Hyperliquid
remains the default venue; CCXT exchanges are used only when explicitly selected
and configured. Paper execution continues to require a real reference price.
"""

from __future__ import annotations

import os
from enum import Enum
from abc import ABC, abstractmethod
from typing import Optional, Callable, Awaitable
from dataclasses import dataclass
from datetime import datetime, timezone

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"


@dataclass
class Order:
    ticker: str
    side: OrderSide
    qty: float
    order_type: OrderType = OrderType.MARKET
    limit_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    leverage: int = 1
    reduce_only: bool = False
    reference_price: Optional[float] = None


class BaseBroker(ABC):
    def __init__(self, paper: bool = True):
        self.paper = paper

    @abstractmethod
    async def place_order(self, order: Order) -> dict: ...

    @abstractmethod
    async def get_positions(self) -> list: ...

    @abstractmethod
    async def get_balance(self) -> dict: ...


class PaperBroker(BaseBroker):
    """In-memory long-only equity simulator with explicit market references."""

    def __init__(self, price_resolver: Optional[Callable[[str], Awaitable[float]]] = None):
        super().__init__(paper=True)
        self.cash = float(settings.PAPER_STARTING_BALANCE)
        self.positions: dict[str, dict] = {}
        self.trade_log: list = []
        self.price_resolver = price_resolver

    async def _resolve_price(self, order: Order) -> float:
        if order.reference_price and order.reference_price > 0:
            return float(order.reference_price)
        if order.limit_price and order.limit_price > 0:
            return float(order.limit_price)
        if self.price_resolver:
            try:
                price = float(await self.price_resolver(order.ticker))
                if price > 0:
                    return price
            except Exception as exc:
                logger.warning("Paper price lookup failed for %s: %s", order.ticker, exc)
        return 0.0

    async def place_order(self, order: Order) -> dict:
        if order.qty <= 0:
            return {"status": "REJECTED", "reason": "Quantity must be positive", "paper": True}
        reference = await self._resolve_price(order)
        if reference <= 0:
            return {
                "status": "REJECTED",
                "reason": "Paper market price unavailable; provide a live reference price",
                "paper": True,
            }
        slip = settings.PAPER_SLIPPAGE_BPS / 10_000
        fill_price = reference * (1 + slip if order.side == OrderSide.BUY else 1 - slip)
        notional = fill_price * order.qty
        fee = notional * settings.PAPER_FEE_BPS / 10_000
        pos = self.positions.get(order.ticker, {"qty": 0.0, "avg_price": 0.0})
        if order.side == OrderSide.BUY:
            if notional + fee > self.cash:
                return {"status": "REJECTED", "reason": "Insufficient paper cash", "paper": True}
            new_qty = pos["qty"] + order.qty
            avg = ((pos["qty"] * pos["avg_price"]) + notional) / new_qty
            self.cash -= notional + fee
            self.positions[order.ticker] = {"qty": new_qty, "avg_price": avg}
        else:
            held = float(pos.get("qty", 0))
            if order.qty > held:
                return {"status": "REJECTED", "reason": "Insufficient paper position", "paper": True}
            self.cash += notional - fee
            remaining = held - order.qty
            if remaining <= 1e-12:
                self.positions.pop(order.ticker, None)
            else:
                pos["qty"] = remaining
                self.positions[order.ticker] = pos
        trade = {
            "order_id": f"PAPER-{len(self.trade_log) + 1}",
            "status": "FILLED",
            "ticker": order.ticker,
            "side": order.side.value,
            "qty": order.qty,
            "reference_price": round(reference, 8),
            "fill_price": round(fill_price, 8),
            "fee": round(fee, 8),
            "stop_loss": order.stop_loss,
            "take_profit": order.take_profit,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "broker": "paper",
            "paper": True,
        }
        self.trade_log.append(trade)
        return trade

    async def get_positions(self) -> list:
        return [
            {"ticker": ticker, "qty": data["qty"], "entry_price": data["avg_price"]}
            for ticker, data in self.positions.items()
            if data["qty"] > 0
        ]

    async def get_balance(self) -> dict:
        return {
            "cash": self.cash,
            "positions": len(self.positions),
            "trade_count": len(self.trade_log),
            "paper": True,
        }


class CCXTBroker(BaseBroker):
    """Explicit CCXT execution venue for Binance, Bybit, or OKX."""

    SUPPORTED_EXCHANGES = {"binance", "bybit", "okx"}

    def __init__(self, exchange_name: str = "binance", api_key: str = "", secret: str = "", paper: bool = True):
        super().__init__(paper)
        normalized = str(exchange_name or "binance").lower()
        if normalized not in self.SUPPORTED_EXCHANGES:
            raise ValueError(f"Unsupported CCXT exchange: {normalized}")
        self.exchange_name = normalized
        self.api_key = api_key
        self.secret = secret

    def _config(self) -> dict:
        return {
            "apiKey": self.api_key,
            "secret": self.secret,
            "enableRateLimit": True,
        }

    async def _exchange(self):
        import ccxt.async_support as ccxt

        exchange_cls = getattr(ccxt, self.exchange_name)
        exchange = exchange_cls(self._config())
        if self.paper and hasattr(exchange, "set_sandbox_mode"):
            try:
                exchange.set_sandbox_mode(True)
            except Exception as exc:
                await exchange.close()
                raise RuntimeError(
                    f"{self.exchange_name} sandbox mode is unavailable; refusing paper order"
                ) from exc
        return exchange

    @staticmethod
    def _symbol(ticker: str) -> str:
        raw = str(ticker).upper().replace("-USD", "").replace("-USDT", "")
        return raw if "/" in raw else f"{raw}/USDT"

    async def place_order(self, order: Order) -> dict:
        exchange = None
        try:
            exchange = await self._exchange()
            symbol = self._symbol(order.ticker)
            params = {"reduceOnly": True} if order.reduce_only else {}
            if order.order_type == OrderType.MARKET:
                result = await exchange.create_order(
                    symbol, "market", order.side.value, order.qty, None, params
                )
            else:
                if not order.limit_price or order.limit_price <= 0:
                    return {"status": "REJECTED", "reason": "Limit price is required", "broker": f"ccxt_{self.exchange_name}"}
                result = await exchange.create_order(
                    symbol,
                    "limit",
                    order.side.value,
                    order.qty,
                    order.limit_price,
                    params,
                )
            return {
                "order_id": result.get("id", "unknown"),
                "status": result.get("status", "unknown"),
                "broker": f"ccxt_{self.exchange_name}",
                "paper": self.paper,
            }
        except ImportError:
            return {
                "status": "ERROR",
                "error": "CCXT is not installed",
                "broker": f"ccxt_{self.exchange_name}",
            }
        except Exception as exc:
            logger.error("CCXTBroker order failed: %s", exc)
            return {"status": "ERROR", "error": str(exc), "broker": f"ccxt_{self.exchange_name}"}
        finally:
            if exchange is not None:
                try:
                    await exchange.close()
                except Exception:
                    pass

    async def get_positions(self) -> list:
        exchange = None
        try:
            exchange = await self._exchange()
            balance = await exchange.fetch_balance()
            return [
                {"ticker": key, "qty": value}
                for key, value in balance.get("total", {}).items()
                if isinstance(value, (int, float)) and value > 0
            ]
        except Exception:
            return []
        finally:
            if exchange is not None:
                try:
                    await exchange.close()
                except Exception:
                    pass

    async def get_balance(self) -> dict:
        exchange = None
        try:
            exchange = await self._exchange()
            balance = await exchange.fetch_balance()
            return {"total": balance.get("total", {}), "broker": f"ccxt_{self.exchange_name}"}
        except Exception as exc:
            return {"total": {}, "error": str(exc), "broker": f"ccxt_{self.exchange_name}"}
        finally:
            if exchange is not None:
                try:
                    await exchange.close()
                except Exception:
                    pass


class BrokerRouter:
    """Route orders to explicitly selected venues; never silently switch funded brokers."""

    def __init__(self, config: dict | None = None):
        config = config or {}
        self.paper_broker = PaperBroker()
        self.default_crypto_venue = str(
            config.get("CRYPTO_BROKER") or os.getenv("CRYPTO_BROKER", "hyperliquid")
        ).lower()
        ccxt_exchange = config.get("CCXT_EXCHANGE") or os.getenv("CCXT_EXCHANGE", "")
        self.ccxt_broker = None
        if ccxt_exchange:
            try:
                self.ccxt_broker = CCXTBroker(
                    exchange_name=str(ccxt_exchange),
                    api_key=str(config.get("CCXT_API_KEY") or os.getenv("CCXT_API_KEY", "")),
                    secret=str(config.get("CCXT_SECRET") or os.getenv("CCXT_SECRET", "")),
                    paper=bool(
                        config.get(
                            "PAPER_TRADE_MODE",
                            config.get("PAPER_TRADING", settings.PAPER_TRADE_MODE),
                        )
                    ),
                )
            except Exception as exc:
                logger.warning("CCXT venue disabled: %s", exc)

        from brokers.hyperliquid_broker import HyperliquidBroker

        self.hyperliquid_broker = HyperliquidBroker(
            private_key=config.get("HYPERLIQUID_PRIVATE_KEY"),
            vault_address=config.get("HYPERLIQUID_VAULT_ADDRESS"),
        )

    async def execute(
        self,
        order: Order,
        asset_class: str = "equity",
        *,
        venue: str | None = None,
    ) -> dict:
        if asset_class != "crypto":
            return await self.paper_broker.place_order(order)

        selected = str(venue or self.default_crypto_venue or "hyperliquid").lower()
        if selected == "hyperliquid":
            return await self.hyperliquid_broker.place_order(order)
        if selected in {"ccxt", "binance", "bybit", "okx"}:
            if self.ccxt_broker is None:
                return {
                    "status": "REJECTED",
                    "reason": "CCXT venue was selected but no CCXT exchange is configured",
                    "requested_venue": selected,
                }
            if selected not in {"ccxt", self.ccxt_broker.exchange_name}:
                return {
                    "status": "REJECTED",
                    "reason": f"Configured CCXT exchange is {self.ccxt_broker.exchange_name}, not {selected}",
                    "requested_venue": selected,
                }
            return await self.ccxt_broker.place_order(order)
        return {
            "status": "REJECTED",
            "reason": f"Unknown crypto execution venue: {selected}",
            "requested_venue": selected,
        }

    async def get_all_positions(self) -> dict:
        positions = {"paper": await self.paper_broker.get_positions()}
        if self.ccxt_broker:
            positions["ccxt"] = await self.ccxt_broker.get_positions()
        if self.hyperliquid_broker:
            positions["hyperliquid"] = await self.hyperliquid_broker.get_positions()
        return positions
