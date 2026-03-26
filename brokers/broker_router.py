"""
BROKER ROUTER — Claude Flow Infrastructure (100% OSS)
Routes trade execution through CCXT for crypto or paper simulation for equities.
Supports: CCXTBroker, PaperBroker, SimulationBroker.
Default: PAPER_TRADING=true — no real money.
"""

from enum import Enum
from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
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
    """Simulates trades in memory — zero risk. Default broker."""

    def __init__(self):
        super().__init__(paper=True)
        self.cash = 100_000.0
        self.positions: dict = {}
        self.trade_log: list = []

    async def place_order(self, order: Order) -> dict:
        # Simulate fill at current "price" (would need market data feed in production)
        fill_price = order.limit_price or 100.0  # Placeholder
        cost = fill_price * order.qty

        if order.side == OrderSide.BUY:
            if cost > self.cash:
                return {"status": "REJECTED", "reason": "Insufficient cash"}
            self.cash -= cost
            self.positions[order.ticker] = self.positions.get(order.ticker, 0) + order.qty
        else:
            held = self.positions.get(order.ticker, 0)
            if order.qty > held:
                return {"status": "REJECTED", "reason": "Insufficient position"}
            self.cash += cost
            self.positions[order.ticker] = held - order.qty

        trade = {
            "order_id": f"PAPER-{len(self.trade_log)+1}",
            "status": "FILLED",
            "ticker": order.ticker,
            "side": order.side.value,
            "qty": order.qty,
            "fill_price": fill_price,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "broker": "paper",
        }
        self.trade_log.append(trade)
        logger.info(f"[PaperBroker] {order.side.value} {order.qty} {order.ticker} @ {fill_price}")
        return trade

    async def get_positions(self) -> list:
        return [{"ticker": t, "qty": q} for t, q in self.positions.items() if q > 0]

    async def get_balance(self) -> dict:
        return {"cash": self.cash, "positions": len(self.positions), "trade_count": len(self.trade_log)}


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
            if self.paper:
                config["sandbox"] = True  # CCXT testnet mode
            exchange = exchange_cls(config)

            symbol = f"{order.ticker}/USDT" if "/" not in order.ticker else order.ticker

            if order.order_type == OrderType.MARKET:
                result = await exchange.create_order(symbol, "market", order.side.value, order.qty)
            else:
                result = await exchange.create_order(symbol, "limit", order.side.value, order.qty, order.limit_price)

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
            return [{"ticker": k, "qty": v["total"]} for k, v in balance.get("total", {}).items() if v.get("total", 0) > 0]
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

    def __init__(self, config: dict = None):
        config = config or {}
        self.paper_broker = PaperBroker()
        self.ccxt_broker = None

        if config.get("CCXT_EXCHANGE"):
            self.ccxt_broker = CCXTBroker(
                exchange_name=config["CCXT_EXCHANGE"],
                api_key=config.get("CCXT_API_KEY", ""),
                secret=config.get("CCXT_SECRET", ""),
                paper=config.get("PAPER_TRADING", True),
            )

    async def execute(self, order: Order, asset_class: str = "equity") -> dict:
        if asset_class == "crypto" and self.ccxt_broker:
            return await self.ccxt_broker.place_order(order)
        # Everything else goes to PaperBroker
        return await self.paper_broker.place_order(order)

    async def get_all_positions(self) -> dict:
        positions = {"paper": await self.paper_broker.get_positions()}
        if self.ccxt_broker:
            positions["ccxt"] = await self.ccxt_broker.get_positions()
        return positions
