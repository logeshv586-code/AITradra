import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class _MemoryStub:
    def __init__(self, store):
        self.structured = store

    async def update_prediction_outcome(
        self,
        prediction_id,
        actual_price,
        accuracy_score,
        outcome=None,
    ):
        await self.structured.update_outcome(
            prediction_id,
            actual_price,
            accuracy_score,
            outcome=outcome,
        )


@pytest.mark.asyncio
async def test_self_improvement_scores_matured_predictions(monkeypatch):
    from memory.memory_manager import PredictionStore
    from self_improvement.accuracy_store import AccuracyStore
    from self_improvement.engine import SelfImprovementEngine
    from self_improvement.precision_store import DirectionalPrecisionStore

    tmp_dir = Path(__file__).resolve().parent.parent / "tmp"
    tmp_dir.mkdir(exist_ok=True)
    log_path = tmp_dir / f"prediction_outcome_{uuid.uuid4().hex}.json"
    db_path = tmp_dir / f"prediction_evidence_{uuid.uuid4().hex}.db"
    store = PredictionStore(log_path=str(log_path))

    await store.save_prediction(
        {
            "ticker": "AAPL",
            "prediction": {
                "final_decision": "BULLISH",
                "price_at_prediction": 100.0,
                "target_price": 110.0,
            },
            "created_at": "2026-04-01T00:00:00+00:00",
            "source_agent": "SignalAggregatorAgent",
        }
    )

    observed_at = datetime.now(timezone.utc).isoformat()

    async def fake_price_data(ticker, allow_scrape=False):
        return {
            "px": 112.0,
            "source_used": "test_feed",
            "is_stale": False,
            "syncing": False,
            "is_estimated": False,
            "freshness_minutes": 0,
            "observed_at": observed_at,
        }

    monkeypatch.setattr(
        "gateway.data_engine.data_engine.get_price_data",
        fake_price_data,
    )
    monkeypatch.setattr(
        "self_improvement.engine.settings.PREDICTION_SCORE_DELAY_HOURS",
        0,
    )
    precision = DirectionalPrecisionStore(str(db_path))
    accuracy = AccuracyStore(str(db_path))
    monkeypatch.setattr("self_improvement.engine.precision_store", precision)
    monkeypatch.setattr("self_improvement.engine.accuracy_store", accuracy)

    engine = SelfImprovementEngine(_MemoryStub(store))
    summary = await engine._evaluate_pending_predictions()

    records = await store.get_predictions_for_ticker("AAPL")
    assert summary["evaluated"] == 1
    assert summary["live_gate_eligible"] == 1
    assert records[0]["accuracy_score"] == 1.0
    assert records[0]["actual_price"] == 112.0
    assert records[0]["outcome"]["direction"] == "BULLISH"
    assert records[0]["outcome"]["live_gate_evidence"]["eligible"] is True

    stats = precision.get_precision_stats(
        ticker="AAPL", model="SignalAggregatorAgent", direction="BULLISH"
    )
    assert stats["total_directional"] == 1


@pytest.mark.asyncio
async def test_stale_research_score_never_becomes_live_gate_evidence(monkeypatch):
    from memory.memory_manager import PredictionStore
    from self_improvement.accuracy_store import AccuracyStore
    from self_improvement.engine import SelfImprovementEngine
    from self_improvement.precision_store import DirectionalPrecisionStore

    tmp_dir = Path(__file__).resolve().parent.parent / "tmp"
    tmp_dir.mkdir(exist_ok=True)
    log_path = tmp_dir / f"stale_prediction_{uuid.uuid4().hex}.json"
    db_path = tmp_dir / f"stale_evidence_{uuid.uuid4().hex}.db"
    store = PredictionStore(log_path=str(log_path))

    await store.save_prediction(
        {
            "ticker": "AAPL",
            "prediction": {
                "final_decision": "BEARISH",
                "price_at_prediction": 100.0,
                "target_price": 97.0,
            },
            "created_at": "2026-04-01T00:00:00+00:00",
            "source_agent": "SignalAggregatorAgent",
        }
    )

    async def fake_price_data(ticker, allow_scrape=False):
        return {
            "px": 95.0,
            "source_used": "cache_stale",
            "is_stale": True,
            "syncing": True,
            "is_estimated": False,
            "freshness_minutes": 300,
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }

    monkeypatch.setattr(
        "gateway.data_engine.data_engine.get_price_data",
        fake_price_data,
    )
    monkeypatch.setattr(
        "self_improvement.engine.settings.PREDICTION_SCORE_DELAY_HOURS",
        0,
    )
    precision = DirectionalPrecisionStore(str(db_path))
    accuracy = AccuracyStore(str(db_path))
    monkeypatch.setattr("self_improvement.engine.precision_store", precision)
    monkeypatch.setattr("self_improvement.engine.accuracy_store", accuracy)

    engine = SelfImprovementEngine(_MemoryStub(store))
    summary = await engine._evaluate_pending_predictions()
    records = await store.get_predictions_for_ticker("AAPL")

    assert summary["evaluated"] == 1
    assert summary["live_gate_eligible"] == 0
    assert summary["live_gate_rejected"] == 1
    assert records[0]["outcome"]["live_gate_evidence"]["eligible"] is False

    stats = precision.get_precision_stats(
        ticker="AAPL", model="SignalAggregatorAgent", direction="BEARISH"
    )
    assert stats["total_directional"] == 0


@pytest.mark.asyncio
async def test_accuracy_store_record_and_leaderboard():
    from self_improvement.accuracy_store import AccuracyStore

    tmp_dir = Path(__file__).resolve().parent.parent / "tmp"
    tmp_dir.mkdir(exist_ok=True)
    db_path = tmp_dir / f"accuracy_{uuid.uuid4().hex}.db"
    store = AccuracyStore(db_path=str(db_path))

    store.record_outcome("AAPL", "test_model", "nvidia_nim", "BULLISH", 0.95)
    store.record_outcome("AAPL", "test_model", "nvidia_nim", "BULLISH", 0.85)
    store.record_outcome("GOOGL", "test_model", "nvidia_nim", "BEARISH", 0.70)

    lb = store.get_leaderboard(group_by="ticker", limit=10)
    assert len(lb) == 2
    assert lb[0]["ticker"] == "AAPL"
    assert lb[0]["total_scored"] == 2
    assert round(lb[0]["avg_accuracy"], 2) == 0.90

    lb_dir = store.get_leaderboard(group_by="direction", limit=10)
    assert any(r["direction"] == "BULLISH" for r in lb_dir)
    assert any(r["direction"] == "BEARISH" for r in lb_dir)

    breakdown = store.get_ticker_breakdown("AAPL")
    assert len(breakdown) == 1
    assert breakdown[0]["best_score"] == 0.95
    assert breakdown[0]["worst_score"] == 0.85

    summary = store.get_summary()
    assert summary["tickers"] == 2
    assert summary["total_scored"] == 3


@pytest.mark.asyncio
async def test_accuracy_store_upsert():
    from self_improvement.accuracy_store import AccuracyStore

    tmp_dir = Path(__file__).resolve().parent.parent / "tmp"
    tmp_dir.mkdir(exist_ok=True)
    db_path = tmp_dir / f"accuracy_upsert_{uuid.uuid4().hex}.db"
    store = AccuracyStore(db_path=str(db_path))

    for accuracy in [0.8, 0.9, 1.0]:
        store.record_outcome("TSLA", "model_a", "lm_studio", "BULLISH", accuracy)

    breakdown = store.get_ticker_breakdown("TSLA")
    assert len(breakdown) == 1
    assert breakdown[0]["total_scored"] == 3
    assert round(breakdown[0]["avg_accuracy"], 4) == 0.9
    assert breakdown[0]["best_score"] == 1.0
    assert breakdown[0]["worst_score"] == 0.8
