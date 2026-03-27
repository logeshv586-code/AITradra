import yfinance as yf
from datetime import datetime, timedelta
import json

class PriceAgent:
    """Agent 5: Price Movement Agent - Track stock movement."""
    
    def __init__(self):
        self.name = "PriceMovementAgent"

    def analyze_movement(self, symbol: str):
        print(f"[{self.name}] Analyzing movement for {symbol}...")
        try:
            ticker = yf.Ticker(symbol)
            # Fetch history for 1 month to calculate changes
            hist = ticker.history(period="1mo")
            if hist.empty:
                return {}
                
            current_price = hist['Close'].iloc[-1]
            
            # 1 Day Change
            prev_day_price = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
            day_change = ((current_price - prev_day_price) / prev_day_price) * 100
            
            # 1 Week Change
            prev_week_price = hist['Close'].iloc[-5] if len(hist) > 5 else hist['Close'].iloc[0]
            week_change = ((current_price - prev_week_price) / prev_week_price) * 100
            
            # 1 Month Change
            prev_month_price = hist['Close'].iloc[0]
            month_change = ((current_price - prev_month_price) / prev_month_price) * 100
            
            data = {
                "symbol": symbol,
                "current_price": round(current_price, 2),
                "day_change": round(day_change, 2),
                "week_change": round(week_change, 2),
                "month_change": round(month_change, 2),
                "summary": f"{symbol} is {'up' if week_change > 0 else 'down'} {abs(round(week_change, 2))}% this week."
            }
            return data
        except Exception as e:
            print(f"[{self.name}] Error analyzing movement: {e}")
            return {}

if __name__ == "__main__":
    agent = PriceMovementAgent()
    print(json.dumps(agent.analyze_movement("AAPL"), indent=2))
