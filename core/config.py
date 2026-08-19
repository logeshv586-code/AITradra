"""AXIOM Core Configuration — all settings from environment variables."""

from pydantic import field_validator
from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Central configuration using Pydantic settings with env var loading."""

    # Application
    APP_NAME: str = "AXIOM"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Server & UI
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    UI_DIST_PATH: str = "ui/dist"

    # Infrastructure & Paths
    DATA_DIR: str = "data"
    KNOWLEDGE_DB_NAME: str = "axiom_knowledge.db"
    MARKET_DATA_DB_NAME: str = "market_data.sqlite3"

    # Database URLs
    DATABASE_URL: str = "sqlite+aiosqlite:///data/axiom_knowledge.db"

    @property
    def KNOWLEDGE_DB_PATH(self) -> str:
        return str((BASE_DIR / self.DATA_DIR / self.KNOWLEDGE_DB_NAME).resolve())

    @property
    def MARKET_DATA_DB_PATH(self) -> str:
        return str((BASE_DIR / self.DATA_DIR / self.MARKET_DATA_DB_NAME).resolve())

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
    LLM_TIMEOUT: int = 120

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
    YFINANCE_RATE_LIMIT: int = 60
    NEWS_FETCH_INTERVAL_MIN: int = 10
    PRICE_FETCH_INTERVAL_MIN: int = 5
    RAG_REINDEX_INTERVAL_MIN: int = 15

    # NVIDIA NIM LLM Settings
    LLM_PROVIDER: str = "nvidia_nim"
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"

    # Generic OpenAI-compatible provider. This works for OpenAI, OpenRouter,
    # Groq, Together, local gateways, or any /chat/completions-compatible API.
    OPENAI_COMPATIBLE_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_COMPATIBLE_API_KEY: str = ""
    OPENAI_COMPATIBLE_MODEL: str = "gpt-4o-mini"

    # Provider credentials must come from .env / secret management. Never commit keys.
    MOONSHOT_API_KEY: str = ""
    NEMOTRON_API_KEY: str = ""
    MINIMAX_API_KEY: str = ""
    MISTRAL_API_KEY: str = ""

    # Model Assignments (NIM)
    SENTIMENT_MODEL: str = "mistralai/mistral-small-4-119b-2603"
    REASONING_MODEL: str = "nvidia/nemotron-3-super-120b-a12b"
    ANALYSIS_MODEL: str = "meta/llama3-70b-instruct"
    GENERAL_MODEL: str = "minimaxai/minimax-m2.5"

    # Local LLM Fallbacks (Store filenames in .env, resolved to absolute at runtime)
    LOCAL_REASONING_MODEL_PATH: str = "NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf"
    LOCAL_GENERAL_MODEL_PATH: str = "Qwen2.5-3B-Instruct-Q4_K_M.gguf"

    # LM Studio Settings
    LM_STUDIO_URL: str = "http://localhost:1234/v1"
    LM_STUDIO_MODEL: str = (
        "Jackrong/Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-GGUF"
    )
    USE_LM_STUDIO: bool = False

    @field_validator("DEBUG", mode="before")
    @classmethod
    def coerce_debug_flag(cls, v):
        """Allow env modes like 'release' or 'development' for DEBUG."""
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            return bool(v)
        if isinstance(v, str):
            normalized = v.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "development", "dev"}:
                return True
            if normalized in {
                "0",
                "false",
                "no",
                "off",
                "release",
                "prod",
                "production",
            }:
                return False
        return v

    @field_validator("LOCAL_REASONING_MODEL_PATH", "LOCAL_GENERAL_MODEL_PATH")
    @classmethod
    def resolve_model_path(cls, v: str) -> str:
        """Joins filename from .env with project root to create an absolute path."""
        if Path(v).is_absolute():
            return str(v)
        return str((BASE_DIR / v).resolve())

    # Risk Controls
    PAPER_TRADE_MODE: bool = True
    MAX_POSITION_PCT: float = 0.05
    MAX_DAILY_LOSS_PCT: float = 0.02
    MAX_OPEN_POSITIONS: int = 5
    MIN_SIGNAL_CONFIDENCE: float = 0.70
    MIN_CONSENSUS_AGENTS: int = 3

    # Execution safety — live trading is fail-closed unless every gate is explicit.
    AUTOTRADE_ENABLED: bool = False
    LIVE_TRADING_ACK: str = ""
    REQUIRE_PROTECTIVE_ORDERS: bool = True
    REQUIRE_STRATEGY_VALIDATION: bool = True
    ALLOW_POSITION_ADDONS: bool = False
    TRADING_CYCLE_MINUTES: int = 5
    LIVE_STRATEGY_ID: str = "hyperliquid-agent-v1"

    # Live-deployment validation thresholds
    STRATEGY_VALIDATION_MAX_AGE_DAYS: int = 30
    MIN_BACKTEST_SHARPE: float = 1.0
    MAX_BACKTEST_DRAWDOWN_PCT: float = 20.0
    MIN_BACKTEST_WIN_RATE: float = 0.52
    MIN_BACKTEST_TRADES: int = 30
    MIN_BACKTEST_PROFIT_FACTOR: float = 1.20

    # Paper execution assumptions
    PAPER_STARTING_BALANCE: float = 100000.0
    PAPER_SLIPPAGE_BPS: float = 5.0
    PAPER_FEE_BPS: float = 4.0

    # External Services (from .env)
    UI_BASE_URL: str = "http://localhost:8000"
    QDRANT_URL: str = "http://localhost:6333"
    SEARXNG_URL: str = "http://localhost:8888"
    LANGFUSE_HOST: str = "http://localhost:3000"
    LANGFUSE_PUBLIC_KEY: str = "pk-lf-local"
    LANGFUSE_SECRET_KEY: str = "sk-lf-local"

    # Hyperliquid settings
    HYPERLIQUID_PRIVATE_KEY: Optional[str] = None
    HYPERLIQUID_VAULT_ADDRESS: Optional[str] = None
    HYPERLIQUID_ASSETS: list[str] = ["BTC", "ETH", "SOL"]
    HYPERLIQUID_INTERVAL: str = "5m"
    HYPERLIQUID_MAX_SLIPPAGE_PCT: float = 0.01

    # Extended Risk Controls
    FORCE_CLOSE_LOSS_PCT: float = 0.20
    MAX_LEVERAGE: int = 10
    BALANCE_RESERVE_PCT: float = 0.20
    MANDATORY_STOP_LOSS_PCT: float = 0.05

    # Watchlist (Expanded for comprehensive global visibility)
    DEFAULT_WATCHLIST: list[str] = [
        # US Tech & Megacap
        "AAPL", "GOOGL", "MSFT", "AMZN", "NVDA", "TSLA", "META", "NFLX",
        "AMD", "INTC", "CRM", "ADBE", "PYPL", "SQ", "UBER", "ABNB", "SPOT",
        "PLTR", "SNOW", "SHOP", "ORCL", "IBM",
        # US Finance / Traditional
        "JPM", "BAC", "WFC", "GS", "MS", "V", "MA", "JNJ", "PFE", "UNH",
        "PG", "KO", "PEP", "WMT", "TGT", "HD", "XOM", "CVX",
        # Indian / Asian Equities
        "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
        "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "TATAMOTORS.NS", "BABA", "TCEHY",
        "TSM", "SONY",
        # European / Other Internationals
        "ASML", "NVO", "NVS", "SAP", "SIE.DE", "LVMUY", "NSRGY", "RY", "TD",
        "BHP", "RIO",
        # Major Indices & ETFs
        "SPY", "QQQ", "DIA", "IWM", "VTI", "VEA", "VWO", "GLD", "SLV", "USO", "TLT",
        # Cryptocurrencies
        "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "ADA-USD",
        "AVAX-USD", "DOGE-USD", "DOT-USD", "LINK-USD", "MATIC-USD",
    ]

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
