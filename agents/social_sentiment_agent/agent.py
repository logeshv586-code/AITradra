"""
SOCIAL SENTIMENT AGENT — Claude Flow Architecture (100% OSS)
Monitors Reddit (praw), RSS news feeds, and Twitter for sentiment signals.
AI model: Local FinBERT for financial text classification.

OBSERVE → Scrape Reddit/RSS for mentions of the ticker
THINK   → Assess volume and tone of social mentions
PLAN    → Score sentiment from -1 (extreme fear) to +1 (extreme greed)
ACT     → Fetch posts, classify sentiment, aggregate score
REFLECT → Confidence based on post count and signal clarity
"""

from agents.base_agent import BaseAgent, AgentContext
from core.logger import get_logger
from datetime import datetime

logger = get_logger(__name__)


class SocialSentimentAgent(BaseAgent):
    """Monitors social media for sentiment signals using free APIs and local NLP."""

    SUBREDDITS = ["wallstreetbets", "stocks", "investing", "CryptoCurrency", "options"]

    def __init__(self, memory=None):
        super().__init__("SocialSentimentAgent", memory)

    # ── OBSERVE ──────────────────────────────────────────────
    async def observe(self, context: AgentContext) -> AgentContext:
        context.observations["target_ticker"] = context.ticker
        context.observations["subreddits"] = self.SUBREDDITS
        context.observations["rss_sources"] = [
            "https://feeds.finance.yahoo.com/rss/2.0/headline",
            "https://www.investing.com/rss/news.rss",
        ]
        return context

    # ── THINK ────────────────────────────────────────────────
    async def think(self, context: AgentContext) -> AgentContext:
        self._add_thought(context, f"Scanning Reddit for ${context.ticker} mentions across {len(self.SUBREDDITS)} subreddits")
        self._add_thought(context, "Will use local VADER/FinBERT for sentiment classification")
        self._add_thought(context, "High Reddit volume + positive sentiment = potential momentum play")
        return context

    # ── PLAN ─────────────────────────────────────────────────
    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan = [
            "1. Search Reddit via praw for recent ticker mentions",
            "2. Fetch RSS news headlines mentioning the ticker",
            "3. Run sentiment classification on each post/headline",
            "4. Aggregate: compute mean sentiment, mention volume, and trending score",
            "5. Generate social signal (BULLISH_SOCIAL / BEARISH_SOCIAL / NEUTRAL)",
        ]
        return context

    # ── ACT ──────────────────────────────────────────────────
    async def act(self, context: AgentContext) -> AgentContext:
        ticker = context.ticker
        posts_data = []
        sentiments = []

        # 1. REDDIT via praw (free)
        try:
            import praw
            reddit = praw.Reddit(
                client_id="axiom_reader",
                client_secret="",
                user_agent="AXIOM-SentimentAgent/1.0",
            )
            for sub_name in self.SUBREDDITS[:3]:
                try:
                    subreddit = reddit.subreddit(sub_name)
                    for post in subreddit.search(ticker, sort="new", time_filter="week", limit=10):
                        text = f"{post.title} {post.selftext[:200]}"
                        score = self._classify_sentiment(text)
                        posts_data.append({
                            "source": f"r/{sub_name}",
                            "title": post.title[:100],
                            "score": post.score,
                            "sentiment": score,
                            "created": datetime.fromtimestamp(post.created_utc).isoformat(),
                        })
                        sentiments.append(score)
                except Exception as e:
                    logger.warning(f"Reddit search failed for r/{sub_name}: {e}")
        except ImportError:
            self._add_thought(context, "praw not installed — Reddit scan skipped")
        except Exception as e:
            self._add_thought(context, f"Reddit connection failed: {e}")

        # 2. RSS NEWS FEEDS
        try:
            import feedparser
            for rss_url in context.observations.get("rss_sources", []):
                try:
                    feed = feedparser.parse(rss_url)
                    for entry in feed.entries[:10]:
                        title = entry.get("title", "")
                        if ticker.lower() in title.lower():
                            score = self._classify_sentiment(title)
                            posts_data.append({
                                "source": "rss_news",
                                "title": title[:100],
                                "sentiment": score,
                            })
                            sentiments.append(score)
                except Exception:
                    pass
        except ImportError:
            self._add_thought(context, "feedparser not installed — RSS scan skipped")

        # 3. AGGREGATE
        if sentiments:
            avg_sentiment = sum(sentiments) / len(sentiments)
            bullish_count = sum(1 for s in sentiments if s > 0.1)
            bearish_count = sum(1 for s in sentiments if s < -0.1)
        else:
            avg_sentiment = 0.0
            bullish_count = bearish_count = 0

        # Social signal
        if avg_sentiment > 0.3 and len(sentiments) >= 5:
            signal = "BULLISH_SOCIAL"
        elif avg_sentiment < -0.3 and len(sentiments) >= 5:
            signal = "BEARISH_SOCIAL"
        else:
            signal = "NEUTRAL_SOCIAL"

        context.result = {
            "ticker": ticker,
            "total_mentions": len(posts_data),
            "avg_sentiment": round(avg_sentiment, 4),
            "bullish_mentions": bullish_count,
            "bearish_mentions": bearish_count,
            "signal": signal,
            "top_posts": posts_data[:10],
        }
        context.actions_taken.append({"action": "social_scan", "mentions_found": len(posts_data)})
        return context

    # ── REFLECT ──────────────────────────────────────────────
    async def reflect(self, context: AgentContext) -> AgentContext:
        result = context.result or {}
        mentions = result.get("total_mentions", 0)
        signal = result.get("signal", "NEUTRAL_SOCIAL")

        if mentions >= 10:
            context.reflection = f"Strong social data: {mentions} mentions. Signal: {signal}"
            context.confidence = 0.75
        elif mentions >= 3:
            context.reflection = f"Moderate social data: {mentions} mentions. Signal: {signal}"
            context.confidence = 0.5
        else:
            context.reflection = f"Weak social data: only {mentions} mentions. Low reliability."
            context.confidence = 0.2
        return context

    def _classify_sentiment(self, text: str) -> float:
        """Simple VADER-based sentiment. Upgrade to FinBERT for production."""
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            analyzer = SentimentIntensityAnalyzer()
            scores = analyzer.polarity_scores(text)
            return scores["compound"]
        except ImportError:
            # Ultra-simple keyword fallback
            positive = ["buy", "bull", "moon", "rocket", "gains", "profit", "up", "breakout", "long"]
            negative = ["sell", "bear", "crash", "dump", "loss", "short", "down", "fear", "puts"]
            text_lower = text.lower()
            pos = sum(1 for w in positive if w in text_lower)
            neg = sum(1 for w in negative if w in text_lower)
            total = pos + neg
            if total == 0:
                return 0.0
            return (pos - neg) / total

    def _add_thought(self, context: AgentContext, thought: str):
        context.thoughts.append(f"[{self.name}] {thought}")
