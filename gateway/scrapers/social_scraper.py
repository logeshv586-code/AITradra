import requests
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
            "User-Agent": "AITradra-Market-Research/2.0"
        })

    @staticmethod
    def _sentiment_score(bull_count: int, bear_count: int) -> float:
        directional = bull_count + bear_count
        if directional <= 0:
            return 0.0
        return round(max(min((bull_count - bear_count) / directional, 1.0), -1.0), 3)

    def get_sentiment(self, ticker: str) -> dict:
        """Return normalized social sentiment plus legacy Reddit display fields.

        A network/provider failure is never represented as fabricated neutral
        sentiment. Callers can distinguish a real zero-mention result from an
        unavailable source using ``data_available`` / ``is_estimated`` / ``source``.
        """
        try:
            posts = self._search_reddit(ticker)
            mentions = len(posts)

            bullish = ["bull", "buy", "long", "call", "moon", "growth", "undervalued"]
            bearish = ["bear", "sell", "short", "put", "crash", "drop", "overvalued"]

            bull_count = 0
            bear_count = 0
            for post in posts:
                text = (post.get("title", "") + " " + post.get("selftext", "")).lower()
                if any(word in text for word in bullish):
                    bull_count += 1
                if any(word in text for word in bearish):
                    bear_count += 1

            sentiment = "neutral"
            if bull_count > bear_count * 1.5:
                sentiment = "positive"
            elif bear_count > bull_count * 1.5:
                sentiment = "negative"

            score = self._sentiment_score(bull_count, bear_count)
            directional = bull_count + bear_count
            ratio = f"{int(bull_count / directional * 100)}% bull" if directional > 0 else "N/A"

            return {
                "score": score,
                "mentions": mentions,
                "source": "reddit",
                "data_available": True,
                "is_estimated": False,
                "reddit_mentions_24h": mentions,
                "reddit_sentiment": sentiment,
                "top_post_title": posts[0].get("title", "") if posts else "N/A",
                "top_post_url": f"https://reddit.com{posts[0].get('permalink', '')}" if posts else "N/A",
                "bull_bear_ratio": ratio,
                "bullish_posts": bull_count,
                "bearish_posts": bear_count,
            }
        except Exception as exc:
            logger.warning(f"Social scrape failed for {ticker}: {type(exc).__name__}")
            return {
                "score": 0.0,
                "mentions": 0,
                "source": "none",
                "data_available": False,
                "is_estimated": True,
                "reddit_mentions_24h": 0,
                "reddit_sentiment": "unavailable",
                "top_post_title": "N/A",
                "top_post_url": "N/A",
                "bull_bear_ratio": "N/A",
                "bullish_posts": 0,
                "bearish_posts": 0,
            }

    def _search_reddit(self, ticker: str) -> list[dict]:
        """Fetch recent Reddit search results and fail loudly on provider errors."""
        url = f"https://www.reddit.com/search.json?q={ticker}&sort=new&limit=25"
        response = self.session.get(url, timeout=10)
        response.raise_for_status()
        payload = response.json()
        return [child["data"] for child in payload.get("data", {}).get("children", []) if isinstance(child, dict) and isinstance(child.get("data"), dict)]


social_scraper = SocialScraper()
