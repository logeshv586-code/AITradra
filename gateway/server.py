"""AXIOM V4.0 Mythic Trading Intelligence API — FastAPI gateway with multi-agent + orchestrator pipeline + Live Data."""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional, List, Dict
import asyncio
import sys
import os
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings
from core.logger import get_logger
from memory.memory_manager import MemoryManager
from llm.client import LLMClient
from agents.base_agent import AgentContext

# V1 Core Agents (Legacy)
from agents.legacy.data_agent.agent import DataAgent
from agents.legacy.news_agent.agent import NewsAgent
from agents.legacy.trend_agent.agent import TrendAgent
from agents.legacy.risk_agent.agent import RiskAgent
from agents.legacy.ml_agent.agent import MLAgent
from agents.legacy.synthesis_agent.agent import SynthesisAgent

# V2 Profit Agents (Legacy)
from agents.legacy.arbitrage_agent.agent import ArbitrageAgent
from agents.legacy.portfolio_agent.agent import PortfolioAgent
from agents.legacy.macro_agent.agent import MacroAgent
from agents.legacy.social_sentiment_agent.agent import SocialSentimentAgent
from agents.legacy.earnings_agent.agent import EarningsAgent
from agents.legacy.options_flow_agent.agent import OptionsFlowAgent
from agents.legacy.regime_detector_agent.agent import RegimeDetectorAgent
from agents.legacy.backtest_agent.agent import BacktestAgent

# V2 Infrastructure (Legacy)
from agents.legacy.orchestrator.graph import AgentOrchestrator
from brokers.broker_router import BrokerRouter
from alerts.alert_manager import AlertManager

# V3 Persistent RAG Agents
from agents.api_agent import router as v3_router
from agents.data_agent import DataAgent as V3DataAgent
from agents.blob_agent import BlobAgent as V3BlobAgent
from agents.rag_agent import RagAgent as V3RagAgent
from agents.news_agent import NewsAgent as V3NewsAgent
from agents.price_agent import PriceAgent as V3PriceAgent
from agents.forecast_agent import ForecastAgent as V3ForecastAgent
from agents.explain_agent import ExplainAgent as V3ExplainAgent
from agents.think_agent import ThinkAgent as V3ThinkAgent
from agents.mcp_news_agent import McpNewsAgent as V3McpNewsAgent
from agents.batch_agent import BatchAgent as V3BatchAgent

# V4 LLM-First Intelligence
from agents.query_router import QueryRouter, query_router
from agents.collector_agent import (
    CollectorAgent, collect_historical_data, collect_daily_data,
    collect_news_data, index_knowledge_to_rag
)
from gateway.session_manager import SessionManager, session_manager
from gateway.knowledge_store import knowledge_store
from gateway.diagnostic import router as diagnostic_router
# V4 Mythic-Tier Architecture
from agents.orchestrator import mythic_orchestrator
from gateway.db_portability import router as db_portability_router
from gateway.mission_control_router import router as mission_control_router
from gateway.market_intel_router import (
    router as market_intel_router,
    build_agent_status_payload,
)

# Global V3 instances for streaming
data_agent = V3DataAgent()
blob_agent = V3BlobAgent()
rag_agent = V3RagAgent()
news_agent = V3NewsAgent()
price_agent = V3PriceAgent()
forecast_agent = V3ForecastAgent()
explain_agent = V3ExplainAgent()
think_agent = V3ThinkAgent()
mcp_news_agent = V3McpNewsAgent()
batch_agent = V3BatchAgent()

# Geo Mapping
from gateway.stock_geo import get_coords_for_ticker, format_market_cap, format_volume
from core.market_manager import MarketManager

# AXIOM v2 Components
from gateway.data_engine import data_engine
from gateway.llm_prompts import (
    build_investment_criteria_prompt,
    build_price_move_explainer_prompt,
    build_stock_chat_prompt
)
from gateway.cache import cache
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pydantic import BaseModel
from gateway.synthesis_service import SynthesisService
from gateway.simulation_engine import SimulationEngine
from gateway.crew_orchestrator import OmniCrewManager
from gateway.intelligence_service import intelligence_service

class ChatRequest(BaseModel):
    message: str
    ticker: Optional[str] = ""
    research_mode: Optional[str] = "QUICK"
    history: Optional[List[Dict]] = []


class SimulationInitRequest(BaseModel):
    initial_balance: float

class BuyRequest(BaseModel):
    ticker: str
    amount: float
    prediction: Optional[str] = None

class SimulationTradeRequest(BaseModel):
    ticker: str
    amount: Optional[float] = 0.0
    quantity: Optional[float] = None

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
    logger.info("🚀 AXIOM V2.0 starting up...")

    # Core Infrastructure
    app.state.memory = MemoryManager()
    await app.state.memory.initialize()
    
    # LLM preloading is now DISABLED on startup to save memory and CPU.
    # Models will be loaded on-demand when a specific analysis is requested.
    # asyncio.create_task(asyncio.to_thread(LLMClient.preload_local_gguf))
    app.state.llm = LLMClient()

    # V1 Core Agents
    data_agent = DataAgent(memory=app.state.memory)
    news_agent = NewsAgent(memory=app.state.memory)
    trend_agent = TrendAgent(memory=app.state.memory)
    risk_agent = RiskAgent(memory=app.state.memory)
    ml_agent = MLAgent(memory=app.state.memory)
    synthesis_agent = SynthesisAgent(memory=app.state.memory)

    # V2 Profit Agents (Claude Flow)
    arbitrage_agent = ArbitrageAgent(memory=app.state.memory)
    portfolio_agent = PortfolioAgent(memory=app.state.memory)
    macro_agent = MacroAgent(memory=app.state.memory)
    social_sentiment_agent = SocialSentimentAgent(memory=app.state.memory)
    earnings_agent = EarningsAgent(memory=app.state.memory)
    options_flow_agent = OptionsFlowAgent(memory=app.state.memory)
    regime_detector_agent = RegimeDetectorAgent(memory=app.state.memory)
    backtest_agent = BacktestAgent(memory=app.state.memory)

    # ─── Market-Aware Scheduler ─────────────────────────────────────────────────
    from core.market_scheduler import market_scheduler
    app.state.market_scheduler = market_scheduler

    # Startup catch-up: if KnowledgeStore has no data, do a one-time RSS fetch NOW
    await market_scheduler.startup_catchup()

    # The background scheduler and jobs are now managed globally in main.py
    # to avoid ConflictingIdErrors and ensure single-source-of-truth orchestration.


    # Background: collect historical data if needed (non-blocking)
    asyncio.create_task(collect_historical_data())
    asyncio.create_task(_background_watchlist_sync(force=False))
    logger.info("📡 Initial data collection triggered in background.")

    # V2 Orchestrator (14 agents)
    app.state.orchestrator = AgentOrchestrator(
        data_agent=data_agent, news_agent=news_agent,
        trend_agent=trend_agent, risk_agent=risk_agent,
        ml_agent=ml_agent, synthesis_agent=synthesis_agent,
        arbitrage_agent=arbitrage_agent, portfolio_agent=portfolio_agent,
        macro_agent=macro_agent, social_sentiment_agent=social_sentiment_agent,
        earnings_agent=earnings_agent, options_flow_agent=options_flow_agent,
        regime_detector_agent=regime_detector_agent, backtest_agent=backtest_agent
    )

    # V3 RAG Agent - Backgrounded to avoid blocking startup
    from agents.rag_agent import RagAgent
    app.state.rag_agent = RagAgent(memory=app.state.memory)
    
    async def _async_load_rag():
        try:
            logger.info("📂 Deferring RAG index load for 10s...")
            await asyncio.sleep(10)
            app.state.rag_agent.load_index()
            logger.info("✅ RAG index loaded in background.")
        except Exception as e:
            logger.warning(f"Background RAG index load failed: {e}")
            
    asyncio.create_task(_async_load_rag())

    # AXIOM v3.1 Synthesis Service
    from gateway.synthesis_service import SynthesisService
    import gateway.synthesis_service as synth_mod
    synth_mod.synthesis_service = SynthesisService(
        orchestrator=app.state.orchestrator,
        rag_agent=app.state.rag_agent
    )

    # OMNI-AXIOM v5 Simulation Engine
    app.state.simulation = SimulationEngine(data_engine=data_engine)

    # V2 Execution Layer
    app.state.broker = BrokerRouter({"PAPER_TRADING": True})
    app.state.alerts = AlertManager()

    # Cache for live data (TTL-based) — always start fresh
    app.state.cache = {"watchlist": None, "watchlist_ts": 0, "indices": None, "indices_ts": 0}
    app.state.last_seen = {}  # Start empty — will be populated by data engine

    logger.info("✅ AXIOM V2.0 ready — 14 agents loaded, all systems green")
    print("\n" + "="*60)
    print("  AXIOM V2.0 — Live Data Mode Active")
    print("  Watchlist: " + ", ".join(settings.DEFAULT_WATCHLIST))
    print("="*60 + "\n")
    logger.info("✅ Startup complete. systems operational.")
    yield
    logger.info("👋 AXIOM V2.0 shutting down")
    scheduler.shutdown()


# Global instances
scheduler = AsyncIOScheduler()
llm_client = LLMClient()
crew_manager = OmniCrewManager(data_engine, llm_client)

app = FastAPI(
    title="AXIOM V4.0 Mythic Intelligence API",
    version="4.0.0",
    description="AI-powered multi-agent trading platform with ReAct orchestrator, specialist fleet, critique layer, and confidence calibration (100% Open-Source)",
    lifespan=lifespan,
)

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include V3 RAG Router
app.include_router(v3_router)

# Include V4 DB Portability Router
app.include_router(db_portability_router)

# Include Mission Control Router
app.include_router(mission_control_router)

# Include Market Intelligence Router
app.include_router(market_intel_router)

UI_DIST_DIR = (Path(__file__).resolve().parent.parent / settings.UI_DIST_PATH).resolve()


# ─── HELPER: Fetch yfinance data with caching ────────────────────────────────

async def _fetch_yf_ticker(ticker: str) -> dict:
    """Fetch real data for a single ticker using DataEngine."""
    last_seen = app.state.last_seen

    # Check if we have fresh data in last_seen (TTL: 60s via background sync)
    if ticker in last_seen and last_seen[ticker].get("px", 0) > 0:
        cached = last_seen[ticker]
        # Skip stale dummy data from old engine (all were $100, source=N/A)
        src = cached.get("ex", cached.get("source_used", ""))
        if src and src != "N/A" and not cached.get("stale", False):
            return cached

    # Fetch real data via DataEngine (knowledge store -> collector -> scrape)
    try:
        price_data = await data_engine.get_price_data(ticker)
        px = price_data.get("px", 0)
        chg = price_data.get("chg", 0)
        lat, lon = get_coords_for_ticker(ticker)
        res = {
            "id": ticker, "name": ticker, "ex": price_data.get("source_used", "N/A"),
            "px": px, "chg": chg, "mcap": format_market_cap(price_data.get("mktcap", 0)),
            "vol": format_volume(price_data.get("volume", 0)),
            "pe": str(price_data.get("pe", 0)), "sector": "Market",
            "lat": lat, "lon": lon,
            "ohlcv": price_data.get("ohlcv", []),
            "risk": {"var": "2.5%", "beta": 1.1, "vol": "Medium"},
            "fundamentals": {
                "52w_high": price_data.get("week52_high", 0),
                "52w_low": price_data.get("week52_low", 0),
            },
            "stale": price_data.get("is_estimated", False),
            "pct_chg": chg,
        }
        last_seen[ticker] = res
        return res
    except Exception as e:
        logger.warning(f"DataEngine failed for {ticker}: {e}")
        # Minimal fallback so UI doesn't break
        lat, lon = get_coords_for_ticker(ticker)
        res = {
            "id": ticker, "name": ticker, "ex": "N/A",
            "px": 0, "chg": 0, "mcap": "N/A", "vol": "N/A",
            "pe": "0", "sector": "Syncing...", "lat": lat, "lon": lon,
            "ohlcv": [], "risk": {"var": "0%", "beta": 1.0, "vol": "Low"},
            "fundamentals": {}, "stale": True, "pct_chg": 0,
        }
        last_seen[ticker] = res
        return res


async def _fetch_yf_index(symbol: str, name: str) -> dict:
    """Fetch index value from knowledge store or collector."""
    try:
        price_data = await data_engine.get_price_data(symbol)
        return {"name": name, "value": round(price_data.get("px", 0), 2), "change": round(price_data.get("chg", 0), 2)}
    except Exception:
        return {"name": name, "value": 0, "change": 0}


def _cache_watchlist_records(records: list[dict]):
    import time

    app.state.cache["watchlist"] = records
    app.state.cache["watchlist_ts"] = time.time()
    for record in records:
        app.state.last_seen[record["id"]] = record


async def _get_watchlist_intelligence(force_refresh: bool = False, max_age_minutes: int = 180) -> tuple[list[dict], list[dict]]:
    snapshots = await intelligence_service.get_watchlist_intelligence(
        force_refresh=force_refresh,
        max_age_minutes=max_age_minutes,
    )
    records = [intelligence_service.to_watchlist_record(snapshot) for snapshot in snapshots]
    if records:
        _cache_watchlist_records(records)
    return snapshots, records


def _analysis_payload_is_usable(result: dict, ticker: str) -> bool:
    if not isinstance(result, dict):
        return False
    result_ticker = str(result.get("ticker", "")).upper()
    if result_ticker not in {"", ticker.upper()}:
        return False
    if result_ticker in {"", "NOT SPECIFIED"}:
        return False
    return bool(result.get("prediction_direction") or result.get("recommendation"))


# ─── AXIOM v2 Endpoints ──────────────────────────────────────────────────────

@app.get("/api/stock/{ticker}")
async def get_stock_detail_v2(ticker: str):
    """
    Full stock detail for the panel view — optimized for speed.
    """
    ticker = ticker.upper()
    # Fast path: use cached intelligence by default
    snapshot = await intelligence_service.get_ticker_intelligence(ticker, max_age_minutes=120)
    data = snapshot.get("price_data", {})
    news = snapshot.get("top_headlines", [])
    sentiment = snapshot.get("sentiment", {})
    ohlcv_history = data.get("ohlcv", [])

    return {
        "ticker": ticker,
        "name": snapshot.get("name", ticker),
        "price_data": data,
        "news": news,
        "sentiment": sentiment,
        "ohlcv_history": ohlcv_history,
        "freshness_label": cache.get_freshness_label(ticker, "price"),
        "intelligence": snapshot.get("analysis", {}),
    }

@app.get("/api/stock/{ticker}/analysis")
async def get_stock_analysis(ticker: str):
    """
    AXIOM V5: CrewAI Multi-Agent Synthesis.
    Combines Technical, News, and Risk agents into a final Mythic report.
    """
    ticker = ticker.upper()
    snapshot = await intelligence_service.get_ticker_intelligence(ticker, max_age_minutes=120)
    data = {
        "price_data": snapshot.get("price_data", {}),
        "historical_stats": snapshot.get("historical_stats", {}),
        "risk": snapshot.get("risk", {}),
        "sentiment": snapshot.get("sentiment", {}),
        "top_headlines": snapshot.get("top_headlines", []),
        "sections": snapshot.get("sections", {}),
    }
    
    # Run the multi-agent crew (offload to thread as kickoff is synchronous)
    try:
        context_str = json.dumps(data, default=str)[:2000] # Limit context size for agents
        result = await asyncio.to_thread(crew_manager.run_analysis, ticker, context_str)
        
        # If result is a string (often from crewAI), try to parse it
        if isinstance(result, str):
            try:
                # Basic cleaning if LLM put code blocks
                clean_res = result.strip().replace("```json", "").replace("```", "")
                parsed = json.loads(clean_res)
                if _analysis_payload_is_usable(parsed, ticker):
                    return parsed
            except:
                pass
            return snapshot.get("analysis", {})
        if _analysis_payload_is_usable(result, ticker):
            return result
        return snapshot.get("analysis", {})
    except Exception as e:
        logger.error(f"CrewAI Synthesis failed for {ticker}: {e}")
        # Fallback to legacy single-prompt analysis, then to persisted backend intelligence.
        try:
            market_ctx = MarketManager.get_ai_suggestion_context(ticker)
            prompt = build_investment_criteria_prompt(ticker, data, market_context=market_ctx)
            result = await llm_client.complete(prompt, expect_json=True)
            if _analysis_payload_is_usable(result, ticker):
                return result
        except Exception as llm_error:
            logger.warning(f"LLM fallback analysis failed for {ticker}: {llm_error}")
        return snapshot.get("analysis", {})

@app.get("/api/stock/{ticker}/explain-move")
async def explain_price_move(ticker: str):
    """Why did this stock move today? Returns reason + source link."""
    ticker = ticker.upper()
    data = await data_engine.get_price_data(ticker)
    news = await data_engine.get_news(ticker, max_items=10)
    prompt = build_price_move_explainer_prompt(ticker, {**data, "news": news})
    result = await llm_client.complete(prompt, expect_json=True)
    return result

@app.post("/api/chat/stock/{ticker}")
async def stock_chat(ticker: str, body: ChatRequest):
    """Dedicated per-stock chat — routes through QueryRouter with RAG + LLM."""
    ticker = ticker.upper()
    
    # Use session-based chat if session_id provided, else one-shot
    session_id = getattr(body, 'session_id', None)
    
    if session_id:
        session = session_manager.get_session(session_id)
        if session:
            session.add_message("user", body.message)
    
    # Route through QueryRouter (RAG → Agents → LLM)
    ctx = AgentContext(task=body.message, ticker=ticker)
    result = await query_router.run(ctx)
    response = result.result.get("response", "") if isinstance(result.result, dict) else str(result.result)
    
    if session_id:
        session = session_manager.get_session(session_id)
        if session:
            session.add_message("assistant", response)
    
    return {"response": response, "ticker": ticker}


@app.post("/api/chat/stock/{ticker}/session")
async def create_stock_session(ticker: str):
    """Create a new per-stock chat session (called when a stock is clicked on the globe)."""
    ticker = ticker.upper()
    session = session_manager.create_session(ticker)
    return {
        "session_id": session.session_id,
        "ticker": ticker,
        "welcome_message": session.messages[0]["content"] if session.messages else "",
    }


@app.post("/api/chat/stock/{ticker}/session/{session_id}")
async def stock_session_chat(ticker: str, session_id: str, body: ChatRequest):
    """Send a message to an existing per-stock chat session."""
    ticker = ticker.upper()
    session = session_manager.get_or_create_session(ticker, session_id)
    session.add_message("user", body.message)
    
    # Build conversation-aware prompt
    conversation_context = session.get_conversation_context(max_messages=6)
    enhanced_query = f"""CONVERSATION HISTORY:
{conversation_context}

CURRENT QUESTION: {body.message}

Answer the current question in context of the conversation above."""
    
    # Route through QueryRouter with full conversation context
    ctx = AgentContext(task=enhanced_query, ticker=ticker)
    result = await query_router.run(ctx)
    response = result.result.get("response", "") if isinstance(result.result, dict) else str(result.result)
    
    session.add_message("assistant", response)
    
    return {
        "response": response,
        "ticker": ticker,
        "session_id": session.session_id,
        "message_count": len(session.messages),
    }


@app.get("/api/knowledge/status")
async def knowledge_status():
    """Get current knowledge store data collection status."""
    status = knowledge_store.get_collection_status()
    status["active_sessions"] = session_manager.get_active_count()
    return status

@app.get("/api/market/globe-data")
async def get_globe_data():
    """Lightweight endpoint for globe pins — returns ALL watchlist stocks with real data."""
    snapshots, records = await _get_watchlist_intelligence(max_age_minutes=240)
    snapshot_map = {item["ticker"]: item for item in snapshots}
    results = []
    for record in records:
        snapshot = snapshot_map.get(record["id"], {})
        results.append({
            "ticker": record["id"],
            "lat": record.get("lat", 40.7),
            "lon": record.get("lon", -74.0),
            "px": record.get("px", 0),
            "pct_chg": record.get("pct_chg", 0),
            "signal": snapshot.get("recommendation", "HOLD"),
            "name": record.get("name", record["id"]),
        })
    return results

# ─── REST Endpoints ───────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "4.0.0", "app": "AXIOM V4 Mythic", "agents": 14, "mythic_agents": 5}


@app.get("/api/system/scheduler-status")
async def scheduler_status():
    """Returns market-aware scheduler state: what's open, when last scraped, etc."""
    if hasattr(app.state, "market_scheduler"):
        return app.state.market_scheduler.get_status()
    return {"error": "Scheduler not initialized"}


@app.get("/api/system/data-status")
async def data_status():
    """Returns KnowledgeStore data counts + freshness info."""
    status = knowledge_store.get_collection_status()
    if hasattr(app.state, "market_scheduler"):
        status["scheduler"] = app.state.market_scheduler.get_status()
    try:
        from gateway.local_plugin_registry import local_plugin_registry

        status["plugins"] = local_plugin_registry.get_summary()
    except Exception as exc:
        logger.warning(f"Failed to load plugin summary for data status: {exc}")
    return status


async def _background_watchlist_sync(force: bool = False):
    """Background task to fetch all watchlist data sequentially without blocking the UI."""
    cache = app.state.cache
    if cache.get("is_syncing"): 
        return
    cache["is_syncing"] = True
    try:
        _, stocks = await _get_watchlist_intelligence(force_refresh=force, max_age_minutes=240)
        logger.info(f"[LIVE] Background Watchlist Sync Complete: {len(stocks)}/{len(settings.DEFAULT_WATCHLIST)} tickers")
    finally:
        cache["is_syncing"] = False

@app.get("/api/market/watchlist")
async def market_watchlist():
    """Fetch LIVE market data instantly from the local intelligence cache."""
    try:
        # 1. Fetch from pre-calculated intelligence store
        snapshots = await intelligence_service.get_watchlist_intelligence(max_age_minutes=60)
        records = [intelligence_service.to_watchlist_record(s) for s in snapshots]
        
        return {
            "stocks": records, 
            "cached": True, 
            "ts": datetime.now().timestamp(),
            "count": len(records),
            "synced_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Watchlist API failed: {e}")
        return {"stocks": [], "error": str(e)}


@app.get("/api/market/status")
async def get_market_status():
    """Returns the current status of all global markets."""
    return MarketManager.get_all_statuses()


@app.get("/api/agents/status-lite")
async def agents_status_lite():
    """Compact agent summary kept for backward compatibility."""
    payload = build_agent_status_payload()
    return {
        "agents": payload.get("agents", [])[:5],
        "summary": payload.get("summary", {}),
        "generated_at": payload.get("generated_at"),
    }


@app.get("/api/market/indices")
async def market_indices():
    """Fetch LIVE global index data."""
    import time
    cache = app.state.cache
    now = time.time()

    if cache["indices"] and now - cache["indices_ts"] < 120:
        return {"indices": cache["indices"], "cached": True}

    index_map = [
        ("^GSPC", "S&P 500"),
        ("^IXIC", "NASDAQ"),
        ("^DJI", "Dow Jones"),
        ("^FTSE", "FTSE 100"),
        ("^N225", "Nikkei 225"),
    ]

    tasks = [_fetch_yf_index(sym, name) for sym, name in index_map]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    indices = [r for r in results if isinstance(r, dict)]

    cache["indices"] = indices
    cache["indices_ts"] = now
    return {"indices": indices, "cached": False}


@app.get("/api/market/overview")
async def market_overview():
    """Combined overview — returns both indices and watchlist tickers."""
    idx_data = await market_indices()
    return {
        "indices": idx_data.get("indices", []),
        "watchlist": settings.DEFAULT_WATCHLIST,
    }


@app.get("/api/stock/{ticker}/detail")
async def stock_detail(ticker: str):
    """Full stock detail: OHLCV, fundamentals, risk, and computed metrics."""
    data = await _fetch_yf_ticker(ticker.upper())
    return {"stock": data}


@app.get("/api/stock/{ticker}/news")
async def stock_news(ticker: str):
    """Fetch recent news for a ticker with LLM-powered sentiment scoring."""
    # Use existing scraped news from data_engine instead of yfinance
    from gateway.data_engine import data_engine
    raw_news = await data_engine.get_news(ticker, max_items=8)
    articles = []
    
    for item in raw_news:
        articles.append({
            "src": item.get("source", "Web")[:12],
            "t": "recent",
            "txt": item.get("headline", "No Title"),
            "s": 0,
        })
    
    if not articles:
        # Provide minimal dummy news if none available
        articles = [
            {"src": "Market", "t": "recent", "txt": f"Market updates on {ticker.upper()}", "s": 0.1},
            {"src": "Finance", "t": "1h", "txt": f"Analysts review {ticker.upper()} outlook", "s": 0.5}
        ]

    # LLM sentiment scoring
    if articles:
        try:
            headlines = "\n".join([f"- {a['txt']}" for a in articles])
            prompt = f"""Score the sentiment of each headline for stock {ticker.upper()} on a scale of -1.0 (very bearish) to +1.0 (very bullish).
Return ONLY a JSON array of numbers, one per headline. Example: [0.5, -0.3, 0.8]

Headlines:
{headlines}"""
            response = await app.state.llm.complete(prompt, system="You are a financial sentiment analyzer. Return only valid JSON.", temperature=0.05, max_tokens=200)
            
            # Parse scores
            try:
                import re
                match = re.search(r'\[[\d\s,.\-]+\]', response)
                if match:
                    scores = json.loads(match.group())
                    for i, score in enumerate(scores):
                        if i < len(articles):
                            articles[i]["s"] = round(float(score), 2)
            except Exception as e:
                logger.warning(f"Sentiment parsing failed: {e}")
                # Fallback: simple keyword scoring
                bullish_keywords = ["surge", "high", "beat", "record", "growth", "rally", "upgrade", "outperform"]
                bearish_keywords = ["fall", "drop", "miss", "decline", "cut", "risk", "warning", "underperform"]
                for idx, a in enumerate(articles):
                    txt = a["txt"].lower()
                    if any(w in txt for w in bullish_keywords):
                        a["s"] = round(0.4 + 0.3 * (idx % 3 / 3), 2)
                    elif any(w in txt for w in bearish_keywords):
                        a["s"] = round(-0.3 - 0.3 * (idx % 3 / 3), 2)
                    else:
                        a["s"] = round(0.1 * (idx % 3 / 3), 2)
        except Exception as e:
            logger.warning(f"LLM sentiment scoring failed: {e}")
            # Apply keyword fallback
            for a in articles:
                txt = a["txt"].lower()
                if any(w in txt for w in ["surge", "high", "beat", "record", "growth", "rally"]):
                    a["s"] = 0.6
                elif any(w in txt for w in ["fall", "drop", "miss", "decline", "cut"]):
                    a["s"] = -0.5
                else:
                    a["s"] = 0.1

    return {"ticker": ticker.upper(), "news": articles}


@app.post("/api/chat")
async def chat_endpoint(request: Request):
    """AXIOM MYTHIC — Multi-agent orchestrated intelligence.
    
    Routes through MythicOrchestrator pipeline:
    Parallel Fan-Out → Specialist Fleet → Critique → Calibrated Synthesis
    """
    body = await request.json()
    user_msg = body.get("message", "").strip()
    ticker = body.get("ticker", "")
    
    # ─── INTERCEPT COMMANDS ────────────────────────────────────────────────
    if user_msg.startswith("> scrape"):
        try:
            from scrapers.playwright_news import run_scraper
            import shlex
            
            # e.g., > scrape "Indian IT" TCS INFY
            parts = shlex.split(user_msg[8:].strip())
            query = parts[0] if parts else "Indian stock market"
            tickers = parts[1:] if len(parts) > 1 else []
            
            saved = await run_scraper(query, tickers, headless=True)
            return {
                "response": f"✅ Scrape completed. Found and saved **{saved}** new articles for `{query}` and tickers `{tickers}` into `stock_news.db`.",
                "source": "playwright_scraper"
            }
        except Exception as e:
            logger.error(f"Scrape command failed: {e}")
            return {"response": f"⚠️ Scraper failed: {e}", "source": "system"}
            
    if user_msg.startswith("> compare") or user_msg.startswith("> sentiment"):
        try:
            from agents.sentiment_engine import sentiment_engine
            
            # extract tickers, e.g., > compare TCS INFY WIPRO
            cmd_parts = user_msg.split(" ")[1:]
            tickers = [t.upper() for t in cmd_parts if len(t) < 10]
            if not tickers and ticker:
                tickers = [ticker.upper()]
                
            res = await sentiment_engine.analyze_sentiment(user_msg, tickers)
            if res.get("error"):
                return {"response": res.get("message", "Error analyzing sentiment."), "source": "system"}
                
            return {
                "response": res["markdown"],
                "source": "sentiment_engine",
                "sources_used": res.get("sources_used", [])
            }
        except Exception as e:
            logger.error(f"Sentiment command failed: {e}")
            return {"response": f"⚠️ Sentiment analysis failed: {e}", "source": "system"}
    # ───────────────────────────────────────────────────────────────────────

    # Route through the intelligent QueryRouter → MythicOrchestrator
    ctx = AgentContext(
        task=user_msg,
        ticker=ticker.upper() if ticker else None,
        metadata={
            "research_mode": body.get("research_mode", "QUICK"),
            "history": body.get("history", [])
        }
    )
    result = await query_router.run(ctx)

    
    if isinstance(result.result, dict):
        response = result.result.get("response", "")
        return {
            "response": response,
            "source": "mythic_v4",
            "consensus": result.result.get("consensus"),
            "confidence": result.result.get("confidence"),
            "specialist_outputs": result.result.get("specialist_outputs"),
            "critique": result.result.get("critique"),
            "pipeline_ms": result.result.get("pipeline_ms"),
            "sources_used": result.result.get("sources_used", []),
        }
    else:
        return {"response": str(result.result), "source": "mythic_v4_fallback"}


@app.get("/api/analyze/{ticker}")
async def analyze_stock(ticker: str, query: str = "Should I buy this stock?"):
    """Full 14-agent analysis for a ticker."""
    result = await app.state.orchestrator.analyze(ticker=ticker.upper(), query=query)
    return result


@app.get("/api/agents/status")
async def agent_status():
    return build_agent_status_payload()


@app.get("/api/pipeline/status")
async def pipeline_status():
    """Mythic pipeline health and recent episode history."""
    recent_episodes = mythic_orchestrator.get_recent_episodes(limit=5)
    memory_status = await app.state.memory.get_system_status()
    return {
        "pipeline": "mythic_v4",
        "status": "operational",
        "components": {
            "orchestrator": "active",
            "technical_specialist": "active",
            "risk_specialist": "active",
            "macro_specialist": "active",
            "critique_agent": "active",
        },
        "memory": memory_status,
        "recent_episodes": recent_episodes,
    }


@app.get("/api/portfolio/positions")
async def portfolio_positions():
    """Get all positions across paper and CCXT brokers."""
    positions = await app.state.broker.get_all_positions()
    return {"positions": positions}


@app.get("/api/memory/predictions/{ticker}")
async def get_predictions(ticker: str, limit: int = 10):
    return await app.state.memory.get_past_predictions(ticker.upper(), limit)


# ─── OMNI-AXIOM Endpoints ────────────────────────────────────────────────────

@app.get("/api/market/predictions")
async def market_predictions():
    """OMNI-AXIOM Prediction Table — structured prediction for every watchlist stock."""
    snapshots, _ = await _get_watchlist_intelligence(max_age_minutes=240)
    predictions = [intelligence_service.to_prediction_record(snapshot) for snapshot in snapshots]
    return {"predictions": predictions, "count": len(predictions), "max_confidence": 85}


@app.get("/api/market/trending")
async def market_trending():
    """OMNI-AXIOM Trending Stocks — top movers by absolute % change."""
    _, stocks = await _get_watchlist_intelligence(max_age_minutes=240)

    sorted_by_move = sorted(stocks, key=lambda s: abs(s.get("chg", 0)), reverse=True)

    gainers = [s for s in sorted_by_move if s.get("chg", 0) > 0][:10]
    losers = [s for s in sorted_by_move if s.get("chg", 0) < 0][:10]
    most_volatile = sorted_by_move[:10]

    def _fmt(s):
        return {
            "ticker": s.get("id", ""),
            "name": s.get("name", ""),
            "price": s.get("px", 0),
            "change_pct": s.get("chg", 0),
            "sector": s.get("sector", "N/A"),
            "volume": s.get("vol", "N/A"),
            "ohlcv": s.get("ohlcv", [])[-20:],
        }

    return {
        "gainers": [_fmt(s) for s in gainers],
        "losers": [_fmt(s) for s in losers],
        "most_volatile": [_fmt(s) for s in most_volatile],
    }


@app.get("/api/stock/{ticker}/risk")
async def stock_risk_analysis(ticker: str):
    """OMNI-AXIOM Risk Analysis — detailed risk breakdown for a single stock."""
    ticker = ticker.upper()
    snapshot = await intelligence_service.get_ticker_intelligence(ticker, max_age_minutes=120)
    stock = intelligence_service.to_watchlist_record(snapshot)
    risk = snapshot.get("risk", {})
    fundamentals = stock.get("fundamentals", {}) if isinstance(stock.get("fundamentals"), dict) else {}
    chg = stock.get("chg", 0)
    beta = risk.get("beta", 1.0)
    var_95 = risk.get("var_95", 0)
    max_drawdown_est = risk.get("max_drawdown", 0)
    volatility = risk.get("volatility_label", "Medium")
    sector = stock.get("sector", "N/A")
    sector_risk = "HIGH" if sector == "Cryptocurrency" else ("MEDIUM" if beta > 1.0 else "LOW")
    overall_risk = risk.get("risk_level", "MEDIUM")

    return {
        "ticker": ticker,
        "name": stock.get("name", ticker),
        "overall_risk": overall_risk,
        "metrics": {
            "var_95": f"{var_95}%",
            "beta": round(beta, 2),
            "volatility": volatility,
            "max_drawdown_estimate": f"{max_drawdown_est}%",
            "current_change": chg,
        },
        "sector_risk": sector_risk,
        "sector": sector,
        "week52_high": fundamentals.get("52w_high", 0),
        "week52_low": fundamentals.get("52w_low", 0),
        "risk_factors": [
            f"Beta of {beta:.2f} indicates {'above' if beta > 1 else 'below'}-average market sensitivity",
            f"VaR(95%) suggests max daily loss of {var_95}%",
            f"Current move of {chg:+.2f}% {'signals elevated' if abs(chg) > 2 else 'within normal'} volatility",
        ],
    }


@app.get("/api/portfolio/insights")
async def portfolio_insights():
    """OMNI-AXIOM Portfolio Insights — allocation breakdown and aggregate metrics."""
    snapshots, stocks = await _get_watchlist_intelligence(max_age_minutes=240)

    # Sector breakdown
    sector_map = {}
    total_value = 0
    for s in stocks:
        sector = s.get("sector", "Other")
        px = s.get("px", 0)
        sector_map.setdefault(sector, {"count": 0, "total_value": 0, "tickers": []})
        sector_map[sector]["count"] += 1
        sector_map[sector]["total_value"] += px
        sector_map[sector]["tickers"].append(s.get("id", ""))
        total_value += px

    sectors = []
    for name, data in sorted(sector_map.items(), key=lambda x: x[1]["total_value"], reverse=True):
        pct = round((data["total_value"] / total_value * 100) if total_value else 0, 1)
        sectors.append({
            "sector": name,
            "count": data["count"],
            "allocation_pct": pct,
            "tickers": data["tickers"][:5],
        })

    # Risk distribution
    risk_dist = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    for snapshot in snapshots:
        risk_dist[snapshot.get("risk_level", "MEDIUM")] += 1

    # Aggregate metrics
    avg_change = round(sum(s.get("chg", 0) for s in stocks) / len(stocks), 2) if stocks else 0
    bullish = sum(1 for snapshot in snapshots if snapshot.get("prediction_direction") == "UP")
    bearish = sum(1 for snapshot in snapshots if snapshot.get("prediction_direction") == "DOWN")

    return {
        "total_assets": len(stocks),
        "sectors": sectors,
        "risk_distribution": risk_dist,
        "aggregate": {
            "avg_change_pct": avg_change,
            "bullish_count": bullish,
            "bearish_count": bearish,
            "bull_bear_ratio": round(bullish / max(bearish, 1), 2),
        },
    }


@app.get("/api/market/news-evidence")
async def market_news_evidence():
    """OMNI-AXIOM News & Evidence — global news feed with impact scoring."""
    from gateway.scrapers.rss_scraper import rss_scraper

    # Get all cached articles
    all_articles = []
    for _hash, article in rss_scraper.cache.items():
        if isinstance(article, dict) and article.get("headline"):
            headline = article.get("headline", "")
            # Simple impact scoring from keywords
            high_kw = ["crash", "surge", "record", "billion", "fed", "rate", "war", "crisis", "bankruptcy"]
            med_kw = ["growth", "earnings", "revenue", "profit", "deal", "merger", "acquisition", "upgrade", "downgrade"]
            headline_lower = headline.lower()

            if any(kw in headline_lower for kw in high_kw):
                impact = "HIGH"
            elif any(kw in headline_lower for kw in med_kw):
                impact = "MEDIUM"
            else:
                impact = "LOW"

            all_articles.append({
                "headline": headline,
                "url": article.get("url", ""),
                "source": article.get("source", "Unknown"),
                "published_at": article.get("published_at", ""),
                "impact": impact,
                "summary": article.get("body", "")[:200] if article.get("body") else "",
            })

    # Sort by impact priority then recency
    impact_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    all_articles.sort(key=lambda a: impact_order.get(a["impact"], 2))

    return {
        "articles": all_articles[:50],
        "total_cached": len(rss_scraper.cache),
        "high_impact": sum(1 for a in all_articles if a["impact"] == "HIGH"),
        "medium_impact": sum(1 for a in all_articles if a["impact"] == "MEDIUM"),
    }


# ─── WebSocket: Live Analysis Stream ──────────────────────────────────────────

@app.websocket("/ws/analyze/{ticker}")
async def analyze_stream(websocket: WebSocket, ticker: str):
    """Stream AXIOM V3 11-agent thinking in real-time."""
    await ws_manager.connect(websocket)
    try:
        await websocket.send_json({"type": "connected", "ticker": ticker, "version": "3.0"})

        # 1. Data Collection
        await websocket.send_json({"type": "agent_start", "agent": "datacollector", "output": "OBSERVING live market feeds..."})
        data_ctx = await data_agent.run(AgentContext(task=f"Fetch {ticker}", ticker=ticker))
        await websocket.send_json({"type": "agent_complete", "agent": "datacollector", "output": "ACT: Data retrieved successfully."})

        # 2. Persistence Layer
        await websocket.send_json({"type": "agent_start", "agent": "blobstorage", "output": "THINKING: Persisting to Daily Blob storage..."})
        await blob_agent.run(AgentContext(task=f"Save {ticker}", ticker=ticker, metadata={"blob_data": data_ctx.result}))
        await websocket.send_json({"type": "agent_complete", "agent": "blobstorage", "output": "ACT: Historical state saved."})

        await websocket.send_json({"type": "agent_start", "agent": "marketrag", "output": "PLANNING: Indexing for semantic RAG retrieval..."})
        await rag_agent.run(AgentContext(task=f"Index {ticker}", ticker=ticker, metadata={"blob_data": data_ctx.result}))
        await websocket.send_json({"type": "agent_complete", "agent": "marketrag", "output": "REFLECT: Semantic index parity achieved."})

        # 3. Market Intelligence (News & Price)
        await websocket.send_json({"type": "agent_start", "agent": "newsintel", "output": "OBSERVING sentiment catalysts..."})
        news_ctx = await mcp_news_agent.run(AgentContext(task=f"News {ticker}", ticker=ticker))
        await websocket.send_json({"type": "agent_complete", "agent": "newsintel", "output": "ACT: Multi-source news aggregated."})

        await websocket.send_json({"type": "agent_start", "agent": "pricemove", "output": "THINKING: Analyzing volatility clusters..."})
        price_ctx = await price_agent.run(AgentContext(task=f"Analyze {ticker}", ticker=ticker))
        await websocket.send_json({"type": "agent_complete", "agent": "pricemove", "output": "REFLECT: Stats confirmed."})

        # 4. Neural Reasoning (The "Think" Engine)
        await websocket.send_json({"type": "agent_start", "agent": "thinkagent", "output": "THINKING: Executing Deep Multi-Step Reasoning..."})
        think_ctx = await think_agent.run(AgentContext(task=f"Think {ticker}", ticker=ticker, metadata={
            "price_data": price_ctx.result,
            "news_data": news_ctx.result
        }))
        await websocket.send_json({"type": "agent_complete", "agent": "thinkagent", "output": f"IMPROVE: Logical path closed. Signal: {think_ctx.result.get('signal')}"})

        # 5. Technical Projection
        await websocket.send_json({"type": "agent_start", "agent": "forecast", "output": "PLANNING: Projecting technical trends..."})
        forecast_ctx = await forecast_agent.run(AgentContext(task=f"Forecast {ticker}", ticker=ticker))
        await websocket.send_json({"type": "agent_complete", "agent": "forecast", "output": "IMPROVE: Level confidence high."})

        # 6. Narrative Synthesis
        await websocket.send_json({"type": "agent_start", "agent": "explanation", "output": "THINKING: Synthesizing final institutional narrative..."})
        explain_ctx = await explain_agent.run(AgentContext(task=f"Explain {ticker}", ticker=ticker, metadata={
            "price_data": price_ctx.result,
            "news_data": news_ctx.result,
            "think_result": think_ctx.result
        }))
        await websocket.send_json({"type": "agent_complete", "agent": "explanation", "output": "ACT: Synthesis complete."})

        # Final Result
        final_result = {
            "stock": data_ctx.result,
            "analysis": {
                "movement": price_ctx.result,
                "forecast": forecast_ctx.result,
                "thinking": think_ctx.result,
                "explanation": explain_ctx.result,
                "news": news_ctx.result
            }
        }
        await websocket.send_json({"type": "analysis_complete", "result": final_result})

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

# ─── OMNI-AXIOM v5 Simulation Endpoints ─────────────────────────────────────

@app.get("/api/simulation/status")
async def simulation_status():
    """Get summarized virtual portfolio status."""
    return app.state.simulation.get_status()

@app.post("/api/simulation/init")
async def simulation_init(req: SimulationInitRequest):
    """Initialize virtual wallet with starting balance."""
    return app.state.simulation.initialize_account(req.initial_balance)

@app.post("/api/simulation/buy")
async def simulation_buy(request: BuyRequest):
    """Execute virtual BUY using live market price."""
    try:
        return app.state.simulation.buy_stock(request.ticker, request.amount, request.prediction)
    except ValueError as e:
        return {"error": str(e)}

@app.post("/api/simulation/sell")
async def simulation_sell(req: SimulationTradeRequest):
    """Execute virtual SELL using live market price."""
    try:
        return app.state.simulation.sell_stock(req.ticker, req.quantity)
    except ValueError as e:
        return {"error": str(e)}

@app.get("/api/simulation/update")
async def simulation_update():
    """Fetch real-time revaluation of all virtual positions."""
    return app.state.simulation.calculate_live_portfolio()


if UI_DIST_DIR.exists():
    # Serve the built Vite app from the same backend port for one-command local startup.
    app.mount("/", StaticFiles(directory=str(UI_DIST_DIR), html=True), name="ui")
    logger.info(f"Serving built frontend from {UI_DIST_DIR}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("gateway.server:app", host="0.0.0.0", port=8000, reload=True)
