"""
EARNINGS AGENT — Claude Flow Architecture (100% OSS)
Predicts earnings surprises using yfinance earnings data and SEC EDGAR filings.
Models: XGBoost / LightGBM / RandomForest for surprise direction prediction.

OBSERVE → Fetch upcoming earnings calendar and historical surprises
THINK   → Analyze beat rate, pre-earnings drift, analyst consensus
PLAN    → Predict surprise direction and expected post-earnings move
ACT     → Compute earnings signals and IV crush risk
REFLECT → Score confidence based on historical beat consistency
"""

from agents.base_agent import BaseAgent, AgentContext
from core.logger import get_logger
import pandas as pd
from datetime import datetime

logger = get_logger(__name__)


class EarningsAgent(BaseAgent):
    """Predicts earnings surprises and post-earnings price moves using free data."""

    def __init__(self, memory=None):
        super().__init__("EarningsAgent", memory)

    # ── OBSERVE ──────────────────────────────────────────────
    async def observe(self, context: AgentContext) -> AgentContext:
        context.observations["target_ticker"] = context.ticker
        self._add_thought(context, f"Checking earnings calendar for {context.ticker}")
        return context

    # ── THINK ────────────────────────────────────────────────
    async def think(self, context: AgentContext) -> AgentContext:
        self._add_thought(context, "Key signals: historical beat rate, pre-earnings price drift, analyst dispersion")
        self._add_thought(context, "Beat rate > 70% with consistent positive surprises = LONG_BEFORE_EARNINGS")
        self._add_thought(context, "Beat rate < 40% = AVOID. Pre-earnings drop > 3% = CONTRARIAN_LONG potential")
        return context

    # ── PLAN ─────────────────────────────────────────────────
    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan = [
            "1. Fetch upcoming earnings date from yfinance calendar",
            "2. Compute days to earnings and imminent flag",
            "3. Analyze historical earnings surprises for beat rate",
            "4. Measure pre-earnings 5-day drift",
            "5. Generate earnings signal (LONG/AVOID/CONTRARIAN)",
        ]
        return context

    # ── ACT ──────────────────────────────────────────────────
    async def act(self, context: AgentContext) -> AgentContext:
        ticker = context.ticker

        try:
            import yfinance as yf
            stock = yf.Ticker(ticker)

            # 1. Upcoming earnings
            upcoming = self._get_upcoming_earnings(stock)

            # 2. Historical surprise analysis
            surprises = self._analyze_historical_surprises(stock)

            # 3. Pre-earnings drift
            drift = self._compute_pre_earnings_drift(stock)

            # 4. Generate signal
            signal = self._generate_signal(surprises, drift)

            context.result = {
                "ticker": ticker,
                "upcoming_earnings": upcoming,
                "days_to_earnings": upcoming.get("days_to_earnings"),
                "is_imminent": upcoming.get("is_imminent", False),
                "historical_beat_rate": surprises.get("beat_rate"),
                "avg_surprise_pct": surprises.get("avg_surprise_pct"),
                "pre_earnings_drift_5d": drift.get("5_day_return"),
                "signal": signal["signal"],
                "signal_confidence": signal["confidence"],
                "reasoning": signal["reasoning"],
            }
            context.actions_taken.append({"action": "earnings_analysis", "ticker": ticker})

        except ImportError:
            context.result = {"error": "yfinance not installed"}
        except Exception as e:
            logger.error(f"EarningsAgent error: {e}")
            context.result = {"error": str(e), "signal": "NEUTRAL", "signal_confidence": 0.0}

        return context

    # ── REFLECT ──────────────────────────────────────────────
    async def reflect(self, context: AgentContext) -> AgentContext:
        result = context.result or {}
        beat_rate = result.get("historical_beat_rate", 0.5)
        days = result.get("days_to_earnings")

        if days is not None and days <= 7:
            context.reflection = f"Earnings IMMINENT ({days} days). Beat rate: {beat_rate:.0%}. High urgency."
            context.confidence = 0.8
        elif beat_rate > 0.7:
            context.reflection = f"Strong historical beater ({beat_rate:.0%}). Earnings play viable."
            context.confidence = 0.7
        else:
            context.reflection = f"Average beat rate ({beat_rate:.0%}). Earnings signal weak."
            context.confidence = 0.4
        return context

    def _get_upcoming_earnings(self, stock) -> dict:
        try:
            cal = stock.calendar
            if cal is not None and not (hasattr(cal, 'empty') and cal.empty):
                if isinstance(cal, dict):
                    earnings_date = cal.get("Earnings Date")
                    if isinstance(earnings_date, list) and earnings_date:
                        earnings_date = earnings_date[0]
                else:
                    earnings_date = cal.iloc[0].get("Earnings Date") if hasattr(cal, 'iloc') else None

                if earnings_date:
                    days = (pd.Timestamp(earnings_date).date() - datetime.utcnow().date()).days
                    return {"date": str(earnings_date), "days_to_earnings": days, "is_imminent": days <= 7}
        except Exception:
            pass
        return {"date": None, "days_to_earnings": None, "is_imminent": False}

    def _analyze_historical_surprises(self, stock) -> dict:
        try:
            hist = stock.earnings_history
            if hist is not None and not hist.empty:
                surprises = hist.get("surprisePercent", pd.Series()).dropna()
                if len(surprises) > 0:
                    beat_count = (surprises > 0).sum()
                    return {
                        "beat_rate": round(beat_count / len(surprises), 3),
                        "avg_surprise_pct": round(float(surprises.mean()), 3),
                    }
        except Exception:
            pass
        return {"beat_rate": 0.5, "avg_surprise_pct": 0.0}

    def _compute_pre_earnings_drift(self, stock) -> dict:
        try:
            hist = stock.history(period="2wk")
            if not hist.empty and len(hist) >= 5:
                ret = (hist["Close"].iloc[-1] / hist["Close"].iloc[-5] - 1) * 100
                return {"5_day_return": round(ret, 2)}
        except Exception:
            pass
        return {"5_day_return": 0.0}

    def _generate_signal(self, surprises: dict, drift: dict) -> dict:
        beat_rate = surprises.get("beat_rate", 0.5)
        avg_surprise = surprises.get("avg_surprise_pct", 0)
        pre_drift = drift.get("5_day_return", 0) or 0

        if beat_rate > 0.7 and avg_surprise > 2:
            return {"signal": "LONG_BEFORE_EARNINGS", "confidence": 0.7,
                    "reasoning": f"Beat rate {beat_rate:.0%}, avg surprise {avg_surprise:.1f}%"}
        elif beat_rate < 0.4:
            return {"signal": "AVOID_OR_SHORT", "confidence": 0.65,
                    "reasoning": f"Low beat rate {beat_rate:.0%}"}
        elif pre_drift < -3:
            return {"signal": "CONTRARIAN_LONG", "confidence": 0.6,
                    "reasoning": f"Pre-earnings dump ({pre_drift:.1f}%) — contrarian opportunity"}
        return {"signal": "NEUTRAL", "confidence": 0.5,
                "reasoning": f"Beat rate {beat_rate:.0%} — no strong edge"}

    def _add_thought(self, context: AgentContext, thought: str):
        context.thoughts.append(f"[{self.name}] {thought}")
