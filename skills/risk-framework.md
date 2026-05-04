# Risk Framework Reference

## RiskManagerAgent Decision Tree

```
Priority 1: Max Open Positions (≥ MAX_OPEN_POSITIONS → BLOCK)
    ↓
Priority 2: Daily Loss Limit (≤ -MAX_DAILY_LOSS_PCT → BLOCK)
    ↓
Priority 3: Force Close (position loss > FORCE_CLOSE_LOSS_PCT → FORCE_CLOSE)
    ↓
Priority 4: Cash Reserve (cash < BALANCE_RESERVE_PCT × total → BLOCK)
    ↓
Priority 5: Leverage Cap (cap at MAX_LEVERAGE)
    ↓
Priority 6: Confidence Gating (get_recommendation() → HOLD if low)
    ↓
Priority 7: Volatility Regime Adjustment (reduce size in HIGH/CRISIS)
    ↓
Priority 8: Kelly + Conviction Sizing → APPROVE with position size
```

## Settings Reference

| Setting | Paper | Live | Description |
|---------|-------|------|-------------|
| MAX_POSITION_PCT | 0.10 | 0.05 | Max position as % of portfolio |
| MAX_DAILY_LOSS_PCT | 0.05 | 0.02 | Daily loss circuit breaker |
| MAX_OPEN_POSITIONS | 5 | 3 | Maximum concurrent positions |
| MAX_LEVERAGE | 3 | 2 | Leverage cap |
| BALANCE_RESERVE_PCT | 0.20 | 0.30 | Cash reserve floor |
| FORCE_CLOSE_LOSS_PCT | 0.10 | 0.05 | Position force-close threshold |
| MANDATORY_STOP_LOSS_PCT | 0.05 | 0.03 | Percentage stop if no ATR |

## Position Sizing Models

### 1. Kelly Criterion (Primary)
```python
calculate_kelly_size(win_rate, avg_win, avg_loss, max_position_pct, safety_factor=0.5)
```
- Formula: `K = W - (1-W)/R` where W = win_rate, R = avg_win/avg_loss
- Applied: Half-Kelly (× 0.5 safety factor)
- Hard cap: MAX_POSITION_PCT
- Minimum: 3% of max when insufficient data

### 2. Conviction-Based Multiplier
```python
get_sizing_multiplier(confidence)
```
| Confidence | Multiplier | Position |
|-----------|------------|----------|
| >= 80 | 1.0 | Full position |
| >= 65 | 0.6 | 60% position |
| >= 50 | 0.3 | 30% position |
| < 50 | 0.0 | BLOCKED |

### 3. Regime-Adjusted Final Size
```
effective_pct = min(kelly, max_position × conviction) × regime_multiplier
suggested_size = total_balance × effective_pct
```

## Volatility Regime Classification

```python
classify_volatility_regime(annualized_vol)
```

| Ann. Vol | Regime | Risk Multiplier | Action |
|----------|--------|----------------|--------|
| > 0.40 | CRISIS | 0.25× | Almost stop trading |
| > 0.25 | HIGH | 0.50× | Reduce positions significantly |
| > 0.12 | NORMAL | 1.00× | Standard sizing |
| ≤ 0.12 | LOW | 1.20× | Can increase size slightly |

### 6-Regime Detector (agents/regime_detector.py)
| Regime | Description | Risk Mult | Strategy |
|--------|-------------|-----------|----------|
| BULL_TRENDING | Low vol + rising | 1.20 | Trend following |
| BULL_VOLATILE | High vol + rising | 0.70 | Momentum |
| BEAR_TRENDING | High vol + falling | 0.40 | Defensive |
| BEAR_QUIET | Low vol + falling | 0.60 | Mean reversion |
| RANGE_BOUND | Low vol + sideways | 0.90 | Mean reversion |
| CRISIS | Extreme vol | 0.20 | Cash preservation |

## ATR-Based Stop-Loss and Take-Profit

```python
calculate_stop_target(entry_price, atr, direction, stop_mult=2.0, target_mult=3.0)
```

- **Stop**: Entry ± (ATR × 2.0)
- **Target**: Entry ± (ATR × 3.0)
- **R:R ratio**: target_mult / stop_mult = 1.5:1
- **Mandatory**: Every APPROVE decision MUST include stop_loss and take_profit

## Circuit Breaker System

### Daily Loss Circuit Breaker
- Triggered when `daily_pnl_pct <= -MAX_DAILY_LOSS_PCT`
- Action: BLOCK all new trades for the day
- Reset: Next trading day

### Force Close Mechanism
- Triggered when `unrealized_pnl_pct <= -FORCE_CLOSE_LOSS_PCT`
- Action: FORCE_CLOSE the position immediately
- Priority: Higher than new trade evaluation

### Balance Reserve Protection
- Triggered when `available_cash < BALANCE_RESERVE_PCT × total_value`
- Action: BLOCK new trades until cash replenished

## Risk Scoring

The `risk_score` returned by RiskManagerAgent (0.0 to 1.0, higher = more risky):
```python
calculate_risk_score(confidence, has_errors=False)
# Approved: 0.2 + (1.0 - confidence/100) × 0.5
# Blocked/Error: 0.8 to 1.0
```

## Confidence Gating Rules

- **EXTREME risk** → always HOLD
- **confidence < 50** → always HOLD (never trade doubt)
- **HIGH risk + confidence < 70** → HOLD
- **confidence >= 65** → allow BUY/SELL
- **confidence >= 80** → allow STRONG BUY/STRONG SELL
