"""Backtest Agent — validation gate for autonomous trading strategies.

A strategy is never marked deployable from in-sample return alone. The agent now
checks realistic friction, minimum trade count, profit factor, drawdown, win rate,
and a held-out out-of-sample window before registering live eligibility.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from agents.base_agent import BaseAgent, AgentContext
from core.config import settings
from core.logger import get_logger
from core.trading_safety import strategy_validation_store

logger = get_logger(__name__)


class BacktestAgent(BaseAgent):
    """Replay dated signals and register an auditable strategy-validation result."""

    def __init__(self, memory=None):
        super().__init__("BacktestAgent", memory)

    async def observe(self, context: AgentContext) -> AgentContext:
        signals = context.observations.get("signals", []) or []
        context.observations["signal_count"] = len(signals)
        context.observations["backtest_period_days"] = context.observations.get(
            "period_days", 730
        )
        self._add_thought(
            context, f"Received {len(signals)} dated signals for validation"
        )
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        count = int(context.observations.get("signal_count", 0) or 0)
        if count < settings.MIN_BACKTEST_TRADES:
            self._add_thought(
                context,
                f"Signal sample is small ({count}); live validation requires at least "
                f"{settings.MIN_BACKTEST_TRADES} completed trades.",
            )
        self._add_thought(
            context,
            "Validation uses a chronological 70/30 train/out-of-sample split with fees and slippage.",
        )
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan = [
            "1. Download historical OHLCV data",
            "2. Replay signals with commission and slippage",
            "3. Measure return, Sharpe, drawdown, win rate and profit factor",
            "4. Re-run only the held-out final 30% of history",
            "5. Register strategy as eligible only if full and out-of-sample gates pass",
        ]
        return context

    @staticmethod
    def _yf_symbol(ticker: str) -> str:
        ticker = ticker.upper()
        if ticker in {"BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "DOGE"}:
            return f"{ticker}-USD"
        return ticker

    @staticmethod
    def _run_backtest(df, signals: list[dict]) -> dict[str, Any]:
        import backtrader as bt

        if df is None or df.empty or len(df) < 30:
            return {"error": "Insufficient historical data"}

        cerebro = bt.Cerebro(stdstats=False)
        cerebro.addstrategy(AXIOMReplayStrategy, signals=signals)
        cerebro.adddata(bt.feeds.PandasData(dataname=df))
        initial_cash = 100_000.0
        cerebro.broker.setcash(initial_cash)
        cerebro.broker.setcommission(commission=0.001)
        cerebro.broker.set_slippage_perc(
            perc=max(0.0, settings.PAPER_SLIPPAGE_BPS / 10_000),
            slip_open=True,
            slip_limit=True,
            slip_match=True,
            slip_out=False,
        )
        cerebro.addanalyzer(
            bt.analyzers.SharpeRatio,
            _name="sharpe",
            riskfreerate=0.04,
            timeframe=bt.TimeFrame.Days,
            annualize=True,
        )
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")

        result = cerebro.run()
        strat = result[0]
        sharpe = strat.analyzers.sharpe.get_analysis().get("sharperatio", 0) or 0
        drawdown = strat.analyzers.drawdown.get_analysis()
        max_dd = float(drawdown.get("max", {}).get("drawdown", 0) or 0)
        trades = strat.analyzers.trades.get_analysis()

        total_closed = int(trades.get("total", {}).get("closed", 0) or 0)
        won = int(trades.get("won", {}).get("total", 0) or 0)
        lost = int(trades.get("lost", {}).get("total", 0) or 0)
        win_rate = won / total_closed if total_closed else 0.0
        gross_profit = float(trades.get("won", {}).get("pnl", {}).get("total", 0) or 0)
        gross_loss = abs(
            float(trades.get("lost", {}).get("pnl", {}).get("total", 0) or 0)
        )
        profit_factor = (
            gross_profit / gross_loss
            if gross_loss > 0
            else (999.0 if gross_profit > 0 else 0.0)
        )
        final_value = float(cerebro.broker.getvalue())
        total_return = (final_value / initial_cash - 1) * 100

        return {
            "total_return_pct": round(total_return, 2),
            "sharpe_ratio": round(float(sharpe), 3),
            "max_drawdown_pct": round(max_dd, 2),
            "total_trades": total_closed,
            "won_trades": won,
            "lost_trades": lost,
            "win_rate": round(win_rate, 4),
            "profit_factor": round(min(profit_factor, 999.0), 3),
            "final_value": round(final_value, 2),
        }

    @staticmethod
    def _passes_full(metrics: dict[str, Any]) -> tuple[bool, list[str]]:
        reasons: list[str] = []
        if metrics.get("error"):
            reasons.append(str(metrics["error"]))
            return False, reasons
        if metrics.get("sharpe_ratio", 0) < settings.MIN_BACKTEST_SHARPE:
            reasons.append("Sharpe below threshold")
        if metrics.get("max_drawdown_pct", 100) > settings.MAX_BACKTEST_DRAWDOWN_PCT:
            reasons.append("Drawdown above threshold")
        if metrics.get("win_rate", 0) < settings.MIN_BACKTEST_WIN_RATE:
            reasons.append("Win rate below threshold")
        if metrics.get("total_trades", 0) < settings.MIN_BACKTEST_TRADES:
            reasons.append("Too few completed trades")
        if metrics.get("profit_factor", 0) < settings.MIN_BACKTEST_PROFIT_FACTOR:
            reasons.append("Profit factor below threshold")
        if metrics.get("total_return_pct", 0) <= 0:
            reasons.append("Backtest return is not positive")
        return not reasons, reasons

    @staticmethod
    def _passes_oos(metrics: dict[str, Any]) -> tuple[bool, list[str]]:
        reasons: list[str] = []
        if metrics.get("error"):
            reasons.append(str(metrics["error"]))
            return False, reasons
        min_oos_trades = max(5, settings.MIN_BACKTEST_TRADES // 4)
        if metrics.get("total_trades", 0) < min_oos_trades:
            reasons.append(f"Out-of-sample completed trades below {min_oos_trades}")
        if metrics.get("total_return_pct", 0) <= 0:
            reasons.append("Out-of-sample return is not positive")
        if metrics.get("sharpe_ratio", 0) <= 0:
            reasons.append("Out-of-sample Sharpe is not positive")
        if metrics.get("max_drawdown_pct", 100) > settings.MAX_BACKTEST_DRAWDOWN_PCT:
            reasons.append("Out-of-sample drawdown above threshold")
        if metrics.get("profit_factor", 0) <= 1.0:
            reasons.append("Out-of-sample profit factor is not above 1.0")
        return not reasons, reasons

    async def act(self, context: AgentContext) -> AgentContext:
        ticker = str(context.ticker or "").upper()
        signals = context.observations.get("signals", []) or []
        period_days = int(context.observations.get("backtest_period_days", 730) or 730)
        strategy_id = str(
            context.observations.get("strategy_id", settings.LIVE_STRATEGY_ID)
        )

        if not ticker or not signals:
            context.result = {
                "error": "Ticker and dated signals are required",
                "recommendation": "NO_DATA",
            }
            return context

        try:
            import yfinance as yf

            end = datetime.utcnow()
            start = end - timedelta(days=period_days)
            df = yf.download(
                self._yf_symbol(ticker),
                start=start,
                end=end,
                auto_adjust=True,
                progress=False,
            )
            if df.empty or len(df) < 100:
                context.result = {
                    "error": f"Insufficient historical data for {ticker}",
                    "recommendation": "NO_DATA",
                }
                return context

            if hasattr(df.columns, "levels"):
                df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            df = df.sort_index().dropna(subset=["Open", "High", "Low", "Close"])

            split_index = max(1, int(len(df) * 0.70))
            split_date = df.index[split_index]
            oos_df = df.iloc[split_index:].copy()
            split_iso = split_date.date().isoformat()
            oos_signals = [
                signal
                for signal in signals
                if str(signal.get("date", "")) >= split_iso
            ]

            full_metrics = self._run_backtest(df, signals)
            oos_metrics = self._run_backtest(oos_df, oos_signals)
            full_pass, full_reasons = self._passes_full(full_metrics)
            oos_pass, oos_reasons = self._passes_oos(oos_metrics)
            approved = full_pass and oos_pass

            validation_metrics = {
                **full_metrics,
                "out_of_sample": oos_metrics,
                "split_date": split_iso,
                "period_days": period_days,
            }
            validation_record = strategy_validation_store.record(
                ticker=ticker,
                strategy_id=strategy_id,
                metrics=validation_metrics,
                approved=approved,
                out_of_sample_passed=oos_pass,
            )

            if approved:
                recommendation = "DEPLOY"
            elif full_metrics.get("total_return_pct", 0) > 0:
                recommendation = "REFINE"
            else:
                recommendation = "REJECT"

            context.result = {
                "ticker": ticker,
                "strategy_id": strategy_id,
                "recommendation": recommendation,
                "meets_criteria": approved,
                "full_sample": full_metrics,
                "out_of_sample": oos_metrics,
                "full_sample_failures": full_reasons,
                "out_of_sample_failures": oos_reasons,
                "validation_record": validation_record,
                # Backward-compatible top-level metrics.
                **full_metrics,
            }
            context.actions_taken.append(
                {
                    "action": "backtest_validation",
                    "approved": approved,
                    "trades": full_metrics.get("total_trades", 0),
                }
            )
        except ImportError as exc:
            context.result = {
                "error": f"Missing library: {exc}",
                "recommendation": "ERROR",
            }
        except Exception as exc:
            logger.error(f"BacktestAgent error: {exc}", exc_info=True)
            context.result = {"error": str(exc), "recommendation": "ERROR"}
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        result = context.result or {}
        rec = result.get("recommendation", "ERROR")
        if rec == "DEPLOY":
            context.reflection = (
                "Validation passed both full-sample and out-of-sample gates. "
                "This permits live eligibility but does not guarantee future profitability."
            )
            context.confidence = 0.85
        elif rec == "REFINE":
            context.reflection = "Positive history was found, but one or more deployment gates failed."
            context.confidence = 0.45
        elif rec == "REJECT":
            context.reflection = "Strategy failed the validation gate and is not live-eligible."
            context.confidence = 0.25
        else:
            context.reflection = "Backtest could not be completed. Live validation remains blocked."
            context.confidence = 0.1
        return context


try:
    import backtrader as bt

    class AXIOMReplayStrategy(bt.Strategy):
        """Replay dated long/short signals with confidence gating."""

        params = (
            ("signals", []),
            ("confidence_threshold", 0.65),
            ("position_pct", 0.05),
        )

        def __init__(self):
            self.signal_map = {
                str(signal["date"]): signal
                for signal in self.params.signals
                if isinstance(signal, dict) and signal.get("date")
            }
            self.pending_order = None

        @staticmethod
        def _confidence(signal: dict) -> float:
            value = float(signal.get("confidence", 0) or 0)
            return value / 100 if value > 1 else value

        def notify_order(self, order):
            if order.status in [order.Completed, order.Canceled, order.Margin, order.Rejected]:
                self.pending_order = None

        def next(self):
            if self.pending_order:
                return
            date_str = self.datas[0].datetime.date(0).isoformat()
            signal = self.signal_map.get(date_str)
            if not signal or self._confidence(signal) < self.params.confidence_threshold:
                return

            action = str(signal.get("action", signal.get("decision", "HOLD"))).upper()
            desired = 1 if action in {"BUY", "LONG", "STRONG BUY"} else -1 if action in {"SELL", "SHORT", "STRONG SELL"} else 0
            if desired == 0:
                return

            current = 1 if self.position.size > 0 else -1 if self.position.size < 0 else 0
            if current == desired:
                return
            if current != 0:
                self.pending_order = self.close()
                return

            price = float(self.datas[0].close[0])
            if price <= 0:
                return
            notional = self.broker.getvalue() * self.params.position_pct
            size = int(notional / price)
            if size <= 0:
                return
            self.pending_order = self.buy(size=size) if desired > 0 else self.sell(size=size)

except ImportError:
    pass
