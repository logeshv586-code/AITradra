# Trading Strategies Reference

## Implemented Strategies

### 1. Consensus Multi-Agent (Primary Strategy)
- **File**: `agents/orchestrator.py` + `agents/signal_aggregator.py`
- **Type**: Multi-factor ensemble
- **Logic**: 14 agents vote; weighted consensus > threshold = trade
- **Entry**: When `verdict = BUY/SELL` AND `confidence >= MIN_SIGNAL_CONFIDENCE`
- **Exit**: When opposing signal OR stop-loss hit

### 2. Technical Momentum
- **File**: `agents/specialist_agents.py` → `TechnicalSpecialist`
- **Type**: Technical trend-following
- **Long signals**: SMA20 > SMA50 + RSI 40-65 + MACD bullish cross + Volume surge
- **Short signals**: SMA20 < SMA50 + RSI > 70 or < 30 + MACD bearish cross

### 3. News Catalyst
- **File**: `agents/move_explainer.py` + `agents/mcp_news_agent.py`
- **Type**: Event-driven
- **Logic**: Significant price move + news catalyst identified → trade in direction
- **Threshold**: `MOVE_THRESHOLD = 0.8%` per bar triggers explanation

### 4. Earnings Surprise Play
- **File**: `agents/legacy/earnings_agent/agent.py`
- **Signals**:
  - `LONG_BEFORE_EARNINGS`: beat_rate > 70% + avg_surprise > 2%
  - `CONTRARIAN_LONG`: pre-earnings drop > 3% (buy the dip)
  - `AVOID_OR_SHORT`: beat_rate < 40%

### 5. Options Flow Signal
- **File**: `agents/legacy/options_flow_agent/agent.py`
- **Logic**: Unusual call/put volume (> 5× open interest) → direction signal
- **PCR Signal**: put/call ratio > 1.2 = BEARISH, < 0.7 = BULLISH
- **Max Pain**: Price tends toward max pain at expiry

### 6. Arbitrage Detection
- **File**: `agents/legacy/arbitrage_agent/agent.py`
- **Type**: Cross-exchange crypto arbitrage
- **Logic**: Price spread > 0.3% across Binance/Bybit/OKX
- **Note**: Signal only — does not account for fees or withdrawal delays

### 7. Market Regime Adaptive
- **File**: `agents/legacy/regime_detector_agent/agent.py`
- **Logic**: HMM-based regime classification → adjust position sizing
- **Regimes**:
  - CRISIS (VIX > 35%): risk_multiplier = 0.25 (25% normal size)
  - HIGH_VOLATILITY (VIX > 22%): risk_multiplier = 0.5
  - LATE_CYCLE (inverted curve): risk_multiplier = 0.6
  - EXPANSIONARY (VIX < 15%): risk_multiplier = 1.2
  - STRONG_UPTREND (ADX > 25 + positive): risk_multiplier = 1.2

### 8. Kelly Criterion Position Sizing
- **File**: `agents/legacy/portfolio_agent/agent.py`
- **Formula**: `K = W - (1-W)/R` where W = win rate, R = win/loss ratio
- **Applied**: Half-Kelly (0.5× safety factor)
- **Hard cap**: MAX_POSITION_PCT from settings
- **Min**: 1% if any positive signal

### 9. Smart Money Concepts (SMC)
- **File**: `agents/quantic_agent.py` (via Vibe Trading AI)
- **Signals**: Institutional order blocks, fair value gaps, liquidity pools
- **Usage**: DEEP and INSTITUTIONAL research modes only
- **Validation**: Bootstrap p-value < 0.05 = statistically significant signal

### 10. Deep Research Suggestions (85% Threshold)
- **File**: `agents/research_engine.py` → `DeepResearchAgent`
- **Logic**: Must have ≥3 specialist agents agree AND weighted score ≥ 0.80
- **Output**: `STRONG BUY` (>0.9) or `BUY` (≥0.80)
- **Stored**: `research_suggestions` table

---

## Adding a New Strategy

### Template for a new momentum strategy:
```python
class BreakoutMomentumAgent(BaseAgent):
    """Detects price breakouts above/below key levels."""
    
    BREAKOUT_THRESHOLD = 0.02  # 2% above resistance = signal
    VOLUME_CONFIRM = 1.5       # Must have 50% above avg volume
    
    async def act(self, context: AgentContext) -> AgentContext:
        ohlcv = context.metadata.get("ohlcv_data", [])
        
        if len(ohlcv) < 20:
            context.result = {"signal": "NEUTRAL", "confidence": 0.2}
            return context
        
        closes = [b['close'] for b in ohlcv]
        volumes = [b['volume'] for b in ohlcv]
        
        # Find resistance (recent 20-bar high excluding last 3)
        resistance = max(closes[3:23])
        support = min(closes[3:23])
        current = closes[0]
        avg_vol = sum(volumes[1:21]) / 20
        vol_confirmed = volumes[0] > avg_vol * self.VOLUME_CONFIRM
        
        if current > resistance * (1 + self.BREAKOUT_THRESHOLD) and vol_confirmed:
            signal = "BULLISH"
            confidence = 0.75
            score = 0.6
        elif current < support * (1 - self.BREAKOUT_THRESHOLD) and vol_confirmed:
            signal = "BEARISH"
            confidence = 0.75
            score = -0.6
        else:
            signal = "NEUTRAL"
            confidence = 0.3
            score = 0.0
        
        context.result = {
            "signal": signal,
            "confidence": confidence,
            "score": score,
            "summary": f"Breakout {'confirmed' if signal != 'NEUTRAL' else 'not detected'}. "
                       f"Current: {current:.2f}, Resistance: {resistance:.2f}, Support: {support:.2f}",
            "key_levels": {"resistance": resistance, "support": support}
        }
        return context
```

---

## Strategy Performance Targets

From `autoresearch/GOAL.md`:
- **Target accuracy**: ≥ 0.75 (75% directional accuracy)
- **Evaluation**: `python scripts/eval_predictions.py`
- **Stop condition**: 20 iterations without improvement
- **Primary model**: `NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf`
- **Target files for AI self-improvement**:
  - `agents/specialist_agents.py`
  - `gateway/llm_prompts.py`
  - `agents/orchestrator.py`

---

## Strategy Backtesting

```python
from agents.legacy.backtest_agent.agent import BacktestAgent
from agents.base_agent import AgentContext

# Prepare signals (generated by your strategy)
signals = [
    {"date": "2024-01-15", "action": "BUY", "confidence": 0.78},
    {"date": "2024-02-20", "action": "SELL", "confidence": 0.71},
]

agent = BacktestAgent()
ctx = AgentContext(
    task="Backtest my strategy",
    ticker="AAPL",
    observations={
        "signals": signals,
        "period_days": 365,
    }
)
result = await agent.run(ctx)

# Check results
print(result.result)
# {
#   "total_return_pct": 18.5,
#   "sharpe_ratio": 1.34,
#   "max_drawdown_pct": 12.1,
#   "win_rate": 0.61,
#   "recommendation": "DEPLOY"  # or REFINE or REJECT
# }
```

**Deployment criteria:**
- Sharpe > 1.0 AND total_return > 10% AND drawdown < 20% → DEPLOY
- Return > 0% AND Sharpe > 0.5 → REFINE
- Otherwise → REJECT

---

## Pine Script / Code Generation

```python
from agents.strategy_generator_agent import strategy_generator_agent

result = await strategy_generator_agent.generate(
    description="EMA crossover with RSI filter — long when EMA9 > EMA21 and RSI < 70",
    language="pine",    # pine | mql5 | python | quantconnect
    market="stocks"     # crypto | stocks | forex | futures
)

print(result.code)   # Generated Pine Script
```

---

## Watchlist Management

```python
# Dynamic watchlist from environment variable
import os
from agents.collector_agent import get_watchlist

watchlist = get_watchlist()
# Falls back to settings.DEFAULT_WATCHLIST if WATCHLIST env not set

# Add to watchlist via env:
# WATCHLIST=AAPL,TSLA,BTC-USD,ETH-USD,NVDA

# Settings default watchlist (core/config.py):
# AAPL, TSLA, MSFT, NVDA, META, AMZN, GOOGL, NFLX + crypto majors
```
