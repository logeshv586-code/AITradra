"""Hyperliquid broker with fail-closed live execution and persistent paper trading."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

try:
    from eth_account import Account
    import hyperliquid.utils
    from hyperliquid.info import Info
    from hyperliquid.exchange import Exchange

    HAS_HL = True
except ImportError:
    HAS_HL = False
    Account = None
    Info = None
    Exchange = None

from brokers.broker_router import BaseBroker, Order, OrderSide, OrderType
from core.config import BASE_DIR, settings
from core.logger import get_logger
from core.trading_safety import get_execution_status

logger = get_logger(__name__)


class HyperliquidBroker(BaseBroker):
    """Hyperliquid integration with realistic paper fills and mandatory protection."""

    PAPER_STATE_PATH = BASE_DIR / "data" / "paper_hyperliquid.json"

    def __init__(
        self, private_key: Optional[str] = None, vault_address: Optional[str] = None
    ):
        self.private_key = private_key or settings.HYPERLIQUID_PRIVATE_KEY
        self.vault_address = vault_address or settings.HYPERLIQUID_VAULT_ADDRESS
        self.execution_status = get_execution_status(settings)
        super().__init__(paper=not self.execution_status["live_execution_allowed"])

        self.account = None
        self.exchange = None
        self.info = None
        self._paper_state = self._load_paper_state()

        if not HAS_HL:
            logger.warning("Hyperliquid SDK not installed. Public data and live broker are disabled.")
            return

        # Public market data is safe in both modes.
        self.info = Info(hyperliquid.utils.constants.MAINNET_API_URL, skip_ws=True)

        # Never construct a signing exchange merely because a key exists. The
        # centralized live gate must explicitly allow execution first.
        if self.execution_status["live_execution_allowed"]:
            try:
                self.account = Account.from_key(self.private_key)
                self.exchange = Exchange(
                    self.account,
                    hyperliquid.utils.constants.MAINNET_API_URL,
                    vault_address=self.vault_address,
                )
                logger.warning("Hyperliquid LIVE execution is explicitly enabled.")
            except Exception as exc:
                logger.error(f"Failed to initialize Hyperliquid signing client: {exc}")
                self.exchange = None
        else:
            logger.info(
                "Hyperliquid broker running in PAPER mode. Live blockers: %s",
                "; ".join(self.execution_status.get("blockers", [])),
            )

    # ------------------------------------------------------------------
    # Paper state and pricing
    # ------------------------------------------------------------------
    def _default_paper_state(self) -> dict[str, Any]:
        return {
            "cash": float(settings.PAPER_STARTING_BALANCE),
            "positions": {},
            "trades": [],
            "realized_pnl": 0.0,
            "fees_paid": 0.0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def _load_paper_state(self) -> dict[str, Any]:
        try:
            if self.PAPER_STATE_PATH.exists():
                payload = json.loads(self.PAPER_STATE_PATH.read_text(encoding="utf-8"))
                if isinstance(payload, dict) and "cash" in payload:
                    payload.setdefault("positions", {})
                    payload.setdefault("trades", [])
                    payload.setdefault("realized_pnl", 0.0)
                    payload.setdefault("fees_paid", 0.0)
                    return payload
        except Exception as exc:
            logger.warning(f"Could not load Hyperliquid paper state: {exc}")
        return self._default_paper_state()

    def _save_paper_state(self) -> None:
        try:
            self.PAPER_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            self.PAPER_STATE_PATH.write_text(
                json.dumps(self._paper_state, indent=2), encoding="utf-8"
            )
        except Exception as exc:
            logger.error(f"Could not persist Hyperliquid paper state: {exc}")

    async def _get_mid_price(self, ticker: str) -> float:
        if not self.info:
            return 0.0
        try:
            mids = await asyncio.to_thread(self.info.all_mids)
            return float(mids.get(ticker, 0) or 0)
        except Exception as exc:
            logger.warning(f"Mid-price lookup failed for {ticker}: {exc}")
            return 0.0

    async def _reference_price(self, order: Order) -> float:
        if order.reference_price and order.reference_price > 0:
            return float(order.reference_price)
        if order.order_type == OrderType.LIMIT and order.limit_price and order.limit_price > 0:
            return float(order.limit_price)
        return await self._get_mid_price(order.ticker)

    @staticmethod
    def _validate_protection(order: Order, reference_price: float) -> Optional[str]:
        if order.reduce_only:
            return None
        if settings.REQUIRE_PROTECTIVE_ORDERS and (
            not order.stop_loss or not order.take_profit
        ):
            return "Stop-loss and take-profit are required for every new position"
        if not order.stop_loss or not order.take_profit or reference_price <= 0:
            return None
        if order.side == OrderSide.BUY:
            if not (order.stop_loss < reference_price < order.take_profit):
                return "Invalid long protection: stop must be below entry and target above entry"
        else:
            if not (order.take_profit < reference_price < order.stop_loss):
                return "Invalid short protection: target must be below entry and stop above entry"
        return None

    def _paper_open(
        self, order: Order, fill_price: float, qty: float, fee: float
    ) -> Optional[str]:
        positions = self._paper_state["positions"]
        existing = positions.get(order.ticker)
        direction = 1 if order.side == OrderSide.BUY else -1
        notional = fill_price * qty
        leverage = max(1, min(int(order.leverage or 1), settings.MAX_LEVERAGE))
        margin = notional / leverage

        if margin + fee > self._paper_state["cash"]:
            return "Insufficient paper margin"

        if existing and existing.get("qty", 0) * direction > 0:
            old_qty_abs = abs(float(existing["qty"]))
            new_qty_abs = old_qty_abs + qty
            existing["entry_price"] = (
                old_qty_abs * float(existing["entry_price"]) + qty * fill_price
            ) / new_qty_abs
            existing["qty"] = direction * new_qty_abs
            existing["margin"] = float(existing.get("margin", 0)) + margin
            existing["leverage"] = leverage
            existing["stop_loss"] = order.stop_loss or existing.get("stop_loss")
            existing["take_profit"] = order.take_profit or existing.get("take_profit")
            existing["current_price"] = fill_price
        else:
            positions[order.ticker] = {
                "ticker": order.ticker,
                "qty": direction * qty,
                "entry_price": fill_price,
                "current_price": fill_price,
                "margin": margin,
                "leverage": leverage,
                "stop_loss": order.stop_loss,
                "take_profit": order.take_profit,
                "opened_at": datetime.now(timezone.utc).isoformat(),
            }

        self._paper_state["cash"] -= margin + fee
        return None

    def _paper_close(
        self, ticker: str, close_qty: float, fill_price: float, fee: float
    ) -> tuple[float, Optional[str]]:
        position = self._paper_state["positions"].get(ticker)
        if not position:
            return 0.0, "No paper position to close"

        signed_qty = float(position.get("qty", 0))
        abs_qty = abs(signed_qty)
        if abs_qty <= 0:
            return 0.0, "No paper position to close"

        qty = min(float(close_qty), abs_qty)
        entry = float(position.get("entry_price", 0))
        direction = 1 if signed_qty > 0 else -1
        realized = (fill_price - entry) * qty * direction
        margin_before = float(position.get("margin", 0))
        released_margin = margin_before * (qty / abs_qty)

        self._paper_state["cash"] += released_margin + realized - fee
        self._paper_state["realized_pnl"] += realized

        remaining = abs_qty - qty
        if remaining <= 1e-12:
            self._paper_state["positions"].pop(ticker, None)
        else:
            position["qty"] = direction * remaining
            position["margin"] = max(0.0, margin_before - released_margin)
            position["current_price"] = fill_price

        return realized, None

    async def _place_paper_order(self, order: Order) -> Dict:
        if order.qty <= 0:
            return {"status": "REJECTED", "reason": "Quantity must be positive", "paper": True}

        reference = await self._reference_price(order)
        if reference <= 0:
            return {
                "status": "REJECTED",
                "reason": "Live market reference price is unavailable",
                "paper": True,
            }

        protection_error = self._validate_protection(order, reference)
        if protection_error:
            return {"status": "REJECTED", "reason": protection_error, "paper": True}

        slippage = settings.PAPER_SLIPPAGE_BPS / 10_000
        fill_price = reference * (1 + slippage if order.side == OrderSide.BUY else 1 - slippage)
        requested_qty = float(order.qty)
        existing = self._paper_state["positions"].get(order.ticker)
        existing_qty = float(existing.get("qty", 0)) if existing else 0.0
        order_direction = 1 if order.side == OrderSide.BUY else -1
        fee_rate = settings.PAPER_FEE_BPS / 10_000
        total_fee = 0.0
        realized = 0.0

        if order.reduce_only:
            if not existing or existing_qty * order_direction >= 0:
                return {
                    "status": "REJECTED",
                    "reason": "Reduce-only order does not reduce the existing position",
                    "paper": True,
                }
            close_qty = min(requested_qty, abs(existing_qty))
            total_fee = fill_price * close_qty * fee_rate
            realized, error = self._paper_close(order.ticker, close_qty, fill_price, total_fee)
            if error:
                return {"status": "REJECTED", "reason": error, "paper": True}
        elif existing and existing_qty * order_direction < 0:
            close_qty = min(requested_qty, abs(existing_qty))
            close_fee = fill_price * close_qty * fee_rate
            realized, error = self._paper_close(order.ticker, close_qty, fill_price, close_fee)
            if error:
                return {"status": "REJECTED", "reason": error, "paper": True}
            total_fee += close_fee
            remainder = requested_qty - close_qty
            if remainder > 1e-12:
                open_fee = fill_price * remainder * fee_rate
                error = self._paper_open(order, fill_price, remainder, open_fee)
                if error:
                    # The close is intentionally kept; do not invent leverage to reopen.
                    self._paper_state["fees_paid"] += total_fee
                    self._save_paper_state()
                    return {
                        "status": "PARTIALLY_FILLED",
                        "reason": error,
                        "closed_qty": close_qty,
                        "paper": True,
                    }
                total_fee += open_fee
        else:
            total_fee = fill_price * requested_qty * fee_rate
            error = self._paper_open(order, fill_price, requested_qty, total_fee)
            if error:
                return {"status": "REJECTED", "reason": error, "paper": True}

        self._paper_state["fees_paid"] += total_fee
        trade = {
            "order_id": f"PAPER-HL-{len(self._paper_state['trades']) + 1}",
            "status": "FILLED",
            "paper": True,
            "broker": "hyperliquid-paper",
            "ticker": order.ticker,
            "side": order.side.value,
            "qty": requested_qty,
            "reference_price": round(reference, 8),
            "fill_price": round(fill_price, 8),
            "fee": round(total_fee, 8),
            "realized_pnl": round(realized, 8),
            "leverage": max(1, min(int(order.leverage or 1), settings.MAX_LEVERAGE)),
            "reduce_only": order.reduce_only,
            "stop_loss": order.stop_loss,
            "take_profit": order.take_profit,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._paper_state["trades"].append(trade)
        self._paper_state["trades"] = self._paper_state["trades"][-1000:]
        self._save_paper_state()
        logger.info(
            "[PAPER-HL] %s %.6f %s @ %.4f fee=%.4f",
            order.side.value,
            requested_qty,
            order.ticker,
            fill_price,
            total_fee,
        )
        return trade

    # ------------------------------------------------------------------
    # Public/account state
    # ------------------------------------------------------------------
    async def get_balance(self) -> Dict:
        if self.paper:
            positions = await self.get_positions()
            margin = sum(float(pos.get("margin", 0)) for pos in positions)
            unrealized = sum(float(pos.get("unrealized_pnl", 0)) for pos in positions)
            cash = float(self._paper_state.get("cash", 0))
            return {
                "total": cash + margin + unrealized,
                "cash": cash,
                "available": cash,
                "withdrawable": cash,
                "margin_used": margin,
                "unrealized_pnl": unrealized,
                "realized_pnl": float(self._paper_state.get("realized_pnl", 0)),
                "fees_paid": float(self._paper_state.get("fees_paid", 0)),
                "paper": True,
            }

        address = self.vault_address or (
            self.account.address if self.account is not None else None
        )
        if not address or not self.info:
            return {"total": 0.0, "available": 0.0, "cash": 0.0}

        try:
            user_state = await asyncio.to_thread(self.info.user_state, address)
            return {
                "total": float(user_state.get("marginSummary", {}).get("accountValue", 0)),
                "withdrawable": float(user_state.get("withdrawable", 0)),
                "cash": float(user_state.get("withdrawable", 0)),
                "available": float(user_state.get("withdrawable", 0)),
                "paper": False,
            }
        except Exception as exc:
            logger.error(f"Error fetching Hyperliquid balance: {exc}")
            return {"total": 0.0, "available": 0.0, "cash": 0.0, "error": str(exc)}

    async def get_positions(self) -> List[Dict]:
        if self.paper:
            positions = []
            mids: dict[str, Any] = {}
            if self.info:
                try:
                    mids = await asyncio.to_thread(self.info.all_mids)
                except Exception:
                    mids = {}
            dirty = False
            for ticker, raw in list(self._paper_state.get("positions", {}).items()):
                qty = float(raw.get("qty", 0))
                if abs(qty) <= 1e-12:
                    continue
                entry = float(raw.get("entry_price", 0))
                mark = float(mids.get(ticker, 0) or raw.get("current_price", entry) or entry)
                if mark != raw.get("current_price"):
                    raw["current_price"] = mark
                    dirty = True
                unrealized = (mark - entry) * abs(qty) * (1 if qty > 0 else -1)
                positions.append(
                    {
                        **raw,
                        "ticker": ticker,
                        "qty": qty,
                        "entry_price": entry,
                        "current_price": mark,
                        "unrealized_pnl": unrealized,
                        "unrealized_pnl_pct": (
                            unrealized / max(abs(qty) * entry, 1e-12)
                        ),
                        "paper": True,
                    }
                )
            if dirty:
                self._save_paper_state()
            return positions

        address = self.vault_address or (
            self.account.address if self.account is not None else None
        )
        if not address or not self.info:
            return []

        try:
            user_state = await asyncio.to_thread(self.info.user_state, address)
            positions = []
            for item in user_state.get("assetPositions", []):
                position = item.get("position", {})
                qty = float(position.get("szi", 0) or 0)
                if qty == 0:
                    continue
                entry = float(position.get("entryPx", 0) or 0)
                unrealized = float(position.get("unrealizedPnl", 0) or 0)
                positions.append(
                    {
                        "ticker": position.get("coin"),
                        "qty": qty,
                        "entry_price": entry,
                        "unrealized_pnl": unrealized,
                        "unrealized_pnl_pct": unrealized / max(abs(qty) * entry, 1e-12),
                        "leverage": position.get("leverage", {}),
                        "paper": False,
                    }
                )
            return positions
        except Exception as exc:
            logger.error(f"Error fetching Hyperliquid positions: {exc}")
            return []

    # ------------------------------------------------------------------
    # Protective orders and execution
    # ------------------------------------------------------------------
    async def process_protective_orders(
        self, ticker: str, mark_price: Optional[float] = None
    ) -> Optional[Dict]:
        """Execute paper SL/TP triggers. Live triggers are resting on exchange."""
        if not self.paper:
            return None
        position = self._paper_state.get("positions", {}).get(ticker)
        if not position:
            return None

        price = float(mark_price or 0) or await self._get_mid_price(ticker)
        if price <= 0:
            return None

        qty = float(position.get("qty", 0))
        stop = float(position.get("stop_loss", 0) or 0)
        target = float(position.get("take_profit", 0) or 0)
        trigger = None
        if qty > 0:
            if stop and price <= stop:
                trigger = "STOP_LOSS"
            elif target and price >= target:
                trigger = "TAKE_PROFIT"
        elif qty < 0:
            if stop and price >= stop:
                trigger = "STOP_LOSS"
            elif target and price <= target:
                trigger = "TAKE_PROFIT"

        if not trigger:
            return None

        result = await self.place_order(
            Order(
                ticker=ticker,
                side=OrderSide.SELL if qty > 0 else OrderSide.BUY,
                qty=abs(qty),
                order_type=OrderType.MARKET,
                reduce_only=True,
                reference_price=price,
            )
        )
        result["trigger"] = trigger
        return result

    @staticmethod
    def _extract_order_id(result: dict) -> str:
        try:
            status = result.get("response", {}).get("data", {}).get("statuses", [{}])[0]
            for key in ("resting", "filled"):
                payload = status.get(key, {}) if isinstance(status, dict) else {}
                if payload.get("oid") is not None:
                    return str(payload["oid"])
        except Exception:
            pass
        return "unknown"

    async def _place_live_protection(self, order: Order) -> dict:
        if not self.exchange:
            return {"status": "ERROR", "error": "Signing exchange is unavailable"}

        close_is_buy = order.side == OrderSide.SELL
        requests = [
            {
                "coin": order.ticker,
                "is_buy": close_is_buy,
                "sz": order.qty,
                "limit_px": float(order.take_profit),
                "order_type": {
                    "trigger": {
                        "triggerPx": float(order.take_profit),
                        "isMarket": True,
                        "tpsl": "tp",
                    }
                },
                "reduce_only": True,
            },
            {
                "coin": order.ticker,
                "is_buy": close_is_buy,
                "sz": order.qty,
                "limit_px": float(order.stop_loss),
                "order_type": {
                    "trigger": {
                        "triggerPx": float(order.stop_loss),
                        "isMarket": True,
                        "tpsl": "sl",
                    }
                },
                "reduce_only": True,
            },
        ]
        return await asyncio.to_thread(
            self.exchange.bulk_orders, requests, grouping="positionTpsl"
        )

    async def place_order(self, order: Order) -> Dict:
        """Place a paper or live order. New live positions require exchange-side TP/SL."""
        if self.paper:
            return await self._place_paper_order(order)

        # Re-evaluate every order so a runtime settings change cannot bypass the gate.
        current_status = get_execution_status(settings)
        if not current_status["live_execution_allowed"]:
            return {
                "status": "REJECTED",
                "error": "Live execution safety gate is closed",
                "blockers": current_status.get("blockers", []),
            }
        if not self.exchange:
            return {"status": "ERROR", "error": "Live exchange is unavailable"}
        if order.qty <= 0:
            return {"status": "REJECTED", "reason": "Quantity must be positive"}

        reference = await self._reference_price(order)
        protection_error = self._validate_protection(order, reference)
        if protection_error:
            return {"status": "REJECTED", "reason": protection_error}

        try:
            if order.reduce_only:
                if order.order_type != OrderType.MARKET:
                    return {
                        "status": "REJECTED",
                        "reason": "Live reduce-only execution currently supports market close only",
                    }
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
                return {
                    "status": "REJECTED",
                    "reason": "Protected live entries currently require market execution",
                }

            leverage = max(1, min(int(order.leverage or 1), settings.MAX_LEVERAGE))
            await asyncio.to_thread(
                self.exchange.update_leverage, leverage, order.ticker, True
            )
            entry_result = await asyncio.to_thread(
                self.exchange.market_open,
                order.ticker,
                order.side == OrderSide.BUY,
                order.qty,
                None,
                settings.HYPERLIQUID_MAX_SLIPPAGE_PCT,
            )
            if entry_result.get("status") != "ok":
                return {"status": "ERROR", "error": str(entry_result), "broker": "hyperliquid"}

            protection_result = await self._place_live_protection(order)
            if protection_result.get("status") != "ok":
                logger.critical(
                    "Protective order placement failed for %s; flattening the new position immediately.",
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
                    "error": "Entry filled but TP/SL placement failed; emergency close submitted",
                    "entry_order_id": self._extract_order_id(entry_result),
                    "protection_result": protection_result,
                    "rollback_status": rollback.get("status"),
                    "broker": "hyperliquid",
                }

            return {
                "status": "FILLED",
                "order_id": self._extract_order_id(entry_result),
                "broker": "hyperliquid",
                "paper": False,
                "protected": True,
                "stop_loss": order.stop_loss,
                "take_profit": order.take_profit,
                "leverage": leverage,
            }
        except Exception as exc:
            logger.error(f"Hyperliquid order failed: {exc}", exc_info=True)
            return {"status": "ERROR", "error": str(exc), "broker": "hyperliquid"}

    async def get_candles(
        self, ticker: str, interval: str = "5m", limit: int = 100
    ) -> List[Dict]:
        """Fetch candles in chronological order for indicator calculations."""
        if not self.info:
            return []
        try:
            import time

            interval_ms = {
                "1m": 60_000,
                "5m": 300_000,
                "15m": 900_000,
                "1h": 3_600_000,
                "4h": 14_400_000,
                "1d": 86_400_000,
            }.get(interval, 300_000)
            end_time = int(time.time() * 1000)
            start_time = end_time - (limit * interval_ms)
            candles = await asyncio.to_thread(
                self.info.candles_snapshot, ticker, interval, start_time, end_time
            )
            formatted = [
                {
                    "timestamp": int(c["t"]),
                    "open": float(c["o"]),
                    "high": float(c["h"]),
                    "low": float(c["l"]),
                    "close": float(c["c"]),
                    "volume": float(c["v"]),
                }
                for c in candles
            ]
            return sorted(formatted, key=lambda row: row["timestamp"])
        except Exception as exc:
            logger.error(f"Error fetching candles for {ticker}: {exc}")
            return []
