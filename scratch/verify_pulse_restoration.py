
import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gateway.data_engine import data_engine
from gateway.knowledge_store import knowledge_store
from core.config import settings

async def verify():
    ticker = "RELIANCE.NS" # Should have data if synced
    print(f"--- Checking {ticker} ---")
    
    # Force a fetch if missing
    data = await data_engine.get_price_data(ticker, allow_scrape=True)
    print(f"Price Source: {data.get('source_used')}")
    print(f"Price: {data.get('px')}")
    ohlcv = data.get('ohlcv', [])
    print(f"OHLCV Points in Response: {len(ohlcv)}")
    
    # Check DB directly
    db_history = knowledge_store.get_ohlcv_history(ticker, days=100)
    print(f"DB History Points: {len(db_history)}")
    
    # Test a NEW ticker (unlikely to be in DB)
    new_ticker = "ADBE" 
    print(f"\n--- Checking NEW ticker: {new_ticker} ---")
    data_new = await data_engine.get_price_data(new_ticker, allow_scrape=True)
    print(f"Price Source: {data_new.get('source_used')}")
    print(f"OHLCV Points in Response: {len(data_new.get('ohlcv', []))}")
    
    db_history_new = knowledge_store.get_ohlcv_history(new_ticker, days=100)
    print(f"DB History Points after fetch: {len(db_history_new)}")
    
    # Check NEWS
    news = await data_engine.get_news(new_ticker, allow_scrape=True)
    print(f"News items retrieved: {len(news)}")
    if news:
        print(f"Latest Headline: {news[0].get('headline')}")

if __name__ == "__main__":
    asyncio.run(verify())
