# Trading Strategies Reference

## Implemented Strategies

### 1. Consensus Multi-Agent (Primary Strategy)
- **File**: `agents/orchestrator.py` + `agents/signal_aggregator.py`
- **Type**: Multi-factor ensemble
- **Logic**: 16 agents vote; weighted consensus > threshold = trade
- **Weights**: Tech×0.40 + News×0.35 + Social×0.15 + Vol×0.10
- **Entry**: When `verdict = BUY/SELL` AND `confidence >= 65`
- **Exit**: When opposing signal OR ATR-based stop-loss hit
- **Conviction Multiplier**: 1.2× when volume > 1.5× average

### 2. Technical Momentum
- **File**: `agents/specialist_agents.py` → `TechnicalSpecialist`
- **Type**: Technical trend-following with 6-indicator composite
- **Indicators**: RSI(14), MACD(12,26,9), Bollinger %B(20,2), ADX(14), SMA20/50, Volume Ratio
- **Composite Score**: Weighted blend normalized to -1.0 to +1.0
- **Long signals**: SMA20 > SMA50 + RSI 30-65 + MACD bullish + Volume surge
- **Short signals**: SMA20 < SMA50 + RSI > 70 + MACD bearish cross
- **Score Weights**: Trend(25%) + RSI(20%) + MACD(20%) + ADX(15%) + BB(10%) + Vol(10%)

### 3. Breakout Momentum
- **File**: `agents/breakout_agent.py` → `BreakoutMomentumAgent`
- **Type**: Donchian Channel breakout with volume confirmation
- **Wave**: 1 (parallel with Technical + Macro + Fundamental)
- **Logic**:
  - Donchian Channel (20-period high/low) defines breakout levels
  - Close must be BEYOND level (not just wick) → false breakout filter
  - Volume > 1.5× average confirms breakout
  - ATR range expansion > 1.2× confirms momentum
- **Scoring**:
  - Base score: ±0.4 for breakout
  - Volume confirmation: +0.25
  - Momentum expansion: +0.15
  - Proximity bonus: up to +0.2

### 4. News Catalyst
- **File**: `agents/move_explainer.py` + `agents/mcp_news_agent.py`
- **Type**: Event-driven
- **Logic**: Significant price move + news catalyst identified → trade in direction
- **Threshold**: `MOVE_THRESHOLD = 0.8%` per bar triggers explanation

### 5. Market Regime Adaptive
- **File**: `agents/regime_detector.py` → `RegimeDetectorAgent`
- **Type**: Rolling volatility regime classification
- **Wave**: 2 (uses Wave 1 insights)
- **Volatility Windows**: 10-day, 21-day, 63-day rolling
- **Regimes**:
  - BULL_TRENDING: Low vol + rising trend → risk_mult = 1.20
  - BULL_VOLATILE: High vol + rising → risk_mult = 0.70
  - BEAR_TRENDING: High vol + falling → risk_mult = 0.40
  - BEAR_QUIET: Low vol + falling → risk_mult = 0.60
  - RANGE_BOUND: Low vol + sideways → risk_mult = 0.90
  - CRISIS: Extreme vol → risk_mult = 0.20
- **Thresholds**: ann_vol > 0.40 = CRISIS, > 0.25 = HIGH, > 0.12 = NORMAL, else LOW

### 6. Kelly Criterion Position Sizing
- **File**: `core/scoring.py` + `agents/risk_manager.py`
- **Formula**: `K = W - (1-W)/R` where W = win rate, R = win/loss ratio
- **Applied**: Half-Kelly (0.5× safety factor)
- **Hard cap**: MAX_POSITION_PCT from settings
- **Final size**: `min(kelly, conviction) × regime_multiplier × balance`

### 7. Smart Money Concepts (SMC)
- **File**: `agents/quantic_agent.py` (via Vibe Trading AI)
- **Signals**: Institutional order blocks, fair value gaps, liquidity pools
- **Usage**: DEEP and INSTITUTIONAL research modes only
- **Validation**: Bootstrap p-value < 0.05 = statistically significant signal

### 8. Sentiment Analysis
- **File**: `agents/extended_specialists.py` → `SentimentSpecialist`
- **Type**: News headline sentiment scoring
- **LLM**: Uses sentiment role model with skill-enhanced prompts
- **Fallback**: Keyword-based scoring (bull/bear keyword matching)
- **Output**: Canonical {signal, confidence, score, summary, key_factors} schema

### 9. Fundamental Analysis
- **File**: `agents/extended_specialists.py` → `FundamentalSpecialist`
- **Type**: Valuation metrics (P/E, market cap)
- **LLM**: Uses analysis role model
- **Fallback**: P/E-based scoring (< 15 = bullish, > 35 = bearish)

### 10. Sector Rotation
- **File**: `agents/extended_specialists.py` → `SectorSpecialist`
- **Type**: Relative sector strength and rotation signals

### 11. Catalyst Event Detection
- **File**: `agents/extended_specialists.py` → `CatalystSpecialist`
- **Type**: Event proximity scoring (earnings, FDA, mergers, lawsuits)
- **Keywords**: earnings, fda, merger, acquisition, buyback, dividend, split, lawsuit, ipo

---

## Agent Pipeline Architecture

### Wave 1 (Parallel — No Dependencies)
```
TechnicalSpecialist  ──┐
MacroSpecialist      ──├─→ specialist_outputs
FundamentalSpecialist──┤
BreakoutMomentumAgent──┘
```

### Wave 2 (Uses Wave 1 Insights)
```
RiskSpecialist       ──┐
SentimentSpecialist  ──├─→ extended_outputs
SectorSpecialist     ──┤
CatalystSpecialist   ──┤
RegimeDetectorAgent  ──┘
```

### Wave 3 (Decision Layer)
```
All outputs ──→ SignalAggregatorAgent ──→ RiskManagerAgent ──→ Verdict
                     │                        │
                     └── CritiqueAgent ────────┘
```

---

## Adding a New Strategy

### Template:
```python
class MyStrategyAgent(BaseAgent):
    """New strategy agent following Claude Flow loop."""

    def __init__(self):
        super().__init__(name="MyStrategyAgent", timeout_seconds=30)

    async def observe(self, ctx): ...   # Load data + cross-agent insights
    async def think(self, ctx): ...     # Analyze
    async def plan(self, ctx): ...      # Steps
    async def act(self, ctx): ...       # Compute + LLM
    async def reflect(self, ctx): ...   # Store prediction

    # MUST return canonical schema:
    # {signal, confidence, score, summary, key_factors}
```

### Registration:
1. Add to `agents/orchestrator.py` → import + instantiate
2. Add to Wave 1 or Wave 2 gather
3. Add to `attach_improvement_engine()` list
4. Add to `core/skill_manager.py` → `AGENT_SKILL_MAP`
