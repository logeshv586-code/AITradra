"""Sentiment Engine — LLM-powered multi-ticker news analysis.

Reads scraped news from stock_news.db and uses the local Nemotron LLM 
to generate comparative sentiment matrices and risk profiles.
"""

import json
import sqlite3
import os
import re
from datetime import datetime
from typing import List, Dict, Any
from core.logger import get_logger
from llm.client import LLMClient

logger = get_logger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "stock_news.db")

class SentimentEngine:
    def __init__(self):
        self.llm = LLMClient()
        
    def _fetch_news_for_tickers(self, tickers: List[str], limit_per_ticker: int = 20) -> Dict[str, List[Dict]]:
        if not os.path.exists(DB_PATH):
            return {}
            
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        
        news_data = {}
        for ticker in tickers:
            rows = conn.execute(
                "SELECT title, summary, source, pub_date FROM articles WHERE ticker LIKE ? ORDER BY scraped_at DESC LIMIT ?",
                (f"%{ticker.upper()}%", limit_per_ticker)
            ).fetchall()
            if rows:
                news_data[ticker.upper()] = [dict(r) for r in rows]
                
        # Also fetch general news if a ticker didn't have specific news, just to have context
        if not news_data and tickers:
            rows = conn.execute("SELECT title, summary, source, pub_date FROM articles ORDER BY scraped_at DESC LIMIT ?", (limit_per_ticker,)).fetchall()
            news_data["MARKET_GENERAL"] = [dict(r) for r in rows]
            
        conn.close()
        return news_data

    async def analyze_sentiment(self, query: str, tickers: List[str]) -> Dict[str, Any]:
        """Runs LLM comparison on scraped news for the given tickers."""
        
        # 1. Fetch News
        news_data = self._fetch_news_for_tickers(tickers)
        if not news_data:
            return {
                "error": True,
                "message": f"No scraped news found in database for {tickers}. Run `> scrape` first."
            }

        # 2. Build Context String
        context_parts = []
        for ticker, articles in news_data.items():
            context_parts.append(f"--- {ticker} NEWS ---")
            for i, a in enumerate(articles[:15], 1): # Limit to top 15 per ticker to fit context
                summary = a.get('summary', '') or ''
                context_parts.append(f"{i}. [{a['source']}] {a['title']}\n   {summary[:200]}")
        
        context_str = "\n".join(context_parts)

        # 3. Construct LLM Prompt
        system_prompt = """You are AXIOM MYTHIC, an elite Wall Street quantitative analyst and news sentiment expert.
Analyze the provided news articles and generate a structured JSON response comparing the sentiment and risks of the requested stocks.
Follow the EXACT JSON schema requested. Do not output markdown code blocks formatting the JSON. ONLY JSON."""

        user_prompt = f"""USER QUERY: {query}
TARGET TICKERS: {", ".join(tickers)}

NEWS CONTEXT:
{context_str}

REQUIRED JSON OUTPUT SCHEMA:
{{
    "comparison_table": [
        {{"ticker": "...", "sentiment": "BULLISH/BEARISH/NEUTRAL", "key_driver": "brief reason"}}
    ],
    "most_positive": {{"ticker": "...", "reason": "..."}},
    "most_risk": {{"ticker": "...", "reason": "..."}},
    "ranking": ["TICKER1 (Best)", "TICKER2", "TICKER3 (Worst)"],
    "differentiators": ["point 1", "point 2"]
}}

OUTPUT ONLY VALID JSON.
"""
        
        # 4. Invoke LLM
        try:
            logger.info(f"Invoking Sentiment Engine LLM for {tickers}...")
            # We use a slightly higher temperature for better reasoning, but strict JSON
            response_text = await self.llm.complete(
                prompt=user_prompt,
                system=system_prompt,
                temperature=0.1,
                max_tokens=2000
            )
            
            # 5. Parse JSON
            # Extract JSON if the model wrapped it in markdown
            json_str = response_text
            match = re.search(r'\{[\s\S]*\}', response_text)
            if match:
                json_str = match.group(0)
                
            result = json.loads(json_str)
            
            # Format as beautifully structured Markdown for the UI
            md = self._format_as_markdown(result, tickers)
            
            return {
                "error": False,
                "markdown": md,
                "raw_data": result,
                "sources_used": [f"{len(news_data.get(t, []))} articles for {t}" for t in tickers]
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON: {e}\nRaw output: {response_text}")
            return {
                "error": True,
                "message": "LLM failed to output valid JSON for the sentiment comparison. Please retry."
            }
        except Exception as e:
            logger.error(f"Sentiment Engine Error: {e}")
            return {
                "error": True,
                "message": f"Sentiment analysis failed: {str(e)}"
            }

    def _format_as_markdown(self, data: Dict, tickers: List[str]) -> str:
        """Converts the JSON result into a styled Markdown response suitable for ChatPanel."""
        
        md = f"### 📊 Multi-Asset Sentiment Matrix: {', '.join(tickers)}\n\n"
        
        # 1. Side-by-side comparison table
        md += "| Asset | Sentiment | Key News Driver |\n"
        md += "|---|---|---|\n"
        for row in data.get("comparison_table", []):
            emoji = "🟢" if "BULL" in row.get("sentiment", "").upper() else "🔴" if "BEAR" in row.get("sentiment", "").upper() else "⚪"
            md += f"| **{row.get('ticker')}** | {emoji} {row.get('sentiment')} | {row.get('key_driver')} |\n"
            
        md += "\n"
        
        # 2. Most Positive & Most Risk
        pos = data.get("most_positive", {})
        md += f"**🏆 Most Positive Flow:** **{pos.get('ticker', 'N/A')}**\n> {pos.get('reason', '')}\n\n"
        
        risk = data.get("most_risk", {})
        md += f"**⚠️ Highest Risk Signal:** **{risk.get('ticker', 'N/A')}**\n> {risk.get('reason', '')}\n\n"
        
        # 3. Ranking
        ranking = data.get("ranking", [])
        if ranking:
            md += "**📈 Relative Ranking (Best to Worst):**\n"
            for i, r in enumerate(ranking, 1):
                md += f"{i}. {r}\n"
            md += "\n"
                
        # 4. Differentiators
        diffs = data.get("differentiators", [])
        if diffs:
            md += "**🔍 Key Differentiators:**\n"
            for d in diffs:
                md += f"- *{d}*\n"
                
        return md

sentiment_engine = SentimentEngine()
