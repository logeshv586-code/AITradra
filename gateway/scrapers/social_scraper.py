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
            "User-Agent": "AITradra-Market-Research/2.1"
        })

    @staticmethod
    def _sentiment_score(bull_count: int, bear_count: int) -> float:
        directional = bull_count + bear_count
        if directional <= 0:
            return 0.0
        return round(max(min((bull_count - bear_count) / directional, 1.0), -1.0), 3)

    def get_sentiment(self, ticker: str) -> dict:
        """Return normalized social sentiment from a real public social source.

        Reddit remains the primary source. If Reddit rejects or rate-limits the
        request, Stocktwits' public symbol stream is attempted. A total provider
        failure is never represented as fabricated neutral sentiment.
        """
        providers = (
            ("reddit", self._search_reddit),
            ("stocktwits", self._search_stocktwits),
        )
        last_error = None
        for source, fetcher in providers:
            try:
                posts = fetcher(ticker)
                return self._normalize_sentiment(posts, source)
            except Exception as exc:
                last_error = exc
                logger.warning(
                    f"Social provider {source} failed for {ticker}: {type(exc).__name__}"
                )

        logger.warning(
            f"All social providers failed for {ticker}: "
            f"{type(last_error).__name__ if last_error else 'unknown'}"
        )
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

    def _normalize_sentiment(self, posts: list[dict], source: str) -> dict:
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
        first = posts[0] if posts else {}

        return {
            "score": score,
            "mentions": mentions,
            "source": source,
            "data_available": True,
            "is_estimated": False,
            # Keep legacy field names for API/UI compatibility. They represent
            # social mentions when the fallback provider is Stocktwits.
            "reddit_mentions_24h": mentions,
            "reddit_sentiment": sentiment,
            "top_post_title": first.get("title", "N/A") or "N/A",
            "top_post_url": first.get("url", "N/A") or "N/A",
            "bull_bear_ratio": ratio,
            "bullish_posts": bull_count,
            "bearish_posts": bear_count,
        }

    def _search_reddit(self, ticker: str) -> list[dict]:
        """Fetch recent Reddit search results and fail loudly on provider errors."""
        url = f"https://www.reddit.com/search.json?q={ticker}&sort=new&limit=25"
        response = self.session.get(url, timeout=10)
        response.raise_for_status()
        payload = response.json()
        posts = []
        for child in payload.get("data", {}).get("children", []):
            if not isinstance(child, dict) or not isinstance(child.get("data"), dict):
                continue
            data = child["data"]
            posts.append({
                "title": data.get("title", ""),
                "selftext": data.get("selftext", ""),
                "url": f"https://reddit.com{data.get('permalink', '')}" if data.get("permalink") else "N/A",
            })
        return posts

    def _search_stocktwits(self, ticker: str) -> list[dict]:
        """Fallback to Stocktwits' public v2 symbol stream."""
        symbol = ticker.upper().split(".")[0].replace("-USD", "")
        url = f"https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json"
        response = self.session.get(url, timeout=10)
        response.raise_for_status()
        payload = response.json()
        posts = []
        for message in payload.get("messages", []):
            if not isinstance(message, dict):
                continue
            body = message.get("body", "") or ""
            message_id = message.get("id")
            username = (message.get("user") or {}).get("username", "")
            post_url = (
                f"https://stocktwits.com/{username}/message/{message_id}"
                if username and message_id else "N/A"
            )
            posts.append({"title": body, "selftext": "", "url": post_url})
        return posts


social_scraper = SocialScraper()
