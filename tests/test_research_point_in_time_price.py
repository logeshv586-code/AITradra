from datetime import datetime, timedelta, timezone


def _swap_store(tmp_path):
    from gateway import knowledge_store as ks_module
    from gateway.knowledge_store import KnowledgeStore

    store = KnowledgeStore(db_path=str(tmp_path / "price_replay.db"))
    original = ks_module.knowledge_store
    ks_module.knowledge_store = store
    return store, original


def _seed_daily(store, ticker: str, as_of: datetime):
    conn = store._get_conn()
    for offset in range(30, -1, -1):
        date = (as_of - timedelta(days=offset)).date().isoformat()
        price = 100.0 + (30 - offset)
        conn.execute(
            """
            INSERT OR REPLACE INTO daily_ohlcv
                (ticker, date, open, high, low, close, volume, adj_close, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (ticker, date, price, price, price, price, 1000, price, "test"),
        )
    conn.commit()


def _snapshot(store, ticker: str, price: float, created_at: str):
    store._get_conn().execute(
        """
        INSERT INTO market_snapshots
            (ticker, price, change_pct, volume, market_cap, pe_ratio, sector,
             signal, metadata_json, created_at)
        VALUES (?, ?, 0, 0, 0, 0, '', '', '{}', ?)
        """,
        (ticker, price, created_at),
    )
    store._get_conn().commit()


def test_same_day_final_daily_close_is_not_visible_intraday(tmp_path):
    store, original = _swap_store(tmp_path)
    try:
        as_of = datetime(2026, 1, 10, 12, tzinfo=timezone.utc)
        _seed_daily(store, "AAPL", as_of)

        from agents.research_council import ResearchCouncil

        context = ResearchCouncil()._price_context("AAPL", as_of)
        # Seeded Jan-10 close is 130, but an intraday Jan-10 replay must only see
        # the completed Jan-09 daily close (129) unless a timestamped snapshot exists.
        assert context["reference_kind"] == "prior_session_close"
        assert context["reference_price"] == 129.0
    finally:
        from gateway import knowledge_store as ks_module
        ks_module.knowledge_store = original


def test_snapshot_must_exist_before_as_of(tmp_path):
    store, original = _swap_store(tmp_path)
    try:
        as_of = datetime(2026, 1, 10, 12, tzinfo=timezone.utc)
        _seed_daily(store, "AAPL", as_of)
        _snapshot(store, "AAPL", 129.5, "2026-01-10 11:55:00")
        _snapshot(store, "AAPL", 999.0, "2026-01-10 13:00:00")

        from agents.research_council import ResearchCouncil

        context = ResearchCouncil()._price_context("AAPL", as_of)
        assert context["reference_kind"] == "timestamped_snapshot"
        assert context["reference_price"] == 129.5
        assert context["reference_observed_at"] <= as_of
    finally:
        from gateway import knowledge_store as ks_module
        ks_module.knowledge_store = original
