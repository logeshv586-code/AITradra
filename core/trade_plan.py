"""Deterministic trade scenarios. Targets are conditional returns, never promises.

All percentages use unlevered entry-reference notional. Fees apply to both
fills; slippage is adverse on entry and exit. Funding, borrow, taxes, gaps and
liquidation are not modelled, so the stop scenario is not a maximum loss.
"""
from __future__ import annotations

import math


def finite_number(value) -> float:
    if isinstance(value, bool):
        raise ValueError("Boolean is not a price or financial amount")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Financial values must be finite")
    return number


def signal_direction(signal: dict) -> str:
    labels = {"BUY": "BUY", "STRONG BUY": "BUY", "SELL": "SELL", "STRONG SELL": "SELL"}
    verdict = str(signal.get("verdict") or "").strip().upper()
    direction = str(signal.get("direction") or "").strip().upper()
    resolved = labels.get(verdict, "HOLD") if verdict else labels.get(direction, "HOLD")
    if direction and labels.get(direction, "HOLD") != resolved:
        return "HOLD"
    return resolved


def trade_economics(direction, entry, stop, target, *, fee_bps=6.0,
                    slippage_bps=10.0, min_reward_risk=1.5) -> dict:
    """Return JSON-safe scenarios, or a fail-closed reason for unusable inputs."""
    try:
        entry, stop, target, fee, slip, minimum = map(
            finite_number, (entry, stop, target, fee_bps, slippage_bps, min_reward_risk)
        )
        if min(entry, stop, target) <= 0:
            raise ValueError("Positive entry, stop-loss and target prices are required")
        if not (0 <= fee < 10000 and 0 <= slip < 10000 and minimum > 0):
            raise ValueError("Invalid trading cost or reward/risk settings")
        valid = stop < entry < target if direction == "BUY" else target < entry < stop if direction == "SELL" else False
        if not valid:
            raise ValueError("Entry, stop and target must match an explicit BUY or SELL direction")
        sign = 1 if direction == "BUY" else -1
        entry_fill = entry * (1 + sign * slip / 10000)

        def net_return(exit_reference):
            exit_fill = exit_reference * (1 - sign * slip / 10000)
            return (sign * (exit_fill - entry_fill) - (entry_fill + exit_fill) * fee / 10000) / entry * 100

        profit = finite_number(net_return(target))
        loss = finite_number(-net_return(stop))
        ratio = finite_number(profit / loss) if loss > 0 else 0.0
        reasons = []
        if profit <= 0:
            reasons.append("Target does not cover estimated entry and exit costs")
        if loss <= 0 or ratio < minimum:
            reasons.append(f"Net reward/risk is below the required {minimum:g}:1")
        return {
            "eligible": not reasons, "reasons": reasons,
            "entry": entry, "stop_loss": stop, "take_profit": target,
            "gross_target_return_pct": finite_number(sign * (target - entry) / entry * 100),
            "net_target_return_pct": profit, "stop_scenario_loss_pct": loss,
            "net_reward_risk": ratio, "fee_bps_per_side": fee,
            "slippage_bps_per_side": slip, "minimum_reward_risk": minimum,
            "return_basis": "unlevered_entry_reference_notional",
        }
    except (ValueError, TypeError, OverflowError, ZeroDivisionError) as exc:
        return {"eligible": False, "reasons": [str(exc)]}


def economics_for_settings(direction, entry, stop, target, settings_obj):
    return trade_economics(
        direction, entry, stop, target,
        fee_bps=getattr(settings_obj, "TRADE_FEE_BPS", 6.0),
        slippage_bps=getattr(settings_obj, "TRADE_SLIPPAGE_BPS", 10.0),
        min_reward_risk=getattr(settings_obj, "MIN_NET_REWARD_RISK", 1.5),
    )


def build_trade_guidance(signal, risk, *, current_price, price_fresh, settings_obj):
    """Paper evaluation guidance only; never grants order/execution authority."""
    signal = signal if isinstance(signal, dict) else {}
    risk = risk if isinstance(risk, dict) else {}
    direction = signal_direction(signal)
    economics = economics_for_settings(
        direction, current_price, risk.get("stop_loss", signal.get("stop_loss")),
        risk.get("take_profit", signal.get("take_profit")), settings_obj,
    )
    reasons = list(economics["reasons"])
    if not price_fresh:
        reasons.append("Wait for a fresh market quote")
    if direction == "HOLD":
        reasons.append("No consistent BUY or SELL signal is available")
    if risk.get("decision") != "APPROVE":
        reasons.append(str(risk.get("reason") or "A complete portfolio risk review is required"))
    try:
        confidence = finite_number(signal.get("confidence"))
        minimum = finite_number(getattr(settings_obj, "MIN_SIGNAL_CONFIDENCE", 0.70)) * 100
        if not (0 < minimum <= 100 and minimum <= confidence <= 100):
            raise ValueError("Signal confidence does not meet the minimum")
        size = finite_number(risk.get("suggested_position_size"))
        if size <= 0:
            raise ValueError("A positive risk-approved position size is required")
        reference = finite_number(risk.get("entry", signal.get("entry_point")))
        quote = finite_number(current_price)
        if reference <= 0 or abs(quote / reference - 1) > 0.01:
            raise ValueError("Price moved beyond the reviewed entry; run a new risk review")
    except (ValueError, TypeError, OverflowError) as exc:
        reasons.append(str(exc))
    action = direction if not reasons else "WAIT"
    return {
        "action": action, "signal_direction": direction, "reasons": list(dict.fromkeys(reasons)),
        "economics": economics, "execution_authority": False, "mode": "paper_evaluation",
        "sell_meaning": "Bearish/short setup; selling an existing holding is a separate reduce-only exit",
        "notice": "Targets are scenarios, not guaranteed profit. Stop orders can fill worse than planned. Funding, borrowing and taxes are excluded. Confidence is not a measured win rate.",
    }
