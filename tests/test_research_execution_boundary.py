from __future__ import annotations

import ast
import inspect
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parent.parent
RESEARCH_FILES = (
    ROOT / "agents" / "research_council.py",
    ROOT / "self_improvement" / "research_scorecard.py",
    ROOT / "self_improvement" / "research_robustness.py",
    ROOT / "scripts" / "research_replay.py",
)
FORBIDDEN_RESEARCH_IMPORTS = (
    "brokers",
    "core.precision_gate",
    "core.trade_qualification",
    "core.trading_safety",
    "gateway.hyperliquid_service",
)


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def _settings():
    return SimpleNamespace(
        REQUIRE_PROTECTIVE_ORDERS=True,
        AUTOTRADE_MIN_SIGNAL_CONFIDENCE=90.0,
        LIVE_STRATEGY_ID="test-strategy",
    )


def _signal(confidence: float = 95.0) -> dict:
    return {
        "verdict": "BUY",
        "direction": "BUY",
        "confidence": confidence,
        "entry_point": 100.0,
        "stop_loss": 95.0,
        "take_profit": 110.0,
    }


def _risk() -> dict:
    return {
        "decision": "APPROVE",
        "reason": "deterministic risk checks passed",
        "entry": 100.0,
        "stop_loss": 95.0,
        "take_profit": 110.0,
        "suggested_position_size": 1000.0,
    }


def test_research_modules_cannot_import_execution_or_broker_layers():
    violations: list[str] = []
    for path in RESEARCH_FILES:
        modules = _imports(path)
        for module in modules:
            if module.startswith(FORBIDDEN_RESEARCH_IMPORTS):
                violations.append(f"{path.relative_to(ROOT)} -> {module}")
    assert violations == []


def test_trade_qualification_contract_has_no_research_input():
    from core.trade_qualification import TradeQualificationService

    parameters = inspect.signature(TradeQualificationService.qualify).parameters
    assert "research" not in parameters
    assert "research_decision" not in parameters
    assert "research_rating" not in parameters


def test_qualification_layer_itself_has_no_research_imports():
    modules = _imports(ROOT / "core" / "trade_qualification.py")
    forbidden = {
        module
        for module in modules
        if module.startswith("agents.research")
        or module.startswith("self_improvement.research")
    }
    assert forbidden == set()


def test_research_decision_defaults_are_advisory_only():
    from agents.research_council import ResearchDecision

    fields = ResearchDecision.__dataclass_fields__
    assert fields["execution_authority"].default is False
    assert fields["live_gate_eligible"].default is False


def test_paper_qualification_is_separate_from_live_permission():
    from core.trade_qualification import TradeQualificationService

    result = TradeQualificationService().qualify(
        "AAPL",
        _signal(confidence=70.0),
        _risk(),
        execution_status={
            "mode": "paper",
            "paper_mode": True,
            "live_execution_allowed": False,
            "blockers": ["PAPER_TRADE_MODE is enabled"],
        },
        settings_obj=_settings(),
    )
    assert result.decision == "EXECUTE_PAPER"
    assert result.execution_allowed is True
    assert result.paper_execution_allowed is True
    assert result.live_execution_allowed is False
    assert result.research_dependency is False
    assert result.gates["strategy_validation"]["checked"] is False
    assert result.gates["empirical_precision"]["checked"] is False


def test_live_qualification_requires_all_live_gates():
    from core.trade_qualification import TradeQualificationService

    service = TradeQualificationService()
    execution = {
        "mode": "live",
        "paper_mode": False,
        "live_execution_allowed": True,
        "blockers": [],
    }
    approved = service.qualify(
        "AAPL",
        _signal(confidence=95.0),
        _risk(),
        execution_status=execution,
        strategy_validation={"eligible": True, "reasons": [], "record": {}},
        precision_validation={
            "eligible": True,
            "reasons": [],
            "stats": {
                "observed_precision": 0.995,
                "wilson_lower_bound": 0.96,
                "total_directional": 250,
            },
        },
        settings_obj=_settings(),
    )
    assert approved.decision == "EXECUTE_LIVE"
    assert approved.execution_allowed is True
    assert approved.live_execution_allowed is True
    assert approved.research_dependency is False

    blocked = service.qualify(
        "AAPL",
        _signal(confidence=95.0),
        _risk(),
        execution_status=execution,
        strategy_validation={"eligible": True, "reasons": [], "record": {}},
        precision_validation={
            "eligible": False,
            "reasons": ["insufficient immutable evidence"],
            "stats": {},
        },
        settings_obj=_settings(),
    )
    assert blocked.decision == "BLOCK"
    assert blocked.execution_allowed is False
    assert blocked.live_execution_allowed is False
    assert "insufficient immutable evidence" in blocked.live_blockers


def test_live_qualification_rejects_high_research_like_confidence_if_signal_is_weak():
    """A research-looking field cannot override the actual live signal gate."""
    from core.trade_qualification import TradeQualificationService

    signal = _signal(confidence=60.0)
    signal["research_confidence"] = 99.9
    result = TradeQualificationService().qualify(
        "AAPL",
        signal,
        _risk(),
        execution_status={
            "mode": "live",
            "paper_mode": False,
            "live_execution_allowed": True,
            "blockers": [],
        },
        strategy_validation={"eligible": True, "reasons": [], "record": {}},
        precision_validation={"eligible": True, "reasons": [], "stats": {}},
        settings_obj=_settings(),
    )
    assert result.execution_allowed is False
    assert any("Current signal confidence" in reason for reason in result.live_blockers)


def test_autonomous_service_uses_one_qualification_firewall():
    source = (ROOT / "gateway" / "hyperliquid_service.py").read_text(encoding="utf-8")
    assert "trade_qualification_service.qualify(" in source
    assert "empirical_precision_gate.check(" not in source
    assert "strategy_validation_store.check(" not in source
    assert "research_execution_dependency\": False" in source
