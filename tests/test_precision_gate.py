from types import SimpleNamespace

from core.precision_gate import EmpiricalPrecisionGate, wilson_lower_bound
from self_improvement.accuracy_store import AccuracyStore
from self_improvement.precision_store import DirectionalPrecisionStore


def _precision_settings(**overrides):
    values = {
        "REQUIRE_EMPIRICAL_PRECISION_VALIDATION": True,
        "AUTOTRADE_TARGET_PRECISION": 0.99,
        "AUTOTRADE_MIN_EVALUATED_SIGNALS": 100,
        "AUTOTRADE_MIN_PRECISION_LOWER_BOUND": 0.95,
        "PRECISION_VALIDATION_MAX_AGE_DAYS": 30,
        "PRECISION_LOOKBACK_DAYS": 90,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _seed(store: DirectionalPrecisionStore, *, correct: int, total: int):
    for i in range(total):
        store.record_outcome(
            prediction_id=f"pred-{i}",
            ticker="BTC",
            model="SignalAggregatorAgent",
            provider="test",
            direction="BULLISH",
            correct=i < correct,
            continuous_accuracy=1.0 if i < correct else 0.0,
        )


def test_wilson_lower_bound_penalizes_small_samples():
    assert 0.95 < wilson_lower_bound(100, 100) < 1.0
    assert wilson_lower_bound(10, 10) < wilson_lower_bound(100, 100)


def test_precision_store_tracks_directional_outcomes(tmp_path):
    store = DirectionalPrecisionStore(str(tmp_path / "precision.db"))
    _seed(store, correct=9, total=10)
    stats = store.get_precision_stats(
        ticker="BTC", model="SignalAggregatorAgent", direction="BUY"
    )
    assert stats["total_directional"] == 10
    assert stats["correct_scored"] == 9


def test_precision_gate_blocks_when_evidence_is_insufficient(tmp_path, monkeypatch):
    import self_improvement.precision_store as precision_module

    store = DirectionalPrecisionStore(str(tmp_path / "precision.db"))
    _seed(store, correct=20, total=20)
    monkeypatch.setattr(precision_module, "precision_store", store)

    result = EmpiricalPrecisionGate().check(
        "BTC", direction="BUY", settings_obj=_precision_settings()
    )
    assert result["eligible"] is False
    assert any("100 are required" in reason for reason in result["reasons"])


def test_precision_gate_passes_only_strong_99_percent_evidence(tmp_path, monkeypatch):
    import self_improvement.precision_store as precision_module

    store = DirectionalPrecisionStore(str(tmp_path / "precision.db"))
    _seed(store, correct=100, total=100)
    monkeypatch.setattr(precision_module, "precision_store", store)

    result = EmpiricalPrecisionGate().check(
        "BTC", direction="BUY", settings_obj=_precision_settings()
    )
    assert result["eligible"] is True
    assert result["stats"]["observed_precision"] == 1.0
    assert result["stats"]["wilson_lower_bound"] >= 0.95


def test_precision_gate_rejects_99_of_100_when_statistical_bound_is_weak(
    tmp_path, monkeypatch
):
    import self_improvement.precision_store as precision_module

    store = DirectionalPrecisionStore(str(tmp_path / "precision.db"))
    _seed(store, correct=99, total=100)
    monkeypatch.setattr(precision_module, "precision_store", store)

    result = EmpiricalPrecisionGate().check(
        "BTC", direction="BUY", settings_obj=_precision_settings()
    )
    assert result["eligible"] is False
    assert result["stats"]["observed_precision"] == 0.99
    assert result["stats"]["wilson_lower_bound"] < 0.95


def test_repeated_same_day_scoring_does_not_inflate_precision_samples(tmp_path):
    db_path = str(tmp_path / "accuracy.db")
    accuracy = AccuracyStore(db_path)
    accuracy.record_outcome(
        ticker="BTC",
        model="SignalAggregatorAgent",
        provider="test",
        direction="BULLISH",
        accuracy=0.4,
    )
    accuracy.record_outcome(
        ticker="BTC",
        model="SignalAggregatorAgent",
        provider="test",
        direction="BULLISH",
        accuracy=0.0,
    )

    precision = DirectionalPrecisionStore(db_path)
    stats = precision.get_precision_stats(
        ticker="BTC", model="SignalAggregatorAgent", direction="BULLISH"
    )
    assert stats["total_directional"] == 1
    assert stats["correct_scored"] == 0
