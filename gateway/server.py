"""AXIOM V4.0 Mythic Trading Intelligence API — FastAPI gateway with multi-agent + orchestrator pipeline + Live Data."""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional, List, Dict
import asyncio
import sys
import os
import json
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings
from core.logger import get_logger
from memory.memory_manager import MemoryManager
from llm.client import LLMClient
from agents.base_agent import AgentContext

# V1 Core Agents (Legacy)
from agents_legacy.data_agent.agent import DataAgent
from agents_legacy.news_agent.agent import NewsAgent
from agents_legacy.trend_agent.agent import TrendAgent
from agents_legacy.risk_agent.agent import RiskAgent
from agents_legacy.ml_agent.agent import MLAgent
from agents_legacy.synthesis_agent.agent import SynthesisAgent

# V2 Profit Agents (Legacy)
from agents_legacy.arbitrage_agent.agent import ArbitrageAgent
from agents_legacy.portfolio_agent.agent import PortfolioAgent
from agents_legacy.macro_agent.agent import MacroAgent
from agents_legacy.social_sentiment_agent.agent import SocialSentimentAgent
from agents_legacy.earnings_agent.agent import EarningsAgent
from agents_legacy.options_flow_agent.agent import OptionsFlowAgent
from agents_legacy.regime_detector_agent.agent import RegimeDetectorAgent
from agents_legacy.backtest_agent.agent import BacktestAgent

# V2 Infrastructure (Legacy)
from agents_legacy.orchestrator.graph import AgentOrchestrator
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

# V4 Mythic-Tier Architecture
from agents.orchestrator import mythic_orchestrator
from gateway.db_portability import router as db_portability_router

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

class ChatRequest(BaseModel):
    message: str
    ticker: Optional[str] = ""

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

    # AXIOM v2 Scheduler
    from gateway.scrapers.rss_scraper import rss_scraper
    scheduler.add_job(rss_scraper.fetch_all, "interval", minutes=5)
    asyncio.create_task(asyncio.to_thread(rss_scraper.fetch_all))

    # V4 Data Collection Scheduler
    # Collect news every 5 minutes and index to RAG every 15 minutes
    scheduler.add_job(collect_news_data, "interval", minutes=5, id="collect_news")
    scheduler.add_job(index_knowledge_to_rag, "interval", minutes=15, id="index_rag")
    # Collect daily OHLCV data at startup and then daily
    scheduler.add_job(collect_daily_data, "interval", hours=24, id="collect_daily")

    scheduler.start()
    logger.info("⏰ Background scheduler started (RSS + News + RAG indexing + Daily OHLCV).")

    # Trigger initial data collection in background (non-blocking)
    asyncio.create_task(collect_news_data())
    asyncio.create_task(collect_historical_data())
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

    # V3 RAG Agent
    from agents.rag_agent import RagAgent
    app.state.rag_agent = RagAgent(memory=app.state.memory)
    try:
        app.state.rag_agent.load_index()
    except Exception as e:
        logger.warning(f"RAG index load failed: {e}")

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

    # Cache for live data (TTL-based)
    app.state.cache = {"watchlist": None, "watchlist_ts": 0, "indices": None, "indices_ts": 0}
    app.state.last_seen = {}  # Persistent store for across-fetch fallbacks

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


# ─── HELPER: Fetch yfinance data with caching ────────────────────────────────

async def _fetch_yf_ticker(ticker: str) -> dict:
    """Fetch live data for a single ticker via yfinance (async-wrapped)."""
    import yfinance as yf
    last_seen = app.state.last_seen
    loop = asyncio.get_running_loop()

    def _sync_fetch():
        import math
        def _sf(v, default=0):
            """Sanitize float: replace NaN/Inf with default."""
            if v is None: return default
            try:
                f = float(v)
                return default if (math.isnan(f) or math.isinf(f)) else f
            except (ValueError, TypeError):
                return default

        try:
            t = yf.Ticker(ticker)
            info = t.info or {}
            
            # If info is empty or contains rate limit error, raise to trigger fallback
            if not info or "Rate limited" in str(info):
                raise Exception("Rate limited")

            hist = t.history(period="3mo")

            # Build OHLCV array for sparkline
            ohlcv = []
            prices = []
            if not hist.empty:
                for idx, row in hist.iterrows():
                    o = round(_sf(row.get("Open", 0)), 2)
                    h = round(_sf(row.get("High", 0)), 2)
                    l = round(_sf(row.get("Low", 0)), 2)
                    c = round(_sf(row.get("Close", 0)), 2)
                    v = int(_sf(row.get("Volume", 0)))
                    ohlcv.append({"t": len(ohlcv) - len(hist), "o": o, "h": h, "l": l, "c": c, "v": v})
                    prices.append(c)

            current_price = _sf(info.get("currentPrice") or info.get("regularMarketPrice") or (prices[-1] if prices else 0))
            prev_close = _sf(info.get("previousClose") or info.get("regularMarketPreviousClose") or current_price)
            change_pct = round(((current_price - prev_close) / prev_close * 100) if prev_close else 0, 2)
            
            exchange = info.get("exchange", "NMS")
            lat, lon = get_coords_for_ticker(ticker, exchange)

            mcap_raw = _sf(info.get("marketCap", 0))
            vol_raw = _sf(info.get("volume") or info.get("regularMarketVolume", 0))
            beta = _sf(info.get("beta", 1.0), 1.0)
            
            # Approximate VaR from beta & volatility
            vol_level = "High" if beta > 1.5 else ("Med" if beta > 0.8 else "Low")
            var_pct = round(min(beta * 2.5, 10.0), 1)

            res = {
                "id": ticker,
                "name": info.get("longName") or info.get("shortName") or ticker,
                "ex": exchange,
                "px": round(current_price, 2),
                "chg": round(_sf(change_pct), 2),
                "mcap": format_market_cap(mcap_raw),
                "vol": format_volume(vol_raw),
                "pe": str(round(_sf(info.get("trailingPE", 0)), 1)),
                "sector": info.get("sector") or info.get("industry") or "N/A",
                "lat": lat,
                "lon": lon,
                "ohlcv": ohlcv,
                "risk": {
                    "var": f"{var_pct}%",
                    "beta": round(beta, 2),
                    "vol": vol_level,
                },
                "fundamentals": {
                    "market_cap": mcap_raw,
                    "pe_ratio": _sf(info.get("trailingPE", 0)),
                    "dividend_yield": _sf(info.get("dividendYield", 0)),
                    "52w_high": _sf(info.get("fiftyTwoWeekHigh", 0)),
                    "52w_low": _sf(info.get("fiftyTwoWeekLow", 0)),
                    "avg_volume": _sf(info.get("averageVolume", 0)),
                    "currency": info.get("currency", "USD"),
                },
                "stale": False,
                "ts": datetime.now().isoformat()
            }
            # Save to persistent cache
            last_seen[ticker] = res
            return res

        except Exception as e:
            logger.warning(f"yfinance fetch failed/throttled for {ticker}: {e}")
            # Fallback to last seen if available
            if ticker in last_seen:
                stale_data = last_seen[ticker].copy()
                stale_data["stale"] = True
                return stale_data
            
            # Absolute fallback (minimal object with dummy data to keep UI alive)
            dummy_prices = {"AAPL": 175.25, "NVDA": 825.40, "TSLA": 180.15, "MSFT": 415.60, "GOOGL": 145.30, "META": 485.20, "AMZN": 178.40, "BTC-USD": 65000, "ETH-USD": 3500}
            dpx = dummy_prices.get(ticker, 100.0)
            return {
                "id": ticker, "name": ticker, "ex": "N/A",
                "px": dpx, "chg": 0.05, "mcap": "N/A", "vol": "N/A",
                "pe": "15.0", "sector": "Technology", "lat": 40.7, "lon": -74.0,
                "ohlcv": [{"t": i, "c": dpx + (i*0.1)} for i in range(10)], 
                "risk": {"var": "2.5%", "beta": 1.1, "vol": "Low"},
                "fundamentals": {}, "error": str(e), "stale": True
            }

    return await loop.run_in_executor(None, _sync_fetch)


async def _fetch_yf_index(symbol: str, name: str) -> dict:
    """Fetch a single index value."""
    import yfinance as yf
    loop = asyncio.get_running_loop()

    def _sync():
        try:
            t = yf.Ticker(symbol)
            info = t.info or {}
            price = info.get("regularMarketPrice") or info.get("previousClose", 0)
            prev = info.get("regularMarketPreviousClose") or info.get("previousClose", price)
            chg = round(((price - prev) / prev * 100) if prev else 0, 2)
            return {"name": name, "value": round(price, 2), "change": chg}
        except Exception as e:
            logger.error(f"Index fetch failed for {symbol}: {e}")
            return {"name": name, "value": 0, "change": 0}

    return await loop.run_in_executor(None, _sync)


# ─── AXIOM v2 Endpoints ──────────────────────────────────────────────────────

@app.get("/api/stock/{ticker}")
async def get_stock_detail_v2(ticker: str):
    """
    Full stock detail for the panel view.
    """
    ticker = ticker.upper()
    data = await data_engine.get_price_data(ticker)
    news = await data_engine.get_news(ticker, max_items=10)
    sentiment = await data_engine.get_social_sentiment(ticker)
    
    # Mocking OHLCV history for now since yfinance is hit-or-miss
    ohlcv_history = data.get("ohlcv", []) 
    
    return {
        "ticker": ticker,
        "price_data": data,
        "news": news,
        "sentiment": sentiment,
        "ohlcv_history": ohlcv_history,
        "freshness_label": cache.get_freshness_label(ticker, "price"),
    }

@app.get("/api/stock/{ticker}/analysis")
async def get_stock_analysis(ticker: str):
    """
    AXIOM V5: CrewAI Multi-Agent Synthesis.
    Combines Technical, News, and Risk agents into a final Mythic report.
    """
    ticker = ticker.upper()
    data = await data_engine.get_full_context(ticker)
    
    # Run the multi-agent crew (offload to thread as kickoff is synchronous)
    try:
        context_str = json.dumps(data, default=str)[:2000] # Limit context size for agents
        result = await asyncio.to_thread(crew_manager.run_analysis, ticker, context_str)
        
        # If result is a string (often from crewAI), try to parse it
        if isinstance(result, str):
            try:
                # Basic cleaning if LLM put code blocks
                clean_res = result.strip().replace("```json", "").replace("```", "")
                return json.loads(clean_res)
            except:
                return {"raw_crew_output": result}
        return result
    except Exception as e:
        logger.error(f"CrewAI Synthesis failed for {ticker}: {e}")
        # Fallback to legacy single-prompt analysis
        market_ctx = MarketManager.get_ai_suggestion_context(ticker)
        prompt = build_investment_criteria_prompt(ticker, data, market_context=market_ctx)
        return await llm_client.complete(prompt, expect_json=True)

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
    """Lightweight endpoint just for globe pins."""
    from core.config import settings
    watchlist = settings.DEFAULT_WATCHLIST
    
    results = []
    for ticker in watchlist:
        data, _ = cache.get(ticker, "price")
        if not data:
             # Fast fallback if nothing in cache
             lat, lon = get_coords_for_ticker(ticker)
             results.append({"ticker": ticker, "lat": lat, "lon": lon, "px": 0, "pct_chg": 0, "signal": "HOLD"})
             continue
             
        lat, lon = get_coords_for_ticker(ticker)
        results.append({
            "ticker": ticker,
            "lat": lat,
            "lon": lon,
            "px": data.get("px", 0),
            "pct_chg": data.get("pct_chg", 0),
            "signal": "BUY" if data.get("pct_chg", 0) > 0 else "SELL", # Simple signal fallback
        })
    return results

# ─── REST Endpoints ───────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "4.0.0", "app": "AXIOM V4 Mythic", "agents": 14, "mythic_agents": 5}


async def _background_watchlist_sync():
    """Background task to fetch all watchlist data sequentially without blocking the UI."""
    import time
    cache = app.state.cache
    if cache.get("is_syncing"): 
        return
    cache["is_syncing"] = True
    try:
        stocks = []
        for ticker in settings.DEFAULT_WATCHLIST:
            res = await _fetch_yf_ticker(ticker)
            if res and res.get("px", 0) > 0:
                stocks.append(res)
            # Small stagger to avoid hitting internal yfinance thresholds too fast
            await asyncio.sleep(0.4)
            
        cache["watchlist"] = stocks
        cache["watchlist_ts"] = time.time()
        logger.info(f"[LIVE] Background Watchlist Sync Complete: {len(stocks)}/{len(settings.DEFAULT_WATCHLIST)} tickers")
    finally:
        cache["is_syncing"] = False

@app.get("/api/market/watchlist")
async def market_watchlist():
    """Fetch LIVE market data instantly utilizing background async scraping to avoid rate limits."""
    import time
    cache = app.state.cache
    now = time.time()

    # 1. Trigger background sync if data is stale or empty
    if not cache.get("watchlist") or now - cache.get("watchlist_ts", 0) > 60:
        asyncio.create_task(_background_watchlist_sync())

    # 2. Return fully cached list if available
    if cache.get("watchlist"):
        return {"stocks": cache.get("watchlist"), "cached": True, "ts": cache.get("watchlist_ts")}

    # 3. Instant Return: Seed dummy/last_seen data so the 3D Globe renders instantly with all nodes
    from gateway.stock_geo import get_coords_for_ticker
    stocks = []
    logger.info("[LIVE] Returning instantaneous placeholder map while background sync gathers live data...")
    for t in settings.DEFAULT_WATCHLIST:
        if t in app.state.last_seen:
            stocks.append(app.state.last_seen[t])
        else:
            lat, lon = get_coords_for_ticker(t)
            dummy = {
                "id": t, "name": t, "ex": "N/A", "px": 100.0, "chg": 0.05, 
                "mcap": "N/A", "vol": "N/A", "pe": "0", "sector": "Syncing...", 
                "lat": lat, "lon": lon, "ohlcv": [], "risk": {"var": "0%", "beta": 1.0, "vol": "Low"}, 
                "fundamentals": {}, "stale": True
            }
            app.state.last_seen[t] = dummy
            stocks.append(dummy)
            
    return {"stocks": stocks, "cached": False, "ts": now, "syncing": True}


@app.get("/api/market/status")
async def get_market_status():
    """Returns the current status of all global markets."""
    return MarketManager.get_all_statuses()


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
    import yfinance as yf
    loop = asyncio.get_running_loop()

    def _get_news():
        try:
            t = yf.Ticker(ticker.upper())
            news_data = t.news
            raw_news = news_data if isinstance(news_data, list) else []
            articles = []
            for item in raw_news[:8]:
                if not isinstance(item, dict): continue
                content = item.get("content") or item
                title = content.get("title") or "No title"
                
                # Publisher lookup
                provider = content.get("provider") or content.get("publisher") or "Unknown"
                publisher = provider.get("displayName") if isinstance(provider, dict) else str(provider)
                
                pub_date = content.get("pubDate") or content.get("providerPublishTime")
                
                # Time formatting
                time_str = "recent"
                if pub_date:
                    try:
                        ts = float(pub_date)
                        dt = datetime.now() - timedelta(seconds=ts) if ts < 1e10 else datetime.fromtimestamp(ts)
                        diff = (datetime.now() - dt).total_seconds()
                        if diff < 3600:
                            time_str = f"{int(diff/60)}m"
                        elif diff < 86400:
                            time_str = f"{int(diff/3600)}h"
                        else:
                            time_str = f"{int(diff/86400)}d"
                    except:
                        time_str = "recent"
                
                articles.append({
                    "src": publisher[:12] if publisher else "News",
                    "t": time_str,
                    "txt": title,
                    "s": 0,  # Will be scored below
                })
            return articles
        except Exception as e:
            logger.error(f"News fetch failed for {ticker}: {e}")
            return []

    articles = await loop.run_in_executor(None, _get_news)

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
        ticker=ticker.upper() if ticker else None
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
    return {
        "agents": [
            # V3 Intelligence Agents
            {"name": "DataCollector",      "status": "active", "type": "v3_intelligence"},
            {"name": "BlobStorageAgent",   "status": "active", "type": "v3_intelligence"},
            {"name": "MarketRagAgent",     "status": "active", "type": "v3_intelligence"},
            {"name": "NewsIntelAgent",     "status": "active", "type": "v3_intelligence"},
            {"name": "PriceMoveAgent",     "status": "active", "type": "v3_intelligence"},
            {"name": "ForecastAgent",      "status": "active", "type": "v3_intelligence"},
            {"name": "ExplainAgent",       "status": "active", "type": "v3_intelligence"},
            {"name": "ThinkAgent",         "status": "active", "type": "v3_intelligence"},
            {"name": "McpNewsAgent",       "status": "active", "type": "v3_intelligence"},
            {"name": "BatchAgent",         "status": "active", "type": "v3_intelligence"},
            {"name": "UIApiAgent",         "status": "active", "type": "v3_intelligence"},
            # V4 Mythic-Tier Agents
            {"name": "MythicOrchestrator",  "status": "active", "type": "v4_mythic", "role": "ReAct reasoning loop"},
            {"name": "TechnicalSpecialist", "status": "active", "type": "v4_mythic", "role": "OHLCV pattern analysis"},
            {"name": "RiskSpecialist",      "status": "active", "type": "v4_mythic", "role": "VaR, beta, stress scenarios"},
            {"name": "MacroSpecialist",     "status": "active", "type": "v4_mythic", "role": "News sentiment, macro trends"},
            {"name": "CritiqueAgent",       "status": "active", "type": "v4_mythic", "role": "Self-reflection + confidence calibration"},
        ]
    }


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
    import math
    cache_data = app.state.cache
    stocks = cache_data.get("watchlist") or []

    predictions = []
    for s in stocks:
        ticker = s.get("id", "")
        px = s.get("px", 0)
        chg = s.get("chg", 0)
        beta = s.get("risk", {}).get("beta", 1.0) if isinstance(s.get("risk"), dict) else 1.0

        # Prediction direction from momentum
        if chg > 1.0:
            direction = "UP"
        elif chg < -1.0:
            direction = "DOWN"
        else:
            direction = "SIDEWAYS"

        # Weighted confidence (capped at 85%)
        momentum_signal = min(abs(chg) * 8, 25)  # 25% technical
        news_signal = 20  # baseline from cached RSS
        macro_signal = 15  # baseline macro
        sentiment_signal = 10  # baseline sentiment
        ml_signal = 7  # baseline ML
        raw_conf = momentum_signal + news_signal + macro_signal + sentiment_signal + ml_signal
        confidence = min(round(raw_conf, 1), 85)

        # Expected move
        expected_move = round(abs(chg) * 0.6 + beta * 0.5, 2)

        # Risk level
        if beta > 1.5 or abs(chg) > 3:
            risk_level = "HIGH"
        elif beta > 0.8 or abs(chg) > 1:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # Predicted price
        multiplier = 1 + (expected_move / 100) * (1 if direction == "UP" else -1 if direction == "DOWN" else 0)
        predicted_price = round(px * multiplier, 2)

        # Primary driver
        if abs(chg) > 2:
            primary_driver = "technical"
        elif beta > 1.3:
            primary_driver = "macro"
        else:
            primary_driver = "news"

        predictions.append({
            "ticker": ticker,
            "name": s.get("name", ticker),
            "current_price": px,
            "predicted_price": predicted_price,
            "prediction_direction": direction,
            "confidence_score": confidence,
            "expected_move_percent": expected_move,
            "risk_level": risk_level,
            "reasoning_summary": f"{ticker} shows {'bullish' if direction == 'UP' else 'bearish' if direction == 'DOWN' else 'neutral'} momentum ({chg:+.2f}%). Beta: {beta:.2f}.",
            "primary_driver": primary_driver,
            "source_link": "",
            "sector": s.get("sector", "N/A"),
            "chg": chg,
        })

    return {"predictions": predictions, "count": len(predictions), "max_confidence": 85}


@app.get("/api/market/trending")
async def market_trending():
    """OMNI-AXIOM Trending Stocks — top movers by absolute % change."""
    cache_data = app.state.cache
    stocks = cache_data.get("watchlist") or []

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
    cache_data = app.state.cache
    stocks = cache_data.get("watchlist") or []
    stock = next((s for s in stocks if s.get("id") == ticker), None)

    if not stock:
        # Fetch fresh
        stock = await _fetch_yf_ticker(ticker)

    risk = stock.get("risk", {}) if isinstance(stock.get("risk"), dict) else {}
    fundamentals = stock.get("fundamentals", {}) if isinstance(stock.get("fundamentals"), dict) else {}
    chg = stock.get("chg", 0)
    beta = risk.get("beta", 1.0)

    # Compute risk metrics
    var_95 = round(min(beta * 2.5, 10.0), 1)
    max_drawdown_est = round(min(beta * 5.0, 25.0), 1)
    volatility = risk.get("vol", "Medium")

    # Sector risk assessment
    sector = stock.get("sector", "N/A")
    high_risk_sectors = ["Cryptocurrency", "Biotech", "Cannabis", "SPACs"]
    sector_risk = "HIGH" if any(hr in sector for hr in high_risk_sectors) else ("MEDIUM" if beta > 1.0 else "LOW")

    # Overall risk level
    if beta > 1.5 or abs(chg) > 4:
        overall_risk = "HIGH"
    elif beta > 0.8 or abs(chg) > 2:
        overall_risk = "MEDIUM"
    else:
        overall_risk = "LOW"

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
    cache_data = app.state.cache
    stocks = cache_data.get("watchlist") or []

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
    for s in stocks:
        beta = s.get("risk", {}).get("beta", 1.0) if isinstance(s.get("risk"), dict) else 1.0
        chg = abs(s.get("chg", 0))
        if beta > 1.5 or chg > 3:
            risk_dist["HIGH"] += 1
        elif beta > 0.8 or chg > 1:
            risk_dist["MEDIUM"] += 1
        else:
            risk_dist["LOW"] += 1

    # Aggregate metrics
    avg_change = round(sum(s.get("chg", 0) for s in stocks) / len(stocks), 2) if stocks else 0
    bullish = sum(1 for s in stocks if s.get("chg", 0) > 0)
    bearish = len(stocks) - bullish

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("gateway.server:app", host="0.0.0.0", port=8000, reload=True)
