"""Backtest Agent — systematic discovery + realistic deployment validation.

A strategy is never marked deployable from in-sample return alone. When dated
signals are not supplied, the agent now runs AITradra's SystematicResearchEngine
to discover a candidate using train/validation/test separation, walk-forward
checks, block-bootstrap Sharpe bounds, a sign-flip null test, multiple-testing
adjustment and regime stability. The surviving candidate is then replayed through
Backtrader with fees/slippage before strategy eligibility can be recorded.

This agent only creates strategy-validation evidence. It does not bypass the
Risk Manager, empirical precision gate or trade-qualification firewall.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from agents.base_agent import BaseAgent, AgentContext
from core.config import settings
from core.logger import get_logger
from core.systematic_research import SystematicResearchEngine
from core.trading_safety import strategy_validation_store

logger = get_logger(__name__)


class BacktestAgent(BaseAgent):
    """Discover/replay strategies and register auditable validation evidence."""

    def __init__(self, memory=None):
        super().__init__("BacktestAgent", memory)

    async def observe(self, context: AgentContext) -> AgentContext:
        signals = context.observations.get("signals", []) or []
        context.observations["signal_count"] = len(signals)
        context.observations["backtest_period_days"] = context.observations.get(
            "period_days", 730
        )
        if signals:
            self._add_thought(
                context, f"Received {len(signals)} dated signals for validation"
            )
        else:
            self._add_thought(
                context,
                "No dated signals supplied; systematic candidate discovery will run before replay.",
            )
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        count = int(context.observations.get("signal_count", 0) or 0)
        if count and count < settings.MIN_BACKTEST_TRADES:
            self._add_thought(
                context,
                f"Signal sample is small ({count}); live validation requires at least "
                f"{settings.MIN_BACKTEST_TRADES} completed trades.",
            )
        self._add_thought(
            context,
            "Validation combines systematic train/validation/test robustness with a separate "
            "event-driven 70/30 replay using realistic friction.",
        )
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan = [
            "1. Download chronological historical OHLCV data",
            "2. If signals are absent, screen systematic momentum, trend, mean-reversion and breakout candidates",
            "3. Challenge the winner with untouched test, walk-forward, bootstrap, null-test and regime checks",
            "4. Replay dated BUY/SELL/EXIT signals in Backtrader with commission and slippage",
            "5. Measure return, Sharpe, drawdown, win rate, profit factor and completed trades",
            "6. Re-run the final 30% as an event-driven out-of-sample replay",
            "7. Register eligibility only when every applicable validation gate passes",
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
        cerebro.addstrategy(
            AXIOMReplayStrategy,
            signals=signals,
            position_pct=max(0.001, min(float(settings.MAX_POSITION_PCT), 0.25)),
        )
        cerebro.adddata(bt.feeds.PandasData(dataname=df))
        initial_cash = 100_000.0
        cerebro.broker.setcash(initial_cash)
        # Keep the event-driven replay conservative. Fees and slippage are both
        # charged here even when the vectorized systematic screen already charged
        # its own friction; these are independent validation engines.
        cerebro.broker.setcommission(
            commission=max(0.0, float(settings.PAPER_FEE_BPS)) / 10_000
        )
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

        if not ticker:
            context.result = {
                "error": "Ticker is required",
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

            systematic_research: dict[str, Any] | None = None
            signal_source = "provided"
            systematic_enabled = bool(
                getattr(settings, "SYSTEMATIC_RESEARCH_ENABLED", True)
            )
            if not signals and systematic_enabled:
                engine = SystematicResearchEngine()
                discovered = engine.discover(df, ticker=ticker)
                signals = list(discovered.get("signals", []) or [])
                systematic_research = {
                    key: value for key, value in discovered.items() if key != "signals"
                }
                if signals:
                    strategy_id = str(discovered.get("strategy_id") or strategy_id)
                    context.observations["signals"] = signals
                    context.observations["strategy_id"] = strategy_id
                    signal_source = "systematic_discovery"
                    self._add_thought(
                        context,
                        f"Systematic research selected {strategy_id} with robustness "
                        f"score {systematic_research.get('robustness_score', 0)}.",
                    )

            if not signals:
                context.result = {
                    "ticker": ticker,
                    "strategy_id": strategy_id,
                    "error": "No dated signals available after systematic discovery",
                    "recommendation": "NO_DATA",
                    "systematic_research": systematic_research,
                }
                return context

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

            systematic_pass = True
            systematic_failures: list[str] = []
            if systematic_research is not None:
                systematic_pass = bool(
                    systematic_research.get("systematic_gate_passed", False)
                )
                systematic_failures = list(
                    systematic_research.get("gate_failures", []) or []
                )

            approved = full_pass and oos_pass and systematic_pass

            validation_metrics = {
                **full_metrics,
                "out_of_sample": oos_metrics,
                "split_date": split_iso,
                "period_days": period_days,
                "signal_source": signal_source,
                "systematic_research": systematic_research,
            }
            validation_record = strategy_validation_store.record(
                ticker=ticker,
                strategy_id=strategy_id,
                metrics=validation_metrics,
                approved=approved,
                out_of_sample_passed=oos_pass and systematic_pass,
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
                "signal_source": signal_source,
                "signal_count": len(signals),
                "recommendation": recommendation,
                "meets_criteria": approved,
                "systematic_gate_passed": systematic_pass,
                "systematic_gate_failures": systematic_failures,
                "systematic_research": systematic_research,
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
                    "action": "systematic_backtest_validation",
                    "approved": approved,
                    "signal_source": signal_source,
                    "trades": full_metrics.get("total_trades", 0),
                    "systematic_gate_passed": systematic_pass,
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
        systematic = result.get("systematic_research") or {}
        robustness = systematic.get("robustness_score")
        robustness_text = (
            f" Systematic robustness score: {robustness}." if robustness is not None else ""
        )
        if rec == "DEPLOY":
            context.reflection = (
                "Strategy passed systematic robustness, full-sample and event-driven "
                "out-of-sample gates. This permits strategy eligibility but does not "
                f"guarantee future profitability.{robustness_text}"
            )
            context.confidence = 0.88
        elif rec == "REFINE":
            context.reflection = (
                "Positive history was found, but one or more robustness/deployment gates "
                f"failed.{robustness_text}"
            )
            context.confidence = 0.45
        elif rec == "REJECT":
            context.reflection = (
                f"Strategy failed validation and is not live-eligible.{robustness_text}"
            )
            context.confidence = 0.25
        else:
            context.reflection = "Backtest could not be completed. Live validation remains blocked."
            context.confidence = 0.1
        return context


try:
    import backtrader as bt

    class AXIOMReplayStrategy(bt.Strategy):
        """Replay dated long/short/exit signals with target-position orders."""

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
            if action in {"EXIT", "FLAT", "CLOSE"}:
                if self.position.size != 0:
                    self.pending_order = self.order_target_percent(target=0.0)
                return

            desired = (
                1
                if action in {"BUY", "LONG", "STRONG BUY"}
                else -1
                if action in {"SELL", "SHORT", "STRONG SELL"}
                else 0
            )
            if desired == 0:
                return

            target = desired * max(0.001, min(float(self.params.position_pct), 0.25))
            current = 1 if self.position.size > 0 else -1 if self.position.size < 0 else 0
            if current == desired:
                return

            # order_target_percent can close and reverse the position in one target
            # operation, avoiding the previous close-only flip bug.
            self.pending_order = self.order_target_percent(target=target)

except ImportError:
    pass
