"""
BROKER ROUTER — safe execution routing for paper and connected brokers.

Paper execution never invents a price. Callers must provide a market reference
price (or a limit price), which keeps simulations from silently filling at a
hard-coded value.
"""

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
    """Simple in-memory long-only equity simulator with realistic price requirements."""

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
                logger.warning(f"Paper price lookup failed for {order.ticker}: {exc}")
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
        logger.info(
            f"[PaperBroker] {order.side.value} {order.qty} {order.ticker} @ {fill_price:.6f} fee={fee:.4f}"
        )
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
    """Routes crypto orders through CCXT exchanges (Binance, Bybit, OKX)."""

    def __init__(self, exchange_name: str = "binance", api_key: str = "", secret: str = "", paper: bool = True):
        super().__init__(paper)
        self.exchange_name = exchange_name
        self.api_key = api_key
        self.secret = secret

    async def place_order(self, order: Order) -> dict:
        try:
            import ccxt.async_support as ccxt

            exchange_cls = getattr(ccxt, self.exchange_name)
            config = {"apiKey": self.api_key, "secret": self.secret}
            exchange = exchange_cls(config)
            if self.paper and hasattr(exchange, "set_sandbox_mode"):
                exchange.set_sandbox_mode(True)

            symbol = f"{order.ticker}/USDT" if "/" not in order.ticker else order.ticker
            params = {"reduceOnly": order.reduce_only} if order.reduce_only else {}
            if order.order_type == OrderType.MARKET:
                result = await exchange.create_order(symbol, "market", order.side.value, order.qty, params=params)
            else:
                result = await exchange.create_order(
                    symbol, "limit", order.side.value, order.qty, order.limit_price, params
                )

            await exchange.close()
            return {
                "order_id": result.get("id", "unknown"),
                "status": result.get("status", "unknown"),
                "broker": f"ccxt_{self.exchange_name}",
                "paper": self.paper,
            }
        except Exception as e:
            logger.error(f"CCXTBroker order failed: {e}")
            return {"status": "ERROR", "error": str(e)}

    async def get_positions(self) -> list:
        try:
            import ccxt.async_support as ccxt

            exchange = getattr(ccxt, self.exchange_name)({"apiKey": self.api_key, "secret": self.secret})
            balance = await exchange.fetch_balance()
            await exchange.close()
            return [
                {"ticker": k, "qty": v}
                for k, v in balance.get("total", {}).items()
                if isinstance(v, (int, float)) and v > 0
            ]
        except Exception:
            return []

    async def get_balance(self) -> dict:
        try:
            import ccxt.async_support as ccxt

            exchange = getattr(ccxt, self.exchange_name)({"apiKey": self.api_key, "secret": self.secret})
            balance = await exchange.fetch_balance()
            await exchange.close()
            return {"total": balance.get("total", {})}
        except Exception:
            return {"total": {}}


class BrokerRouter:
    """Routes orders to the correct broker based on asset class."""

    def __init__(self, config: dict | None = None):
        config = config or {}
        self.paper_broker = PaperBroker()
        self.ccxt_broker = None

        if config.get("CCXT_EXCHANGE"):
            self.ccxt_broker = CCXTBroker(
                exchange_name=config["CCXT_EXCHANGE"],
                api_key=config.get("CCXT_API_KEY", ""),
                secret=config.get("CCXT_SECRET", ""),
                paper=config.get("PAPER_TRADE_MODE", True),
            )

        from brokers.hyperliquid_broker import HyperliquidBroker

        self.hyperliquid_broker = HyperliquidBroker(
            private_key=config.get("HYPERLIQUID_PRIVATE_KEY"),
            vault_address=config.get("HYPERLIQUID_VAULT_ADDRESS"),
        )

    async def execute(self, order: Order, asset_class: str = "equity") -> dict:
        if asset_class == "crypto":
            if self.hyperliquid_broker:
                return await self.hyperliquid_broker.place_order(order)
            if self.ccxt_broker:
                return await self.ccxt_broker.place_order(order)
        return await self.paper_broker.place_order(order)

    async def get_all_positions(self) -> dict:
        positions = {"paper": await self.paper_broker.get_positions()}
        if self.ccxt_broker:
            positions["ccxt"] = await self.ccxt_broker.get_positions()
        if self.hyperliquid_broker:
            positions["hyperliquid"] = await self.hyperliquid_broker.get_positions()
        return positions
