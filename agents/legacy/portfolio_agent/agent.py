"""Portfolio Agent — Kelly/volatility sizing plus real multi-asset HRP.

Single-asset sizing uses Half-Kelly and volatility targeting. When callers supply
``portfolio_prices`` (dict/DataFrame with 30+ rows and at least two assets), the
agent invokes ``core.portfolio_optimizer.hrp_allocation`` which uses
PyPortfolioOpt's HRPOpt when available and deterministic inverse-volatility as a
fallback. All recommendations remain clipped to central MAX_POSITION_PCT.
"""

from __future__ import annotations

from agents.base_agent import BaseAgent, AgentContext
from core.config import settings
from core.logger import get_logger
from core.portfolio_optimizer import hrp_allocation
import numpy as np
import pandas as pd

logger = get_logger(__name__)


class PortfolioAgent(BaseAgent):
    KELLY_FRACTION = 0.5

    def __init__(self, memory=None):
        super().__init__("PortfolioAgent", memory)

    @staticmethod
    def _hard_cap_fraction() -> float:
        return max(0.0, min(float(settings.MAX_POSITION_PCT), 0.25))

    async def observe(self, context: AgentContext) -> AgentContext:
        prices = context.observations.get("prices", []) or []
        portfolio_prices = context.observations.get("portfolio_prices")
        context.observations["has_price_data"] = len(prices) >= 30
        context.observations["data_points"] = len(prices)
        context.observations["has_multi_asset_data"] = portfolio_prices is not None
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        cap = self._hard_cap_fraction() * 100.0
        if context.observations.get("has_multi_asset_data"):
            self._add_thought(context, f"Multi-asset history supplied — trying PyPortfolioOpt HRP under {cap:.2f}% central cap")
        elif context.observations.get("has_price_data"):
            self._add_thought(context, f"Using Half-Kelly + volatility sizing under {cap:.2f}% central cap")
        else:
            self._add_thought(context, "Insufficient history for measured position sizing")
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan = [
            "Compute single-asset Kelly and volatility limits",
            "If multi-asset prices are present, compute HRP allocation with PyPortfolioOpt",
            "Use inverse-volatility fallback only if the optional optimizer fails",
            "Take the most conservative applicable allocation",
            "Clip every asset to central MAX_POSITION_PCT and leave excess as cash",
        ]
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        prices = context.observations.get("prices", []) or []
        portfolio_prices = context.observations.get("portfolio_prices")
        ticker = str(context.ticker or context.metadata.get("ticker", "") or "").upper()
        hard_cap = self._hard_cap_fraction()
        fallback = min(0.02, hard_cap) if hard_cap > 0 else 0.0

        hrp = hrp_allocation(portfolio_prices, hard_cap) if portfolio_prices is not None else {
            "available": False, "method": "not_requested", "weights": {}
        }
        hrp_weight = None
        if hrp.get("available") and ticker:
            weights = hrp.get("weights", {}) or {}
            candidates = [ticker, ticker.replace("-USD", ""), ticker.replace(".NS", "")]
            for key in candidates:
                if key in weights:
                    hrp_weight = float(weights[key])
                    break

        if len(prices) < 30:
            recommended = min(hrp_weight, hard_cap) if hrp_weight is not None else fallback
            context.result = {
                "error": "Insufficient single-asset price data",
                "recommended_position_size_pct": round(recommended * 100.0, 2),
                "risk_limit_position_pct": round(hard_cap * 100.0, 2),
                "portfolio_optimization": hrp,
                "method": "hrp_only" if hrp_weight is not None else "default_fallback",
                "execution_authority": False,
            }
            return context

        try:
            returns = pd.Series(prices, dtype=float).pct_change().dropna()
            wins = returns[returns > 0]
            losses = returns[returns < 0]
            win_rate = len(wins) / len(returns) if len(returns) else 0.5
            avg_win = float(wins.mean()) if len(wins) else 0.01
            avg_loss = abs(float(losses.mean())) if len(losses) else 0.01
            win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 1.0
            kelly_raw = win_rate - ((1 - win_rate) / win_loss_ratio)
            half_kelly = max(0.0, kelly_raw * self.KELLY_FRACTION)

            daily_vol = float(returns.std(ddof=1))
            ann_vol = daily_vol * np.sqrt(252)
            target_risk = 0.15
            volatility_size = min(1.0, target_risk / max(ann_vol, 0.01))
            mean_return = float(returns.mean()) * 252
            sharpe = mean_return / max(ann_vol, 0.01)

            candidates = [half_kelly, volatility_size, hard_cap]
            method = "kelly_volatility_central_cap"
            if hrp_weight is not None:
                candidates.append(hrp_weight)
                method = "pypfopt_hrp+kelly+volatility+central_cap"
            recommended = max(0.0, min(candidates))
            if recommended > 0 and hard_cap > 0:
                # A 1% probe is only used when it does not violate an explicit HRP
                # allocation. If HRP recommends less, respect the smaller weight.
                minimum_probe = min(0.01, hard_cap)
                if hrp_weight is None or hrp_weight >= minimum_probe:
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
                "hrp_target_weight": None if hrp_weight is None else round(hrp_weight, 6),
                "portfolio_optimization": hrp,
                "recommended_position_size_pct": round(recommended * 100, 2),
                "risk_limit_position_pct": round(hard_cap * 100.0, 2),
                "method": method,
                "execution_authority": False,
            }
            context.actions_taken.append(
                {
                    "action": "position_sizing",
                    "method": method,
                    "risk_limit_position_pct": round(hard_cap * 100.0, 2),
                }
            )
        except Exception as exc:
            logger.error("PortfolioAgent ACT error: %s", exc)
            context.result = {
                "error": str(exc),
                "recommended_position_size_pct": round(fallback * 100.0, 2),
                "risk_limit_position_pct": round(hard_cap * 100.0, 2),
                "portfolio_optimization": hrp,
                "method": "error_fallback",
                "execution_authority": False,
            }
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        result = context.result or {}
        size = float(result.get("recommended_position_size_pct", 0) or 0)
        sharpe = float(result.get("sharpe_ratio", 0) or 0)
        cap = float(result.get("risk_limit_position_pct", self._hard_cap_fraction() * 100.0) or 0)
        if size >= max(cap * 0.8, 0.01):
            context.reflection = f"Sizing {size:.1f}% is near configured {cap:.1f}% cap (Sharpe {sharpe:.2f})"
            context.confidence = 0.8
        elif size > 3:
            context.reflection = f"Moderate allocation: {size:.1f}% (Sharpe {sharpe:.2f})"
            context.confidence = 0.65
        else:
            context.reflection = f"Conservative allocation: {size:.1f}%"
            context.confidence = 0.4
        return context
