# Self-Improvement Reference

## Architecture Overview

```
Every agent run → SelfImprovementEngine.process_agent_run()
                         ↓
              PerformanceTracker.record_run()
              (latency, errors, confidence)
                         ↓
              If directional signal found:
                  Store prediction to knowledge_store
                         ↓
              If errors > 0 OR confidence < 0.4:
                  _trigger_optimization()
                         ↓
              Every hour: _evaluate_pending_predictions()
                  Pull predictions from knowledge_store
                  Fetch actual prices → score accuracy →
                  AccuracyStore.record_outcome()
                         ↓
              _compute_agent_weights()
                  Per-agent accuracy → weight adjustments (0.6× to 1.3×)
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
#     "evaluated": 12, "skipped": 3, "failed": 0,
#     "average_accuracy": 0.71,
#     "agent_accuracies": {"TechnicalSpecialist": 0.68, "SentimentSpecialist": 0.75},
#     "updated_at": "2026-05-04T..."
#   },
#   "agent_weight_adjustments": {"TechnicalSpecialist": 1.1, "SentimentSpecialist": 1.3},
#   "feedback_loops": [
#     "agent_run_telemetry",
#     "prediction_outcome_scoring",
#     "low_confidence_optimization",
#     "dynamic_agent_weighting",
#     "all_agent_prediction_storage"
#   ]
# }
```

---

## Prediction Lifecycle

### 1. Automatic Prediction Storage (ALL agents)

Every agent that produces a directional signal (BULLISH/BEARISH/BUY/SELL) gets its prediction
stored automatically via `process_agent_run()`:

```python
# Called automatically at end of every agent's Claude Flow loop
async def process_agent_run(self, agent_name, context):
    # Record telemetry
    await self.tracker.record_run(agent_name, metrics)

    # Store prediction for directional signals
    if signal in ("BULLISH", "BEARISH", "BUY", "SELL", "STRONG BUY", "STRONG SELL"):
        knowledge_store.store_insight(
            ticker=ticker, agent_name=agent_name,
            insight_type="prediction",
            content=f"{signal} @ {price} | conf={confidence}",
            confidence=confidence,
        )
```

Agents that store predictions:
- TechnicalSpecialist
- MacroSpecialist
- SentimentSpecialist
- FundamentalSpecialist
- BreakoutMomentumAgent
- RegimeDetectorAgent
- SignalAggregatorAgent (final verdict)

### 2. Score a Prediction (Automatic, after 24h)

```python
# SelfImprovementEngine._evaluate_pending_predictions() runs every hour.
# It pulls predictions from BOTH:
#   1. memory.structured._predictions (in-memory)
#   2. knowledge_store.get_recent_insights(insight_type="prediction", hours=72)

scorer = PredictionScorer()
accuracy = scorer.calculate_accuracy(
    prediction_price=182.50,
    target_price=195.00,
    actual_price=190.00,
    direction="BULLISH"
)
# Returns 0.0 to 1.0 (0.6 in this case — moved 60% toward target)
```

### 3. Persist Accuracy

```python
accuracy_store.record_outcome(
    ticker="AAPL",
    model="TechnicalSpecialist",   # Per-agent tracking
    provider="yfinance",
    direction="BULLISH",
    accuracy=0.6
)
```

### 4. Dynamic Agent Weighting

```python
# Computed hourly by _compute_agent_weights()
# Based on historical accuracy from AccuracyStore

| Avg Accuracy | Weight Multiplier |
|-------------|-------------------|
| > 0.70 | 1.3× (boost) |
| > 0.60 | 1.1× |
| > 0.50 | 1.0× (neutral) |
| > 0.40 | 0.8× (penalize) |
| ≤ 0.40 | 0.6× (strong penalty) |

# Minimum 5 scored predictions before any adjustment
```

---

## AccuracyStore API

```python
from self_improvement.accuracy_store import accuracy_store

# Record an outcome
accuracy_store.record_outcome(ticker, model, provider, direction, accuracy)

# Get leaderboard (group by ticker, model, provider, or direction)
leaderboard = accuracy_store.get_leaderboard(group_by="model", limit=20)
# [{"model": "TechnicalSpecialist", "total_scored": 45, "avg_accuracy": 0.68, ...}]

# Get ticker breakdown
breakdown = accuracy_store.get_ticker_breakdown("AAPL")

# Get global summary
summary = accuracy_store.get_summary()
# {"tickers": 12, "providers": 3, "models": 7, "total_scored": 156, "global_avg_accuracy": 0.62}
```

---

## Performance Tracker

Tracks per-agent telemetry (in-memory, incremental moving averages):

```python
# Recorded automatically for every agent run:
{
    "runs": 45,
    "errors": 2,
    "avg_latency": 1250.0,   # milliseconds
    "avg_confidence": 0.72
}
```

---

## Optimization Triggers

When an agent has errors > 0 or confidence < 0.4:
1. `_trigger_optimization()` is called
2. Failure is logged to knowledge_store as `optimization_trigger` insight
3. Future: automatic prompt rewriting or parameter tuning (e.g., RSI period 14→10 in high vol)
