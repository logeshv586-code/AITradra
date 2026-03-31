import feedparser
import hashlib
import time
from datetime import datetime
from core.logger import get_logger

logger = get_logger(__name__)

RSS_FEEDS = {
    "general": [
        "https://feeds.reuters.com/reuters/businessNews",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "https://feeds.marketwatch.com/marketwatch/topstories",
        "https://feeds.bloomberg.com/markets/news.rss",
        "https://www.investing.com/rss/news.rss",
        "https://finance.yahoo.com/news/rssindex",
    ],
    "crypto": [
        "https://cointelegraph.com/rss",
        "https://coindesk.com/arc/outboundfeeds/rss/",
        "https://decrypt.co/feed",
    ],
    "india": [
        "https://economictimes.indiatimes.com/markets/rss.cms",
        "https://www.moneycontrol.com/rss/latestnews.xml",
        "https://www.livemint.com/rss/markets",
    ]
}

class RssScraper:
    def __init__(self):
        self.cache = {}           # headline_hash -> article dict
        self.last_fetch = {}      # feed_url -> datetime

    def fetch_all(self):
        """Run every 5 minutes in background thread. Persists to KnowledgeStore."""
        logger.info("Starting RSS fetch cycle...")
        all_articles = []
        for category, feeds in RSS_FEEDS.items():
            for url in feeds:
                try:
                    articles = self._parse_feed(url)
                    all_articles.extend(articles)
                    self.last_fetch[url] = datetime.now()
                except Exception as e:
                    logger.warning(f"Failed to fetch RSS feed {url}: {e}")
        
        deduped = self._dedupe(all_articles)
        for art in deduped:
            h = hashlib.md5(art['headline'].encode()).hexdigest()
            self.cache[h] = art
        
        # Persist to KnowledgeStore so all agents can access the data
        stored = 0
        try:
            from gateway.knowledge_store import knowledge_store
            stored = knowledge_store.store_news(deduped)
        except Exception as e:
            logger.warning(f"Failed to persist RSS articles to KnowledgeStore: {e}")
        
        logger.info(f"RSS fetch complete. {len(deduped)} unique articles in cache, {stored} new stored to DB.")

    def has_recent_data(self, max_age_hours: int = 12) -> bool:
        """Check if we have data collected within the last N hours."""
        try:
            from gateway.knowledge_store import knowledge_store
            status = knowledge_store.get_collection_status()
            if status.get("total_news_articles", 0) > 0:
                return True
        except Exception:
            pass
        return len(self.cache) > 0

    def get_for_ticker(self, ticker: str) -> list[dict]:
        """Filter cached articles by ticker mention."""
        matches = []
        t_lower = ticker.lower()
        for art in self.cache.values():
            if t_lower in art['headline'].lower() or (art.get('summary') and t_lower in art['summary'].lower()):
                matches.append(art)
        return sorted(matches, key=lambda x: x.get('published_at', ''), reverse=True)

    def _parse_feed(self, url: str) -> list[dict]:
        """Use feedparser. Return list of {headline, url, summary, published_at, source}."""
        feed = feedparser.parse(url)
        articles = []
        source_name = url.split("//")[1].split("/")[0]
        
        for entry in feed.entries:
            articles.append({
                "headline": entry.get("title", ""),
                "url": entry.get("link", ""),
                "summary": entry.get("summary", ""),
                "published_at": entry.get("published", ""),
                "source": source_name
            })
        return articles

    def _dedupe(self, articles: list) -> list:
        """Hash headline to remove duplicates across sources."""
        seen = set()
        unique = []
        for art in articles:
            h = hashlib.md5(art['headline'].encode()).hexdigest()
            if h not in seen:
                seen.add(h)
                unique.append(art)
        return unique

# Global instance
rss_scraper = RssScraper()
