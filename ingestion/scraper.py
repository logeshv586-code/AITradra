from playwright.async_api import async_playwright
from core.logger import get_logger
from ingestion.store import CompressedDataStore
import asyncio

logger = get_logger(__name__)

class LightpandaMarketScraper:
    """Autonomously extracts live market data using Lightpanda CDP."""

    def __init__(self, cdp_url="http://localhost:9222"):
        self.cdp_url = cdp_url
        self.store = CompressedDataStore()

    async def scrape_ticker(self, ticker: str):
        """Connects to Lightpanda CDP, navigates to financial summary, and extracts trend data."""
        logger.info(f"Connecting to Lightpanda browser at {self.cdp_url} to scrape {ticker}...")
        
        try:
            async with async_playwright() as p:
                # Connect directly to the Lightpanda headless browser over CDP
                browser = await p.chromium.connect_over_cdp(self.cdp_url)
                context = await browser.new_context()
                page = await context.new_page()

                # Using a generic public finance URL for live pricing details
                url = f"https://finance.yahoo.com/quote/{ticker}"
                logger.info(f"Navigating to {url}")
                
                # Navigate and wait for DOM load
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                # Extract real-time price using specific Yahoo Finance selector
                # Playwright selector logic: identify the active primary price header
                locators = await page.locator("fin-streamer[data-field='regularMarketPrice']").all()
                price_text = await locators[0].inner_text() if locators else "0.00"
                
                # Extract daily volume
                vol_locators = await page.locator("fin-streamer[data-field='regularMarketVolume']").all()
                volume_text = await vol_locators[0].inner_text() if vol_locators else "0"
                
                # Parse to floats
                live_price = float(price_text.replace(',', '')) if price_text != "0.00" else None
                live_volume = int(volume_text.replace(',', '')) if volume_text != "0" else None

                scraped_dataset = {
                    "source": "Lightpanda Live Extract",
                    "ticker": ticker,
                    "live_price": live_price,
                    "live_volume": live_volume,
                }
                
                # Store it structurally into our zlib compressed db
                if live_price:
                    self.store.save_live_data(ticker, "live_pricing", scraped_dataset)
                else:
                    logger.warning(f"Failed to extract meaningful price for {ticker}")

                await page.close()
                await browser.close()

        except Exception as e:
            logger.error(f"Lightpanda CDP scraping failed: {e}")
