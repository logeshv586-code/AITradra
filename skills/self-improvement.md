# Self-Improvement Reference

## Architecture Overview

```
Every agent run → SelfImprovementEngine.process_agent_run()
                         ↓
              PerformanceTracker.record_run()
              (latency, errors, confidence)
                         ↓
              If errors > 0 OR confidence < 0.4:
                  _trigger_optimization()
                         ↓
              Every hour: _evaluate_pending_predictions()
                  Fetch actual prices → score accuracy → 
                  AccuracyStore.record_outcome()
```

---

## SelfImprovementEngine

```python
from self_improvement.engine import SelfImprovementEngine
from memory.memory_manager import MemoryManager

memory = MemoryManager()
engine = SelfImprovementEngine(memory_manager=memory)

# Start background optimization loop (runs hourly)
await engine.start()

# Get current status
status = await engine.get_status()
# {
#   "enabled": True,
#   "loop_running": True,
#   "agent_health": {...},
#   "prediction_scoring": {
#     "evaluated": 12,
#     "skipped": 3,
#     "failed": 0,
#     "average_accuracy": 0.71,
#     "updated_at": "2026-05-04T..."
#   }
# }
```

---

## Prediction Lifecycle

### 1. Store a Prediction
```python
# Called when final verdict is generated:
pred_id = await memory_manager.store_prediction(
    ticker=ticker,
    prediction={
        "final_decision": "BUY",          # BUY | SELL | HOLD
        "confidence": 0.78,
        "current_price": 182.50,          # Price at prediction time
        "target_price": 195.00,           # Expected target
        "expected_move_percent": 6.8,     # % expected move
        "price_at_prediction": 182.50,
        "prediction_direction": "BULLISH",
    },
    reasoning="Technical + macro alignment. Earnings beat expected.",
    confidence=0.78
)
```

### 2. Score a Prediction (Automatic, after 24h)
```python
# SelfImprovementEngine._evaluate_pending_predictions() runs automatically.
# But you can also score manually:

scorer = PredictionScorer()
accuracy = scorer.calculate_accuracy(
    prediction_price=182.50,
    target_price=195.00,
    actual_price=191.20,    # What actually happened
    direction="BULLISH"
)
# Returns 0.0 to 1.0
# BULLISH: 1.0 if actual >= target, 0.0 if actual <= prediction
# BEARISH: 1.0 if actual <= target, 0.0 if actual >= prediction
```

### 3. Normalize Direction
```python
scorer.normalize_direction("BUY")        → "BULLISH"
scorer.normalize_direction("UP")         → "BULLISH"
scorer.normalize_direction("LONG")       → "BULLISH"
scorer.normalize_direction("ACCUMULATE") → "BULLISH"
scorer.normalize_direction("SELL")       → "BEARISH"
scorer.normalize_direction("SHORT")      → "BEARISH"
scorer.normalize_direction("DOWN")       → "BEARISH"
scorer.normalize_direction("HOLD")       → "NEUTRAL"
```

---

## AccuracyStore

SQLite-backed aggregate accuracy tracking per (ticker, model, provider, direction):

```python
from self_improvement.accuracy_store import accuracy_store

# Record an outcome
accuracy_store.record_outcome(
    ticker="AAPL",
    model="nvidia-nemotron-4B",
    provider="local_gguf",
    direction="BULLISH",
    accuracy=0.85
)

# Get leaderboard
leaders = accuracy_store.get_leaderboard(group_by="ticker", limit=20)
# [{"ticker": "NVDA", "avg_accuracy": 0.82, "total_scored": 45, ...}]

# Get breakdown for one ticker
breakdown = accuracy_store.get_ticker_breakdown("AAPL")
# [{"model": "...", "provider": "...", "direction": "BULLISH", "avg_accuracy": 0.79}]

# Global summary
summary = accuracy_store.get_summary()
# {"tickers": 12, "providers": 3, "total_scored": 234, "global_avg_accuracy": 0.71}
```

---

## PerformanceTracker

In-memory agent telemetry (phase 1 — will move to SQLite):

```python
from self_improvement.performance_tracker import PerformanceTracker

tracker = PerformanceTracker()

# Record an agent run
await tracker.record_run("TechnicalSpecialist", {
    "latency_ms": 2340,
    "confidence": 0.72,
    "error_count": 0,
    "success": True
})

# Get health for one agent
health = await tracker.get_agent_health("TechnicalSpecialist")
# {"runs": 45, "errors": 2, "avg_latency": 1850.0, "avg_confidence": 0.68}

# Get system-wide health
system = await tracker.get_system_health()
# {"TechnicalSpecialist": {...}, "RiskSpecialist": {...}, ...}
```

---

## Memory Manager

Three-tier memory: Working (in-memory) → Episodic (SQLite) → Semantic (FAISS)

```python
from memory.memory_manager import MemoryManager

memory = MemoryManager()
await memory.initialize()

# WORKING MEMORY (current session)
memory.set_working_context("current_ticker", "AAPL")
ticker = memory.get_working_context("current_ticker")

memory.add_conversation_turn("user", "What's happening with AAPL?")
memory.add_conversation_turn("assistant", "AAPL is up 2.3% on earnings beat.")
turns = memory.get_conversation(limit=10)

# EPISODIC MEMORY (SQLite — persists across restarts)
await memory.store_episode(
    agent="TechnicalSpecialist",
    task="Analyze AAPL for DEEP mode",
    result="BULLISH signal at 0.78 confidence",
    reflection="Strong technical alignment with earnings catalyst",
    confidence=0.78,
    errors=[]
)

# Search episodic memory by keyword
past_runs = await memory.recall_relevant("AAPL technical bullish", limit=5)

# SEMANTIC MEMORY (FAISS vector search)
results = await memory.semantic_search("earnings beat tech stock rally", n_results=5)

# PREDICTIONS
pred_id = await memory.store_prediction(ticker, prediction_dict, reasoning, confidence)
past_preds = await memory.get_past_predictions("AAPL", limit=10)
await memory.update_prediction_outcome(pred_id, actual_price, accuracy_score, outcome)

# STATUS
status = await memory.get_system_status()
# {"episodic_episodes": 1250, "working_memory_keys": 3, "predictions_tracked": 89}
```

---

## Nightly Self-Improvement Loop (autoresearch)

From `autoresearch/GOAL.md`:

```bash
# Target: improve MythicOrchestrator signal accuracy ≥ 0.75
python scripts/eval_predictions.py
# Output: METRIC accuracy=0.XX

# The nightly loop modifies these files:
# - agents/specialist_agents.py  (system prompts, thresholds)
# - gateway/llm_prompts.py       (prompt templates)
# - agents/orchestrator.py       (wave logic, fusion weights)

# Constraints:
# - Zero paid APIs (local GGUF or SearXNG only)
# - Each iteration < 5 minutes
# - Primary model: NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf
# - Stop: accuracy >= 0.75 OR 20 iterations without improvement
```

---

## AccuracyStoreAgent (Nightly Audit)

Automatically scores 24h-old research suggestions:

```python
from agents.accuracy_store import AccuracyStoreAgent

agent = AccuracyStoreAgent()
ctx = AgentContext(task="Nightly accuracy sweep")
result = await agent.run(ctx)

# result.result = {"audited": 8, "accuracy": 0.625}
# Prints: "Audited 8 suggestions. Swarm accuracy: 62.5%"
```

---

## Adding Accuracy Feedback to Any Agent

To make any agent contribute to the self-improvement loop:

```python
# In your agent's act() or reflect():
async def reflect(self, context: AgentContext) -> AgentContext:
    # 1. Store prediction if making a directional call
    if context.result.get("signal") in ("BULLISH", "BEARISH"):
        from memory.memory_manager import MemoryManager
        memory = MemoryManager()
        await memory.store_prediction(
            ticker=context.ticker,
            prediction={
                "final_decision": context.result["signal"],
                "confidence": context.result.get("confidence", 0.5),
                "price_at_prediction": context.observations.get("current_price"),
                "prediction_direction": context.result["signal"],
                "expected_move_percent": 3.0,
            },
            reasoning=context.result.get("summary", ""),
            confidence=context.result.get("confidence", 0.5),
        )
    
    context.confidence = context.result.get("confidence", 0.5)
    context.reflection = context.result.get("summary", "Analysis complete")
    return context
```
