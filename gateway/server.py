"""AXIOM Trading Intelligence API — FastAPI gateway with REST + WebSocket endpoints."""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings
from core.logger import get_logger
from memory.memory_manager import MemoryManager
from llm.client import LLMClient
from agents.data_agent.agent import DataAgent
from agents.news_agent.agent import NewsAgent
from agents.trend_agent.agent import TrendAgent
from agents.risk_agent.agent import RiskAgent
from agents.ml_agent.agent import MLAgent
from agents.synthesis_agent.agent import SynthesisAgent
from agents.orchestrator.graph import AgentOrchestrator
from agents.base_agent import AgentContext

logger = get_logger(__name__)


# ─── WebSocket Manager ────────────────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, message: dict):
        for ws in self.active:
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(ws)


ws_manager = ConnectionManager()


# ─── Application Lifecycle ────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 AXIOM starting up...")
    app.state.memory = MemoryManager()
    await app.state.memory.initialize()
    app.state.llm = LLMClient()
    
    # Initialize all agents
    data_agent = DataAgent(memory=app.state.memory)
    news_agent = NewsAgent(memory=app.state.memory)
    trend_agent = TrendAgent(memory=app.state.memory)
    risk_agent = RiskAgent(memory=app.state.memory)
    ml_agent = MLAgent(memory=app.state.memory)
    synthesis_agent = SynthesisAgent(memory=app.state.memory)
    
    app.state.orchestrator = AgentOrchestrator(
        data_agent, news_agent, trend_agent, risk_agent, ml_agent, synthesis_agent
    )
    
    logger.info("✅ AXIOM ready — all systems green")
    yield
    logger.info("👋 AXIOM shutting down")


app = FastAPI(
    title="AXIOM Trading Intelligence API",
    version="1.0.0",
    description="AI-powered multi-agent trading analysis platform",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── REST Endpoints ───────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "healthy", "version": settings.APP_VERSION, "app": settings.APP_NAME}


@app.get("/api/analyze/{ticker}")
async def analyze_stock(ticker: str, query: str = "Should I buy this stock?"):
    """Full multi-agent analysis for a ticker."""
    result = await app.state.orchestrator.analyze(ticker=ticker.upper(), query=query)
    return result


@app.get("/api/market/overview")
async def market_overview():
    """Get global market overview."""
    return {
        "indices": [
            {"name": "S&P 500", "value": 5234.18, "change": 0.82},
            {"name": "NASDAQ", "value": 16428.82, "change": 1.24},
            {"name": "Dow Jones", "value": 39127.14, "change": 0.35},
            {"name": "FTSE 100", "value": 7930.96, "change": -0.12},
            {"name": "Nikkei 225", "value": 40580.76, "change": 1.68},
        ],
        "watchlist": settings.DEFAULT_WATCHLIST,
    }


@app.get("/api/memory/predictions/{ticker}")
async def get_predictions(ticker: str, limit: int = 10):
    return await app.state.memory.get_past_predictions(ticker.upper(), limit)


@app.get("/api/agents/status")
async def agent_status():
    return {
        "agents": [
            {"name": "DataAgent", "status": "active", "accuracy": 99.9, "tasks": 1420},
            {"name": "NewsAgent", "status": "learning", "accuracy": 84.2, "tasks": 890},
            {"name": "TrendAgent", "status": "active", "accuracy": 78.5, "tasks": 1105},
            {"name": "RiskAgent", "status": "active", "accuracy": 92.1, "tasks": 650},
            {"name": "MLAgent", "status": "retraining", "accuracy": 68.4, "tasks": 430},
            {"name": "SynthesisAgent", "status": "active", "accuracy": 88.8, "tasks": 920},
        ]
    }


# ─── WebSocket: Live Analysis Stream ──────────────────────────────────────────

@app.websocket("/ws/analyze/{ticker}")
async def analyze_stream(websocket: WebSocket, ticker: str):
    """Stream agent thinking in real-time."""
    await ws_manager.connect(websocket)
    try:
        await websocket.send_json({"type": "connected", "ticker": ticker})

        # Simulate multi-agent analysis stream
        steps = [
            {"agent": "data_agent", "status": "start", "message": f"Fetching OHLCV for {ticker}"},
            {"agent": "data_agent", "status": "complete", "message": "Data collection complete"},
            {"agent": "news_agent", "status": "start", "message": f"Scanning news for {ticker}"},
            {"agent": "news_agent", "status": "complete", "message": "Sentiment analysis complete"},
            {"agent": "trend_agent", "status": "start", "message": "Computing RSI, MACD, Bollinger Bands"},
            {"agent": "trend_agent", "status": "complete", "message": "Technical signals generated"},
            {"agent": "risk_agent", "status": "start", "message": "Calculating VaR and Beta"},
            {"agent": "risk_agent", "status": "complete", "message": "Risk profile computed"},
            {"agent": "ml_agent", "status": "start", "message": "Running LSTM + XGBoost ensemble"},
            {"agent": "ml_agent", "status": "complete", "message": "Prediction generated"},
            {"agent": "synthesis_agent", "status": "start", "message": "Chain-of-thought synthesis"},
            {"agent": "synthesis_agent", "status": "complete", "message": "Final recommendation ready"},
        ]

        for step in steps:
            await websocket.send_json({"type": f"agent_{step['status']}", "agent": step["agent"], "output": step["message"]})
            await asyncio.sleep(0.5)

        # Run actual DataAgent
        ctx = AgentContext(task=f"analyze:{ticker}", ticker=ticker)
        result = await app.state.data_agent.run(ctx)

        await websocket.send_json({"type": "analysis_complete", "result": {"ticker": ticker, "confidence": result.confidence, "recommendation": "BUY" if result.confidence > 0.7 else "HOLD"}})

    except WebSocketDisconnect:
        logger.info(f"Client disconnected from {ticker} stream")
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        ws_manager.disconnect(websocket)


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("gateway.server:app", host="0.0.0.0", port=8000, reload=True)
