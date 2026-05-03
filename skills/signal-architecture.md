# Signal Architecture Reference

## Complete Signal Math

### Layer 1: Individual Specialist Scores

Each specialist returns a normalized score:

| Specialist | Score Range | Key Computation |
|-----------|-------------|-----------------|
| TechnicalSpecialist | -1.0 to +1.0 | RSI + MACD + Bollinger blend |
| RiskSpecialist | 0.0 to 1.0 (risk level) | VaR + Beta + Drawdown |
| MacroSpecialist | -1.0 to +1.0 | News sentiment + Yield curve |
| SentimentSpecialist | -1.0 to +1.0 | FinBERT scores on headlines |
| FundamentalSpecialist | -1.0 to +1.0 | P/E, growth, earnings quality |
| SectorSpecialist | -1.0 to +1.0 | Sector rotation signals |
| CatalystSpecialist | -0.5 to +0.5 | Upcoming event calendar |

### Layer 2: SignalAggregatorAgent Fusion

```python
# core/scoring.py — calculate_consensus_verdict()

def calculate_consensus_verdict(
    tech_score: float,       # -1 to +1
    news_sentiment: float,   # -1 to +1
    social_sentiment: float, # -1 to +1
    vol_ratio: float,        # e.g. 1.5 = 50% above average
) -> dict:
    
    # Weighted blend
    base_score = (
        tech_score * 0.40 +
        news_sentiment * 0.35 +
        social_sentiment * 0.15 +
        (vol_ratio - 1.0) * 0.10  # Volume contribution
    )
    
    # Conviction multiplier for high volume
    if vol_ratio > 1.5:
        base_score *= 1.2
    
    direction = "BUY" if base_score > 0.15 else "SELL" if base_score < -0.15 else "HOLD"
    is_strong = abs(base_score) > 0.45
    
    return {
        "score": round(base_score, 3),
        "direction": direction,
        "is_strong": is_strong,
    }
```

### Layer 3: Confidence Calibration

```python
# core/scoring.py — calibrate_confidence()

def calibrate_confidence(
    base_score: float,        # from consensus_verdict
    data_points: int,         # number of OHLCV bars
    headline_count: int,      # number of news articles
    agreement_factor: float,  # 1.1 if agents agree
) -> float:
    
    # Data quality multiplier
    data_quality = min(1.0, data_points / 100)  # Full confidence at 100+ bars
    
    # News freshness multiplier
    news_quality = min(1.0, headline_count / 10)
    
    # Base confidence from score magnitude
    score_conf = min(0.95, abs(base_score) * 1.5 + 0.3)
    
    # Final confidence
    conf = score_conf * data_quality * 0.5 + news_quality * 0.3 + 0.2
    conf *= agreement_factor
    
    return round(max(0.1, min(0.95, conf * 100)), 1)  # Returns 0-100 scale
```

### Layer 4: CritiqueAgent Adjustments

The CritiqueAgent detects contradictions and applies penalties:

| Contradiction | Confidence Penalty |
|--------------|-------------------|
| Technical BULLISH + Risk EXTREME | × 0.7 |
| Technical BULLISH + Macro BEARISH | × 0.8 |
| All specialists LOW confidence | × 0.5 |
| Cross-market divergence detected | × 0.8 |

```python
# Agreement score formula (from critique_layer.py)
signals = [tech_signal, macro_signal, risk_signal]  # mapped to -1, 0, +1
agreement_score = 1.0 - (max(signals) - min(signals)) / 2.0
# Perfect agreement = 1.0, total disagreement = 0.0
```

### Layer 5: RiskManager Final Gate

Before any trade gets approved:

```python
# Conviction-based position sizing
if confidence >= 80:   multiplier = 1.0  # Full position
elif confidence >= 65: multiplier = 0.6  # 60% position  
elif confidence >= 50: multiplier = 0.3  # 30% position
else:                  multiplier = 0.0  # BLOCK

suggested_size = portfolio_balance * MAX_POSITION_PCT * multiplier
```

---

## Vibe Extensions (DEEP / INSTITUTIONAL modes)

### Quantic (SMC + Monte Carlo)
Applied in DEEP and INSTITUTIONAL research modes:
- Smart Money Concepts: order blocks, fair value gaps, liquidity pools
- Monte Carlo: expected return distribution, Sharpe, VaR(95%), CVaR
- Bootstrap: statistical significance test, p-value < 0.05 = signal valid

If Quantic SMC signal DISAGREES with consensus: confidence × 0.6
If Quantic SMC signal AGREES with consensus: confidence += smart_money_score × 0.2

### Swarm Intelligence (INSTITUTIONAL mode only)
- 29 team presets (investment-committee, crypto-trading-desk, etc.)
- Confidence blend: `final_conf = base_conf × 0.7 + swarm_conf × 0.3`
- Cross-market sanity check: if divergence detected → confidence × 0.8

---

## Research Mode Decision Tree

```
User Query
    ↓
QueryRouter.observe() → classify intent
    ↓
research_mode = "QUICK" | "DEEP" | "INSTITUTIONAL"
    ↓
QUICK:  Wave 1 only + fast LLM synthesis (< 5s)
DEEP:   Wave 1 + Wave 2 + Quantic + Signal Aggregation (10-30s)
INSTITUTIONAL: All waves + Swarm + Cross-market + Full pipeline (30-120s)
```

---

## Adding a New Signal Source

### Step 1: Create specialist agent
```python
class MyNewSpecialist(_SpecialistBase):
    async def act(self, context):
        # Compute your signal
        context.result = {
            "signal": "BULLISH",
            "confidence": 0.72,
            "summary": "...",
            "score": 0.45,  # -1 to +1 normalized
            "my_metric": value
        }
        return context
```

### Step 2: Add to orchestrator Wave 1 or Wave 2
```python
# agents/orchestrator.py
self.my_specialist = MyNewSpecialist()

# In _run_first_wave() or _run_second_wave():
results = await asyncio.gather(
    self.technical.run(ctx),
    self.my_specialist.run(ctx),  # ADD
    ...
)
outputs["my_specialist"] = results[N].result
```

### Step 3: Feed into SignalAggregatorAgent
```python
# agents/signal_aggregator.py act():
my_score = spec_outputs.get("my_specialist", {}).get("score", 0.0)

# Add to the consensus formula
base_score = (
    tech_score * 0.35 +
    news_sentiment * 0.30 +
    my_score * 0.20 +       # NEW SOURCE
    social_sentiment * 0.10 +
    (vol_ratio - 1.0) * 0.05
)
```

---

## Prediction Storage & Accuracy Tracking

Every final signal should be stored for later accuracy evaluation:

```python
# Store prediction when signal is generated
pred_id = await memory_manager.store_prediction(
    ticker=ticker,
    prediction={
        "final_decision": verdict,        # BUY/SELL/HOLD
        "confidence": confidence,
        "current_price": current_price,
        "target_price": target_price,
        "expected_move_percent": 3.0,     # Expected % move
    },
    reasoning=response_text,
    confidence=confidence / 100.0
)

# Accuracy is scored 24h+ later by SelfImprovementEngine:
# accuracy = (actual_price - predicted_price) / (target_price - predicted_price)
# Clamped 0.0 to 1.0
```

---

## Backtesting Integration

Using BacktestAgent with Backtrader:

```python
# Deployment criteria (BacktestAgent constants):
MIN_SHARPE = 1.0          # Must exceed 1.0 Sharpe ratio
MAX_DRAWDOWN = 20.0       # Max 20% drawdown allowed
MIN_WIN_RATE = 0.52       # Must win > 52% of trades

# Signal format for backtesting:
signals = [
    {"date": "2024-01-15", "action": "BUY", "confidence": 0.78},
    {"date": "2024-02-03", "action": "SELL", "confidence": 0.65},
]

# BacktestAgent uses AXIOMReplayStrategy (Backtrader)
# Returns: total_return_pct, sharpe_ratio, max_drawdown_pct, win_rate
# Recommendation: DEPLOY | REFINE | REJECT
```
