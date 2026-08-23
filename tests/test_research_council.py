"""Offline invariants for Research Council V2.

These tests intentionally avoid LLM/network calls.  They verify the properties
that matter most for research correctness: no look-ahead, provenance-aware
selection, deduplication, uncertainty handling and zero execution authority.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone


def _swap_store(tmp_path):
    from gateway import knowledge_store as ks_module
    from gateway.knowledge_store import KnowledgeStore

    store = KnowledgeStore(db_path=str(tmp_path / "research.db"))
    original = ks_module.knowledge_store
    ks_module.knowledge_store = store
    return store, original


def _insert_insight(
    store,
    *,
    ticker="AAPL",
    agent="TechnicalSpecialist",
    kind="signal",
    content="BULLISH setup",
    confidence=0.8,
    source_urls='["https://example.com/evidence"]',
    created_at="2026-01-10 10:00:00",
):
    store._get_conn().execute(
        """
        INSERT INTO agent_insights
            (ticker, agent_name, insight_type, content, confidence, source_urls, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (ticker, agent, kind, content, confidence, source_urls, created_at),
    )
    store._get_conn().commit()


def _insert_news(
    store,
    *,
    ticker="AAPL",
    headline="AAPL demand improves",
    url="https://example.com/news/aapl",
    source="ExampleWire",
    sentiment=0.7,
    relevance=0.9,
    published_at="2026-01-10 09:00:00",
    created_at="2026-01-10 09:05:00",
):
    store._get_conn().execute(
        """
        INSERT INTO news_articles
            (ticker, headline, url, source, published_at, sentiment_score,
             relevance_score, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ticker,
            headline,
            url,
            source,
            published_at,
            sentiment,
            relevance,
            created_at,
        ),
    )
    store._get_conn().commit()


def _seed_prices(store, ticker: str, as_of: datetime, *, start=100.0, step=1.0):
    conn = store._get_conn()
    # Insert oldest -> newest; queries order most recent first.
    for offset in range(30, -1, -1):
        date = (as_of - timedelta(days=offset)).date().isoformat()
        close = start + (30 - offset) * step
        conn.execute(
            """
            INSERT OR REPLACE INTO daily_ohlcv
                (ticker, date, open, high, low, close, volume, adj_close, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (ticker, date, close, close, close, close, 1_000_000, close, "test_feed"),
        )
    conn.commit()


def test_point_in_time_pack_excludes_future_rows(tmp_path):
    store, original = _swap_store(tmp_path)
    try:
        as_of = datetime(2026, 1, 10, 12, tzinfo=timezone.utc)
        _insert_insight(
            store,
            content="BULLISH evidence available before decision",
            created_at="2026-01-10 10:00:00",
        )
        _insert_insight(
            store,
            content="BEARISH future evidence must never leak backward",
            created_at="2026-01-10 13:00:00",
        )
        _insert_news(
            store,
            headline="AAPL positive story before decision",
            published_at="2026-01-10 09:00:00",
            created_at="2026-01-10 09:05:00",
        )
        _insert_news(
            store,
            headline="AAPL negative future story",
            url="https://example.com/news/future",
            sentiment=-0.8,
            published_at="2026-01-10 14:00:00",
            created_at="2026-01-10 14:01:00",
        )

        from agents.research_council import ResearchCouncil

        pack = ResearchCouncil().build_evidence_pack("AAPL", as_of=as_of.isoformat())
        text = "\n".join(item.text for item in pack["items"])
        assert "available before decision" in text
        assert "positive story before decision" in text
        assert "future evidence" not in text
        assert "negative future story" not in text
        assert all(datetime.fromisoformat(item.observed_at) <= as_of for item in pack["items"])
    finally:
        from gateway import knowledge_store as ks_module
        ks_module.knowledge_store = original


def test_duplicate_news_url_counts_once(tmp_path):
    store, original = _swap_store(tmp_path)
    try:
        as_of = datetime(2026, 1, 10, 12, tzinfo=timezone.utc)
        _insert_news(store, headline="AAPL demand story version one")
        _insert_news(store, headline="AAPL demand story version two")

        from agents.research_council import ResearchCouncil

        pack = ResearchCouncil().build_evidence_pack("AAPL", as_of=as_of)
        matching = [
            item for item in pack["items"]
            if item.url == "https://example.com/news/aapl"
        ]
        assert len(matching) == 1
    finally:
        from gateway import knowledge_store as ks_module
        ks_module.knowledge_store = original


def test_narrow_single_agent_research_fails_closed_to_hold(tmp_path):
    store, original = _swap_store(tmp_path)
    try:
        for index in range(4):
            _insert_insight(
                store,
                content=f"BULLISH technical confirmation {index}",
                source_urls=f'["https://example.com/tech/{index}"]',
            )

        from agents.research_council import ResearchCouncil

        decision = asyncio.run(
            ResearchCouncil().analyze(
                "AAPL",
                as_of="2026-01-10T12:00:00+00:00",
                use_llm_debate=False,
                persist=False,
            )
        )
        assert decision.rating == "HOLD"
        assert decision.verdict == "HOLD"
        assert decision.execution_authority is False
        assert decision.live_gate_eligible is False
        assert decision.coverage_score < 2 / 6
        assert any("coverage" in reason.lower() for reason in decision.reasons)
    finally:
        from gateway import knowledge_store as ks_module
        ks_module.knowledge_store = original


def test_broad_fresh_provenance_support_can_produce_active_research_rating(tmp_path):
    store, original = _swap_store(tmp_path)
    try:
        as_of = datetime(2026, 1, 10, 12, tzinfo=timezone.utc)
        rows = [
            ("TechnicalSpecialist", "technical_signal", "BULLISH trend and momentum"),
            ("FundamentalSpecialist", "fundamental", "BULLISH valuation and cash flow"),
            ("MacroSpecialist", "macro", "BULLISH macro backdrop"),
            ("SentimentSpecialist", "sentiment", "BULLISH sentiment breadth"),
            ("RiskSpecialist", "risk", "BULLISH risk-adjusted setup within limits"),
        ]
        for index, (agent, kind, content) in enumerate(rows):
            _insert_insight(
                store,
                agent=agent,
                kind=kind,
                content=content,
                confidence=0.9,
                source_urls=f'["https://example.com/source/{index}"]',
                created_at="2026-01-10 11:00:00",
            )
        _insert_news(
            store,
            headline="AAPL catalyst has verifiable positive impact",
            url="https://example.com/catalyst",
            sentiment=0.8,
            relevance=0.95,
            published_at="2026-01-10 10:30:00",
            created_at="2026-01-10 10:31:00",
        )
        _seed_prices(store, "AAPL", as_of, start=100.0, step=1.0)
        _seed_prices(store, "SPY", as_of, start=100.0, step=0.2)

        from agents.research_council import ResearchCouncil

        decision = asyncio.run(
            ResearchCouncil().analyze(
                "AAPL",
                as_of=as_of.isoformat(),
                use_llm_debate=False,
                persist=False,
            )
        )
        assert decision.rating in {"BUY", "OVERWEIGHT"}
        assert decision.verdict == "BUY"
        assert decision.coverage_score == 1.0
        assert decision.evidence_quality >= 0.7
        assert decision.benchmark_context["available"] is True
        assert decision.benchmark_context["alpha_pct"] > 0
        assert decision.risk_advisory["execution_authority"] is False
        assert (
            decision.risk_advisory["research_exposure_ceiling_pct"]
            <= decision.risk_advisory["configured_max_position_pct"]
        )
    finally:
        from gateway import knowledge_store as ks_module
        ks_module.knowledge_store = original


def test_balanced_bull_bear_evidence_reduces_conviction(tmp_path):
    store, original = _swap_store(tmp_path)
    try:
        agents = [
            ("TechnicalSpecialist", "BULLISH technical evidence"),
            ("FundamentalSpecialist", "BULLISH fundamental evidence"),
            ("MacroSpecialist", "BULLISH macro evidence"),
            ("SentimentSpecialist", "BEARISH sentiment evidence"),
            ("RiskSpecialist", "BEARISH risk evidence"),
            ("SectorSpecialist", "BEARISH sector evidence"),
        ]
        for index, (agent, content) in enumerate(agents):
            _insert_insight(
                store,
                agent=agent,
                kind="signal",
                content=content,
                confidence=0.9,
                source_urls=f'["https://example.com/conflict/{index}"]',
            )

        from agents.research_council import ResearchCouncil

        decision = asyncio.run(
            ResearchCouncil().analyze(
                "AAPL",
                as_of="2026-01-10T12:00:00+00:00",
                use_llm_debate=False,
                persist=False,
            )
        )
        assert decision.rating == "HOLD"
        assert decision.contradiction_score >= 0.8
        assert decision.confidence < 70
    finally:
        from gateway import knowledge_store as ks_module
        ks_module.knowledge_store = original
