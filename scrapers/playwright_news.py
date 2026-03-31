"""
Stock News Scraper - Uses Playwright to scrape real news from multiple sources
No yfinance. No API rate limits. Pure web scraping like a human does.
"""

import asyncio
import json
import sqlite3
import hashlib
import re
import os
from datetime import datetime, date
from typing import Optional
from playwright.async_api import async_playwright, Page, Browser

# Use the same data directory as the rest of the application
# Use the central KnowledgeStore
from gateway.knowledge_store import knowledge_store

def save_articles(articles: list[dict]):
    """Save articles to the central KnowledgeStore."""
    if not articles:
        return 0
    return knowledge_store.store_news(articles)

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────

TICKERS = re.compile(
    r'\b(RELIANCE|TCS|INFY|HDFCBANK|ICICIBANK|WIPRO|TATAMOTORS|BAJFINANCE|'
    r'HINDUNILVR|SBIN|AAPL|GOOGL|MSFT|AMZN|TSLA|NVDA|META|NFLX|'
    r'ADANIENT|ADANIPORTS|COALINDIA|ONGC|POWERGRID|NTPC|BHARTIARTL)\b',
    re.IGNORECASE
)

def extract_tickers(text: str) -> str:
    found = TICKERS.findall(text)
    return ",".join(set(t.upper() for t in found)) if found else ""

async def safe_goto(page: Page, url: str, timeout: int = 20000):
    try:
        await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        return True
    except Exception:
        return False

# ─────────────────────────────────────────────
#  SOURCE 1 — Google News (RSS)
# ─────────────────────────────────────────────
async def scrape_google_news(page: Page, query: str) -> list[dict]:
    """Scrape Google News RSS feed — no JS needed, ultra fast."""
    articles = []
    rss_url = f"https://news.google.com/rss/search?q={query.replace(' ','+')}&hl=en-IN&gl=IN&ceid=IN:en"
    ok = await safe_goto(page, rss_url)
    if not ok: return articles
    content = await page.content()
    items = re.findall(r'<item>(.*?)</item>', content, re.DOTALL)
    for item in items[:20]:
        title = re.search(r'<title><!\[CDATA\[(.*?)\]\]>', item)
        link = re.search(r'<link>(.*?)</link>', item)
        pub = re.search(r'<pubDate>(.*?)</pubDate>', item)
        desc = re.search(r'<description><!\[CDATA\[(.*?)\]\]>', item)
        if title:
            text = (title.group(1) or "") + " " + (desc.group(1) if desc else "")
            articles.append({
                "title": title.group(1),
                "summary": re.sub(r'<[^>]+>','', desc.group(1)) if desc else "",
                "url": link.group(1) if link else "",
                "source": "Google News",
                "ticker": extract_tickers(text + " " + query),
                "pub_date": pub.group(1) if pub else "",
            })
    print(f"  [Google News] {len(articles)} articles for '{query}'")
    return articles

# ─────────────────────────────────────────────
#  SOURCE 2 — Economic Times Markets
# ─────────────────────────────────────────────
async def scrape_economic_times(page: Page, query: str = "") -> list[dict]:
    articles = []
    url = f"https://economictimes.indiatimes.com/markets/stocks/news"
    ok = await safe_goto(page, url, 25000)
    if not ok: return articles
    try: await page.wait_for_selector(".eachStory", timeout=8000)
    except Exception: pass
    items = await page.query_selector_all(".eachStory, .story-box, article.artData")
    for item in items[:25]:
        try:
            title_el = await item.query_selector("h3 a, h4 a, .story-title a")
            if not title_el: continue
            title = await title_el.inner_text()
            href = await title_el.get_attribute("href") or ""
            if href and not href.startswith("http"): href = "https://economictimes.indiatimes.com" + href
            desc_el = await item.query_selector("p, .story-summary")
            summary = (await desc_el.inner_text()) if desc_el else ""
            articles.append({
                "title": title.strip(), "summary": summary.strip(), "url": href,
                "source": "Economic Times", "ticker": extract_tickers(title + " " + summary),
                "pub_date": date.today().isoformat(),
            })
        except Exception: continue
    print(f"  [Economic Times] {len(articles)} articles")
    return articles

# ─────────────────────────────────────────────
#  SOURCE 3 — Moneycontrol News
# ─────────────────────────────────────────────
async def scrape_moneycontrol(page: Page, query: str = "") -> list[dict]:
    articles = []
    url = "https://www.moneycontrol.com/news/business/stocks/"
    ok = await safe_goto(page, url, 25000)
    if not ok: return articles
    try: await page.wait_for_selector("li.clearfix", timeout=8000)
    except Exception: pass
    items = await page.query_selector_all("li.clearfix, .article-list li, .news_list li")
    for item in items[:25]:
        try:
            title_el = await item.query_selector("h2 a, h3 a, p.news_head a")
            if not title_el: continue
            title = await title_el.inner_text()
            href = await title_el.get_attribute("href") or ""
            desc_el = await item.query_selector("p.news_desc, .news-desc")
            summary = (await desc_el.inner_text()) if desc_el else ""
            articles.append({
                "title": title.strip(), "summary": summary.strip(), "url": href,
                "source": "Moneycontrol", "ticker": extract_tickers(title + " " + summary),
                "pub_date": date.today().isoformat(),
            })
        except Exception: continue
    print(f"  [Moneycontrol] {len(articles)} articles")
    return articles

# ─────────────────────────────────────────────
#  SOURCE 4 — Reuters Finance
# ─────────────────────────────────────────────
async def scrape_reuters(page: Page, query: str) -> list[dict]:
    articles = []
    url = f"https://www.reuters.com/search/news?blob={query.replace(' ','+')}&sortBy=date&dateRange=pastWeek"
    ok = await safe_goto(page, url, 20000)
    if not ok: return articles
    try: await page.wait_for_selector("[data-testid='Heading']", timeout=8000)
    except Exception: pass
    items = await page.query_selector_all("article, [data-testid='MediaStoryCard']")
    for item in items[:15]:
        try:
            title_el = await item.query_selector("h3, [data-testid='Heading']")
            if not title_el: continue
            title = await title_el.inner_text()
            link_el = await item.query_selector("a")
            href = (await link_el.get_attribute("href")) if link_el else ""
            if href and not href.startswith("http"): href = "https://www.reuters.com" + href
            articles.append({
                "title": title.strip(), "summary": "", "url": href,
                "source": "Reuters", "ticker": extract_tickers(title + " " + query),
                "pub_date": date.today().isoformat(),
            })
        except Exception: continue
    print(f"  [Reuters] {len(articles)} articles for '{query}'")
    return articles

# ─────────────────────────────────────────────
#  SOURCE 5 — LiveMint
# ─────────────────────────────────────────────
async def scrape_livemint(page: Page) -> list[dict]:
    articles = []
    url = "https://www.livemint.com/market/stock-market-news"
    ok = await safe_goto(page, url, 25000)
    if not ok: return articles
    try: await page.wait_for_selector(".listingNew", timeout=8000)
    except Exception: pass
    items = await page.query_selector_all(".listingNew li, .storyList li")
    for item in items[:25]:
        try:
            title_el = await item.query_selector("h2 a, h3 a")
            if not title_el: continue
            title = await title_el.inner_text()
            href = await title_el.get_attribute("href") or ""
            if href and not href.startswith("http"): href = "https://www.livemint.com" + href
            articles.append({
                "title": title.strip(), "summary": "", "url": href,
                "source": "LiveMint", "ticker": extract_tickers(title),
                "pub_date": date.today().isoformat(),
            })
        except Exception: continue
    print(f"  [LiveMint] {len(articles)} articles")
    return articles

# ─────────────────────────────────────────────
#  SOURCE 6 — Business Standard
# ─────────────────────────────────────────────
async def scrape_business_standard(page: Page) -> list[dict]:
    articles = []
    url = "https://www.business-standard.com/markets/news"
    ok = await safe_goto(page, url, 25000)
    if not ok: return articles
    try: await page.wait_for_selector(".listing-txt", timeout=8000)
    except Exception: pass
    items = await page.query_selector_all(".listing-txt, article")
    for item in items[:25]:
        try:
            title_el = await item.query_selector("h2 a, h3 a")
            if not title_el: continue
            title = await title_el.inner_text()
            href = await title_el.get_attribute("href") or ""
            if href and not href.startswith("http"): href = "https://www.business-standard.com" + href
            articles.append({
                "title": title.strip(), "summary": "", "url": href,
                "source": "Business Standard", "ticker": extract_tickers(title),
                "pub_date": date.today().isoformat(),
            })
        except Exception: continue
    print(f"  [Business Standard] {len(articles)} articles")
    return articles

# ─────────────────────────────────────────────
#  SOURCE 7 — NDTV Profit
# ─────────────────────────────────────────────
async def scrape_ndtv_profit(page: Page) -> list[dict]:
    articles = []
    url = "https://www.ndtvprofit.com/markets"
    ok = await safe_goto(page, url, 25000)
    if not ok: return articles
    try: await page.wait_for_selector("article", timeout=8000)
    except Exception: pass
    items = await page.query_selector_all("article, .story-card")
    for item in items[:20]:
        try:
            title_el = await item.query_selector("h2 a, h3 a, .headline a")
            if not title_el: continue
            title = await title_el.inner_text()
            href = await title_el.get_attribute("href") or ""
            if href and not href.startswith("http"): href = "https://www.ndtvprofit.com" + href
            articles.append({
                "title": title.strip(), "summary": "", "url": href,
                "source": "NDTV Profit", "ticker": extract_tickers(title),
                "pub_date": date.today().isoformat(),
            })
        except Exception: continue
    print(f"  [NDTV Profit] {len(articles)} articles")
    return articles

# ─────────────────────────────────────────────
#  SOURCE 8 — Seeking Alpha (public feed)
# ─────────────────────────────────────────────
async def scrape_seeking_alpha_rss(page: Page, ticker: str) -> list[dict]:
    articles = []
    rss_url = f"https://seekingalpha.com/api/sa/combined/{ticker.upper()}.xml"
    ok = await safe_goto(page, rss_url, 15000)
    if not ok: return articles
    content = await page.content()
    items = re.findall(r'<item>(.*?)</item>', content, re.DOTALL)
    for item in items[:10]:
        title = re.search(r'<title><!\[CDATA\[(.*?)\]\]>', item)
        link = re.search(r'<link>(.*?)</link>', item)
        if title:
            articles.append({
                "title": title.group(1), "summary": "", "url": link.group(1) if link else "",
                "source": "Seeking Alpha", "ticker": ticker.upper(),
                "pub_date": date.today().isoformat(),
            })
    print(f"  [Seeking Alpha] {len(articles)} articles for {ticker}")
    return articles

# ─────────────────────────────────────────────
#  MASTER SCRAPER
# ─────────────────────────────────────────────

async def run_scraper(query: str, tickers: list[str] = None, headless: bool = True) -> int:
    """
    Runs all scrapers and saves results to the central KnowledgeStore.
    Returns total new articles saved.
    """
    tickers = tickers or []
    all_articles = []

    async with async_playwright() as pw:
        browser: Browser = await pw.chromium.launch(
            headless=headless,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="en-IN",
        )
        page = await context.new_page()
        # Block heavy assets
        await page.route("**/*.{png,jpg,jpeg,gif,webp,svg,mp4,woff,woff2}", lambda r: r.abort())

        print("\n🔍 Scraping Google News RSS...")
        all_articles += await scrape_google_news(page, query + " stock market")

        if tickers:
            for ticker in tickers[:3]:
                all_articles += await scrape_google_news(page, ticker + " stock news")

        print("\n🔍 Scraping Economic Times...")
        all_articles += await scrape_economic_times(page, query)

        print("\n🔍 Scraping Moneycontrol...")
        all_articles += await scrape_moneycontrol(page, query)

        print("\n🔍 Scraping LiveMint...")
        all_articles += await scrape_livemint(page)

        print("\n🔍 Scraping Business Standard...")
        all_articles += await scrape_business_standard(page)

        print("\n🔍 Scraping NDTV Profit...")
        all_articles += await scrape_ndtv_profit(page)

        print("\n🔍 Scraping Reuters...")
        all_articles += await scrape_reuters(page, query)

        if tickers:
            for ticker in tickers[:2]:
                print(f"\n🔍 Seeking Alpha: {ticker}...")
                all_articles += await scrape_seeking_alpha_rss(page, ticker)

        await browser.close()

    saved = save_articles(all_articles)
    print(f"\n✅ Scraped {len(all_articles)} articles | {saved} new saved to KnowledgeStore")
    return saved

if __name__ == "__main__":
    import sys
    query = sys.argv[1] if len(sys.argv) > 1 else "Indian stock market"
    tickers = sys.argv[2:] if len(sys.argv) > 2 else []
    asyncio.run(run_scraper(query, tickers))
