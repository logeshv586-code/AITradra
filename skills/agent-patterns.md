# Agent Patterns Reference

## Complete Agent Template

```python
"""
AgentName — One line description of what this agent does.
Part of the AXIOM trading intelligence platform.
"""
from agents.base_agent import BaseAgent, AgentContext
from core.logger import get_logger

logger = get_logger(__name__)


class MyTradingAgent(BaseAgent):
    """
    Agent N: [Name]
    Role: [Technical|Risk|Macro|Sentiment|Data|Execution]
    Wave: [1=parallel with others | 2=uses wave 1 outputs | 3=decision layer]
    """

    def __init__(self, memory=None, improvement_engine=None):
        super().__init__(
            name="MyTradingAgent",
            memory=memory,
            improvement_engine=improvement_engine,
            timeout_seconds=60,  # act() gets 3x this = 180s
        )
        # Pre-load constants, not data
        self.system_prompt = """You are a [Role] Specialist Agent.
Return ONLY valid JSON matching the required schema."""

    async def observe(self, context: AgentContext) -> AgentContext:
        """Load inputs. Check memory. Set observations."""
        # 1. Get cross-agent insights from other specialists
        if context.ticker:
            other_insights = await self._get_cross_agent_insights(
                context.ticker, hours=24
            )
            if other_insights:
                context.observations["other_insights"] = other_insights
                self._add_thought(context,
                    f"Found {len(other_insights)} insights from peer agents")

        # 2. Pull needed data into observations
        context.observations["has_data"] = bool(context.metadata.get("ohlcv_data"))
        self._add_thought(context, f"Observing {context.ticker} — data ready: {context.observations['has_data']}")
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        """Form hypothesis. Log reasoning steps."""
        self._add_thought(context, "Analyzing [domain] signals for entry/exit decision")
        self._add_thought(context, "Key factors: [list the market indicators this agent cares about]")
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        """Define execution steps."""
        context.plan = [
            "1. Extract relevant features from OHLCV/news/metadata",
            "2. Call LLM for structured analysis",
            "3. Fallback to algorithmic computation if LLM fails",
            "4. Store insight in KnowledgeStore",
        ]
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        """Execute analysis. Always set context.result."""
        ticker = context.ticker
        meta = context.metadata

        # Build insight context from peer agents
        insight_context = self._build_insight_context(
            context.observations.get("other_insights", [])
        )

        # LLM Analysis
        from llm.client import get_shared_llm
        llm = get_shared_llm()

        prompt = f"""TICKER: {ticker}
DATA: {str(meta.get('relevant_data', {}))[:800]}
{insight_context}

Analyze and return ONLY valid JSON:
{{
  "signal": "BULLISH|BEARISH|NEUTRAL",
  "confidence": 0.0,
  "summary": "...",
  "score": 0.0,
  "key_factors": ["factor1", "factor2"]
}}"""

        try:
            res = await llm.complete(
                prompt=prompt,
                system=self.system_prompt,
                expect_json=True,
                temperature=0.1,
                role="analysis"
            )
            if isinstance(res, dict) and "signal" in res:
                context.result = res
            else:
                context.result = self._algorithmic_fallback(meta)
        except Exception as e:
            context.errors.append(f"LLM failed: {e}")
            context.result = self._algorithmic_fallback(meta)

        # Store insight for cross-agent memory
        try:
            from gateway.knowledge_store import knowledge_store
            if ticker and context.result:
                knowledge_store.store_insight(
                    ticker=ticker,
                    agent_name=self.name,
                    insight_type="technical",  # Change to your domain
                    content=str(context.result.get("summary", "")),
                    confidence=context.result.get("confidence", 0.5)
                )
        except Exception:
            pass  # Non-fatal

        context.actions_taken.append({"action": "my_analysis_complete"})
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        """Set confidence and reflection. Be honest about data quality."""
        result = context.result or {}
        signal = result.get("signal", "NEUTRAL")
        conf = result.get("confidence", 0.5)

        if conf > 0.7 and not context.errors:
            context.reflection = f"High-conviction {signal} signal for {context.ticker}."
            context.confidence = conf
        elif context.errors:
            context.reflection = f"Analysis completed with {len(context.errors)} error(s). Signal degraded."
            context.confidence = max(0.2, conf * 0.6)
        else:
            context.reflection = f"{signal} signal with moderate confidence."
            context.confidence = conf
        return context

    def _build_insight_context(self, insights: list) -> str:
        """Format cross-agent insights for LLM prompt."""
        if not insights:
            return ""
        lines = ["\nInsights from peer agents:"]
        for i in insights[:5]:
            lines.append(f"- {i['agent_name']} ({i['insight_type']}): {i['content'][:150]}")
        return "\n".join(lines)

    def _algorithmic_fallback(self, meta: dict) -> dict:
        """Pure data-driven result when LLM is unavailable."""
        # Implement deterministic logic here
        return {
            "signal": "NEUTRAL",
            "confidence": 0.35,
            "summary": "Algorithmic fallback — LLM unavailable",
            "score": 0.0,
            "key_factors": ["Insufficient data"]
        }
```

---

## Specialist Patterns by Domain

### Technical Analysis Agent
Key indicators to compute (use `pandas_ta`):
- RSI(14): < 30 = oversold (bullish), > 70 = overbought (bearish)
- MACD(12,26,9): histogram crossing zero = signal
- SMA20/SMA50 crossover: golden/death cross
- Bollinger Bands: price relative to bands
- ADX(14): > 25 = trending, < 20 = ranging
- Volume ratio: current / 20-day avg > 1.5 = significant

```python
import pandas as pd
import pandas_ta as ta

df = pd.DataFrame(ohlcv_bars)  # needs Open/High/Low/Close/Volume cols
df.ta.rsi(length=14, append=True)
df.ta.macd(fast=12, slow=26, signal=9, append=True)
df.ta.bbands(length=20, std=2, append=True)
df.ta.adx(length=14, append=True)

latest = df.iloc[-1]
rsi = latest.get("RSI_14", 50)
macd_hist = latest.get("MACDh_12_26_9", 0)
```

### Risk Analysis Agent
Key risk metrics:
- VaR(95%) = 1.65 × daily_std_dev
- Max Drawdown = (peak - trough) / peak × 100
- Beta = correlation with SPY / SPY variance
- Sharpe = (annualized_return - 0.04) / annualized_vol
- Kelly Fraction = win_rate - (1 - win_rate) / win_loss_ratio

```python
import numpy as np

closes = [bar['close'] for bar in ohlcv_bars]
returns = np.diff(closes) / closes[:-1]

var_95 = abs(np.percentile(returns, 5)) * 100
daily_vol = np.std(returns)
ann_vol = daily_vol * np.sqrt(252)
max_dd = max((max(closes[:i+1]) - closes[i]) / max(closes[:i+1]) 
             for i in range(len(closes))) * 100
```

### Sentiment Analysis Agent
Sentiment signal construction:
- BULLISH keywords: surge, beat, record, upgrade, growth, rally, buy
- BEARISH keywords: crash, miss, decline, downgrade, cut, risk, sell
- Score = (bullish_count - bearish_count) / total_keywords
- Threshold: > 0.2 = BULLISH, < -0.2 = BEARISH

### Macro Analysis Agent
Key macro signals (from FRED CSV endpoints):
- VIX > 30 = CRISIS, > 22 = HIGH_VOL, < 15 = EXPANSIONARY
- Yield curve spread (10Y - 2Y) < 0 = INVERTED (recession risk)
- Unemployment 3-month trend: rising = BEARISH
- CPI momentum: accelerating = BEARISH for equities

---

## MCP Integration Pattern

All MCP agents follow this pattern:

```python
# mcp/my_mcp.py
class MyMCP:
    def __init__(self):
        logger.info("MyMCP initialized")

    async def get_data(self, ticker: str) -> dict:
        try:
            # Call external MCP server / API
            result = await external_call(ticker)
            return result
        except Exception as e:
            logger.error(f"MyMCP failed for {ticker}: {e}")
            return {}

_instance = None

def get_my_mcp():
    global _instance
    if _instance is None:
        _instance = MyMCP()
    return _instance
```

---

## Batch Agent Pattern

For nightly jobs that process the entire watchlist:

```python
async def run_nightly_batch(self):
    for symbol in self.watchlist:
        try:
            ctx = AgentContext(task=f"Process {symbol}", ticker=symbol)
            # 1. Collect fresh data
            data_ctx = await self.data_agent.run(ctx)
            # 2. Persist to blob storage
            await self.blob_agent.save_blob(symbol, data_ctx.result)
            # 3. Index for RAG
            await self.rag_agent.index_daily_snapshot(symbol, data_ctx.result)
        except Exception as e:
            logger.error(f"Batch failed for {symbol}: {e}")
    self.rag_agent.save_index()
```

---

## Error Handling Standards

```python
# CORRECT: append to errors, use fallback
try:
    result = await risky_call()
    context.result = result
except Exception as e:
    context.errors.append(f"MyAgent failed: {str(e)}")
    context.result = self._safe_fallback()
    # DO NOT raise — let the loop continue

# CORRECT: reflect on errors honestly
async def reflect(self, context):
    if context.errors:
        context.confidence = 0.25  # Degraded confidence
        context.reflection = f"Completed with {len(context.errors)} error(s)"
    else:
        context.confidence = 0.85
        context.reflection = "Clean analysis complete"
    return context

# WRONG: raising exceptions
async def act(self, context):
    result = await risky_call()  # Can crash the whole orchestrator
    raise ValueError("something")  # NEVER do this
```

---

## Agent Registration in MythicOrchestrator

```python
# agents/orchestrator.py

# Wave 1 (parallel, no dependencies):
results = await asyncio.gather(
    self.technical.run(ctx),
    self.macro.run(ctx),
    self.fundamental.run(ctx),
    self.my_new_agent.run(ctx),   # ADD HERE
    return_exceptions=True,
)

# Wave 2 (sequential, uses wave 1 outputs):
results = await asyncio.gather(
    self.risk.run(ctx),
    self.sentiment.run(ctx),
    self.my_knowledge_dependent_agent.run(ctx),  # ADD HERE
    return_exceptions=True,
)

# Wave 3 (decision layer):
agg_res = await self.signal_aggregator.run(decision_ctx)
risk_res = await self.risk_manager.run(decision_ctx)
```
