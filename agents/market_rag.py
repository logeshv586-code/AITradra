"""
agents/market_rag.py
────────────────────────────────────────────────────────────────────────────────
MarketRAGAgent — AITradra's institutional memory and Q&A engine.

What it does:
  1. INDEXING  — On every agent_insights write, embeds the insight text and
                 upserts the vector into Qdrant collection "market_memory".
                 Also indexes news headlines from news_articles on schedule.

  2. RETRIEVAL — Given a natural-language question (optionally scoped to a
                 symbol), retrieves the top-k most semantically relevant
                 chunks from Qdrant, then fetches the raw OHLCV rows and
                 agent_insights records that match those chunks from SQLite.

  3. ANSWER    — Calls the configured LLM with a structured RAG prompt that
                 injects the retrieved context. Streams the answer token-by-
                 token as Server-Sent Events (SSE) for the /ask endpoint.

Embedding strategy (priority order):
  1. LM Studio /v1/embeddings  — uses the same local server already running.
  2. SentenceTransformer        — if sentence-transformers is installed.
  3. Hash-embed fallback        — deterministic, offline, good for testing.

Qdrant setup:
  - Local server  : set QDRANT_URL=http://localhost:6333
  - In-memory     : set QDRANT_MODE=memory  (default, zero-setup)
  - Collection    : "market_memory"
  - Vector dim    : 384 (all-MiniLM-L6-v2 / LM Studio default)

SSE streaming:
  Each token arrives as:   data: <token>\n\n
  On completion:           data: [DONE]\n\n
  On error:                data: [ERROR] <message>\n\n

SQLite tables used:
  - agent_insights  (read + index trigger write)
  - news_articles   (read + index)
  - daily_ohlcv     (read for OHLCV context rows)
  - rag_index_log   (write — tracks what has been indexed to avoid re-indexing)
  - agent_health    (write — heartbeat)

FastAPI integration (gateway/server.py):
  from agents.market_rag import ask_stream, index_insight, get_agent as get_rag

  @router.post("/ask")
  async def ask_endpoint(body: AskRequest):
      return StreamingResponse(
          ask_stream(body.question, body.symbol),
          media_type="text/event-stream",
      )

  # Call after every agent_insights insert:
  index_insight(insight_id, symbol, insight_text)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator, Iterator

import httpx
import numpy as np

# ── Optional sentence-transformers (graceful if absent or offline) ────────────
try:
    from sentence_transformers import SentenceTransformer as _ST

    _ST_AVAILABLE = True
except ImportError:
    _ST_AVAILABLE = False

# ── Qdrant ────────────────────────────────────────────────────────────────────
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("MarketRAG")

# ── Configuration ─────────────────────────────────────────────────────────────
DB_PATH         = os.getenv("KNOWLEDGE_DB_NAME", "axiom_knowledge.db")
QDRANT_MODE     = os.getenv("QDRANT_MODE", "memory")          # memory | server
QDRANT_URL      = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION      = os.getenv("RAG_COLLECTION", "market_memory")
EMBED_DIM       = int(os.getenv("RAG_EMBED_DIM", "384"))
TOP_K           = int(os.getenv("RAG_TOP_K", "5"))
OHLCV_ROWS      = int(os.getenv("RAG_OHLCV_ROWS", "10"))
LLM_PROVIDER    = os.getenv("LLM_PROVIDER", "lm_studio")
LM_STUDIO_URL   = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")
NIM_URL         = os.getenv("NIM_URL", "https://integrate.api.nvidia.com/v1")
NIM_API_KEY     = os.getenv("MOONSHOT_API_KEY", "")
LM_STUDIO_MODEL = os.getenv("LM_STUDIO_MODEL", "local-model")
NIM_MODEL       = os.getenv("NIM_MODEL", "nvidia/nemotron-4-340b-instruct")
LLM_TIMEOUT_SEC = int(os.getenv("LLM_TIMEOUT_SEC", "60"))
ST_MODEL_NAME   = os.getenv("ST_MODEL_NAME", "all-MiniLM-L6-v2")
AGENT_NAME      = "MarketRAGAgent"

# ── RAG system prompt ─────────────────────────────────────────────────────────
RAG_SYSTEM_PROMPT = """You are AITradra, an institutional-grade market intelligence AI.
You have been given retrieved context from a live financial database containing:
  • Agent insights (technical analysis, move explanations, risk assessments)
  • Recent news headlines with sentiment scores
  • OHLCV price data (Open, High, Low, Close, Volume)

Instructions:
  1. Answer the user's question using ONLY the provided context below.
  2. If the context does not contain enough information, say:
     "I don't have enough data in my current database to answer that precisely."
     Then suggest what data would be needed.
  3. Always cite the date/timestamp of the data you reference.
  4. Be direct and concise. Structure: [Direct answer] → [Supporting data] → [Caveat if any].
  5. When citing price levels, always include the timestamp: e.g. "AAPL closed at $182.50 (2026-04-18 14:30)".
  6. Never hallucinate data that is not in the context.
  7. Do not add disclaimers about not being financial advice — the user knows this.

RETRIEVED INSIGHTS & NEWS:
{insights}

OHLCV PRICE DATA (recent bars):
{ohlcv}

USER QUESTION: {question}

Answer (be direct, cite timestamps, no disclaimers):"""


# ════════════════════════════════════════════════════════════════════════════════
# Embedding layer  (priority: LM Studio → SentenceTransformer → hash-fallback)
# ════════════════════════════════════════════════════════════════════════════════

class EmbedderBase:
    """Abstract base. Subclasses implement encode()."""
    name: str = "base"

    def encode(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def encode_one(self, text: str) -> list[float]:
        return self.encode([text])[0]


class LMStudioEmbedder(EmbedderBase):
    """
    Uses the LM Studio /v1/embeddings endpoint — same server already running.
    Works with any model loaded in LM Studio that supports embeddings.
    Falls back gracefully if the endpoint is not available.
    """
    name = "lm_studio"

    def __init__(self) -> None:
        self._base = LM_STUDIO_URL.rstrip("/")
        self._client = httpx.Client(timeout=15)

    def encode(self, texts: list[str]) -> list[list[float]]:
        resp = self._client.post(
            f"{self._base}/embeddings",
            json={"input": texts, "model": LM_STUDIO_MODEL},
        )
        resp.raise_for_status()
        data = resp.json()
        # Sort by index to preserve order (spec guarantees index field)
        items = sorted(data["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in items]


class SentenceTransformerEmbedder(EmbedderBase):
    """sentence-transformers/all-MiniLM-L6-v2 — requires model download."""
    name = "sentence_transformer"

    def __init__(self) -> None:
        self._model = _ST(ST_MODEL_NAME)

    def encode(self, texts: list[str]) -> list[list[float]]:
        vecs = self._model.encode(texts, normalize_embeddings=True)
        return vecs.tolist()


class HashEmbedder(EmbedderBase):
    """
    Deterministic hash-based embedding — no downloads, no network, no GPU.
    Same text → same vector always.  Used as offline fallback / in tests.
    Quality is intentionally limited; replace with LM Studio in production.
    """
    name = "hash_fallback"

    def encode(self, texts: list[str]) -> list[list[float]]:
        out = []
        for text in texts:
            seed = int(hashlib.md5(text.lower().encode()).hexdigest(), 16) % (2**32)
            rng  = np.random.default_rng(seed)
            vec  = rng.standard_normal(EMBED_DIM).astype(np.float32)
            norm = np.linalg.norm(vec)
            out.append((vec / norm if norm > 0 else vec).tolist())
        return out


def _build_embedder() -> EmbedderBase:
    """Try LM Studio first, then sentence-transformers, then hash fallback."""
    # 1 — LM Studio
    try:
        emb = LMStudioEmbedder()
        vecs = emb.encode(["ping"])
        if len(vecs) == 1 and len(vecs[0]) > 0:
            global EMBED_DIM
            EMBED_DIM = len(vecs[0])
            log.info("Embedder: LM Studio (%d-dim)", EMBED_DIM)
            return emb
    except Exception as exc:
        log.debug("LM Studio embedder unavailable: %s", exc)

    # 2 — SentenceTransformer
    if _ST_AVAILABLE:
        try:
            emb = SentenceTransformerEmbedder()
            vecs = emb.encode(["ping"])
            if len(vecs) == 1 and len(vecs[0]) > 0:
                EMBED_DIM = len(vecs[0])
                log.info("Embedder: SentenceTransformer/%s (%d-dim)", ST_MODEL_NAME, EMBED_DIM)
                return emb
        except Exception as exc:
            log.debug("SentenceTransformer unavailable: %s", exc)

    # 3 — Hash fallback
    log.warning(
        "Using hash-based fallback embedder (no LM Studio / sentence-transformers). "
        "Semantic search quality will be limited."
    )
    return HashEmbedder()


# ════════════════════════════════════════════════════════════════════════════════
# SQLite helpers
# ════════════════════════════════════════════════════════════════════════════════

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _ensure_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS agent_insights (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name     TEXT    NOT NULL,
            ticker         TEXT    NOT NULL,
            insight_type   TEXT    NOT NULL,
            content        TEXT    NOT NULL,
            price_change   REAL,
            sentiment      TEXT,
            confidence     INTEGER,
            catalyst_type  TEXT,
            magnitude      TEXT,
            created_at     TEXT    DEFAULT (datetime('now')),
            model_used     TEXT
        );

        CREATE TABLE IF NOT EXISTS news_articles (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker          TEXT    NOT NULL,
            headline        TEXT    NOT NULL,
            url             TEXT,
            source          TEXT,
            sentiment_score REAL    DEFAULT 0.0,
            published_at    TEXT,
            fetched_at      TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS daily_ohlcv (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker    TEXT    NOT NULL,
            date      TEXT    NOT NULL,
            open      REAL,
            high      REAL,
            low       REAL,
            close     REAL,
            volume    REAL,
            UNIQUE(ticker, date)
        );

        CREATE TABLE IF NOT EXISTS rag_index_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type  TEXT    NOT NULL,   -- insight | news
            source_id    INTEGER NOT NULL,
            qdrant_id    TEXT    NOT NULL,
            indexed_at   TEXT    DEFAULT (datetime('now')),
            UNIQUE(source_type, source_id)
        );

        CREATE TABLE IF NOT EXISTS agent_health (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name     TEXT    NOT NULL,
            status         TEXT    NOT NULL,
            last_run       TEXT,
            last_error     TEXT,
            run_count      INTEGER DEFAULT 0,
            error_count    INTEGER DEFAULT 0,
            avg_latency_ms REAL    DEFAULT 0.0,
            updated_at     TEXT    DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_rag_log_src ON rag_index_log(source_type, source_id);
        CREATE INDEX IF NOT EXISTS idx_ohlcv_sym   ON daily_ohlcv(ticker, date DESC);
        CREATE INDEX IF NOT EXISTS idx_insights_sym ON agent_insights(ticker, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_news_sym     ON news_articles(ticker, published_at DESC);
    """)
    conn.commit()


# ── Data fetchers used during retrieval ───────────────────────────────────────

def _fetch_ohlcv(conn: sqlite3.Connection, symbol: str | None, n: int) -> str:
    """Return a formatted table of recent OHLCV rows, optionally filtered by symbol."""
    if symbol:
        rows = conn.execute("""
            SELECT ticker, date, open, high, low, close, volume
            FROM   daily_ohlcv
            WHERE  ticker = ?
            ORDER  BY date DESC
            LIMIT  ?
        """, (symbol, n)).fetchall()
    else:
        rows = conn.execute("""
            SELECT ticker, date, open, high, low, close, volume
            FROM   daily_ohlcv
            ORDER  BY date DESC
            LIMIT  ?
        """, (n,)).fetchall()

    if not rows:
        return "(no OHLCV data available)"

    lines = ["symbol    | ts                    | open    | high    | low     | close   | volume",
             "----------+-----------------------+---------+---------+---------+---------+----------"]
    for r in reversed(rows):
        lines.append(
            f"{r['ticker']:<9} | {r['date'][:19]:<21} | "
            f"{r['open']:>7.2f} | {r['high']:>7.2f} | {r['low']:>7.2f} | "
            f"{r['close']:>7.2f} | {int(r['volume']):>10,}"
        )
    return "\n".join(lines)


def _fetch_insights_by_ids(conn: sqlite3.Connection, ids: list[int]) -> list[dict]:
    """Fetch agent_insights rows by primary key."""
    if not ids:
        return []
    placeholders = ",".join("?" * len(ids))
    rows = conn.execute(
        f"SELECT * FROM agent_insights WHERE id IN ({placeholders}) ORDER BY created_at DESC",
        ids,
    ).fetchall()
    return [dict(r) for r in rows]


def _fetch_news_by_ids(conn: sqlite3.Connection, ids: list[int]) -> list[dict]:
    """Fetch news_articles rows by primary key."""
    if not ids:
        return []
    placeholders = ",".join("?" * len(ids))
    rows = conn.execute(
        f"SELECT * FROM news_articles WHERE id IN ({placeholders}) ORDER BY published_at DESC",
        ids,
    ).fetchall()
    return [dict(r) for r in rows]


def _already_indexed(conn: sqlite3.Connection, source_type: str, source_id: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM rag_index_log WHERE source_type=? AND source_id=?",
        (source_type, source_id),
    ).fetchone()
    return row is not None


def _log_indexed(conn: sqlite3.Connection, source_type: str, source_id: int, qdrant_id: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO rag_index_log (source_type, source_id, qdrant_id) VALUES (?,?,?)",
        (source_type, source_id, qdrant_id),
    )
    conn.commit()


# ── Health tracking ───────────────────────────────────────────────────────────

def _update_health(
    conn: sqlite3.Connection,
    *,
    status: str,
    latency_ms: float = 0.0,
    error_msg: str = "",
) -> None:
    row = conn.execute(
        "SELECT id, run_count, error_count, avg_latency_ms FROM agent_health WHERE agent_name=?",
        (AGENT_NAME,),
    ).fetchone()
    if row:
        rc  = row["run_count"] + 1
        ec  = row["error_count"] + (1 if status == "ERROR" else 0)
        avg = (row["avg_latency_ms"] * (rc - 1) + latency_ms) / rc
        conn.execute("""
            UPDATE agent_health
            SET status=?, last_run=datetime('now'), last_error=?,
                run_count=?, error_count=?, avg_latency_ms=?, updated_at=datetime('now')
            WHERE agent_name=?
        """, (status, error_msg, rc, ec, avg, AGENT_NAME))
    else:
        conn.execute("""
            INSERT INTO agent_health
                (agent_name, status, last_run, last_error, run_count, error_count, avg_latency_ms)
            VALUES (?,?,datetime('now'),?,1,?,?)
        """, (AGENT_NAME, status, error_msg, 1 if status == "ERROR" else 0, latency_ms))
    conn.commit()


# ════════════════════════════════════════════════════════════════════════════════
# LLM streaming
# ════════════════════════════════════════════════════════════════════════════════

def _llm_headers() -> dict[str, str]:
    if LLM_PROVIDER == "nvidia_nim":
        return {"Authorization": f"Bearer {NIM_API_KEY}", "Content-Type": "application/json"}
    return {"Content-Type": "application/json"}


def _llm_url() -> str:
    base = NIM_URL if LLM_PROVIDER == "nvidia_nim" else LM_STUDIO_URL
    return f"{base.rstrip('/')}/chat/completions"


def _llm_model() -> str:
    return NIM_MODEL if LLM_PROVIDER == "nvidia_nim" else LM_STUDIO_MODEL


def _stream_llm_sync(prompt: str) -> Iterator[str]:
    """
    Synchronous streaming generator. Yields raw text tokens as they arrive.
    Uses httpx streaming with iter_lines() for SSE parsing.
    Raises on connection errors so the caller can yield an [ERROR] SSE event.
    """
    payload = {
        "model":       _llm_model(),
        "stream":      True,
        "temperature": 0.2,
        "max_tokens":  1024,
        "messages": [
            {"role": "system", "content": "You are AITradra, a financial intelligence AI."},
            {"role": "user",   "content": prompt},
        ],
    }

    with httpx.Client(timeout=LLM_TIMEOUT_SEC) as client:
        with client.stream(
            "POST", _llm_url(), headers=_llm_headers(), json=payload
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                line = line.strip()
                if not line or not line.startswith("data:"):
                    continue
                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    return
                try:
                    chunk = json.loads(data_str)
                    delta = chunk["choices"][0].get("delta", {})
                    token = delta.get("content", "")
                    if token:
                        yield token
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue


async def _stream_llm_async(prompt: str) -> AsyncIterator[str]:
    """
    Async streaming wrapper for use in FastAPI async routes.
    Wraps the synchronous httpx streaming call in a thread executor.
    """
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue[str | None] = asyncio.Queue()

    def _producer() -> None:
        try:
            for token in _stream_llm_sync(prompt):
                asyncio.run_coroutine_threadsafe(queue.put(token), loop)
        except Exception as exc:
            asyncio.run_coroutine_threadsafe(queue.put(f"__ERROR__{exc}"), loop)
        finally:
            asyncio.run_coroutine_threadsafe(queue.put(None), loop)

    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_producer)
        while True:
            token = await queue.get()
            if token is None:
                break
            yield token
        future.result()  # surface any thread exception


# ════════════════════════════════════════════════════════════════════════════════
# Core agent class
# ════════════════════════════════════════════════════════════════════════════════

@dataclass
class RetrievedChunk:
    qdrant_id:   str
    score:       float
    source_type: str          # "insight" | "news"
    source_id:   int
    symbol:      str
    text:        str
    created_at:  str
    metadata:    dict = field(default_factory=dict)


class MarketRAGAgent:
    """
    Retrieval-Augmented Generation over AITradra's market memory.

    Public API:
        agent.index_insight(id, symbol, text, metadata)  — called after each agent_insights write
        agent.index_news(id, symbol, headline, metadata) — called after each news_articles write
        agent.index_all_unindexed()                      — bulk-indexes everything not yet in Qdrant
        agent.retrieve(question, symbol, top_k)          — returns list[RetrievedChunk]
        agent.ask_sync(question, symbol)                 — returns full answer string (blocking)
        agent.ask_sse(question, symbol)                  — sync SSE event generator
        await agent.ask_sse_async(question, symbol)      — async SSE event generator
        agent.health()                                   — returns agent_health row
    """

    def __init__(self) -> None:
        self._conn    = _get_conn()
        self._embedder = _build_embedder()
        self._qdrant  = self._init_qdrant()
        _ensure_tables(self._conn)
        log.info(
            "%s ready | embedder=%s | qdrant=%s | dim=%d",
            AGENT_NAME, self._embedder.name, QDRANT_MODE, EMBED_DIM,
        )

    # ── Qdrant setup ──────────────────────────────────────────────────────────

    def _init_qdrant(self) -> QdrantClient:
        if QDRANT_MODE == "server":
            client = QdrantClient(url=QDRANT_URL)
            log.info("Qdrant: server @ %s", QDRANT_URL)
        else:
            client = QdrantClient(":memory:")
            log.info("Qdrant: in-memory (set QDRANT_MODE=server for persistence)")

        # Create collection if missing
        existing = [c.name for c in client.get_collections().collections]
        if COLLECTION not in existing:
            client.create_collection(
                COLLECTION,
                vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
            )
            log.info("Created Qdrant collection '%s' (dim=%d)", COLLECTION, EMBED_DIM)
        return client

    # ── Indexing ──────────────────────────────────────────────────────────────

    def index_insight(
        self,
        insight_id: int,
        ticker:     str,
        text:       str,
        metadata:   dict | None = None,
    ) -> str | None:
        """
        Embed and upsert a single agent_insight into Qdrant.
        Returns the Qdrant point ID (UUID string) or None if already indexed.
        """
        if _already_indexed(self._conn, "insight", insight_id):
            log.debug("Insight %d already indexed — skipping", insight_id)
            return None

        try:
            vector    = self._embedder.encode_one(text)
            point_id  = str(uuid.uuid4())
            payload   = {
                "source_type": "insight",
                "source_id":   insight_id,
                "symbol":      ticker,
                "text":        text[:2000],   # cap payload size
                "created_at":  datetime.now(timezone.utc).isoformat(),
                **(metadata or {}),
            }
            self._qdrant.upsert(
                collection_name=COLLECTION,
                points=[PointStruct(id=point_id, vector=vector, payload=payload)],
            )
            _log_indexed(self._conn, "insight", insight_id, point_id)
            log.debug("Indexed insight id=%d symbol=%s point=%s", insight_id, symbol, point_id)
            return point_id

        except Exception as exc:
            log.error("Failed to index insight %d: %s", insight_id, exc)
            return None

    def index_news(
        self,
        news_id:   int,
        ticker:    str,
        headline:  str,
        metadata:  dict | None = None,
    ) -> str | None:
        """Embed and upsert a single news headline into Qdrant."""
        if _already_indexed(self._conn, "news", news_id):
            return None

        try:
            vector   = self._embedder.encode_one(headline)
            point_id = str(uuid.uuid4())
            payload  = {
                "source_type": "news",
                "source_id":   news_id,
                "symbol":      ticker,
                "text":        headline[:1000],
                "created_at":  datetime.now(timezone.utc).isoformat(),
                **(metadata or {}),
            }
            self._qdrant.upsert(
                collection_name=COLLECTION,
                points=[PointStruct(id=point_id, vector=vector, payload=payload)],
            )
            _log_indexed(self._conn, "news", news_id, point_id)
            return point_id

        except Exception as exc:
            log.error("Failed to index news %d: %s", news_id, exc)
            return None

    def index_all_unindexed(self) -> dict[str, int]:
        """
        Bulk-index everything in agent_insights and news_articles that hasn't
        been indexed yet. Call this on startup to warm Qdrant from existing DB.
        Returns {"insights": N, "news": M} count of newly indexed items.
        """
        t0 = time.monotonic()
        counts = {"insights": 0, "news": 0}

        # ── Insights ──
        rows = self._conn.execute("""
            SELECT ai.id, ai.ticker, ai.content, ai.insight_type, ai.sentiment,
                   ai.confidence, ai.catalyst_type, ai.created_at
            FROM   agent_insights ai
            LEFT JOIN rag_index_log l
              ON  l.source_type = 'insight' AND l.source_id = ai.id
            WHERE  l.id IS NULL
            ORDER  BY ai.created_at ASC
        """).fetchall()

        texts, metas, ids = [], [], []
        for r in rows:
            # Build a rich text blob combining all searchable fields
            try:
                # content might be JSON or plain text
                content_data = r["content"]
                if content_data.startswith("{"):
                    payload_data = json.loads(content_data)
                    reason = payload_data.get("reason", payload_data.get("content", content_data))
                else:
                    reason = content_data
            except Exception:
                reason = r["content"]
            text = (
                f"[{r['insight_type']}] {r['ticker']} "
                f"sentiment={r['sentiment']} confidence={r['confidence']} "
                f"catalyst={r['catalyst_type']} "
                f"{reason}"
            )
            texts.append(text)
            metas.append({
                "insight_type": r["insight_type"],
                "sentiment":    r["sentiment"],
                "confidence":   r["confidence"],
            })
            ids.append(r["id"])

        if texts:
            vectors = self._embedder.encode(texts)
            points  = []
            for i, (insight_id, vector, text, meta) in enumerate(zip(ids, vectors, texts, metas)):
                row     = rows[i]
                pid     = str(uuid.uuid4())
                points.append(PointStruct(
                    id=pid,
                    vector=vector,
                    payload={
                        "source_type": "insight",
                        "source_id":   insight_id,
                        "symbol":      row["ticker"],
                        "text":        text[:2000],
                        "created_at":  row["created_at"],
                        **meta,
                    },
                ))
            # Batch upsert in chunks of 100
            for chunk_start in range(0, len(points), 100):
                self._qdrant.upsert(COLLECTION, points=points[chunk_start:chunk_start + 100])
            for i, point in enumerate(points):
                _log_indexed(self._conn, "insight", ids[i], point.id)
            counts["insights"] = len(points)
            log.info("Bulk-indexed %d insights", len(points))

        # ── News ──
        news_rows = self._conn.execute("""
            SELECT n.id, n.ticker, n.headline, n.source, n.sentiment_score, n.published_at
            FROM   news_articles n
            LEFT JOIN rag_index_log l
              ON  l.source_type = 'news' AND l.source_id = n.id
            WHERE  l.id IS NULL
            ORDER  BY n.published_at ASC
        """).fetchall()

        news_texts, news_ids = [], []
        for r in news_rows:
            news_texts.append(r["headline"])
            news_ids.append(r["id"])

        if news_texts:
            vectors = self._embedder.encode(news_texts)
            points  = []
            for i, (news_id, vector, text) in enumerate(zip(news_ids, vectors, news_texts)):
                r   = news_rows[i]
                pid = str(uuid.uuid4())
                points.append(PointStruct(
                    id=pid,
                    vector=vector,
                    payload={
                        "source_type":     "news",
                        "source_id":       news_id,
                        "symbol":          r["ticker"],
                        "text":            text[:1000],
                        "created_at":      r["published_at"] or "",
                        "sentiment_score": r["sentiment_score"],
                        "source":          r["source"] or "",
                    },
                ))
            for chunk_start in range(0, len(points), 100):
                self._qdrant.upsert(COLLECTION, points=points[chunk_start:chunk_start + 100])
            for i, point in enumerate(points):
                _log_indexed(self._conn, "news", news_ids[i], point.id)
            counts["news"] = len(points)
            log.info("Bulk-indexed %d news articles", len(points))

        elapsed = (time.monotonic() - t0) * 1000
        log.info("index_all_unindexed: %s in %.0fms", counts, elapsed)
        return counts

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def retrieve(
        self,
        question: str,
        symbol:   str | None = None,
        top_k:    int        = TOP_K,
    ) -> list[RetrievedChunk]:
        """
        Embed the question and search Qdrant.
        Optionally filter by symbol (keeps results from both 'insight' and 'news' sources).
        Returns ranked list of RetrievedChunk objects.
        """
        try:
            query_vec = self._embedder.encode_one(question)
        except Exception as exc:
            log.error("Embedding query failed: %s", exc)
            return []

        # Build optional symbol filter
        search_filter = None
        if symbol:
            search_filter = Filter(
                must=[FieldCondition(key="symbol", match=MatchValue(value=symbol))]
            )

        try:
            hits = self._qdrant.query_points(
                collection_name=COLLECTION,
                query=query_vec,
                query_filter=search_filter,
                limit=top_k,
            ).points
        except Exception as exc:
            log.error("Qdrant search failed: %s", exc)
            return []

        chunks: list[RetrievedChunk] = []
        for hit in hits:
            p = hit.payload or {}
            chunks.append(RetrievedChunk(
                qdrant_id   = str(hit.id),
                score       = hit.score,
                source_type = p.get("source_type", "unknown"),
                source_id   = int(p.get("source_id", 0)),
                symbol      = p.get("symbol", ""),
                text        = p.get("text", ""),
                created_at  = p.get("created_at", ""),
                metadata    = {k: v for k, v in p.items()
                               if k not in ("source_type", "source_id", "symbol", "text", "created_at")},
            ))

        log.debug(
            "Retrieved %d chunks for question='%s...' symbol=%s",
            len(chunks), question[:40], symbol,
        )
        return chunks

    # ── Context builder ───────────────────────────────────────────────────────

    def _build_context(
        self,
        chunks:  list[RetrievedChunk],
        symbol:  str | None,
    ) -> tuple[str, str]:
        """
        Given retrieved chunks, hydrate from SQLite and build two formatted
        context strings: (insights_block, ohlcv_block).
        """
        insight_ids = [c.source_id for c in chunks if c.source_type == "insight"]
        news_ids    = [c.source_id for c in chunks if c.source_type == "news"]

        insight_rows = _fetch_insights_by_ids(self._conn, insight_ids)
        news_rows    = _fetch_news_by_ids(self._conn, news_ids)
        ohlcv_block  = _fetch_ohlcv(self._conn, symbol, OHLCV_ROWS)

        # Build insights block — interleave ranked chunk text with SQLite hydration
        lines: list[str] = []
        rank = 1
        for chunk in chunks:
            lines.append(f"[{rank}] (relevance={chunk.score:.3f}) symbol={chunk.symbol} @ {chunk.created_at[:19]}")
            if chunk.source_type == "insight":
                # Find the hydrated row
                row = next((r for r in insight_rows if r["id"] == chunk.source_id), None)
                if row:
                    try:
                        content_data = row["content"]
                        if content_data.startswith("{"):
                            payload = json.loads(content_data)
                            reason = payload.get("reason", payload.get("content", content_data))
                        else:
                            reason = content_data
                    except Exception:
                        reason = row["content"]
                    lines.append(
                        f"   TYPE: agent_insight | {row['insight_type']} | "
                        f"sentiment={row['sentiment']} | confidence={row['confidence']} | "
                        f"catalyst={row['catalyst_type']}"
                    )
                    if reason:
                        lines.append(f"   REASON: {reason}")
                else:
                    lines.append(f"   {chunk.text}")
            else:  # news
                row = next((r for r in news_rows if r["id"] == chunk.source_id), None)
                if row:
                    lines.append(
                        f"   TYPE: news | source={row['source']} | "
                        f"sentiment_score={row['sentiment_score']:.2f} | "
                        f"published={row['published_at']}"
                    )
                    lines.append(f"   HEADLINE: {row['headline']}")
                else:
                    lines.append(f"   {chunk.text}")
            lines.append("")
            rank += 1

        insights_block = "\n".join(lines) if lines else "(no relevant insights or news found in database)"
        return insights_block, ohlcv_block

    # ── Full RAG prompt ───────────────────────────────────────────────────────

    def _build_prompt(self, question: str, symbol: str | None) -> str:
        chunks          = self.retrieve(question, symbol)
        insights_block, ohlcv_block = self._build_context(chunks, symbol)
        return RAG_SYSTEM_PROMPT.format(
            insights=insights_block,
            ohlcv=ohlcv_block,
            question=question,
        )

    # ── Public answer methods ─────────────────────────────────────────────────

    def ask_sync(self, question: str, symbol: str | None = None) -> str:
        """
        Blocking version: retrieves context, calls LLM, returns full answer string.
        Use this from background agents (not web endpoints).
        """
        t0     = time.monotonic()
        prompt = self._build_prompt(question, symbol)

        full_answer = ""
        try:
            for token in _stream_llm_sync(prompt):
                full_answer += token
            _update_health(
                self._conn,
                status="ACTIVE",
                latency_ms=(time.monotonic() - t0) * 1000,
            )
        except Exception as exc:
            _update_health(
                self._conn,
                status="ERROR",
                latency_ms=(time.monotonic() - t0) * 1000,
                error_msg=str(exc),
            )
            return f"[ERROR] LLM unavailable: {exc}"

        return full_answer

    def ask_sse(self, question: str, symbol: str | None = None) -> Iterator[str]:
        """
        Synchronous SSE generator.
        Yields SSE-formatted lines.  Use with Flask / sync WSGI.

        Usage:
            def flask_ask():
                return Response(agent.ask_sse(question, symbol),
                                mimetype='text/event-stream')
        """
        t0     = time.monotonic()
        prompt = self._build_prompt(question, symbol)

        # Emit a metadata event first so the client knows the context was found
        meta = json.dumps({"symbol": symbol, "question": question[:80]})
        yield f"event: meta\ndata: {meta}\n\n"

        full_answer = ""
        try:
            for token in _stream_llm_sync(prompt):
                full_answer += token
                # Escape any newlines inside the token (SSE spec)
                safe_token = token.replace("\n", "\\n")
                yield f"data: {safe_token}\n\n"

            _update_health(
                self._conn,
                status="ACTIVE",
                latency_ms=(time.monotonic() - t0) * 1000,
            )

        except Exception as exc:
            log.error("SSE LLM stream error: %s", exc)
            _update_health(
                self._conn,
                status="ERROR",
                latency_ms=(time.monotonic() - t0) * 1000,
                error_msg=str(exc),
            )
            yield f"data: [ERROR] {exc}\n\n"

        yield "data: [DONE]\n\n"

    async def ask_sse_async(
        self, question: str, symbol: str | None = None
    ) -> AsyncIterator[str]:
        """
        Async SSE generator for FastAPI StreamingResponse.

        Usage in gateway/server.py:
            @router.post("/ask")
            async def ask(body: AskRequest):
                return StreamingResponse(
                    agent.ask_sse_async(body.question, body.symbol),
                    media_type="text/event-stream",
                    headers={"X-Accel-Buffering": "no",
                             "Cache-Control": "no-cache"},
                )
        """
        t0     = time.monotonic()
        prompt = self._build_prompt(question, symbol)

        meta = json.dumps({"symbol": symbol, "question": question[:80]})
        yield f"event: meta\ndata: {meta}\n\n"

        try:
            async for token in _stream_llm_async(prompt):
                if token.startswith("__ERROR__"):
                    raise RuntimeError(token[9:])
                safe_token = token.replace("\n", "\\n")
                yield f"data: {safe_token}\n\n"
                await asyncio.sleep(0)   # yield control back to event loop

            _update_health(
                self._conn,
                status="ACTIVE",
                latency_ms=(time.monotonic() - t0) * 1000,
            )

        except Exception as exc:
            log.error("Async SSE error: %s", exc)
            _update_health(
                self._conn,
                status="ERROR",
                latency_ms=(time.monotonic() - t0) * 1000,
                error_msg=str(exc),
            )
            yield f"data: [ERROR] {exc}\n\n"

        yield "data: [DONE]\n\n"

    # ── Misc ──────────────────────────────────────────────────────────────────

    def collection_stats(self) -> dict:
        """Return Qdrant collection info (vector count, disk usage)."""
        try:
            info   = self._qdrant.get_collection(COLLECTION)
            return {
                "collection":    COLLECTION,
                "vector_count":  info.points_count,
                "vector_dim":    EMBED_DIM,
                "embedder":      self._embedder.name,
                "qdrant_mode":   QDRANT_MODE,
            }
        except Exception as exc:
            return {"error": str(exc)}

    def health(self) -> dict:
        row = self._conn.execute(
            "SELECT * FROM agent_health WHERE agent_name=?", (AGENT_NAME,)
        ).fetchone()
        return dict(row) if row else {"agent_name": AGENT_NAME, "status": "IDLE"}


# ════════════════════════════════════════════════════════════════════════════════
# Module-level singleton + integration hooks
# ════════════════════════════════════════════════════════════════════════════════

_agent_instance: MarketRAGAgent | None = None


def get_agent() -> MarketRAGAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = MarketRAGAgent()
    return _agent_instance


# ── Hooks called from other agents ───────────────────────────────────────────

def index_insight(insight_id: int, symbol: str, text: str, metadata: dict | None = None) -> str | None:
    """
    Call this immediately after every agent_insights INSERT.
    Keeps Qdrant in sync with SQLite without a batch job.
    Returns the Qdrant point ID string, or None if already indexed / error.

    Example in move_explainer.py, after _persist_explanation():
        from agents.market_rag import index_insight
        index_insight(row_id, exp.symbol, exp.reason, {"catalyst": exp.catalyst_type})
    """
    return get_agent().index_insight(insight_id, symbol, text, metadata)


def index_news_headline(news_id: int, ticker: str, headline: str, metadata: dict | None = None) -> str | None:
    """
    Call this after every news_articles INSERT.
    Returns the Qdrant point ID string, or None if already indexed / error.

    Example in news_intel_agent.py:
        from agents.market_rag import index_news_headline
        index_news_headline(news_id, ticker, headline, {"source": source})
    """
    return get_agent().index_news(news_id, ticker, headline, metadata)


def ask_stream(question: str, symbol: str | None = None) -> AsyncIterator[str]:
    """
    Top-level async hook for the /ask endpoint in gateway/server.py.

    Example:
        from agents.market_rag import ask_stream
        from fastapi.responses import StreamingResponse

        @router.post("/ask")
        async def ask_endpoint(body: AskRequest):
            return StreamingResponse(
                ask_stream(body.question, body.symbol),
                media_type="text/event-stream",
                headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
            )
    """
    return get_agent().ask_sse_async(question, symbol)


# ════════════════════════════════════════════════════════════════════════════════
# CLI test harness
# ════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys, textwrap

    symbol   = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    question = sys.argv[2] if len(sys.argv) > 2 else f"Why did {symbol} move recently?"

    print(f"\n{'─'*65}")
    print(f"  AITradra MarketRAGAgent — CLI test")
    print(f"  Symbol  : {symbol}")
    print(f"  Question: {question}")
    print(f"  Embedder: (will auto-detect)")
    print(f"  DB      : {DB_PATH}")
    print(f"{'─'*65}\n")

    agent = MarketRAGAgent()

    # ── Seed dummy data if DB is empty ────────────────────────────────────────
    conn = agent._conn
    has_insights = conn.execute(
        "SELECT COUNT(*) FROM agent_insights WHERE symbol=?", (symbol,)
    ).fetchone()[0]

    if has_insights == 0:
        print("  Seeding synthetic data for demo...\n")
        import random
        now = datetime.now(timezone.utc)
        base = 180.0

        # OHLCV
        for i in range(15):
            ts    = (now - timedelta(minutes=5*(14-i))).isoformat()
            close = round(base + random.uniform(-2, 2), 2)
            conn.execute("INSERT OR IGNORE INTO daily_ohlcv (symbol,ts,open,high,low,close,volume) VALUES (?,?,?,?,?,?,?)",
                         (symbol, ts, base, close+1, close-1, close, random.randint(1_000_000, 8_000_000)))
            base = close
        big_ts = (now + timedelta(seconds=1)).isoformat()
        conn.execute("INSERT OR IGNORE INTO daily_ohlcv (symbol,ts,open,high,low,close,volume) VALUES (?,?,?,?,?,?,?)",
                     (symbol, big_ts, base, base*1.04, base*.99, round(base*1.037, 2), 11_000_000))

        # Insights
        insights = [
            (symbol, "move_explanation", json.dumps({"reason": f"{symbol} surged on earnings beat, EPS +18% YoY.", "sentiment": "BULLISH", "confidence": 88, "catalyst_type": "earnings"}), 3.7, "BULLISH", 88, "earnings", "SIGNIFICANT"),
            (symbol, "technical_analysis", json.dumps({"reason": f"SMA20 crossed above SMA50 for {symbol}, RSI at 62 — bullish momentum.", "sentiment": "BULLISH", "confidence": 74, "catalyst_type": "technical"}), 3.7, "BULLISH", 74, "technical", "MODERATE"),
            (symbol, "risk_assessment", json.dumps({"reason": f"VaR 95% for {symbol} is $4.20/share. Max drawdown at 8.3%. Risk level: MEDIUM.", "sentiment": "NEUTRAL", "confidence": 91, "catalyst_type": "risk"}), 3.7, "NEUTRAL", 91, "risk", "MINOR"),
        ]
        for row in insights:
            conn.execute("""
                INSERT INTO agent_insights
                    (agent_name, symbol, insight_type, payload, price_change, sentiment, confidence, catalyst_type, magnitude)
                VALUES ('TestAgent',?,?,?,?,?,?,?,?)
            """, row)

        # News
        headlines = [
            f"{symbol} reports Q1 earnings: EPS $2.18 vs $1.84 expected",
            f"Analyst upgrades {symbol} to Strong Buy, raises PT to $220",
            f"Fed holds rates steady — tech stocks including {symbol} rally",
            f"{symbol} announces $90B share buyback program",
        ]
        for h in headlines:
            conn.execute("INSERT INTO news_articles (symbol,headline,source,sentiment_score,published_at) VALUES (?,?,?,?,?)",
                         (symbol, h, "Reuters", 0.78, (now - timedelta(hours=2)).isoformat()))
        conn.commit()
        print(f"  Seeded 3 insights, 4 news, 16 OHLCV bars for {symbol}\n")

    # ── Index everything ──────────────────────────────────────────────────────
    print("  Indexing unindexed data into Qdrant...")
    counts = agent.index_all_unindexed()
    print(f"  Indexed: {counts}")
    print(f"  Collection stats: {agent.collection_stats()}\n")

    # ── Retrieve ──────────────────────────────────────────────────────────────
    print(f"  Retrieving top-{TOP_K} chunks for: '{question}'")
    chunks = agent.retrieve(question, symbol)
    for i, c in enumerate(chunks, 1):
        print(f"  [{i}] score={c.score:.4f}  type={c.source_type}  id={c.source_id}  text={c.text[:70]}...")
    print()

    # ── Stream (with stubbed LLM) ─────────────────────────────────────────────
    print("  Streaming SSE answer (using stubbed LLM — replace with real in production):\n")

    # Monkey-patch _stream_llm_sync for the CLI test
    import agents.market_rag as _me
    def _fake_stream(prompt: str) -> Iterator[str]:
        answer = (
            f"Based on available data, {symbol} moved significantly due to a strong Q1 earnings beat "
            f"with EPS of $2.18 against $1.84 consensus. SMA20 crossed above SMA50 (bullish technical signal). "
            f"The Fed's rate hold boosted risk-on sentiment. "
            f"VaR 95% is $4.20/share — risk level MEDIUM. "
            f"Analyst upgrades and a $90B buyback amplified the move."
        )
        for word in answer.split():
            yield word + " "
            time.sleep(0.01)

    _me._stream_llm_sync = _fake_stream

    answer_tokens = []
    for event in agent.ask_sse(question, symbol):
        if event.startswith("event: meta"):
            continue
        if "data: " in event:
            token = event.replace("data: ", "").replace("\\n", "\n").strip()
            if token == "[DONE]":
                break
            answer_tokens.append(token)
            print(token, end="", flush=True)

    print(f"\n\n  Agent health: {json.dumps(agent.health(), indent=4)}")
    print(f"\n{'─'*65}\n")
