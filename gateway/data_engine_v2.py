"""
Open-source data engine using OpenBB Platform + SEC EDGAR + yfinance + SearXNG.
Zero paid API keys required for basic operation.
"""
import httpx
import yfinance as yf
from openbb import obb
from typing import Optional, List, Dict
import asyncio
import os
from core.logger import get_logger

logger = get_logger(__name__)

OPENBB_BASE = os.getenv("OPENBB_BASE_URL", "http://localhost:6900")
EDGAR_BASE = "https://data.sec.gov"
SEARXNG_BASE = os.getenv("SEARXNG_BASE_URL", "http://localhost:8888")

class OpenSourceDataEngine:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(OpenSourceDataEngine, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, 'initialized'):
            return
        self.initialized = True
        logger.info("OpenSource Data Engine initialized.")

    # ─── PRICE DATA ──────────────────────────────────────────────
    async def get_price(self, ticker: str) -> dict:
        """yfinance — free, no key"""
        try:
            # Run yfinance in thread to avoid blocking
            def _fetch_yf():
                t = yf.Ticker(ticker)
                # fast_info might fail on some tickers, use info if needed
                try:
                    info = t.fast_info
                    hist = t.history(period="1mo")
                    return {
                        "current_price": getattr(info, 'last_price', 0),
                        "52w_high": getattr(info, 'year_high', 0),
                        "52w_low": getattr(info, 'year_low', 0),
                        "market_cap": getattr(info, 'market_cap', 0),
                        "ohlcv": hist.tail(30).to_dict('records') if not hist.empty else [],
                        "source_used": "yfinance"
                    }
                except:
                    return None
            
            res = await asyncio.to_thread(_fetch_yf)
            if res: return res
            
            # Fallback to OpenBB
            return await self._openbb_price(ticker)
        except Exception as e:
            logger.warning(f"Price fetch failed for {ticker}: {e}")
            return {"current_price": 0, "source_used": "error"}

    async def _openbb_price(self, ticker: str) -> dict:
        """OpenBB Platform — free tier with yfinance provider"""
        try:
            # Try using OpenBB SDK directly if available, otherwise fallback to API
            res = obb.equity.price.historical(symbol=ticker, provider="yfinance")
            data = res.to_df()
            return {
                "current_price": float(data['close'].iloc[-1]),
                "ohlcv": data.tail(30).to_dict('records'),
                "source_used": "openbb/yfinance"
            }
        except Exception as e:
            logger.warning(f"OpenBB price fetch failed: {e}")
            return {"current_price": 0, "source_used": "openbb_error"}

    # ─── FINANCIALS ──────────────────────────────────────────────
    async def get_financials(self, ticker: str) -> dict:
        """OpenBB Platform — standardizes data from yfinance + EDGAR"""
        try:
            # Use OpenBB SDK directly
            income = obb.equity.fundamental.income(symbol=ticker, provider="yfinance", limit=5).to_df()
            balance = obb.equity.fundamental.balance(symbol=ticker, provider="yfinance", limit=5).to_df()
            cashflow = obb.equity.fundamental.cash(symbol=ticker, provider="yfinance", limit=5).to_df()
            
            return {
                "income": income.to_dict('records'),
                "balance": balance.to_dict('records'),
                "cashflow": cashflow.to_dict('records'),
                "source_used": "openbb/yfinance"
            }
        except Exception as e:
            logger.warning(f"Financials fetch failed for {ticker}: {e}")
            return {"income": [], "balance": [], "cashflow": [], "source_used": "error"}

    # ─── SEC FILINGS (FREE, NO KEY) ──────────────────────────────
    async def get_sec_filings(self, ticker: str, form_type: str = "10-K") -> dict:
        """
        SEC EDGAR Full-Text Search API — 100% free, no API key needed.
        """
        try:
            # SEC requires a User-Agent header
            headers = {"User-Agent": "AITradra/1.0 (contact@aitradra.com)"}
            async with httpx.AsyncClient(headers=headers) as client:
                # 1. Search for filings
                r = await client.get(
                    f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&dateRange=custom&startdt=2023-01-01&forms={form_type}"
                )
                if r.status_code == 200:
                    return {
                        "ticker": ticker,
                        "form_type": form_type,
                        "filings": r.json().get("hits", {}).get("hits", []),
                        "source_used": "sec_edgar_free"
                    }
                return {"ticker": ticker, "filings": [], "source_used": "sec_error"}
        except Exception as e:
            logger.warning(f"SEC filing fetch failed for {ticker}: {e}")
            return {"ticker": ticker, "filings": [], "source_used": "error"}

    # ─── WEB SEARCH (SearXNG — SELF-HOSTED) ─────────────────────
    async def web_search(self, query: str, num_results: int = 5) -> List[Dict]:
        """SearXNG self-hosted — completely free, no API key"""
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    f"{SEARXNG_BASE}/search",
                    params={"q": query, "format": "json", "engines": "google,bing,duckduckgo"},
                    timeout=15
                )
                if r.status_code == 200:
                    results = r.json().get("results", [])[:num_results]
                    return [{"title": r.get("title", ""), "url": r.get("url", ""), 
                             "snippet": r.get("content", "")} for r in results]
                return []
        except Exception as e:
            logger.warning(f"SearXNG fetch failed: {e}")
            return []

    # ─── MACRO DATA (FRED — FREE) ────────────────────────────────
    async def get_macro(self, series: str = "FEDFUNDS") -> dict:
        """
        FRED API — free, get key at fred.stlouisfed.org.
        No key? OpenBB econdb provider works without one.
        """
        try:
            res = obb.economy.fred_series(symbol=series, provider="econdb")
            return {**res.to_df().to_dict('records'), "source_used": "openbb/econdb_free"}
        except Exception as e:
            logger.warning(f"Macro fetch failed: {e}")
            return {"data": [], "source_used": "error"}

    async def get_full_context(self, ticker: str) -> dict:
        """Aggregates everything for LLM reasoning."""
        price, financials, filings, news = await asyncio.gather(
            self.get_price(ticker),
            self.get_financials(ticker),
            self.get_sec_filings(ticker),
            self.web_search(f"{ticker} stock news")
        )
        
        return {
            "ticker": ticker,
            "price": price,
            "financials": financials,
            "filings": filings,
            "news": news,
            "timestamp": os.getlogin() if hasattr(os, 'getlogin') else "unknown"
        }

# Global instance
data_engine = OpenSourceDataEngine()
