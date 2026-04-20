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

class ApiAgent:
    """Agent 8 & 11: UI API Agent & Orchestrator - Central Interface coordinating all 11 Agents."""
    
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
        self._cache = {} # Simple TTL cache: {ticker_endpoint: (timestamp, data)}
        
        # Load RAG Index on startup
        try:
            self.rag_agent.load_index()
        except Exception as e:
            print(f"Warning: Could not load RAG index: {e}")
            
        self._setup_routes()

    def _setup_routes(self):
        @self.router.get("/api/stock/{ticker}")
        async def get_stock_detail(ticker: str, live: bool = False):
            """Institutional-Grade persistent fetch flow with lazy-synchronization."""
            try:
                # Normalize ticker
                ticker = ticker.upper()
                blob = await self.blob_agent.load_blob(ticker)
                
                if blob is None:
                    # If entirely missing even after fetch_ticker attempt, 
                    # we return a 'Syncing' stub so the UI can show the spinner 
                    # while agents work in the background.
                    return {
                        "ticker": ticker,
                        "status": "syncing",
                        "last_price": 0,
                        "pct_1d": 0,
                        "records": 0,
                        "fetched_at": None,
                        "is_new_ticker": True
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
            """Step 3: Synthetic Thinking Flow - V3 Institutional Deep Reasoner."""
            import time
            ticker = ticker.upper()
            cache_key = f"explain_{ticker}"
            
            # Check Cache (15 min TTL)
            if cache_key in self._cache:
                ts, data = self._cache[cache_key]
                if time.time() - ts < 900:
                    return data

            # 1. Gather all inputs
            price_res = await self.price_agent.run(AgentContext(task=f"Analyze {ticker}", ticker=ticker))
            news_res = await self.mcp_news_agent.run(AgentContext(task=f"Fetch News {ticker}", ticker=ticker))
            rag_res = await self.rag_agent.run(AgentContext(task=f"Context for {ticker}", ticker=ticker))
            
            # 2. Deep Thinking Phase
            think_res = await self.think_agent.run(AgentContext(task=f"Thinking for {ticker}", ticker=ticker, metadata={
                "price_data": price_res.result,
                "news_data": news_res.result,
                "rag_context": rag_res.result
            }))
            
            # 3. Final Human Explanation (NVIDIA NIM fallback to Synthesis output)
            explain_res = await self.explain_agent.run(AgentContext(task=f"Explain {ticker}", ticker=ticker, metadata={
                "think_result": think_res.result,
                "price_data": price_res.result,
                "news_data": news_res.result
            }))
            
            res = {
                "movement": price_res.result,
                "explanation": explain_res.result,
                "thinking": think_res.result,
                "news": news_res.result,
                "confidence": think_res.result.get("confidence_score")
            }
            self._cache[cache_key] = (time.time(), res)
            return res

        @self.router.get("/api/forecast/{ticker}")
        async def get_forecast(ticker: str):
            import time
            ticker = ticker.upper()
            cache_key = f"forecast_{ticker}"
            if cache_key in self._cache:
                ts, data = self._cache[cache_key]
                if time.time() - ts < 900: return data

            res = await self.forecast_agent.run(AgentContext(task=f"Predict {ticker}", ticker=ticker))
            self._cache[cache_key] = (time.time(), res.result)
            return res.result

        @self.router.get("/api/news/{ticker}")
        async def get_news(ticker: str):
            res = await self.mcp_news_agent.run(AgentContext(task=f"News {ticker}", ticker=ticker))
            return res.result

        @self.router.get("/api/batch/run")
        async def run_batch():
            """Force trigger nightly batch process."""
            return await self.batch_agent.run(AgentContext(task="Manual Core Sync"))

# Singleton instance
agent_instance = ApiAgent()
router = agent_instance.router
