from fastapi import APIRouter
from agents.data_agent import DataAgent
from agents.blob_agent import BlobAgent
from agents.rag_agent import RagAgent
from agents.news_agent import NewsAgent
from agents.price_agent import PriceAgent
from agents.forecast_agent import ForecastAgent
from agents.explain_agent import ExplanationAgent
import asyncio

router = APIRouter()

# Initialize Agents
data_agent = DataAgent()
blob_agent = BlobAgent()
rag_agent = RagAgent()
news_agent = NewsAgent()
price_agent = PriceAgent()
forecast_agent = ForecastAgent()
explain_agent = ExplanationAgent()

# Load RAG Index on startup
rag_agent.load_index()

@router.get("/api/stock/{ticker}")
async def get_stock_detail(ticker: str, live: bool = False):
    """Step 1 & 2: Get stock details and current price."""
    # Try blob first
    if not live:
        cached = blob_agent.load_blob(ticker)
        if cached:
            return cached
            
    # Fetch live
    data = data_agent.fetch_stock_data(ticker)
    blob_agent.save_blob(data)
    # Index for RAG
    rag_agent.index_stock_blob(data)
    rag_agent.save_index()
    return data

@router.get("/api/history/{ticker}")
async def get_stock_history(ticker: str):
    """Step 2: Get historical movement."""
    return blob_agent.get_stock_history(ticker)

@router.get("/api/explain/{ticker}")
async def explain_movement(ticker: str):
    """Step 3: Why price moved."""
    price_data = price_agent.analyze_movement(ticker)
    news_data = news_agent.fetch_news(ticker)
    rag_context = rag_agent.query(f"Price movement of {ticker}")
    
    explanation = await explain_agent.explain(ticker, price_data, news_data, rag_context)
    return {
        "movement": price_data,
        "explanation": explanation,
        "news": news_data
    }

@router.get("/api/forecast/{ticker}")
async def get_forecast(ticker: str):
    """Step 5: Forecast."""
    return forecast_agent.predict(ticker)

@router.get("/api/news/{ticker}")
async def get_news(ticker: str):
    """Step 4: News links."""
    return news_agent.fetch_news(ticker)

# Note: This is an APIRouter to be included in the main FastAPI app.
class ApiAgent:
    """Agent 8: UI API Agent - Central REST interface."""
    def __init__(self):
        self.router = router
