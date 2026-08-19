from fastapi import APIRouter
import asyncio
from agents.data_agent import DataAgent
from agents.blob_agent import BlobAgent
from agents.rag_agent import RagAgent
from agents.news_agent import get_agent as get_news_agent
from agents.price_agent import PriceAgent
from agents.forecast_agent import ForecastAgent
from agents.explain_agent import ExplainAgent
from agents.think_agent import ThinkAgent
from agents.mcp_news_agent import McpNewsAgent
from agents.batch_agent import BatchAgent
from agents.base_agent import AgentContext
from core.config import settings
from core.trading_safety import get_execution_status, strategy_validation_store


class ApiAgent:
    """UI API Agent & Orchestrator for customer-facing market tools."""

    def __init__(self):
        self.router = APIRouter()
        self.data_agent = DataAgent()
        self.blob_agent = BlobAgent()
        self.rag_agent = RagAgent()
        self.news_agent = get_news_agent()
        self.price_agent = PriceAgent()
        self.forecast_agent = ForecastAgent()
        self.explain_agent = ExplainAgent()
        self.think_agent = ThinkAgent()
        self.mcp_news_agent = McpNewsAgent()
        self.batch_agent = BatchAgent()
        self._cache = {}

        try:
            self.rag_agent.load_index()
        except Exception as e:
            print(f"Warning: Could not load RAG index: {e}")

        self._setup_routes()

    def _setup_routes(self):
        @self.router.get("/api/stock/{ticker}")
        async def get_stock_detail(ticker: str, live: bool = False):
            try:
                ticker = ticker.upper()
                blob = await self.blob_agent.load_blob(ticker)
                if blob is None:
                    return {
                        "ticker": ticker,
                        "status": "syncing",
                        "last_price": 0,
                        "pct_1d": 0,
                        "records": 0,
                        "fetched_at": None,
                        "is_new_ticker": True,
                    }
                return {**blob, "status": "active"}
            except Exception as e:
                from fastapi import HTTPException
                raise HTTPException(status_code=500, detail=str(e))

        @self.router.get("/api/history/{ticker}")
        async def get_stock_history(ticker: str):
            return self.blob_agent.get_stock_history(ticker)

        @self.router.get("/api/explain/{ticker}")
        async def explain_movement(ticker: str):
            import time

            ticker = ticker.upper()
            cache_key = f"explain_{ticker}"
            if cache_key in self._cache:
                ts, data = self._cache[cache_key]
                if time.time() - ts < 900:
                    return data

            price_res = await self.price_agent.run(
                AgentContext(task=f"Analyze {ticker}", ticker=ticker)
            )
            news_res = await self.mcp_news_agent.run(
                AgentContext(task=f"Fetch News {ticker}", ticker=ticker)
            )
            rag_res = await self.rag_agent.run(
                AgentContext(task=f"Context for {ticker}", ticker=ticker)
            )
            think_res = await self.think_agent.run(
                AgentContext(
                    task=f"Thinking for {ticker}",
                    ticker=ticker,
                    metadata={
                        "price_data": price_res.result,
                        "news_data": news_res.result,
                        "rag_context": rag_res.result,
                    },
                )
            )
            explain_res = await self.explain_agent.run(
                AgentContext(
                    task=f"Explain {ticker}",
                    ticker=ticker,
                    metadata={
                        "think_result": think_res.result,
                        "price_data": price_res.result,
                        "news_data": news_res.result,
                    },
                )
            )

            result = {
                "movement": price_res.result,
                "explanation": explain_res.result,
                "thinking": think_res.result,
                "news": news_res.result,
                "confidence": think_res.result.get("confidence_score"),
            }
            self._cache[cache_key] = (time.time(), result)
            return result

        @self.router.get("/api/forecast/{ticker}")
        async def get_forecast(ticker: str):
            import time

            ticker = ticker.upper()
            cache_key = f"forecast_{ticker}"
            if cache_key in self._cache:
                ts, data = self._cache[cache_key]
                if time.time() - ts < 900:
                    return data

            result = await self.forecast_agent.run(
                AgentContext(task=f"Predict {ticker}", ticker=ticker)
            )
            self._cache[cache_key] = (time.time(), result.result)
            return result.result

        @self.router.get("/api/news/{ticker}")
        async def get_news(ticker: str):
            result = await self.mcp_news_agent.run(
                AgentContext(task=f"News {ticker}", ticker=ticker)
            )
            return result.result

        @self.router.get("/api/batch/run")
        async def run_batch():
            return await self.batch_agent.run(AgentContext(task="Manual Core Sync"))

        @self.router.get("/api/trading/status")
        async def trading_status():
            """Return a secret-free, customer-friendly execution readiness summary."""
            execution = get_execution_status(settings)
            validations = {
                ticker: strategy_validation_store.check(ticker, settings.LIVE_STRATEGY_ID)
                for ticker in settings.HYPERLIQUID_ASSETS
            }
            validation_ready = all(item.get("eligible", False) for item in validations.values()) if validations else False
            live_ready = execution["live_execution_allowed"] and validation_ready
            return {
                "mode": "live" if execution["live_execution_allowed"] else "practice",
                "uses_real_money": execution["live_execution_allowed"],
                "automation_enabled": execution["automation_enabled"],
                "live_ready": live_ready,
                "protective_orders_required": execution["protective_orders_required"],
                "strategy_validation_required": execution["strategy_validation_required"],
                "checks": {
                    "execution_gate": execution["live_execution_allowed"],
                    "strategy_validation": validation_ready,
                    "stop_and_target_protection": execution["protective_orders_required"],
                },
                "risk_controls": {
                    "max_position_pct": settings.MAX_POSITION_PCT * 100,
                    "daily_loss_limit_pct": settings.MAX_DAILY_LOSS_PCT * 100,
                    "max_open_positions": settings.MAX_OPEN_POSITIONS,
                    "max_leverage": settings.MAX_LEVERAGE,
                    "cash_reserve_pct": settings.BALANCE_RESERVE_PCT * 100,
                },
                "assets": {
                    ticker: {
                        "validated": result.get("eligible", False),
                        "reasons": result.get("reasons", []),
                        "last_validation": (result.get("record") or {}).get("validated_at"),
                    }
                    for ticker, result in validations.items()
                },
                "message": (
                    "Live execution is unlocked and strategy checks are current."
                    if live_ready
                    else "Real-money execution remains locked until every required safety and strategy check passes."
                ),
            }


agent_instance = ApiAgent()
router = agent_instance.router

# Mount customer-facing research, data-connection, history and manual trading APIs
# through the already-loaded V3 router. This avoids touching the global FastAPI
# shell and keeps existing routes/navigation unchanged.
from gateway.customer_market_router import router as customer_market_router
router.include_router(customer_market_router)
