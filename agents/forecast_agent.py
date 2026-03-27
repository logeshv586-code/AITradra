import yfinance as yf
import pandas as pd
from datetime import datetime
import json

class ForecastAgent:
    """Agent 6: Forecast Agent - Predict future price using technical indicators."""
    
    def __init__(self):
        self.name = "ForecastAgent"

    def predict(self, symbol: str):
        print(f"[{self.name}] Predicting forecast for {symbol}...")
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="6mo")
            if len(hist) < 20:
                return {"symbol": symbol, "forecast": "Neutral", "confidence": 50}
                
            # Simple Moving Average based trend
            ma20 = hist['Close'].rolling(window=20).mean()
            current_price = hist['Close'].iloc[-1]
            current_ma20 = ma20.iloc[-1]
            
            trend = "Bullish" if current_price > current_ma20 else "Bearish"
            
            # Simple confidence based on MA crossover distance
            diff = abs(current_price - current_ma20) / current_ma20
            confidence = min(int(50 + (diff * 500)), 85) # Caps at 85% for simple logic
            
            data = {
                "symbol": symbol,
                "forecast": trend,
                "confidence": confidence,
                "period": "Next 7 days",
                "indicators": {
                    "current_price": round(current_price, 2),
                    "ma20": round(current_ma20, 2)
                }
            }
            return data
        except Exception as e:
            print(f"[{self.name}] Error in forecast: {e}")
            return {}

if __name__ == "__main__":
    agent = ForecastAgent()
    print(json.dumps(agent.predict("AAPL"), indent=2))
