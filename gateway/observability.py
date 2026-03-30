"""
Langfuse self-hosted observability (v4.0.1 compatible).
Tracks every LLM call: cost, latency, input/output.
Free forever when self-hosted.
"""
from langfuse import Langfuse, observe
import os
import time
from functools import wraps
from core.logger import get_logger

logger = get_logger(__name__)

# Global Langfuse setup
langfuse_host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
langfuse_public = os.getenv("LANGFUSE_PUBLIC_KEY", "pk-lf-local")
langfuse_secret = os.getenv("LANGFUSE_SECRET_KEY", "sk-lf-local")

# Set global environment variables for the observe() decorator
os.environ["LANGFUSE_PUBLIC_KEY"] = langfuse_public
os.environ["LANGFUSE_SECRET_KEY"] = langfuse_secret
os.environ["LANGFUSE_BASEURL"] = langfuse_host # Note: v4 uses LANGFUSE_BASEURL

try:
    # Initialize Langfuse client for manual events if needed
    langfuse_client = Langfuse(
        public_key=langfuse_public,
        secret_key=langfuse_secret,
        host=langfuse_host,
    )
    logger.info(f"Langfuse v4 initialized via {langfuse_host}")
except Exception as e:
    logger.warning(f"Langfuse failed to initialize: {e}")
    langfuse_client = None

def trace_llm(name: str, metadata: dict = None):
    """
    Decorator to auto-trace any LLM call to Langfuse using the @observe decorator.
    """
    def decorator(func):
        @observe(name=name)
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # v4 observe() decorator handles most of this automatically
            return await func(*args, **kwargs)
        return wrapper
    return decorator

async def log_event(name: str, level: str = "DEFAULT", metadata: dict = None):
    """Log a manual event to Langfuse"""
    if langfuse_client:
        try:
            langfuse_client.event(name=name, level=level, metadata=metadata or {})
        except Exception as e:
            logger.warning(f"Failed to log event to Langfuse: {e}")
