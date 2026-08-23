from datetime import datetime, timedelta, timezone
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
    now = datetime.now(timezone.utc)
    for i in range(total):
        assert store.record_outcome(
            prediction_id=f"pred-{i}",
            ticker="BTC",
            model="SignalAggregatorAgent",
            provider="test_feed",
            upstream_provider="test_feed",
            direction="BULLISH",
            correct=i < correct,
            continuous_accuracy=1.0 if i < correct else 0.0,
            prediction_timestamp=(now - timedelta(hours=25)).isoformat(),
            horizon_hours=24,
            evaluated_at=now.isoformat(),
            observed_at=(now - timedelta(minutes=1)).isoformat(),
            live_gate_eligible=True,
        )


def test_wilson_lower_bound_penalizes_small_samples():
    assert 0.95 < wilson_lower_bound(100, 100) < 1.0
    assert wilson_lower_bound(10, 10) < wilson_lower_bound(100, 100)


def test_precision_store_tracks_only_eligible_directional_outcomes(tmp_path):
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


def test_research_accuracy_no_longer_creates_live_precision_evidence(tmp_path):
    db_path = str(tmp_path / "accuracy.db")
    accuracy = AccuracyStore(db_path)
    accuracy.record_outcome(
        ticker="BTC",
        model="SignalAggregatorAgent",
        provider="cache",
        direction="BULLISH",
        accuracy=1.0,
    )

    precision = DirectionalPrecisionStore(db_path)
    stats = precision.get_precision_stats(
        ticker="BTC", model="SignalAggregatorAgent", direction="BULLISH"
    )
    assert stats["total_directional"] == 0


def test_live_precision_evidence_is_immutable_and_deduped(tmp_path):
    store = DirectionalPrecisionStore(str(tmp_path / "precision.db"))
    now = datetime.now(timezone.utc)
    common = {
        "prediction_id": "immutable-prediction",
        "ticker": "BTC",
        "model": "SignalAggregatorAgent",
        "direction": "BULLISH",
        "prediction_timestamp": (now - timedelta(hours=25)).isoformat(),
        "horizon_hours": 24,
        "evaluated_at": now.isoformat(),
        "observed_at": (now - timedelta(minutes=1)).isoformat(),
        "live_gate_eligible": True,
    }

    assert store.record_outcome(
        **common,
        provider="feed_a",
        upstream_provider="feed_a",
        correct=True,
        continuous_accuracy=1.0,
    )
    assert not store.record_outcome(
        **common,
        provider="feed_b",
        upstream_provider="feed_b",
        correct=False,
        continuous_accuracy=0.0,
    )

    rows = store.export_evidence(ticker="BTC")
    assert len(rows) == 1
    assert rows[0]["provider"] == "feed_a"
    assert rows[0]["correct"] == 1


def test_cache_evidence_requires_upstream_provider(tmp_path):
    store = DirectionalPrecisionStore(str(tmp_path / "precision.db"))
    now = datetime.now(timezone.utc)
    base = {
        "prediction_id": "cache-pred",
        "ticker": "BTC",
        "model": "SignalAggregatorAgent",
        "provider": "cache",
        "direction": "BULLISH",
        "correct": True,
        "continuous_accuracy": 1.0,
        "prediction_timestamp": (now - timedelta(hours=25)).isoformat(),
        "horizon_hours": 24,
        "evaluated_at": now.isoformat(),
        "observed_at": (now - timedelta(minutes=1)).isoformat(),
        "live_gate_eligible": True,
    }
    assert not store.record_outcome(**base, upstream_provider="")
    assert store.record_outcome(
        **{**base, "prediction_id": "cache-pred-valid"},
        upstream_provider="yfinance",
    )
