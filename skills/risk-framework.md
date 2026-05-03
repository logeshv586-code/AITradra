# Risk Framework Reference

## RiskManagerAgent Decision Tree

```
Input: ticker + portfolio state + signal from aggregator
        ↓
1. CHECK: open_positions >= MAX_OPEN_POSITIONS?
   YES → BLOCK ("Max positions reached")
        ↓
2. CHECK: daily_pnl_pct <= -MAX_DAILY_LOSS_PCT?
   YES → BLOCK ("Daily loss limit exceeded")
        ↓
3. CHECK: any position unrealized_pnl_pct <= -FORCE_CLOSE_LOSS_PCT?
   YES → FORCE_CLOSE (that position)
        ↓
4. CHECK: available_cash < total_balance * BALANCE_RESERVE_PCT?
   YES → BLOCK ("Below cash reserve")
        ↓
5. CAP leverage to MAX_LEVERAGE if exceeded
        ↓
6. READ signal aggregator verdict + confidence
   - Get direction (BUY/SELL/HOLD) and confidence (0-100)
   - Calculate risk_level from historical volatility
        ↓
7. CALCULATE sizing multiplier:
   confidence >= 80 → 1.0 (full size)
   confidence >= 65 → 0.6
   confidence >= 50 → 0.3
   confidence < 50  → 0.0 → BLOCK
        ↓
8. APPROVE with suggested_position_size = balance * MAX_POSITION_PCT * multiplier
```

## Settings Reference

```python
# core/config.py — these are the critical risk settings:

MAX_POSITION_PCT = 0.10       # Max 10% of portfolio per trade
MAX_DAILY_LOSS_PCT = 0.05     # Stop trading after 5% daily loss
MAX_OPEN_POSITIONS = 5        # Max 5 concurrent positions
FORCE_CLOSE_LOSS_PCT = 0.15   # Force close at 15% unrealized loss
BALANCE_RESERVE_PCT = 0.20    # Keep 20% cash always
MAX_LEVERAGE = 10             # Hard leverage cap
MIN_SIGNAL_CONFIDENCE = 60    # Minimum confidence to generate signal
MIN_CONSENSUS_AGENTS = 3      # Minimum agents that must agree
PAPER_TRADE_MODE = True       # DEFAULT: paper trading (no real orders)
PREDICTION_SCORE_DELAY_HOURS = 24  # Wait 24h before scoring predictions
```

---

## Position Sizing Models

### 1. Conviction-Based (Default, RiskManagerAgent)
```python
multiplier = {
    confidence >= 80: 1.0,
    confidence >= 65: 0.6,
    confidence >= 50: 0.3,
    confidence < 50:  0.0  # No trade
}
base_size = portfolio_value * MAX_POSITION_PCT
position_size = base_size * multiplier
```

### 2. Kelly Criterion (PortfolioAgent)
```python
win_rate = wins / total_trades
win_loss_ratio = avg_win / avg_loss
kelly_raw = win_rate - (1 - win_rate) / win_loss_ratio
half_kelly = max(0.0, kelly_raw * 0.5)  # Safety: use half-Kelly

# Final: min of Kelly, risk-parity, and hard cap
risk_parity_size = target_risk (0.15) / annualized_volatility
final_size = min(half_kelly, risk_parity_size, MAX_POSITION_PCT)
```

### 3. Risk-Parity
```python
target_portfolio_risk = 0.15  # 15% annual portfolio volatility
asset_volatility = daily_std * sqrt(252)  # Annualized
position_size = target_portfolio_risk / asset_volatility
position_size = min(position_size, MAX_POSITION_PCT)
```

---

## VaR Calculation

```python
# Historical VaR (95% confidence)
closes = [bar['close'] for bar in ohlcv_data]
returns = np.diff(closes) / closes[:-1]
var_95 = abs(np.percentile(returns, 5)) * 100  # As percentage

# Parametric VaR (approximate)
daily_std = np.std(returns)
var_95_parametric = 1.65 * daily_std * 100  # 95% confidence

# CVaR (Conditional VaR / Expected Shortfall)
threshold = np.percentile(returns, 5)
cvar_95 = abs(np.mean(returns[returns <= threshold])) * 100
```

---

## Circuit Breaker System

### Daily Loss Circuit Breaker
```python
# Checked at start of each trade
daily_pnl_pct = (current_portfolio_value - day_start_value) / day_start_value
if daily_pnl_pct <= -MAX_DAILY_LOSS_PCT:
    return {"decision": "BLOCK", "reason": "Daily loss limit exceeded"}
```

### Force Close Mechanism
```python
# Checked for each open position
for position in open_positions:
    unrealized_pnl_pct = (current_price - entry_price) / entry_price
    if unrealized_pnl_pct <= -FORCE_CLOSE_LOSS_PCT:
        return {"decision": "FORCE_CLOSE", "ticker": position['ticker']}
```

### Balance Reserve Protection
```python
reserve_amount = total_balance * BALANCE_RESERVE_PCT
if available_cash < reserve_amount:
    return {"decision": "BLOCK", "reason": "Below cash reserve threshold"}
```

---

## Risk Scoring

The `risk_score` returned by RiskManagerAgent (0.0 to 1.0, higher = more risky):

```python
# Approved trades:
risk_score = 0.2 + (1.0 - confidence/100) * 0.5
# Example: 80% confidence → risk_score = 0.2 + 0.1 = 0.3 (low risk)
# Example: 50% confidence → risk_score = 0.2 + 0.25 = 0.45 (medium risk)

# Blocked trades: risk_score = 0.8 to 1.0
```

---

## Volatility Regime Classification

Used by TechnicalSpecialist and RegimeDetectorAgent:

```python
daily_vol = np.std(returns)
ann_vol = daily_vol * np.sqrt(252)

if ann_vol > 0.40:      regime = "CRISIS"
elif ann_vol > 0.25:    regime = "HIGH"
elif ann_vol > 0.12:    regime = "NORMAL"
else:                   regime = "LOW"

# Risk level → position sizing multiplier
risk_multipliers = {
    "CRISIS": 0.25,
    "HIGH": 0.5,
    "NORMAL": 1.0,
    "LOW": 1.2
}
```

---

## Stress Testing

StressScenarios added by RiskSpecialist:

```python
beta = position_beta  # e.g., 1.2 for high-beta stock

stress_scenarios = [
    {"scenario": "Market crash -20%", "impact_pct": round(-20 * beta, 1)},
    {"scenario": "Sector rotation -10%", "impact_pct": round(-10 * beta * 0.8, 1)},
    {"scenario": "Rate hike shock", "impact_pct": round(-5 * beta, 1)},
    {"scenario": "Black swan -35%", "impact_pct": round(-35 * beta, 1)},
]
```

---

## Hyperliquid-Specific Risk

For Hyperliquid perpetual futures:

```python
# Additional checks before Hyperliquid orders:
settings.HYPERLIQUID_PRIVATE_KEY    # Must be set for live trading
settings.HYPERLIQUID_VAULT_ADDRESS  # Optional vault address
settings.PAPER_TRADE_MODE = True    # Default OFF for safety

# Leverage handling:
if requested_leverage > settings.MAX_LEVERAGE:
    requested_leverage = settings.MAX_LEVERAGE  # Hard cap, never exceed

# Market order vs limit:
# MARKET: uses exchange.market_open(ticker, is_buy, qty, slippage)
# LIMIT: uses exchange.order(ticker, is_buy, qty, price, {"limit": {"tif": "Gtc"}})
```
