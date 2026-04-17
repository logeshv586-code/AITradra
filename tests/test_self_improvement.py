import sys
import uuid
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
    from self_improvement.engine import SelfImprovementEngine

    tmp_dir = Path(__file__).resolve().parent.parent / "tmp"
    tmp_dir.mkdir(exist_ok=True)
    log_path = tmp_dir / f"prediction_outcome_{uuid.uuid4().hex}.json"
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
        }
    )

    async def fake_price_data(ticker, allow_scrape=False):
        return {"px": 112.0, "source_used": "test_feed"}

    monkeypatch.setattr(
        "gateway.data_engine.data_engine.get_price_data",
        fake_price_data,
    )
    monkeypatch.setattr(
        "self_improvement.engine.settings.PREDICTION_SCORE_DELAY_HOURS",
        0,
    )

    engine = SelfImprovementEngine(_MemoryStub(store))
    summary = await engine._evaluate_pending_predictions()

    records = await store.get_predictions_for_ticker("AAPL")
    assert summary["evaluated"] == 1
    assert records[0]["accuracy_score"] == 1.0
    assert records[0]["actual_price"] == 112.0
    assert records[0]["outcome"]["direction"] == "BULLISH"


@pytest.mark.asyncio
async def test_accuracy_store_record_and_leaderboard():
    """AccuracyStore persists outcomes and returns correct leaderboard."""
    from self_improvement.accuracy_store import AccuracyStore

    tmp_dir = Path(__file__).resolve().parent.parent / "tmp"
    tmp_dir.mkdir(exist_ok=True)
    db_path = tmp_dir / f"accuracy_{uuid.uuid4().hex}.db"
    store = AccuracyStore(db_path=str(db_path))

    # Record multiple outcomes
    store.record_outcome("AAPL", "test_model", "nvidia_nim", "BULLISH", 0.95)
    store.record_outcome("AAPL", "test_model", "nvidia_nim", "BULLISH", 0.85)
    store.record_outcome("GOOGL", "test_model", "nvidia_nim", "BEARISH", 0.70)

    # Leaderboard by ticker
    lb = store.get_leaderboard(group_by="ticker", limit=10)
    assert len(lb) == 2
    # AAPL avg is (0.95 + 0.85) / 2 = 0.9 — should rank first
    assert lb[0]["ticker"] == "AAPL"
    assert lb[0]["total_scored"] == 2
    assert round(lb[0]["avg_accuracy"], 2) == 0.90

    # Leaderboard by direction
    lb_dir = store.get_leaderboard(group_by="direction", limit=10)
    assert any(r["direction"] == "BULLISH" for r in lb_dir)
    assert any(r["direction"] == "BEARISH" for r in lb_dir)

    # Ticker breakdown
    breakdown = store.get_ticker_breakdown("AAPL")
    assert len(breakdown) == 1
    assert breakdown[0]["best_score"] == 0.95
    assert breakdown[0]["worst_score"] == 0.85

    # Summary
    summary = store.get_summary()
    assert summary["tickers"] == 2
    assert summary["total_scored"] == 3


@pytest.mark.asyncio
async def test_accuracy_store_upsert():
    """AccuracyStore correctly upserts rather than duplicating rows."""
    from self_improvement.accuracy_store import AccuracyStore

    tmp_dir = Path(__file__).resolve().parent.parent / "tmp"
    tmp_dir.mkdir(exist_ok=True)
    db_path = tmp_dir / f"accuracy_upsert_{uuid.uuid4().hex}.db"
    store = AccuracyStore(db_path=str(db_path))

    for accuracy in [0.8, 0.9, 1.0]:
        store.record_outcome("TSLA", "model_a", "lm_studio", "BULLISH", accuracy)

    breakdown = store.get_ticker_breakdown("TSLA")
    assert len(breakdown) == 1  # single row, not 3 duplicates
    assert breakdown[0]["total_scored"] == 3
    assert round(breakdown[0]["avg_accuracy"], 4) == 0.9
    assert breakdown[0]["best_score"] == 1.0
    assert breakdown[0]["worst_score"] == 0.8
