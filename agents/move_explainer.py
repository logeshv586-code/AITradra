"""
agents/move_explainer.py
────────────────────────────────────────────────────────────────────────────────
MoveExplainerAgent — AITradra's "Why Did It Move?" core intelligence agent.

What it does:
  1. Listens for market_update events (fired by DataCollector on every price fetch).
  2. On significant price change (>= MOVE_THRESHOLD %), triggers an explanation run.
  3. Pulls the last N hours of news from news_articles table for the symbol.
  4. Pulls recent OHLCV bars from daily_ohlcv for price context.
  5. Calls the configured LLM (local via LM Studio / NVIDIA NIM) with a structured prompt.
  6. Parses the JSON response and persists the explanation to agent_insights table.
  7. Also exposes a synchronous explain(symbol) method for on-demand calls via /ask endpoint.

SQLite tables used:
  - daily_ohlcv      (read)  — OHLCV bars, populated by DataCollector
  - news_articles    (read)  — headlines, populated by NewsIntelAgent
  - agent_insights   (write) — move explanations persist here
  - agent_health     (write) — heartbeat and error tracking

LLM output schema (strict JSON):
  {
    "reason":        string,          # primary cause of the move
    "sentiment":     "BULLISH" | "BEARISH" | "NEUTRAL",
    "confidence":    int (0-100),
    "key_headlines": [string, ...],   # 1-2 most relevant headlines cited
    "catalyst_type": string,          # e.g. "earnings", "macro", "technical", "news"
    "magnitude":     "MINOR" | "MODERATE" | "SIGNIFICANT" | "EXTREME"
  }
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

# ── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("MoveExplainer")

# ── Configuration (reads from .env / environment) ────────────────────────────

DB_PATH         = os.getenv("KNOWLEDGE_DB_NAME", "axiom_knowledge.db")
LLM_PROVIDER    = os.getenv("LLM_PROVIDER", "lm_studio")       # lm_studio | nvidia_nim
LM_STUDIO_URL   = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")
NIM_URL         = os.getenv("NIM_URL", "https://integrate.api.nvidia.com/v1")
NIM_API_KEY     = os.getenv("MOONSHOT_API_KEY", "")
LM_STUDIO_MODEL = os.getenv("LM_STUDIO_MODEL", "local-model")
NIM_MODEL       = os.getenv("NIM_MODEL", "nvidia/nemotron-4-340b-instruct")

MOVE_THRESHOLD      = float(os.getenv("MOVE_THRESHOLD_PCT", "0.8"))   # % change to trigger explain
NEWS_LOOKBACK_HOURS = int(os.getenv("NEWS_LOOKBACK_HOURS", "6"))
OHLCV_BARS_CONTEXT  = int(os.getenv("OHLCV_BARS_CONTEXT", "12"))      # bars sent to LLM
LLM_TIMEOUT_SEC     = int(os.getenv("LLM_TIMEOUT_SEC", "45"))
MAX_RETRIES         = int(os.getenv("LLM_MAX_RETRIES", "2"))
AGENT_NAME          = "MoveExplainerAgent"

# ── Data models ──────────────────────────────────────────────────────────────

@dataclass
class MoveExplanation:
    symbol:        str
    price_change:  float                    # percentage, signed
    reason:        str
    sentiment:     str                      # BULLISH | BEARISH | NEUTRAL
    confidence:    int                      # 0-100
    key_headlines: list[str] = field(default_factory=list)
    catalyst_type: str = "unknown"          # earnings | macro | technical | news | crypto
    magnitude:     str = "MINOR"           # MINOR | MODERATE | SIGNIFICANT | EXTREME
    generated_at:  str = ""
    model_used:    str = ""
    raw_response:  str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol":        self.symbol,
            "price_change":  self.price_change,
            "reason":        self.reason,
            "sentiment":     self.sentiment,
            "confidence":    self.confidence,
            "key_headlines": self.key_headlines,
            "catalyst_type": self.catalyst_type,
            "magnitude":     self.magnitude,
            "generated_at":  self.generated_at,
            "model_used":    self.model_used,
        }


# ── SQLite helpers ────────────────────────────────────────────────────────────

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _ensure_tables(conn: sqlite3.Connection) -> None:
    """Create tables if they don't already exist (idempotent)."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS daily_ohlcv (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol    TEXT    NOT NULL,
            ts        TEXT    NOT NULL,
            open      REAL,
            high      REAL,
            low       REAL,
            close     REAL,
            volume    REAL,
            UNIQUE(symbol, ts)
        );

        CREATE TABLE IF NOT EXISTS news_articles (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol          TEXT    NOT NULL,
            headline        TEXT    NOT NULL,
            url             TEXT,
            source          TEXT,
            sentiment_score REAL    DEFAULT 0.0,
            published_at    TEXT,
            fetched_at      TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS agent_insights (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name     TEXT    NOT NULL,
            symbol         TEXT    NOT NULL,
            insight_type   TEXT    NOT NULL,
            payload        TEXT    NOT NULL,   -- JSON blob
            price_change   REAL,
            sentiment      TEXT,
            confidence     INTEGER,
            catalyst_type  TEXT,
            magnitude      TEXT,
            created_at     TEXT    DEFAULT (datetime('now')),
            model_used     TEXT
        );

        CREATE TABLE IF NOT EXISTS agent_health (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name   TEXT    NOT NULL,
            status       TEXT    NOT NULL,   -- ACTIVE | ERROR | IDLE
            last_run     TEXT,
            last_error   TEXT,
            run_count    INTEGER DEFAULT 0,
            error_count  INTEGER DEFAULT 0,
            avg_latency_ms REAL  DEFAULT 0.0,
            updated_at   TEXT    DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_ts    ON daily_ohlcv(symbol, ts DESC);
        CREATE INDEX IF NOT EXISTS idx_news_symbol_pub    ON news_articles(symbol, published_at DESC);
        CREATE INDEX IF NOT EXISTS idx_insights_symbol    ON agent_insights(symbol, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_health_agent       ON agent_health(agent_name);
    """)
    conn.commit()


# ── Data fetchers ─────────────────────────────────────────────────────────────

def fetch_recent_ohlcv(conn: sqlite3.Connection, symbol: str, n_bars: int = 12) -> list[dict]:
    """Return the last n_bars OHLCV rows for a symbol, newest first."""
    rows = conn.execute("""
        SELECT ts, open, high, low, close, volume
        FROM   daily_ohlcv
        WHERE  symbol = ?
        ORDER  BY ts DESC
        LIMIT  ?
    """, (symbol, n_bars)).fetchall()
    return [dict(r) for r in rows]


def fetch_recent_news(
    conn: sqlite3.Connection,
    symbol: str,
    lookback_hours: int = 6,
) -> list[dict]:
    """Return news articles published within the lookback window."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).isoformat()
    rows = conn.execute("""
        SELECT headline, url, source, sentiment_score, published_at
        FROM   news_articles
        WHERE  symbol      = ?
          AND  published_at >= ?
        ORDER  BY published_at DESC
        LIMIT  20
    """, (symbol, cutoff)).fetchall()
    return [dict(r) for r in rows]


def compute_price_change(bars: list[dict]) -> float:
    """
    Compute percentage change between the oldest and newest bar in the list.
    bars is sorted newest-first (as returned by fetch_recent_ohlcv).
    Returns signed float, e.g. -3.21 means -3.21 %.
    """
    if len(bars) < 2:
        return 0.0
    newest = bars[0]["close"]
    oldest = bars[-1]["open"]
    if not oldest or oldest == 0:
        return 0.0
    return round(((newest - oldest) / oldest) * 100, 4)


# ── LLM integration ───────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are AITradra's Move Explainer — a precision financial analyst AI embedded in an institutional trading platform.

Your ONLY job: given recent price action and news for a ticker or crypto, explain WHY the asset moved.

Rules:
- Be direct. No fluff, no disclaimers.
- Base your answer strictly on the provided headlines and OHLCV data.
- If headlines are empty or irrelevant, attribute the move to technical factors or low liquidity.
- Never hallucinate headlines that weren't given to you.
- Always return VALID JSON — nothing else. No markdown fences, no preamble.

Output format (strict JSON, no extra keys):
{
  "reason":        "<1-2 sentence primary cause of the price move>",
  "sentiment":     "<BULLISH | BEARISH | NEUTRAL>",
  "confidence":    <integer 0-100>,
  "key_headlines": ["<most relevant headline 1>", "<most relevant headline 2>"],
  "catalyst_type": "<earnings | macro | technical | news | crypto | unknown>",
  "magnitude":     "<MINOR | MODERATE | SIGNIFICANT | EXTREME>"
}

Magnitude scale:
  MINOR       = |change| < 1%
  MODERATE    = 1% – 3%
  SIGNIFICANT = 3% – 7%
  EXTREME     = > 7%
"""


def _build_user_prompt(
    symbol: str,
    price_change: float,
    bars: list[dict],
    articles: list[dict],
) -> str:
    ohlcv_summary = "\n".join(
        f"  {b['ts']}: O={b['open']} H={b['high']} L={b['low']} C={b['close']} V={b['volume']}"
        for b in reversed(bars)
    ) or "  (no OHLCV data available)"

    if articles:
        news_block = "\n".join(
            f"  [{a['published_at'] or 'unknown time'}] {a['headline']}"
            f" (source: {a['source'] or 'unknown'}, sentiment: {a['sentiment_score']:.2f})"
            for a in articles
        )
    else:
        news_block = "  (no recent news found for this symbol in the lookback window)"

    direction = "UP" if price_change >= 0 else "DOWN"

    return f"""Analyze the following market event:

SYMBOL:       {symbol}
PRICE MOVED:  {direction} {abs(price_change):.2f}% over the observed window
WINDOW:       last {OHLCV_BARS_CONTEXT} bars shown below

OHLCV DATA (oldest → newest):
{ohlcv_summary}

RECENT NEWS (last {NEWS_LOOKBACK_HOURS}h):
{news_block}

Explain why {symbol} moved {direction} {abs(price_change):.2f}%.
Respond ONLY with the JSON object — no extra text."""


def _call_llm(user_prompt: str) -> tuple[str, str]:
    """
    Call the configured LLM endpoint.
    Returns (raw_text_response, model_name_used).
    Raises httpx.HTTPError or json-related errors on failure.
    """
    if LLM_PROVIDER == "nvidia_nim":
        base_url = NIM_URL
        model    = NIM_MODEL
        headers  = {
            "Authorization": f"Bearer {NIM_API_KEY}",
            "Content-Type":  "application/json",
        }
    else:
        base_url = LM_STUDIO_URL
        model    = LM_STUDIO_MODEL
        headers  = {"Content-Type": "application/json"}

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt},
        ],
        "temperature":      0.1,    # low temp for deterministic JSON output
        "max_tokens":       512,
        "response_format":  {"type": "json_object"},  # supported by most modern endpoints
    }

    url = f"{base_url}/chat/completions"

    with httpx.Client(timeout=LLM_TIMEOUT_SEC) as client:
        resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()

    data    = resp.json()
    content = data["choices"][0]["message"]["content"].strip()
    return content, model


def _parse_llm_response(raw: str, symbol: str, price_change: float, model: str) -> MoveExplanation:
    """
    Parse the LLM JSON response into a MoveExplanation.
    Applies sensible fallbacks if any field is missing.
    """
    # Strip accidental markdown fences if model ignored response_format
    clean = raw.strip()
    if clean.startswith("```"):
        clean = clean.split("```")[1]
        if clean.startswith("json"):
            clean = clean[4:]
    clean = clean.strip()

    try:
        data = json.loads(clean)
    except json.JSONDecodeError as exc:
        log.warning("LLM returned non-JSON — using fallback. Raw: %.200s…  Error: %s", raw, exc)
        data = {}

    sentiment = data.get("sentiment", "NEUTRAL").upper()
    if sentiment not in ("BULLISH", "BEARISH", "NEUTRAL"):
        sentiment = "NEUTRAL"

    magnitude = data.get("magnitude", "MINOR").upper()
    if magnitude not in ("MINOR", "MODERATE", "SIGNIFICANT", "EXTREME"):
        abs_chg = abs(price_change)
        magnitude = (
            "EXTREME"     if abs_chg > 7 else
            "SIGNIFICANT" if abs_chg > 3 else
            "MODERATE"    if abs_chg > 1 else
            "MINOR"
        )

    return MoveExplanation(
        symbol        = symbol,
        price_change  = price_change,
        reason        = data.get("reason", "Insufficient data to determine cause."),
        sentiment     = sentiment,
        confidence    = min(100, max(0, int(data.get("confidence", 50)))),
        key_headlines = data.get("key_headlines", [])[:2],
        catalyst_type = data.get("catalyst_type", "unknown"),
        magnitude     = magnitude,
        generated_at  = datetime.now(timezone.utc).isoformat(),
        model_used    = model,
        raw_response  = raw,
    )


# ── Persistence ───────────────────────────────────────────────────────────────

def _persist_explanation(conn: sqlite3.Connection, exp: MoveExplanation) -> int:
    """Write the explanation to agent_insights. Returns the new row id."""
    payload = json.dumps(exp.to_dict(), ensure_ascii=False)
    cur = conn.execute("""
        INSERT INTO agent_insights
            (agent_name, symbol, insight_type, payload,
             price_change, sentiment, confidence, catalyst_type,
             magnitude, created_at, model_used)
        VALUES (?, ?, 'move_explanation', ?,
                ?, ?, ?, ?,
                ?, datetime('now'), ?)
    """, (
        AGENT_NAME,
        exp.symbol,
        payload,
        exp.price_change,
        exp.sentiment,
        exp.confidence,
        exp.catalyst_type,
        exp.magnitude,
        exp.model_used,
    ))
    conn.commit()
    row_id = cur.lastrowid
    log.info(
        "Persisted explanation for %s | %+.2f%% | %s | conf=%d | id=%d",
        exp.symbol, exp.price_change, exp.sentiment, exp.confidence, row_id,
    )
    return row_id


def _update_agent_health(
    conn: sqlite3.Connection,
    *,
    status:      str,
    latency_ms:  float = 0.0,
    error_msg:   str   = "",
) -> None:
    """Upsert agent_health row for this agent."""
    existing = conn.execute(
        "SELECT id, run_count, error_count, avg_latency_ms FROM agent_health WHERE agent_name = ?",
        (AGENT_NAME,),
    ).fetchone()

    if existing:
        run_count   = existing["run_count"] + 1
        error_count = existing["error_count"] + (1 if status == "ERROR" else 0)
        # running average of latency
        avg_lat = (existing["avg_latency_ms"] * (run_count - 1) + latency_ms) / run_count
        conn.execute("""
            UPDATE agent_health
            SET    status = ?, last_run = datetime('now'), last_error = ?,
                   run_count = ?, error_count = ?, avg_latency_ms = ?,
                   updated_at = datetime('now')
            WHERE  agent_name = ?
        """, (status, error_msg, run_count, error_count, avg_lat, AGENT_NAME))
    else:
        conn.execute("""
            INSERT INTO agent_health
                (agent_name, status, last_run, last_error, run_count, error_count, avg_latency_ms)
            VALUES (?, ?, datetime('now'), ?, 1, ?, ?)
        """, (AGENT_NAME, status, error_msg, 1 if status == "ERROR" else 0, latency_ms))

    conn.commit()


# ── Core agent class ──────────────────────────────────────────────────────────

class MoveExplainerAgent:
    """
    Stateless (per-call) agent that explains price moves.

    Usage:
        agent = MoveExplainerAgent()

        # Called automatically by DataCollector on market_update events:
        result = agent.on_market_update(symbol="AAPL", latest_close=182.5)

        # Called on-demand by the /ask endpoint or Mythic Orchestrator:
        result = agent.explain("BTC-USD")
    """

    def __init__(self) -> None:
        self._conn = _get_conn()
        _ensure_tables(self._conn)
        log.info("%s initialized — DB: %s | LLM: %s", AGENT_NAME, DB_PATH, LLM_PROVIDER)

    # ── Public API ────────────────────────────────────────────────────────────

    def on_market_update(self, symbol: str, latest_close: float) -> MoveExplanation | None:
        """
        Event handler called by DataCollector after each price fetch.

        Threshold check: compares latest_close against the previous bar's close
        (i.e. "did THIS bar move significantly?"), not the whole window.
        LLM context still uses the full OHLCV_BARS_CONTEXT window.

        Returns the explanation or None if below threshold.
        """
        bars = fetch_recent_ohlcv(self._conn, symbol, OHLCV_BARS_CONTEXT)
        if not bars:
            log.debug("No OHLCV bars for %s — skipping", symbol)
            return None

        # Use the second bar (previous close) as the baseline for the threshold.
        # Fall back to whole-window change when only 1 bar exists.
        if len(bars) >= 2:
            prev_close = bars[1]["close"] or bars[1]["open"] or latest_close
            if prev_close and prev_close != 0:
                bar_change = ((latest_close - prev_close) / prev_close) * 100
            else:
                bar_change = 0.0
        else:
            bar_change = 0.0

        if abs(bar_change) < MOVE_THRESHOLD:
            log.debug(
                "%s bar change %.2f%% < threshold %.2f%% — no explanation triggered",
                symbol, bar_change, MOVE_THRESHOLD,
            )
            return None

        # For the LLM we report the whole-window price change for richer context.
        window_change = compute_price_change(bars)
        log.info(
            "%s bar moved %+.2f%% (window %+.2f%%) — triggering explanation run",
            symbol, bar_change, window_change,
        )
        return self._run_explanation(symbol, window_change, bars)

    def explain(self, symbol: str) -> MoveExplanation:
        """
        On-demand explanation — always runs regardless of move threshold.
        Used by /ask endpoint and Mythic Orchestrator.
        """
        bars = fetch_recent_ohlcv(self._conn, symbol, OHLCV_BARS_CONTEXT)
        price_change = compute_price_change(bars) if len(bars) >= 2 else 0.0
        return self._run_explanation(symbol, price_change, bars)

    def get_latest(self, symbol: str) -> dict | None:
        """
        Retrieve the most recent persisted explanation for a symbol.
        Returns the payload dict or None.
        """
        row = self._conn.execute("""
            SELECT payload, created_at
            FROM   agent_insights
            WHERE  agent_name = ?
              AND  symbol     = ?
              AND  insight_type = 'move_explanation'
            ORDER  BY created_at DESC
            LIMIT  1
        """, (AGENT_NAME, symbol)).fetchone()

        if not row:
            return None

        result = json.loads(row["payload"])
        result["retrieved_at"] = row["created_at"]
        return result

    def get_history(self, symbol: str, limit: int = 10) -> list[dict]:
        """Return the last `limit` explanations for a symbol, newest first."""
        rows = self._conn.execute("""
            SELECT payload, created_at, confidence, sentiment, magnitude
            FROM   agent_insights
            WHERE  agent_name    = ?
              AND  symbol        = ?
              AND  insight_type  = 'move_explanation'
            ORDER  BY created_at DESC
            LIMIT  ?
        """, (AGENT_NAME, symbol, limit)).fetchall()

        return [json.loads(r["payload"]) for r in rows]

    def health(self) -> dict:
        """Return current agent_health row as dict."""
        row = self._conn.execute(
            "SELECT * FROM agent_health WHERE agent_name = ?", (AGENT_NAME,)
        ).fetchone()
        return dict(row) if row else {"agent_name": AGENT_NAME, "status": "IDLE", "run_count": 0}

    # ── Internal pipeline ─────────────────────────────────────────────────────

    def _run_explanation(
        self,
        symbol:       str,
        price_change: float,
        bars:         list[dict],
    ) -> MoveExplanation:
        """Full pipeline: fetch news → build prompt → call LLM → parse → persist."""
        t_start = time.monotonic()

        articles = fetch_recent_news(self._conn, symbol, NEWS_LOOKBACK_HOURS)
        log.debug("Fetched %d articles for %s", len(articles), symbol)

        user_prompt = _build_user_prompt(symbol, price_change, bars, articles)

        explanation: MoveExplanation | None = None
        last_error  = ""

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                raw, model = _call_llm(user_prompt)
                explanation = _parse_llm_response(raw, symbol, price_change, model)
                break
            except httpx.ConnectError as exc:
                last_error = f"LLM unreachable ({LLM_PROVIDER}): {exc}"
                log.warning("Attempt %d/%d — %s", attempt, MAX_RETRIES, last_error)
                if attempt < MAX_RETRIES:
                    time.sleep(2 ** attempt)
            except httpx.HTTPStatusError as exc:
                last_error = f"LLM HTTP {exc.response.status_code}: {exc}"
                log.error("Attempt %d/%d — %s", attempt, MAX_RETRIES, last_error)
                break
            except Exception as exc:
                last_error = f"Unexpected error: {exc}"
                log.exception("Attempt %d/%d — %s", attempt, MAX_RETRIES, last_error)
                break

        latency_ms = (time.monotonic() - t_start) * 1000

        if explanation is None:
            # Graceful fallback — always return something useful
            log.error("All LLM attempts failed for %s — using fallback explanation", symbol)
            explanation = MoveExplanation(
                symbol        = symbol,
                price_change  = price_change,
                reason        = (
                    f"{symbol} moved {price_change:+.2f}%. "
                    "LLM analysis unavailable — check agent health."
                ),
                sentiment     = "NEUTRAL",
                confidence    = 0,
                catalyst_type = "unknown",
                magnitude     = self._magnitude_from_change(price_change),
                generated_at  = datetime.now(timezone.utc).isoformat(),
                model_used    = "fallback",
            )
            _update_agent_health(
                self._conn, status="ERROR", latency_ms=latency_ms, error_msg=last_error
            )
        else:
            _persist_explanation(self._conn, explanation)
            _update_agent_health(self._conn, status="ACTIVE", latency_ms=latency_ms)

        return explanation

    @staticmethod
    def _magnitude_from_change(pct: float) -> str:
        abs_pct = abs(pct)
        if abs_pct > 7:  return "EXTREME"
        if abs_pct > 3:  return "SIGNIFICANT"
        if abs_pct > 1:  return "MODERATE"
        return "MINOR"


# ── Module-level singleton (imported by main.py and gateway/server.py) ────────

_agent_instance: MoveExplainerAgent | None = None


def get_agent() -> MoveExplainerAgent:
    """Return (or create) the module-level singleton."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = MoveExplainerAgent()
    return _agent_instance


# ── Integration hooks (called from other agents) ──────────────────────────────

def on_market_update(symbol: str, latest_close: float) -> MoveExplanation | None:
    """
    Top-level hook — import and call this from DataCollector after each price fetch.

    Example in data_collector.py:
        from agents.move_explainer import on_market_update
        ...
        on_market_update(symbol=ticker, latest_close=float(bar["close"]))
    """
    return get_agent().on_market_update(symbol, latest_close)


def explain_on_demand(symbol: str) -> dict:
    """
    Top-level hook — import and call this from gateway/server.py /ask endpoint.

    Example in gateway/server.py:
        from agents.move_explainer import explain_on_demand
        ...
        result = explain_on_demand(symbol)
        return JSONResponse(result)
    """
    exp = get_agent().explain(symbol)
    return exp.to_dict()


def get_latest_explanation(symbol: str) -> dict | None:
    """
    Top-level hook — returns last cached explanation from DB without calling LLM.
    Use for fast UI polls that don't need a fresh LLM call.
    """
    return get_agent().get_latest(symbol)


# ── CLI test harness ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import textwrap

    symbol = sys.argv[1] if len(sys.argv) > 1 else "AAPL"

    print(f"\n{'─'*60}")
    print(f"  AITradra MoveExplainerAgent — test run")
    print(f"  Symbol  : {symbol}")
    print(f"  LLM     : {LLM_PROVIDER}")
    print(f"  DB      : {DB_PATH}")
    print(f"{'─'*60}\n")

    agent = MoveExplainerAgent()

    # ── Inject dummy data if tables are empty (for testing without DataCollector) ──
    conn = agent._conn
    bars_exist = conn.execute(
        "SELECT COUNT(*) FROM daily_ohlcv WHERE symbol = ?", (symbol,)
    ).fetchone()[0]

    if bars_exist == 0:
        print("  No OHLCV data found — injecting synthetic test bars...\n")
        import random
        base = 180.0
        now  = datetime.now(timezone.utc)
        for i in range(OHLCV_BARS_CONTEXT + 2):
            ts    = (now - timedelta(minutes=5 * (OHLCV_BARS_CONTEXT + 1 - i))).isoformat()
            close = round(base + random.uniform(-2, 2), 2)
            conn.execute("""
                INSERT OR IGNORE INTO daily_ohlcv (symbol, ts, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (symbol, ts, base, close + 0.5, close - 0.5, close, random.randint(1_000_000, 5_000_000)))
            base = close
        # Make the last bar a big move so explanation triggers
        big_close = round(base * 1.035, 2)  # +3.5%
        conn.execute("""
            INSERT OR IGNORE INTO daily_ohlcv (symbol, ts, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (symbol, now.isoformat(), base, big_close + 1, base - 0.5, big_close, 8_000_000))
        conn.commit()

        # Inject dummy news
        headlines = [
            f"{symbol} surges on strong earnings beat, EPS up 18% YoY",
            f"Analyst upgrades {symbol} to Buy, raises price target",
            f"Fed holds rates steady — risk-on sentiment lifts tech stocks including {symbol}",
        ]
        for h in headlines:
            published = (now - timedelta(hours=2)).isoformat()
            conn.execute("""
                INSERT INTO news_articles (symbol, headline, source, sentiment_score, published_at)
                VALUES (?, ?, 'TestSource', 0.75, ?)
            """, (symbol, h, published))
        conn.commit()
        print("  Injected synthetic OHLCV bars and test headlines.\n")

    # ── Run the explanation ────────────────────────────────────────────────────
    print(f"  Running explain('{symbol}')...\n")
    result = agent.explain(symbol)

    print(f"  {'Symbol':<16}: {result.symbol}")
    print(f"  {'Price change':<16}: {result.price_change:+.2f}%")
    print(f"  {'Sentiment':<16}: {result.sentiment}")
    print(f"  {'Confidence':<16}: {result.confidence}/100")
    print(f"  {'Magnitude':<16}: {result.magnitude}")
    print(f"  {'Catalyst':<16}: {result.catalyst_type}")
    print(f"  {'Model used':<16}: {result.model_used}")
    print(f"\n  Reason:\n  {textwrap.fill(result.reason, width=55, initial_indent='  ', subsequent_indent='  ')}")
    if result.key_headlines:
        print(f"\n  Key headlines:")
        for h in result.key_headlines:
            print(f"    • {h}")

    print(f"\n  Agent health:\n  {json.dumps(agent.health(), indent=4)}")
    print(f"\n{'─'*60}\n")
