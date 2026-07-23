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
    """
    Simulates trades with REAL market prices — zero risk, honest P&L.

    Paper trading is the profitability proving ground: its numbers are only
    meaningful if fills happen at actual market prices. Orders therefore fill
    at the latest stored close for the ticker (limit price as fallback) and
    are REJECTED when no market price is known — never at a made-up price.
    Positions carry a cost basis so realized/unrealized P&L and win rate are
    measured exactly. Trades persist to the knowledge store, so the income
    record survives restarts.
    """

    STARTING_CASH = 100_000.0

    def __init__(self):
        super().__init__(paper=True)
        self.cash = self.STARTING_CASH
        self.positions: dict[str, dict] = {}   # ticker -> {"qty": float, "avg_price": float}
        self.trade_log: list = []
        self.realized_pnl = 0.0
        self._restore_state()

    # ── Market data + persistence ────────────────────────────────────────────

    @staticmethod
    def _market_price(ticker: str) -> Optional[float]:
        """Latest stored close for the ticker (collector keeps this fresh)."""
        try:
            from gateway.knowledge_store import knowledge_store
            bars = knowledge_store.get_ohlcv_history(ticker, days=7)
            if bars and bars[0].get("close"):
                return float(bars[0]["close"])
        except Exception as e:
            logger.debug(f"[PaperBroker] Price lookup failed for {ticker}: {e}")
        return None

    def _restore_state(self):
        """Rebuild cash/positions/P&L by replaying persisted paper trades."""
        try:
            from gateway.knowledge_store import knowledge_store
            for trade in knowledge_store.get_paper_trades(limit=10_000):
                self._apply_fill(
                    trade["ticker"], trade["side"], trade["qty"], trade["fill_price"]
                )
                self.trade_log.append(trade)
            if self.trade_log:
                logger.info(
                    f"[PaperBroker] Restored {len(self.trade_log)} trades — "
                    f"cash={self.cash:.2f} realized_pnl={self.realized_pnl:.2f}"
                )
        except Exception as e:
            logger.debug(f"[PaperBroker] No persisted state restored: {e}")

    def _apply_fill(self, ticker: str, side: str, qty: float, fill_price: float) -> float:
        """Apply a fill to cash/positions. Returns realized P&L for this fill."""
        realized = 0.0
        pos = self.positions.get(ticker, {"qty": 0.0, "avg_price": 0.0})
        if side == "buy":
            total_cost = pos["qty"] * pos["avg_price"] + qty * fill_price
            pos["qty"] += qty
            pos["avg_price"] = total_cost / pos["qty"] if pos["qty"] else 0.0
            self.cash -= qty * fill_price
        else:
            realized = (fill_price - pos["avg_price"]) * qty
            pos["qty"] -= qty
            if pos["qty"] <= 0:
                pos["avg_price"] = 0.0
            self.cash += qty * fill_price
            self.realized_pnl += realized
        self.positions[ticker] = pos
        return realized

    # ── Broker interface ─────────────────────────────────────────────────────

    async def place_order(self, order: Order) -> dict:
        fill_price = self._market_price(order.ticker) or order.limit_price
        if not fill_price or fill_price <= 0:
            return {
                "status": "REJECTED",
                "reason": f"No market price known for {order.ticker} — refusing fantasy fill",
            }

        if order.side == OrderSide.BUY:
            if fill_price * order.qty > self.cash:
                return {"status": "REJECTED", "reason": "Insufficient cash"}
        else:
            held = self.positions.get(order.ticker, {}).get("qty", 0.0)
            if order.qty > held:
                return {"status": "REJECTED", "reason": "Insufficient position"}

        realized = self._apply_fill(order.ticker, order.side.value, order.qty, fill_price)

        trade = {
            "order_id": f"PAPER-{len(self.trade_log)+1}",
            "status": "FILLED",
            "ticker": order.ticker,
            "side": order.side.value,
            "qty": order.qty,
            "fill_price": round(fill_price, 4),
            "realized_pnl": round(realized, 4),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "broker": "paper",
        }
        self.trade_log.append(trade)
        try:
            from gateway.knowledge_store import knowledge_store
            knowledge_store.store_paper_trade(trade)
        except Exception as e:
            logger.debug(f"[PaperBroker] Trade persistence skipped: {e}")
        logger.info(
            f"[PaperBroker] {order.side.value} {order.qty} {order.ticker} @ {fill_price:.2f}"
            + (f" (realized {realized:+.2f})" if order.side == OrderSide.SELL else "")
        )
        return trade

    async def get_positions(self) -> list:
        out = []
        for ticker, pos in self.positions.items():
            if pos["qty"] <= 0:
                continue
            mark = self._market_price(ticker) or pos["avg_price"]
            out.append({
                "ticker": ticker,
                "qty": pos["qty"],
                "avg_price": round(pos["avg_price"], 4),
                "mark_price": round(mark, 4),
                "unrealized_pnl": round((mark - pos["avg_price"]) * pos["qty"], 2),
            })
        return out

    async def get_balance(self) -> dict:
        positions = await self.get_positions()
        unrealized = sum(p["unrealized_pnl"] for p in positions)
        equity = self.cash + sum(p["mark_price"] * p["qty"] for p in positions)
        sells = [t for t in self.trade_log if t.get("side") == "sell"]
        wins = sum(1 for t in sells if t.get("realized_pnl", 0) > 0)
        return {
            "cash": round(self.cash, 2),
            "equity": round(equity, 2),
            "total_return_pct": round((equity - self.STARTING_CASH) / self.STARTING_CASH * 100, 3),
            "realized_pnl": round(self.realized_pnl, 2),
            "unrealized_pnl": round(unrealized, 2),
            "positions": len(positions),
            "trade_count": len(self.trade_log),
            "closed_trades": len(sells),
            "win_rate": round(wins / len(sells), 3) if sells else None,
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
        self.hyperliquid_broker = None

        if config.get("CCXT_EXCHANGE"):
            self.ccxt_broker = CCXTBroker(
                exchange_name=config["CCXT_EXCHANGE"],
                api_key=config.get("CCXT_API_KEY", ""),
                secret=config.get("CCXT_SECRET", ""),
                paper=config.get("PAPER_TRADING", True),
            )
        
        # Initialize Hyperliquid Broker
        from brokers.hyperliquid_broker import HyperliquidBroker
        self.hyperliquid_broker = HyperliquidBroker(
            private_key=config.get("HYPERLIQUID_PRIVATE_KEY"),
            vault_address=config.get("HYPERLIQUID_VAULT_ADDRESS")
        )

    async def execute(self, order: Order, asset_class: str = "equity") -> dict:
        if asset_class == "crypto":
            if self.hyperliquid_broker:
                 return await self.hyperliquid_broker.place_order(order)
            elif self.ccxt_broker:
                return await self.ccxt_broker.place_order(order)
        
        # Everything else goes to PaperBroker
        return await self.paper_broker.place_order(order)

    async def get_all_positions(self) -> dict:
        positions = {"paper": await self.paper_broker.get_positions()}
        if self.ccxt_broker:
            positions["ccxt"] = await self.ccxt_broker.get_positions()
        return positions
