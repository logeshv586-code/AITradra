# 🧠 AXIOM — AI Trading Intelligence Platform

> Multi-agent AI system that observes, analyzes, and predicts global markets using Claude Flow architecture.

## Architecture

```
User → FastAPI Gateway → LangGraph Orchestrator → [6 Agents in parallel]
                                                    ├── DataAgent (yfinance)
                                                    ├── NewsAgent (RSS + sentiment)
                                                    ├── TrendAgent (RSI, MACD, BB)
                                                    ├── RiskAgent (VaR, Beta)
                                                    ├── MLAgent (LSTM + XGBoost)
                                                    └── SynthesisAgent (LLM CoT)
                                                         ↓
                                              Memory System + Self-Improvement
```

## Quick Start

### Frontend (Vite + React)
```bash
cd axiom/ui
npm install
npm run dev
# → http://localhost:5173
```

### Backend (FastAPI)
```bash
cd axiom
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn gateway.server:app --reload --port 8000
# → http://localhost:8000/docs
```

### Docker (Full Stack)
```bash
cd axiom
docker compose up -d
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | System health check |
| `GET` | `/api/analyze/{ticker}` | Full multi-agent analysis |
| `GET` | `/api/market/overview` | Global market overview |
| `GET` | `/api/agents/status` | Agent matrix health |
| `GET` | `/api/memory/predictions/{ticker}` | Past predictions |
| `WS` | `/ws/analyze/{ticker}` | Real-time agent thinking stream |

## Core Principles

1. **Every prediction has a reason** — no black boxes
2. **Every agent has a clear role** — OBSERVE → THINK → PLAN → ACT → REFLECT → IMPROVE
3. **Memory is intelligence** — episodic + semantic + structured
4. **Self-improvement is priority** — automatic prediction scoring + prompt optimization
5. **Failure is data** — log everything, learn from everything

## Tech Stack

- **Frontend**: Vite + React + Tailwind CSS + Recharts + Lucide Icons
- **Backend**: FastAPI + Python 3.11+
- **LLM**: Ollama (local) with Qwen2.5
- **Memory**: SQLite → PostgreSQL + ChromaDB (vector store)
- **ML**: XGBoost + LSTM (PyTorch)
- **Orchestration**: LangGraph StateGraph
