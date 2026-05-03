# AITradra — Master Platform Plan
## "Why It Moves. Where It Goes. When to Trade."

> **Version**: 4.0 Mythic  
> **Status**: Production-Ready Blueprint  
> **Goal**: Real-money autonomous trading with multi-agent intelligence  
> **Date**: 2026-05-03

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Critical Bugs & Fixes Required NOW](#2-critical-bugs--fixes-required-now)
3. [Agent Architecture & Correct Workflow](#3-agent-architecture--correct-workflow)
4. [Data Pipeline — Truth First](#4-data-pipeline--truth-first)
5. [Database Schema — Single Source of Truth](#5-database-schema--single-source-of-truth)
6. [LLM Routing — Profit-Grade Inference](#6-llm-routing--profit-grade-inference)
7. [Signal Architecture — The Money Formula](#7-signal-architecture--the-money-formula)
8. [Risk Framework — Capital Protection First](#8-risk-framework--capital-protection-first)
9. [UI Data Flow — Real-Time Updates](#9-ui-data-flow--real-time-updates)
10. [Chat Query Structure — User Message Format](#10-chat-query-structure--user-message-format)
11. [Real Money Readiness Checklist](#11-real-money-readiness-checklist)
12. [Implementation Phases — Sprint Plan](#12-implementation-phases--sprint-plan)
13. [Monitoring & Self-Healing](#13-monitoring--self-healing)

---

## 1. Executive Summary

AITradra is a **14-agent, 3-wave multi-specialist trading intelligence platform**. The system currently has several schema mismatches, duplicate code paths, and broken data flows that prevent it from being real-money ready. This document is the definitive plan to fix every critical issue, standardize all flows, and build a system that reliably generates profit signals.

### Core Architecture (What It Should Be)

```
User Query / Market Tick
        │
        ▼
  QueryRouter ──────────── Intent Classification
        │                        │
        ▼                        ▼
  MythicOrchestrator      Fast Path (QUICK mode)
        │
        ├── Wave 1 (Parallel): Technical + Macro + Fundamental
        ├── Wave 2 (Sequential): Risk + Sentiment + Catalyst + Sector
        ├── Wave 3 (Decision): SignalAggregator + RiskManager
        │
        ▼
  CritiqueAgent ──── Contradiction Detection
        │
        ▼
  Final LLM Synthesis ──── Streamed Response
        │
        ▼
  KnowledgeStore ──── SQLite + Qdrant RAG
        │
        ▼
  Hyperliquid / PaperBroker ──── Order Execution
```

---

## 2. Critical Bugs & Fixes Required NOW

These bugs will LOSE money in real trading. Fix before going live.

### BUG 1 — Schema Mismatch (CRITICAL 🔴)

**Problem**: Two different schemas exist for the same tables.

| Table | `move_explainer.py` (root) | `agents/move_explainer.py` | `agents/market_rag.py` (root) |
|-------|---------------------------|---------------------------|-------------------------------|
| `daily_ohlcv` | `symbol`, `ts` | `ticker`, `date` | `symbol`, `ts` |
| `agent_insights` | `symbol`, `payload` | `ticker`, `content` | `symbol`, `payload` |
| `news_articles` | `symbol` | `ticker` | `symbol` |

**Fix**: Run this migration ONCE and delete the legacy root-level files:

```sql
-- Run in axiom_knowledge.db
-- Step 1: Add missing columns safely
ALTER TABLE daily_ohlcv ADD COLUMN IF NOT EXISTS ticker TEXT;
ALTER TABLE daily_ohlcv ADD COLUMN IF NOT EXISTS date TEXT;
UPDATE daily_ohlcv SET ticker = symbol, date = ts WHERE ticker IS NULL;

ALTER TABLE agent_insights ADD COLUMN IF NOT EXISTS ticker TEXT;
ALTER TABLE agent_insights ADD COLUMN IF NOT EXISTS content TEXT;
UPDATE agent_insights SET ticker = symbol, content = payload WHERE ticker IS NULL;

ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS ticker TEXT;
UPDATE news_articles SET ticker = symbol WHERE ticker IS NULL;

-- Step 2: Create unified views
CREATE VIEW IF NOT EXISTS v_insights AS
  SELECT id, agent_name,
    COALESCE(ticker, symbol) as ticker,
    insight_type,
    COALESCE(content, payload) as content,
    price_change, sentiment, confidence,
    catalyst_type, magnitude, created_at, model_used
  FROM agent_insights;

CREATE VIEW IF NOT EXISTS v_ohlcv AS
  SELECT id,
    COALESCE(ticker, symbol) as ticker,
    COALESCE(date, ts) as date,
    open, high, low, close, volume
  FROM daily_ohlcv;
```

**Then standardize** — ALL code must use `ticker` and `date` going forward (matches `data-layer.md`).

---

### BUG 2 — Duplicate MoveExplainer Files (CRITICAL 🔴)

**Problem**: `move_explainer.py` exists at BOTH root AND `agents/` with different schemas.

**Fix**:
```bash
# Delete the root-level duplicates (legacy)
rm move_explainer.py
rm market_rag.py

# The canonical versions are:
# agents/move_explainer.py  ← uses ticker/content schema ✓
# agents/market_rag.py      ← uses ticker/content schema ✓
```

---

### BUG 3 — CLI Test Harness Uses Wrong Column (HIGH 🟡)

In `agents/move_explainer.py` CLI test section (line ~316):
```python
# WRONG:
bars_exist = conn.execute(
    "SELECT COUNT(*) FROM daily_ohlcv WHERE symbol = ?", (symbol,)
).fetchone()[0]

# CORRECT:
bars_exist = conn.execute(
    "SELECT COUNT(*) FROM daily_ohlcv WHERE ticker = ?", (symbol,)
).fetchone()[0]
```

And the dummy data insert uses `symbol` and `ts` but the table uses `ticker` and `date`.

---

### BUG 4 — Collector fires MoveExplainer with stale data (HIGH 🟡)

In `agents/collector_agent.py`, the `_fetch_yfinance` function doesn't write OHLCV to SQLite before calling `on_market_update`. The MoveExplainer then reads 0 bars and returns `None`.

**Fix** — add to `fetch_ticker()` before the `on_market_update` call:

```python
# After df is fetched from yfinance, write to SQLite immediately:
from gateway.knowledge_store import knowledge_store
for idx, row in df.iterrows():
    knowledge_store.store_ohlcv(
        ticker=ticker,
        date=str(idx.date()),
        open=float(row["Open"]),
        high=float(row["High"]),
        low=float(row["Low"]),
        close=float(row["Close"]),
        volume=float(row["Volume"])
    )

# NOW call MoveExplainer (bars will exist in DB)
from agents.move_explainer import on_market_update
latest_close = float(df.iloc[-1]["Close"])
on_market_update(symbol=ticker, latest_close=latest_close)
```

---

### BUG 5 — Knowledge Graph Import in MoveExplainer (HIGH 🟡)

In `agents/move_explainer.py`, `_run_explanation()` does:
```python
from gateway.knowledge_graph_service import knowledge_graph
```
This import will crash if `gateway/knowledge_graph_service.py` doesn't exist.

**Fix**: Wrap in try/except:
```python
graph_context = ""
try:
    from gateway.knowledge_graph_service import knowledge_graph
    graph_context = knowledge_graph.get_code_context(symbol)
except ImportError:
    pass
```

---

### BUG 6 — strategy_generator_agent.py Python Syntax Error (MEDIUM 🟡)

In `agents/strategy_generator_agent.py`, line ~220:
```python
# WRONG (non-ASCII variable name — will crash):
self.vibe.generate_strategy(
    strategy描述=description,  # ← Chinese characters in Python param name!

# CORRECT:
self.vibe.generate_strategy(
    description=description,
```

---

### BUG 7 — AccuracyStoreAgent Uses Wrong Method (MEDIUM 🟡)

In `agents/accuracy_store.py`:
```python
conn = knowledge_store._get_conn()  # ← Private method, breaks encapsulation
```
**Fix**: Add a public method to KnowledgeStore:
```python
# In gateway/knowledge_store.py:
def update_suggestion_performance(self, suggestion_id: int, perf_1m: float):
    self._conn.execute(
        "UPDATE research_suggestions SET perf_1m = ? WHERE id = ?",
        (perf_1m, suggestion_id)
    )
    self._conn.commit()
```

---

## 3. Agent Architecture & Correct Workflow

### The 3-Wave Pipeline (Canonical Order)

```
TRIGGER: User query OR market_update event
           │
           ▼
┌─────────────────────────────────────────────────────┐
│  WAVE 1 — Parallel Intelligence (no dependencies)   │
│                                                     │
│  TechnicalSpecialist  ──┐                           │
│  MacroSpecialist      ──┼──► KnowledgeStore.store_insight()
│  FundamentalSpecialist──┘                           │
│                                                     │
│  Latency target: < 8 seconds                       │
└─────────────────────────────────────────────────────┘
           │ outputs stored in knowledge store
           ▼
┌─────────────────────────────────────────────────────┐
│  WAVE 2 — Knowledge-Aware Specialists               │
│           (reads Wave 1 insights via cross-agent)   │
│                                                     │
│  RiskSpecialist     ──┐  ← reads Technical signal  │
│  SentimentSpecialist──┼──► KnowledgeStore.store_insight()
│  SectorSpecialist   ──┤  ← reads Macro signal      │
│  CatalystSpecialist ──┘                             │
│                                                     │
│  Latency target: < 12 seconds (total from W1)      │
└─────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────┐
│  WAVE 3 — Decision Layer                            │
│                                                     │
│  SentimentClassifierAgent (FinBERT)                 │
│  SignalAggregatorAgent ──► Consensus Score          │
│  RiskManagerAgent      ──► APPROVE / BLOCK / SIZE   │
│  CritiqueAgent         ──► Contradiction Check      │
│                                                     │
│  Latency target: < 5 seconds (total from W2)       │
└─────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────┐
│  SYNTHESIS                                          │
│                                                     │
│  MythicOrchestrator._synthesize_final()             │
│    → LLM call with ALL specialist context           │
│    → Streamed response to UI                        │
│    → Persisted to agent_insights                    │
│    → Indexed to Qdrant RAG                          │
└─────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────┐
│  EXECUTION (DEEP / INSTITUTIONAL modes only)        │
│                                                     │
│  RiskManager APPROVES → BrokerRouter.execute()      │
│  PAPER_TRADE_MODE=True → PaperBroker (safe default) │
│  PAPER_TRADE_MODE=False → HyperliquidBroker (live)  │
└─────────────────────────────────────────────────────┘
```

### Agent Responsibility Matrix

| Agent | Input | Output | Persists? | Cross-Agent? |
|-------|-------|--------|-----------|-------------|
| `TechnicalSpecialist` | OHLCV | signal, confidence, patterns | ✅ knowledge_store | ✅ reads peers |
| `RiskSpecialist` | OHLCV + price | risk_level, VaR, drawdown | ✅ | ✅ reads Technical |
| `MacroSpecialist` | News headlines | macro_outlook, sentiment_score | ✅ | ✅ reads Technical |
| `SentimentSpecialist` | Headlines | sentiment_score, label | ✅ | ✅ |
| `FundamentalSpecialist` | Knowledge results | fundamental_analysis | ✅ | ✅ |
| `SectorSpecialist` | ticker + news | sector_analysis | ✅ | ✅ |
| `CatalystSpecialist` | News | catalyst_events | ✅ | ✅ |
| `SignalAggregatorAgent` | All specialist outputs | verdict, confidence, score | ✅ | ✅ reads all |
| `RiskManagerAgent` | Aggregator verdict + portfolio | APPROVE/BLOCK/SIZE | ❌ (decision only) | ✅ |
| `CritiqueAgent` | All specialist outputs | agreement_score, flags | ❌ | ✅ |
| `MoveExplainerAgent` | OHLCV + news | move explanation JSON | ✅ agent_insights | ❌ |
| `MarketRAGAgent` | question + symbol | retrieved context + SSE | ✅ rag_index_log | ❌ |
| `QueryRouter` | user query | routed result | ❌ | ✅ orchestrates all |

---

## 4. Data Pipeline — Truth First

### Every Data Write Must Follow This Sequence

```
1. FETCH   → collector_agent.fetch_ticker() [5-layer fallback]
      │
      ▼
2. PERSIST → knowledge_store.store_ohlcv() [SQLite daily_ohlcv]
      │
      ▼
3. TRIGGER → on_market_update(ticker, close) [MoveExplainer threshold check]
      │
      ▼
4. EXPLAIN → MoveExplainerAgent._run_explanation() [LLM call]
      │
      ▼
5. PERSIST → knowledge_store.store_insight() [agent_insights]
      │
      ▼
6. INDEX   → market_rag.index_insight() [Qdrant vector store]
      │
      ▼
7. EMIT    → WebSocket/SSE event to UI [real-time update]
```

### News Data Pipeline

```
RSS Scraper (every 15min)
    ├── rss_scraper.fetch_all()
    ├── knowledge_store.store_news(articles)
    └── index_news_headline() → Qdrant

Playwright Scraper (on-demand)
    ├── playwright_news.run_scraper(query)
    ├── save_articles() → knowledge_store.store_news()
    └── index_news_headline() → Qdrant

MCP News Agent (per-ticker)
    ├── McpNewsAgent.act() → knowledge_store.get_news_for_ticker()
    └── Fallback: RSS fetch if empty
```

### Data Freshness Rules

| Data Type | Max Age | Source | Fallback |
|-----------|---------|--------|---------|
| OHLCV (live) | 5 minutes | yfinance 5m bars | Stooq |
| OHLCV (daily) | 24 hours | yfinance 1d | Stooq → Alpha Vantage → Scrape |
| News | 15 minutes | RSS + MCP | Knowledge store cache |
| Move Explanation | Per new bar > 0.8% | MoveExplainer | Previous explanation |
| Agent Insights | Per analysis run | All specialists | Cached insights |
| RAG Index | Real-time | After each INSERT | Bulk index on startup |

---

## 5. Database Schema — Single Source of Truth

Use ONLY `agents/market_rag.py`'s `_ensure_tables()` — this is the authoritative schema. All tables must use:

```sql
-- CANONICAL SCHEMA (copy from data-layer.md)

CREATE TABLE daily_ohlcv (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker      TEXT NOT NULL,      -- NOT symbol
    date        TEXT NOT NULL,      -- NOT ts (ISO 8601 date string)
    open        REAL,
    high        REAL,
    low         REAL,
    close       REAL,
    volume      REAL,
    adj_close   REAL,
    market_cap  REAL DEFAULT 0,
    pe_ratio    REAL DEFAULT 0,
    source      TEXT DEFAULT 'yfinance',
    UNIQUE(ticker, date)
);

CREATE TABLE news_articles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker          TEXT NOT NULL,   -- NOT symbol
    headline        TEXT NOT NULL,
    url             TEXT,
    source          TEXT,
    sentiment_score REAL DEFAULT 0.0,
    published_at    TEXT,
    fetched_at      TEXT DEFAULT (datetime('now')),
    summary         TEXT,
    body            TEXT,
    relevance_score REAL DEFAULT 0.0
);

CREATE TABLE agent_insights (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name      TEXT NOT NULL,
    ticker          TEXT NOT NULL,   -- NOT symbol
    insight_type    TEXT NOT NULL,
    content         TEXT NOT NULL,   -- NOT payload (JSON blob)
    price_change    REAL,
    sentiment       TEXT,
    confidence      INTEGER,
    catalyst_type   TEXT,
    magnitude       TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    model_used      TEXT
);

CREATE TABLE research_suggestions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker      TEXT NOT NULL,
    score       REAL,
    signal      TEXT,
    reasoning   TEXT,
    breakdown   TEXT,
    perf_1m     REAL,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE agent_health (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name      TEXT NOT NULL UNIQUE,
    status          TEXT NOT NULL,
    last_run        TEXT,
    last_error      TEXT,
    run_count       INTEGER DEFAULT 0,
    error_count     INTEGER DEFAULT 0,
    avg_latency_ms  REAL DEFAULT 0.0,
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE rag_index_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type  TEXT NOT NULL,
    source_id    INTEGER NOT NULL,
    qdrant_id    TEXT NOT NULL,
    indexed_at   TEXT DEFAULT (datetime('now')),
    UNIQUE(source_type, source_id)
);

-- INDICES
CREATE INDEX IF NOT EXISTS idx_ohlcv_ticker_date ON daily_ohlcv(ticker, date DESC);
CREATE INDEX IF NOT EXISTS idx_news_ticker_pub    ON news_articles(ticker, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_insights_ticker    ON agent_insights(ticker, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_insights_agent     ON agent_insights(agent_name, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_health_agent       ON agent_health(agent_name);
```

---

## 6. LLM Routing — Profit-Grade Inference

### Provider Priority (Correct Order)

```python
# In llm/client.py — this is the CORRECT priority chain:

Priority 1: NVIDIA NIM       (best quality, needs API key)
Priority 2: OpenAI-compatible (e.g., OpenRouter, Groq)
Priority 3: LM Studio        (local, fast, no cost)
Priority 4: Local GGUF       (offline fallback)
Priority 5: Ollama           (secondary local)
Priority 6: Structured fallback (data-driven, NO LLM)
```

### Role → Model Mapping (Fix This)

```python
# core/config.py — set these environment variables:

SENTIMENT_MODEL  = "mistralai/mistral-7b-instruct-v0.3"    # Fast, cheap
REASONING_MODEL  = "nvidia/nemotron-4-340b-instruct"        # High quality
ANALYSIS_MODEL   = "moonshotai/kimi-k1.5"                  # Long context
GENERAL_MODEL    = "MiniMax-Text-01"                        # General purpose

# Role → Model mapping in llm/client.py:
# "sentiment" role → SENTIMENT_MODEL (64-512 tokens, temp=0.0)
# "reasoning" role → REASONING_MODEL (4096 tokens, temp=0.1)
# "analysis"  role → ANALYSIS_MODEL  (8192 tokens, temp=0.2)
# "general"   role → GENERAL_MODEL   (2048 tokens, temp=0.3)
```

### LLM Call Pattern (Every Agent Must Follow This)

```python
async def act(self, context: AgentContext) -> AgentContext:
    from llm.client import get_shared_llm
    llm = get_shared_llm()

    prompt = self._build_prompt(context)

    try:
        res = await llm.complete(
            prompt=prompt,
            system=self.system_prompt,
            expect_json=True,
            temperature=0.1,        # Low for analysis
            role="analysis"         # Route to best model
        )
        # Validate the response schema
        if isinstance(res, dict) and "signal" in res:
            context.result = res
        else:
            self._add_thought(context, "LLM returned invalid schema — using algorithmic fallback")
            context.result = self._compute_fallback(context.metadata)
    except Exception as e:
        context.errors.append(f"{self.name} LLM failed: {e}")
        context.result = self._compute_fallback(context.metadata)

    # ALWAYS persist insight
    try:
        from gateway.knowledge_store import knowledge_store
        if context.ticker and context.result:
            knowledge_store.store_insight(
                ticker=context.ticker,
                agent_name=self.name,
                insight_type="technical",  # change per agent domain
                content=str(context.result.get("summary", "")),
                confidence=context.result.get("confidence", 0.5)
            )
    except Exception:
        pass  # Non-fatal — never block trading on RAG failure

    return context
```

---

## 7. Signal Architecture — The Money Formula

### The Consensus Score Formula

```
Final Score = (Technical × 0.40) + (News Sentiment × 0.35) + (Social Sentiment × 0.15) + (Volume Delta × 0.10)

Conviction Multiplier = 1.2× if Volume > 1.5× 20-day average
```

### Verdict Thresholds

```python
# core/scoring.py — canonical thresholds:

if score > 0.65 AND confidence >= 65:   verdict = "BUY"
if score < -0.65 AND confidence >= 65:   verdict = "SELL"
if confidence < 50:                       verdict = "HOLD"  # Never trade doubt
else:                                     verdict = "HOLD"

# Strong signal:
if abs(score) > 0.80 AND confidence >= 80: is_strong = True
```

### Confidence Calibration

```python
# agents/critique_layer.py — calibrate_confidence():

final_confidence = (
    0.40 × specialist_agreement  +  # Do all agents agree?
    0.30 × rag_source_density    +  # How much historical data?
    0.30 × news_recency_score       # How fresh is the news?
)

# Penalties applied by CritiqueAgent:
if "RISK_CONTRADICTS_TECHNICAL":  confidence × 0.70
if "MACRO_CONTRADICTS_TECHNICAL": confidence × 0.80
if "LOW_OVERALL_CONFIDENCE":      confidence × 0.50
if cross_market_divergence:       confidence × 0.80

# Clamp: always between 0.10 and 0.95
```

### Position Sizing (RiskManagerAgent)

```python
# Conviction-Based Position Sizing:
if confidence >= 80:   multiplier = 1.0  # Full position (10% portfolio)
elif confidence >= 65: multiplier = 0.6  # 60% of max position
elif confidence >= 50: multiplier = 0.3  # 30% of max position
else:                  multiplier = 0.0  # BLOCK — do not trade

suggested_size = total_balance × MAX_POSITION_PCT × multiplier
# MAX_POSITION_PCT = 0.10 (10% hard cap per trade)
```

---

## 8. Risk Framework — Capital Protection First

### Circuit Breakers (In Order of Priority)

```
PRIORITY 1: Max Open Positions
  └── open_positions >= 5 → BLOCK all new trades

PRIORITY 2: Daily Loss Limit  
  └── daily_pnl_pct <= -5% → BLOCK all new trades until next day

PRIORITY 3: Force Close
  └── any position unrealized_pnl <= -15% → FORCE_CLOSE that position

PRIORITY 4: Cash Reserve
  └── available_cash < 20% of total_balance → BLOCK new trades

PRIORITY 5: Leverage Cap
  └── requested_leverage > MAX_LEVERAGE (10x) → Cap to MAX_LEVERAGE

PRIORITY 6: Confidence Check
  └── confidence < MIN_SIGNAL_CONFIDENCE (60) → BLOCK
```

### Settings — Real Money Configuration

```bash
# .env for REAL MONEY (proceed with extreme caution):
PAPER_TRADE_MODE=false            # ← Only set this when fully tested

# Risk limits (conservative for live):
MAX_POSITION_PCT=0.05             # 5% max (not 10%) for live
MAX_DAILY_LOSS_PCT=0.02           # 2% daily loss limit (not 5%) for live
MAX_OPEN_POSITIONS=3              # 3 max (not 5) for live
FORCE_CLOSE_LOSS_PCT=0.10         # 10% stop (not 15%) for live
BALANCE_RESERVE_PCT=0.30          # 30% cash reserve for live
MAX_LEVERAGE=5                    # 5x max (not 10x) for live
MIN_SIGNAL_CONFIDENCE=70          # 70% min (not 60%) for live

# Live broker:
HYPERLIQUID_PRIVATE_KEY=your_key_here
HYPERLIQUID_VAULT_ADDRESS=optional_vault
```

### Pre-Trade Validation Checklist (Automated)

Every trade must pass ALL before execution:

- [ ] `RiskManagerAgent.decision == "APPROVE"`
- [ ] `confidence >= MIN_SIGNAL_CONFIDENCE`
- [ ] `open_positions < MAX_OPEN_POSITIONS`
- [ ] `daily_pnl_pct > -MAX_DAILY_LOSS_PCT`
- [ ] `available_cash >= suggested_position_size`
- [ ] `PAPER_TRADE_MODE` checked before any broker call
- [ ] Signal is less than 5 minutes old (stale signal = no trade)

---

## 9. UI Data Flow — Real-Time Updates

### WebSocket Event Sequence (What the UI Receives)

```
Server Boot
   ├── 1. Bulk RAG index (all unindexed insights + news)
   ├── 2. Load watchlist from WATCHLIST env var
   └── 3. Trigger initial data fetch for all tickers

Every 5 Minutes (background scheduler):
   ├── collect_news_data() → RSS fetch → store_news() → index_news_headline()
   └── index_knowledge_to_rag() → Qdrant sync

Every 15 Minutes (market hours):
   ├── collect_daily_data() → fetch_ticker() → store_ohlcv()
   ├── on_market_update() → MoveExplainer threshold check
   └── WebSocket emit: { type: "price_update", ticker, close, change_pct }

On MoveExplainer trigger (>0.8% move):
   ├── _run_explanation() → LLM → persist insight
   ├── index_insight() → Qdrant
   └── WebSocket emit: { type: "move_explained", ticker, reason, sentiment, confidence }

On User Query:
   ├── QueryRouter.act() → MythicOrchestrator.orchestrate()
   ├── SSE stream: each token as "data: <token>\n\n"
   └── Final: "data: [DONE]\n\n"
```

### UI Component → API Endpoint Mapping

```
Dashboard Overview    → GET /api/watchlist          (BlobAgent blobs)
Stock Detail Page     → GET /api/stock/{ticker}      (BlobAgent.load_blob)
Price History Chart   → GET /api/history/{ticker}    (knowledge_store OHLCV)
Move Explanation      → GET /api/explain/{ticker}    (MoveExplainerAgent)
7-Day Forecast        → GET /api/forecast/{ticker}   (ForecastAgent)
News Feed             → GET /api/news/{ticker}       (McpNewsAgent)
Chat Interface        → POST /api/chat               (QueryRouter → Orchestrator)
Research Cards        → GET /api/research            (DeepResearchAgent)
Agent Health          → GET /api/health              (knowledge_store.get_collection_status)
Trade Signals         → GET /api/signals             (SignalAggregatorAgent)
Portfolio Status      → GET /api/portfolio           (BrokerRouter positions)
Accuracy Stats        → GET /api/accuracy            (AccuracyStoreAgent)
```

---

## 10. Chat Query Structure — User Message Format

### How to Write Queries for Best Results

The QueryRouter classifies user intent into 6 types. Structure your query to match the intent you want:

---

### Query Type 1 — Price Movement Explanation

**Format**: `"Why did [TICKER] [move/drop/surge/crash] [today/this week/recently]?"`

**Examples**:
```
"Why did AAPL drop today?"
"Why did BTC-USD surge this week?"
"What caused RELIANCE to move?"
"Explain why NVDA crashed yesterday"
```

**What you get**: Move explanation with reason, sentiment (BULLISH/BEARISH/NEUTRAL), confidence score, key headlines, catalyst type, and magnitude.

---

### Query Type 2 — Current Price & Market Status

**Format**: `"What is [TICKER] trading at?" / "Show me [TICKER] price"`

**Examples**:
```
"What is TSLA trading at right now?"
"Current price of BTC-USD"
"AAPL live price and volume"
"What's the market cap of NVDA?"
```

**What you get**: Current price, day change %, volume, market cap, P/E ratio.

---

### Query Type 3 — News & Catalyst Analysis

**Format**: `"What's the latest news on [TICKER]?" / "Any earnings news for [TICKER]?"`

**Examples**:
```
"What's the latest news on MSFT?"
"Any earnings announcements for GOOGL?"
"Show me recent headlines for ETH-USD"
"What news is moving TATAMOTORS today?"
"Breaking news for semiconductor stocks"
```

**What you get**: Top 5-10 recent headlines, sentiment scores, catalyst classification.

---

### Query Type 4 — Prediction & Forecast

**Format**: `"Should I buy [TICKER]?" / "Is [TICKER] a good time to enter?"`

**Examples**:
```
"Should I buy AAPL right now?"
"Is this a good time to enter SOL-USD?"
"Predict TSLA price next week"
"Will NVDA go up or down?"
"Entry point for BTC-USD long?"
"Best time to sell META?"
```

**What you get**: BUY/SELL/HOLD verdict, confidence score, entry price, target price, stop-loss, and reasoning from all 14 specialists.

---

### Query Type 5 — Risk Analysis

**Format**: `"How risky is [TICKER]?" / "What's the downside on [TICKER]?"`

**Examples**:
```
"How risky is TSLA right now?"
"What's the VaR on ETH-USD?"
"Risk analysis for RELIANCE"
"Max drawdown for my NVDA position?"
"Is BTC-USD in a crisis regime?"
"Volatility analysis for AAPL"
```

**What you get**: Risk level (LOW/MEDIUM/HIGH/EXTREME), VaR(95%), max drawdown, beta, volatility regime, stress scenarios.

---

### Query Type 6 — Comparison & Ranking

**Format**: `"Compare [TICKER1] vs [TICKER2]" / "Which is better, X or Y?"`

**Examples**:
```
"Compare AAPL vs MSFT"
"Which is better to buy now — NVDA or AMD?"
"BTC vs ETH sentiment comparison"
"RELIANCE vs TCS performance"
"Rank these: AAPL, TSLA, NVDA, META"
```

**What you get**: Side-by-side sentiment matrix, relative ranking, key differentiators.

---

### Research Mode Modifiers

Append these to any query to change depth:

```
[default]           → QUICK mode (< 5 seconds, Wave 1 only)
"deep analysis"     → DEEP mode (< 30 seconds, all waves + Quantic)
"institutional"     → INSTITUTIONAL mode (< 2 minutes, all waves + Swarm + Cross-market)

Examples:
"Deep analysis of AAPL — should I buy?"
"Institutional grade research on BTC-USD"
"Quick price check TSLA"
```

---

### Multi-Ticker Batch Queries

```
"Scan my watchlist: AAPL, TSLA, NVDA, META — which has the strongest buy signal?"
"Weekly summary for: BTC-USD, ETH-USD, SOL-USD"
"Compare sentiment across top tech stocks"
```

---

### Chat Response Format

Every chat response follows this structure:

```
🧠 AXIOM MYTHIC — [TICKER] Analysis
════════════════════════════════════

📊 Consensus: [BUY/SELL/HOLD] (Confidence: XX%)

📈 Technical Analysis
[Signal: BULLISH/BEARISH/NEUTRAL]
[Summary from TechnicalSpecialist]

⚠️ Risk Assessment
[Risk Level: LOW/MEDIUM/HIGH/EXTREME]
[VaR, drawdown, stress scenarios]

🌍 Macro Environment
[Outlook: BULLISH/BEARISH/NEUTRAL]
[News sentiment, earnings signals, rate impact]

💡 Key Catalysts
• [Headline 1]
• [Headline 2]

🎯 Investment Verdict
[BUY/SELL/HOLD] at $XXX.XX
Target: $XXX.XX | Stop: $XXX.XX
Position Size: X% of portfolio

🔍 Critique
[Contradiction flags if any]
Agreement Score: XX%
```

---

## 11. Real Money Readiness Checklist

Complete ALL items before setting `PAPER_TRADE_MODE=false`:

### Infrastructure
- [ ] Database schema migrated — single canonical schema, no duplicates
- [ ] All root-level duplicate files deleted (`move_explainer.py`, `market_rag.py`)
- [ ] Schema migration script run and verified: `python scripts/migrate_db_schema.py`
- [ ] OHLCV data writes verified before MoveExplainer trigger
- [ ] Qdrant running in server mode (not in-memory) for persistence
- [ ] Backup of `axiom_knowledge.db` before every migration

### Data Quality
- [ ] Watchlist tested — all tickers returning valid OHLCV data
- [ ] News pipeline active — RSS scraper running every 15 minutes
- [ ] MoveExplainer tested for 5+ tickers — explanations generating correctly
- [ ] RAG index populated — `index_all_unindexed()` run at startup
- [ ] Cross-agent insights working — Wave 2 agents reading Wave 1 outputs

### LLM & AI
- [ ] LLM endpoint live and responding in < 10 seconds
- [ ] All 7 specialist agents returning valid JSON schemas
- [ ] CritiqueAgent detecting contradictions correctly
- [ ] SignalAggregator producing BUY/SELL/HOLD verdicts with correct confidence
- [ ] RiskManager BLOCKING trades correctly when limits are hit
- [ ] Fallback algorithms work when LLM is unavailable

### Broker & Execution
- [ ] PaperBroker tested — 10+ simulated trades executed correctly
- [ ] HyperliquidBroker connected — `get_balance()` returning real balance
- [ ] Order flow tested in paper mode for all order types
- [ ] Position sizing calculations verified (Kelly + risk-parity)
- [ ] All circuit breakers tested — force close, daily loss limit, position limit

### UI & Monitoring
- [ ] All API endpoints returning correct data (health check all endpoints)
- [ ] WebSocket events firing for price updates, move explanations
- [ ] Agent health dashboard showing all agents as ACTIVE/IDLE (not ERROR)
- [ ] AccuracyStore recording and scoring predictions
- [ ] Self-improvement loop scoring predictions after 24 hours

### Paper Trading Validation
- [ ] Run paper trading for minimum **2 weeks**
- [ ] Achieve accuracy ≥ 0.65 (65% directional accuracy) on paper
- [ ] Sharpe ratio ≥ 1.0 on paper portfolio
- [ ] Maximum drawdown ≤ 15% on paper portfolio
- [ ] Win rate ≥ 55% on paper trades
- [ ] All circuit breakers triggered and behaved correctly at least once

---

## 12. Implementation Phases — Sprint Plan

### Phase 1 — Fix & Stabilize (Week 1-2)

**Priority**: Fix ALL critical bugs before building anything new.

| Task | File | Effort |
|------|------|--------|
| Run schema migration | `scripts/migrate_db_schema.py` | 2h |
| Delete duplicate root files | `move_explainer.py`, `market_rag.py` | 30min |
| Fix CLI test column names | `agents/move_explainer.py` | 1h |
| Fix OHLCV write before MoveExplainer | `agents/collector_agent.py` | 2h |
| Fix knowledge_graph import | `agents/move_explainer.py` | 30min |
| Fix strategy_generator syntax | `agents/strategy_generator_agent.py` | 30min |
| Fix AccuracyStoreAgent DB access | `agents/accuracy_store.py` | 1h |
| Standardize all table queries to `ticker`/`date` | All agents | 4h |
| Write integration test: data → explain → RAG → UI | `tests/test_pipeline.py` | 4h |

**Deliverable**: All agents start without errors. Pipeline test passes end-to-end.

---

### Phase 2 — Data Integrity (Week 2-3)

| Task | Description | Effort |
|------|-------------|--------|
| Centralize OHLCV writes | All data flows through `knowledge_store.store_ohlcv()` | 3h |
| News pipeline validation | Verify RSS → SQLite → Qdrant chain | 2h |
| MoveExplainer threshold tuning | Test 0.5%, 0.8%, 1.0% thresholds | 2h |
| Bulk RAG indexing on startup | Call `index_all_unindexed()` in `lifespan` | 1h |
| WebSocket event system | Real-time price + explanation events to UI | 6h |
| Agent health monitoring | All agents report to `agent_health` table | 2h |

**Deliverable**: Live data flowing to UI in real-time. RAG populated.

---

### Phase 3 — Signal Quality (Week 3-4)

| Task | Description | Effort |
|------|-------------|--------|
| Specialist prompt tuning | Optimize all 7 specialist system prompts | 8h |
| Cross-agent memory validation | Verify Wave 2 reads Wave 1 insights | 3h |
| CritiqueAgent contradiction detection | Test all contradiction scenarios | 4h |
| SignalAggregator weight tuning | A/B test signal weights | 6h |
| Confidence calibration | Verify `calibrate_confidence()` accuracy | 3h |
| Backtesting framework | Run 90-day backtest on all signals | 8h |

**Deliverable**: Signal accuracy ≥ 0.65. Sharpe ≥ 1.0 in backtest.

---

### Phase 4 — Paper Trading (Week 4-6)

| Task | Description | Effort |
|------|-------------|--------|
| PaperBroker full integration | Connect to all execution paths | 4h |
| Prediction store active | Log every signal with metadata | 2h |
| AccuracyStore scoring | Verify 24h delayed scoring | 3h |
| Self-improvement loop | Weekly reweight based on accuracy | 6h |
| UI trade dashboard | Show paper trades, P&L, win rate | 8h |
| Alert system | Notify on large moves, errors, signals | 4h |

**Deliverable**: 2 weeks paper trading. All metrics tracked.

---

### Phase 5 — Live Deployment (Week 7+)

| Task | Description | Effort |
|------|-------------|--------|
| Hyperliquid connection | Test with minimum capital | 4h |
| Conservative risk limits | 2% daily loss, 5% position max | 1h |
| Kill switch | Single-button full position liquidation | 2h |
| Monitoring dashboard | Real-time P&L, drawdown, agent health | 6h |
| Alerting | Email/Telegram on circuit breaker trigger | 4h |
| Gradual scaling | Start 1% position, scale to 5% over 4 weeks | ongoing |

---

## 13. Monitoring & Self-Healing

### Agent Health States

```
ACTIVE  → Agent ran successfully in last cycle
IDLE    → Agent waiting for next trigger (normal)
ERROR   → Agent failed — check last_error in agent_health table
TIMEOUT → Agent exceeded timeout — check network/LLM connectivity
```

### Self-Healing Rules

```python
# In BaseAgent.run() — after every failure:
if context.errors:
    knowledge_store.update_agent_health(
        self.name, "idle",  # Not "error" — allows next run to proceed
        latency_ms=latency,
        error=True
    )
    # NEVER permanently disable an agent — always allow retry

# Circuit breaker for repeated failures:
if agent_health.error_count > 5 and agent_health.avg_latency_ms > 30000:
    # Agent is consistently failing — alert admin
    send_alert(f"{agent_name} failing consistently — check LLM/DB")
```

### Scheduled Health Checks

```python
# scheduler/jobs.py — add these jobs:

# Every 5 minutes: verify all critical agents
@scheduler.add_job(interval=minutes(5))
async def health_check():
    critical_agents = [
        "TechnicalSpecialist", "RiskSpecialist", "MacroSpecialist",
        "SignalAggregatorAgent", "RiskManagerAgent", "MoveExplainerAgent"
    ]
    for agent in critical_agents:
        health = knowledge_store.get_agent_health(agent)
        if health.get("status") == "ERROR" and health.get("error_count", 0) > 3:
            # Restart agent + alert
            await restart_agent(agent)

# Every 1 hour: prediction scoring
@scheduler.add_job(interval=hours(1))
async def score_predictions():
    engine = SelfImprovementEngine(memory_manager)
    await engine._evaluate_pending_predictions()

# Every 24 hours: deep research sweep
@scheduler.add_job(cron="02:00")
async def deep_research():
    agent = DeepResearchAgent()
    await agent.run(AgentContext(task="Daily research sweep"))
```

### Key Metrics to Track (Daily)

```
Trading Metrics:
  ├── Win rate (target: > 55%)
  ├── Average win/loss ratio (target: > 1.5)
  ├── Sharpe ratio (target: > 1.0)
  ├── Max drawdown (alert if > 10%)
  └── Daily P&L vs benchmark

Signal Quality Metrics:
  ├── Signal accuracy by agent (target: > 65%)
  ├── Average confidence score (target: > 70%)
  ├── False positive rate (target: < 30%)
  └── Time from signal to execution (target: < 30 seconds)

System Health Metrics:
  ├── LLM latency p95 (alert if > 15 seconds)
  ├── Agent error rate (alert if > 5%)
  ├── Data freshness (alert if OHLCV > 20 minutes old)
  └── RAG index lag (alert if unindexed items > 100)
```

---

## Appendix A — Environment Variables Reference

```bash
# === DATABASE ===
KNOWLEDGE_DB_NAME=axiom_knowledge.db
KNOWLEDGE_DB_PATH=/path/to/axiom_knowledge.db

# === LLM PROVIDERS ===
LLM_PROVIDER=nvidia_nim          # nvidia_nim | lm_studio | openai_compatible | ollama
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NEMOTRON_API_KEY=your_key
MOONSHOT_API_KEY=your_key
MISTRAL_API_KEY=your_key
MINIMAX_API_KEY=your_key

# Models by role
SENTIMENT_MODEL=mistralai/mistral-7b-instruct-v0.3
REASONING_MODEL=nvidia/nemotron-4-340b-instruct
ANALYSIS_MODEL=moonshotai/kimi-k1.5
GENERAL_MODEL=MiniMax-Text-01

# === LOCAL LLM ===
USE_LM_STUDIO=false
LM_STUDIO_URL=http://localhost:1234/v1
LM_STUDIO_MODEL=local-model
OLLAMA_URL=http://localhost:11434

# === VECTOR STORE ===
QDRANT_MODE=server               # server for production, memory for dev
QDRANT_URL=http://localhost:6333
RAG_COLLECTION=market_memory
RAG_EMBED_DIM=384
RAG_TOP_K=5

# === DATA ===
WATCHLIST=AAPL,TSLA,NVDA,META,BTC-USD,ETH-USD,SOL-USD
ALPHA_VANTAGE_KEY=your_key      # optional
NEWS_LOOKBACK_HOURS=6
OHLCV_BARS_CONTEXT=12
MOVE_THRESHOLD_PCT=0.8

# === RISK ===
PAPER_TRADE_MODE=true            # ALWAYS true until fully tested
MAX_POSITION_PCT=0.10
MAX_DAILY_LOSS_PCT=0.05
MAX_OPEN_POSITIONS=5
FORCE_CLOSE_LOSS_PCT=0.15
BALANCE_RESERVE_PCT=0.20
MAX_LEVERAGE=10
MIN_SIGNAL_CONFIDENCE=60
MIN_CONSENSUS_AGENTS=3

# === BROKER ===
HYPERLIQUID_PRIVATE_KEY=
HYPERLIQUID_VAULT_ADDRESS=

# === SELF IMPROVEMENT ===
PREDICTION_SCORE_DELAY_HOURS=24
```

---

## Appendix B — File Deletion List

Delete these files — they are legacy duplicates causing schema conflicts:

```bash
# ROOT LEVEL DUPLICATES (DELETE THESE):
rm move_explainer.py          # Use agents/move_explainer.py instead
rm market_rag.py              # Use agents/market_rag.py instead

# KEEP THESE (CANONICAL VERSIONS):
# agents/move_explainer.py    ✅ canonical, ticker/content schema
# agents/market_rag.py        ✅ canonical, ticker/content schema
```

---

*Last updated: 2026-05-03 | Version: 4.0 Mythic | Status: Production Blueprint*
