---
name: axiom-trading-intelligence
description: |
  Master skill for the AXIOM/AITradra multi-agent stock market trading intelligence platform. Use this skill ALWAYS when working on ANY aspect of this codebase including: agent development, trading strategy, signal aggregation, risk management, broker integration, RAG/memory systems, LLM orchestration, data pipelines, backtesting, portfolio optimization, technical analysis, news intelligence, sentiment analysis, market regime detection, options flow, earnings prediction, arbitrage detection, self-improvement loops, batch processing, MCP integrations, SQLite schema, Qdrant vector store, FAISS indexing, Hyperliquid broker, Claude Flow loop (OBSERVE→THINK→PLAN→ACT→REFLECT→IMPROVE), or any feature that helps agents make profitable trading decisions. Trigger on: "improve agent", "add strategy", "fix signal", "trading logic", "make profit", "agent intelligence", "market analysis", "backtest", "risk manager", "position sizing", "sentiment", "technical indicator", "momentum", "orchestrator", "pipeline", "LLM call", "RAG", "memory", "news scraper", "price data", "OHLCV", "Hyperliquid", "batch agent", "nightly job", "accuracy", "prediction scoring", or any mention of stocks, crypto, trading, or financial analysis in the context of this platform.
---

# AXIOM / AITradra Trading Intelligence Skill

## Platform Overview

AXIOM is a **multi-agent, multi-layer AI trading system** with these core layers:

| Layer | Purpose | Key Files |
|-------|---------|-----------|
| Data Engine | OHLCV collection, price feeds | `agents/collector_agent.py`, `agents/data_agent.py` |
| News Intelligence | Scraping, sentiment, move explanations | `agents/move_explainer.py`, `agents/mcp_news_agent.py` |
| RAG / Memory | Qdrant + FAISS semantic search | `agents/market_rag.py`, `agents/rag_agent.py`, `memory/memory_manager.py` |
| Specialists | Technical, Risk, Macro, Sentiment, Fundamental | `agents/specialist_agents.py`, `agents/extended_specialists.py` |
| Orchestration | MythicOrchestrator, QueryRouter, LangGraph | `agents/orchestrator.py`, `agents/query_router.py` |
| Risk & Execution | RiskManager, SignalAggregator, Brokers | `agents/risk_manager.py`, `agents/signal_aggregator.py`, `brokers/` |
| Self-Improvement | Scoring, accuracy tracking, optimization | `self_improvement/` |
| Batch / Nightly | Historical backfill, batch processing | `agents/batch_agent.py` |

## Claude Flow Loop — The Foundation

**Every agent MUST implement all 5 abstract methods:**

```python
async def observe(self, context: AgentContext) -> AgentContext:
    # Gather data, check context, load from memory
    pass

async def think(self, context: AgentContext) -> AgentContext:
    # Form hypothesis, log thoughts with self._add_thought()
    pass

async def plan(self, context: AgentContext) -> AgentContext:
    # Add steps to context.plan list
    pass

async def act(self, context: AgentContext) -> AgentContext:
    # Execute — call LLMs, databases, APIs
    # Set context.result with structured output
    pass

async def reflect(self, context: AgentContext) -> AgentContext:
    # Set context.confidence (0.0–1.0) and context.reflection string
    pass
```

**AgentContext fields to use:**
- `context.ticker` — Stock/crypto symbol
- `context.observations` — Input data dict (OHLCV, news, indicators)
- `context.metadata` — Pass-through data from callers
- `context.result` — OUTPUT: always a dict with structured data
- `context.thoughts` — Log reasoning via `self._add_thought(context, "...")`
- `context.errors` — Append error strings here (don't raise)
- `context.confidence` — Float 0.0–1.0 set in `reflect()`

---

## Agent Development Patterns

See `references/agent-patterns.md` for complete patterns. Quick reference:

### Signal Output Schema (all specialist agents must return this shape)
```python
context.result = {
    "signal": "BULLISH|BEARISH|NEUTRAL",
    "confidence": 0.0,      # 0.0 to 1.0
    "summary": "...",       # One sentence
    "score": 0.0,           # Normalized -1.0 to +1.0
    # domain-specific keys below
}
```

### LLM Call Pattern (always async, always with fallback)
```python
from llm.client import get_shared_llm
llm = get_shared_llm()

try:
    res = await llm.complete(
        prompt=prompt,
        system=system_prompt,
        expect_json=True,       # Returns dict if JSON
        temperature=0.1,        # Low for analysis
        role="analysis"         # routes to best model
    )
    if isinstance(res, dict) and "signal" in res:
        context.result = res
    else:
        context.result = self._compute_fallback(...)
except Exception:
    context.result = self._compute_fallback(...)
```

### KnowledgeStore Pattern (persist insights)
```python
from gateway.knowledge_store import knowledge_store

# Store an insight after act()
knowledge_store.store_insight(
    ticker=ticker,
    agent_name=self.name,
    insight_type="technical|risk|macro|sentiment",
    content=str(context.result.get("summary", "")),
    confidence=context.result.get("confidence", 0.5)
)

# Read cross-agent insights in observe()
insights = await self._get_cross_agent_insights(ticker, hours=24)
```

---

## Trading Signal Architecture

See `references/signal-architecture.md` for the full weighting system.

### Consensus Formula (SignalAggregatorAgent)
```
Final Score = (Technical × 0.4) + (News Sentiment × 0.4) + (Volume × 0.2)
Conviction Multiplier = 1.2× if Volume > 1.5× 20-day average
```

### Verdict Thresholds
| Score | Verdict |
|-------|---------|
| > 0.65 + confidence > 65 | BUY |
| < -0.65 + confidence > 65 | SELL |
| Otherwise | HOLD |

### Risk Manager Approval Gates
1. Max open positions check → BLOCK if exceeded
2. Daily loss circuit breaker → BLOCK if exceeded  
3. Force close check → FORCE_CLOSE if position > threshold loss
4. Balance reserve protection → BLOCK if cash < reserve
5. Leverage capping → Cap to MAX_LEVERAGE setting
6. Conviction-based sizing → 100%/60%/30% multiplier by confidence tier

---

## Data Flow Architecture

```
yfinance / CoinGecko / Stooq / Alpha Vantage / Web Scrape
        ↓
  collector_agent.py  (5-layer fallback chain)
        ↓
  daily_ohlcv (SQLite)  ←→  rag_index_log (Qdrant)
        ↓
  news_articles (SQLite) ←→  move_explainer.py
        ↓
  agent_insights (SQLite) → market_rag.py (Qdrant vectors)
        ↓
  QueryRouter → MythicOrchestrator
        ↓
  [TechnicalSpecialist, RiskSpecialist, MacroSpecialist] (Wave 1, parallel)
        ↓
  [SentimentSpecialist, SectorSpecialist, CatalystSpecialist] (Wave 2)
        ↓
  CritiqueAgent → SignalAggregatorAgent → RiskManagerAgent
        ↓
  Final Response + research_suggestions (SQLite)
```

---

## Key Configuration Settings

All live in `core/config.py` via `settings`:

```python
settings.MAX_POSITION_PCT       # Max % of portfolio per trade
settings.MAX_DAILY_LOSS_PCT     # Daily stop-loss circuit breaker
settings.MAX_OPEN_POSITIONS     # Max concurrent positions
settings.FORCE_CLOSE_LOSS_PCT   # Force-close threshold
settings.BALANCE_RESERVE_PCT    # Minimum cash reserve
settings.MAX_LEVERAGE           # Hard leverage cap
settings.MIN_SIGNAL_CONFIDENCE  # Min confidence to trigger trade
settings.MIN_CONSENSUS_AGENTS   # Min agents agreeing for trade
settings.PAPER_TRADE_MODE       # True = no real orders
```

---

## What's in Each Reference File

- `references/agent-patterns.md` — Full agent templates, specialist patterns, error handling
- `references/signal-architecture.md` — Complete signal math, weighting, scoring formulas
- `references/data-layer.md` — SQLite schemas, Qdrant setup, FAISS indexing, MCP integrations
- `references/trading-strategies.md` — All implemented strategies, how to add new ones
- `references/llm-prompts.md` — System prompts for all agent roles, prompt engineering guide
- `references/risk-framework.md` — Full risk model, Kelly criterion, VaR, position sizing
- `references/broker-integration.md` — Hyperliquid, CCXT, PaperBroker integration guide
- `references/self-improvement.md` — Accuracy scoring, prediction resolution, optimization loop

---

## When Adding a New Agent

1. Inherit from `BaseAgent` in `agents/base_agent.py`
2. Implement all 5 abstract methods
3. Set `context.result` as a dict with `signal`, `confidence`, `summary`
4. Call `knowledge_store.store_insight()` in `act()` to enable cross-agent memory
5. Register in `agents/orchestrator.py` in the appropriate wave
6. Add to the relevant pipeline in `agents/legacy/orchestrator/graph.py` if using LangGraph

## When Improving Signal Accuracy

1. Check `self_improvement/accuracy_store.py` for current performance metrics
2. Tune weights in `core/scoring.py` — `calculate_consensus_verdict()`
3. Adjust LLM prompts in `agents/specialist_agents.py` system_prompt strings
4. Review `autoresearch/GOAL.md` for nightly self-improvement targets
5. Run `python scripts/eval_predictions.py` to measure accuracy

## When Debugging Data Issues

1. Run `python scratch/check_schema.py` to verify SQLite table columns
2. Run `python scratch/full_diag_v2.py` to see all table contents
3. Check `agents/collector_agent.py` fallback chain — 5 levels
4. Verify `TICKER_ALIASES` dict for renamed/rebranded tickers

---

## Profit-Maximizing Checklist

Before any trading feature is considered complete:

- [ ] Agent uses cross-agent insights (`_get_cross_agent_insights`)
- [ ] Result stored to KnowledgeStore (`store_insight`)
- [ ] Confidence score set realistically (not always 0.5)
- [ ] LLM call has data-driven fallback
- [ ] Risk manager is called before any order
- [ ] Position size respects `MAX_POSITION_PCT`
- [ ] Paper trade mode checked before live order
- [ ] Prediction stored for accuracy tracking
- [ ] Error appended to `context.errors` (never raise)
- [ ] Reflection set with actionable insight
