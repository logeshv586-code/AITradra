import json

def format_news_for_prompt(news_items: list) -> str:
    lines = []
    for i, item in enumerate(news_items[:8], 1):
        lines.append(f"{i}. [{item.get('source', 'News')}] {item['headline']}")
        lines.append(f"   URL: {item['url']}")
        if item.get('summary'):
            lines.append(f"   Summary: {item['summary'][:200]}")
    return "\n".join(lines)

def build_price_analysis_prompt(ticker: str, data: dict) -> str:
    return f"""
You are OMNI-DATA, a market intelligence AI. Analyze {ticker} using only the
data provided below. Do NOT use training memory for current prices.

CURRENT DATA:
Price: {data.get('px', 'N/A')} | Change: {data.get('chg', 'N/A')} ({data.get('pct_chg', 'N/A')}%)
Open: {data.get('open', 'N/A')} | High: {data.get('high', 'N/A')} | Low: {data.get('low', 'N/A')}
Volume: {data.get('volume', 'N/A')} | Avg Volume: {data.get('avg_volume', 'N/A')}
52W High: {data.get('week52_high', 'N/A')} | 52W Low: {data.get('week52_low', 'N/A')}
P/E: {data.get('pe', 'N/A')} | Market Cap: {data.get('mktcap', 'N/A')}

TODAY'S NEWS (scraped {data.get('news_freshness', 'N/A')}):
{format_news_for_prompt(data.get('news', []))}

SOCIAL SENTIMENT:
Reddit mentions: {data.get('reddit_mentions_24h', 0)} | Sentiment: {data.get('reddit_sentiment', 'neutral')}
Bull/Bear ratio: {data.get('bull_bear_ratio', '50% bull')}

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
    {{"name": "Fundamental strength", "score": 7, "reason": "...", "source_url": "..."}},
    {{"name": "Technical momentum", "score": 7, "reason": "...", "source_url": "..."}},
    {{"name": "News sentiment", "score": 7, "reason": "...", "source_url": "..."}},
    {{"name": "Social sentiment", "score": 7, "reason": "...", "source_url": "..."}},
    {{"name": "Risk/reward ratio", "score": 7, "reason": "...", "source_url": "..."}},
    {{"name": "Sector tailwinds", "score": 7, "reason": "...", "source_url": "..."}}
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
You are OMNI-DATA, the dedicated AI for {ticker}.
You have full access to this stock's data. Answer ONLY about this stock.

STOCK CONTEXT:
{json.dumps(context, indent=2)}

RECENT NEWS:
{format_news_for_prompt(context.get('news', []))}

USER QUESTION: {question}

RULES:
- Answer specifically about {ticker}
- If question is about historical data, use the data provided
- If question asks "why did it go up/down", cite the news article
- Include the article URL when citing a news reason
- If you mention a price prediction, give a reason and confidence
- Keep response under 300 words unless the user asks for detail
- End with 👉 Source: [article headline](url) when relevant
"""

def build_price_move_explainer_prompt(ticker: str, data: dict) -> str:
    return f"""
{ticker} moved {data.get('pct_chg', 'N/A')}% today.
Today's high: {data.get('high', 'N/A')} | Low: {data.get('low', 'N/A')}

NEWS CONTEXT:
{format_news_for_prompt(data.get('news', []))}

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
