import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY", "")
    LLM_PROVIDERS = os.getenv("LLM_PROVIDER_ORDER", "mistral_gguf,nvidia_nim,ollama").split(",")
    CACHE_TTL = {
        "price":     int(os.getenv("CACHE_TTL_PRICE_MINUTES", 5)),
        "news":      int(os.getenv("CACHE_TTL_NEWS_MINUTES", 15)),
        "sentiment": int(os.getenv("CACHE_TTL_SENTIMENT_HOURS", 1)),
        "fundamentals": int(os.getenv("CACHE_TTL_FUNDAMENTALS_HOURS", 24)),
        "analysis":  int(os.getenv("CACHE_TTL_ANALYSIS_HOURS", 6)),
    }
    SCRAPE_INTERVAL = int(os.getenv("SCRAPE_INTERVAL_MINUTES", 5))
    MAX_SCRAPE_WORKERS = int(os.getenv("MAX_SCRAPE_WORKERS", 4))
    REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
    REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
    NVIDIA_NIM_KEY = os.getenv("NVIDIA_NIM_KEY", "")
