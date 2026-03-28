"""Persistent Knowledge Store — SQLite-backed data warehouse for all market intelligence."""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Optional
from core.logger import get_logger

logger = get_logger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "axiom_knowledge.db")


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

            CREATE TABLE IF NOT EXISTS collection_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                data_type TEXT NOT NULL,
                last_collected TEXT,
                records_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                UNIQUE(ticker, data_type)
            );

            CREATE INDEX IF NOT EXISTS idx_ohlcv_ticker_date ON daily_ohlcv(ticker, date);
            CREATE INDEX IF NOT EXISTS idx_news_ticker ON news_articles(ticker);
            CREATE INDEX IF NOT EXISTS idx_news_published ON news_articles(published_at);
            CREATE INDEX IF NOT EXISTS idx_snapshots_ticker ON market_snapshots(ticker, created_at);
            CREATE INDEX IF NOT EXISTS idx_insights_ticker ON agent_insights(ticker, created_at);
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

    def get_insights(self, ticker: str, limit: int = 20) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT agent_name, insight_type, content, confidence, source_urls, created_at
            FROM agent_insights WHERE ticker = ?
            ORDER BY created_at DESC LIMIT ?
        """, (ticker, limit)).fetchall()
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

        return {
            "total_ohlcv_records": ohlcv_count,
            "total_news_articles": news_count,
            "total_snapshots": snapshot_count,
            "total_insights": insight_count,
            "tickers_with_ohlcv": tickers_with_data,
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


# Global singleton
knowledge_store = KnowledgeStore()
