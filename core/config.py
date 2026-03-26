"""AXIOM Core Configuration — all settings from environment variables."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Central configuration using Pydantic settings with env var loading."""

    # Application
    APP_NAME: str = "AXIOM"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./axiom.db"

    # ChromaDB
    CHROMADB_HOST: str = "localhost"
    CHROMADB_PORT: int = 8001
    CHROMADB_COLLECTION: str = "axiom_memory"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # LLM
    OLLAMA_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "qwen2.5:7b"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 2000
    LLM_TIMEOUT: int = 60

    # Embedding Model
    EMBEDDING_MODEL: str = "nomic-embed-text"

    # Agent Settings
    AGENT_MAX_RETRIES: int = 3
    AGENT_TIMEOUT_SECONDS: int = 30
    MAX_PARALLEL_AGENTS: int = 5

    # Memory Settings
    EPISODIC_MEMORY_MAX_DAYS: int = 90
    SEMANTIC_MEMORY_MAX_RESULTS: int = 10
    WORKING_MEMORY_MAX_TOKENS: int = 4000

    # Self-Improvement
    PREDICTION_SCORE_DELAY_HOURS: int = 24
    MIN_ACCURACY_THRESHOLD: float = 0.55
    RETRAINING_MIN_SAMPLES: int = 100
    WEEKLY_REPORT_DAY: str = "sunday"

    # Market Data
    YFINANCE_RATE_LIMIT_PER_MIN: int = 60
    NEWS_FETCH_INTERVAL_MINUTES: int = 30
    MARKET_SCAN_INTERVAL_MINUTES: int = 15

    # Watchlist
    DEFAULT_WATCHLIST: list[str] = [
        "AAPL", "GOOGL", "MSFT", "AMZN", "NVDA",
        "TSLA", "META", "NFLX",
        "RELIANCE.NS", "TCS.NS", "INFY.NS",
        "BTC-USD", "ETH-USD"
    ]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
