"""
blob_agent.py  —  Async-safe blob / cache agent
=================================================
FIX: Replaced loop.run_until_complete() with proper async/await.
     load_blob() is now async — call it with `await self.blob_agent.load_blob(ticker)`.
"""

import logging
import asyncio
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Optional

import pandas as pd

from .collector_agent import fetch_ticker

logger = logging.getLogger("agents.blob_agent")

BLOB_DIR = Path("./data/blobs")
BLOB_DIR.mkdir(parents=True, exist_ok=True)


class BlobAgent:
    """
    Stores and retrieves rich per-ticker analysis blobs.
    All I/O is async — never blocks the event loop.
    """

    def __init__(self, ttl_hours: int = 4):
        self.ttl_hours = ttl_hours

    def _blob_path(self, ticker: str) -> Path:
        safe = hashlib.md5(ticker.encode()).hexdigest()[:10]
        return BLOB_DIR / f"{safe}_{ticker.replace('/', '_')}.json"

    def _is_fresh(self, path: Path) -> bool:
        if not path.exists():
            return False
        age_h = (datetime.now().timestamp() - path.stat().st_mtime) / 3600
        return age_h < self.ttl_hours

    # ── Public async API ─────────────────────────────────────────────────────

    async def load_blob(self, ticker: str) -> Optional[dict]:
        """
        Load a ticker blob from disk (if fresh) or fetch fresh data.
        SAFE to await inside FastAPI/uvicorn — no run_until_complete().
        """
        path = self._blob_path(ticker)
        if self._is_fresh(path):
            try:
                loop = asyncio.get_running_loop()
                text = await loop.run_in_executor(None, path.read_text)
                blob = json.loads(text)
                logger.debug(f"[BlobAgent] Cache hit for {ticker}")
                return blob
            except Exception as e:
                logger.debug(f"[BlobAgent] Cache read failed for {ticker}: {e}")

        # Fetch fresh data
        df, source = await fetch_ticker(ticker, period="1y")
        if df.empty:
            logger.warning(f"[BlobAgent] No historical data available for {ticker}")
            # Instead of returning None, return a skeleton so ApiAgent knows we tried
            return {
                "ticker": ticker,
                "source": "none",
                "records": 0,
                "last_price": 0,
                "is_stale": True,
                "fetched_at": datetime.now(timezone.utc).isoformat()
            }

        blob = self._df_to_blob(ticker, df, source)
        await self._save_blob(path, blob)
        return blob

    async def save_blob(self, ticker: str, data: dict):
        path = self._blob_path(ticker)
        await self._save_blob(path, data)

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _df_to_blob(self, ticker: str, df: pd.DataFrame, source: str) -> dict:
        close = df["Close"].dropna()
        return {
            "ticker":      ticker,
            "source":      source,
            "records":     len(df),
            "last_price":  float(close.iloc[-1]) if not close.empty else None,
            "last_date":   str(df.index[-1].date()) if not df.empty else None,
            "fetched_at":  datetime.now(timezone.utc).isoformat(),
            "pct_1d":      _pct_change(close, 1),
            "pct_5d":      _pct_change(close, 5),
            "pct_30d":     _pct_change(close, 30),
            "high_52w":    float(close.tail(252).max()) if len(close) >= 5 else None,
            "low_52w":     float(close.tail(252).min()) if len(close) >= 5 else None,
        }

    async def _save_blob(self, path: Path, blob: dict):
        try:
            loop = asyncio.get_running_loop()
            text = json.dumps(blob, default=str)
            await loop.run_in_executor(None, path.write_text, text)
        except Exception as e:
            logger.debug(f"[BlobAgent] Save failed: {e}")


def _pct_change(series: pd.Series, days: int) -> Optional[float]:
    if len(series) < days + 1:
        return None
    old = series.iloc[-(days + 1)]
    new = series.iloc[-1]
    if old == 0:
        return None
    return round((new - old) / old * 100, 4)
