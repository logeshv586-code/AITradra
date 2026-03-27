# AXIOM v2 — Full Implementation Prompt

> Paste this entire document into your AI coding assistant (Cursor, Claude Code, etc.)
> to build the upgraded AXIOM trading intelligence platform end-to-end.

---

## MISSION

Upgrade AXIOM from a hardcoded, API-rate-limited system into a self-healing,
multi-source intelligence platform that:
- Never shows "data not found" — always falls back gracefully
- Scrapes news and blogs all day as the primary data source
- Uses LLM to reason over scraped content for every stock/crypto
- Shows every stock as a clickable pin on a 3D globe
- Opens a dedicated stock panel with chart, daily H/L, news links, and AI suggestion
- Has a per-stock chat where users ask anything (past, present, prediction)
- Every AI suggestion cites the news article that caused the reasoning

---

## PART 1 — BACKEND: MULTI-SOURCE DATA ENGINE

### 1.1 Source Priority Chain (NO hardcoding, full fallback)

Create `gateway/data_engine.py` implementing this class:

```python
class DataEngine:
    """
    Tries sources in order. Never raises. Always returns something.
    Each method logs which source was actually used.
    """

    SOURCE_CHAIN = [
        "yfinance",         # Primary - fast OHLCV
        "alpha_vantage",    # Free API, 25 calls/day
        "rss_scraper",      # Parse RSS from Reuters, CNBC, MarketWatch
        "web_scraper",      # BeautifulSoup on finance sites
        "reddit_scraper",   # r/stocks, r/wallstreetbets, r/investing sentiment
        "cached_stale",     # Return last known good data with staleness flag
        "llm_estimate",     # LLM reasons over everything it knows about ticker
    ]

    def get_price_data(self, ticker: str) -> dict:
        """
        Returns: {
            px, chg, pct_chg, open, high, low, close, volume,
            source_used, freshness_minutes, is_estimated
        }
        """

    def get_news(self, ticker: str, max_items: int = 10) -> list[dict]:
        """
        Returns list of: {
            headline, summary, url, source, published_at,
            sentiment_score,  # -1.0 to 1.0
            relevance_score,  # 0.0 to 1.0 how relevant to price move
        }
        """

    def get_price_move_reason(self, ticker: str) -> dict:
        """
        Returns: {
            reason_text,      # LLM-written explanation
            source_article,   # The news item that best explains today's move
            confidence        # 0-100
        }
        """
```

### 1.2 RSS Scraper (PRIMARY news source — runs all day)

Create `gateway/scrapers/rss_scraper.py`:

```python
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
        """Run every 5 minutes in background thread."""

    def get_for_ticker(self, ticker: str) -> list[dict]:
        """Filter cached articles by ticker mention."""

    def _parse_feed(self, url: str) -> list[dict]:
        """Use feedparser. Return list of {headline, url, body, published_at, source}."""

    def _dedupe(self, articles: list) -> list:
        """Hash headline to remove duplicates across sources."""
```

### 1.3 Web Scraper (for blog posts and site articles)

Create `gateway/scrapers/web_scraper.py`:

```python
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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def scrape_ticker_news(self, ticker: str) -> list[dict]:
        """Try each target, return combined deduplicated articles."""

    def _scrape_with_retry(self, url: str, retries=3) -> str | None:
        """Exponential backoff. Never raise."""
```

### 1.4 Reddit + Social Sentiment Scraper

Create `gateway/scrapers/social_scraper.py`:

```python
REDDIT_SUBREDDITS = [
    "stocks", "investing", "wallstreetbets", "SecurityAnalysis",
    "StockMarket", "options", "Daytrading", "IndiaInvestments"
]

class SocialScraper:
    def get_sentiment(self, ticker: str) -> dict:
        """
        Returns: {
            reddit_mentions_24h,
            reddit_sentiment,    # positive/negative/neutral
            top_post_title,
            top_post_url,
            bull_bear_ratio,     # e.g. "65% bull"
        }
        Scrapes pushshift.io or old.reddit.com search. No auth needed.
        """

    def _search_reddit(self, ticker: str) -> list[dict]:
        """GET https://old.reddit.com/search.json?q={ticker}&sort=new&limit=25"""
```

### 1.5 Smart Cache with Staleness Tracking

Create `gateway/cache.py`:

```python
import sqlite3, json, hashlib
from datetime import datetime, timedelta

class SmartCache:
    """
    SQLite-backed cache with TTL and source tracking.
    Never deletes old data — marks it stale instead.
    """

    TTL = {
        "price":     timedelta(minutes=5),
        "news":      timedelta(minutes=15),
        "sentiment": timedelta(hours=1),
        "fundamentals": timedelta(hours=24),
        "analysis":  timedelta(hours=6),
    }

    def get(self, key: str, data_type: str) -> tuple[dict | None, bool]:
        """Returns (data, is_fresh). data is None only if never cached."""

    def set(self, key: str, data_type: str, value: dict, source: str):
        """Store with timestamp and source name."""

    def get_freshness_label(self, key: str, data_type: str) -> str:
        """Returns 'Live', 'Cached 4h ago', 'Estimated', or 'Stale'."""
```

---

## PART 2 — LLM INTELLIGENCE ENGINE

### 2.1 Structured Prompt Templates (NEVER hardcode outputs)

Create `gateway/llm_prompts.py` with these prompt builders. Every prompt
instructs the LLM to reason over REAL scraped data passed in, not from memory.

```python
def build_price_analysis_prompt(ticker: str, data: dict) -> str:
    return f"""
You are OMNI-DATA, a market intelligence AI. Analyze {ticker} using only the
data provided below. Do NOT use training memory for current prices.

CURRENT DATA:
Price: {data['px']} | Change: {data['chg']} ({data['pct_chg']}%)
Open: {data['open']} | High: {data['high']} | Low: {data['low']}
Volume: {data['volume']} | Avg Volume: {data['avg_volume']}
52W High: {data['week52_high']} | 52W Low: {data['week52_low']}
P/E: {data.get('pe', 'N/A')} | Market Cap: {data.get('mktcap', 'N/A')}

TODAY'S NEWS (scraped {data['news_freshness']}):
{format_news_for_prompt(data['news'])}

SOCIAL SENTIMENT:
Reddit mentions: {data['reddit_mentions']} | Sentiment: {data['reddit_sentiment']}
Bull/Bear ratio: {data['bull_bear_ratio']}

TASK: Write a clean analysis with these sections:
🧠 OMNI-DATA — {ticker} INTELLIGENCE
📊 Market Context (2-3 sentences on macro backdrop)
📈 Price Analysis (why it moved today, cite the news article)
⚠️ Risk Factors (3-4 bullet points, be specific)
🎯 Strategy (specific entry/exit suggestion with price levels)
📌 Verdict (one clear sentence)
👉 Confidence: X% (data quality: X, trend: X, sentiment: X)

RULES:
- Always cite which news article caused your reasoning
- Include the article URL after your price-move explanation
- Be specific with price levels, not generic advice
- If data is stale, say so and lower confidence accordingly
- Never say "I don't have data" — synthesize from what you have
"""

def build_investment_criteria_prompt(ticker: str, data: dict) -> str:
    return f"""
You are OMNI-DATA. Evaluate {ticker} against these investment criteria.
Use the data provided. Reason step by step.

DATA: {json.dumps(data, indent=2)}

EVALUATE THESE CRITERIA (score each 1-10, explain why):
1. Fundamental strength (P/E, revenue growth, debt/equity)
2. Technical momentum (above/below 50MA, 200MA, RSI, MACD)
3. News sentiment (positive/negative catalyst today)
4. Social sentiment (retail interest, Reddit buzz)
5. Risk/reward ratio (upside vs downside from current price)
6. Sector tailwinds (is the sector hot or cold right now?)

OUTPUT FORMAT (JSON):
{{
  "overall_score": 0-100,
  "signal": "STRONG_BUY | BUY | HOLD | SELL | STRONG_SELL",
  "criteria": [
    {{"name": "...", "score": 7, "reason": "...", "source_url": "..."}}
  ],
  "entry_price": 123.45,
  "target_price": 145.00,
  "stop_loss": 118.00,
  "time_horizon": "1-3 months",
  "key_risk": "One-sentence risk",
  "key_catalyst": "One-sentence upside catalyst",
  "cited_article": {{"headline": "...", "url": "..."}}
}}
"""

def build_stock_chat_prompt(ticker: str, context: dict, question: str) -> str:
    return f"""
You are OMNI-DATA, the dedicated AI for {ticker} ({context['name']}).
You have full access to this stock's data. Answer ONLY about this stock.

STOCK CONTEXT:
{json.dumps(context, indent=2)}

RECENT NEWS:
{format_news_for_prompt(context['news'])}

USER QUESTION: {question}

RULES:
- Answer specifically about {ticker}
- If question is about historical data, use the OHLCV data provided
- If question asks "why did it go up/down", cite the news article
- Include the article URL when citing a news reason
- If you mention a price prediction, give a reason and confidence
- Keep response under 300 words unless the user asks for detail
- End with 👉 Source: [article headline](url) when relevant
"""

def build_price_move_explainer_prompt(ticker: str, data: dict) -> str:
    return f"""
{ticker} moved {data['pct_chg']}% today.
Today's high: {data['high']} | Low: {data['low']}

NEWS CONTEXT:
{format_news_for_prompt(data['news'])}

In 2-3 sentences, explain the most likely reason for today's price move.
Then cite the single best article explaining it.

OUTPUT (JSON):
{{
  "explanation": "...",
  "confidence": 0-100,
  "primary_cause": "earnings | macro | sector | news | technicals | unknown",
  "cited_article": {{"headline": "...", "url": "...", "source": "..."}}
}}
"""

def format_news_for_prompt(news_items: list) -> str:
    lines = []
    for i, item in enumerate(news_items[:8], 1):
        lines.append(f"{i}. [{item['source']}] {item['headline']}")
        lines.append(f"   URL: {item['url']}")
        if item.get('summary'):
            lines.append(f"   Summary: {item['summary'][:200]}")
    return "\n".join(lines)
```

### 2.2 LLM Client with Retry (no hardcoded fallbacks)

Upgrade `gateway/client.py`:

```python
class LLMClient:
    PROVIDERS = ["mistral_gguf", "nvidia_nim", "ollama", "anthropic_api"]

    async def complete(self, prompt: str, expect_json: bool = False) -> str:
        """Try each provider. Never return hardcoded text."""
        for provider in self.PROVIDERS:
            try:
                result = await self._try_provider(provider, prompt)
                if result:
                    return self._parse(result, expect_json)
            except Exception as e:
                log.warning(f"{provider} failed: {e}, trying next...")
        raise RuntimeError("All LLM providers failed")

    def _parse(self, text: str, expect_json: bool) -> str:
        if expect_json:
            # Strip markdown code fences, parse JSON
            clean = re.sub(r"```json|```", "", text).strip()
            return json.loads(clean)
        return text
```

---

## PART 3 — FASTAPI ENDPOINTS

Add these endpoints to `gateway/server.py`:

```python
@app.get("/api/stock/{ticker}")
async def get_stock_detail(ticker: str):
    """
    Full stock detail for the panel view.
    Returns everything needed to render the stock detail panel.
    """
    engine = DataEngine()
    data = engine.get_price_data(ticker)
    news = engine.get_news(ticker, max_items=10)
    sentiment = engine.get_social_sentiment(ticker)
    ohlcv_history = engine.get_ohlcv_history(ticker, days=365)  # for chart
    fundamentals = engine.get_fundamentals(ticker)
    move_reason = engine.get_price_move_reason(ticker)

    return {
        "ticker": ticker,
        "price_data": data,
        "news": news,
        "sentiment": sentiment,
        "ohlcv_history": ohlcv_history,  # [{date, open, high, low, close, volume}]
        "fundamentals": fundamentals,
        "today_move_reason": move_reason,
        "freshness_label": cache.get_freshness_label(ticker, "price"),
    }

@app.get("/api/stock/{ticker}/analysis")
async def get_stock_analysis(ticker: str):
    """LLM-generated investment analysis with criteria scores."""
    engine = DataEngine()
    data = await engine.get_full_context(ticker)
    prompt = build_investment_criteria_prompt(ticker, data)
    result = await llm_client.complete(prompt, expect_json=True)
    return result  # JSON with signal, criteria scores, cited article

@app.get("/api/stock/{ticker}/explain-move")
async def explain_price_move(ticker: str):
    """Why did this stock move today? Returns reason + source link."""
    engine = DataEngine()
    data = await engine.get_price_data(ticker)
    news = await engine.get_news(ticker, max_items=10)
    prompt = build_price_move_explainer_prompt(ticker, {**data, "news": news})
    result = await llm_client.complete(prompt, expect_json=True)
    return result

@app.post("/api/chat/stock/{ticker}")
async def stock_chat(ticker: str, body: ChatRequest):
    """
    Dedicated per-stock chat.
    Loads full stock context, passes to LLM with user question.
    """
    engine = DataEngine()
    context = await engine.get_full_context(ticker)
    prompt = build_stock_chat_prompt(ticker, context, body.message)
    response = await llm_client.complete(prompt)
    return {"response": response, "ticker": ticker}

@app.get("/api/market/globe-data")
async def get_globe_data():
    """
    Lightweight endpoint just for globe pins.
    Returns minimal data for all 86+ tickers for fast globe load.
    """
    return [
        {
            "ticker": t,
            "name": name,
            "lat": lat,
            "lon": lon,
            "px": price,
            "pct_chg": pct_chg,
            "signal": signal,  # BUY/HOLD/SELL for pin color
            "sector": sector,
        }
        for t, name, lat, lon, price, pct_chg, signal, sector in get_all_tickers()
    ]
```

### 3.1 Background Job Scheduler

Add to server startup:

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def start_scheduler():
    # Scrape RSS feeds every 5 minutes
    scheduler.add_job(rss_scraper.fetch_all, "interval", minutes=5)
    # Refresh price data for all tickers every 2 minutes
    scheduler.add_job(refresh_all_prices, "interval", minutes=2)
    # Rebuild LLM analysis for trending tickers every 30 minutes
    scheduler.add_job(rebuild_hot_analyses, "interval", minutes=30)
    # Full web scrape cycle every 2 hours
    scheduler.add_job(web_scraper.scrape_all, "interval", hours=2)
    scheduler.start()
```

---

## PART 4 — REACT FRONTEND

### 4.1 Globe with Clickable Stock Pins

Upgrade `ui/src/components/Globe3D.jsx`:

```jsx
// Globe pins colored by signal
const PIN_COLORS = {
  STRONG_BUY: "#22c55e",
  BUY:        "#4ade80",
  HOLD:       "#fbbf24",
  SELL:       "#f87171",
  STRONG_SELL:"#ef4444",
};

function Globe3D({ onStockSelect }) {
  // Use Three.js globe (threejs-globe or react-globe.gl)
  // Each pin: size scaled by market cap, color by signal
  // On click: call onStockSelect(ticker)
  // Tooltip on hover: show ticker, price, % change
}
```

### 4.2 Stock Detail Panel (opens on globe click)

Create `ui/src/components/StockDetailPanel.jsx`:

```jsx
function StockDetailPanel({ ticker, onClose }) {
  const [data, setData] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [moveReason, setMoveReason] = useState(null);
  const [chatOpen, setChatOpen] = useState(false);

  useEffect(() => {
    // Load in parallel
    Promise.all([
      fetch(`/api/stock/${ticker}`).then(r => r.json()),
      fetch(`/api/stock/${ticker}/analysis`).then(r => r.json()),
      fetch(`/api/stock/${ticker}/explain-move`).then(r => r.json()),
    ]).then(([stock, analysis, reason]) => {
      setData(stock);
      setAnalysis(analysis);
      setMoveReason(reason);
    });
  }, [ticker]);

  return (
    <div className="stock-panel">
      {/* Header: ticker, name, price, % change, freshness badge */}
      <PanelHeader data={data} />

      {/* OHLCV chart (recharts or lightweight-charts) */}
      <PriceChart history={data?.ohlcv_history} />

      {/* Today's High / Low bar */}
      <HighLowBar high={data?.price_data.high} low={data?.price_data.low}
                  current={data?.price_data.px} />

      {/* Why did it move today */}
      <MoveExplainer reason={moveReason} />
      {/* Shows: "AAPL dropped 1.8% because [article headline](url)" */}

      {/* AI Investment Analysis */}
      <AnalysisCard analysis={analysis} />
      {/* Shows signal, score, criteria list, entry/target/stop, cited article link */}

      {/* News feed with links */}
      <NewsFeed news={data?.news} ticker={ticker} />

      {/* Open per-stock chat button */}
      <button onClick={() => setChatOpen(true)}>
        💬 Ask AI about {ticker}
      </button>

      {chatOpen && <StockChat ticker={ticker} context={data} />}
    </div>
  );
}
```

### 4.3 Move Explainer Component

Create `ui/src/components/MoveExplainer.jsx`:

```jsx
function MoveExplainer({ reason }) {
  if (!reason) return <Skeleton />;

  const { explanation, cited_article, confidence, primary_cause } = reason;

  return (
    <div className="move-explainer">
      <div className="cause-badge">{primary_cause}</div>
      <p>{explanation}</p>
      {cited_article && (
        <a href={cited_article.url} target="_blank" rel="noopener"
           className="source-link">
          📰 {cited_article.headline}
          <span className="source-name">{cited_article.source}</span>
        </a>
      )}
      <div className="confidence">AI confidence: {confidence}%</div>
    </div>
  );
}
```

### 4.4 AI Analysis Card with Criteria + Cited Links

Create `ui/src/components/AnalysisCard.jsx`:

```jsx
function AnalysisCard({ analysis }) {
  if (!analysis) return <Skeleton />;

  const signalColor = {
    STRONG_BUY: "text-green-400", BUY: "text-green-300",
    HOLD: "text-yellow-400",
    SELL: "text-red-300", STRONG_SELL: "text-red-500"
  }[analysis.signal];

  return (
    <div className="analysis-card">
      {/* Signal badge + overall score */}
      <div className="signal-header">
        <span className={`signal-badge ${signalColor}`}>{analysis.signal}</span>
        <div className="score-ring">{analysis.overall_score}/100</div>
      </div>

      {/* Price levels */}
      <div className="price-levels">
        <PriceLevel label="Entry"  value={analysis.entry_price} color="blue" />
        <PriceLevel label="Target" value={analysis.target_price} color="green" />
        <PriceLevel label="Stop"   value={analysis.stop_loss} color="red" />
        <PriceLevel label="Horizon" value={analysis.time_horizon} color="gray" />
      </div>

      {/* Criteria breakdown */}
      <div className="criteria-list">
        {analysis.criteria.map(c => (
          <div key={c.name} className="criterion">
            <div className="crit-header">
              <span>{c.name}</span>
              <ScoreBar score={c.score} />
            </div>
            <p className="crit-reason">{c.reason}</p>
            {c.source_url && (
              <a href={c.source_url} target="_blank" className="crit-link">
                🔗 source
              </a>
            )}
          </div>
        ))}
      </div>

      {/* Why the suggestion is good — cited article */}
      <div className="cited-article">
        <span className="label">Why this suggestion:</span>
        <a href={analysis.cited_article.url} target="_blank">
          {analysis.cited_article.headline}
        </a>
      </div>

      {/* Key risk + catalyst */}
      <div className="key-points">
        <div className="risk">⚠️ {analysis.key_risk}</div>
        <div className="catalyst">🚀 {analysis.key_catalyst}</div>
      </div>
    </div>
  );
}
```

### 4.5 Per-Stock Chat Component

Create `ui/src/components/StockChat.jsx`:

```jsx
function StockChat({ ticker, context }) {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: `Hi! I'm your dedicated analyst for ${ticker}. Ask me anything — 
past performance, today's move, price prediction, fundamentals, or comparison with peers.`
    }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const send = async () => {
    if (!input.trim()) return;
    const userMsg = { role: "user", content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    const res = await fetch(`/api/chat/stock/${ticker}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: input })
    });
    const data = await res.json();

    setMessages(prev => [...prev, {
      role: "assistant",
      content: data.response
    }]);
    setLoading(false);
  };

  // Render messages with link detection
  // Parse "👉 Source: [headline](url)" into clickable links
  return (
    <div className="stock-chat">
      <div className="chat-header">
        <span>🧠 {ticker} AI Analyst</span>
        <div className="suggested-questions">
          {SUGGESTED_QUESTIONS[ticker.type || "stock"].map(q => (
            <button key={q} onClick={() => setInput(q)}>{q}</button>
          ))}
        </div>
      </div>
      <MessageList messages={messages} />
      {loading && <ThinkingIndicator />}
      <ChatInput value={input} onChange={setInput} onSend={send} />
    </div>
  );
}

// Pre-built suggested questions per asset type
const SUGGESTED_QUESTIONS = {
  stock: [
    "Why did it move today?",
    "What's the 52-week high and low?",
    "Is now a good time to buy?",
    "What do analysts say about it?",
    "What's the biggest risk right now?",
  ],
  crypto: [
    "What's driving the price today?",
    "What's the market sentiment?",
    "Is this a good entry point?",
    "What are the on-chain signals?",
  ]
};
```

### 4.6 Freshness Badge Component

Show users where data came from:

```jsx
function FreshnessBadge({ label }) {
  // label = "Live" | "Cached 4h ago" | "Estimated" | "Stale"
  const colors = {
    "Live":      "bg-green-900 text-green-300",
    "Estimated": "bg-purple-900 text-purple-300",
    "Stale":     "bg-red-900 text-red-300",
  };
  const color = colors[label] || "bg-gray-800 text-gray-400";

  return (
    <span className={`freshness-badge ${color}`}>
      {label === "Live" ? "🟢" : label === "Stale" ? "🔴" : "🟡"} {label}
    </span>
  );
}
```

---

## PART 5 — DEPENDENCIES TO INSTALL

```bash
# Backend
pip install feedparser beautifulsoup4 requests apscheduler redis \
            aiohttp httpx playwright lxml python-dateutil \
            yfinance alpha-vantage pandas numpy

# Install Playwright browsers for JS-rendered pages
playwright install chromium

# Frontend
cd ui && npm install react-globe.gl three lightweight-charts \
                    recharts date-fns
```

---

## PART 6 — ENVIRONMENT CONFIG (no hardcoding)

Create `.env` (never commit):
```
ALPHA_VANTAGE_KEY=your_free_key_here
REDDIT_CLIENT_ID=optional
REDDIT_CLIENT_SECRET=optional
NVIDIA_NIM_KEY=your_key
LLM_PROVIDER_ORDER=mistral_gguf,nvidia_nim,ollama
CACHE_TTL_PRICE_MINUTES=5
CACHE_TTL_NEWS_MINUTES=15
SCRAPE_INTERVAL_MINUTES=5
MAX_SCRAPE_WORKERS=4
```

Create `gateway/config.py`:
```python
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY", "")
    LLM_PROVIDERS = os.getenv("LLM_PROVIDER_ORDER", "ollama").split(",")
    CACHE_TTL = {
        "price":     int(os.getenv("CACHE_TTL_PRICE_MINUTES", 5)),
        "news":      int(os.getenv("CACHE_TTL_NEWS_MINUTES", 15)),
    }
    SCRAPE_INTERVAL = int(os.getenv("SCRAPE_INTERVAL_MINUTES", 5))
```

---

## PART 7 — UX DETAILS

### Globe Pin Design
- Green pin = BUY signal
- Yellow pin = HOLD
- Red pin = SELL
- Pin size = proportional to market cap
- Hover tooltip: `AAPL $175 ▲1.2% | BUY`
- Click → slides open StockDetailPanel from the right

### Stock Detail Panel Layout (top to bottom)
1. Header: ticker, company name, price, % change, freshness badge
2. Price chart (1D / 1W / 1M / 1Y tabs)
3. Today's range bar (high — current — low)
4. "Why it moved today" — 2 sentences + cited news link
5. AI Analysis card (signal, score, entry/target/stop, 6 criteria with scores)
6. "Why this suggestion is good" → news article link with headline
7. News feed (10 items, each with headline + source + link)
8. "Ask AI about AAPL" button → expands StockChat

### Chat UX
- Opens as a drawer at the bottom of the panel
- Header shows `🧠 AAPL AI Analyst`
- 5 suggested question pills to click
- Responses render markdown with clickable `[headline](url)` links
- Loading state shows "Thinking..." with pulsing dots

---

## PART 8 — FALLBACK CHAIN RULE (implement in every single data method)

```python
async def get_any_data(self, ticker: str, data_type: str):
    """Universal pattern — use this for EVERY data method."""
    
    # 1. Check cache first
    cached, is_fresh = self.cache.get(ticker, data_type)
    if cached and is_fresh:
        return {**cached, "source": "cache_live"}
    
    # 2. Try live sources in order
    for source_fn in self.SOURCE_CHAIN:
        try:
            result = await source_fn(ticker)
            if result:
                self.cache.set(ticker, data_type, result, source=source_fn.__name__)
                return {**result, "source": source_fn.__name__}
        except Exception as e:
            log.warning(f"[{source_fn.__name__}] {ticker} failed: {e}")
            continue
    
    # 3. Return stale cache if we have it (never return nothing)
    if cached:
        log.info(f"Returning stale cache for {ticker}:{data_type}")
        return {**cached, "source": "cache_stale", "is_stale": True}
    
    # 4. LLM estimate as absolute last resort
    log.warning(f"No data at all for {ticker}:{data_type} — using LLM estimate")
    return await self.llm_estimate(ticker, data_type)
```

---

## IMPLEMENTATION ORDER

1. `gateway/config.py` — env-driven config
2. `gateway/cache.py` — SQLite smart cache
3. `gateway/scrapers/rss_scraper.py` — RSS feeds
4. `gateway/scrapers/web_scraper.py` — BeautifulSoup scraper
5. `gateway/scrapers/social_scraper.py` — Reddit scraper
6. `gateway/data_engine.py` — combine all sources with fallback chain
7. `gateway/llm_prompts.py` — all prompt builders
8. Update `gateway/client.py` — multi-provider LLM with JSON mode
9. Update `gateway/server.py` — new endpoints + scheduler
10. `ui/src/components/Globe3D.jsx` — clickable globe pins
11. `ui/src/components/StockDetailPanel.jsx` — full panel
12. `ui/src/components/MoveExplainer.jsx` — why it moved + link
13. `ui/src/components/AnalysisCard.jsx` — criteria + cited link
14. `ui/src/components/StockChat.jsx` — per-stock chat
15. `ui/src/components/FreshnessBadge.jsx` — data source label
16. Wire it all together in `ui/src/App.jsx`

---

*AXIOM v2 — Every answer is sourced. Every suggestion is cited. No hardcoding. No "data not found".*
