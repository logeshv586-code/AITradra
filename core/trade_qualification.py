"""Single qualification boundary between analysis/risk and order execution.

Research is deliberately absent from this contract. A research rating may inform
upstream analysis, but it can never grant trading permission. Only a concrete
signal, deterministic Risk Manager approval, execution-mode authorization,
protective orders, strategy validation and empirical live evidence can qualify
an order for execution.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from core.config import settings
from core.precision_gate import empirical_precision_gate
from core.trading_safety import get_execution_status, strategy_validation_store

_ACTIVE_DIRECTIONS = {"BUY", "SELL"}


def _float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _direction(signal_result: dict[str, Any]) -> str:
    direction = str(signal_result.get("direction") or "").upper().strip()
    if direction in _ACTIVE_DIRECTIONS:
        return direction
    verdict = str(signal_result.get("verdict") or "").upper().strip()
    if "BUY" in verdict:
        return "BUY"
    if "SELL" in verdict:
        return "SELL"
    return "HOLD"


@dataclass(frozen=True)
class TradeQualification:
    """Immutable result consumed by an execution adapter."""

    ticker: str
    decision: str
    mode: str
    execution_allowed: bool
    paper_execution_allowed: bool
    live_execution_allowed: bool
    signal_direction: str
    signal_confidence: float
    risk_decision: str
    execution_blockers: list[str] = field(default_factory=list)
    live_blockers: list[str] = field(default_factory=list)
    gates: dict[str, Any] = field(default_factory=dict)
    research_dependency: bool = False
    contract_version: str = "aitradra.trade_qualification.v1"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TradeQualificationService:
    """Authoritative pre-order qualification service.

    The public method intentionally accepts no ResearchDecision/ResearchCouncil
    object. This prevents research confidence from being confused with execution
    authorization.
    """

    def qualify(
        self,
        ticker: str,
        signal_result: dict[str, Any],
        risk_result: dict[str, Any],
        *,
        execution_status: dict[str, Any] | None = None,
        strategy_validation: dict[str, Any] | None = None,
        precision_validation: dict[str, Any] | None = None,
        settings_obj=settings,
        strategy_id: str | None = None,
    ) -> TradeQualification:
        ticker = str(ticker or "").upper().strip()
        signal_result = signal_result or {}
        risk_result = risk_result or {}
        execution = execution_status or get_execution_status(settings_obj)
        mode = "live" if execution.get("live_execution_allowed") else "paper"

        direction = _direction(signal_result)
        confidence = _float(signal_result.get("confidence"))
        risk_decision = str(risk_result.get("decision") or "BLOCK").upper().strip()

        blockers: list[str] = []
        gates: dict[str, Any] = {}

        signal_ok = direction in _ACTIVE_DIRECTIONS and str(
            signal_result.get("verdict") or direction
        ).upper() != "HOLD"
        if not ticker:
            blockers.append("Ticker is required")
        if not signal_ok:
            blockers.append("Signal Aggregator did not produce an active BUY/SELL signal")
        gates["signal"] = {
            "eligible": signal_ok,
            "direction": direction,
            "confidence": confidence,
        }

        risk_ok = risk_decision == "APPROVE"
        if not risk_ok:
            blockers.append(f"Risk Manager decision is {risk_decision or 'BLOCK'}")
        gates["risk_manager"] = {
            "eligible": risk_ok,
            "decision": risk_decision,
            "reason": risk_result.get("reason"),
        }

        entry = _float(risk_result.get("entry") or signal_result.get("entry_point"))
        stop = _float(risk_result.get("stop_loss") or signal_result.get("stop_loss"))
        target = _float(
            risk_result.get("take_profit") or signal_result.get("take_profit")
        )
        if direction == "BUY":
            protection_ok = entry > 0 and stop > 0 and target > 0 and stop < entry < target
        elif direction == "SELL":
            protection_ok = entry > 0 and stop > 0 and target > 0 and target < entry < stop
        else:
            protection_ok = False

        protection_required = bool(
            getattr(settings_obj, "REQUIRE_PROTECTIVE_ORDERS", True)
        )
        if protection_required and not protection_ok:
            blockers.append("Valid protective stop-loss/take-profit levels are required")
        gates["protective_orders"] = {
            "required": protection_required,
            "eligible": protection_ok if protection_required else True,
            "entry": entry,
            "stop_loss": stop,
            "take_profit": target,
        }

        base_allowed = not blockers
        live_authorized = bool(execution.get("live_execution_allowed"))
        live_blockers = list(execution.get("blockers") or []) if not live_authorized else []
        gates["execution_authorization"] = {
            "eligible": live_authorized,
            "mode": mode,
            "details": execution,
        }

        strategy_result: dict[str, Any] = {
            "eligible": True,
            "reasons": [],
            "record": None,
            "checked": False,
        }
        precision_result: dict[str, Any] = {
            "eligible": True,
            "reasons": [],
            "stats": None,
            "checked": False,
        }

        if live_authorized:
            min_live_confidence = _float(
                getattr(settings_obj, "AUTOTRADE_MIN_SIGNAL_CONFIDENCE", 90.0)
            )
            current_confidence_ok = confidence >= min_live_confidence
            if not current_confidence_ok:
                live_blockers.append(
                    f"Current signal confidence {confidence:.1f}% is below the live minimum "
                    f"{min_live_confidence:.1f}%"
                )
            gates["current_signal_confidence"] = {
                "eligible": current_confidence_ok,
                "observed": confidence,
                "minimum": min_live_confidence,
            }

            strategy_id = strategy_id or str(
                getattr(settings_obj, "LIVE_STRATEGY_ID", "") or ""
            )
            if strategy_validation is None:
                strategy_result = {
                    **strategy_validation_store.check(ticker, strategy_id),
                    "checked": True,
                }
            else:
                strategy_result = {**strategy_validation, "checked": True}
            if not strategy_result.get("eligible"):
                live_blockers.extend(strategy_result.get("reasons") or [
                    "Strategy validation did not pass"
                ])
            gates["strategy_validation"] = strategy_result

            if precision_validation is None:
                precision_result = {
                    **empirical_precision_gate.check(ticker, direction=direction),
                    "checked": True,
                }
            else:
                precision_result = {**precision_validation, "checked": True}
            if not precision_result.get("eligible"):
                live_blockers.extend(precision_result.get("reasons") or [
                    "Empirical precision validation did not pass"
                ])
            gates["empirical_precision"] = precision_result
        else:
            gates["current_signal_confidence"] = {
                "eligible": True,
                "checked": False,
                "reason": "Live-only gate",
            }
            gates["strategy_validation"] = strategy_result
            gates["empirical_precision"] = precision_result

        paper_allowed = base_allowed and not live_authorized
        live_allowed = base_allowed and live_authorized and not live_blockers
        execution_allowed = paper_allowed or live_allowed
        decision = (
            "EXECUTE_LIVE"
            if live_allowed
            else "EXECUTE_PAPER"
            if paper_allowed
            else "BLOCK"
        )

        return TradeQualification(
            ticker=ticker,
            decision=decision,
            mode=mode,
            execution_allowed=execution_allowed,
            paper_execution_allowed=paper_allowed,
            live_execution_allowed=live_allowed,
            signal_direction=direction,
            signal_confidence=round(confidence, 4),
            risk_decision=risk_decision,
            execution_blockers=blockers,
            live_blockers=live_blockers,
            gates=gates,
            research_dependency=False,
        )


trade_qualification_service = TradeQualificationService()
