# Stock Market Trading Agent — Complete Skills Inventory

> **Project**: Intelligent Multi-Agent Stock Market Trading System
> **Goal**: Build a fully autonomous, profit-generating trading agent ecosystem capable of analyzing, deciding, and executing trades across all market conditions and asset classes
> **Version**: 1.0
> **Date**: 2026-05-04

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Skill Category 1 — Market Data Acquisition](#2-skill-category-1--market-data-acquisition)
3. [Skill Category 2 — Technical Analysis](#3-skill-category-2--technical-analysis)
4. [Skill Category 3 — Fundamental Analysis](#4-skill-category-3--fundamental-analysis)
5. [Skill Category 4 — Sentiment & Alternative Data Analysis](#5-skill-category-4--sentiment--alternative-data-analysis)
6. [Skill Category 5 — Trading Strategy Engine](#6-skill-category-5--trading-strategy-engine)
7. [Skill Category 6 — Risk Management & Portfolio Protection](#7-skill-category-6--risk-management--portfolio-protection)
8. [Skill Category 7 — Order Execution & Smart Routing](#8-skill-category-7--order-execution--smart-routing)
9. [Skill Category 8 — AI & Machine Learning Models](#9-skill-category-8--ai--machine-learning-models)
10. [Skill Category 9 — Market Microstructure Analysis](#10-skill-category-9--market-microstructure-analysis)
11. [Skill Category 10 — Portfolio Management & Optimization](#11-skill-category-10--portfolio-management--optimization)
12. [Skill Category 11 — Backtesting & Simulation](#12-skill-category-11--backtesting--simulation)
13. [Skill Category 12 — News & Event Processing](#13-skill-category-12--news--event-processing)
14. [Skill Category 13 — Macro & Economic Analysis](#14-skill-category-13--macro--economic-analysis)
15. [Skill Category 14 — Options & Derivatives Trading](#15-skill-category-14--options--derivatives-trading)
16. [Skill Category 15 — Crypto & Digital Asset Trading](#16-skill-category-15--crypto--digital-asset-trading)
17. [Skill Category 16 — Compliance & Regulatory Monitoring](#17-skill-category-16--compliance--regulatory-monitoring)
18. [Skill Category 17 — Adaptive Learning & Regime Detection](#18-skill-category-17--adaptive-learning--regime-detection)
19. [Skill Category 18 — Multi-Agent Coordination & Orchestration](#19-skill-category-18--multi-agent-coordination--orchestration)
20. [Skill Category 19 — Performance Analytics & Reporting](#20-skill-category-19--performance-analytics--reporting)
21. [Skill Category 20 — Infrastructure & DevOps](#21-skill-category-20--infrastructure--devops)
22. [Agent Role Definitions](#22-agent-role-definitions)
23. [Skill Dependency Map](#23-skill-dependency-map)
24. [Implementation Priority Matrix](#24-implementation-priority-matrix)

---

## 1. Architecture Overview

The Intelligent Stock Market Trading System is built as a **multi-agent architecture** where each agent specializes in a specific domain of trading intelligence. These agents communicate through a central orchestration layer, share insights via a unified data bus, and collectively make trading decisions that are more accurate and profitable than any single-agent approach.

### Core Principles

- **Autonomy**: Each agent operates independently within its domain while contributing to collective intelligence
- **Real-time Processing**: All data pipelines and decision engines operate with sub-second latency
- **Adaptability**: Agents learn from market feedback and adjust strategies dynamically
- **Safety First**: Risk management agents have veto power over all trade decisions
- **Scalability**: The system handles thousands of instruments across multiple exchanges simultaneously

### Agent Communication Topology

```
┌─────────────────────────────────────────────────────────┐
│                   ORCHESTRATION LAYER                     │
│              (Central Decision Coordinator)                │
└──────┬──────┬──────┬──────┬──────┬──────┬──────┬────────┘
       │      │      │      │      │      │      │
  ┌────▼──┐┌──▼───┐┌─▼────┐┌▼─────┐┌▼─────┐┌▼──────┐┌──▼────┐
  │ Data  ││Tech  ││Funda ││Senti-││Risk  ││Execu- ││ML/AI  │
  │Agent  ││Agent ││Agent ││ment  ││Agent ││tion   ││Agent  │
  │       ││      ││      ││Agent ││      ││Agent  ││       │
  └───────┘└──────┘└──────┘└──────┘└──────┘└───────┘└───────┘
```

---

## 2. Skill Category 1 — Market Data Acquisition

### Skill 1.1: Real-Time Market Data Streaming

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `DATA-001` |
| **Description** | Ingest, parse, and distribute real-time market data feeds (Level 1 and Level 2) from multiple exchanges with sub-millisecond latency |
| **Input** | WebSocket/REST API connections to exchanges (NYSE, NASDAQ, BSE, NSE, LSE, etc.) |
| **Output** | Normalized tick data, quote updates, trade prints in unified schema |
| **Latency Target** | < 1ms from exchange to internal data bus |
| **Technologies** | WebSocket, FIX protocol, Apache Kafka, Redis Streams, Protocol Buffers |

**Key Capabilities:**
- Subscribe to and process real-time price ticks for 10,000+ instruments simultaneously
- Normalize data from different exchanges into a unified schema (price, volume, bid/ask, timestamp)
- Handle exchange-specific quirks (lot sizes, tick sizes, trading hours, halts)
- Detect and flag data anomalies (stale quotes, price jumps, missing ticks)
- Maintain local order book snapshots for Level 2 data

**Implementation Details:**
- Use connection pooling with automatic reconnection and failover
- Implement data buffering with configurable time windows for micro-batch processing
- Apply checksum validation on all incoming data packets
- Support both push (WebSocket) and pull (REST polling) modes with automatic switching
- Store raw and processed data in separate streams for audit trail

---

### Skill 1.2: Historical Data Management

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `DATA-002` |
| **Description** | Fetch, store, and serve historical market data (OHLCV, tick, order book snapshots) for backtesting and analysis |
| **Input** | Data vendor APIs, exchange archives, internal tick database |
| **Output** | Time-series data in multiple resolutions (tick, 1s, 1m, 5m, 15m, 1h, 4h, 1D, 1W, 1M) |
| **Storage** | TimescaleDB, Arctic, or ClickHouse for tick-level data; Parquet files for bulk archives |
| **Coverage** | 20+ years of daily data, 5+ years of intraday data, 1+ year of tick data |

**Key Capabilities:**
- Incremental data updates with gap detection and backfill automation
- Corporate action adjustment (splits, dividends, spin-offs, symbol changes)
- Multi-resolution aggregation on-the-fly (resample from tick to any OHLCV period)
- Data quality scoring with automated anomaly flagging
- Point-in-time accuracy ensuring no look-ahead bias in backtests

---

### Skill 1.3: Alternative Data Ingestion

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `DATA-003` |
| **Description** | Acquire and process non-traditional data sources that provide trading edge |
| **Input** | Satellite imagery, credit card transactions, web scraping, app usage, geolocation, social media |
| **Output** | Structured signals, sentiment scores, activity metrics, predictive features |
| **Processing** | NLP pipelines, computer vision models, geospatial analytics |

**Key Capabilities:**
- Satellite imagery processing for retail parking lot traffic, crop yields, oil storage levels
- Credit card transaction aggregation for consumer spending trends
- Web scraping for pricing data, job postings, product reviews
- App download and usage tracking for technology company metrics
- Shipping and logistics data for supply chain analysis
- Patent filings and regulatory submissions for competitive intelligence
- Weather data integration for commodity trading signals

---

### Skill 1.4: Options & Derivatives Data Processing

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `DATA-004` |
| **Description** | Acquire and process options chain data, futures curves, and derivatives pricing information |
| **Input** | Options chains, futures term structures, implied volatility surfaces, Greeks |
| **Output** | Normalized options data, volatility surfaces, term structure curves, Greeks snapshots |

**Key Capabilities:**
- Full options chain processing across all expirations and strikes
- Real-time implied volatility surface construction and arbitrage-free smoothing
- Greeks calculation (Delta, Gamma, Theta, Vega, Rho) using multiple models
- Put-call parity validation and arbitrage detection
- Open interest and volume analysis across strikes and expirations
- Futures curve analysis (contango, backwardation, roll yield)

---

## 3. Skill Category 2 — Technical Analysis

### Skill 2.1: Trend Indicators & Pattern Recognition

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `TECH-001` |
| **Description** | Compute and interpret trend-following indicators and chart patterns for directional bias |
| **Input** | OHLCV time-series data |
| **Output** | Trend signals (bullish/bearish/neutral), pattern alerts, confidence scores |
| **Timeframes** | Multi-timeframe analysis (1m to monthly) |

**Key Capabilities:**

- **Moving Averages**: SMA, EMA, WMA, VWMA, Hull MA, KAMA (Kaufman Adaptive), ALMA (Arnaud Legoux)
  - Crossover signals (Golden Cross, Death Cross, MACD crossovers)
  - Moving average ribbon analysis for trend strength
  - Adaptive moving average periods based on market volatility

- **Trend Indicators**: 
  - ADX/DMI (Average Directional Index) for trend strength quantification
  - Ichimoku Cloud (Tenkan, Kijun, Senkou A/B, Chikou) for multi-dimensional trend analysis
  - SuperTrend for dynamic support/resistance levels
  - Parabolic SAR for trailing stop and trend reversal detection
  - Linear Regression Channel for statistical trend boundaries
  - Donchian Channel for breakout detection

- **Chart Pattern Recognition** (AI-enhanced):
  - Reversal patterns: Head & Shoulders, Double/Triple Top/Bottom, Rounding Top/Bottom
  - Continuation patterns: Flags, Pennants, Triangles (ascending/descending/symmetrical), Wedges
  - Complex patterns: Harmonic patterns (Gartley, Bat, Butterfly, Crab), Wolfe Waves
  - Candlestick patterns: 30+ single and multi-candle patterns (Doji, Engulfing, Hammer, Morning/Evening Star, Three White Soldiers, etc.)

---

### Skill 2.2: Momentum & Oscillator Analysis

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `TECH-002` |
| **Description** | Measure momentum, identify overbought/oversold conditions, and detect divergences |
| **Input** | OHLCV data, indicator parameters |
| **Output** | Momentum signals, divergence alerts, overbought/oversold flags |

**Key Capabilities:**

- **Oscillators**:
  - RSI (Relative Strength Index) with adaptive periods and divergence detection
  - Stochastic Oscillator (%K, %D) with multi-timeframe alignment
  - CCI (Commodity Channel Index) for cyclical overbought/oversold
  - Williams %R for momentum extremes
  - ROC (Rate of Change) for absolute momentum measurement
  - Momentum (MOM) for raw price change tracking

- **Momentum Indicators**:
  - MACD (Moving Average Convergence Divergence) with histogram analysis
  - PPO (Percentage Price Oscillator) for cross-asset momentum comparison
  - TRIX for triple-smoothed momentum filtering
  - Awesome Oscillator for market acceleration/deceleration
  - Chande Momentum Oscillator for pure momentum measurement

- **Divergence Detection** (automated):
  - Regular bullish/bearish divergences (price vs indicator)
  - Hidden divergences for trend continuation signals
  - Multi-indicator divergence confirmation (RSI + MACD + Stochastic aligned)
  - Divergence strength scoring based on number of swing points and angle

---

### Skill 2.3: Volatility Analysis

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `TECH-003` |
| **Description** | Measure and forecast volatility for position sizing, stop placement, and options trading |
| **Input** | OHLCV data, options data, VIX index |
| **Output** | Volatility regime classification, volatility forecasts, Bollinger Band positions |

**Key Capabilities:**

- **Historical Volatility Metrics**:
  - Rolling standard deviation (realized volatility) at multiple lookback periods
  - Parkinson volatility (high-low range estimator)
  - Garman-Klass volatility (OHLC estimator)
  - Rogers-Satchell volatility (drift-independent estimator)
  - Yang-Zhang volatility (optimal OHLCV estimator)

- **Volatility Indicators**:
  - Bollinger Bands with %B and Bandwidth for squeeze detection
  - Keltner Channels for ATR-based volatility envelopes
  - Donchian Channels for range-based volatility
  - Average True Range (ATR) for adaptive stop-loss and position sizing
  - Chaikin Volatility for volatility expansion/contraction cycles
  - VIX correlation analysis for market-wide fear assessment

- **Volatility Regime Detection**:
  - Hidden Markov Model for regime classification (low/medium/high/extreme volatility)
  - GARCH(1,1) and EGARCH for volatility forecasting
  - Volatility clustering identification and mean-reversion signals
  - Implied vs. Realized volatility spread analysis for options strategies

---

### Skill 2.4: Volume & Market Breadth Analysis

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `TECH-004` |
| **Description** | Analyze volume patterns and market breadth to confirm price movements and identify distribution/accumulation |
| **Input** | OHLCV data, advance/decline data, sector rotation data |
| **Output** | Volume confirmation signals, breadth indicators, accumulation/distribution phases |

**Key Capabilities:**

- **Volume Indicators**:
  - OBV (On-Balance Volume) for volume trend confirmation
  - VWAP (Volume Weighted Average Price) with standard deviation bands for intraday institutional levels
  - Accumulation/Distribution Line for money flow tracking
  - Chaikin Money Flow (CMF) for buying/selling pressure
  - Money Flow Index (MFI) as volume-weighted RSI
  - Volume Profile (VPOC, Value Area, High/Low Volume Nodes)
  - Ease of Movement for price-volume relationship
  - Force Index for blending price and volume momentum

- **Market Breadth**:
  - Advance/Decline Line and Ratio for market participation
  - McClellan Oscillator and Summation Index for breadth momentum
  - Percentage of stocks above moving averages (50-day, 200-day)
  - New Highs/New Lows ratio for market health assessment
  - Tick and TRIN (Arms Index) for intraday sentiment
  - Sector rotation analysis using relative strength

- **Volume-Price Confirmation Engine**:
  - Automated divergence detection between price and volume trends
  - Volume breakout validation (price breakout on above-average volume = confirmed)
  - Climax volume detection for potential reversal signals
  - Institutional footprint analysis using volume cluster detection

---

### Skill 2.5: Support & Resistance Identification

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `TECH-005` |
| **Description** | Automatically identify key price levels where supply/demand imbalances exist |
| **Input** | OHLCV data, volume profile data, options chain data |
| **Output** | Support/resistance zones with strength scores, pivot levels, psychological levels |

**Key Capabilities:**

- **Level Identification Methods**:
  - Swing high/low detection with configurable sensitivity
  - Volume Profile-based levels (VPOC, High Volume Nodes, Low Volume Nodes)
  - Pivot Points (Classic, Fibonacci, Camarilla, Woodie, DeMark)
  - Fibonacci Retracement and Extension levels from major swings
  - Round number / psychological level detection
  - Previous day/week/month high/low levels
  - Gap identification and fill probability scoring

- **Zone Strength Scoring**:
  - Number of times a level has been tested (confluence scoring)
  - Volume at price level relative to average
  - Time spent at level (consolidation zones)
  - Sharpness of rejection moves from the level
  - Multi-timeframe level alignment (S/R on 1D confirmed on 4H and 1H)

- **Dynamic Level Tracking**:
  - Level migration as new data comes in (levels shift, break, or transform)
  - Support-to-resistance and resistance-to-support flip detection
  - Zone width adjustment based on volatility regime

---

## 4. Skill Category 3 — Fundamental Analysis

### Skill 3.1: Financial Statement Analysis

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `FUND-001` |
| **Description** | Parse, normalize, and analyze company financial statements to assess intrinsic value and financial health |
| **Input** | SEC filings (10-K, 10-Q), annual reports, financial data APIs |
| **Output** | Financial health scores, valuation metrics, growth rates, quality ratings |

**Key Capabilities:**

- **Income Statement Analysis**:
  - Revenue growth rates (YoY, QoQ, TTM) and acceleration/deceleration detection
  - Gross margin, operating margin, net margin trend analysis
  - EPS growth and EPS surprise tracking (actual vs. consensus)
  - EBITDA and EBITDA margin for operational profitability
  - Revenue composition analysis (segment breakdown, geographic split)
  - Non-recurring item identification and adjusted earnings calculation

- **Balance Sheet Analysis**:
  - Debt-to-equity, current ratio, quick ratio for financial stability
  - Return on Equity (ROE) decomposition via DuPont Analysis
  - Asset turnover and inventory turnover efficiency metrics
  - Goodwill and intangible asset percentage for acquisition risk
  - Share count tracking (dilution from options, buyback programs)
  - Working capital trend analysis for operational liquidity

- **Cash Flow Analysis**:
  - Free Cash Flow (FCF) generation and FCF yield calculation
  - Operating cash flow vs. net income divergence (earnings quality flag)
  - Capital expenditure trends (maintenance vs. growth CapEx)
  - Cash flow from financing activities (debt issuance/repayment patterns)
  - Cash conversion efficiency metrics

---

### Skill 3.2: Valuation Modeling

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `FUND-002` |
| **Description** | Compute intrinsic value estimates using multiple valuation methodologies and compare to market price |
| **Input** | Financial data, growth assumptions, discount rates, comparable company data |
| **Output** | Fair value estimates, valuation range, upside/downside to current price, confidence intervals |

**Key Capabilities:**

- **Discounted Cash Flow (DCF)**:
  - Multi-stage DCF with explicit forecast period + terminal value
  - WACC calculation with market-implied equity risk premium
  - Sensitivity analysis across discount rate and terminal growth rate
  - Monte Carlo DCF with probabilistic assumptions for revenue growth, margins, and discount rates
  - Reverse DCF to infer market expectations embedded in current price

- **Relative Valuation**:
  - P/E, Forward P/E, PEG ratio with sector and historical context
  - EV/EBITDA, EV/Sales, EV/FCF for enterprise-level comparison
  - Price/Book, Price/Tangible Book for asset-heavy industries
  - Comparable company analysis with peer group selection and adjustment
  - Historical percentile ranking of all valuation metrics

- **Specialized Valuation**:
  - Dividend Discount Model (DDM) for income stocks
  - Residual Income Model (EVA-based) for economic profit assessment
  - Sum-of-the-parts valuation for conglomerates
  - Real option valuation for biotech, mining, and early-stage companies
  - NAV (Net Asset Value) for REITs, closed-end funds, and holding companies

---

### Skill 3.3: Earnings & Event Analysis

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `FUND-003` |
| **Description** | Analyze earnings reports, guidance, and corporate events for trading opportunities |
| **Input** | Earnings reports, conference call transcripts, guidance data, SEC filings |
| **Output** | Earnings surprise signals, guidance change flags, event-driven trade setups |

**Key Capabilities:**

- **Earnings Analysis**:
  - EPS and revenue surprise detection (actual vs. consensus estimate)
  - Post-earnings drift prediction based on surprise magnitude and historical patterns
  - Earnings quality scoring (cash flow backing, one-time items, accounting changes)
  - Management guidance analysis (raise, maintain, lower) with tone assessment
  - Conference call NLP analysis (sentiment, keyword extraction, topic modeling)
  - Analyst estimate revision tracking and consensus momentum

- **Corporate Event Processing**:
  - M&A deal analysis (premium, synergy estimates, regulatory risk, timeline)
  - Spin-off and restructuring opportunity identification
  - Share buyback program analysis (authorization vs. execution, price sensitivity)
  - Dividend initiation, increase, cut, or suspension analysis
  - Stock split impact assessment (liquidity, retail interest, options activity)
  - Management changes (CEO/CFO turnover risk/opportunity assessment)
  - Legal/regulatory events (FDA approvals, FTC actions, lawsuits, settlements)

---

### Skill 3.4: Industry & Competitive Analysis

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `FUND-004` |
| **Description** | Analyze industry dynamics, competitive positioning, and market share trends |
| **Input** | Industry reports, company filings, market share data, patent databases |
| **Output** | Industry attractiveness scores, competitive moat ratings, sector rotation signals |

**Key Capabilities:**

- **Porter's Five Forces Analysis** (automated scoring):
  - Threat of new entrants (barrier to entry assessment)
  - Bargaining power of suppliers (concentration, switching costs)
  - Bargaining power of buyers (concentration, price sensitivity)
  - Threat of substitutes (technology disruption risk)
  - Competitive rivalry (market concentration, pricing power)

- **Competitive Moat Assessment**:
  - Network effect strength (user growth, engagement metrics)
  - Switching cost quantification (churn rates, contract terms)
  - Cost advantage analysis (scale economies, process efficiency)
  - Intangible asset valuation (brands, patents, licenses, regulatory approvals)
  - Efficient scale assessment (natural monopoly characteristics)

- **Industry Lifecycle Positioning**:
  - Growth stage identification (emerging, growth, mature, declining)
  - TAM/SAM/SOM estimation and addressable market analysis
  - Technology disruption timeline forecasting
  - Regulatory environment assessment and policy change probability

---

## 5. Skill Category 4 — Sentiment & Alternative Data Analysis

### Skill 4.1: Social Media Sentiment Analysis

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `SENT-001` |
| **Description** | Monitor and analyze social media platforms for real-time sentiment shifts that precede price movements |
| **Input** | Twitter/X, Reddit, StockTwits, Discord, Telegram, Weibo, financial forums |
| **Output** | Sentiment scores (-1 to +1), volume spikes, viral content alerts, coordinated activity detection |

**Key Capabilities:**

- **NLP Pipeline**:
  - Fine-tuned BERT/FinBERT for financial sentiment classification
  - Named entity recognition for ticker extraction from unstructured text
  - Sarcasm and irony detection in casual financial discourse
  - Multi-language sentiment analysis (English, Chinese, Hindi, Japanese)
  - Emotion detection beyond positive/negative (fear, greed, FOMO, panic, confidence)

- **Social Signal Processing**:
  - Sentiment momentum (rate of change in sentiment) as leading indicator
  - Unusual volume spike detection in social mentions
  - Influencer/whale account tracking and weighted sentiment scoring
  - Coordinated pumping/dumping campaign detection (bot network identification)
  - Subreddit activity analysis (wallstreetbets, options, investing)
  - Hashtag trend analysis for sector-wide sentiment shifts

- **Contrarian Signal Generation**:
  - Extreme sentiment as contrarian indicator (peak bullishness → sell signal)
  - Sentiment divergence from price action (price up + sentiment down → reversal risk)
  - Social volume exhaustion detection (meme stock lifecycle identification)

---

### Skill 4.2: News Analytics & NLP

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `SENT-002` |
| **Description** | Process thousands of news articles in real-time to extract tradeable signals |
| **Input** | News feeds (Reuters, Bloomberg, AP, financial blogs, press releases) |
| **Output** | Event classifications, sentiment scores, relevance ratings, impact predictions |

**Key Capabilities:**

- **Real-Time News Processing**:
  - Sub-second news ingestion and entity extraction
  - Event classification (earnings, M&A, regulatory, macro, product, management)
  - News novelty scoring (first mention vs. follow-on coverage)
  - Source credibility weighting (tier-1 wire vs. blog vs. social)
  - Geographic and sector tagging for targeted distribution

- **Impact Prediction**:
  - Historical news impact model (how similar events moved prices in the past)
  - Expected move magnitude prediction based on news severity and stock characteristics
  - Cross-asset impact assessment (commodity news affecting related equities)
  - News sequence analysis (initial report → follow-up → resolution timeline)

- **Advanced NLP Features**:
  - Abstractive summarization for rapid event understanding
  - Causal relationship extraction (event A → likely effect B)
  - Factual claim verification against company data
  - Tone analysis distinguishing between factual reporting and opinion
  - Forward-looking statement extraction (guidance, forecasts, plans)

---

### Skill 4.3: Analyst & Institutional Activity Tracking

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `SENT-003` |
| **Description** | Track and analyze analyst estimates, institutional holdings, and insider transactions |
| **Input** | Analyst reports, 13F filings, insider transaction data, institutional holdings |
| **Output** | Consensus shift signals, smart money flow indicators, insider sentiment scores |

**Key Capabilities:**

- **Analyst Consensus Tracking**:
  - Estimate revision momentum (upward/downward revision trends)
  - Analyst dispersion (disagreement) as uncertainty proxy
  - Analyst accuracy scoring and reliability weighting
  - Initiation/coverage drop signals
  - Price target distribution analysis and implied upside
  - Contrarian analyst signals (when most bearish → potential bottom)

- **Institutional Flow Analysis**:
  - 13F filing parsing for quarterly position changes
  - Hedge fund clone strategies (replicating top managers' holdings)
  - Institutional accumulation/distribution detection using volume-price analysis
  - ETF creation/redemption flow impact assessment
  - Short interest tracking and days-to-cover analysis
  - Fail-to-deliver data monitoring for settlement issues

- **Insider Activity Analysis**:
  - Clustered insider buying (multiple executives buying simultaneously)
  - Insider selling pattern analysis (planned 10b5-1 vs. discretionary)
  - Insider transaction size relative to historical patterns
  - CEO/CFO purchase signals vs. board member signals
  - Pre-earnings insider activity window analysis

---

## 6. Skill Category 5 — Trading Strategy Engine

### Skill 5.1: Mean Reversion Strategies

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `STRAT-001` |
| **Description** | Identify and trade when prices deviate from statistical norms, expecting return to mean |
| **Input** | Price data, volatility regime, mean reversion indicators |
| **Output** | Trade signals with entry, stop, and target levels |

**Key Capabilities:**

- **Statistical Mean Reversion**:
  - Z-score based entry/exit (buy at -2σ, sell at +2σ from rolling mean)
  - Bollinger Band mean reversion with RSI confirmation
  - Pairs trading (cointegrated securities) with dynamic hedge ratio
  - Statistical arbitrage (basket of cointegrated stocks)
  - Mean reversion within volatility-adjusted channels

- **Market Microstructure Reversion**:
  - Opening gap fade strategy (gaps that historically fill within the day)
  - VIX spike mean reversion (extreme fear → contrarian long)
  - Intraday VWAP reversion for institutional price levels
  - Overnight gap and go vs. gap fill probability models

- **Adaptive Parameters**:
  - Lookback period optimization based on current volatility regime
  - Dynamic z-score thresholds (wider in trends, tighter in ranges)
  - Half-life estimation for mean reversion speed
  - Position sizing inversely proportional to deviation magnitude

---

### Skill 5.2: Trend Following Strategies

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `STRAT-002` |
| **Description** | Identify and ride sustained price trends using systematic breakout and momentum methods |
| **Input** | Price data, trend indicators, volume confirmation |
| **Output** | Trend entry signals, trailing stop levels, trend continuation/exit signals |

**Key Capabilities:**

- **Breakout Systems**:
  - Donchian Channel breakout (classic Turtle Trading system)
  - Volatility breakout (ATR-based expansion entries)
  - Range contraction → expansion cycle detection
  - Volume-confirmed breakout validation
  - Multi-timeframe breakout alignment (1H breakout in direction of 1D trend)

- **Trend Following Systems**:
  - Moving average crossover systems (dual/triple MA with adaptive periods)
  - Channel breakout with pyramiding (adding to winning positions)
  - Aberration trading (price outside Keltner/Bollinger channels)
  - ADX-filtered trend following (only trade when ADX > 25)

- **Trend Management**:
  - Chandelier trailing stops for profit protection
  - Parabolic SAR for trend following with dynamic stops
  - Trend exhaustion detection (divergence, volume climax, extended deviation)
  - Time-based exit rules (if trade doesn't work in N bars, exit)
  - Volatility-adjusted position sizing for equal risk across instruments

---

### Skill 5.3: Scalping & High-Frequency Strategies

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `STRAT-003` |
| **Description** | Execute large numbers of small-profit trades exploiting micro-price movements and market inefficiencies |
| **Input** | Level 2 order book data, tick data, latency metrics |
| **Output** | Sub-second trade signals, market making quotes, arbitrage opportunities |
| **Latency Requirement** | < 10ms round-trip for signal generation |

**Key Capabilities:**

- **Market Making**:
  - Continuous bid/ask quoting with dynamic spread adjustment
  - Inventory management and risk limits per symbol
  - Adverse selection protection (detect informed order flow)
  - Skew quotes based on inventory position (reduce inventory by tightening side)
  - Multi-venue quoting for best execution

- **Statistical Arbitrage**:
  - Tick-level cointegration trading with real-time hedge ratio updates
  - Cross-venue arbitrage (same instrument, different exchanges)
  - ETF vs. NAV arbitrage (ETF price deviation from underlying basket)
  - Index arbitrage (futures vs. cash index mispricing)

- **Microstructure Exploitation**:
  - Order flow toxicity detection (VPIN, trade intensity)
  - Hidden liquidity detection (iceberg orders, dark pool patterns)
  - Speed advantage strategies (co-location dependent)
  - Momentum ignition detection and front-running avoidance

---

### Skill 5.4: Swing Trading Strategies

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `STRAT-004` |
| **Description** | Capture multi-day to multi-week price swings using technical setups and catalysts |
| **Input** | Daily/4H price data, technical indicators, catalyst calendar |
| **Output** | Swing trade setups with risk/reward ratios, hold period estimates |

**Key Capabilities:**

- **Setup Identification**:
  - Pullback to moving average in established trend
  - Breakout from consolidation patterns (flags, pennants, bases)
  - Reversal patterns at key support/resistance levels
  - Gap fill trades with defined time horizon
  - Earnings momentum plays (buy ahead of or after earnings with catalyst)

- **Trade Management**:
  - ATR-based stop loss and take profit levels
  - Partial profit taking at defined milestones (1R, 2R, 3R)
  - Time stop (exit if trade doesn't move within expected timeframe)
  - Trend continuation vs. reversal assessment at each bar close
  - Multi-position correlation management

- **Catalyst Integration**:
  - Earnings date proximity for setup timing
  - Fed meeting / economic data release scheduling
  - Sector rotation alignment for increased probability
  - Seasonal pattern overlay (sell in May, Santa Claus rally, etc.)

---

### Skill 5.5: Event-Driven Strategies

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `STRAT-005` |
| **Description** | Trade around specific corporate events and catalysts with defined risk/reward |
| **Input** | Earnings calendar, M&A pipeline, FDA calendar, economic calendar |
| **Output** | Event trade setups, pre/post-event positioning, straddle/strangle recommendations |

**Key Capabilities:**

- **Earnings Trading**:
  - Pre-earnings momentum (stocks that tend to run into earnings)
  - Post-earnings drift (systematic buying after positive surprises)
  - Earnings volatility crush (selling options premium post-earnings)
  - Whisper number analysis vs. consensus
  - Sector earnings contagion (first reporter sets tone for sector)

- **Merger Arbitrage**:
  - Deal spread calculation and annualized return
  - Deal completion probability estimation (regulatory, financing risks)
  - Timeline analysis with expected closing date
  - Reverse breakup fee assessment for downside protection
  - Pair trade (long target, short acquirer) with ratio management

- **Special Situations**:
  - Spin-off trading (forced selling creates discounts)
  - Bankruptcy/distressed debt analysis for deep value
  - Regulatory decision plays (FDA PDUFA dates, FTC rulings)
  - Activist investor tracking and co-investment
  - Rights offering and secondary offering analysis

---

### Skill 5.6: Quantitative Factor Strategies

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `STRAT-006` |
| **Description** | Systematic factor-based stock selection and portfolio construction |
| **Input** | Cross-sectional stock data, factor definitions, risk model |
| **Output** | Factor scores, ranked stock lists, factor-mimicking portfolios |

**Key Capabilities:**

- **Factor Models**:
  - Value factor (P/E, P/B, EV/EBITDA, FCF yield composite)
  - Momentum factor (12-1 month return, earnings momentum)
  - Quality factor (ROE, debt coverage, earnings stability)
  - Low Volatility factor (minimum variance optimization)
  - Size factor (market cap based, small cap premium)
  - Profitability factor (gross margin, operating leverage)

- **Factor Timing**:
  - Factor rotation based on macro regime (value in recovery, quality in recession)
  - Factor momentum (recent factor performance continuation)
  - Factor valuations (is the value factor itself cheap or expensive?)
  - Crowding risk assessment (popular factor unwinds)

- **Multi-Factor Portfolio Construction**:
  - Factor exposure targeting with risk budgeting
  - Sector-neutral factor portfolios
  - Transaction-cost-aware rebalancing
  - Factor purity maximization (minimize unintended exposures)

---

## 7. Skill Category 6 — Risk Management & Portfolio Protection

### Skill 6.1: Position Sizing & Risk Allocation

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `RISK-001` |
| **Description** | Determine optimal position size for each trade based on risk parameters, portfolio constraints, and market conditions |
| **Input** | Account equity, risk per trade, stop distance, correlation matrix |
| **Output** | Position size in shares/contracts, dollar risk, portfolio heat map |

**Key Capabilities:**

- **Position Sizing Methods**:
  - Fixed fractional (risk X% of equity per trade)
  - Kelly Criterion (optimal f for maximum geometric growth)
  - Volatility-adjusted sizing (ATR-based equal volatility weighting)
  - Risk parity (equal risk contribution from each position)
  - Optimal f (Ralph Vince's method for maximum terminal wealth)
  - Anti-martingale sizing (increase after wins, decrease after losses)

- **Portfolio-Level Constraints**:
  - Maximum portfolio heat (total risk across all open positions)
  - Sector/asset concentration limits
  - Correlation-adjusted position reduction (reduce when positions are correlated)
  - Margin utilization monitoring and maintenance requirement buffers
  - Drawdown-based position reduction (decrease size during drawdowns)

- **Dynamic Adjustment**:
  - Volatility regime-based scaling (smaller positions in high-vol regimes)
  - Win rate and expectancy tracking for strategy-level sizing
  - Time-of-day adjustment (smaller size in low-liquidity periods)
  - Event risk adjustment (reduce size before major events)

---

### Skill 6.2: Stop Loss & Take Profit Management

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `RISK-002` |
| **Description** | Implement intelligent, adaptive stop-loss and take-profit mechanisms that protect capital while allowing winners to run |
| **Input** | Entry price, ATR, support/resistance levels, volatility regime |
| **Output** | Dynamic stop levels, trailing stop adjustments, partial exit triggers |

**Key Capabilities:**

- **Stop Loss Types**:
  - Fixed percentage/dollar stop
  - ATR-based stop (e.g., 2× ATR from entry or recent swing low)
  - Volatility stop (Chandelier exit)
  - Time stop (exit if trade hasn't moved favorably within N bars)
  - Structural stop (below key support level for longs)
  - Parabolic SAR trailing stop
  - Moving average trailing stop (exit when price closes below MA)

- **Take Profit Mechanisms**:
  - Fixed R:R ratio targets (1:2, 1:3 risk-to-reward)
  - Partial scaling out (1/3 at 1R, 1/3 at 2R, 1/3 trailing)
  - Resistance-based targets (sell at next resistance level)
  - Extension targets (Fibonacci extensions, measured moves)
  - Volatility-based targets (expected daily range multiples)

- **Smart Order Management**:
  - Breakeven stop trigger (move stop to entry after 1R profit)
  - Trailing stop tightening as trend matures
  - Gap risk management (overnight gap stop adjustment)
  - Stop hunting awareness (place stops beyond obvious levels)

---

### Skill 6.3: Portfolio Risk Monitoring

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `RISK-003` |
| **Description** | Continuously monitor and manage portfolio-level risk metrics with real-time alerts and automatic protective actions |
| **Input** | Current positions, market data, correlation matrix, VaR parameters |
| **Output** | Real-time risk dashboard, alert notifications, automatic hedging actions |

**Key Capabilities:**

- **Risk Metrics (Real-time)**:
  - Value at Risk (VaR) — Historical, Parametric, Monte Carlo
  - Conditional VaR (CVaR / Expected Shortfall)
  - Maximum drawdown and current drawdown from peak
  - Portfolio beta relative to benchmark
  - Greeks exposure (if options positions exist) — Net Delta, Gamma, Vega, Theta
  - Sector and factor exposure breakdown
  - Concentration risk (single name, sector, country)

- **Correlation & Dependency**:
  - Rolling correlation matrix with decay factor
  - Tail dependency estimation (correlation during stress)
  - Copula-based dependency modeling (non-linear relationships)
  - Cross-asset contagion risk scoring

- **Circuit Breakers & Auto-Protection**:
  - Daily loss limit (auto-close all positions if breached)
  - Max drawdown limit (reduce all positions by 50% if hit)
  - Volatility spike protection (widen stops, reduce position sizes)
  - Gap risk protection (pre-market hedging for overnight positions)
  - Liquidity crisis protocol (switch to cash if bid-ask spreads explode)

---

### Skill 6.4: Hedging Strategies

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `RISK-004` |
| **Description** | Implement dynamic hedging to protect portfolio value during adverse market conditions |
| **Input** | Current portfolio, risk metrics, options chain data, correlation data |
| **Output** | Hedge recommendations, collar setups, protective put selections, dynamic hedge ratios |

**Key Capabilities:**

- **Direct Hedging**:
  - Index put options for portfolio-level protection
  - Sector ETF hedging for concentrated sector exposure
  - Futures hedging for equity exposure reduction
  - Currency hedging for international positions
  - Interest rate hedging for fixed-income exposure

- **Options-Based Hedging**:
  - Protective puts (ATM or OTM based on cost tolerance)
  - Collar strategies (cap upside to fund downside protection)
  - Put spreads (reduce cost by selling further OTM put)
  - VIX call options for tail risk protection
  - Calendar spreads for time-decay-favored protection

- **Dynamic Hedging**:
  - Delta-neutral hedging using options and underlying
  - Beta-adjusted short positions for partial hedging
  - Regime-dependent hedge ratio (more hedge in bear regimes)
  - Cross-asset hedging (gold, bonds, volatility as equity hedges)
  - Correlation breakdown anticipation (hedges that work when correlations spike)

---

## 8. Skill Category 7 — Order Execution & Smart Routing

### Skill 7.1: Smart Order Routing

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `EXEC-001` |
| **Description** | Route orders to optimal venues for best execution price and minimal market impact |
| **Input** | Order details, venue liquidity, fee schedules, latency matrix |
| **Output** | Routed orders across venues, execution reports, slippage analysis |

**Key Capabilities:**

- **Venue Selection**:
  - Lit exchange routing (NYSE, NASDAQ, BATS, etc.) based on NBBO
  - Dark pool routing for large orders (minimize information leakage)
  - Midpoint execution venues for spread savings
  - ETF-specific routing for creation/redemption efficiency
  - International venue routing with FX consideration

- **Order Type Optimization**:
  - Limit orders at optimal price levels (based on order book analysis)
  - Market orders only when urgency justifies slippage
  - Stop market vs. stop limit selection based on liquidity
  - Iceberg orders for large position building
  - TWAP (Time-Weighted Average Price) slicing for large orders
  - VWAP algorithm participation for institutional-size execution

- **Execution Quality Analysis**:
  - Implementation shortfall measurement
  - Slippage tracking (actual vs. signal price)
  - Fill rate analysis and venue performance comparison
  - Market impact estimation and post-trade analysis

---

### Skill 7.2: Algorithmic Execution

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `EXEC-002` |
| **Description** | Implement and manage algorithmic execution strategies for optimal trade implementation |
| **Input** | Target position, urgency level, market conditions, volume profiles |
| **Output** | Executed child orders, progress tracking, benchmark comparison |

**Key Capabilities:**

- **Execution Algorithms**:
  - **VWAP**: Distribute orders proportional to historical volume pattern
  - **TWAP**: Even distribution across time horizon
  - **Implementation Shortfall**: Balance market impact vs. timing risk
  - **Percentage of Volume**: Participate at X% of real-time volume
  - **Aggressive in the Money**: Prioritize speed when momentum is favorable
  - **Sniper**: Wait for liquidity, execute quickly when available

- **Adaptive Execution**:
  - Real-time volume prediction for VWAP adjustment
  - Volatility-triggered acceleration/deceleration
  - Price trend-aware execution (more aggressive in favorable direction)
  - Liquidity-seeking mode for illiquid securities
  - Deadline-aware scheduling (complete before market close if required)

- **Multi-Leg Execution**:
  - Synchronized execution for pair trades
  - Options hedging with delta-aware timing
  - Basket execution with sector neutrality maintenance
  - Roll execution for futures contracts

---

## 9. Skill Category 8 — AI & Machine Learning Models

### Skill 8.1: Price Prediction Models

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `ML-001` |
| **Description** | Train and deploy machine learning models for price direction and magnitude prediction |
| **Input** | Feature-engineered market data, labels, model configurations |
| **Output** | Price predictions with confidence intervals, direction probabilities |

**Key Capabilities:**

- **Model Architectures**:
  - LSTM/GRU networks for sequential price pattern learning
  - Transformer-based models for attention-weighted feature importance
  - Temporal Convolutional Networks for multi-scale pattern detection
  - Gradient Boosted Trees (XGBoost, LightGBM) for tabular feature dominance
  - Ensemble methods combining multiple model predictions

- **Feature Engineering**:
  - Technical indicator features (100+ indicators as model inputs)
  - Price-derived features (returns, log returns, fractional differentiation)
  - Cross-sectional features (relative strength, sector momentum)
  - Microstructure features (order book imbalance, trade flow metrics)
  - Calendar features (day of week, month, days to expiry, earnings proximity)
  - Macro features (yield curve, VIX, DXY, commodity prices)

- **Model Management**:
  - Walk-forward validation for realistic performance estimation
  - Feature importance tracking and drift detection
  - Model ensembling with dynamic weight adjustment
  - A/B testing of model versions in live trading
  - Retraining triggers based on performance degradation

---

### Skill 8.2: Reinforcement Learning for Trading

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `ML-002` |
| **Description** | Use reinforcement learning to learn optimal trading policies through simulated market interaction |
| **Input** | Market simulation environment, reward function, state space definition |
| **Output** | Trained policy network, action probabilities, position recommendations |

**Key Capabilities:**

- **RL Algorithms**:
  - Proximal Policy Optimization (PPO) for stable policy updates
  - Soft Actor-Critic (SAC) for exploration-exploitation balance
  - Deep Q-Network (DQN) with experience replay
  - Advantage Actor-Critic (A2C) for parallel training
  - Multi-agent RL for market simulation with competing agents

- **Environment Design**:
  - Realistic market simulation with order book dynamics
  - Transaction cost modeling (commissions, slippage, market impact)
  - Multiple reward functions (Sharpe, profit factor, Sortino, Calmar)
  - Curriculum learning (start simple, increase complexity)
  - Domain randomization for robust policy learning

- **Policy Interpretation**:
  - Action distribution analysis for understanding learned behavior
  - Feature attribution for policy decisions
  - Policy comparison across market regimes
  - Safe RL constraints (maximum drawdown, position limits)

---

### Skill 8.3: NLP for Financial Text

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `ML-003` |
| **Description** | Apply NLP models to extract trading signals from financial text data |
| **Input** | News articles, earnings calls, SEC filings, social media, analyst reports |
| **Output** | Sentiment scores, event classifications, entity relationships, forward-looking statements |

**Key Capabilities:**

- **Model Types**:
  - FinBERT / FinGPT for financial domain sentiment analysis
  - Named Entity Recognition for company, person, product extraction
  - Relation extraction for event graph construction
  - Summarization models for rapid document processing
  - Question answering for targeted information extraction from filings

- **Text Processing Pipeline**:
  - Document ingestion and deduplication
  - Language detection and translation
  - Key phrase and topic extraction
  - Temporal expression resolution ("next quarter" → specific date)
  - Financial numeric normalization ("1.5B" → 1500000000)
  - Negation and hedging language detection

- **Signal Generation**:
  - Earnings call tone shift detection (Q-over-Q comparison)
  - 10-K risk section change analysis
  - Patent filing novelty scoring
  - Management guidance extraction and comparison to consensus
  - Regulatory filing urgency classification

---

### Skill 8.4: Anomaly & Regime Detection

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `ML-004` |
| **Description** | Detect anomalous market behavior and regime changes that require strategy adaptation |
| **Input** | Real-time market data, feature distributions, historical regime labels |
| **Output** | Anomaly alerts, regime classifications, strategy parameter adjustments |

**Key Capabilities:**

- **Regime Detection**:
  - Hidden Markov Models for bull/bear/sideways regime classification
  - Change-point detection for structural break identification
  - Clustering-based regime identification (K-means, Gaussian Mixture)
  - Volatility regime classification (low/normal/high/extreme)
  - Correlation regime detection (risk-on vs. risk-off)

- **Anomaly Detection**:
  - Isolation Forest for outlier detection in multi-dimensional feature space
  - Autoencoder reconstruction error for unusual price patterns
  - Statistical process control for monitoring strategy performance
  - Flash crash detection and circuit breaker triggers
  - Liquidity anomaly detection (sudden spread widening)

- **Adaptive Response**:
  - Strategy parameter switching based on detected regime
  - Position size reduction in uncertain regimes
  - Defensive posture activation during anomaly periods
  - Strategy cooldown after consecutive losses in changed regime

---

## 10. Skill Category 9 — Market Microstructure Analysis

### Skill 9.1: Order Book Analysis

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `MICRO-001` |
| **Description** | Analyze real-time order book dynamics for short-term price prediction and execution optimization |
| **Input** | Level 2 market data (full order book), trade prints |
| **Output** | Order flow imbalance, liquidity maps, price pressure indicators |

**Key Capabilities:**

- **Order Flow Imbalance (OFI)**:
  - Bid/ask volume ratio as directional pressure indicator
  - Order cancellation rate analysis (spoofing detection)
  - Trade size distribution analysis (retail vs. institutional)
  - Limit order arrival rate for liquidity assessment
  - Market order toxicity scoring (informed vs. uninformed flow)

- **Liquidity Analysis**:
  - Bid-ask spread monitoring and tightening/widening trends
  - Depth-of-book analysis at multiple price levels
  - Liquidity vacuum detection (thin order book → potential for large moves)
  - Dark pool liquidity estimation from block trade data
  - Resiliency measurement (how quickly the book replenishes after trades)

- **Price Formation**:
  - Micro-price calculation (midpoint weighted by book imbalance)
  - Fair price estimation from order flow dynamics
  - Price impact estimation for various order sizes
  - Tick-by-tick price change prediction from book dynamics

---

### Skill 9.2: Trade Flow & Tape Reading

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `MICRO-002` |
| **Description** | Interpret the time-and-sales tape to identify institutional activity and informed trading |
| **Input** | Time and sales data, Level 1 quotes, block trade data |
| **Output** | Institutional activity flags, absorption signals, climax indicators |

**Key Capabilities:**

- **Trade Classification**:
  - Buyer/seller initiated trade classification (Lee-Ready algorithm)
  - Trade size categorization (small/medium/large/block)
  - Algorithmic trading detection (rapid small orders, time patterns)
  - Spoofing and layering pattern detection

- **Absorption Analysis**:
  - Large seller absorption at support (buying pressure absorbing sells)
  - Large buyer absorption at resistance (selling pressure absorbing buys)
  - Supply/demand zone identification from concentrated trade flow
  - Institutional accumulation/distribution footprint tracking

- **Climax Detection**:
  - Volume climax at key levels (potential reversal)
  - Exhaustion detection (declining volume on price extension)
  - Capitulation identification (panic selling climax)
  - Buying/selling pressure divergence from price

---

## 11. Skill Category 10 — Portfolio Management & Optimization

### Skill 10.1: Portfolio Construction

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `PORT-001` |
| **Description** | Construct optimal portfolios using quantitative methods balancing return, risk, and constraints |
| **Input** | Expected returns, covariance matrix, constraints, risk budget |
| **Output** | Optimal weights, rebalancing schedule, constraint-satisfying portfolio |

**Key Capabilities:**

- **Optimization Methods**:
  - Mean-Variance Optimization (Markowitz)
  - Black-Litterman model (incorporating investor views with market equilibrium)
  - Risk parity / equal risk contribution
  - Minimum variance portfolio
  - Maximum diversification portfolio
  - Robust optimization with estimation error handling
  - Hierarchical Risk Parity (HRP) for improved out-of-sample performance

- **Constraint Handling**:
  - Position size limits (min/max weight per asset)
  - Sector/industry exposure constraints
  - Turnover constraints for transaction cost control
  - Long-only vs. long-short constraints
  - Leverage limits and margin requirements
  - Tax lot optimization (tax-loss harvesting)

- **Rebalancing Strategies**:
  - Calendar rebalancing (weekly, monthly, quarterly)
  - Threshold rebalancing (rebalance when drift exceeds X%)
  - Cash flow rebalancing (use new capital to bring portfolio back to target)
  - Tax-aware rebalancing (defer gains, realize losses)

---

### Skill 10.2: Multi-Asset Allocation

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `PORT-002` |
| **Description** | Allocate capital across asset classes (equities, bonds, commodities, currencies, alternatives) for diversified returns |
| **Input** | Asset class returns, correlations, macro indicators, risk tolerance |
| **Output** | Strategic and tactical asset allocation, rebalancing triggers |

**Key Capabilities:**

- **Strategic Asset Allocation**:
  - Long-term target allocation based on investment horizon and risk profile
  - Efficient frontier construction across asset classes
  - Liability-driven investment (LDI) for specific cash flow needs
  - Goal-based allocation (safety, income, growth buckets)

- **Tactical Asset Allocation**:
  - Short-term deviation from strategic weights based on market conditions
  - Valuation-based tilts (overweight cheap asset classes)
  - Momentum-based tilts (overweight trending asset classes)
  - Macro signal-based allocation (yield curve, inflation, growth)
  - Risk budget reallocation during stress periods

- **Dynamic Risk Management**:
  - Target volatility strategy (deleverage when vol rises, releverage when it falls)
  - Drawdown control (reduce risk after peak-to-trough exceeds threshold)
  - Crisis alpha allocation (trend following as portfolio diversifier)
  - Correlation regime monitoring for diversification effectiveness

---

## 12. Skill Category 11 — Backtesting & Simulation

### Skill 11.1: Strategy Backtesting Engine

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `BACK-001` |
| **Description** | Rigorously test trading strategies against historical data with realistic assumptions |
| **Input** | Strategy logic, historical data, cost assumptions, risk parameters |
| **Output** | Performance metrics, trade logs, equity curves, statistical significance tests |

**Key Capabilities:**

- **Backtesting Framework**:
  - Event-driven backtesting with realistic order fill simulation
  - Bar-by-bar replay with configurable granularity (tick, second, minute)
  - Multi-asset, multi-timeframe simultaneous backtesting
  - Point-in-time data ensuring no look-ahead bias
  - Slippage and commission modeling (fixed, percentage, tiered)
  - Market impact estimation for large positions
  - Margin and borrowing cost simulation for leveraged strategies

- **Performance Metrics**:
  - Total return, CAGR, monthly/annual returns
  - Sharpe ratio, Sortino ratio, Calmar ratio, Omega ratio
  - Maximum drawdown, average drawdown, drawdown duration
  - Win rate, profit factor, expectancy per trade
  - Average win/loss ratio, consecutive win/loss streaks
  - Alpha and beta relative to benchmark
  - Information ratio and tracking error

- **Statistical Validation**:
  - Bootstrap confidence intervals for all metrics
  - Deflated Sharpe ratio (accounting for multiple testing)
  - Monte Carlo permutation test for strategy significance
  - Walk-forward analysis for out-of-sample validation
  - Parameter sensitivity analysis (is the strategy robust to parameter changes?)

---

### Skill 11.2: Paper Trading & Forward Testing

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `BACK-002` |
| **Description** | Test strategies in real-time with simulated execution before committing real capital |
| **Input** | Live market data, strategy signals, simulated order book |
| **Output** | Forward test performance, live vs. backtest comparison, go-live readiness assessment |

**Key Capabilities:**

- **Paper Trading System**:
  - Real-time signal generation matching production code
  - Simulated order execution with realistic fill assumptions
  - Latency simulation matching expected production environment
  - Position tracking and P&L calculation identical to live system
  - Paper trade journaling with signal context for post-analysis

- **Backtest vs. Live Comparison**:
  - Systematic comparison of expected vs. actual performance
  - Slippage analysis (how much worse are real fills?)
  - Signal divergence detection (any differences in signal generation?)
  - Execution quality benchmarking
  - Go-live checklist validation (all criteria met before capital allocation)

---

### Skill 11.3: Stress Testing & Scenario Analysis

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `BACK-003` |
| **Description** | Evaluate portfolio and strategy performance under extreme market scenarios |
| **Input** | Current portfolio, historical crisis scenarios, hypothetical scenarios |
| **Output** | Scenario P&L, risk metric changes, survival probability, recommended hedges |

**Key Capabilities:**

- **Historical Scenario Replay**:
  - 2008 Financial Crisis (Lehman, credit freeze, liquidity crisis)
  - 2020 COVID Crash (fast crash, V-shaped recovery, sector rotation)
  - 2010 Flash Crash (microstructure failure, rapid recovery)
  - 2018 Volmageddon (inverse VIX product blowup)
  - 2022 Rate Shock (bond/equity simultaneous decline)
  - 1998 LTCM Crisis (correlation breakdown, flight to quality)

- **Hypothetical Scenarios**:
  - S&P 500 decline of 10%, 20%, 30%, 50%
  - Interest rate shock (+200bps, +500bps)
  - Currency crisis (USD surge, emerging market collapse)
  - Geopolitical event (war, trade embargo, sanctions)
  - Technology sector crash (AI bubble burst, regulation)
  - Liquidity crisis (market closure, failed clearing)

- **Stress Test Outputs**:
  - Portfolio P&L under each scenario
  - Margin call probability and funding requirements
  - Liquidity assessment (can positions be liquidated?)
  - Recommended defensive actions for each scenario
  - Tail risk insurance cost-benefit analysis

---

## 13. Skill Category 12 — News & Event Processing

### Skill 12.1: Economic Calendar Integration

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `NEWS-001` |
| **Description** | Track and react to scheduled economic releases that move markets |
| **Input** | Economic calendar, consensus estimates, actual releases |
| **Output** | Surprise alerts, market impact predictions, position adjustments |

**Key Capabilities:**

- **Key Economic Indicators**:
  - Employment (NFP, unemployment rate, ADP, jobless claims)
  - Inflation (CPI, PPI, PCE, wage growth)
  - GDP (advance, preliminary, final estimates)
  - Central bank decisions (Fed, ECB, BOJ, BOE, RBI rate decisions and minutes)
  - Manufacturing (ISM, PMI, industrial production)
  - Housing (starts, permits, sales, Case-Shiller)
  - Consumer (retail sales, consumer confidence, sentiment)

- **Market Impact Modeling**:
  - Historical impact database (how much did S&P 500 move after each release type?)
  - Surprise magnitude vs. price move regression
  - Pre-positioning vs. post-release drift patterns
  - Cross-asset impact (bond, FX, commodity reaction to same data)
  - Time-of-day impact variation (pre-market vs. midday releases)

- **Event Risk Management**:
  - Automatic position reduction before high-impact events
  - Straddle/strangle opportunity identification around events
  - Post-event volatility trading strategies
  - Calendar-aware strategy scheduling (avoid trading around event uncertainty)

---

### Skill 12.2: Real-Time News Impact Engine

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `NEWS-002` |
| **Description** | Process breaking news in real-time and generate immediate, tradeable signals |
| **Input** | Real-time news feeds, event classification, historical impact database |
| **Output** | Tradeable signals with urgency levels, position recommendations, risk alerts |

**Key Capabilities:**

- **Breaking News Pipeline**:
  - Sub-second news ingestion and parsing
  - Event type classification (terrorist attack, CEO resignation, product recall, etc.)
  - Affected securities identification (direct and indirect exposure)
  - Historical analogy matching (similar past events and their market impact)
  - Urgency classification (trade now, adjust positions, monitor only)

- **Automated Response**:
  - Immediate position flattening for catastrophic events
  - Sector-wide hedging for industry-specific news
  - Opportunistic entry for overreactions with defined risk
  - Cross-asset cascade analysis (equity → bond → currency → commodity chain reaction)

---

## 14. Skill Category 13 — Macro & Economic Analysis

### Skill 13.1: Business Cycle Analysis

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `MACRO-001` |
| **Description** | Identify current business cycle phase and position portfolio accordingly |
| **Input** | GDP, employment, inflation, yield curve, leading indicators |
| **Output** | Cycle phase classification, sector/factor rotation recommendations |

**Key Capabilities:**

- **Cycle Phase Identification**:
  - Early cycle (recovery from recession): Favor cyclicals, financials, small caps
  - Mid cycle (expansion): Broad equity exposure, growth stocks
  - Late cycle (overheating): Energy, commodities, defensive rotation
  - Recession: Bonds, defensive sectors, minimum volatility, cash

- **Leading Indicators**:
  - Yield curve shape (inversion as recession predictor)
  - ISM New Orders for manufacturing momentum
  - Building permits for housing cycle
  - Initial jobless claims for labor market turning points
  - Credit spreads for financial stress
  - Consumer confidence for spending outlook

- **Sector Rotation Model**:
  - Relative strength sector rotation tracking
  - Macro-informed sector overweight/underweight
  - Factor rotation aligned with business cycle
  - Regional allocation based on divergent economic cycles

---

### Skill 13.2: Interest Rate & Yield Curve Analysis

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `MACRO-002` |
| **Description** | Analyze yield curve dynamics and interest rate expectations for fixed-income and equity positioning |
| **Input** | Treasury yields, Fed funds futures, swap rates, inflation expectations |
| **Output** | Rate move predictions, yield curve trade recommendations, duration positioning |

**Key Capabilities:**

- **Yield Curve Analysis**:
  - Curve steepening/flattening trade signals
  - 2s10s, 3m10s spread tracking for recession signals
  - Real yield analysis (nominal minus breakeven inflation)
  - Term premium estimation (ACM model)
  - Forward rate analysis for market-implied rate path

- **Central Bank Interpretation**:
  - FOMC statement parsing for policy change signals
  - Dot plot analysis for rate path expectations
  - Forward guidance credibility tracking
  - Balance sheet policy impact (QT/QE effects on liquidity)
  - Global central bank policy divergence analysis

- **Interest Rate Strategy**:
  - Duration management based on rate outlook
  - Curve positioning for expected shape changes
  - Inflation-protected securities (TIPS) vs. nominal selection
  - Credit spread positioning (investment grade vs. high yield)

---

## 15. Skill Category 14 — Options & Derivatives Trading

### Skill 14.1: Options Strategy Selection

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `OPT-001` |
| **Description** | Select and execute optimal options strategies based on volatility outlook and directional view |
| **Input** | Directional view, volatility view, time horizon, risk tolerance |
| **Output** | Strategy recommendation, strike/expiration selection, risk/reward profile |

**Key Capabilities:**

- **Directional Strategies**:
  - Bullish: Long call, bull call spread, bull put spread, call calendar spread
  - Bearish: Long put, bear put spread, bear call spread, put calendar spread
  - Neutral: Iron condor, butterfly, straddle selling, iron butterfly

- **Volatility Strategies**:
  - Low vol expectation: Sell straddles/strangles, iron condors, calendar spreads
  - High vol expectation: Buy straddles/strangles, vix calls, variance swaps
  - Vol skew trades: Risk reversal, put spread collar, skewed butterflies

- **Income Strategies**:
  - Covered call writing (enhanced yield on long stock)
  - Cash-secured put selling (lower cost basis entry)
  - Poor man's covered call (LEAPS + short calls)
  - Wheel strategy (put → assigned → covered call → repeat)

- **Strike & Expiration Optimization**:
  - Delta-based strike selection matching directional conviction
  - Expiration selection balancing time decay and move expectation
  - Implied volatility rank/percentile for strategy selection
  - Earnings cycle consideration for expiration timing
  - Probability of profit calculation for each strategy

---

### Skill 14.2: Greeks Management & Hedging

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `OPT-002` |
| **Description** | Monitor and manage portfolio Greeks exposure with dynamic hedging |
| **Input** | Options positions, underlying prices, volatility surface, interest rates |
| **Output** | Greeks exposure report, hedge recommendations, rebalance triggers |

**Key Capabilities:**

- **Greeks Monitoring**:
  - Net Delta exposure (directional risk)
  - Net Gamma exposure (convexity / acceleration risk)
  - Net Vega exposure (volatility risk)
  - Net Theta exposure (time decay P&L)
  - Rho exposure (interest rate sensitivity)
  - Vanna and Volga (second-order Greeks for advanced risk management)

- **Delta Hedging**:
  - Continuous delta-neutral rebalancing for market-making
  - Band-based hedging (rebalance when delta exceeds threshold)
  - Gamma-aware hedging (more frequent near ATM and near expiry)
  - Cost-aware hedging (minimize transaction costs of rebalancing)

- **Volatility Trading**:
  - Implied vs. realized volatility spread analysis
  - Volatility arbitrage (sell overpriced, buy underpriced implied vol)
  - Term structure trading (front month vs. back month vol spreads)
  - Skew trading (put vs. call volatility spreads)
  - Volatility surface arbitrage detection

---

## 16. Skill Category 15 — Crypto & Digital Asset Trading

### Skill 15.1: Crypto Market Analysis & Trading

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `CRYPTO-001` |
| **Description** | Apply and adapt trading strategies specifically for cryptocurrency markets |
| **Input** | Crypto price data, on-chain data, exchange flows, DeFi metrics |
| **Output** | Crypto trade signals, on-chain alerts, DeFi opportunity identification |

**Key Capabilities:**

- **On-Chain Analysis**:
  - Whale wallet tracking and large transaction monitoring
  - Exchange inflow/outflow analysis (selling/buying pressure)
  - Miner activity (hash rate, miner selling, difficulty adjustments)
  - Active address and transaction volume trends
  - HODL waves and coin dormancy for supply analysis
  - Stablecoin supply and issuance for buying power assessment

- **DeFi Analytics**:
  - Yield farming opportunity identification and comparison
  - Liquidity pool analysis and impermanent loss estimation
  - Lending protocol rate monitoring and arbitrage
  - DEX volume and price deviation from CEX
  - Bridge activity for cross-chain capital flow

- **Crypto-Specific Strategies**:
  - Bitcoin halving cycle analysis and positioning
  - Altcoin rotation and sector cycling (L1, DeFi, Gaming, AI tokens)
  - Funding rate arbitrage (perpetual futures vs. spot)
  - Cross-exchange arbitrage (price differences between venues)
  - NFT and token airdrop farming strategies

---

## 17. Skill Category 16 — Compliance & Regulatory Monitoring

### Skill 16.1: Trade Compliance & Surveillance

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `COMP-001` |
| **Description** | Ensure all trading activities comply with regulatory requirements and internal risk limits |
| **Input** | Trade records, regulatory rules, position limits, restricted lists |
| **Output** | Compliance reports, violation alerts, restricted trade blocks |

**Key Capabilities:**

- **Regulatory Compliance**:
  - Pattern day trading rule monitoring (for applicable accounts)
  - Position limit tracking (CFTC, exchange-specific limits)
  - Wash sale rule compliance for tax purposes
  - Short sale restriction (SSR) monitoring and compliance
  - Market manipulation detection (spoofing, layering, painting the tape)
  - Insider trading prevention (restricted list enforcement)

- **Internal Risk Limits**:
  - Maximum position size per instrument
  - Maximum sector exposure
  - Daily loss limit enforcement
  - Maximum drawdown threshold
  - Leverage ratio monitoring
  - Concentration risk limits

- **Audit Trail**:
  - Complete trade lifecycle logging (signal → decision → order → fill)
  - Strategy attribution (which strategy generated which trade)
  - Decision context recording (why was this trade taken?)
  - P&L attribution by strategy, instrument, and factor
  - Regulatory reporting data preparation

---

## 17. Skill Category 17 — Adaptive Learning & Regime Detection

### Skill 17.1: Market Regime Detection

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `ADAPT-001` |
| **Description** | Continuously classify the current market regime and adjust strategy parameters accordingly |
| **Input** | Price data, volatility, correlation, macro indicators |
| **Output** | Current regime label, confidence score, recommended strategy adjustments |

**Key Capabilities:**

- **Regime Classification Models**:
  - Hidden Markov Model (HMM) with 4+ states
  - Gaussian Mixture Model for soft regime assignment
  - Regime-Switching Model (Hamilton's Markov Switching)
  - Clustering-based regime identification
  - Expert rule-based regime detection (volatility + trend + breadth)

- **Regime Definitions**:
  - Bull Trending (low vol, rising prices, broad participation)
  - Bull Volatile (high vol, rising prices, narrow leadership)
  - Bear Trending (high vol, falling prices, negative breadth)
  - Bear Quiet (low vol, falling prices, apathy)
  - Range-bound (low vol, sideways, mean reversion favorable)
  - Crisis (extreme vol, correlation spike, liquidity dry-up)

- **Strategy Adaptation**:
  - Trend-following allocation increase in trending regimes
  - Mean-reversion allocation increase in range-bound regimes
  - Cash allocation increase in crisis/uncertain regimes
  - Position size scaling based on regime confidence
  - Stop loss width adjustment based on volatility regime

---

### Skill 17.2: Strategy Performance Feedback Loop

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `ADAPT-002` |
| **Description** | Continuously evaluate strategy performance and automatically adjust or deactivate underperforming strategies |
| **Input** | Live trading results, performance benchmarks, statistical tests |
| **Output** | Strategy health scores, parameter adjustments, activation/deactivation decisions |

**Key Capabilities:**

- **Performance Monitoring**:
  - Rolling Sharpe ratio tracking (declining Sharpe → warning)
  - Win rate and expectancy trend analysis
  - Drawdown monitoring relative to historical norms
  - Slippage and execution quality degradation detection
  - Strategy correlation increase (losing diversification benefit)

- **Adaptive Actions**:
  - Parameter recalibration when performance degrades
  - Strategy weight reduction for underperformers
  - Complete strategy suspension when statistical significance is lost
  - Automatic strategy rotation to better-suited alternatives
  - Capital reallocation from weak to strong strategies

- **Learning Mechanisms**:
  - Online learning for model parameter updates
  - Reinforcement learning for strategy selection policy
  - Bayesian updating for regime probability estimation
  - A/B testing framework for strategy improvements
  - Ensemble method reweighting based on recent performance

---

## 18. Skill Category 18 — Multi-Agent Coordination & Orchestration

### Skill 18.1: Agent Orchestration & Decision Fusion

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `AGENT-001` |
| **Description** | Coordinate multiple specialized agents, fuse their signals, and make unified trading decisions |
| **Input** | Agent signals, confidence scores, historical accuracy, market context |
| **Output** | Unified trade decisions, position sizes, execution instructions |

**Key Capabilities:**

- **Signal Aggregation**:
  - Weighted voting based on agent accuracy scores
  - Bayesian opinion pooling for probability fusion
  - Stacking meta-learner combining agent predictions
  - Conflict resolution (when agents disagree → reduce confidence)
  - Signal strength amplification (multiple agents agree → high conviction)

- **Agent Management**:
  - Agent health monitoring (is the agent producing signals on time?)
  - Agent performance tracking (which agents are adding value?)
  - Dynamic agent weighting (increase weight of accurate agents)
  - Agent cooldown (temporarily disable agents in drawdown)
  - New agent onboarding and validation framework

- **Decision Pipeline**:
  1. Data agents collect and preprocess market data
  2. Analysis agents generate signals (technical, fundamental, sentiment, ML)
  3. Strategy agents convert signals into trade ideas
  4. Risk agent evaluates trade ideas and adjusts sizes
  5. Execution agent implements approved trades
  6. Monitor agent tracks performance and provides feedback
  7. Learning agent updates models and parameters

---

### Skill 18.2: Inter-Agent Communication Protocol

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `AGENT-002` |
| **Description** | Define and manage the communication protocol between agents for efficient information flow |
| **Input** | Agent outputs, message schemas, priority rules |
| **Output** | Standardized messages, priority-queued tasks, audit logs |

**Key Capabilities:**

- **Message Schema**:
  - Signal message (direction, instrument, confidence, timeframe, source agent)
  - Risk message (exposure alert, limit warning, margin call notice)
  - Execution message (order request, fill confirmation, rejection notice)
  - Market event message (breaking news, economic release, halt/resume)
  - System message (agent status, health check, heartbeat)

- **Priority & Routing**:
  - Emergency priority (circuit breaker, flash crash, system failure)
  - High priority (risk alerts, margin calls, breaking news)
  - Normal priority (trade signals, analysis updates)
  - Low priority (model retraining, report generation, data updates)

- **Communication Patterns**:
  - Publish-subscribe for market data distribution
  - Request-reply for risk queries
  - Event-driven for breaking news cascade
  - Batch processing for end-of-day reconciliation

---

## 19. Skill Category 19 — Performance Analytics & Reporting

### Skill 19.1: Real-Time P&L & Performance Dashboard

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `PERF-001` |
| **Description** | Track and visualize trading performance in real-time with comprehensive metrics |
| **Input** | Trade data, position data, market data, benchmark data |
| **Output** | Real-time P&L, performance charts, risk dashboards, attribution reports |

**Key Capabilities:**

- **Real-Time Metrics**:
  - Unrealized and realized P&L by position, strategy, and portfolio
  - Running Sharpe ratio, Sortino ratio, Calmar ratio
  - Current drawdown from peak and maximum drawdown
  - Win rate, average win/loss, profit factor (rolling windows)
  - Exposure metrics (gross, net, beta, sector breakdown)
  - Greeks exposure for options positions

- **Visualization Dashboard**:
  - Equity curve with drawdown overlay
  - Rolling returns (1M, 3M, 6M, 12M)
  - Monthly return heatmap
  - Strategy contribution waterfall chart
  - Risk metric trend lines
  - Position exposure pie chart by sector/strategy

- **Alert System**:
  - Daily loss threshold alerts
  - Drawdown limit alerts
  - Strategy performance degradation warnings
  - Unusual activity notifications
  - Margin utilization warnings

---

### Skill 19.2: Trade Journaling & Attribution

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `PERF-002` |
| **Description** | Maintain detailed trade journals and perform P&L attribution analysis |
| **Input** | Complete trade records, market conditions, strategy classifications |
| **Output** | Trade journals, attribution reports, strategy performance breakdowns |

**Key Capabilities:**

- **Trade Journal**:
  - Entry/exit timestamps and prices
  - Signal source and strategy attribution
  - Market context at entry (trend, volatility, sentiment)
  - Trade rationale and decision quality scoring
  - Post-trade analysis (what worked, what didn't, lessons learned)
  - Screenshot of chart at entry for pattern review

- **Attribution Analysis**:
  - P&L attribution by strategy (which strategies contributed most?)
  - P&L attribution by instrument (which stocks were most profitable?)
  - P&L attribution by sector (sector exposure effect on returns)
  - P&L attribution by factor (value, momentum, quality contribution)
  - Timing attribution (entry timing vs. exit timing quality)
  - Luck vs. skill decomposition using statistical tests

---

## 20. Skill Category 20 — Infrastructure & DevOps

### Skill 20.1: Low-Latency Infrastructure

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `INFRA-001` |
| **Description** | Maintain ultra-low-latency infrastructure for time-critical trading operations |
| **Input** | Infrastructure requirements, latency targets, uptime SLAs |
| **Output** | Optimized execution environment, latency monitoring, auto-scaling policies |

**Key Capabilities:**

- **Infrastructure Stack**:
  - Co-located servers near exchange matching engines
  - Kernel-bypass networking (DPDK, Solarflare) for sub-microsecond network I/O
  - FPGA acceleration for critical signal processing paths
  - In-memory databases for hot data (Redis, Aerospike)
  - Real-time operating system configurations (CPU pinning, IRQ isolation)

- **Latency Optimization**:
  - Tick-to-trade latency measurement and optimization
  - Network path optimization and monitoring
  - Code-level profiling for hot path optimization
  - Garbage collection tuning for Java-based components
  - Lock-free data structures for concurrent processing

- **Monitoring & Alerting**:
  - Microsecond-level latency tracking per component
  - Jitter monitoring and alerting
  - Exchange connectivity health checks
  - Automatic failover to backup systems
  - Capacity planning based on message rate trends

---

### Skill 20.2: Data Pipeline & Storage

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `INFRA-002` |
| **Description** | Build and maintain scalable data pipelines for market data, analytics, and storage |
| **Input** | Raw data feeds, processing requirements, storage policies |
| **Output** | Processed data streams, queryable databases, archived data stores |

**Key Capabilities:**

- **Data Pipeline Architecture**:
  - Apache Kafka for real-time event streaming
  - Apache Flink for stream processing and complex event processing
  - TimescaleDB for time-series storage with fast range queries
  - ClickHouse for analytical queries on historical data
  - Parquet on S3/GCS for long-term archival storage

- **Data Quality**:
  - Real-time data validation and anomaly detection
  - Missing data detection and backfill automation
  - Cross-source data reconciliation
  - Data lineage tracking for audit compliance
  - Schema evolution management

- **Scalability**:
  - Horizontal scaling for increasing data volume
  - Auto-scaling based on message throughput
  - Multi-region deployment for disaster recovery
  - Data partitioning for query performance
  - Hot/warm/cold data tiering for cost optimization

---

### Skill 20.3: System Reliability & Disaster Recovery

| Attribute | Detail |
|-----------|--------|
| **Skill ID** | `INFRA-003` |
| **Description** | Ensure 99.99% uptime for trading systems with comprehensive failover and recovery |
| **Input** | System architecture, failure scenarios, recovery time objectives |
| **Output** | Monitoring dashboards, failover automation, recovery procedures |

**Key Capabilities:**

- **High Availability**:
  - Active-active deployment across multiple availability zones
  - Automatic failover for all critical components
  - Health check endpoints with circuit breaker patterns
  - Graceful degradation (reduce functionality rather than full outage)
  - Kill switch for emergency portfolio liquidation

- **Disaster Recovery**:
  - RPO < 1 second for trade data (synchronous replication)
  - RTO < 30 seconds for critical system recovery
  - Regular DR testing with simulated failures
  - Off-site backup of all configuration and code
  - Documented runbooks for all failure scenarios

- **Security**:
  - API key and secret management (HashiCorp Vault)
  - Network segmentation (trading systems isolated from internet)
  - Encrypted data at rest and in transit
  - Multi-factor authentication for all trading operations
  - Regular penetration testing and security audits

---

## 22. Agent Role Definitions

### Agent Roster

| Agent Name | Primary Skills | Description |
|-----------|---------------|-------------|
| **DataAgent** | DATA-001 to DATA-004 | Collects, normalizes, and distributes all market and alternative data |
| **TechAgent** | TECH-001 to TECH-005 | Performs comprehensive technical analysis and pattern recognition |
| **FundAgent** | FUND-001 to FUND-004 | Conducts fundamental analysis, valuation, and competitive assessment |
| **SentimentAgent** | SENT-001 to SENT-003 | Analyzes social media, news, and institutional activity for sentiment signals |
| **StrategyAgent** | STRAT-001 to STRAT-006 | Generates trade signals from mean reversion, trend, scalping, swing, event, and factor strategies |
| **RiskAgent** | RISK-001 to RISK-004 | Manages position sizing, stops, portfolio risk, and hedging — has VETO power |
| **ExecAgent** | EXEC-001, EXEC-002 | Handles smart order routing and algorithmic execution |
| **MLAgent** | ML-001 to ML-004 | Runs price prediction, RL, NLP, and anomaly detection models |
| **MicroAgent** | MICRO-001, MICRO-002 | Analyzes order book and trade flow for microstructure signals |
| **PortfolioAgent** | PORT-001, PORT-002 | Constructs and optimizes multi-asset portfolios |
| **BacktestAgent** | BACK-001 to BACK-003 | Runs backtests, paper trading, and stress tests |
| **NewsAgent** | NEWS-001, NEWS-002 | Processes economic calendar and real-time news |
| **MacroAgent** | MACRO-001, MACRO-002 | Analyzes business cycles and interest rates |
| **OptionsAgent** | OPT-001, OPT-002 | Selects options strategies and manages Greeks |
| **CryptoAgent** | CRYPTO-001 | Handles crypto-specific analysis and trading |
| **ComplianceAgent** | COMP-001 | Ensures regulatory compliance and maintains audit trails |
| **AdaptAgent** | ADAPT-001, ADAPT-002 | Detects market regimes and adapts strategies |
| **OrchestratorAgent** | AGENT-001, AGENT-002 | Coordinates all agents and fuses signals into decisions |
| **PerfAgent** | PERF-001, PERF-002 | Tracks performance, generates reports, and journals trades |
| **InfraAgent** | INFRA-001 to INFRA-003 | Maintains low-latency infrastructure, data pipelines, and system reliability |

---

## 23. Skill Dependency Map

```
DataAgent ────────┐
  DATA-001        │
  DATA-002        ├──→ TechAgent ──────┐
  DATA-003        │    TECH-001..005    │
  DATA-004        │                     │
                  ├──→ FundAgent ──────┤
                  │    FUND-001..004    │
                  │                     │
                  ├──→ SentimentAgent ─┤
                  │    SENT-001..003    │
                  │                     │
                  ├──→ MicroAgent ─────┤
                  │    MICRO-001..002   ├──→ StrategyAgent ────┐
                  │                     │    STRAT-001..006     │
                  ├──→ NewsAgent ──────┤                        │
                  │    NEWS-001..002    │                        │
                  │                     │                        ├──→ RiskAgent
                  ├──→ MacroAgent ─────┤                        │    RISK-001..004
                  │    MACRO-001..002   │                        │
                  │                     │                        │
                  └──→ MLAgent ────────┘                        │
                       ML-001..004                              │
                                                                │
BacktestAgent ──────────────────────────────────────────────────┤
  BACK-001..003                                                 │
                                                                │
OptionsAgent ───────────────────────────────────────────────────┤
  OPT-001, OPT-002                                              │
                                                                │
CryptoAgent ────────────────────────────────────────────────────┤
  CRYPTO-001                                                    │
                                                                ├──→ OrchestratorAgent ──→ ExecAgent
                                                                │    AGENT-001..002       EXEC-001..002
ComplianceAgent ────────────────────────────────────────────────┤
  COMP-001                                                      │
                                                                │
AdaptAgent ─────────────────────────────────────────────────────┤
  ADAPT-001..002                                                │
                                                                │
PerfAgent ──────────────────────────────────────────────────────┘
  PERF-001..002

InfraAgent ── Supports ALL agents
  INFRA-001..003

PortfolioAgent ── Independent optimization layer
  PORT-001, PORT-002
```

---

## 24. Implementation Priority Matrix

### Phase 1: Foundation (Weeks 1-4)
| Priority | Skill ID | Skill Name | Effort |
|----------|----------|-----------|--------|
| P0 | DATA-001 | Real-Time Market Data Streaming | 2 weeks |
| P0 | DATA-002 | Historical Data Management | 1 week |
| P0 | TECH-001 | Trend Indicators & Pattern Recognition | 1 week |
| P0 | TECH-002 | Momentum & Oscillator Analysis | 1 week |
| P0 | RISK-001 | Position Sizing & Risk Allocation | 1 week |
| P0 | RISK-002 | Stop Loss & Take Profit Management | 1 week |
| P0 | EXEC-001 | Smart Order Routing | 2 weeks |
| P0 | INFRA-001 | Low-Latency Infrastructure | 2 weeks |
| P0 | INFRA-002 | Data Pipeline & Storage | 2 weeks |

### Phase 2: Intelligence (Weeks 5-8)
| Priority | Skill ID | Skill Name | Effort |
|----------|----------|-----------|--------|
| P1 | TECH-003 | Volatility Analysis | 1 week |
| P1 | TECH-005 | Support & Resistance Identification | 1 week |
| P1 | FUND-001 | Financial Statement Analysis | 2 weeks |
| P1 | FUND-002 | Valuation Modeling | 2 weeks |
| P1 | STRAT-001 | Mean Reversion Strategies | 1 week |
| P1 | STRAT-002 | Trend Following Strategies | 1 week |
| P1 | ML-001 | Price Prediction Models | 2 weeks |
| P1 | BACK-001 | Strategy Backtesting Engine | 2 weeks |
| P1 | RISK-003 | Portfolio Risk Monitoring | 1 week |

### Phase 3: Advanced (Weeks 9-12)
| Priority | Skill ID | Skill Name | Effort |
|----------|----------|-----------|--------|
| P2 | SENT-001 | Social Media Sentiment Analysis | 2 weeks |
| P2 | SENT-002 | News Analytics & NLP | 2 weeks |
| P2 | STRAT-004 | Swing Trading Strategies | 1 week |
| P2 | STRAT-005 | Event-Driven Strategies | 1 week |
| P2 | ML-002 | Reinforcement Learning for Trading | 3 weeks |
| P2 | ML-004 | Anomaly & Regime Detection | 1 week |
| P2 | ADAPT-001 | Market Regime Detection | 1 week |
| P2 | AGENT-001 | Agent Orchestration & Decision Fusion | 2 weeks |
| P2 | NEWS-001 | Economic Calendar Integration | 1 week |

### Phase 4: Professional (Weeks 13-16)
| Priority | Skill ID | Skill Name | Effort |
|----------|----------|-----------|--------|
| P3 | STRAT-003 | Scalping & High-Frequency Strategies | 2 weeks |
| P3 | STRAT-006 | Quantitative Factor Strategies | 2 weeks |
| P3 | OPT-001 | Options Strategy Selection | 2 weeks |
| P3 | OPT-002 | Greeks Management & Hedging | 1 week |
| P3 | MICRO-001 | Order Book Analysis | 2 weeks |
| P3 | MICRO-002 | Trade Flow & Tape Reading | 1 week |
| P3 | PORT-001 | Portfolio Construction | 2 weeks |
| P3 | RISK-004 | Hedging Strategies | 1 week |
| P3 | EXEC-002 | Algorithmic Execution | 2 weeks |

### Phase 5: Specialized (Weeks 17-20)
| Priority | Skill ID | Skill Name | Effort |
|----------|----------|-----------|--------|
| P4 | DATA-003 | Alternative Data Ingestion | 3 weeks |
| P4 | DATA-004 | Options & Derivatives Data Processing | 1 week |
| P4 | FUND-003 | Earnings & Event Analysis | 1 week |
| P4 | FUND-004 | Industry & Competitive Analysis | 2 weeks |
| P4 | SENT-003 | Analyst & Institutional Activity Tracking | 1 week |
| P4 | ML-003 | NLP for Financial Text | 2 weeks |
| P4 | TECH-004 | Volume & Market Breadth Analysis | 1 week |
| P4 | MACRO-001 | Business Cycle Analysis | 1 week |
| P4 | MACRO-002 | Interest Rate & Yield Curve Analysis | 1 week |
| P4 | CRYPTO-001 | Crypto Market Analysis & Trading | 2 weeks |

### Phase 6: Mastery (Weeks 21-24)
| Priority | Skill ID | Skill Name | Effort |
|----------|----------|-----------|--------|
| P5 | BACK-002 | Paper Trading & Forward Testing | 1 week |
| P5 | BACK-003 | Stress Testing & Scenario Analysis | 1 week |
| P5 | PORT-002 | Multi-Asset Allocation | 2 weeks |
| P5 | COMP-001 | Trade Compliance & Surveillance | 2 weeks |
| P5 | ADAPT-002 | Strategy Performance Feedback Loop | 1 week |
| P5 | AGENT-002 | Inter-Agent Communication Protocol | 1 week |
| P5 | PERF-001 | Real-Time P&L & Performance Dashboard | 2 weeks |
| P5 | PERF-002 | Trade Journaling & Attribution | 1 week |
| P5 | INFRA-003 | System Reliability & Disaster Recovery | 2 weeks |
| P5 | NEWS-002 | Real-Time News Impact Engine | 1 week |

---

## Summary Statistics

| Category | Count | Skill IDs |
|----------|-------|-----------|
| Market Data Acquisition | 4 | DATA-001 to DATA-004 |
| Technical Analysis | 5 | TECH-001 to TECH-005 |
| Fundamental Analysis | 4 | FUND-001 to FUND-004 |
| Sentiment & Alternative Data | 3 | SENT-001 to SENT-003 |
| Trading Strategy Engine | 6 | STRAT-001 to STRAT-006 |
| Risk Management | 4 | RISK-001 to RISK-004 |
| Order Execution | 2 | EXEC-001, EXEC-002 |
| AI & Machine Learning | 4 | ML-001 to ML-004 |
| Market Microstructure | 2 | MICRO-001, MICRO-002 |
| Portfolio Management | 2 | PORT-001, PORT-002 |
| Backtesting & Simulation | 3 | BACK-001 to BACK-003 |
| News & Event Processing | 2 | NEWS-001, NEWS-002 |
| Macro & Economic Analysis | 2 | MACRO-001, MACRO-002 |
| Options & Derivatives | 2 | OPT-001, OPT-002 |
| Crypto & Digital Assets | 1 | CRYPTO-001 |
| Compliance & Regulatory | 1 | COMP-001 |
| Adaptive Learning | 2 | ADAPT-001, ADAPT-002 |
| Multi-Agent Coordination | 2 | AGENT-001, AGENT-002 |
| Performance Analytics | 2 | PERF-001, PERF-002 |
| Infrastructure & DevOps | 3 | INFRA-001 to INFRA-003 |
| **TOTAL** | **56** | |

---

> **This document serves as the master blueprint for building a complete, intelligent stock market trading agent system. Each skill defines precise inputs, outputs, capabilities, and implementation details. The 56 skills across 20 categories ensure comprehensive coverage of every aspect of professional trading — from data acquisition through analysis, decision-making, execution, risk management, and continuous learning.**
