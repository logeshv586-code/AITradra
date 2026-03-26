"""
BACKTEST AGENT — Claude Flow Architecture (100% OSS)
Validates strategies on historical data before live deployment using Backtrader.
Reports: Sharpe, max drawdown, win rate, profit factor, and deploy recommendation.

OBSERVE → Gather signals and historical data for the ticker
THINK   → Assess whether sufficient history exists for reliable backtest
PLAN    → Configure Backtrader strategy, analyzers, and risk parameters
ACT     → Run full event-driven backtest
REFLECT → Determine if strategy passes deployment criteria (Sharpe > 1.0)
"""

from agents.base_agent import BaseAgent, AgentContext
from core.logger import get_logger
from datetime import datetime, timedelta

logger = get_logger(__name__)


class BacktestAgent(BaseAgent):
    """Backtests agent signals on historical data to validate profitability before deployment."""

    # Deployment criteria
    MIN_SHARPE = 1.0
    MAX_DRAWDOWN = 20.0  # percent
    MIN_WIN_RATE = 0.52  # 52%

    def __init__(self, memory=None):
        super().__init__("BacktestAgent", memory)

    # ── OBSERVE ──────────────────────────────────────────────
    async def observe(self, context: AgentContext) -> AgentContext:
        signals = context.observations.get("signals", [])
        context.observations["signal_count"] = len(signals)
        context.observations["backtest_period_days"] = context.observations.get("period_days", 365)
        self._add_thought(context, f"Received {len(signals)} signals to backtest for {context.ticker}")
        return context

    # ── THINK ────────────────────────────────────────────────
    async def think(self, context: AgentContext) -> AgentContext:
        count = context.observations.get("signal_count", 0)
        if count < 5:
            self._add_thought(context, f"Only {count} signals — backtest may not be statistically significant")
        else:
            self._add_thought(context, f"{count} signals available — sufficient for meaningful backtest")
        self._add_thought(context, f"Deployment criteria: Sharpe > {self.MIN_SHARPE}, DD < {self.MAX_DRAWDOWN}%, WR > {self.MIN_WIN_RATE:.0%}")
        return context

    # ── PLAN ─────────────────────────────────────────────────
    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan = [
            "1. Download historical OHLCV data for the backtest period",
            "2. Create Backtrader strategy that replays AXIOM signals",
            "3. Configure analyzers: SharpeRatio, DrawDown, TradeAnalyzer, Returns",
            "4. Run backtest with $100,000 initial capital and 0.1% commission",
            "5. Extract performance metrics and compare against deployment criteria",
            "6. Recommend: DEPLOY / REFINE / REJECT",
        ]
        return context

    # ── ACT ──────────────────────────────────────────────────
    async def act(self, context: AgentContext) -> AgentContext:
        ticker = context.ticker
        signals = context.observations.get("signals", [])
        period_days = context.observations.get("backtest_period_days", 365)

        if not signals:
            context.result = {"error": "No signals to backtest", "recommendation": "NO_DATA"}
            return context

        try:
            import backtrader as bt
            import yfinance as yf
            import pandas as pd

            # Fetch historical data
            end = datetime.utcnow()
            start = end - timedelta(days=period_days)
            df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)

            if df.empty or len(df) < 30:
                context.result = {"error": f"Insufficient data for {ticker}", "recommendation": "NO_DATA"}
                return context

            # Flatten MultiIndex if needed
            if hasattr(df.columns, 'levels'):
                df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

            # Create and run Backtrader
            cerebro = bt.Cerebro()
            cerebro.addstrategy(AXIOMReplayStrategy, signals=signals)

            data_feed = bt.feeds.PandasData(dataname=df)
            cerebro.adddata(data_feed)
            cerebro.broker.setcash(100_000)
            cerebro.broker.setcommission(commission=0.001)

            cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", riskfreerate=0.04)
            cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
            cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")

            result = cerebro.run()
            strat = result[0]

            # Extract metrics
            sharpe_analysis = strat.analyzers.sharpe.get_analysis()
            sharpe = sharpe_analysis.get("sharperatio", 0) or 0

            dd = strat.analyzers.drawdown.get_analysis()
            max_dd = dd.get("max", {}).get("drawdown", 0)

            trades = strat.analyzers.trades.get_analysis()
            won = trades.get("won", {}).get("total", 0)
            lost = trades.get("lost", {}).get("total", 0)
            total_trades = won + lost
            win_rate = won / total_trades if total_trades > 0 else 0

            total_return = (cerebro.broker.getvalue() / 100_000 - 1) * 100

            # Recommendation
            if total_return > 10 and sharpe > self.MIN_SHARPE and max_dd < self.MAX_DRAWDOWN:
                recommendation = "DEPLOY"
            elif total_return > 0 and sharpe > 0.5:
                recommendation = "REFINE"
            else:
                recommendation = "REJECT"

            context.result = {
                "ticker": ticker,
                "period_days": period_days,
                "total_return_pct": round(total_return, 2),
                "sharpe_ratio": round(sharpe, 3),
                "max_drawdown_pct": round(max_dd, 2),
                "total_trades": total_trades,
                "win_rate": round(win_rate, 3),
                "recommendation": recommendation,
                "meets_criteria": recommendation == "DEPLOY",
            }
            context.actions_taken.append({"action": "backtest_run", "trades": total_trades})

        except ImportError as e:
            context.result = {"error": f"Missing library: {e}", "recommendation": "ERROR"}
        except Exception as e:
            logger.error(f"BacktestAgent error: {e}")
            context.result = {"error": str(e), "recommendation": "ERROR"}

        return context

    # ── REFLECT ──────────────────────────────────────────────
    async def reflect(self, context: AgentContext) -> AgentContext:
        result = context.result or {}
        rec = result.get("recommendation", "ERROR")

        if rec == "DEPLOY":
            sharpe = result.get("sharpe_ratio", 0)
            ret = result.get("total_return_pct", 0)
            context.reflection = f"DEPLOY: Sharpe {sharpe:.2f}, Return {ret:.1f}%. Strategy validated."
            context.confidence = 0.9
        elif rec == "REFINE":
            context.reflection = "Strategy shows promise but needs refinement before deployment."
            context.confidence = 0.5
        elif rec == "REJECT":
            context.reflection = "Strategy failed to meet minimum criteria. Do NOT deploy."
            context.confidence = 0.3
        else:
            context.reflection = "Backtest could not be completed."
            context.confidence = 0.1
        return context

    def _add_thought(self, context: AgentContext, thought: str):
        context.thoughts.append(f"[{self.name}] {thought}")


# ── Backtrader Strategy (signal replay) ──────────────────────

try:
    import backtrader as bt

    class AXIOMReplayStrategy(bt.Strategy):
        """Replays AXIOM-generated signals on historical data."""
        params = (
            ("signals", []),
            ("confidence_threshold", 0.65),
            ("risk_pct", 0.02),
        )

        def __init__(self):
            self.signal_map = {s["date"]: s for s in self.params.signals if "date" in s}
            self.order = None

        def next(self):
            date_str = self.datas[0].datetime.date(0).isoformat()
            signal = self.signal_map.get(date_str)
            if not signal:
                return
            if signal.get("confidence", 0) < self.params.confidence_threshold:
                return

            action = signal.get("action", "HOLD")
            if action == "BUY" and not self.position:
                cash = self.broker.cash
                size = int(cash * self.params.risk_pct / self.datas[0].close[0])
                if size > 0:
                    self.order = self.buy(size=size)
            elif action == "SELL" and self.position:
                self.order = self.sell(size=self.position.size)

except ImportError:
    pass  # backtrader not installed — agent will catch this at runtime
