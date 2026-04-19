import asyncio
import os
import sys

# Ensure we can import from the project root
sys.path.append(os.getcwd())

async def refresh():
    from gateway.data_engine import data_engine
    
    tickers = ["NFLX", "AAPL", "TSLA", "BTC-USD"]
    print(f"Restoring intelligence for: {tickers}")
    
    for ticker in tickers:
        print(f"\nProcessing {ticker}...")
        try:
            # 1. Force price scrape (allow_scrape=True triggers collector)
            print(f"  Fetching price action and fundamentals...")
            price_data = await data_engine.get_price_data(ticker, allow_scrape=True)
            print(f"  Result: ${price_data.get('px', 0)} (Source: {price_data.get('source_used')})")
            
            # 2. Force news scrape
            print(f"  Fetching latest news...")
            news_items = await data_engine.get_news(ticker, allow_scrape=True)
            print(f"  Result: Found {len(news_items)} recent headlines.")
            
        except Exception as e:
            print(f"  Error processing {ticker}: {e}")

    print("\nRestoration complete. Frontend should now show data.")

if __name__ == "__main__":
    asyncio.run(refresh())
