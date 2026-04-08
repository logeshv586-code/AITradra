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
            # We'd need current price to calculate real pnl_pct if HL doesn't provide it
            # For now, we'll assume the risk manager might handle fetch if needed or we use HL unrlzd PnL
            pos["unrealized_pnl_pct"] = pos["unrealized_pnl"] / (abs(pos["qty"]) * entry_px) if entry_px != 0 else 0

        portfolio_context = {
            "total_value": portfolio_sum.get("total", 0),
            "cash": portfolio_sum.get("cash", 0),
            "available": portfolio_sum.get("available", 0),
            "open_positions": positions
        }

        for ticker in self.active_tickers:
            try:
                # 2. Check for Force Close on this specific ticker
                # (Risk manager will handle this in its act() method)
                
                # 3. Gather TA Indicators
                candles = await self.broker.get_candles(ticker, interval=settings.HYPERLIQUID_INTERVAL)
                if not candles:
                    logger.warning(f"Could not fetch candles for {ticker}, skipping.")
                    continue
                
                df = pd.DataFrame(candles)
                latest_indicators = IndicatorService.get_latest_indicators(df)
                
                # 4. Create Agent Context
                context = AgentContext(ticker=ticker)
                context.observations["indicators"] = latest_indicators
                context.observations["portfolio"] = portfolio_context
                
                # 5. Agent Decision
                context = await self.agent.run(context)
                decision = context.result.get("decision", "HOLD")
                
                if decision == "HOLD":
                    logger.info(f"[{ticker}] Agent chose to HOLD. Reason: {context.result.get('reasoning', 'N/A')}")
                    continue

                # 6. Risk Manager Validation
                risk_context = AgentContext(ticker=ticker)
                risk_context.observations["portfolio"] = portfolio_context
                risk_context.observations["confidence"] = context.confidence
                risk_context.observations["requested_leverage"] = context.result.get("leverage", 1)
                
                risk_context = await self.risk_manager.run(risk_context)
                
                if risk_context.result.get("decision") == "BLOCK":
                    logger.warning(f"[{ticker}] Trade BLOCKED by Risk Manager. Reason: {risk_context.result.get('reason')}")
                    continue
                
                if risk_context.result.get("decision") == "FORCE_CLOSE":
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
                if risk_context.result.get("decision") == "APPROVE":
                    side = OrderSide.BUY if decision == "LONG" else OrderSide.SELL
                    suggested_qty = risk_context.result.get("suggested_position_size", 0) / df.iloc[-1]["close"]
                    
                    order = Order(
                        ticker=ticker,
                        side=side,
                        qty=suggested_qty,
                        order_type=OrderType.MARKET # Or LIMIT if we had logic for it
                    )
                    
                    logger.info(f"[{ticker}] Executing {decision} order: {suggested_qty} units.")
                    exec_result = await self.broker.place_order(order)
                    logger.info(f"[{ticker}] Execution result: {exec_result.get('status')}")

            except Exception as e:
                logger.error(f"Error in {ticker} trading cycle: {e}")

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
                logger.error(f"Critical error in trading loop: {e}")
            
            await asyncio.sleep(sleep_secs)

# Singleton instance
hyperliquid_trading_service = HyperliquidTradingService()
