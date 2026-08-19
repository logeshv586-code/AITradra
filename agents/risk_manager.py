"""Risk Manager Agent — deterministic capital protection before execution."""

from agents.base_agent import BaseAgent, AgentContext
from core.config import settings
from core.logger import get_logger
from core.scoring import (
    get_recommendation,
    calculate_kelly_size,
    get_sizing_multiplier,
    classify_volatility_regime,
    calculate_risk_score,
)

logger = get_logger(__name__)


class RiskManagerAgent(BaseAgent):
    """Final deterministic risk veto before an order can be constructed."""

    def __init__(self):
        super().__init__(name="RiskManagerAgent", timeout_seconds=60)
        self.max_pos_pct = settings.MAX_POSITION_PCT
        self.max_daily_loss = settings.MAX_DAILY_LOSS_PCT
        self.max_open_pos = settings.MAX_OPEN_POSITIONS

    async def observe(self, context: AgentContext) -> AgentContext:
        if not context.observations.get("portfolio"):
            self._add_thought(context, "No portfolio data. Risk checks will use conservative defaults.")
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        self._add_thought(context, f"Evaluating deterministic risk controls for {context.ticker}")
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan = [
            "1. Max-position and daily-loss circuit breakers",
            "2. Emergency force-close scan",
            "3. Cash reserve and leverage cap",
            "4. Volatility regime classification",
            "5. Confidence gate and conservative Kelly sizing",
            "6. Mandatory stop-loss and take-profit validation",
        ]
        return context

    @staticmethod
    def _normalize_direction(verdict: str) -> str:
        verdict = str(verdict or "HOLD").upper().strip()
        if "BUY" in verdict:
            return "BUY"
        if "SELL" in verdict:
            return "SELL"
        return "HOLD"

    async def act(self, context: AgentContext) -> AgentContext:
        ticker = context.ticker
        portfolio = context.observations.get("portfolio", {}) or {}
        open_positions = portfolio.get("open_positions", []) or []

        # 1. Max open positions. Existing ticker management is still allowed by
        # the service; this gate protects new entries.
        if len(open_positions) >= self.max_open_pos:
            context.result = {
                "decision": "BLOCK",
                "reason": f"Max open positions ({self.max_open_pos}) reached.",
                "risk_score": 1.0,
            }
            return context

        # 2. Daily loss breaker. This is now populated by the execution service.
        daily_pnl_pct = float(portfolio.get("daily_pnl_pct", 0.0) or 0.0)
        if daily_pnl_pct <= -self.max_daily_loss:
            context.result = {
                "decision": "BLOCK",
                "reason": (
                    f"Daily loss limit reached ({daily_pnl_pct * 100:.2f}% <= "
                    f"-{self.max_daily_loss * 100:.2f}%)."
                ),
                "risk_score": 1.0,
            }
            return context

        # 3. Emergency loss scan can return a different ticker than the current
        # analysis target. The execution service honors this exact ticker.
        for pos in open_positions:
            unrealized = float(pos.get("unrealized_pnl_pct", 0.0) or 0.0)
            if unrealized <= -settings.FORCE_CLOSE_LOSS_PCT:
                force_ticker = pos.get("ticker", ticker)
                self._add_thought(
                    context,
                    f"FORCE CLOSE: {force_ticker} at {unrealized * 100:.1f}% loss",
                )
                context.result = {
                    "decision": "FORCE_CLOSE",
                    "ticker": force_ticker,
                    "reason": (
                        f"Position hit emergency loss threshold "
                        f"({settings.FORCE_CLOSE_LOSS_PCT * 100:.1f}%)."
                    ),
                    "risk_score": 1.0,
                }
                return context

        # 4. Cash reserve
        total_balance = float(portfolio.get("total_value", 0) or 0)
        available_cash = float(portfolio.get("cash", total_balance) or 0)
        if total_balance <= 0:
            context.result = {
                "decision": "BLOCK",
                "reason": "Portfolio value is unavailable or zero.",
                "risk_score": 1.0,
            }
            return context

        reserve = total_balance * settings.BALANCE_RESERVE_PCT
        if available_cash < reserve:
            context.result = {
                "decision": "BLOCK",
                "reason": f"Available cash ({available_cash:.2f}) is below reserve ({reserve:.2f}).",
                "risk_score": 0.95,
            }
            return context

        # 5. Leverage cap
        requested_leverage = int(context.observations.get("requested_leverage", 1) or 1)
        requested_leverage = max(1, min(requested_leverage, settings.MAX_LEVERAGE))

        # 6. Consensus normalization. STRONG BUY/SELL must not be accidentally
        # converted to HOLD by a second call to get_recommendation.
        agg_result = context.observations.get("signal_aggregator_result", {}) or {}
        consensus_verdict = agg_result.get("verdict", "HOLD")
        direction = self._normalize_direction(consensus_verdict)
        confidence = float(agg_result.get("confidence", 0.0) or 0.0)

        risk_spec = (
            context.observations.get("specialist_outputs", {}).get("risk", {}) or {}
        )
        risk_level = str(risk_spec.get("risk_level", "MEDIUM")).upper()
        recommendation = get_recommendation(
            direction=direction,
            confidence=confidence,
            risk_level=risk_level,
        )

        if recommendation == "HOLD":
            context.result = {
                "decision": "BLOCK",
                "reason": (
                    f"Signal did not pass confidence/risk gating "
                    f"(confidence {confidence:.0f}%, risk {risk_level})."
                ),
                "risk_score": calculate_risk_score(confidence),
            }
            return context

        # 7. Volatility regime. Prefer a real annualized volatility value; only
        # use the legacy drawdown proxy when a specialist does not supply one.
        ann_vol = risk_spec.get("annualized_volatility")
        if ann_vol is None:
            ann_vol = float(risk_spec.get("max_drawdown_pct", 10.0) or 10.0) / 100 * 2.5
        ann_vol = max(0.0, float(ann_vol or 0.0))
        regime = classify_volatility_regime(ann_vol)
        regime_mult = float(regime["risk_multiplier"])

        conviction_mult = get_sizing_multiplier(confidence)

        # 8. Kelly sizing. Missing history is deliberately conservative instead
        # of pretending a 55% win rate exists.
        stats = context.observations.get("historical_stats", {}) or {}
        win_rate = float(stats.get("win_rate", 0.0) or 0.0)
        avg_win = float(stats.get("avg_win", 0.0) or 0.0)
        avg_loss = float(stats.get("avg_loss", 0.0) or 0.0)
        kelly_size = calculate_kelly_size(
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            max_position_pct=self.max_pos_pct,
        )

        effective_pct = min(
            kelly_size,
            self.max_pos_pct * conviction_mult,
        ) * regime_mult
        effective_pct = min(effective_pct, self.max_pos_pct)
        suggested_size = total_balance * effective_pct

        max_deployable = max(0.0, available_cash - reserve)
        suggested_size = min(suggested_size, max_deployable)
        if suggested_size <= 0:
            context.result = {
                "decision": "BLOCK",
                "reason": "No deployable capital remains after risk adjustments.",
                "risk_score": 0.85,
            }
            return context

        # 9. Mandatory protection. Prefer signal/ATR levels and fall back to
        # percentage protection only when the signal stack could not calculate it.
        entry = float(agg_result.get("entry_point", 0) or 0)
        stop = float(agg_result.get("stop_loss", 0) or 0)
        target = float(agg_result.get("take_profit", 0) or 0)
        if entry <= 0:
            context.result = {
                "decision": "BLOCK",
                "reason": "A valid entry/reference price is required before execution.",
                "risk_score": 1.0,
            }
            return context

        if not stop:
            stop = (
                entry * (1 - settings.MANDATORY_STOP_LOSS_PCT)
                if direction == "BUY"
                else entry * (1 + settings.MANDATORY_STOP_LOSS_PCT)
            )
        if not target:
            target = (
                entry * (1 + settings.MANDATORY_STOP_LOSS_PCT * 2)
                if direction == "BUY"
                else entry * (1 - settings.MANDATORY_STOP_LOSS_PCT * 2)
            )

        valid_levels = (
            stop < entry < target if direction == "BUY" else target < entry < stop
        )
        if not valid_levels:
            context.result = {
                "decision": "BLOCK",
                "reason": "Stop-loss/take-profit levels are invalid for the trade direction.",
                "risk_score": 1.0,
            }
            return context

        context.result = {
            "decision": "APPROVE",
            "reason": (
                f"Risk checks passed. {recommendation}. Size ${suggested_size:.0f} "
                f"({effective_pct * 100:.2f}% of portfolio)."
            ),
            "suggested_position_size": round(suggested_size, 2),
            "position_pct": round(effective_pct * 100, 2),
            "leverage": requested_leverage,
            "sizing_multiplier": conviction_mult,
            "kelly_fraction": round(kelly_size, 4),
            "regime": regime["regime"],
            "regime_multiplier": regime_mult,
            "confidence": confidence,
            "recommendation": recommendation,
            "risk_level": risk_level,
            "risk_score": calculate_risk_score(confidence),
            "entry": round(entry, 8),
            "stop_loss": round(stop, 8),
            "take_profit": round(target, 8),
        }
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        decision = (context.result or {}).get("decision", "BLOCK")
        context.reflection = f"Risk decision for {context.ticker}: {decision}"
        context.confidence = 1.0
        return context
