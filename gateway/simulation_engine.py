import os
import json
from datetime import datetime
from typing import List, Dict, Optional
from core.logger import get_logger
from gateway.knowledge_store import knowledge_store

logger = get_logger(__name__)

DATA_FILE = os.path.join(os.path.dirname(__file__), "virtual_portfolio_data.json")

class SimulationEngine:
    def __init__(self, data_engine):
        self.data_engine = data_engine
        self.state = self._load_state()

    def _load_state(self) -> Dict:
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load virtual portfolio: {e}")
        
        return {
            "initialized": False,
            "total_balance": 0.0,
            "available_cash": 0.0,
            "invested_amount": 0.0,
            "positions": [],
            "history": [],
            "accuracy_metrics": {"total_trades": 0, "correct_predictions": 0, "accuracy_score": 100.0}
        }

    def _save_state(self):
        try:
            with open(DATA_FILE, "w") as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save virtual portfolio: {e}")

    def _get_snapshot(self, ticker: str) -> Optional[Dict]:
        try:
            return knowledge_store.get_ticker_intelligence(ticker.upper())
        except Exception as e:
            logger.warning(f"Failed to load intelligence snapshot for {ticker}: {e}")
            return None

    def _get_live_price(self, ticker: str) -> float:
        snapshot = self._get_snapshot(ticker)
        price = ((snapshot or {}).get("price_data") or {}).get("px", 0)
        return float(price or 0)

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
        self.state = {
            "initialized": True,
            "total_balance": initial_balance,
            "available_cash": initial_balance,
            "invested_amount": 0.0,
            "positions": [],
            "history": [],
            "accuracy_metrics": {"total_trades": 0, "correct_predictions": 0, "accuracy_score": 0.0}
        }
        self._save_state()
        return self.state

    def get_status(self):
        metrics = self.state.setdefault(
            "accuracy_metrics",
            {"total_trades": 0, "correct_predictions": 0, "accuracy_score": 0.0},
        )
        if metrics.get("total_trades", 0) == 0:
            metrics["accuracy_score"] = 0.0
        if self.state.get("initialized"):
            return self.calculate_live_portfolio()
        return self.state

    def buy_stock(self, ticker: str, quantity: float, prediction: Optional[str] = None):
        if not self.state["initialized"]:
            raise ValueError("Simulation not initialized")
        
        price = self._get_live_price(ticker)
        if price <= 0:
            raise ValueError(f"Could not fetch live price for {ticker}")

        amount = quantity * price
        
        if amount > self.state["available_cash"]:
            raise ValueError(f"Insufficient virtual funds for ${amount:.2f} purchase")

        signal_context = self._get_signal_context(ticker)

        # Update position
        existing_pos = next((p for p in self.state["positions"] if p["ticker"] == ticker), None)
        if existing_pos:
            # Weighted average price
            total_qty = existing_pos["quantity"] + quantity
            new_avg_price = ((existing_pos["buy_price"] * existing_pos["quantity"]) + (price * quantity)) / total_qty
            existing_pos["quantity"] = total_qty
            existing_pos["buy_price"] = new_avg_price
            existing_pos["invested_value"] = total_qty * new_avg_price
            # Keep original prediction or update to most recent? Let's update.
            existing_pos["prediction"] = prediction or signal_context["prediction_direction"] or existing_pos.get("prediction")
            existing_pos["signal_context"] = signal_context
        else:
            self.state["positions"].append({
                "ticker": ticker,
                "buy_price": price,
                "quantity": quantity,
                "invested_value": amount,
                "prediction": prediction or signal_context["prediction_direction"],
                "signal_context": signal_context,
                "timestamp": datetime.now().isoformat()
            })

        # Update wallet
        self.state["available_cash"] -= amount
        self.state["invested_amount"] += amount
        
        self.state["history"].append({
            "type": "BUY",
            "ticker": ticker,
            "price": price,
            "amount": amount,
            "quantity": quantity,
            "prediction_at_buy": prediction or signal_context["prediction_direction"],
            "signal_context": signal_context,
            "timestamp": datetime.now().isoformat()
        })

        self._save_state()
        return self.calculate_live_portfolio()

    def sell_stock(self, ticker: str, quantity_to_sell: Optional[float] = None):
        if not self.state["initialized"]:
            raise ValueError("Simulation not initialized")

        pos_index = next((i for i, p in enumerate(self.state["positions"]) if p["ticker"] == ticker), None)
        if pos_index is None:
            raise ValueError(f"No position found for {ticker}")

        pos = self.state["positions"][pos_index]
        orig_prediction = pos.get("prediction")

        if quantity_to_sell is None or quantity_to_sell >= pos["quantity"]:
            quantity_to_sell = pos["quantity"]
            fully_closed = True
        else:
            fully_closed = False

        current_price = self._get_live_price(ticker) or pos.get("current_price", pos["buy_price"])
        
        sale_value = quantity_to_sell * current_price
        profit_loss = sale_value - (quantity_to_sell * pos["buy_price"])

        # Update accuracy metrics based on original AI prediction
        self.state["accuracy_metrics"]["total_trades"] += 1
        
        # Accuracy logic: 
        # If prediction was UP, and profit_loss > 0, correct.
        # If prediction was DOWN, and we're selling with profit (meaning we bought at a 'dip' suggested or something?), 
        # actually, since we only track BUYS for now, we only track if the UP prediction was right.
        is_correct = False
        if orig_prediction == "UP" and profit_loss > 0:
            is_correct = True
        elif orig_prediction == "DOWN" and profit_loss < 0: # Profit loss < 0 means price dropped as predicted
            # Wait, if we BOUGHT because it said DOWN, we are stupid unless it's a short. 
            # In this dummy system, we only BUY.
            is_correct = False 
        
        if is_correct:
            self.state["accuracy_metrics"]["correct_predictions"] += 1
        
        total_trades = self.state["accuracy_metrics"]["total_trades"]
        self.state["accuracy_metrics"]["accuracy_score"] = (
            (self.state["accuracy_metrics"]["correct_predictions"] / total_trades) * 100
            if total_trades
            else 0.0
        )

        # Update wallet
        self.state["available_cash"] += sale_value
        
        if fully_closed:
            self.state["positions"].pop(pos_index)
        else:
            pos["quantity"] -= quantity_to_sell
            pos["invested_value"] = pos["quantity"] * pos["buy_price"]

        # Recalculate total invested
        self.state["invested_amount"] = sum(p["invested_value"] for p in self.state["positions"])

        self.state["history"].append({
            "type": "SELL",
            "ticker": ticker,
            "price": current_price,
            "amount": sale_value,
            "quantity": quantity_to_sell,
            "profit_loss": profit_loss,
            "signal_context": self._get_signal_context(ticker),
            "timestamp": datetime.now().isoformat()
        })

        self._save_state()
        return self.calculate_live_portfolio()

    def calculate_live_portfolio(self):
        if not self.state["initialized"]:
            return self.state

        total_invested_current = 0.0
        total_p_l = 0.0

        for pos in self.state["positions"]:
            curr_px = self._get_live_price(pos["ticker"]) or pos["buy_price"]
            signal_context = self._get_signal_context(pos["ticker"])
            
            pos["current_price"] = curr_px
            pos["current_value"] = curr_px * pos["quantity"]
            pos["profit_loss"] = pos["current_value"] - pos["invested_value"]
            pos["profit_loss_pct"] = (pos["profit_loss"] / pos["invested_value"] * 100) if pos["invested_value"] else 0
            pos["signal_context"] = signal_context
            
            total_invested_current += pos["current_value"]
            total_p_l += pos["profit_loss"]

        self.state["invested_amount"] = total_invested_current
        self.state["total_balance"] = self.state["available_cash"] + total_invested_current
        self.state["total_profit_loss"] = total_p_l
        self.state["profit_loss_percentage"] = (total_p_l / (self.state["total_balance"] - total_p_l) * 100) if (self.state["total_balance"] - total_p_l) > 0 else 0
        if self.state["accuracy_metrics"].get("total_trades", 0) == 0:
            self.state["accuracy_metrics"]["accuracy_score"] = 0.0
        
        return self.state
