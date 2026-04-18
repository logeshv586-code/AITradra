# 🧠 AITradra — High-Conviction Market Intelligence Platform

> An autonomous, multi-agent AI framework designed for institutional-grade market analysis. AITradra observes global markets, filters noise through rigorous quantitative validation (Mythic Pipeline), and continuously improves its predictive logic via a 27-agent swarm.

## 🏗️ Intelligence Architecture (The 27-Agent Swarm)

AITradra operates on a multi-tiered, highly concurrent agent network orchestrated via a central logic loop (AXIOM V4). The system distributes tasks across four distinct operational tiers:

### 📡 Tier 1: v3 Edge Intelligence
Lightweight agents focused on real-time data ingestion, preprocessing, and immediate directional bias.
- **DataCollector**: Streams yFinance and crypto gateway data.
- **BlobStorage**: Manages high-frequency local state persistence.
- **UI API**: Internal interface for frontend state synchronization.

### 🧠 Tier 2: v4 Mythic Core
The heavy reasoning layer. These agents handle complex cross-asset correlation and long-sequence reasoning.
- **MythicOrchestrator**: The central "brain" that delegates to specialists.
- **QueryRouter**: Intelligently routes user queries to the most relevant sub-agent cluster.
- **Swarm Intelligence**: Aggregates output from all specialists into a unified verdict.

### 🛡️ Tier 3: High-Conviction Specialists
Specialized quantitative and qualitative nodes that provide "veto" power or confirmation for signals.
- **QuanticAnalysis (Vibe-AI)**: Computes **Smart Money Concepts (SMC)**, identifying Institutional Order Blocks and Fair Value Gaps (FVG).
- **TechnicalSpecialist**: Analyzes OHLCV patterns and momentum (SMA20/50, RSI).
- **RiskSpecialist**: Computes **VaR 95%**, Beta, Max Drawdown, and Stress Scenarios.
- **MacroSpecialist**: News sentiment, earnings signals, and sector rotation analysis.
- **Forecast / StrategyGen**: Predictive modeling and trade execution plan generation.

### 🔍 Tier 4: Research & Discovery
Deep scanning agents that look for outliers and alpha beyond the primary watchlist.
- **MarketRAG**: Retrieval-augmented generation over market historical archives.
- **NewsIntel / MCPNews**: Deep NLP analysis of global headlines and alternative data.
- **DeepResearch**: Long-form synthesis of sector trends and macro-economic shifts.

---

## ⚙️ Core Capabilities

### 1. Mythic Validation Pipeline (MVP)
Eliminates predictive noise. Before any signal is pushed to the UI, it passes through the "Mythic Consensus" scoring engine:
- **Technical (40%)**: SMA alignment, Volume ratios, and Momentum.
- **News/Sent (40%)**: NLP sentiment scores from 20+ global sources.
- **Social (20%)**: Sentiment trending across public financial forums.
- **Volume Filter**: High-volume "confirmations" apply a 1.2x conviction multiplier.

### 2. Quantitative Diagnostic Engine
Powered by **Vibe-Trading AI**, the platform executes institutional-grade simulations:
- **Monte Carlo Simulations**: Runs 10,000 parallel market iterations to visualize the probability distribution of returns.
- **Bootstrap Validation**: Executes 5,000 sampling tests to verify the statistical significance of identified trends.
- **Institutional SMC**: Identifies liquidity pools and fair-price imbalances used by top-tier funds.

### 3. Continuous Self-Improvement
The **AccuracyStore** background orchestrator continuously evaluates prediction outcomes against real price action (>24h lag). It grades agents individually, adjusting their "Influence Weight" in the Mythic Pipeline based on their verified real-world accuracy.

---

## 🧪 Tech Stack

- **Frontend**: React 19, Vite 8, Tailwind CSS v4, Lucide, Recharts.
- **Backend**: FastAPI (Python 3.12), APScheduler, Uvicorn.
- **AI Infrastructure**: LM Studio (Local Inference @ port 1234), NVIDIA NIM (Cloud Scaling).
- **Data & Quant**: Pandas-TA, NumPy, Scikit-learn (Simulations).
- **Memory**: Qdrant (Vector Store), SQLite (Accuracy Leaderboard), JSON Persistence.

## 🚀 Quick Start

1. **Backend**: `python main.py` (Starts 27-agent heartbeat and API Gateway).
2. **Frontend**: `cd ui && npm run dev`.
3. **Local LLM**: Load a reasoning model in LM Studio (1234) for private inference.

---

*AITradra: Institutional Intelligence, Democratized.*
