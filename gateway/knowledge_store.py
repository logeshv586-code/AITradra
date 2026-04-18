"""Persistent Knowledge Store — SQLite-backed data warehouse for all market intelligence."""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Optional
from core.logger import get_logger

logger = get_logger(__name__)

from core.config import settings

DB_PATH = settings.KNOWLEDGE_DB_PATH

# Agentic platform hooks (lazy imports to avoid circular deps)
_move_explainer = None
_market_rag = None

def _get_move_explainer():
    global _move_explainer
    if _move_explainer is None:
        try:
            from agents.move_explainer import get_agent as _me
            _move_explainer = _me()
        except Exception as e:
            logger.debug(f"MoveExplainer not available: {e}")
    return _move_explainer

def _get_market_rag():
    global _market_rag
    if _market_rag is None:
        try:
            from agents.market_rag import get_agent as _mr
            _market_rag = _mr()
        except Exception as e:
            logger.debug(f"MarketRAG not available: {e}")
    return _market_rag


class KnowledgeStore:
    """
    Persistent SQLite warehouse storing:
    - Daily OHLCV data (5-year+ history per ticker)
    - News articles (scraped RSS/web with headline, body, source URL)
    - Market snapshots (periodic price/sentiment captures)
    - Agent insights (analysis outputs for RAG retrieval)
    
    Data is NEVER deleted, only appended. Queries support time ranges.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._conn = None
        self._ensure_schema()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
        return self._conn

    def _ensure_schema(self):
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS daily_ohlcv (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL, high REAL, low REAL, close REAL,
                volume INTEGER,
                adj_close REAL,
                source TEXT DEFAULT 'yfinance',
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(ticker, date)
            );
            
            CREATE TABLE IF NOT EXISTS news_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT,
                headline TEXT NOT NULL,
                summary TEXT,
                body TEXT,
                url TEXT,
                source TEXT,
                published_at TEXT,
                sentiment_score REAL DEFAULT 0.0,
                relevance_score REAL DEFAULT 0.0,
                embedding_indexed INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );
            
            CREATE TABLE IF NOT EXISTS market_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                price REAL,
                change_pct REAL,
                volume INTEGER,
                market_cap REAL,
                pe_ratio REAL,
                sector TEXT,
                signal TEXT,
                metadata_json TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            
            CREATE TABLE IF NOT EXISTS agent_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                insight_type TEXT,
                content TEXT NOT NULL,
                confidence REAL DEFAULT 0.0,
                source_urls TEXT,
                embedding_indexed INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS agent_episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                task TEXT NOT NULL,
                status TEXT DEFAULT 'running',
                state_json TEXT,
                result_json TEXT,
                error_log TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS collection_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                data_type TEXT NOT NULL,
                last_collected TEXT,
                records_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                UNIQUE(ticker, data_type)
            );

            CREATE TABLE IF NOT EXISTS agent_health (
                agent_name TEXT PRIMARY KEY,
                last_seen TEXT DEFAULT (datetime('now')),
                latency_ms INTEGER DEFAULT 0,
                status TEXT DEFAULT 'idle',
                current_task TEXT,
                error_count INTEGER DEFAULT 0,
                version TEXT
            );

            CREATE TABLE IF NOT EXISTS research_suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                score REAL,
                signal TEXT,
                reasoning TEXT,
                breakdown_json TEXT,
                perf_1m REAL,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS ticker_intelligence (
                ticker TEXT PRIMARY KEY,
                recommendation TEXT,
                should_invest INTEGER DEFAULT 0,
                prediction_direction TEXT,
                confidence_score REAL DEFAULT 0.0,
                expected_move_percent REAL DEFAULT 0.0,
                risk_level TEXT,
                primary_driver TEXT,
                updated_at TEXT DEFAULT (datetime('now')),
                snapshot_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_ohlcv_ticker_date ON daily_ohlcv(ticker, date);
            CREATE INDEX IF NOT EXISTS idx_news_ticker ON news_articles(ticker);
            CREATE INDEX IF NOT EXISTS idx_news_published ON news_articles(published_at);
            CREATE INDEX IF NOT EXISTS idx_snapshots_ticker ON market_snapshots(ticker, created_at);
            CREATE INDEX IF NOT EXISTS idx_insights_ticker ON agent_insights(ticker, created_at);
            CREATE INDEX IF NOT EXISTS idx_episodes_session ON agent_episodes(session_id);
            CREATE INDEX IF NOT EXISTS idx_ticker_intelligence_updated ON ticker_intelligence(updated_at);
        """)
        conn.commit()
        logger.info(f"Knowledge store initialized at {self.db_path}")

    # ─── OHLCV ────────────────────────────────────────────────────────────────

    def store_daily_ohlcv(self, ticker: str, records: list[dict]) -> int:
        """
        Store daily OHLCV records. Uses INSERT OR IGNORE for idempotency.
        records: [{"date": "2024-01-15", "open": 100, "high": 105, ...}, ...]
        Returns count of newly inserted records.
        """
        conn = self._get_conn()
        inserted = 0
        for r in records:
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO daily_ohlcv (ticker, date, open, high, low, close, volume, adj_close)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (ticker, r["date"], r.get("open"), r.get("high"), r.get("low"),
                      r.get("close"), r.get("volume"), r.get("adj_close", r.get("close"))))
                inserted += conn.total_changes
            except Exception as e:
                logger.warning(f"OHLCV insert error for {ticker}/{r.get('date')}: {e}")
        conn.commit()
        self._update_collection_status(ticker, "ohlcv", inserted)

        # Trigger MoveExplainer if significant price movement (only if we have recent data)
        if inserted > 0 and records:
            latest = records[-1]
            latest_close = latest.get("close")
            if latest_close:
                me = _get_move_explainer()
                if me:
                    try:
                        me.on_market_update(ticker, float(latest_close))
                    except Exception as e:
                        logger.debug(f"MoveExplainer trigger skipped: {e}")

        return inserted

    def get_ohlcv_history(self, ticker: str, days: int = 365 * 5) -> list[dict]:
        """Get OHLCV history for a ticker, most recent first."""
        conn = self._get_conn()
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = conn.execute("""
            SELECT date, open, high, low, close, volume FROM daily_ohlcv
            WHERE ticker = ? AND date >= ?
            ORDER BY date DESC
        """, (ticker, cutoff)).fetchall()
        return [dict(r) for r in rows]

    # ─── News ─────────────────────────────────────────────────────────────────

    def store_news(self, articles: list[dict]) -> int:
        """Store news articles. Deduplicates by headline+source."""
        conn = self._get_conn()
        inserted = 0
        for a in articles:
            try:
                # Check for duplicate
                existing = conn.execute(
                    "SELECT id FROM news_articles WHERE headline = ? AND source = ?",
                    (a.get("headline", ""), a.get("source", ""))
                ).fetchone()
                if existing:
                    continue
                conn.execute("""
                    INSERT INTO news_articles (ticker, headline, summary, body, url, source, published_at, sentiment_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (a.get("ticker"), a.get("headline"), a.get("summary"), a.get("body"),
                      a.get("url"), a.get("source"), a.get("published_at"), a.get("sentiment_score", 0.0)))
                inserted += 1

                # Index in MarketRAG for semantic search
                if inserted > 0:
                    mr = _get_market_rag()
                    if mr:
                        try:
                            news_id = conn.lastrowid
                            mr.index_news(news_id, a.get("ticker"), a.get("headline"), {"source": a.get("source")})
                        except Exception as e:
                            logger.debug(f"MarketRAG news indexing skipped: {e}")
            except Exception as e:
                logger.warning(f"News insert error: {e}")
        conn.commit()
        return inserted

    def get_news_for_ticker(self, ticker: str, limit: int = 20, days: int = 7) -> list[dict]:
        """Get recent news articles mentioning a ticker."""
        conn = self._get_conn()
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = conn.execute("""
            SELECT headline, summary, url, source, published_at, sentiment_score
            FROM news_articles
            WHERE (ticker = ? OR headline LIKE ?)
            AND created_at >= ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (ticker, f"%{ticker}%", cutoff, limit)).fetchall()
        return [dict(r) for r in rows]

    def get_unindexed_news(self, limit: int = 100) -> list[dict]:
        """Get news articles not yet indexed in FAISS."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT id, ticker, headline, summary, url, source, published_at
            FROM news_articles WHERE embedding_indexed = 0
            ORDER BY created_at DESC LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]

    def mark_news_indexed(self, article_ids: list[int]):
        """Mark articles as indexed in FAISS."""
        conn = self._get_conn()
        conn.executemany(
            "UPDATE news_articles SET embedding_indexed = 1 WHERE id = ?",
            [(aid,) for aid in article_ids]
        )
        conn.commit()

    # ─── Market Snapshots ─────────────────────────────────────────────────────

    def store_snapshot(self, ticker: str, data: dict):
        """Store a market snapshot."""
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO market_snapshots (ticker, price, change_pct, volume, market_cap, pe_ratio, sector, signal, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (ticker, data.get("px"), data.get("chg"), data.get("volume"),
              data.get("market_cap"), data.get("pe"), data.get("sector"),
              data.get("signal"), json.dumps(data)))
        conn.commit()

    def get_snapshots(self, ticker: str, limit: int = 50) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT * FROM market_snapshots WHERE ticker = ?
            ORDER BY created_at DESC LIMIT ?
        """, (ticker, limit)).fetchall()
        return [dict(r) for r in rows]

    # ─── Agent Insights ───────────────────────────────────────────────────────

    def store_insight(self, ticker: str, agent_name: str, insight_type: str,
                      content: str, confidence: float = 0.0, source_urls: list[str] = None):
        """Store an agent-generated insight."""
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO agent_insights (ticker, agent_name, insight_type, content, confidence, source_urls)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (ticker, agent_name, insight_type, content, confidence,
              json.dumps(source_urls) if source_urls else None))
        conn.commit()

        # Index in MarketRAG for semantic search
        mr = _get_market_rag()
        if mr:
            try:
                insight_id = conn.lastrowid
                mr.index_insight(insight_id, ticker, content, {"agent": agent_name, "type": insight_type})
            except Exception as e:
                logger.debug(f"MarketRAG insight indexing skipped: {e}")

    def get_insights(self, ticker: str, limit: int = 20) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT agent_name, insight_type, content, confidence, source_urls, created_at
            FROM agent_insights WHERE ticker = ?
            ORDER BY created_at DESC LIMIT ?
        """, (ticker, limit)).fetchall()
        return [dict(r) for r in rows]

    def get_recent_insights(self, ticker: str, hours: int = 24, limit: int = 50) -> list[dict]:
        """Get insights for a ticker within the last N hours."""
        conn = self._get_conn()
        cutoff = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
        rows = conn.execute("""
            SELECT agent_name, insight_type, content, confidence, source_urls, created_at
            FROM agent_insights 
            WHERE ticker = ? AND created_at >= ?
            ORDER BY created_at DESC LIMIT ?
        """, (ticker, cutoff, limit)).fetchall()
        return [dict(r) for r in rows]

    def get_unindexed_insights(self, limit: int = 100) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT id, ticker, agent_name, content, source_urls
            FROM agent_insights WHERE embedding_indexed = 0
            ORDER BY created_at DESC LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]

    def mark_insights_indexed(self, insight_ids: list[int]):
        conn = self._get_conn()
        conn.executemany(
            "UPDATE agent_insights SET embedding_indexed = 1 WHERE id = ?",
            [(iid,) for iid in insight_ids]
        )
        conn.commit()

    # ─── Agent Episodes (Mission Control / Checkpoints) ───────────────────────

    def store_episode_start(self, session_id: str, agent_name: str, task: str):
        """Initialize a new agent episode."""
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO agent_episodes (session_id, agent_name, task, status)
            VALUES (?, ?, ?, 'running')
        """, (session_id, agent_name, task))
        conn.commit()

    def update_episode_checkpoint(self, session_id: str, agent_name: str, state_dict: dict):
        """Update the current state of an episode for resuming."""
        conn = self._get_conn()
        conn.execute("""
            UPDATE agent_episodes 
            SET state_json = ?, updated_at = datetime('now')
            WHERE session_id = ? AND agent_name = ?
        """, (json.dumps(state_dict), session_id, agent_name))
        conn.commit()

    def complete_episode(self, session_id: str, agent_name: str, result: dict):
        """Mark episode as complete and store result."""
        conn = self._get_conn()
        conn.execute("""
            UPDATE agent_episodes 
            SET status = 'complete', result_json = ?, updated_at = datetime('now')
            WHERE session_id = ? AND agent_name = ?
        """, (json.dumps(result), session_id, agent_name))
        conn.commit()

    def fail_episode(self, session_id: str, agent_name: str, error: str):
        """Mark episode as failed and log error."""
        conn = self._get_conn()
        conn.execute("""
            UPDATE agent_episodes 
            SET status = 'failed', error_log = ?, updated_at = datetime('now')
            WHERE session_id = ? AND agent_name = ?
        """, (error, session_id, agent_name))
        conn.commit()

    def get_episode_state(self, session_id: str, agent_name: str) -> Optional[dict]:
        """Retrieve the last checkpoint for an episode."""
        conn = self._get_conn()
        row = conn.execute("""
            SELECT state_json FROM agent_episodes 
            WHERE session_id = ? AND agent_name = ?
            ORDER BY updated_at DESC LIMIT 1
        """, (session_id, agent_name)).fetchone()
        if row and row["state_json"]:
            return json.loads(row["state_json"])
        return None

    def get_active_episodes(self) -> list[dict]:
        """Get all currently running episodes."""
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM agent_episodes WHERE status = 'running'").fetchall()
        return [dict(r) for r in rows]

    # ─── Collection Status ────────────────────────────────────────────────────

    def _update_collection_status(self, ticker: str, data_type: str, count: int):
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO collection_status (ticker, data_type, last_collected, records_count, status)
            VALUES (?, ?, datetime('now'), ?, 'complete')
            ON CONFLICT(ticker, data_type) DO UPDATE SET
                last_collected = datetime('now'),
                records_count = records_count + ?,
                status = 'complete'
        """, (ticker, data_type, count, count))
        conn.commit()

    def get_collection_status(self) -> dict:
        """Get overall data collection status summary."""
        conn = self._get_conn()
        ohlcv_count = conn.execute("SELECT COUNT(*) FROM daily_ohlcv").fetchone()[0]
        news_count = conn.execute("SELECT COUNT(*) FROM news_articles").fetchone()[0]
        snapshot_count = conn.execute("SELECT COUNT(*) FROM market_snapshots").fetchone()[0]
        insight_count = conn.execute("SELECT COUNT(*) FROM agent_insights").fetchone()[0]
        tickers_with_data = conn.execute("SELECT COUNT(DISTINCT ticker) FROM daily_ohlcv").fetchone()[0]
        intelligence_count = conn.execute("SELECT COUNT(*) FROM ticker_intelligence").fetchone()[0]

        return {
            "total_ohlcv_records": ohlcv_count,
            "total_news_articles": news_count,
            "total_snapshots": snapshot_count,
            "total_insights": insight_count,
            "tickers_with_ohlcv": tickers_with_data,
            "tickers_with_intelligence": intelligence_count,
            "db_path": self.db_path,
            "db_size_mb": round(os.path.getsize(self.db_path) / 1024 / 1024, 2) if os.path.exists(self.db_path) else 0
        }

    # ─── Full-Text Search ─────────────────────────────────────────────────────

    def search_all(self, query: str, limit: int = 20) -> list[dict]:
        """Search across news, insights, and snapshots by keyword."""
        conn = self._get_conn()
        results = []

        # Search news
        news = conn.execute("""
            SELECT 'news' as type, headline as title, summary as content, url, source, published_at as timestamp
            FROM news_articles
            WHERE headline LIKE ? OR summary LIKE ?
            ORDER BY created_at DESC LIMIT ?
        """, (f"%{query}%", f"%{query}%", limit)).fetchall()
        results.extend([dict(r) for r in news])

        # Search insights
        insights = conn.execute("""
            SELECT 'insight' as type, agent_name || ': ' || insight_type as title,
                   content, source_urls as url, agent_name as source, created_at as timestamp
            FROM agent_insights
            WHERE content LIKE ? OR ticker LIKE ?
            ORDER BY created_at DESC LIMIT ?
        """, (f"%{query}%", f"%{query}%", limit)).fetchall()
        results.extend([dict(r) for r in insights])

        return results[:limit]

    # ─── AGENT HEALTH ─────────────────────────────────────────────────────────

    def update_agent_health(self, name: str, status: str, latency_ms: int = 0, task: str = None, error: bool = False):
        """Update real-time health metrics for an agent."""
        conn = self._get_conn()
        now = datetime.now().isoformat()
        err_inc = 1 if error else 0
        
        conn.execute("""
            INSERT INTO agent_health (agent_name, last_seen, status, latency_ms, current_task, error_count)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(agent_name) DO UPDATE SET
                last_seen = excluded.last_seen,
                status = excluded.status,
                latency_ms = excluded.latency_ms,
                current_task = COALESCE(excluded.current_task, agent_health.current_task),
                error_count = agent_health.error_count + ?
        """, (name, now, status, latency_ms, task, err_inc, err_inc))
        conn.commit()

    def get_all_agent_health(self) -> list[dict]:
        """Fetch health metrics for all agents."""
        conn = self._get_conn()
        cursor = conn.execute("SELECT * FROM agent_health ORDER BY agent_name ASC")
        return [dict(row) for row in cursor.fetchall()]

    # ─── RESEARCH SUGGESTIONS ──────────────────────────────────────────────────

    def store_research_suggestion(self, ticker: str, score: float, signal: str, reasoning: str, breakdown: dict, perf_1m: float):
        """Store a high-conviction research suggestion."""
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO research_suggestions (ticker, score, signal, reasoning, breakdown_json, perf_1m)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (ticker, score, signal, reasoning, json.dumps(breakdown), perf_1m))
        conn.commit()

    def get_latest_research_suggestions(self, limit: int = 5) -> list[dict]:
        """Fetch latest deep research suggestions."""
        conn = self._get_conn()
        cursor = conn.execute("""
            SELECT * FROM research_suggestions ORDER BY created_at DESC LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]

    # ───────────────────────────────────────────────────────────────────────
    # Ticker Intelligence
    # ───────────────────────────────────────────────────────────────────────

    def store_ticker_intelligence(self, ticker: str, snapshot: dict):
        """Store the latest normalized intelligence snapshot for a ticker."""
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO ticker_intelligence (
                ticker, recommendation, should_invest, prediction_direction,
                confidence_score, expected_move_percent, risk_level,
                primary_driver, updated_at, snapshot_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)
            ON CONFLICT(ticker) DO UPDATE SET
                recommendation = excluded.recommendation,
                should_invest = excluded.should_invest,
                prediction_direction = excluded.prediction_direction,
                confidence_score = excluded.confidence_score,
                expected_move_percent = excluded.expected_move_percent,
                risk_level = excluded.risk_level,
                primary_driver = excluded.primary_driver,
                updated_at = datetime('now'),
                snapshot_json = excluded.snapshot_json
        """, (
            ticker,
            snapshot.get("recommendation"),
            1 if snapshot.get("should_invest") else 0,
            snapshot.get("prediction_direction"),
            snapshot.get("confidence_score", 0.0),
            snapshot.get("expected_move_percent", 0.0),
            snapshot.get("risk_level"),
            snapshot.get("primary_driver"),
            json.dumps(snapshot),
        ))
        conn.commit()

    def get_ticker_intelligence(self, ticker: str) -> Optional[dict]:
        """Return the latest intelligence snapshot for a ticker."""
        conn = self._get_conn()
        row = conn.execute("""
            SELECT snapshot_json FROM ticker_intelligence WHERE ticker = ?
        """, (ticker,)).fetchone()
        if not row:
            return None
        try:
            return json.loads(row["snapshot_json"])
        except Exception as e:
            logger.warning(f"Failed to decode intelligence snapshot for {ticker}: {e}")
            return None

    def get_all_ticker_intelligence(self, tickers: Optional[list[str]] = None, limit: int = 500) -> list[dict]:
        """Return intelligence snapshots for many tickers, newest first."""
        conn = self._get_conn()
        if tickers:
            placeholders = ",".join("?" for _ in tickers)
            rows = conn.execute(f"""
                SELECT snapshot_json
                FROM ticker_intelligence
                WHERE ticker IN ({placeholders})
                ORDER BY updated_at DESC
                LIMIT ?
            """, (*tickers, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT snapshot_json
                FROM ticker_intelligence
                ORDER BY updated_at DESC
                LIMIT ?
            """, (limit,)).fetchall()

        snapshots = []
        for row in rows:
            try:
                snapshots.append(json.loads(row["snapshot_json"]))
            except Exception as e:
                logger.warning(f"Failed to decode one intelligence snapshot: {e}")
        return snapshots

knowledge_store = KnowledgeStore()
