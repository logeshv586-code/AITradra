"""
PORTFOLIO AGENT — Claude Flow Architecture (100% OSS)
Optimizes position sizing using Kelly Criterion and Sharpe-based risk parity.
Libraries: numpy, pandas, PyPortfolioOpt (optional for multi-asset).

OBSERVE → Load price history and current portfolio state
THINK   → Assess win rate, volatility, and risk tolerance
PLAN    → Decide between Kelly, Risk Parity, or equal weight
ACT     → Compute optimal position size
REFLECT → Validate sizing is within central safety bounds
"""

from agents.base_agent import BaseAgent, AgentContext
from core.config import settings
from core.logger import get_logger
import numpy as np
import pandas as pd

logger = get_logger(__name__)


class PortfolioAgent(BaseAgent):
    """Optimizes position sizes using Kelly Criterion and volatility-aware sizing."""

    KELLY_FRACTION = 0.5  # Half-Kelly for safety

    def __init__(self, memory=None):
        super().__init__("PortfolioAgent", memory)

    @staticmethod
    def _hard_cap_fraction() -> float:
        """Use the same cap enforced by the central deterministic risk settings."""
        return max(0.0, min(float(settings.MAX_POSITION_PCT), 0.25))

    # ── OBSERVE ──────────────────────────────────────────────
    async def observe(self, context: AgentContext) -> AgentContext:
        prices = context.observations.get("prices", [])
        context.observations["has_price_data"] = len(prices) >= 30
        context.observations["data_points"] = len(prices)
        return context

    # ── THINK ────────────────────────────────────────────────
    async def think(self, context: AgentContext) -> AgentContext:
        hard_cap_pct = self._hard_cap_fraction() * 100.0
        if not context.observations.get("has_price_data"):
            self._add_thought(context, f"Only {context.observations['data_points']} prices — need at least 30 for sizing")
        else:
            self._add_thought(context, f"Have {context.observations['data_points']} data points — sufficient for Kelly")
            self._add_thought(
                context,
                f"Using Half-Kelly ({self.KELLY_FRACTION}x) with central {hard_cap_pct:.2f}% position cap",
            )
        return context

    # ── PLAN ─────────────────────────────────────────────────
    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan = [
            "1. Compute daily returns from price series",
            "2. Calculate win rate (positive return days / total)",
            "3. Calculate win/loss ratio (avg win / avg loss)",
            "4. Apply Kelly Criterion: K = W - (1-W)/R",
            "5. Scale by KELLY_FRACTION (Half-Kelly = 0.5x)",
            "6. Compute annualized volatility for risk-parity sizing",
            "7. Take the minimum of Kelly, volatility sizing, and the central MAX_POSITION_PCT safety cap",
        ]
        return context

    # ── ACT ──────────────────────────────────────────────────
    async def act(self, context: AgentContext) -> AgentContext:
        prices = context.observations.get("prices", [])
        hard_cap = self._hard_cap_fraction()
        fallback = min(0.02, hard_cap) if hard_cap > 0 else 0.0

        if len(prices) < 30:
            context.result = {
                "error": "Insufficient price data",
                "recommended_position_size_pct": round(fallback * 100.0, 2),
                "risk_limit_position_pct": round(hard_cap * 100.0, 2),
                "method": "default_fallback",
            }
            return context

        try:
            returns = pd.Series(prices, dtype=float).pct_change().dropna()

            # Win rate
            wins = returns[returns > 0]
            losses = returns[returns < 0]
            win_rate = len(wins) / len(returns) if len(returns) > 0 else 0.5

            # Win/Loss ratio
            avg_win = wins.mean() if len(wins) > 0 else 0.01
            avg_loss = abs(losses.mean()) if len(losses) > 0 else 0.01
            win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 1.0

            # Kelly Criterion: K = W - (1 - W) / R
            kelly_raw = win_rate - ((1 - win_rate) / win_loss_ratio)
            half_kelly = max(0.0, kelly_raw * self.KELLY_FRACTION)

            # Annualized volatility for risk-parity sizing
            daily_vol = returns.std()
            ann_vol = daily_vol * np.sqrt(252)
            target_risk = 0.15  # 15% target portfolio volatility
            volatility_size = min(1.0, target_risk / max(ann_vol, 0.01))

            # Sharpe Ratio
            mean_return = returns.mean() * 252
            sharpe = mean_return / max(ann_vol, 0.01)

            # Final recommendation: minimum of all approaches and the same cap
            # used by deterministic trade qualification. Never introduce a hidden
            # 25% research-agent cap when the central system is configured to 5%.
            recommended = min(half_kelly, volatility_size, hard_cap)
            if recommended > 0 and hard_cap > 0:
                minimum_probe = min(0.01, hard_cap)
                recommended = max(minimum_probe, recommended)
            recommended = min(recommended, hard_cap)

            context.result = {
                "win_rate": round(win_rate, 4),
                "win_loss_ratio": round(win_loss_ratio, 4),
                "kelly_raw": round(kelly_raw, 4),
                "half_kelly": round(half_kelly, 4),
                "annualized_volatility": round(ann_vol, 4),
                "sharpe_ratio": round(sharpe, 3),
                "risk_parity_size": round(volatility_size, 4),
                "recommended_position_size_pct": round(recommended * 100, 2),
                "risk_limit_position_pct": round(hard_cap * 100.0, 2),
                "method": "kelly_volatility_central_cap",
            }
            context.actions_taken.append(
                {
                    "action": "position_sizing",
                    "method": "kelly+volatility+central_cap",
                    "risk_limit_position_pct": round(hard_cap * 100.0, 2),
                }
            )

        except Exception as e:
            logger.error(f"PortfolioAgent ACT error: {e}")
            context.result = {
                "error": str(e),
                "recommended_position_size_pct": round(fallback * 100.0, 2),
                "risk_limit_position_pct": round(hard_cap * 100.0, 2),
                "method": "error_fallback",
            }

        return context

    # ── REFLECT ──────────────────────────────────────────────
    async def reflect(self, context: AgentContext) -> AgentContext:
        result = context.result or {}
        size = result.get("recommended_position_size_pct", 0)
        sharpe = result.get("sharpe_ratio", 0)
        cap = result.get("risk_limit_position_pct", self._hard_cap_fraction() * 100.0)

        if size >= max(cap * 0.8, 0.01):
            context.reflection = (
                f"Sizing reached {size:.1f}% near the configured {cap:.1f}% safety cap "
                f"(Sharpe: {sharpe:.2f})"
            )
            context.confidence = 0.8
        elif size > 3:
            context.reflection = f"Moderate conviction: {size:.1f}% position (Sharpe: {sharpe:.2f})"
            context.confidence = 0.65
        else:
            context.reflection = f"Low/moderate conviction: {size:.1f}% position — proceed cautiously"
            context.confidence = 0.4
        return context
