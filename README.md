# 🧠 AITradra — High-Conviction Market Intelligence Platform

> An autonomous, multi-agent AI system designed for institutional-grade market analysis. AITradra observes global markets, filters noise through rigorous quantitative validation (Mythic Pipeline), and continuously improves its predictive logic.

## 🏗️ Architecture

AITradra operates on a highly concurrent, dynamic agent network orchestrated via a central logic loop, supported by a self-improving memory architecture:

```
User Interface (React/Vite) 
        ↓ 
FastAPI Gateway Endpoint
        ↓
Model Router (Dynamic Provider Switching: LM Studio ↔ NVIDIA NIM)
        ↓
Agent Orchestrator (14+ Specialist Agents)
  ├── 📡 Data Sources: yFinance, RSS, News Agents
  ├── 🧠 Intelligence: Sentiment Classifier, Macro Analyst, Trend Agent
  ├── 🛡️ Validation: Mythic Pipeline (SMC, Monte Carlo, Bootstrap)
  └── 🗣️ Interface: AI Expert Chat (Direct User Interaction)
        ↓
Prediction Memory & Self-Improvement Loop (AccuracyStore)
```

## 🚀 Quick Start

### 1. Frontend (Vite + React)
```bash
cd ui
npm install
npm run dev
# → http://localhost:5173
```

### 2. Backend (FastAPI)
```bash
# Return to the root directory
pip install -r requirements.txt
cp .env.example .env

# Start the Gateway Server
python -m uvicorn gateway.server:app --reload --port 8000
# → http://localhost:8000/docs
```

### 3. Local Model Setup (LM Studio)
AITradra is configured for unparalleled privacy via Local LLMs. You will need:
- An instance of [LM Studio](https://lmstudio.ai/) running locally on port `1234`.
- The primary reasoning model loaded (e.g., `Qwen2.5-3B-Instruct/Nemotron`).
- *Note: You can place your `.gguf` weights in the `models/` directory.*

## 🔌 Core API Endpoints

AITradra exposes several critical REST and WebSocket endpoints defining the intelligence network:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/analyze/{ticker}` | Runs the complete high-conviction analysis pipeline |
| `GET` | `/api/market/overview` | Scans for trending tickers and general market state |
| `POST` | `/api/chat` | Interacts dynamically with the Agent Network via the Chat UI |
| `GET` | `/api/intelligence/status` | Real-time telemetry on active models, agent latency, and learning loops |
| `GET` | `/api/admin/accuracy-leaderboard` | View aggregate prediction accuracies across models and tickers |
| `POST` | `/api/admin/force-score-predictions` | Manually triggers the engine to score matured market predictions |
| `WS` | `/ws/analyze/{ticker}` | Live, streaming WebSocket connection of agent thoughts |

## ⚙️ Core Capabilities

1. **Mythic Validation Pipeline**: Eliminates predictive noise. Before any signal is pushed to the UI, it passes through Monte Carlo simulations, Bootstrap tests, and Smart Money Concepts (SMC) filters to ensure institutional-grade conviction.
2. **Dynamic LLM Routing**: Intelligently switches inference models mid-flight based on latency and failure states. Automatically falls back to secondary API providers if the local LM Studio instance is burdened.
3. **Continuous Self-Improvement**: Stores rolling, aggregate prediction metadata (AccuracyStore). A background orchestrator continuously checks the actual market price against predictions >24h old, grading the pipeline components and models on real-world accuracy.
4. **Vite Code Splitting**: The User Interface is extremely lightweight, deferring massive graphical libraries (like Three.js and React-Globe) into dynamic vendor chunks to maintain 60FPS UI interactions.

## 🛠️ Tech Stack

- **Frontend**: React 19, Vite 8, Tailwind CSS v4, Recharts, Three.js / React-Globe, Lucide
- **Backend**: FastAPI, Python 3.12, APScheduler
- **AI Infrastructure**: LM Studio (Local Inference), LangGraph concepts, ReAct Query Routing
- **Persistence**: SQLite (AccuracyStore / Memory), Local JSON States for high-IO persistence
- **Quantitative**: Pandas-TA, Numpy, Scikit-learn (Simulations & Bootstrapping)
