import asyncio

import pytest

from agents.sentiment_classifier import SentimentClassifierAgent
from agents.strategy_generator_agent import StrategyGeneratorAgent
from agents.swarm_agent import SwarmResult
from self_improvement.plugin_ablation import PluginAblationLab


def test_finbert_aggregate_is_directional_and_calibrated():
    result = SentimentClassifierAgent._aggregate(
        [
            {"label": "positive", "score": 0.90},
            {"label": "positive", "score": 0.80},
            {"label": "neutral", "score": 0.70},
        ]
    )
    assert result["label"] == "positive"
    assert result["sentiment_score"] > 0.5
    assert 0 < result["confidence"] <= 1


def test_vibe_backtest_requires_real_metrics():
    parsed = StrategyGeneratorAgent._parse_backtest(
        '{"metrics":{"total_trades":42,"win_rate":58.0,"profit_factor":1.45,'
        '"sharpe_ratio":1.31,"max_drawdown_pct":12.4,"total_return_pct":18.2}}'
    )
    assert parsed.success is True
    assert parsed.total_trades == 42
    assert parsed.win_rate == pytest.approx(0.58)
    assert parsed.sharpe_ratio == pytest.approx(1.31)
    assert "sharpe_ratio" in parsed.parsed_metrics
    assert parsed.execution_authority is False


def test_vibe_backtest_does_not_fabricate_success():
    parsed = StrategyGeneratorAgent._parse_backtest("Backtest completed successfully")
    assert parsed.success is False
    assert parsed.total_trades == 0
    assert parsed.errors


def test_swarm_success_is_not_predictive_confidence():
    result = SwarmResult(success=True, preset_used="investment-committee", query="test")
    assert result.confidence_score == 0.5
    assert result.calibrated is False


def _rows(plugin_good: bool, count: int = 80):
    rows = []
    for i in range(count):
        actual_up = i % 2 == 0
        core = 0.55 if actual_up else 0.45
        if plugin_good:
            plugin = 0.90 if actual_up else 0.10
        else:
            plugin = 0.05 if actual_up else 0.95
        rows.append(
            {
                "actual_up": actual_up,
                "evidence": {"core_probability_up": core},
                "plugin_snapshot": {"finbert": {"probability_up": plugin}},
            }
        )
    return rows


def test_plugin_ablation_reads_shadow_evidence_and_keeps_value_add():
    lab = PluginAblationLab(min_samples=20, plugin_weight=0.40)
    report = lab.evaluate(_rows(True), plugins=["finbert"])
    row = report["results"]["finbert"]
    assert row["samples"] == 80
    assert row["policy"] == "KEEP"
    assert row["brier_improvement"] > 0


def test_plugin_ablation_disables_measurable_noise():
    lab = PluginAblationLab(min_samples=20, plugin_weight=0.40)
    report = lab.evaluate(_rows(False), plugins=["finbert"])
    row = report["results"]["finbert"]
    assert row["samples"] == 80
    assert row["policy"] in {"DISABLE", "ADVISORY"}
    assert row["brier_improvement"] < 0
