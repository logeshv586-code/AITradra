"""Hyperliquid autonomous trading service with fail-closed execution gates.

Flow: account state -> protective exits -> indicators -> AI decision -> signal
fusion -> deterministic risk gate -> strategy validation -> empirical precision
validation -> protected execution.
"""

from __future__ import annotations

from typing import Optional
import pandas as pd

from core.config import settings
from core.logger import get_logger
from core.precision_gate import empirical_precision_gate
from core.trading_safety import (
    DailyEquityTracker,
    get_execution_status,
    normalize_candles_latest_first,
    strategy_validation_store,
)
from brokers.hyperliquid_broker import HyperliquidBroker
from brokers.broker_router import Order, OrderSide, OrderType
from tools.indicator_service import IndicatorService
from agents.hyperliquid_agent import HyperliquidTradingAgent
from agents.risk_manager import RiskManagerAgent
from agents.signal_aggregator import SignalAggregatorAgent
from agents.base_agent import AgentContext

logger = get_logger(__name__)


class HyperliquidTradingService:
    """Runs a guarded trading cycle for the configured Hyperliquid assets."""

    def __init__(self):
        self.broker = HyperliquidBroker()
        self.agent = HyperliquidTradingAgent()
        self.risk_manager = RiskManagerAgent()
        self.signal_aggregator = SignalAggregatorAgent()
        self.active_tickers = settings.HYPERLIQUID_ASSETS
        self.daily_equity = DailyEquityTracker(
            scope=f"hyperliquid-{'paper' if self.broker.paper else 'live'}"
        )

    async def _portfolio_context(self) -> tuple[dict, list[dict]]:
        balance = await self.broker.get_balance()
        positions = await self.broker.get_positions()
        total_value = float(balance.get("total", 0) or 0)
        daily_pnl_pct = self.daily_equity.update(total_value)

        for position in positions:
            if "unrealized_pnl_pct" not in position:
                entry = float(position.get("entry_price", 0) or 0)
                qty = abs(float(position.get("qty", 0) or 0))
                unrealized = float(position.get("unrealized_pnl", 0) or 0)
                position["unrealized_pnl_pct"] = (
                    unrealized / (qty * entry) if qty > 0 and entry > 0 else 0.0
                )

        return (
            {
                "total_value": total_value,
                "cash": float(balance.get("cash", balance.get("available", 0)) or 0),
                "available": float(balance.get("available", balance.get("cash", 0)) or 0),
                "daily_pnl_pct": daily_pnl_pct,
                "open_positions": positions,
                "paper": bool(balance.get("paper", self.broker.paper)),
            },
            positions,
        )

    @staticmethod
    def _find_position(positions: list[dict], ticker: str) -> Optional[dict]:
        ticker = ticker.upper()
        return next(
            (p for p in positions if str(p.get("ticker", "")).upper() == ticker),
            None,
        )

    async def _force_close(self, ticker: str, positions: list[dict], reason: str) -> dict:
        position = self._find_position(positions, ticker)
        if not position:
            return {"status": "SKIPPED", "reason": f"No open position for {ticker}"}

        qty = float(position.get("qty", 0) or 0)
        if qty == 0:
            return {"status": "SKIPPED", "reason": f"Position for {ticker} is already flat"}

        logger.warning("[%s] FORCE CLOSE: %s", ticker, reason)
        return await self.broker.place_order(
            Order(
                ticker=ticker,
                side=OrderSide.SELL if qty > 0 else OrderSide.BUY,
                qty=abs(qty),
                order_type=OrderType.MARKET,
                reduce_only=True,
                reference_price=float(position.get("current_price", 0) or 0) or None,
            )
        )

    async def run_cycle(self):
        """Run one guarded iteration for all configured assets."""
        execution = get_execution_status(settings)
        logger.info(
            "Starting Hyperliquid trading cycle | mode=%s | assets=%s",
            execution["mode"],
            self.active_tickers,
        )

        portfolio_context, positions = await self._portfolio_context()
        if portfolio_context["daily_pnl_pct"] <= -settings.MAX_DAILY_LOSS_PCT:
            logger.critical(
                "Daily loss breaker active: %.2f%% <= -%.2f%%. New entries are disabled.",
                portfolio_context["daily_pnl_pct"] * 100,
                settings.MAX_DAILY_LOSS_PCT * 100,
            )

        for ticker in self.active_tickers:
            try:
                candles = await self.broker.get_candles(
                    ticker, interval=settings.HYPERLIQUID_INTERVAL
                )
                if not candles:
                    logger.warning("[%s] No candles available; skipping.", ticker)
                    continue

                # Indicators need chronological bars. Signal and ATR code explicitly
                # uses index 0 as the newest bar, so it receives a normalized copy.
                df = pd.DataFrame(candles).sort_values("timestamp").reset_index(drop=True)
                last_close = float(df.iloc[-1]["close"]) if not df.empty else 0.0
                ohlcv_latest_first = normalize_candles_latest_first(candles)

                protective_result = await self.broker.process_protective_orders(
                    ticker, mark_price=last_close
                )
                if protective_result:
                    logger.info(
                        "[%s] Paper protective exit fired: %s",
                        ticker,
                        protective_result.get("trigger"),
                    )
                    portfolio_context, positions = await self._portfolio_context()

                breached = next(
                    (
                        p
                        for p in positions
                        if float(p.get("unrealized_pnl_pct", 0) or 0)
                        <= -settings.FORCE_CLOSE_LOSS_PCT
                    ),
                    None,
                )
                if breached:
                    breached_ticker = str(breached.get("ticker", ticker)).upper()
                    await self._force_close(
                        breached_ticker,
                        positions,
                        f"loss exceeded {settings.FORCE_CLOSE_LOSS_PCT * 100:.1f}%",
                    )
                    portfolio_context, positions = await self._portfolio_context()
                    if breached_ticker == ticker.upper():
                        continue

                if portfolio_context["daily_pnl_pct"] <= -settings.MAX_DAILY_LOSS_PCT:
                    continue

                latest_indicators = IndicatorService.get_latest_indicators(df)
                context = AgentContext(
                    task=f"Hyperliquid trading analysis for {ticker}", ticker=ticker
                )
                context.observations["indicators"] = latest_indicators
                context.observations["portfolio"] = portfolio_context
                context.metadata["ohlcv_data"] = ohlcv_latest_first

                context = await self.agent.run(context)
                agent_result = context.result or {}
                decision = str(agent_result.get("decision", "HOLD")).upper()
                if decision not in {"LONG", "SHORT"}:
                    logger.info(
                        "[%s] HOLD: %s",
                        ticker,
                        agent_result.get(
                            "reasoning",
                            agent_result.get("reason", "No high-conviction setup"),
                        ),
                    )
                    continue

                existing = self._find_position(positions, ticker)
                if existing and not settings.ALLOW_POSITION_ADDONS:
                    logger.info(
                        "[%s] Existing position detected; add-on entries are disabled.",
                        ticker,
                    )
                    continue

                agent_confidence = (
                    context.confidence * 100
                    if context.confidence <= 1.0
                    else context.confidence
                )
                technical_signal = {
                    "signal": "BULLISH" if decision == "LONG" else "BEARISH",
                    "confidence": context.confidence,
                }
                if agent_result.get("score") is not None:
                    technical_signal["score"] = agent_result["score"]

                agg_context = AgentContext(
                    task=f"Signal aggregation for {ticker}",
                    ticker=ticker,
                    metadata={"ohlcv_data": ohlcv_latest_first},
                    observations={
                        "specialist_outputs": {"technical": technical_signal},
                    },
                )
                agg_context = await self.signal_aggregator.run(agg_context)
                signal_result = agg_context.result or {
                    "verdict": "HOLD",
                    "direction": "HOLD",
                    "confidence": 0,
                    "entry_point": last_close,
                    "stop_loss": 0,
                    "take_profit": 0,
                }

                # A high model confidence is not the same as historical accuracy,
                # but autonomous live mode should still reject weak current signals.
                if execution["live_execution_allowed"]:
                    min_live_confidence = float(
                        getattr(settings, "AUTOTRADE_MIN_SIGNAL_CONFIDENCE", 90.0)
                    )
                    current_confidence = float(signal_result.get("confidence", 0) or 0)
                    if current_confidence < min_live_confidence:
                        logger.critical(
                            "[%s] LIVE trade blocked: current signal confidence %.1f%% < %.1f%%.",
                            ticker,
                            current_confidence,
                            min_live_confidence,
                        )
                        continue

                risk_context = AgentContext(
                    task=f"Risk evaluation for {ticker} trade", ticker=ticker
                )
                risk_context.observations.update(
                    {
                        "portfolio": portfolio_context,
                        "confidence": agent_confidence,
                        "requested_leverage": agent_result.get("leverage", 1),
                        "signal_aggregator_result": signal_result,
                        "specialist_outputs": {
                            "risk": {
                                "risk_level": agent_result.get("risk_level", "MEDIUM"),
                                "var_pct": agent_result.get("var_pct", 2.5),
                                "annualized_volatility": agent_result.get(
                                    "annualized_volatility", 0.20
                                ),
                                "max_drawdown_pct": agent_result.get(
                                    "max_drawdown_pct", 10.0
                                ),
                            }
                        },
                    }
                )
                risk_context = await self.risk_manager.run(risk_context)
                risk_result = risk_context.result or {}
                risk_decision = risk_result.get("decision", "BLOCK")

                if risk_decision == "BLOCK":
                    logger.warning(
                        "[%s] Trade blocked by Risk Manager: %s",
                        ticker,
                        risk_result.get("reason"),
                    )
                    continue

                if risk_decision == "FORCE_CLOSE":
                    force_ticker = str(risk_result.get("ticker") or ticker).upper()
                    await self._force_close(
                        force_ticker,
                        positions,
                        risk_result.get("reason", "Risk Manager force close"),
                    )
                    portfolio_context, positions = await self._portfolio_context()
                    continue

                if risk_decision != "APPROVE":
                    continue

                suggested_size = float(
                    risk_result.get("suggested_position_size", 0) or 0
                )
                suggested_qty = suggested_size / last_close if last_close > 0 else 0
                if suggested_qty <= 0:
                    logger.warning(
                        "[%s] Suggested quantity is too small; skipping.", ticker
                    )
                    continue

                if execution["live_execution_allowed"]:
                    validation = strategy_validation_store.check(
                        ticker, settings.LIVE_STRATEGY_ID
                    )
                    if not validation["eligible"]:
                        logger.critical(
                            "[%s] LIVE trade blocked by strategy validation: %s",
                            ticker,
                            "; ".join(validation["reasons"]),
                        )
                        continue

                    precision = empirical_precision_gate.check(
                        ticker,
                        direction=signal_result.get("direction"),
                    )
                    if not precision["eligible"]:
                        logger.critical(
                            "[%s] LIVE trade blocked by empirical precision gate: %s",
                            ticker,
                            "; ".join(precision["reasons"]),
                        )
                        continue
                    logger.info(
                        "[%s] Empirical precision gate passed: observed=%.2f%% lower_bound=%.2f%% samples=%s",
                        ticker,
                        float(precision["stats"].get("observed_precision", 0)) * 100,
                        float(precision["stats"].get("wilson_lower_bound", 0)) * 100,
                        precision["stats"].get("total_directional", 0),
                    )

                stop_loss = float(risk_result.get("stop_loss", 0) or 0)
                take_profit = float(risk_result.get("take_profit", 0) or 0)
                order = Order(
                    ticker=ticker,
                    side=OrderSide.BUY if decision == "LONG" else OrderSide.SELL,
                    qty=suggested_qty,
                    order_type=OrderType.MARKET,
                    reference_price=last_close,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    leverage=int(risk_result.get("leverage", 1) or 1),
                )

                logger.info(
                    "[%s] %s %s %.6f units ($%.2f) | SL=%.4f TP=%.4f mode=%s",
                    ticker,
                    "Executing"
                    if execution["live_execution_allowed"]
                    else "Paper executing",
                    decision,
                    suggested_qty,
                    suggested_size,
                    stop_loss,
                    take_profit,
                    execution["mode"],
                )
                exec_result = await self.broker.place_order(order)
                if exec_result.get("status") not in {"FILLED", "PARTIALLY_FILLED"}:
                    logger.error(
                        "[%s] Execution was not completed: %s", ticker, exec_result
                    )
                else:
                    logger.info(
                        "[%s] Execution complete: %s",
                        ticker,
                        exec_result.get("status"),
                    )
                    portfolio_context, positions = await self._portfolio_context()

            except Exception as exc:
                logger.error(
                    "Error in %s trading cycle: %s", ticker, exc, exc_info=True
                )

        return {
            "mode": execution["mode"],
            "live_execution_allowed": execution["live_execution_allowed"],
            "daily_pnl_pct": portfolio_context.get("daily_pnl_pct", 0),
            "positions": len(positions),
            "assets_checked": len(self.active_tickers),
        }


hyperliquid_trading_service = HyperliquidTradingService()
