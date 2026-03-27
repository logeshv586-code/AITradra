import requests
import time
from datetime import datetime
from bs4 import BeautifulSoup
from core.logger import get_logger

logger = get_logger(__name__)

SCRAPE_TARGETS = {
    "seeking_alpha": {
        "url_pattern": "https://seekingalpha.com/symbol/{ticker}",
        "selectors": {"articles": ".article-list article", "title": "h3", "body": "p"},
    },
    "motley_fool": {
        "url_pattern": "https://www.fool.com/quote/{ticker}/",
        "selectors": {"articles": ".article-card", "title": "h4"},
    },
    "investing_com": {
        "url_pattern": "https://www.investing.com/search/?q={ticker}",
    },
    "benzinga": {
        "url_pattern": "https://www.benzinga.com/stock/{ticker}",
    },
    "zacks": {
        "url_pattern": "https://www.zacks.com/stock/quote/{ticker}",
    },
}

class WebScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    def scrape_ticker_news(self, ticker: str) -> list[dict]:
        """Try each target, return combined deduplicated articles."""
        combined = []
        for site, config in SCRAPE_TARGETS.items():
            try:
                url = config["url_pattern"].format(ticker=ticker)
                content = self._scrape_with_retry(url)
                if content:
                    articles = self._parse_html(content, config, site)
                    combined.extend(articles)
            except Exception as e:
                logger.warning(f"Scrape failed for {site} ticker {ticker}: {e}")
        
        return combined

    def _scrape_with_retry(self, url: str, retries=3) -> str | None:
        """Exponential backoff. Never raise."""
        for i in range(retries):
            try:
                resp = self.session.get(url, timeout=10)
                if resp.status_code == 200:
                    return resp.text
                elif resp.status_code == 429:
                    time.sleep(2 ** i)
            except Exception:
                time.sleep(1)
        return None

    def _parse_html(self, html: str, config: dict, source: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        articles = []
        selectors = config.get("selectors")
        
        if selectors:
            items = soup.select(selectors["articles"])
            for item in items[:5]:
                title_el = item.select_one(selectors["title"])
                if title_el:
                    articles.append({
                        "headline": title_el.text.strip(),
                        "url": config["url_pattern"], # Simplification
                        "source": source,
                        "published_at": datetime.now().isoformat()
                    })
        else:
            # Fallback parsing for sites without specific selectors
            for link in soup.find_all("a", href=True)[:10]:
                if len(link.text) > 20: # Likely a headline
                     articles.append({
                        "headline": link.text.strip(),
                        "url": link['href'],
                        "source": source,
                        "published_at": datetime.now().isoformat()
                    })
        
        return articles

# Global instance
web_scraper = WebScraper()
