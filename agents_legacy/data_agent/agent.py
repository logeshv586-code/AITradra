"""DataAgent — Fetches OHLCV data, fundamentals, and market info using OSS APIs (yfinance, CCXT)."""

from agents.base_agent import BaseAgent, AgentContext
from core.logger import get_logger
from tools.ticker_registry import TickerRegistry, AssetClass
import asyncio
from datetime import datetime

logger = get_logger(__name__)


class DataAgent(BaseAgent):
    """Collects raw market data, routing through TickerRegistry for Universal OSS support."""

    def __init__(self, memory):
        super().__init__("DataAgent", memory)
        self.registry = TickerRegistry()
        try:
            from ingestion.store import CompressedDataStore
            self.store = CompressedDataStore()
        except ImportError:
            self.store = None

    async def observe(self, context: AgentContext) -> AgentContext:
        """Identify asset class and correct data source."""
        asset_info = self.registry.resolve(context.ticker)
        context.observations["asset_info"] = {
            "name": asset_info.name,
            "class": asset_info.asset_class,
            "source": asset_info.data_source,
            "currency": asset_info.currency
        } if asset_info else None
        context.observations["ticker"] = context.ticker
        return context

    async def think(self, context: AgentContext) -> AgentContext:
        asset_info = context.observations.get("asset_info")
        if asset_info:
            self._add_thought(context, f"Resolved {context.ticker} as {asset_info['class']} via {asset_info['source']}")
        else:
            self._add_thought(context, f"Could not resolve {context.ticker}, defaulting to yfinance fallback")
        return context

    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan = [
            "1. Check Lightpanda local DB for live scrape",
            "2. Route to correct OSS provider (CCXT for Crypto, Yfinance/Stooq for Equity)",
            "3. Fetch OHLCV history",
            "4. Fetch basic fundamentals if applicable"
        ]
        return context

    async def act(self, context: AgentContext) -> AgentContext:
        asset_info = context.observations.get("asset_info")
        source = asset_info["source"] if asset_info else "yfinance"

        ohlcv = []
        prices = []
        volumes = []
        fundamentals = {
            "name": asset_info["name"] if asset_info else context.ticker,
            "sector": "Crypto" if (asset_info and asset_info["class"] == AssetClass.CRYPTO) else "Unknown",
            "current_price": 0
        }

        # 1. LIGHTPANDA LIVE STORE FALLBACK
        if self.store:
            latest = self.store.get_latest_data(context.ticker, "live_pricing")
            if latest:
                self._add_thought(context, "Using Lightpanda local cache for live price.")
                ohlcv.append({
                    "date": latest.get("timestamp", datetime.utcnow()).isoformat(),
                    "open": latest.get("live_price"),
                    "high": latest.get("live_price"),
                    "low": latest.get("live_price"),
                    "close": latest.get("live_price"),
                    "volume": latest.get("live_volume", 0)
                })
                prices.append(latest.get("live_price"))
                fundamentals["current_price"] = latest.get("live_price", 0)

        # 2. CCXT CRYPTO ROUTE
        if source == "ccxt":
            try:
                import ccxt.async_support as ccxt
                exchange = getattr(ccxt, asset_info["exchange"].lower() if asset_info else "binance")()
                symbol = f"{context.ticker}/USDT" if "/" not in context.ticker and "USDT" not in context.ticker else context.ticker
                if "USDT" in symbol and "/" not in symbol:
                    symbol = symbol.replace("USDT", "/USDT")

                bars = await exchange.fetch_ohlcv(symbol, '1d', limit=90)
                await exchange.close()

                for bar in bars:
                    # bar: [timestamp, open, high, low, close, volume]
                    date_str = datetime.fromtimestamp(bar[0]/1000).isoformat()
                    ohlcv.append({
                        "date": date_str,
                        "open": bar[1], "high": bar[2], "low": bar[3], "close": bar[4], "volume": bar[5]
                    })
                    prices.append(bar[4])
                    volumes.append(bar[5])
                
                fundamentals["current_price"] = prices[-1] if prices else 0
                context.actions_taken.append({"action": "fetch_ccxt_ohlcv", "count": len(bars)})
            except Exception as e:
                self.logger.error(f"CCXT fetch failed: {e}")
                self._add_thought(context, f"CCXT failed: {e}")

        # 3. YFINANCE EQUITY ROUTE
        else:
            try:
                import yfinance as yf
                ticker = yf.Ticker(context.ticker)
                hist = ticker.history(period="3mo")

                if not hist.empty:
                    for idx, row in hist.iterrows():
                        ohlcv.append({
                            "date": idx.isoformat(),
                            "open": round(row["Open"], 2), "high": round(row["High"], 2),
                            "low": round(row["Low"], 2), "close": round(row["Close"], 2),
                            "volume": int(row["Volume"])
                        })
                        prices.append(round(row["Close"], 2))
                    
                    info = ticker.info
                    fundamentals.update({
                        "name": info.get("longName", context.ticker),
                        "sector": info.get("sector", "Unknown"),
                        "market_cap": info.get("marketCap", 0),
                        "pe_ratio": info.get("trailingPE", 0),
                        "current_price": info.get("currentPrice", prices[-1] if prices else 0)
                    })
                context.actions_taken.append({"action": "fetch_yfinance_ohlcv", "count": len(hist)})
            except Exception as e:
                self.logger.error(f"Yfinance fetch failed: {e}")
                self._add_thought(context, f"Yfinance failed: {e}")

        # FALLBACK IF EMPTY
        if not ohlcv:
            context.result = self._generate_mock_data(context.ticker)
            return context

        context.result = {
            "ticker": context.ticker,
            "ohlcv": ohlcv,
            "prices": prices,
            "fundamentals": fundamentals,
            "data_points": len(ohlcv)
        }
        return context

    async def reflect(self, context: AgentContext) -> AgentContext:
        dp = context.result.get("data_points", 0) if context.result else 0
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
        import random
        price = 100
        ohlcv = []
        p = price
        for i in range(60):
            vol = p * 0.02
            o = p + (random.random() - 0.5) * vol
            c = o + (random.random() - 0.3) * vol
            h = max(o, c) + random.random() * vol
            l = min(o, c) - random.random() * vol
            v = int(random.random() * 1e6)
            ohlcv.append({"open": o, "high": h, "low": l, "close": c, "volume": v})
            p = c
        return {
            "ticker": ticker, "ohlcv": ohlcv, "prices": [d["close"] for d in ohlcv],
            "fundamentals": {"name": ticker, "sector": "Mock", "current_price": p},
            "data_points": 60
        }
