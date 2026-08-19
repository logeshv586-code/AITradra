"""Customer-facing paper portfolio using live references plus configurable friction."""

import os
import json
import asyncio
from datetime import datetime
from typing import Dict, Optional

from core.config import settings
from core.logger import get_logger
from gateway.knowledge_store import knowledge_store

logger = get_logger(__name__)
DATA_FILE = os.path.join(os.path.dirname(__file__), "virtual_portfolio_data.json")


class SimulationEngine:
    def __init__(self, data_engine):
        self.data_engine = data_engine
        self.state = self._load_state()

    def _empty_state(self) -> Dict:
        return {
            "initialized": False,
            "initial_balance": 0.0,
            "total_balance": 0.0,
            "available_cash": 0.0,
            "invested_amount": 0.0,
            "positions": [],
            "history": [],
            "daily_profit_history": [],
            "fees_paid": 0.0,
            "realized_profit_loss": 0.0,
            "accuracy_metrics": {
                "total_trades": 0,
                "correct_predictions": 0,
                "accuracy_score": 0.0,
            },
            "execution_assumptions": {
                "slippage_bps": settings.PAPER_SLIPPAGE_BPS,
                "fee_bps": settings.PAPER_FEE_BPS,
            },
        }

    def _load_state(self) -> Dict:
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as handle:
                    state = json.load(handle)
                state.setdefault("initial_balance", state.get("total_balance", 0.0))
                state.setdefault("daily_profit_history", [])
                state.setdefault("fees_paid", 0.0)
                state.setdefault("realized_profit_loss", 0.0)
                state.setdefault(
                    "execution_assumptions",
                    {
                        "slippage_bps": settings.PAPER_SLIPPAGE_BPS,
                        "fee_bps": settings.PAPER_FEE_BPS,
                    },
                )
                return state
            except Exception as exc:
                logger.error(f"Failed to load virtual portfolio: {exc}")
        return self._empty_state()

    def _save_state(self):
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as handle:
                json.dump(self.state, handle, indent=2)
        except Exception as exc:
            logger.error(f"Failed to save virtual portfolio: {exc}")

    def _get_snapshot(self, ticker: str) -> Optional[Dict]:
        try:
            return knowledge_store.get_ticker_intelligence(ticker.upper())
        except Exception as exc:
            logger.warning(f"Failed to load intelligence snapshot for {ticker}: {exc}")
            return None

    async def _get_live_price(self, ticker: str) -> float:
        try:
            price_data = await self.data_engine.get_price_data(
                ticker.upper(), allow_scrape=True
            )
            price = float(price_data.get("px", 0) or 0)
            if price > 0:
                return price
        except Exception as exc:
            logger.warning(f"Data engine price fetch failed for {ticker}: {exc}")

        snapshot = self._get_snapshot(ticker)
        return float(((snapshot or {}).get("price_data") or {}).get("px", 0) or 0)

    @staticmethod
    def _fill_price(reference_price: float, side: str) -> float:
        slippage = settings.PAPER_SLIPPAGE_BPS / 10_000
        return reference_price * (1 + slippage if side == "BUY" else 1 - slippage)

    @staticmethod
    def _fee(notional: float) -> float:
        return notional * settings.PAPER_FEE_BPS / 10_000

    def _get_signal_context(self, ticker: str) -> Dict:
        snapshot = self._get_snapshot(ticker) or {}
        return {
            "recommendation": snapshot.get("recommendation", "HOLD"),
            "prediction_direction": snapshot.get("prediction_direction", "SIDEWAYS"),
            "confidence_score": snapshot.get("confidence_score", 0),
            "risk_level": snapshot.get("risk_level", "MEDIUM"),
            "primary_driver": snapshot.get("primary_driver", "technical"),
            "updated_at": snapshot.get("updated_at") or snapshot.get("as_of"),
        }

    def initialize_account(self, initial_balance: float):
        if initial_balance <= 0:
            raise ValueError("Starting balance must be greater than zero")
        self.state = self._empty_state()
        self.state.update(
            {
                "initialized": True,
                "initial_balance": float(initial_balance),
                "total_balance": float(initial_balance),
                "available_cash": float(initial_balance),
            }
        )
        self._save_state()
        return self.state

    async def get_status(self):
        metrics = self.state.setdefault(
            "accuracy_metrics",
            {"total_trades": 0, "correct_predictions": 0, "accuracy_score": 0.0},
        )
        if metrics.get("total_trades", 0) == 0:
            metrics["accuracy_score"] = 0.0
        if self.state.get("initialized"):
            return await self.calculate_live_portfolio()
        return self.state

    async def buy_stock(
        self,
        ticker: str,
        quantity: float,
        prediction: Optional[str] = None,
        monte_carlo_volatility: Optional[float] = None,
        confidence_score: Optional[float] = None,
    ):
        if not self.state.get("initialized"):
            raise ValueError("Practice account is not initialized")
        ticker = str(ticker or "").upper().strip()
        quantity = float(quantity or 0)
        if not ticker:
            raise ValueError("Enter a ticker symbol")
        if quantity <= 0:
            raise ValueError("Shares must be greater than zero")

        reference_price = await self._get_live_price(ticker)
        if reference_price <= 0:
            raise ValueError(f"A live market price is not available for {ticker}")
        fill_price = self._fill_price(reference_price, "BUY")
        signal_context = self._get_signal_context(ticker)

        # AI metadata may reduce a requested practice size but never increases what
        # the customer typed into the order form.
        scaling_factor = 1.0
        if confidence_score is not None:
            confidence = float(confidence_score or 0)
            scaling_factor = 1.0 if confidence >= 80 else 0.75 if confidence >= 60 else 0.5 if confidence >= 40 else 0.25
        quantity *= scaling_factor

        if monte_carlo_volatility is not None and float(monte_carlo_volatility or 0) > 0:
            volatility = float(monte_carlo_volatility)
            max_position_pct = max(0.02, min(settings.MAX_POSITION_PCT, 1.0 / (volatility + 1)))
            max_position_value = self.state["total_balance"] * max_position_pct
            quantity = min(quantity, max_position_value / fill_price)

        notional = quantity * fill_price
        fee = self._fee(notional)
        if notional + fee > self.state["available_cash"]:
            max_notional = self.state["available_cash"] / (1 + settings.PAPER_FEE_BPS / 10_000)
            quantity = max_notional / fill_price
            notional = quantity * fill_price
            fee = self._fee(notional)
        if quantity <= 0:
            raise ValueError("Not enough practice cash for this order")

        existing = next(
            (position for position in self.state["positions"] if position["ticker"] == ticker),
            None,
        )
        if existing:
            old_qty = float(existing["quantity"])
            total_qty = old_qty + quantity
            existing["buy_price"] = (
                float(existing["buy_price"]) * old_qty + fill_price * quantity
            ) / total_qty
            existing["quantity"] = total_qty
            existing["invested_value"] = total_qty * existing["buy_price"]
            existing["entry_fee"] = float(existing.get("entry_fee", 0)) + fee
            existing["prediction"] = prediction or signal_context["prediction_direction"]
            existing["signal_context"] = signal_context
        else:
            self.state["positions"].append(
                {
                    "ticker": ticker,
                    "buy_price": fill_price,
                    "quantity": quantity,
                    "invested_value": notional,
                    "entry_fee": fee,
                    "prediction": prediction or signal_context["prediction_direction"],
                    "signal_context": signal_context,
                    "timestamp": datetime.now().isoformat(),
                }
            )

        self.state["available_cash"] -= notional + fee
        self.state["fees_paid"] = float(self.state.get("fees_paid", 0)) + fee
        self.state["history"].append(
            {
                "type": "BUY",
                "ticker": ticker,
                "reference_price": reference_price,
                "price": fill_price,
                "amount": notional,
                "fee": fee,
                "quantity": quantity,
                "prediction_at_buy": prediction or signal_context["prediction_direction"],
                "signal_context": signal_context,
                "timestamp": datetime.now().isoformat(),
            }
        )
        self._save_state()
        return await self.calculate_live_portfolio()

    async def sell_stock(self, ticker: str, quantity_to_sell: Optional[float] = None):
        if not self.state.get("initialized"):
            raise ValueError("Practice account is not initialized")
        ticker = str(ticker or "").upper().strip()
        index = next(
            (i for i, position in enumerate(self.state["positions"]) if position["ticker"] == ticker),
            None,
        )
        if index is None:
            raise ValueError(f"No practice position found for {ticker}")

        position = self.state["positions"][index]
        held_qty = float(position["quantity"])
        requested = held_qty if quantity_to_sell is None else float(quantity_to_sell or 0)
        if requested <= 0:
            raise ValueError("Shares to sell must be greater than zero")
        sell_qty = min(requested, held_qty)
        fully_closed = sell_qty >= held_qty - 1e-12

        reference_price = await self._get_live_price(ticker)
        if reference_price <= 0:
            reference_price = float(position.get("current_price", position["buy_price"]) or 0)
        if reference_price <= 0:
            raise ValueError(f"A market price is not available for {ticker}")
        fill_price = self._fill_price(reference_price, "SELL")

        sale_value = sell_qty * fill_price
        exit_fee = self._fee(sale_value)
        entry_fee_total = float(position.get("entry_fee", 0) or 0)
        allocated_entry_fee = entry_fee_total * (sell_qty / held_qty)
        cost = sell_qty * float(position["buy_price"]) + allocated_entry_fee
        profit_loss = sale_value - exit_fee - cost

        metrics = self.state.setdefault(
            "accuracy_metrics",
            {"total_trades": 0, "correct_predictions": 0, "accuracy_score": 0.0},
        )
        metrics["total_trades"] += 1
        original_prediction = str(position.get("prediction", "SIDEWAYS")).upper()
        is_correct = (
            (original_prediction == "UP" and profit_loss > 0)
            or (original_prediction == "DOWN" and fill_price < float(position["buy_price"]))
            or (original_prediction in {"SIDEWAYS", "HOLD"} and abs(profit_loss / max(cost, 1e-12)) < 0.01)
        )
        if is_correct:
            metrics["correct_predictions"] += 1
        metrics["accuracy_score"] = (
            metrics["correct_predictions"] / metrics["total_trades"] * 100
        )

        self.state["available_cash"] += sale_value - exit_fee
        self.state["fees_paid"] = float(self.state.get("fees_paid", 0)) + exit_fee
        self.state["realized_profit_loss"] = float(
            self.state.get("realized_profit_loss", 0)
        ) + profit_loss

        if fully_closed:
            self.state["positions"].pop(index)
        else:
            position["quantity"] = held_qty - sell_qty
            position["invested_value"] = position["quantity"] * position["buy_price"]
            position["entry_fee"] = max(0.0, entry_fee_total - allocated_entry_fee)

        self.state["history"].append(
            {
                "type": "SELL",
                "ticker": ticker,
                "reference_price": reference_price,
                "price": fill_price,
                "amount": sale_value,
                "fee": exit_fee,
                "quantity": sell_qty,
                "profit_loss": profit_loss,
                "profit_loss_pct": round((profit_loss / cost) * 100, 2) if cost > 0 else 0,
                "signal_context": self._get_signal_context(ticker),
                "timestamp": datetime.now().isoformat(),
            }
        )
        self._save_state()
        return await self.calculate_live_portfolio()

    async def calculate_live_portfolio(self):
        if not self.state.get("initialized"):
            return self.state

        tickers = [position["ticker"] for position in self.state["positions"]]
        prices = await asyncio.gather(
            *[self._get_live_price(ticker) for ticker in tickers],
            return_exceptions=True,
        )
        price_map = {
            ticker: float(price) if isinstance(price, (int, float)) and price > 0 else 0.0
            for ticker, price in zip(tickers, prices)
        }

        current_positions_value = 0.0
        unrealized = 0.0
        for position in self.state["positions"]:
            current_price = price_map.get(position["ticker"], 0) or float(position["buy_price"])
            position["current_price"] = current_price
            position["current_value"] = current_price * float(position["quantity"])
            position["profit_loss"] = (
                position["current_value"]
                - float(position["invested_value"])
                - float(position.get("entry_fee", 0) or 0)
            )
            position["profit_loss_pct"] = (
                round(
                    position["profit_loss"]
                    / max(float(position["invested_value"]) + float(position.get("entry_fee", 0) or 0), 1e-12)
                    * 100,
                    2,
                )
            )
            position["signal_context"] = self._get_signal_context(position["ticker"])
            current_positions_value += position["current_value"]
            unrealized += position["profit_loss"]

        self.state["invested_amount"] = current_positions_value
        self.state["total_balance"] = self.state["available_cash"] + current_positions_value
        initial = float(self.state.get("initial_balance", 0) or 0)
        self.state["total_profit_loss"] = self.state["total_balance"] - initial
        self.state["unrealized_profit_loss"] = unrealized
        self.state["profit_loss_percentage"] = (
            round(self.state["total_profit_loss"] / initial * 100, 2) if initial > 0 else 0.0
        )
        self.state["mode"] = "practice"
        self.state["uses_real_money"] = False
        self.state["execution_assumptions"] = {
            "slippage_bps": settings.PAPER_SLIPPAGE_BPS,
            "fee_bps": settings.PAPER_FEE_BPS,
        }
        self._save_state()
        return self.state

    def record_daily_snapshot(self):
        if not self.state.get("initialized"):
            return None
        snapshot = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "total_balance": self.state["total_balance"],
            "profit_loss": self.state.get("total_profit_loss", 0),
            "available_cash": self.state["available_cash"],
        }
        history = self.state.setdefault("daily_profit_history", [])
        existing = next((item for item in history if item["date"] == snapshot["date"]), None)
        if existing:
            existing.update(snapshot)
        else:
            history.append(snapshot)
        self._save_state()
        return snapshot
