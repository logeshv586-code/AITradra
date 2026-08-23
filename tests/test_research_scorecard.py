from datetime import datetime, timedelta, timezone


def _knowledge_db(tmp_path):
    from gateway.knowledge_store import KnowledgeStore

    return KnowledgeStore(db_path=str(tmp_path / "scorecard.db"))


def _future_prices(store, ticker: str, start_date: datetime, *, start: float, step: float):
    conn = store._get_conn()
    for session in range(1, 26):
        date = (start_date + timedelta(days=session)).date().isoformat()
        price = start + step * session
        conn.execute(
            """
            INSERT OR REPLACE INTO daily_ohlcv
                (ticker, date, open, high, low, close, volume, adj_close, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (ticker, date, price, price, price, price, 1000000, price, "future_test"),
        )
    conn.commit()


def _decision(**overrides):
    values = {
        "decision_id": "decision-aapl-1",
        "ticker": "AAPL",
        "as_of": "2026-01-10T12:00:00+00:00",
        "rating": "BUY",
        "verdict": "BUY",
        "confidence": 80,
        "directional_score": 0.7,
        "evidence_quality": 0.85,
        "evidence_count": 12,
        "source_diversity_score": 1.0,
        "created_at": "2026-01-10T12:00:01+00:00",
        "benchmark_context": {
            "benchmark": "SPY",
            "reference_price": 100.0,
            "reference_observed_at": "2026-01-10T11:55:00+00:00",
            "reference_kind": "timestamped_snapshot",
            "benchmark_reference_price": 200.0,
            "benchmark_reference_observed_at": "2026-01-10T11:55:00+00:00",
        },
    }
    values.update(overrides)
    return values


def test_scorecard_requires_timestamped_reference(tmp_path):
    store = _knowledge_db(tmp_path)
    from self_improvement.research_scorecard import ResearchScorecardStore

    scorecard = ResearchScorecardStore(store.db_path)
    weak = _decision(
        decision_id="prior-close-only",
        benchmark_context={
            "benchmark": "SPY",
            "reference_price": 100.0,
            "reference_observed_at": "2026-01-09T00:00:00+00:00",
            "reference_kind": "prior_session_close",
        },
    )
    assert scorecard.record_decision(weak) is True
    summary = scorecard.summary(horizon_sessions=1)
    assert summary["decisions_recorded"] == 1
    assert summary["audit_eligible_decisions"] == 0
    assert summary["resolved_active_decisions"] == 0
    assert summary["live_gate_input"] is False


def test_forward_outcome_evaluation_and_calibration(tmp_path):
    store = _knowledge_db(tmp_path)
    as_of = datetime(2026, 1, 10, 12, tzinfo=timezone.utc)
    _future_prices(store, "AAPL", as_of, start=100.0, step=1.0)
    _future_prices(store, "SPY", as_of, start=200.0, step=0.25)

    from self_improvement.research_scorecard import ResearchScorecardStore

    scorecard = ResearchScorecardStore(store.db_path)
    assert scorecard.record_decision(_decision()) is True
    assert scorecard.record_decision(_decision(confidence=10)) is False

    result = scorecard.evaluate_pending(
        horizons=(1, 5),
        now=datetime(2026, 2, 20, tzinfo=timezone.utc),
    )
    assert result["outcomes_added"] == 2

    one = scorecard.summary(horizon_sessions=1)
    assert one["audit_eligible_decisions"] == 1
    assert one["resolved_active_decisions"] == 1
    assert one["directional_hit_rate"] == 1.0
    assert one["average_return_pct"] > 0
    assert one["average_alpha_pct"] > 0
    assert one["brier_score"] == 0.04
    assert one["profitability_claim"] is False

    five = scorecard.summary(horizon_sessions=5)
    assert five["resolved_active_decisions"] == 1
    assert five["directional_hit_rate"] == 1.0


def test_bearish_decision_is_correct_only_when_later_price_falls(tmp_path):
    store = _knowledge_db(tmp_path)
    as_of = datetime(2026, 1, 10, 12, tzinfo=timezone.utc)
    _future_prices(store, "TSLA", as_of, start=100.0, step=-1.0)

    from self_improvement.research_scorecard import ResearchScorecardStore

    scorecard = ResearchScorecardStore(store.db_path)
    decision = _decision(
        decision_id="decision-tsla-short",
        ticker="TSLA",
        rating="UNDERWEIGHT",
        verdict="SELL",
        confidence=70,
        benchmark_context={
            "benchmark": None,
            "reference_price": 100.0,
            "reference_observed_at": "2026-01-10T11:55:00+00:00",
            "reference_kind": "timestamped_snapshot",
        },
    )
    assert scorecard.record_decision(decision)
    scorecard.evaluate_pending(
        horizons=(1,), now=datetime(2026, 2, 20, tzinfo=timezone.utc)
    )
    summary = scorecard.summary(horizon_sessions=1)
    assert summary["directional_hit_rate"] == 1.0
    assert summary["average_return_pct"] < 0
