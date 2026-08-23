from __future__ import annotations

from datetime import datetime, timedelta, timezone


def _init_db(path):
    from gateway.knowledge_store import KnowledgeStore
    from self_improvement.research_scorecard import ResearchScorecardStore

    knowledge = KnowledgeStore(db_path=str(path))
    ResearchScorecardStore(str(path))
    return knowledge


def _insert_resolved(
    knowledge,
    *,
    index: int,
    correct: bool,
    confidence: float,
    quality: float,
    diversity: float,
    directional_score: float,
    horizon: int = 5,
):
    as_of = datetime(2026, 1, 1, 12, tzinfo=timezone.utc) + timedelta(days=index)
    decision_id = f"decision-{index:03d}"
    conn = knowledge._get_conn()
    conn.execute(
        """
        INSERT INTO research_decisions_v2 (
            decision_id, ticker, as_of, rating, verdict, confidence,
            directional_score, evidence_quality, evidence_count,
            source_diversity_score, benchmark, reference_price,
            reference_observed_at, reference_kind,
            benchmark_reference_price, benchmark_reference_observed_at,
            audit_eligible, created_at
        ) VALUES (?, 'AAPL', ?, 'BUY', 'BUY', ?, ?, ?, 8, ?, 'SPY',
                  100, ?, 'timestamped_snapshot', 200, ?, 1, ?)
        """,
        (
            decision_id,
            as_of.isoformat(),
            confidence,
            directional_score,
            quality,
            diversity,
            (as_of - timedelta(minutes=5)).isoformat(),
            (as_of - timedelta(minutes=5)).isoformat(),
            as_of.isoformat(),
        ),
    )
    return_pct = 2.0 if correct else -2.0
    alpha_pct = 1.0 if correct else -1.0
    conn.execute(
        """
        INSERT INTO research_outcomes_v2 (
            decision_id, horizon_sessions, ticker, target_date, target_price,
            return_pct, benchmark, benchmark_target_price,
            benchmark_return_pct, alpha_pct, direction_correct,
            alpha_direction_correct, brier_score, resolved_at
        ) VALUES (?, ?, 'AAPL', ?, ?, ?, 'SPY', ?, 1.0, ?, ?, ?, ?, ?)
        """,
        (
            decision_id,
            horizon,
            (as_of + timedelta(days=horizon)).date().isoformat(),
            100 + return_pct,
            return_pct,
            202.0,
            alpha_pct,
            1 if correct else 0,
            1 if correct else 0,
            (confidence / 100.0 - (1.0 if correct else 0.0)) ** 2,
            (as_of + timedelta(days=horizon + 1)).isoformat(),
        ),
    )
    conn.commit()


def _seed_walk_forward(path, *, future_correct: bool):
    knowledge = _init_db(path)
    # Training history: weak rows are noisy; strong rows are consistently better.
    for index in range(40):
        strong = index % 2 == 1
        if strong:
            correct = index % 10 != 9  # 80% in this deterministic synthetic set.
            _insert_resolved(
                knowledge,
                index=index,
                correct=correct,
                confidence=82,
                quality=0.82,
                diversity=1.0,
                directional_score=0.68,
            )
        else:
            correct = index % 4 == 0
            _insert_resolved(
                knowledge,
                index=index,
                correct=correct,
                confidence=55,
                quality=0.50,
                diversity=0.50,
                directional_score=0.30,
            )

    # First test block. Deliberately vary only these future outcomes between DBs.
    for index in range(40, 50):
        _insert_resolved(
            knowledge,
            index=index,
            correct=future_correct,
            confidence=82,
            quality=0.82,
            diversity=1.0,
            directional_score=0.68,
        )
    return knowledge


def test_walk_forward_reports_insufficient_evidence_instead_of_overfitting(tmp_path):
    knowledge = _init_db(tmp_path / "small.db")
    for index in range(12):
        _insert_resolved(
            knowledge,
            index=index,
            correct=True,
            confidence=80,
            quality=0.8,
            diversity=1.0,
            directional_score=0.7,
        )

    from self_improvement.research_robustness import ResearchRobustnessLab

    result = ResearchRobustnessLab(knowledge.db_path).walk_forward(
        horizon_sessions=5,
        min_train=30,
        test_size=10,
    )
    assert result["status"] == "insufficient_evidence"
    assert result["resolved_decisions"] == 12
    assert result["live_gate_input"] is False


def test_walk_forward_policy_selection_cannot_see_future_test_outcomes(tmp_path):
    good_future = _seed_walk_forward(tmp_path / "future_good.db", future_correct=True)
    bad_future = _seed_walk_forward(tmp_path / "future_bad.db", future_correct=False)

    from self_improvement.research_robustness import ResearchRobustnessLab

    good = ResearchRobustnessLab(good_future.db_path).walk_forward(
        horizon_sessions=5,
        min_train=40,
        test_size=10,
        min_train_accepted=10,
    )
    bad = ResearchRobustnessLab(bad_future.db_path).walk_forward(
        horizon_sessions=5,
        min_train=40,
        test_size=10,
        min_train_accepted=10,
    )

    first_good = good["folds"][0]
    first_bad = bad["folds"][0]
    # The training rows are byte-for-byte equivalent; only later test outcomes differ.
    # Policy selection must therefore be identical.
    assert first_good["selected_policy"] == first_bad["selected_policy"]
    assert first_good["train_objective"] == first_bad["train_objective"]
    assert first_good["train_end_as_of"] < first_good["test_start_as_of"]
    # The resulting OOS measurement is allowed to differ because the future differs.
    assert first_good["test_stats"]["hit_rate"] == 1.0
    assert first_bad["test_stats"]["hit_rate"] == 0.0
    assert good["live_gate_input"] is False


def test_regime_classification_ignores_post_decision_prices(tmp_path):
    knowledge = _init_db(tmp_path / "regime.db")
    as_of = datetime(2026, 5, 1, 12, tzinfo=timezone.utc)
    conn = knowledge._get_conn()
    # Strong prior 20-session uptrend.
    for offset in range(30, 0, -1):
        date = (as_of - timedelta(days=offset)).date().isoformat()
        price = 100 + (30 - offset) * 1.0
        conn.execute(
            """
            INSERT OR REPLACE INTO daily_ohlcv
                (ticker, date, open, high, low, close, volume, adj_close, source)
            VALUES ('SPY', ?, ?, ?, ?, ?, 1000, ?, 'test')
            """,
            (date, price, price, price, price, price),
        )
    # Catastrophic future prices must not influence the pre-decision regime.
    for offset in range(1, 6):
        date = (as_of + timedelta(days=offset)).date().isoformat()
        price = 20 - offset
        conn.execute(
            """
            INSERT OR REPLACE INTO daily_ohlcv
                (ticker, date, open, high, low, close, volume, adj_close, source)
            VALUES ('SPY', ?, ?, ?, ?, ?, 1000, ?, 'future')
            """,
            (date, price, price, price, price, price),
        )
    conn.commit()

    from self_improvement.research_robustness import ResearchRobustnessLab

    regime = ResearchRobustnessLab(knowledge.db_path).classify_regime(
        {"ticker": "AAPL", "benchmark": "SPY", "as_of": as_of.isoformat()}
    )
    assert regime["available"] is True
    assert regime["trend"] == "BULL"
    assert regime["trend_return_pct"] > 5


def test_signed_performance_handles_short_research_correctly():
    from self_improvement.research_robustness import ResearchRobustnessLab

    rows = [
        {
            "rating": "BUY",
            "return_pct": 3,
            "alpha_pct": 1,
            "direction_correct": 1,
            "alpha_direction_correct": 1,
            "confidence": 80,
            "brier_score": 0.04,
        },
        {
            "rating": "SELL",
            "return_pct": -5,
            "alpha_pct": -2,
            "direction_correct": 1,
            "alpha_direction_correct": 1,
            "confidence": 80,
            "brier_score": 0.04,
        },
    ]
    stats = ResearchRobustnessLab._stats(rows)
    assert stats["hit_rate"] == 1.0
    assert stats["average_signed_return_pct"] == 4.0
    assert stats["average_signed_alpha_pct"] == 1.5


def test_category_and_source_ablation_exposes_fragile_research(tmp_path, monkeypatch):
    from gateway.knowledge_store import KnowledgeStore
    import gateway.knowledge_store as ks_module

    store = KnowledgeStore(db_path=str(tmp_path / "ablation.db"))
    monkeypatch.setattr(ks_module, "knowledge_store", store)
    conn = store._get_conn()
    as_of = datetime(2026, 1, 10, 12, tzinfo=timezone.utc)
    rows = [
        ("TechnicalSpecialist", "technical_signal", "BULLISH trend", "tech"),
        ("FundamentalSpecialist", "fundamental", "BULLISH cash flow", "fund"),
        ("MacroSpecialist", "macro", "BULLISH macro", "macro"),
    ]
    for agent, kind, content, slug in rows:
        conn.execute(
            """
            INSERT INTO agent_insights
                (ticker, agent_name, insight_type, content, confidence,
                 source_urls, created_at)
            VALUES ('AAPL', ?, ?, ?, 0.95, ?, '2026-01-10 11:00:00')
            """,
            (agent, kind, content, f'["https://example.com/{slug}"]'),
        )
    conn.commit()

    from self_improvement.research_robustness import ResearchRobustnessLab

    result = ResearchRobustnessLab(store.db_path).ablation(
        "AAPL", as_of=as_of.isoformat()
    )
    assert result["baseline"]["rating"] in {"BUY", "OVERWEIGHT"}
    assert result["fragile"] is True
    assert result["category_flip_rate"] > 0
    assert result["source_flip_rate"] > 0
    assert result["execution_authority"] is False
    assert result["live_gate_input"] is False
