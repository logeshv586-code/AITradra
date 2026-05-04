"""
Risk Manager Agent — Kelly Criterion + Volatility Regime + ATR Stops.

From risk-framework.md:
  Priority 1: Max Open Positions
  Priority 2: Daily Loss Limit
  Priority 3: Force Close
  Priority 4: Cash Reserve
  Priority 5: Leverage Cap
  Priority 6: Confidence Check + Kelly Sizing
"""

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
    """
    Agent 6: Risk Manager — capital protection first.
    Controls: MAX_POSITION_PCT, MAX_DAILY_LOSS_PCT, MAX_OPEN_POSITIONS.
    Enhanced with Kelly Criterion, volatility regime adjustment, and ATR stops.
    """

    def __init__(self):
        super().__init__(name="RiskManagerAgent", timeout_seconds=60)
        self.max_pos_pct = settings.MAX_POSITION_PCT
        self.max_daily_loss = settings.MAX_DAILY_LOSS_PCT
        self.max_open_pos = settings.MAX_OPEN_POSITIONS

    async def observe(self, context: AgentContext) -> AgentContext:
        if not context.observations.get("portfolio"):
            self._add_thought(context, "No portfolio data. Using defaults.")
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        self._add_thought(context, f"Evaluating risk for {context.ticker}")
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan = [
            "1. Circuit breaker checks (positions, daily loss, force close)",
            "2. Cash reserve validation",
            "3. Leverage cap",
            "4. Volatility regime classification",
            "5. Kelly + conviction sizing",
        ]
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        ticker = context.ticker
        portfolio = context.observations.get("portfolio", {})

        # ─── Priority 1: Max Open Positions ────────────────────
        open_positions = portfolio.get("open_positions", [])
        if len(open_positions) >= self.max_open_pos:
            context.result = {
                "decision": "BLOCK",
                "reason": f"Max open positions ({self.max_open_pos}) reached.",
                "risk_score": 1.0,
            }
            return context

        # ─── Priority 2: Daily Loss Circuit Breaker ────────────
        daily_pnl_pct = portfolio.get("daily_pnl_pct", 0.0)
        if daily_pnl_pct <= -self.max_daily_loss:
            context.result = {
                "decision": "BLOCK",
                "reason": f"Daily loss limit ({self.max_daily_loss*100}%) exceeded.",
                "risk_score": 1.0,
            }
            return context

        # ─── Priority 3: Force Close ───────────────────────────
        for pos in open_positions:
            unrealized = pos.get("unrealized_pnl_pct", 0.0)
            if unrealized <= -settings.FORCE_CLOSE_LOSS_PCT:
                self._add_thought(context,
                    f"FORCE CLOSE: {pos.get('ticker','?')} at {unrealized*100:.1f}% loss")
                context.result = {
                    "decision": "FORCE_CLOSE",
                    "ticker": pos.get("ticker", ticker),
                    "reason": f"Position hit {settings.FORCE_CLOSE_LOSS_PCT*100}% loss threshold.",
                    "risk_score": 1.0,
                }
                return context

        # ─── Priority 4: Cash Reserve ──────────────────────────
        total_balance = portfolio.get("total_value", 10000.0)
        available_cash = portfolio.get("cash", total_balance)
        reserve = total_balance * settings.BALANCE_RESERVE_PCT

        if available_cash < reserve:
            context.result = {
                "decision": "BLOCK",
                "reason": f"Cash ({available_cash:.0f}) below reserve ({reserve:.0f}).",
                "risk_score": 0.95,
            }
            return context

        # ─── Priority 5: Leverage Cap ──────────────────────────
        requested_leverage = context.observations.get("requested_leverage", 1)
        if requested_leverage > settings.MAX_LEVERAGE:
            self._add_thought(context,
                f"Capping leverage {requested_leverage}x → {settings.MAX_LEVERAGE}x")
            requested_leverage = settings.MAX_LEVERAGE

        # ─── Get Signal from Aggregator ────────────────────────
        agg_result = context.observations.get("signal_aggregator_result", {})
        consensus_verdict = agg_result.get("verdict", "HOLD")
        confidence = agg_result.get("confidence", 0.0)

        # ─── Priority 6: Confidence Gating ─────────────────────
        # Determine risk level from specialist risk output
        risk_spec = context.observations.get("specialist_outputs", {}).get("risk", {})
        vol = risk_spec.get("var_pct", 2.5)
        risk_level = risk_spec.get("risk_level", "MEDIUM")

        rec = get_recommendation(
            direction=consensus_verdict,
            confidence=confidence,
            risk_level=risk_level,
        )

        if rec == "HOLD":
            context.result = {
                "decision": "BLOCK",
                "reason": f"Recommendation is {rec} (Conf: {confidence:.0f}%, Risk: {risk_level}).",
                "risk_score": calculate_risk_score(confidence),
            }
            return context

        # ─── Volatility Regime Adjustment ──────────────────────
        ann_vol = risk_spec.get("max_drawdown_pct", 10.0) / 100 * 2.5  # Rough proxy
        regime = classify_volatility_regime(ann_vol)
        regime_mult = regime["risk_multiplier"]

        self._add_thought(context,
            f"Regime: {regime['regime']} → multiplier={regime_mult}")

        # ─── Conviction-Based Sizing ───────────────────────────
        conviction_mult = get_sizing_multiplier(confidence)

        # ─── Kelly Criterion Sizing ────────────────────────────
        stats = context.observations.get("historical_stats", {})
        win_rate = stats.get("win_rate", 0.55)
        avg_win = stats.get("avg_win", 0.05)
        avg_loss = stats.get("avg_loss", 0.03)

        kelly_size = calculate_kelly_size(
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            max_position_pct=self.max_pos_pct,
        )

        # Final position size = min(kelly, conviction) × regime × balance
        effective_pct = min(kelly_size, self.max_pos_pct * conviction_mult) * regime_mult
        suggested_size = total_balance * effective_pct

        # Never exceed available cash minus reserve
        max_deployable = available_cash - reserve
        suggested_size = min(suggested_size, max_deployable)
        suggested_size = max(0, suggested_size)

        if suggested_size <= 0:
            context.result = {
                "decision": "BLOCK",
                "reason": "Position size too small after risk adjustments.",
                "risk_score": 0.85,
            }
            return context

        # ─── Mandatory Stop-Loss ───────────────────────────────
        entry = agg_result.get("entry_point", 0)
        stop = agg_result.get("stop_loss", 0)
        target = agg_result.get("take_profit", 0)

        if not stop and entry:
            stop = round(entry * (1 - settings.MANDATORY_STOP_LOSS_PCT), 2)
        if not target and entry:
            target = round(entry * (1 + settings.MANDATORY_STOP_LOSS_PCT * 2), 2)

        context.result = {
            "decision": "APPROVE",
            "reason": f"Risk validated. {rec}. Size: ${suggested_size:.0f} "
                      f"({effective_pct*100:.1f}% of portfolio).",
            "suggested_position_size": round(suggested_size, 2),
            "position_pct": round(effective_pct * 100, 2),
            "leverage": requested_leverage,
            "sizing_multiplier": conviction_mult,
            "kelly_fraction": round(kelly_size, 4),
            "regime": regime["regime"],
            "regime_multiplier": regime_mult,
            "confidence": confidence,
            "recommendation": rec,
            "risk_level": risk_level,
            "risk_score": calculate_risk_score(confidence),
            "entry": entry,
            "stop_loss": stop,
            "take_profit": target,
        }

        self._add_thought(context,
            f"APPROVED: ${suggested_size:.0f} | Kelly={kelly_size:.3f} "
            f"× Conv={conviction_mult} × Regime={regime_mult}")
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        decision = (context.result or {}).get("decision", "BLOCK")
        context.reflection = f"Risk decision for {context.ticker}: {decision}"
        context.confidence = 1.0  # Risk logic is deterministic
        return context
