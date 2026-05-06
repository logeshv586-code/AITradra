"""
Hyperliquid Trading Service — Orchestrates the autonomous trading loop.
Flow: Fetch Stats -> Close Losers -> Gather TA -> LLM Decision -> Risk Check -> Execute.
"""

import asyncio
from typing import List, Dict
from core.config import settings
from core.logger import get_logger
from brokers.hyperliquid_broker import HyperliquidBroker
from brokers.broker_router import Order, OrderSide, OrderType
from tools.indicator_service import IndicatorService
from agents.hyperliquid_agent import HyperliquidTradingAgent
from agents.risk_manager import RiskManagerAgent
from agents.signal_aggregator import SignalAggregatorAgent
from agents.base_agent import AgentContext
import pandas as pd

logger = get_logger(__name__)

class HyperliquidTradingService:
    """
    Service that runs the Hyperliquid trading loop.
    Designed to mimic the functionality of the reference repo.
    """
    
    def __init__(self):
        self.broker = HyperliquidBroker()
        self.agent = HyperliquidTradingAgent()
        self.risk_manager = RiskManagerAgent()
        self.signal_aggregator = SignalAggregatorAgent()
        self.active_tickers = settings.HYPERLIQUID_ASSETS

    async def run_cycle(self):
        """Runs one iteration of the trading loop for all assets."""
        logger.info(f"Starting Hyperliquid Trading Cycle for assets: {self.active_tickers}")
        
        # 1. Fetch current account state
        portfolio_sum = await self.broker.get_balance()
        positions = await self.broker.get_positions()
        
        # Add unrealized PnL % to positions for risk manager
        for pos in positions:
            entry_px = pos.get("entry_price", 1)
            pos["unrealized_pnl_pct"] = pos["unrealized_pnl"] / (abs(pos["qty"]) * entry_px) if entry_px != 0 else 0

        portfolio_context = {
            "total_value": portfolio_sum.get("total", 0),
            "cash": portfolio_sum.get("cash", 0),
            "available": portfolio_sum.get("available", 0),
            "open_positions": positions
        }

        for ticker in self.active_tickers:
            try:
                # 2. Gather TA Indicators
                candles = await self.broker.get_candles(ticker, interval=settings.HYPERLIQUID_INTERVAL)
                if not candles:
                    logger.warning(f"Could not fetch candles for {ticker}, skipping.")
                    continue
                
                df = pd.DataFrame(candles)
                latest_indicators = IndicatorService.get_latest_indicators(df)
                
                # Convert candle data to OHLCV list for agents
                ohlcv_list = candles if isinstance(candles, list) else candles.to_dict("records") if hasattr(candles, "to_dict") else []
                
                # 3. Create Agent Context for trading agent
                context = AgentContext(task=f"Hyperliquid trading analysis for {ticker}", ticker=ticker)
                context.observations["indicators"] = latest_indicators
                context.observations["portfolio"] = portfolio_context
                context.metadata["ohlcv_data"] = ohlcv_list
                
                # 4. Agent Decision
                context = await self.agent.run(context)
                decision = context.result.get("decision", "HOLD") if context.result else "HOLD"
                
                if decision == "HOLD":
                    logger.info(f"[{ticker}] Agent chose to HOLD. Reason: {(context.result or {}).get('reasoning', 'N/A')}")
                    continue

                # 5. Build a mock signal_aggregator_result from the agent decision
                # This is required so RiskManagerAgent can gate on confidence + direction
                agent_confidence = context.confidence * 100 if context.confidence <= 1.0 else context.confidence
                agent_result = context.result or {}
                
                # Run signal aggregation using indicator data
                agg_context = AgentContext(
                    task=f"Signal aggregation for {ticker}",
                    ticker=ticker,
                    metadata={"ohlcv_data": ohlcv_list},
                    observations={
                        "specialist_outputs": {
                            "technical": {
                                "signal": "BULLISH" if decision == "LONG" else "BEARISH",
                                "confidence": context.confidence,
                                "score": agent_result.get("score", 0.3 if decision == "LONG" else -0.3),
                            }
                        }
                    }
                )
                agg_context = await self.signal_aggregator.run(agg_context)
                signal_aggregator_result = agg_context.result or {
                    "verdict": "BUY" if decision == "LONG" else "SELL",
                    "confidence": agent_confidence,
                    "entry_point": df.iloc[-1]["close"] if not df.empty else 0,
                    "stop_loss": 0,
                    "take_profit": 0,
                }

                # 6. Risk Manager Validation — now with proper signal_aggregator_result
                risk_context = AgentContext(task=f"Risk evaluation for {ticker} trade", ticker=ticker)
                risk_context.observations["portfolio"] = portfolio_context
                risk_context.observations["confidence"] = agent_confidence
                risk_context.observations["requested_leverage"] = agent_result.get("leverage", 1)
                risk_context.observations["signal_aggregator_result"] = signal_aggregator_result
                # Pass specialist outputs for risk level extraction
                risk_context.observations["specialist_outputs"] = {
                    "risk": {
                        "risk_level": "MEDIUM",
                        "var_pct": 2.5,
                        "max_drawdown_pct": 10.0,
                    }
                }
                
                risk_context = await self.risk_manager.run(risk_context)
                risk_result = risk_context.result or {}
                
                if risk_result.get("decision") == "BLOCK":
                    logger.warning(f"[{ticker}] Trade BLOCKED by Risk Manager. Reason: {risk_result.get('reason')}")
                    continue
                
                if risk_result.get("decision") == "FORCE_CLOSE":
                    logger.info(f"[{ticker}] FORCE CLOSE triggered by Risk Manager.")
                    # Find position to close
                    pos_to_close = next((p for p in positions if p["ticker"] == ticker), None)
                    if pos_to_close:
                        side = OrderSide.SELL if pos_to_close["qty"] > 0 else OrderSide.BUY
                        order = Order(
                            ticker=ticker,
                            side=side,
                            qty=abs(pos_to_close["qty"]),
                            order_type=OrderType.MARKET
                        )
                        await self.broker.place_order(order)
                    continue

                # 7. Execute Approved Trade
                if risk_result.get("decision") == "APPROVE":
                    side = OrderSide.BUY if decision == "LONG" else OrderSide.SELL
                    last_close = df.iloc[-1]["close"] if not df.empty else 1
                    suggested_size = risk_result.get("suggested_position_size", 0)
                    suggested_qty = suggested_size / last_close if last_close > 0 else 0
                    
                    if suggested_qty <= 0:
                        logger.warning(f"[{ticker}] Skipping: qty={suggested_qty:.6f} too small")
                        continue
                    
                    order = Order(
                        ticker=ticker,
                        side=side,
                        qty=suggested_qty,
                        order_type=OrderType.MARKET
                    )
                    
                    logger.info(f"[{ticker}] Executing {decision} order: {suggested_qty:.6f} units "
                                f"(${suggested_size:.2f} at ${last_close:.2f})")
                    exec_result = await self.broker.place_order(order)
                    logger.info(f"[{ticker}] Execution result: {exec_result.get('status')}")

            except Exception as e:
                logger.error(f"Error in {ticker} trading cycle: {e}", exc_info=True)

    async def start_loop(self):
        """Infinite loop for autonomous trading."""
        interval_map = {
            "1m": 60,
            "5m": 300,
            "15m": 900,
            "1h": 3600,
            "4h": 14400,
            "1d": 86400
        }
        sleep_secs = interval_map.get(settings.HYPERLIQUID_INTERVAL, 300)
        
        logger.info(f"Hyperliquid Trading Service loop started. Interval: {settings.HYPERLIQUID_INTERVAL}")
        while True:
            try:
                await self.run_cycle()
            except Exception as e:
                logger.error(f"Critical error in trading loop: {e}", exc_info=True)
            
            await asyncio.sleep(sleep_secs)

# Singleton instance
hyperliquid_trading_service = HyperliquidTradingService()
