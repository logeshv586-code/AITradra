# Data Layer Reference

## SQLite Schema (axiom_knowledge.db)

### daily_ohlcv
```sql
CREATE TABLE daily_ohlcv (
    id          INTEGER PRIMARY KEY,
    ticker      TEXT NOT NULL,      -- was 'symbol' in legacy schema
    date        TEXT NOT NULL,      -- was 'ts' in legacy schema
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
```

### news_articles
```sql
CREATE TABLE news_articles (
    id              INTEGER PRIMARY KEY,
    ticker          TEXT NOT NULL,
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
```

### agent_insights
```sql
CREATE TABLE agent_insights (
    id              INTEGER PRIMARY KEY,
    agent_name      TEXT NOT NULL,
    ticker          TEXT NOT NULL,
    insight_type    TEXT NOT NULL,   -- technical|risk|macro|sentiment|move_explanation
    content         TEXT NOT NULL,   -- was 'payload' in legacy schema
    price_change    REAL,
    sentiment       TEXT,
    confidence      INTEGER,         -- 0-100
    catalyst_type   TEXT,
    magnitude       TEXT,            -- MINOR|MODERATE|SIGNIFICANT|EXTREME
    created_at      TEXT DEFAULT (datetime('now')),
    model_used      TEXT
);
```

### research_suggestions
```sql
CREATE TABLE research_suggestions (
    id          INTEGER PRIMARY KEY,
    ticker      TEXT NOT NULL,
    score       REAL,               -- 0.0 to 1.0 conviction
    signal      TEXT,               -- BUY|STRONG BUY|SELL|HOLD
    reasoning   TEXT,
    breakdown   TEXT,               -- JSON of specialist outputs
    perf_1m     REAL,               -- 1-month actual performance (updated by AccuracyStoreAgent)
    created_at  TEXT DEFAULT (datetime('now'))
);
```

### agent_health
```sql
CREATE TABLE agent_health (
    id              INTEGER PRIMARY KEY,
    agent_name      TEXT NOT NULL,
    status          TEXT NOT NULL,   -- active|idle|error
    last_run        TEXT,
    last_error      TEXT,
    run_count       INTEGER DEFAULT 0,
    error_count     INTEGER DEFAULT 0,
    avg_latency_ms  REAL DEFAULT 0.0,
    updated_at      TEXT DEFAULT (datetime('now'))
);
```

### rag_index_log
```sql
CREATE TABLE rag_index_log (
    id           INTEGER PRIMARY KEY,
    source_type  TEXT NOT NULL,   -- insight|news
    source_id    INTEGER NOT NULL,
    qdrant_id    TEXT NOT NULL,
    indexed_at   TEXT DEFAULT (datetime('now')),
    UNIQUE(source_type, source_id)
);
```

### agent_episodes
```sql
CREATE TABLE agent_episodes (
    id            INTEGER PRIMARY KEY,
    agent         TEXT NOT NULL,
    task          TEXT NOT NULL,
    result        TEXT,
    reflection    TEXT,
    confidence    REAL DEFAULT 0.0,
    errors        TEXT,
    metadata_json TEXT,
    created_at    TEXT DEFAULT (datetime('now'))
);
```

---

## Schema Migration Issues

**CRITICAL**: The codebase has two schema versions. Always check which one you have:

```python
# Check in scratch/check_schema.py or:
import sqlite3
conn = sqlite3.connect("axiom_knowledge.db")
cols = [r[1] for r in conn.execute("PRAGMA table_info(agent_insights)").fetchall()]
# Look for 'ticker' vs 'symbol', 'content' vs 'payload'
```

If you see `symbol` and `payload` (legacy), run:
```bash
python scratch/migrate_db.py
python scripts/migrate_db_schema.py
```

---

## KnowledgeStore API

Main interface: `from gateway.knowledge_store import knowledge_store`

```python
# Store market data
knowledge_store.store_ohlcv(ticker, date, open, high, low, close, volume)
knowledge_store.store_news(articles: list[dict])  # headline, ticker, source, published_at, sentiment_score

# Store agent outputs
knowledge_store.store_insight(ticker, agent_name, insight_type, content, confidence)
knowledge_store.store_research_suggestion(ticker, score, signal, reasoning, breakdown, perf_1m)

# Read data
knowledge_store.get_ohlcv_history(ticker, days=365)         # List of OHLCV dicts
knowledge_store.get_news_for_ticker(ticker, limit=20, days=7) # Recent articles
knowledge_store.get_agent_insights(ticker)                   # All insights
knowledge_store.get_latest_insights(ticker, agent_name, limit)
knowledge_store.get_recent_insights(ticker, hours=24)        # Cross-agent memory
knowledge_store.get_latest_research_suggestions(limit=10)

# Agent health
knowledge_store.update_agent_health(agent_name, status, latency_ms, task, error)
knowledge_store.get_collection_status()

# KnowledgeStore search
knowledge_store.search_all(query, limit=10)

# Episode tracking (for checkpoint/resume)
knowledge_store.store_episode_start(session_id, agent_name, query)
knowledge_store.update_episode_checkpoint(session_id, agent_name, state_dict)
knowledge_store.complete_episode(session_id, agent_name, result_dict)
knowledge_store.fail_episode(session_id, agent_name, error_str)
knowledge_store.get_episode_state(session_id, agent_name)
```

---

## Qdrant Vector Store (MarketRAG)

**Location**: `agents/market_rag.py`
**Collection**: `market_memory`
**Vector dim**: 384 (all-MiniLM-L6-v2) or auto-detected from LM Studio

### Environment Variables
```bash
QDRANT_MODE=memory       # In-memory (default, resets on restart)
QDRANT_MODE=server       # Persistent server
QDRANT_URL=http://localhost:6333
RAG_COLLECTION=market_memory
RAG_EMBED_DIM=384
RAG_TOP_K=5
```

### Indexing New Content
```python
from agents.market_rag import index_insight, index_news_headline

# After every agent_insights INSERT:
index_insight(insight_id, ticker, insight_text, metadata_dict)

# After every news_articles INSERT:
index_news_headline(news_id, ticker, headline, metadata_dict)

# Bulk index all unindexed content on startup:
agent = get_agent()
counts = agent.index_all_unindexed()
# Returns {"insights": N, "news": M}
```

### Retrieval
```python
from agents.market_rag import get_agent as get_rag

rag = get_rag()
chunks = rag.retrieve(question="Why did AAPL drop?", symbol="AAPL", top_k=5)
# Returns List[RetrievedChunk] with .score, .text, .source_type, .created_at

answer = rag.ask_sync("What is the current trend for AAPL?", symbol="AAPL")
# Returns full answer string (blocking)
```

---

## FAISS Index (RagAgent)

**Location**: `agents/rag_agent.py`
**Index file**: `gateway/market_rag_index/market.index`
**Model**: `all-MiniLM-L6-v2` (sentence-transformers)
**Dimension**: 384

### Usage
```python
from agents.rag_agent import RagAgent

rag = RagAgent()
rag.load_index()  # Load persisted FAISS index

# Index content
await rag.index_news_article({"ticker": "AAPL", "headline": "...", "summary": "..."})
await rag.index_daily_snapshot(ticker, snapshot_dict)
await rag.index_market_event(ticker, event_text, source_url)

# Search
results = await rag.search_for_ticker("earnings beat", "AAPL", k=5)

# Save index periodically
rag.save_index()
```

---

## Data Collector Fallback Chain

`agents/collector_agent.py` — `fetch_ticker(ticker, period)`:

1. **yfinance** — Primary. OHLCV + market cap + P/E. Uses `download()` + `Ticker.fast_info`
2. **Stooq** — Free CSV. `https://stooq.com/q/d/l/?s={ticker}&i=d`. Converts US=`.US`, crypto=`.V`
3. **Alpha Vantage** — Free tier (25/day). Set `ALPHA_VANTAGE_KEY` env var. Only US equities.
4. **FRED** — Macro instruments only (VIX=`VIXCLS`, 10Y=`DGS10`, etc.)
5. **Web Scrape** — Yahoo Finance HTML → MarketWatch HTML. Returns snapshot (1 bar)
6. **Stale Cache** — Returns cached data with warning if all sources fail

### Ticker Aliases
```python
# In collector_agent.py TICKER_ALIASES dict
"TATAMOTORS" → "TATAMOTORS.NS"  # Indian NSE
"FB" → "META"                   # Rebranded
"MATIC-USD" → "POL-USD"         # Rebranded
```

### Stooq Symbol Conversion
```python
"AAPL" → "AAPL.US"
"BTC-USD" → "BTC.V"
"RELIANCE" → "RELIANCE.IN"
"TATAMOTORS.NS" → "TATAMOTORS.IN"
```

---

## MCP Server Configuration

`mcp_config.json` in project root:
```json
{
  "mcpServers": {
    "coingecko": {
      "command": "npx",
      "args": ["-y", "@llmindset/mcp-coingecko"]
    },
    "fetch": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-fetch"]
    },
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"]
    }
  }
}
```

---

## News Pipeline

```
RSS feeds (every 15min) → gateway/scrapers/rss_scraper.py → news_articles table
Playwright scraper (on demand) → scrapers/playwright_news.py → knowledge_store.store_news()
MCP News Agent → mcp/news_mcp.py → knowledge_store.get_news_for_ticker()
```

### News Freshness Check
```python
# In McpNewsAgent.act():
recent_news = knowledge_store.get_news_for_ticker(ticker, limit=20, days=7)
if not recent_news:
    # Trigger RSS fetch
    await rss_scraper.fetch_all()
    # Re-check
    recent_news = knowledge_store.get_news_for_ticker(ticker, limit=20, days=7)
```

---

## Crypto Data via CoinGecko MCP

`mcp/crypto_gateway.py` — Wraps CoinGecko API:

```python
from mcp.crypto_gateway import get_crypto_gateway

gateway = get_crypto_gateway()
data = await gateway.get_price("BTC-USD")
# Returns: {symbol, price, volume_24h, change_24h_pct, Open, High, Low, Close, Volume}
```

Supported slugs: `BTC-USD, ETH-USD, SOL-USD, BNB-USD, XRP-USD, ADA-USD, AVAX-USD, DOGE-USD, DOT-USD, LINK-USD, MATIC-USD`
