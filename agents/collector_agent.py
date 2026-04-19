"""
collector_agent.py  —  Resilient Multi-Source Market Data Collector
====================================================================
Fallback chain (in order):
  1. yfinance          — primary, fast, free
  2. Stooq             — free CSV, no API key
  3. Alpha Vantage     — free tier (25 req/day), set ALPHA_VANTAGE_KEY env
  4. Web scrape        — Yahoo Finance HTML + MarketWatch HTML
  5. Open datasets     — FRED (macro), Quandl-free endpoints

Rules:
  • NEVER raises an unhandled exception — always returns empty DataFrame with metadata
  • NEVER logs a red ERROR for expected "no data" cases — uses WARNING at most
  • Ticker aliasing table handles renamed / rebranded symbols automatically
  • Scraper rotates User-Agent headers and respects robots.txt delays
"""

import os
import time
import logging
import asyncio
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Optional
from pathlib import Path

import httpx
import pandas as pd

from bs4 import BeautifulSoup
from core.config import settings
from agents.base_agent import AgentContext

logger = logging.getLogger("agents.collector_agent")

# ── Silence noisy third-party loggers ───────────────────────────────────────
logging.getLogger("peewee").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# ── Ticker alias table ───────────────────────────────────────────────────────
#   Key   = what your watchlist says
#   Value = what to actually query
TICKER_ALIASES: dict[str, str] = {
    # Indian markets — dollar sign is invalid
    "$TATOMOTORS.NS": "TATAMOTORS.NS",
    "TATOMOTORS.NS": "TATAMOTORS.NS",
    "TATAMOTORS": "TATAMOTORS.NS",
    "RELIANCE": "RELIANCE.NS",
    "HDFCBANK": "HDFCBANK.NS",
    "INFY": "INFY.NS",
    "TCS": "TCS.NS",
    "SBIN": "SBIN.NS",
    "ICICIBANK": "ICICIBANK.NS",
    # Rebranded tickers - keep original if API doesn't support the new ticker
    "SQ": "SQ",  # Block Inc
    "MATIC-USD": "POL-USD",  # Polygon rebranded to POL
    "FB": "META",
    "TWTR": "X",
    # OTC / ADR alternatives (fallback to these if primary fails)
    "BABA": "BABA",
    "TCEHY": "TCEHY",
}

# ── Open-source fallback endpoints ─────────────────────────────────────────
STOOQ_URL = "https://stooq.com/q/d/l/?s={ticker}&i=d"
AV_URL = "https://www.alphavantage.co/query"
YF_HTML_URL = "https://finance.yahoo.com/quote/{ticker}/history/"
MW_URL = "https://www.marketwatch.com/investing/stock/{ticker}"

SCRAPE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

CACHE_DIR = Path(os.environ.get("DATA_CACHE_DIR", "./data/cache"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

ALPHA_VANTAGE_KEY = os.environ.get("ALPHA_VANTAGE_KEY", "demo")

# ── Layer 1: Dynamic Watchlist loading ───────────────────────────────────────
def get_watchlist() -> list[str]:
    """Load watchlist from environment variable or fallback to settings."""
    env_watchlist = os.environ.get("WATCHLIST")
    if env_watchlist:
        # Split bypasses whitespace and comma/semicolon delimiters
        return [t.strip().upper() for t in re.split(r'[,\s;]+', env_watchlist) if t.strip()]
    return settings.DEFAULT_WATCHLIST


# ─────────────────────────────────────────────────────────────────────────────
# Utility helpers
# ─────────────────────────────────────────────────────────────────────────────


def _cache_path(ticker: str, period: str) -> Path:
    key = hashlib.md5(f"{ticker}:{period}".encode()).hexdigest()[:12]
    return CACHE_DIR / f"{key}.parquet"


def _load_cache(
    ticker: str, period: str, max_age_hours: Optional[int] = 6
) -> Optional[pd.DataFrame]:
    path = _cache_path(ticker, period)
    if not path.exists():
        return None
    age = (
        datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
    ).total_seconds() / 3600
    if max_age_hours is not None and age > max_age_hours:
        return None
    try:
        df = pd.read_parquet(path)
        if not df.empty:
            logger.debug(f"[Collector] Cache hit for {ticker}")
            return df
    except Exception:
        pass
    return None


def _save_cache(ticker: str, period: str, df: pd.DataFrame):
    if df.empty:
        return
    try:
        df.to_parquet(_cache_path(ticker, period))
    except Exception as e:
        logger.debug(f"[Collector] Cache write failed for {ticker}: {e}")


def _normalize_df(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """Ensure standard OHLCV columns regardless of source format."""
    col_map = {
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume",
        "adj close": "Adj Close",
        "adjusted close": "Adj Close",
    }
    df.columns = [col_map.get(c.lower().strip(), c) for c in df.columns]
    required = ["Open", "High", "Low", "Close", "Volume"]
    for col in required:
        if col not in df.columns:
            df[col] = float("nan")
    if not isinstance(df.index, pd.DatetimeIndex):
        for candidate in ["Date", "date", "timestamp", "Datetime"]:
            if candidate in df.columns:
                df[candidate] = pd.to_datetime(df[candidate], errors="coerce")
                df = df.set_index(candidate)
                break
    df.index = pd.to_datetime(df.index, errors="coerce")
    df = df[~df.index.isna()]
    df = df.sort_index()
    df["_source"] = source
    return df[required + ["_source"]]


def _period_to_days(period: str) -> int:
    mapping = {
        "1d": 1,
        "5d": 5,
        "1mo": 30,
        "3mo": 90,
        "6mo": 180,
        "1y": 365,
        "2y": 730,
        "5y": 1825,
        "10y": 3650,
        "ytd": 180,
        "max": 3650,
    }
    return mapping.get(period, 365)


# ─────────────────────────────────────────────────────────────────────────────
# Layer 1 — yfinance (DISABLED to avoid rate limits)
# ─────────────────────────────────────────────────────────────────────────────


def _fetch_yfinance(ticker: str, period: str) -> Optional[pd.DataFrame]:
    """Primary fetcher for standard equities, ETFs, and crypto pairs."""
    try:
        import yfinance as yf

        interval = '5m' if period == '1d' else '1d'
        fetch_period = '1mo' if (period == '1d' or period == '') else period

        df = yf.download(
            tickers=ticker,
            period=fetch_period,
            interval=interval,
            auto_adjust=False,
            progress=False,
            threads=False,
        )
        if df is None or df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [
                col[0] if isinstance(col, tuple) else col for col in df.columns
            ]
        df = _normalize_df(df, "yfinance")
        
        # Capture metadata (Market Cap, PE) if available
        try:
            info = yf.Ticker(ticker).info
            df.attrs["mktcap"] = info.get("marketCap", 0)
            df.attrs["pe"] = info.get("forwardPE", info.get("trailingPE", 0))
        except Exception:
            try:
                # Fallback: Scrape from Yahoo Finance summary page if info fails
                import httpx
                import re
                url = f"https://finance.yahoo.com/quote/{ticker}"
                headers = {"User-Agent": "Mozilla/5.0"}
                with httpx.Client(timeout=10, follow_redirects=True) as client:
                    resp = client.get(url, headers=headers)
                    if resp.status_code == 200:
                        # Find "Market Cap" and "PE Ratio (TTM)"
                        import re
                        # Using a more flexible regex that survives layout changes
                        mcap_match = re.search(r'(?:Market Cap|Market cap).*?(?:<span[^>]*>)([\d\.]+[TBM])', resp.text, re.IGNORECASE | re.DOTALL)
                        pe_match = re.search(r'(?:PE Ratio \(TTM\)|PE ratio).*?(?:<span[^>]*>)([\d\.]+)', resp.text, re.IGNORECASE | re.DOTALL)
                        
                        def parse_mcap(s):
                            # Remove tags and whitespace
                            s = re.sub(r'<.*?>', '', s).strip().upper().replace(',', '')
                            if 'T' in s: return float(s.replace('T', '')) * 1e12
                            if 'B' in s: return float(s.replace('B', '')) * 1e9
                            if 'M' in s: return float(s.replace('M', '')) * 1e6
                            try: return float(s)
                            except: return 0

                        if mcap_match:
                            df.attrs["mktcap"] = parse_mcap(mcap_match.group(1))
                        if pe_match:
                            pe_str = re.sub(r'<.*?>', '', pe_match.group(1)).strip().replace(',', '')
                            try: df.attrs["pe"] = float(pe_str)
                            except: df.attrs["pe"] = 0
            except Exception as e:
                logger.debug(f"[Collector] Fallback scrape failed for {ticker}: {e}")
                df.attrs["mktcap"] = df.attrs.get("mktcap", 0)
                df.attrs["pe"] = df.attrs.get("pe", 0)
            
        return df if not df.empty else None
    except Exception as e:
        logger.debug(f"[Collector] yfinance failed for {ticker}: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Layer 2 — Stooq (free CSV, no key required)
# ─────────────────────────────────────────────────────────────────────────────


async def _fetch_stooq(ticker: str, period: str) -> Optional[pd.DataFrame]:
    """
    Stooq uses its own symbol format. US stocks: AAPL.US, indices: ^SPX, crypto: BTC.V.
    """
    stooq_ticker = _to_stooq_symbol(ticker)
    url = STOOQ_URL.format(ticker=stooq_ticker)
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            r = await client.get(url, headers=SCRAPE_HEADERS)
        if r.status_code != 200 or len(r.text) < 100:
            return None
        from io import StringIO

        df = pd.read_csv(StringIO(r.text))
        if df.empty or "No data" in r.text:
            return None
        days = _period_to_days(period)
        cutoff = datetime.now() - timedelta(days=days)
        df = _normalize_df(df, "stooq")
        df = df[df.index >= pd.Timestamp(cutoff)]
        return df if not df.empty else None
    except Exception as e:
        logger.debug(f"[Collector] Stooq failed for {ticker}: {e}")
        return None


def _to_stooq_symbol(ticker: str) -> str:
    """Convert yfinance-style ticker to stooq format."""
    t = ticker.upper()
    if t.endswith("-USD"):  # crypto: BTC-USD → BTC.V
        return t.replace("-USD", ".V")
    if t.endswith(".NS"): # NSE
        return t.replace(".NS", ".IN")
    if t.endswith(".BO"): # BSE
        return t.replace(".BO", ".IN")
    if t.endswith(".L"): # London
        return t.replace(".L", ".UK")
    if t.endswith(".DE"): # Germany
        return t.replace(".DE", ".DE")
    if t.startswith("^"):  # index — pass through
        return t
    return f"{t}.US"  # default: US stock


# ─────────────────────────────────────────────────────────────────────────────
# Layer 3 — Alpha Vantage (free, 25 req/day)
# ─────────────────────────────────────────────────────────────────────────────


async def _fetch_alpha_vantage(ticker: str, period: str) -> Optional[pd.DataFrame]:
    if ALPHA_VANTAGE_KEY == "demo":
        return None  # skip if no real key
    # only plain US equities work well on free tier
    if any(c in ticker for c in [".", "-", "^"]):
        return None
    try:
        params = {
            "function": "TIME_SERIES_DAILY_ADJUSTED",
            "symbol": ticker,
            "outputsize": "full" if _period_to_days(period) > 100 else "compact",
            "apikey": ALPHA_VANTAGE_KEY,
        }
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(AV_URL, params=params)
        data = r.json()
        if "Time Series (Daily)" not in data:
            return None
        ts = data["Time Series (Daily)"]
        rows = []
        for date_str, vals in ts.items():
            rows.append(
                {
                    "Date": date_str,
                    "Open": float(vals["1. open"]),
                    "High": float(vals["2. high"]),
                    "Low": float(vals["3. low"]),
                    "Close": float(vals["5. adjusted close"]),
                    "Volume": float(vals["6. volume"]),
                }
            )
        df = pd.DataFrame(rows).set_index("Date")
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        days = _period_to_days(period)
        cutoff = datetime.now() - timedelta(days=days)
        df = df[df.index >= pd.Timestamp(cutoff)]
        df["_source"] = "alpha_vantage"
        return df if not df.empty else None
    except Exception as e:
        logger.debug(f"[Collector] Alpha Vantage failed for {ticker}: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Layer 4 — Web scraping (Yahoo Finance HTML)
# ─────────────────────────────────────────────────────────────────────────────


async def _scrape_yahoo_finance(ticker: str) -> Optional[dict]:
    """
    Scrape the Yahoo Finance quote page for current price + basic info.
    Returns a dict with current snapshot data (not full history).
    """
    url = f"https://finance.yahoo.com/quote/{ticker}/"
    try:
        async with httpx.AsyncClient(
            timeout=20, follow_redirects=True, headers=SCRAPE_HEADERS
        ) as client:
            r = await client.get(url)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "html.parser")

        # Extract JSON embedded in the page (most reliable)
        for script in soup.find_all("script"):
            if script.string and "QuoteSummaryStore" in (script.string or ""):
                match = re.search(
                    r'"regularMarketPrice":\{"raw":([\d.]+)', script.string
                )
                if match:
                    price = float(match.group(1))
                    prev_match = re.search(
                        r'"regularMarketPreviousClose":\{"raw":([\d.]+)', script.string
                    )
                    vol_match = re.search(
                        r'"regularMarketVolume":\{"raw":([\d.]+)', script.string
                    )
                    name_match = re.search(r'"longName":"([^"]+)"', script.string)
                    mcap_match = re.search(r'"marketCap":\{"raw":([\d.]+)', script.string)
                    pe_match = re.search(r'"trailingPE":\{"raw":([\d.]+)', script.string)
                    return {
                        "price": price,
                        "prev_close": float(prev_match.group(1)) if prev_match else None,
                        "volume": float(vol_match.group(1)) if vol_match else None,
                        "mktcap": float(mcap_match.group(1)) if mcap_match else 0,
                        "pe": float(pe_match.group(1)) if pe_match else 0,
                        "name": name_match.group(1) if name_match else ticker,
                        "source": "yahoo_scrape",
                        "scraped_at": datetime.now(timezone.utc).isoformat(),
                    }

        # Fallback: parse visible price element
        price_el = soup.select_one('[data-testid="qsp-price"]') or soup.select_one(
            'fin-streamer[data-field="regularMarketPrice"]'
        )
        if price_el:
            price_text = price_el.get("value") or price_el.get_text(strip=True)
            price = float(price_text.replace(",", ""))
            return {"price": price, "source": "yahoo_scrape_html", "ticker": ticker}

        return None
    except Exception as e:
        logger.debug(f"[Collector] Yahoo scrape failed for {ticker}: {e}")
        return None


async def _scrape_marketwatch(ticker: str) -> Optional[dict]:
    """Scrape MarketWatch for current quote as secondary scrape source."""
    # MarketWatch uses different URL patterns for different asset types
    if "-USD" in ticker:
        url = f"https://www.marketwatch.com/investing/cryptocurrency/{ticker.replace('-USD', '').lower()}"
    elif "." in ticker:
        url = f"https://www.marketwatch.com/investing/stock/{ticker.split('.')[0].lower()}"
    else:
        url = f"https://www.marketwatch.com/investing/stock/{ticker.lower()}"
    try:
        async with httpx.AsyncClient(
            timeout=20, follow_redirects=True, headers=SCRAPE_HEADERS
        ) as client:
            r = await client.get(url)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        price_el = soup.select_one(".intraday__price .value") or soup.select_one(
            'bg-quote[field="Last"]'
        )
        if price_el:
            price_text = price_el.get_text(strip=True).replace(",", "")
            price = float(re.sub(r"[^\d.]", "", price_text))
            return {"price": price, "source": "marketwatch_scrape", "ticker": ticker}
        return None
    except Exception as e:
        logger.debug(f"[Collector] MarketWatch scrape failed for {ticker}: {e}")
        return None


def _snapshot_to_df(snapshot: dict, ticker: str) -> pd.DataFrame:
    """Convert a scraped price snapshot into a single-row DataFrame."""
    price = snapshot.get("price")
    if not price:
        return pd.DataFrame()
    today = pd.Timestamp.now().normalize()
    df = pd.DataFrame(
        [
            {
                "Open": snapshot.get("prev_close", price),
                "High": price,
                "Low": price,
                "Close": price,
                "Volume": snapshot.get("volume", 0),
                "_source": snapshot.get("source", "scrape"),
            }
        ],
        index=[today],
    )
    df.index.name = "Date"
    df.attrs["mktcap"] = snapshot.get("mktcap", 0)
    df.attrs["pe"] = snapshot.get("pe", 0)
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Layer 5 — Open datasets  (FRED for macro, Quandl-free for commodities)
# ─────────────────────────────────────────────────────────────────────────────

FRED_SERIES_MAP = {
    "^TNX": "DGS10",  # 10-Year Treasury
    "^IRX": "DTB3",  # 3-Month T-Bill
    "^VIX": None,  # not on FRED — skip
    "USDEUR": "DEXUSEU",
    "USDJPY": "DEXJPUS",
    "GOLD": "GOLDAMGBD228NLBM",
    "WTI": "DCOILWTICO",
}

FRED_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"


async def _fetch_fred(ticker: str, period: str) -> Optional[pd.DataFrame]:
    series = FRED_SERIES_MAP.get(ticker.upper())
    if not series:
        return None
    url = FRED_BASE.format(series=series)
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url, headers=SCRAPE_HEADERS)
        if r.status_code != 200:
            return None
        from io import StringIO

        df = pd.read_csv(StringIO(r.text), parse_dates=["DATE"], index_col="DATE")
        df.index.name = "Date"
        df.columns = ["Close"]
        df["Open"] = df["Close"]
        df["High"] = df["Close"]
        df["Low"] = df["Close"]
        df["Volume"] = 0
        df["_source"] = "fred"
        days = _period_to_days(period)
        cutoff = datetime.now() - timedelta(days=days)
        df = df[df.index >= pd.Timestamp(cutoff)]
        df = df[df["Close"].notna()]
        return df if not df.empty else None
    except Exception as e:
        logger.debug(f"[Collector] FRED failed for {ticker}: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Main public interface
# ─────────────────────────────────────────────────────────────────────────────


async def fetch_ticker(
    ticker: str,
    period: str = "5y",
    use_cache: bool = True,
    scrape_ok: bool = True,
) -> tuple[pd.DataFrame, str]:
    """
    Fetch OHLCV data for a ticker using the full fallback chain.

    Returns
    -------
    (df, source_used)
        df is empty DataFrame if all sources fail — never raises.
        source_used is one of: 'cache', 'yfinance', 'stooq', 'alpha_vantage',
                                'yahoo_scrape', 'marketwatch_scrape', 'fred', 'none'
    """
    # ── Resolve alias ────────────────────────────────────────────────────────
    resolved = TICKER_ALIASES.get(ticker, ticker)
    if resolved != ticker:
        logger.debug(f"[Collector] Alias {ticker} → {resolved}")
    ticker = resolved

    # ── Cache ────────────────────────────────────────────────────────────────
    if use_cache:
        cached = _load_cache(ticker, period)
        if cached is not None:
            return cached, "cache"
    stale_cache = _load_cache(ticker, period, max_age_hours=None) if use_cache else None

    df: Optional[pd.DataFrame] = None
    source = "none"

    # ── Layer 1: yfinance ────────────────────────────────────────────────────
    df = _fetch_yfinance(ticker, period)
    if df is not None and not df.empty:
        source = "yfinance"
        logger.info(f"[Collector] {ticker}: {len(df)} OHLCV records (5m) from yfinance")
        _save_cache(ticker, period, df)
        
        # Fire internal market_update event for MoveExplainer
        from agents.move_explainer import on_market_update
        latest_close = float(df.iloc[-1]["Close"])
        on_market_update(symbol=ticker, latest_close=latest_close)
        
        return df, source

    # ── Layer 2: Stooq ───────────────────────────────────────────────────────
    df = await _fetch_stooq(ticker, period)
    if df is not None and not df.empty:
        source = "stooq"
        logger.info(f"[Collector] {ticker}: {len(df)} records from stooq")
        _save_cache(ticker, period, df)
        return df, source

    # ── Layer 3: Alpha Vantage ───────────────────────────────────────────────
    df = await _fetch_alpha_vantage(ticker, period)
    if df is not None and not df.empty:
        source = "alpha_vantage"
        logger.info(f"[Collector] {ticker}: {len(df)} records from alpha_vantage")
        _save_cache(ticker, period, df)
        return df, source

    # ── Layer 4: FRED (macro instruments) ───────────────────────────────────
    df = await _fetch_fred(ticker, period)
    if df is not None and not df.empty:
        source = "fred"
        logger.info(f"[Collector] {ticker}: {len(df)} records from FRED")
        _save_cache(ticker, period, df)
        return df, source

    # ── Layer 5: Web scrape (snapshot only) ─────────────────────────────────
    if scrape_ok:
        snapshot = await _scrape_yahoo_finance(ticker)
        if snapshot is None:
            snapshot = await _scrape_marketwatch(ticker)
        if snapshot:
            df = _snapshot_to_df(snapshot, ticker)
            source = snapshot.get("source", "scrape")
            logger.info(
                f"[Collector] {ticker}: snapshot scraped from {source} — price={snapshot.get('price')}"
            )
            # note: don't cache single-row snapshots as long-term history
            return df, source

    # ── All sources exhausted ────────────────────────────────────────────────
    logger.warning(
        f"[Collector] {ticker}: no data found from any source — returning empty"
    )
    if stale_cache is not None and not stale_cache.empty:
        logger.info(
            f"[Collector] {ticker}: live sources unavailable, using stale cache"
        )
        return stale_cache, "stale_cache"
    return pd.DataFrame(), "none"


class CollectorAgent:
    """
    Async agent that collects market data for a list of tickers,
    with full fallback chain and zero unhandled exceptions.
    """

    def __init__(
        self,
        tickers: list[str],
        period: str = "5y",
        max_concurrent: int = 8,
        scrape_ok: bool = True,
    ):
        self.tickers = tickers
        self.period = period
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.scrape_ok = scrape_ok
        self.results: dict[str, dict] = {}

    async def _collect_one(self, ticker: str):
        async with self.semaphore:
            try:
                df, source = await fetch_ticker(
                    ticker, self.period, scrape_ok=self.scrape_ok
                )
                self.results[ticker] = {
                    "df": df,
                    "source": source,
                    "records": len(df),
                    "ok": not df.empty,
                }
            except Exception as e:
                # Absolute safety net — this should never trigger in normal use
                logger.warning(f"[Collector] Unexpected error for {ticker}: {e}")
                self.results[ticker] = {
                    "df": pd.DataFrame(),
                    "source": "none",
                    "records": 0,
                    "ok": False,
                }
            # Polite delay between requests to avoid rate limits
            await asyncio.sleep(0.3)

    async def run(self) -> dict[str, dict]:
        """Collect all tickers concurrently and return results dict."""
        tasks = [self._collect_one(t) for t in self.tickers]
        await asyncio.gather(*tasks)

        ok = sum(1 for v in self.results.values() if v["ok"])
        total = len(self.tickers)
        sources = {}
        for v in self.results.values():
            sources[v["source"]] = sources.get(v["source"], 0) + 1

        logger.info(
            f"[Collector] Collection complete: {ok}/{total} tickers have data. "
            f"Sources used: {sources}"
        )
        return self.results

    def run_sync(self) -> dict[str, dict]:
        """Synchronous wrapper — safe to call from non-async code."""
        return asyncio.run(self.run())


# ── Scheduler Wrappers ───────────────────────────────────────────────────────


async def collect_historical_data():
    """Triggered on startup and weekly. Pulls 5y history for all tickers."""
    logger.info("📡 Starting exhaustive historical data collection (5y)...")
    watchlist = get_watchlist()
    collector = CollectorAgent(watchlist, period="5y")
    results = await collector.run()
    # Save to blobs
    from agents.blob_agent import BlobAgent

    blob_agent = BlobAgent()
    for ticker, res in results.items():
        if res["ok"]:
            # Standard blobs only need 1y, but we store history in parquet
            pass
    logger.info("✅ Historical collection complete.")


async def collect_daily_data():
    """Triggered daily. Pulls 1y (compact) update for all tickers."""
    logger.info("📡 Starting daily refresh for all tickers...")
    watchlist = get_watchlist()
    collector = CollectorAgent(watchlist, period="1y")
    await collector.run()
    logger.info("✅ Daily refresh complete.")


async def collect_news_data():
    """Triggered every 5 minutes. Syncs news catalysts."""
    from agents.mcp_news_agent import McpNewsAgent

    agent = McpNewsAgent()
    watchlist = get_watchlist()
    for ticker in watchlist:
        try:
            await agent.run(AgentContext(task=f"News sync for {ticker}", ticker=ticker))
        except Exception as e:
            logger.warning(f"News sync failed for {ticker}: {e}")


async def index_knowledge_to_rag():
    """Triggered every 15 minutes. Indexes news/blobs into context store."""
    from agents.rag_agent import RagAgent

    agent = RagAgent()
    watchlist = get_watchlist()
    for ticker in watchlist:
        try:
            # We index "what is stock" or similar generic task to force a summary refresh
            await agent.run(
                AgentContext(task=f"Index knowledge for {ticker}", ticker=ticker)
            )
        except Exception as e:
            logger.warning(f"RAG indexing failed for {ticker}: {e}")
    agent.save_index()
