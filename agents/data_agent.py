import yfinance as yf
from datetime import datetime
import json
import os

class DataAgent:
    """Agent 1: Data Collector Agent - Fetches stock data daily."""
    
    def __init__(self):
        self.name = "DataCollectorAgent"

    def fetch_stock_data(self, symbol: str):
        print(f"[{self.name}] Fetching data for {symbol}...")
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Get latest close price if currentPrice is missing
            price = info.get("currentPrice") or info.get("regularMarketPrice")
            if price is None:
                hist = ticker.history(period="1d")
                if not hist.empty:
                    price = hist['Close'].iloc[-1]
            
            data = {
                "symbol": symbol,
                "name": info.get("longName"),
                "price": round(float(price), 2) if price else 0.0,
                "change_pct": round(float(info.get("regularMarketChangePercent", 0)), 2),
                "volume": info.get("regularMarketVolume") or info.get("volume"),
                "market_cap": info.get("marketCap"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "exchange": info.get("exchange"),
                "timestamp": datetime.now().isoformat()
            }
            return data
        except Exception as e:
            print(f"[{self.name}] Error fetching {symbol}: {e}")
            return {"symbol": symbol, "error": str(e), "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    agent = DataAgent()
    print(json.dumps(agent.fetch_stock_data("AAPL"), indent=2))
