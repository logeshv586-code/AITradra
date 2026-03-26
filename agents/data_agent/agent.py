"""DataAgent — Fetches OHLCV data, fundamentals, and market info using yfinance."""

from agents.base_agent import BaseAgent, AgentContext
from core.logger import get_logger

logger = get_logger(__name__)


class DataAgent(BaseAgent):
    """Collects raw market data, prioritizing Lightpanda local encoded DB, falling back to YFinance."""

    def __init__(self, memory: MemoryManager):
        super().__init__("DataWorker", memory)
        try:
            from ingestion.store import CompressedDataStore
            self.store = CompressedDataStore()
        except ImportError:
            self.store = None

    async def observe(self, context: AgentContext) -> AgentContext:
        """Fetch OHLCV and fundamental data."""
        context.observations["ticker"] = context.ticker
        context.observations["data_sources"] = ["lightpanda_db", "yfinance"] if self.store else ["yfinance"]
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        self._add_thought(context, f"Need to fetch OHLCV data for {context.ticker}")
        self._add_thought(context, "Will also collect fundamentals (P/E, market cap, sector)")
        self._add_thought(context, "Data quality check: must have at least 60 days of history")
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan = [
            "1. Attempt to fetch latest live data from Lightpanda DB",
            "2. If no live data or historical needed, fetch 90-day OHLCV from yfinance",
            "3. Fetch company info and fundamentals from yfinance",
            "4. Validate data completeness",
            "5. Normalize and structure output",
        ]
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        import yfinance as yf # Moved import inside act for conditional use
        ohlcv = []
        prices = []
        volumes = []
        fundamentals = {
            "name": context.ticker,
            "sector": "Unknown",
            "industry": "Unknown",
            "market_cap": 0,
            "pe_ratio": 0,
            "current_price": 0,
            "52w_high": 0,
            "52w_low": 0,
            "avg_volume": 0,
            "beta": 1.0,
        }

        # 1. ATTEMPT LIGHTPANDA DB FETCH FIRST
        if self.store:
            latest = self.store.get_latest_data(context.ticker, "live_pricing")
            if latest:
                self._add_thought(context, "Lightpanda encoded local DB has fresh live data! Bypassing YFinance.")
                ohlcv.append({
                    "date": latest.get("timestamp", "").isoformat() if latest.get("timestamp") else "",
                    "open": latest.get("live_price"),
                    "high": latest.get("live_price"),
                    "low": latest.get("live_price"),
                    "close": latest.get("live_price"),
                    "volume": latest.get("live_volume", 0)
                })
                prices.append(latest.get("live_price"))
                volumes.append(latest.get("live_volume", 0))
                # Update current price in fundamentals if available
                fundamentals["current_price"] = latest.get("live_price", 0)

        # 2. FALLBACK TO YFINANCE FOR HISTORICAL
        try:
            # Only fetch historical from yfinance if no live data was added or if more historical data is needed
            if not ohlcv or len(ohlcv) < 60: # Ensure we have enough data points
                ticker = yf.Ticker(context.ticker)

                # Fetch historical data
                hist = ticker.history(period="3mo")

                if hist.empty:
                    self._add_thought(context, "yfinance returned empty dataset")
                    raise ValueError(f"No data found for {context.ticker}")

                for idx, row in hist.iterrows():
                    ohlcv.append({
                        "date": idx.isoformat(),
                        "open": round(row["Open"], 2),
                        "high": round(row["High"], 2),
                        "low": round(row["Low"], 2),
                        "close": round(row["Close"], 2),
                        "volume": int(row["Volume"]),
                    })
                    prices.append(round(row['Close'], 2))
                    volumes.append(int(row['Volume']))

                # Fetch fundamentals
                info = ticker.info
                fundamentals.update({
                    "name": info.get("longName", context.ticker),
                    "sector": info.get("sector", "Unknown"),
                    "industry": info.get("industry", "Unknown"),
                    "market_cap": info.get("marketCap", 0),
                    "pe_ratio": info.get("trailingPE", 0),
                    "current_price": info.get("currentPrice", prices[-1] if prices else 0),
                    "52w_high": info.get("fiftyTwoWeekHigh", 0),
                    "52w_low": info.get("fiftyTwoWeekLow", 0),
                    "avg_volume": info.get("averageVolume", 0),
                    "beta": info.get("beta", 1.0),
                })

            context.result = {
                "ticker": context.ticker,
                "ohlcv": ohlcv,
                "prices": [d["close"] for d in ohlcv],
                "volume": [d["volume"] for d in ohlcv],
                "fundamentals": fundamentals,
                "data_points": len(ohlcv),
            }
            context.actions_taken.append({
                "action": "fetch_ohlcv",
                "data_points": len(ohlcv),
                "source": "yfinance"
            })
        except ImportError:
            # Fallback with mock data if yfinance not installed
            context.result = self._generate_mock_data(context.ticker)
            context.actions_taken.append({"action": "mock_data", "reason": "yfinance not available"})
        except Exception as e:
            context.result = self._generate_mock_data(context.ticker)
            context.errors.append(f"yfinance fetch failed: {str(e)}, using mock data")

        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        result = context.result or {}
        dp = result.get("data_points", 0)
        if dp >= 60:
            context.reflection = f"Collected {dp} data points — sufficient for analysis"
            context.confidence = 0.95
        elif dp > 0:
            context.reflection = f"Only {dp} data points — reduced confidence"
            context.confidence = 0.6
        else:
            context.reflection = "Failed to collect any data"
            context.confidence = 0.1
        return context

    def _generate_mock_data(self, ticker: str) -> dict:
        """Generate realistic mock data as fallback."""
        import random
        price = {"NVDA": 892, "AAPL": 178, "TSLA": 182, "MSFT": 420}.get(ticker, 100)
        ohlcv = []
        p = price * 0.9
        for i in range(60):
            vol = p * 0.022
            o = p + (random.random() - 0.5) * vol
            c = o + (random.random() - 0.3) * vol
            h = max(o, c) + random.random() * vol * 0.6
            l = min(o, c) - random.random() * vol * 0.6
            v = int((50 + random.random() * 80) * 1e6)
            ohlcv.append({"open": round(o,2), "high": round(h,2), "low": round(l,2), "close": round(c,2), "volume": v})
            p = c
        return {
            "ticker": ticker, "ohlcv": ohlcv,
            "prices": [d["close"] for d in ohlcv],
            "volume": [d["volume"] for d in ohlcv],
            "fundamentals": {"name": ticker, "sector": "Tech", "market_cap": 0, "pe_ratio": 0, "current_price": p, "beta": 1.0},
            "data_points": len(ohlcv),
        }
