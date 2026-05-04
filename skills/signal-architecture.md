# Signal Architecture Reference

## Complete Signal Math

### Layer 1: Individual Specialist Scores
Each specialist MUST return a normalized score in the canonical schema:

```json
{
  "signal": "BULLISH|BEARISH|NEUTRAL",
  "confidence": 0.0-1.0,
  "score": -1.0 to +1.0,
  "summary": "One sentence",
  "key_factors": ["factor1", "factor2"]
}
```

| Specialist | Score Range | Key Computation |
|-----------|-------------|-----------------|
| TechnicalSpecialist | -1.0 to +1.0 | RSI(14) + MACD(12,26,9) + BB(20,2) + ADX(14) + SMA20/50 + Volume |
| RiskSpecialist | 0.0 to 1.0 (risk level) | VaR + Beta + Drawdown |
| MacroSpecialist | -1.0 to +1.0 | News sentiment + sector rotation |
| SentimentSpecialist | -1.0 to +1.0 | Headline keyword/LLM scoring |
| FundamentalSpecialist | -1.0 to +1.0 | P/E + valuation metrics |
| SectorSpecialist | -1.0 to +1.0 | Sector rotation signals |
| CatalystSpecialist | -1.0 to +1.0 | Event proximity scoring |
| BreakoutMomentumAgent | -1.0 to +1.0 | Donchian breakout + volume confirmation |
| RegimeDetectorAgent | -1.0 to +1.0 | Rolling volatility regime |

### Layer 2: SignalAggregatorAgent Fusion

**Canonical Formula** (from `core/scoring.py`):
```
Weighted Score = Tech × 0.40 + News × 0.35 + Social × 0.15 + Vol × 0.10
```

Where:
- **Tech** = TechnicalSpecialist.score (also includes BreakoutMomentumAgent blend)
- **News** = MacroSpecialist.score × 0.6 + FundamentalSpecialist.score × 0.4
- **Social** = SentimentSpecialist.score × 0.5 + CatalystSpecialist.score × 0.25 + SectorSpecialist.score × 0.25
- **Vol** = (current_volume / 20d_avg_volume) - 1.0, clamped to [-1, 1]

**Conviction Multiplier**: Score × 1.2 when volume ratio > 1.5

### Layer 3: Confidence Calibration

```python
calibrate_confidence(base_score, data_points, headline_count, agreement_factor)
```

Three pillars:
1. **Score magnitude** → base confidence (|score| × 1.5 + 0.3, capped at 0.95)
2. **Data quality** → multiplier (full at 100+ OHLCV bars)
3. **News freshness** → multiplier (full at 10+ articles)
4. **Agreement factor** → bonus (1.2× when all scores same sign + strong, 0.8× when disagreeing)

**Penalties**:
- < 5 bars → confidence capped at 40
- 0 headlines → confidence capped at 45

### Layer 4: Cross-Agent Validation

- **Quantic (SMC)**: If SMC signal diverges from consensus → confidence × 0.65
- **Swarm**: Blended into confidence (75% consensus + 25% swarm)
- **CritiqueAgent**: Flags contradictions between specialist signals

### Layer 5: Verdict with Confidence Gating

```python
get_recommendation(direction, confidence, risk_level)
```

| Condition | Verdict |
|-----------|---------|
| confidence >= 80 + BUY | **STRONG BUY** |
| confidence >= 65 + BUY | **BUY** |
| confidence >= 80 + SELL | **STRONG SELL** |
| confidence >= 65 + SELL | **SELL** |
| confidence < 50 | **HOLD** (never trade doubt) |
| risk_level == EXTREME | **HOLD** (always) |
| risk_level == HIGH + confidence < 70 | **HOLD** |

### Layer 6: Entry/Exit Levels

**ATR-Based Stop-Loss and Take-Profit** (from `core/scoring.py`):
```python
calculate_stop_target(entry_price, atr, direction, stop_mult=2.0, target_mult=3.0)
```
- Stop = Entry ± (ATR × 2.0)
- Target = Entry ± (ATR × 3.0)
- Default R:R ratio = 1.5:1

**Fallback** (when ATR unavailable):
- Stop = Entry × 0.95 (BUY) or Entry × 1.05 (SELL)
- Target = Entry × 1.10 (BUY) or Entry × 0.90 (SELL)

---

## Score Extraction

The `SignalAggregatorAgent` uses `_extract_score()` to normalize any specialist output:

```python
def _extract_score(output: dict) -> float:
    """Extract -1.0 to +1.0 score from specialist output."""
    if "score" in output:
        return clamp(output["score"], -1.0, 1.0)
    # Fallback: infer from signal + confidence
    if signal in ("BULLISH", "BUY"):
        return confidence * 0.8
    elif signal in ("BEARISH", "SELL"):
        return -confidence * 0.8
    return 0.0
```

This means ALL specialists MUST return the canonical schema for proper fusion.

---

## Skill-Enhanced Prompts

Every agent's LLM call uses `_build_skill_enhanced_prompt()` which:
1. Reads the agent's mapped skill files from `core/skill_manager.py`
2. Condenses them (headers + key terms: formula, weight, threshold, must, never)
3. Appends as `--- PLATFORM INTELLIGENCE RULES ---` to system prompt
4. LLM reads the rules before generating its analysis

---

## Prediction Storage for Self-Learning

Every directional signal is stored as a prediction:
```python
# Stored automatically by SelfImprovementEngine.process_agent_run()
knowledge_store.store_insight(
    ticker=ticker, agent_name=agent_name,
    insight_type="prediction",
    content=f"{signal} @ {price} | conf={confidence}",
    confidence=confidence,
)
```

After 24h+, predictions are scored against actual prices:
```
accuracy = calculate_accuracy(prediction_price, target_price, actual_price, direction)
accuracy_store.record_outcome(ticker, model=agent_name, provider, direction, accuracy)
```

Per-agent accuracy feeds back into weight adjustments (0.6× to 1.3× multiplier).
