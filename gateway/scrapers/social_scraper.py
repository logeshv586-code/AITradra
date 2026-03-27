import requests
from datetime import datetime
from core.logger import get_logger

logger = get_logger(__name__)

REDDIT_SUBREDDITS = [
    "stocks", "investing", "wallstreetbets", "SecurityAnalysis",
    "StockMarket", "options", "Daytrading", "IndiaInvestments"
]

class SocialScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "AXIOM-Bot/2.0"
        })

    def get_sentiment(self, ticker: str) -> dict:
        """
        Returns: {
            reddit_mentions_24h,
            reddit_sentiment,    # positive/negative/neutral
            top_post_title,
            top_post_url,
            bull_bear_ratio,     # e.g. "65% bull"
        }
        """
        try:
            posts = self._search_reddit(ticker)
            mentions = len(posts)
            
            # Simple keyword-based sentiment for now
            bullish = ["bull", "buy", "long", "call", "moon", "growth", "undervalued"]
            bearish = ["bear", "sell", "short", "put", "crash", "drop", "overvalued"]
            
            bull_count = 0
            bear_count = 0
            
            for p in posts:
                txt = (p['title'] + " " + p.get('selftext', '')).lower()
                if any(w in txt for w in bullish): bull_count += 1
                if any(w in txt for w in bearish): bear_count += 1
            
            sentiment = "neutral"
            if bull_count > bear_count * 1.5: sentiment = "positive"
            if bear_count > bull_count * 1.5: sentiment = "negative"
            
            ratio = f"{int(bull_count/(bull_count+bear_count)*100)}% bull" if (bull_count+bear_count) > 0 else "50% bull"
            
            return {
                "reddit_mentions_24h": mentions,
                "reddit_sentiment": sentiment,
                "top_post_title": posts[0]['title'] if posts else "N/A",
                "top_post_url": f"https://reddit.com{posts[0]['permalink']}" if posts else "N/A",
                "bull_bear_ratio": ratio
            }
        except Exception as e:
            logger.warning(f"Social scrape failed for {ticker}: {e}")
            return {
                "reddit_mentions_24h": 0,
                "reddit_sentiment": "neutral",
                "top_post_title": "N/A",
                "top_post_url": "N/A",
                "bull_bear_ratio": "50% bull"
            }

    def _search_reddit(self, ticker: str) -> list[dict]:
        """GET https://old.reddit.com/search.json?q={ticker}&sort=new&limit=25"""
        url = f"https://www.reddit.com/search.json?q={ticker}&sort=new&limit=25"
        resp = self.session.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return [child['data'] for child in data.get('data', {}).get('children', [])]
        return []

# Global instance
social_scraper = SocialScraper()
