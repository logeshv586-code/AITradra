import yfinance as yf
from datetime import datetime
import json

class NewsAgent:
    """Agent 4: News Intelligence Agent - Explains 'Why price moved'."""
    
    def __init__(self):
        self.name = "NewsIntelligenceAgent"

    def fetch_news(self, symbol: str):
        print(f"[{self.name}] Fetching news for {symbol}...")
        try:
            ticker = yf.Ticker(symbol)
            news = ticker.news
            
            processed_news = []
            for item in news[:5]:
                processed_news.append({
                    "title": item.get("title"),
                    "publisher": item.get("publisher"),
                    "link": item.get("link"),
                    "timestamp": datetime.fromtimestamp(item.get("providerPublishTime")).isoformat() if item.get("providerPublishTime") else None,
                    "sentiment": "Neutral" # Placeholder for LLM sentiment analysis
                })
            return processed_news
        except Exception as e:
            print(f"[{self.name}] Error fetching news: {e}")
            return []

if __name__ == "__main__":
    agent = NewsAgent()
    print(json.dumps(agent.fetch_news("AAPL"), indent=2))
