"""Persistent ticker intelligence snapshots for all backend market views."""

from __future__ import annotations

import asyncio
import math
from datetime import datetime, timedelta
from typing import Any

from core.config import settings
from core.logger import get_logger
from gateway.data_engine import data_engine
from gateway.knowledge_store import knowledge_store
from gateway.stock_geo import get_coords_for_ticker, format_market_cap, format_volume

logger = get_logger(__name__)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


class IntelligenceService:
    """Builds, stores, and serves normalized per-ticker intelligence."""

    def __init__(self):
        self.data_engine = data_engine
        self.store = knowledge_store

    def _parse_ts(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    def _is_stale(self, snapshot: dict | None, max_age_minutes: int) -> bool:
        if not snapshot:
            return True
        ts = self._parse_ts(snapshot.get("updated_at") or snapshot.get("as_of"))
        if ts is None:
            return True
        if ts.tzinfo is not None:
            ts = ts.replace(tzinfo=None)
        return datetime.now() - ts > timedelta(minutes=max_age_minutes)

    def _infer_sector(self, ticker: str) -> str:
        upper = ticker.upper()
        if upper.endswith("-USD"):
            return "Cryptocurrency"
        if upper.endswith(".NS") or upper.endswith(".BO"):
            return "India Equity"
        if upper.endswith(".DE") or upper.endswith(".L"):
            return "Europe Equity"
        if upper.startswith("^"):
            return "Index"
        return "Global Equity"

    def _compute_rsi(self, closes: list[float], period: int = 14) -> float | None:
        if len(closes) < period + 1:
            return None
        gains = []
        losses = []
        for idx in range(len(closes) - period, len(closes)):
            change = closes[idx] - closes[idx - 1]
            gains.append(max(change, 0.0))
            losses.append(abs(min(change, 0.0)))
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0:
            return 100.0 if avg_gain > 0 else 50.0
        rs = avg_gain / avg_loss
        return round(100 - (100 / (1 + rs)), 2)

    def _compute_max_drawdown(self, closes: list[float]) -> float:
        if not closes:
            return 0.0
        peak = closes[0]
        max_drawdown = 0.0
        for price in closes:
            peak = max(peak, price)
            if peak <= 0:
                continue
            drawdown = (price - peak) / peak
            max_drawdown = min(max_drawdown, drawdown)
        return round(abs(max_drawdown) * 100, 2)

    def _pct_move(self, closes: list[float], periods_back: int) -> float:
        if len(closes) <= periods_back:
            return 0.0
        current = closes[-1]
        previous = closes[-1 - periods_back]
        if previous == 0:
            return 0.0
        return round(((current - previous) / previous) * 100, 2)

    def _compute_stats(self, history: list[dict], price_data: dict) -> dict:
        ordered = list(reversed(history))
        closes = [_safe_float(row.get("close")) for row in ordered if _safe_float(row.get("close")) > 0]
        volumes = [_safe_float(row.get("volume")) for row in ordered if _safe_float(row.get("volume")) >= 0]

        if not closes and price_data.get("ohlcv"):
            closes = [_safe_float(row.get("c")) for row in price_data["ohlcv"] if _safe_float(row.get("c")) > 0]
            volumes = [_safe_float(row.get("v")) for row in price_data["ohlcv"] if _safe_float(row.get("v")) >= 0]

        if not closes and _safe_float(price_data.get("px")) > 0:
            closes = [_safe_float(price_data.get("px"))]

        sma20 = round(sum(closes[-20:]) / min(len(closes), 20), 2) if closes else 0.0
        sma50 = round(sum(closes[-50:]) / min(len(closes), 50), 2) if closes else 0.0
        returns = []
        for idx in range(1, len(closes)):
            prev_close = closes[idx - 1]
            if prev_close > 0:
                returns.append((closes[idx] - prev_close) / prev_close)

        daily_volatility = 0.0
        if returns:
            avg = sum(returns) / len(returns)
            variance = sum((value - avg) ** 2 for value in returns) / len(returns)
            daily_volatility = math.sqrt(max(variance, 0.0))

        annualized_volatility = round(daily_volatility * math.sqrt(252) * 100, 2)
        avg_volume_20 = round(sum(volumes[-20:]) / min(len(volumes), 20), 2) if volumes else 0.0
        current_volume = _safe_float(price_data.get("volume"), volumes[-1] if volumes else 0.0)
        volume_ratio = round(current_volume / avg_volume_20, 2) if avg_volume_20 > 0 else 1.0

        return {
            "points": len(closes),
            "last_close": round(closes[-1], 2) if closes else _safe_float(price_data.get("px")),
            "change_1d": round(_safe_float(price_data.get("pct_chg"), _safe_float(price_data.get("chg"))), 2),
            "change_5d": self._pct_move(closes, 5),
            "change_20d": self._pct_move(closes, 20),
            "change_60d": self._pct_move(closes, 60),
            "sma20": sma20,
            "sma50": sma50,
            "rsi14": self._compute_rsi(closes),
            "annualized_volatility": annualized_volatility,
            "max_drawdown": self._compute_max_drawdown(closes),
            "avg_volume_20": avg_volume_20,
            "volume_ratio": volume_ratio,
        }

    def _summarize_news(self, ticker: str, news: list[dict]) -> tuple[float, list[dict]]:
        total = 0.0
        count = 0
        headlines = []
        for item in news[:5]:
            score = _safe_float(item.get("sentiment_score"))
            total += score
            count += 1
            headlines.append({
                "headline": item.get("headline", f"{ticker} market update"),
                "source": item.get("source", "market_feed"),
                "published_at": item.get("published_at", ""),
                "sentiment_score": round(score, 2),
            })
        return (round(total / count, 3) if count else 0.0, headlines)

    def _derive_prediction(self, ticker: str, price_data: dict, stats: dict, news_score: float, sentiment: dict) -> dict:
        tech_score = 0.0
        price = _safe_float(price_data.get("px"))
        sma20 = _safe_float(stats.get("sma20"))
        sma50 = _safe_float(stats.get("sma50"))

        if price > 0 and sma20 > 0:
            tech_score += 1.25 if price >= sma20 else -1.25
        if sma20 > 0 and sma50 > 0:
            tech_score += 1.0 if sma20 >= sma50 else -1.0

        tech_score += max(min(_safe_float(stats.get("change_5d")) / 2.5, 1.5), -1.5)
        tech_score += max(min(_safe_float(stats.get("change_20d")) / 4.0, 1.5), -1.5)

        sentiment_score = max(min(news_score * 3.0, 1.5), -1.5)
        social_score = max(min(_safe_float(sentiment.get("score")) * 1.5, 1.0), -1.0)
        total_score = tech_score + sentiment_score + social_score

        if total_score >= 1.25:
            direction = "UP"
        elif total_score <= -1.25:
            direction = "DOWN"
        else:
            direction = "SIDEWAYS"

        volatility = _safe_float(stats.get("annualized_volatility"))
        expected_move = round(min(max(abs(total_score) * 1.8 + volatility / 18.0, 0.6), 12.0), 2)

        data_depth_bonus = min(_safe_float(stats.get("points")) / 12.0, 20.0)
        catalyst_bonus = min(len(sentiment.get("top_headlines", [])) * 2.0, 10.0)
        agreement_bonus = 8.0 if abs(total_score) >= 2.5 else 4.0 if abs(total_score) >= 1.5 else 0.0
        confidence = round(min(max(38.0 + abs(total_score) * 12.0 + data_depth_bonus + catalyst_bonus + agreement_bonus, 35.0), 85.0), 1)

        if _safe_float(stats.get("points")) < 5 or len(sentiment.get("top_headlines", [])) == 0:
            confidence = min(confidence, 45.0)

        if abs(_safe_float(stats.get("change_20d"))) >= abs(news_score * 10):
            primary_driver = "technical"
        elif abs(_safe_float(sentiment.get("score"))) > 0.35 or abs(news_score) > 0.2:
            primary_driver = "sentiment"
        else:
            primary_driver = "macro"

        return {
            "ticker": ticker,
            "prediction_direction": direction,
            "confidence_score": confidence,
            "expected_move_percent": expected_move,
            "primary_driver": primary_driver,
            "composite_score": round(total_score, 2),
        }

    def _derive_risk(self, stats: dict, price_data: dict) -> dict:
        volatility = _safe_float(stats.get("annualized_volatility"))
        max_drawdown = _safe_float(stats.get("max_drawdown"))
        beta = round(0.7 + min(volatility / 25.0, 1.8), 2)
        var_95 = round(min(max(volatility / 8.0, 0.8), 12.0), 1)

        if volatility >= 45 or max_drawdown >= 30:
            risk_level = "HIGH"
            vol_label = "High"
        elif volatility >= 22 or max_drawdown >= 15:
            risk_level = "MEDIUM"
            vol_label = "Medium"
        else:
            risk_level = "LOW"
            vol_label = "Low"

        return {
            "risk_level": risk_level,
            "beta": beta,
            "var_95": var_95,
            "max_drawdown": max_drawdown,
            "annualized_volatility": volatility,
            "volatility_label": vol_label,
            "price_range_position": self._range_position(price_data),
        }

    def _range_position(self, price_data: dict) -> float:
        low = _safe_float(price_data.get("week52_low"))
        high = _safe_float(price_data.get("week52_high"))
        px = _safe_float(price_data.get("px"))
        if high <= low or px <= 0:
            return 0.0
        return round(((px - low) / (high - low)) * 100, 1)

    def _build_sections(
        self,
        ticker: str,
        price_data: dict,
        stats: dict,
        news_summary: float,
        top_headlines: list[dict],
        sentiment: dict,
        prediction: dict,
        risk: dict,
    ) -> dict:
        trend_bias = "bullish" if prediction["prediction_direction"] == "UP" else "bearish" if prediction["prediction_direction"] == "DOWN" else "balanced"
        rsi = stats.get("rsi14")
        rsi_text = f"RSI {rsi}" if rsi is not None else "RSI unavailable"
        headwind = "supportive" if news_summary >= 0.15 else "negative" if news_summary <= -0.15 else "mixed"
        invest = prediction["prediction_direction"] == "UP" and prediction["confidence_score"] >= 60 and risk["risk_level"] != "HIGH"
        recommendation = "BUY" if invest else "HOLD / AVOID" if prediction["prediction_direction"] != "DOWN" else "AVOID"

        sections = {
            "executive_summary": (
                f"{ticker} shows a {trend_bias} setup with {prediction['confidence_score']}% confidence. "
                f"Backend intelligence is using {stats['points']} historical data points and {len(top_headlines)} recent headlines."
            ),
            "technical": (
                f"Price is {price_data.get('pct_chg', price_data.get('chg', 0)):+.2f}% on the day, "
                f"{stats['change_5d']:+.2f}% over 5 sessions, and {stats['change_20d']:+.2f}% over 20 sessions. "
                f"SMA20 {stats['sma20']:.2f} vs SMA50 {stats['sma50']:.2f}; {rsi_text}."
            ),
            "macro_fundamental": (
                f"Market context is {headwind}. The asset is trading at {risk['price_range_position']}% of its 52-week range "
                f"with source {price_data.get('source_used', 'unknown')} and sector tag {self._infer_sector(ticker)}."
            ),
            "sentiment": (
                f"News sentiment averages {news_summary:+.2f} and social sentiment reads "
                f"{_safe_float(sentiment.get('score')):+.2f} across {_safe_float(sentiment.get('mentions')):.0f} mentions."
            ),
            "risk": (
                f"Risk is {risk['risk_level']} with annualized volatility {risk['annualized_volatility']:.2f}%, "
                f"estimated beta {risk['beta']:.2f}, and max drawdown {risk['max_drawdown']:.2f}%."
            ),
            "verdict": (
                f"Recommendation: {recommendation}. "
                f"{'Investable trend with acceptable risk.' if invest else 'Wait for stronger confirmation or lower risk before deploying capital.'}"
            ),
        }

        agents = {
            "technical_agent": {
                "signal": prediction["prediction_direction"],
                "summary": sections["technical"],
                "score": round(max(min(_safe_float(stats.get("change_20d")) / 5.0, 1.0), -1.0), 2),
            },
            "macro_agent": {
                "signal": "POSITIVE" if news_summary > 0.15 else "NEGATIVE" if news_summary < -0.15 else "NEUTRAL",
                "summary": sections["macro_fundamental"],
                "score": round(max(min(news_summary * 2.0, 1.0), -1.0), 2),
            },
            "sentiment_agent": {
                "signal": "POSITIVE" if _safe_float(sentiment.get("score")) > 0.2 else "NEGATIVE" if _safe_float(sentiment.get("score")) < -0.2 else "NEUTRAL",
                "summary": sections["sentiment"],
                "score": round(max(min(_safe_float(sentiment.get("score")), 1.0), -1.0), 2),
            },
            "risk_agent": {
                "signal": risk["risk_level"],
                "summary": sections["risk"],
                "score": round(max(0.0, 1.0 - (_safe_float(risk["annualized_volatility"]) / 60.0)), 2),
            },
        }
        return {"sections": sections, "agents": agents}

    def _analysis_payload(self, snapshot: dict) -> dict:
        return {
            "ticker": snapshot["ticker"],
            "consensus": snapshot["prediction_direction"],
            "confidence": snapshot["confidence_score"],
            "recommendation": snapshot["recommendation"],
            "should_invest": snapshot["should_invest"],
            "prediction_direction": snapshot["prediction_direction"],
            "confidence_score": snapshot["confidence_score"],
            "expected_move_percent": snapshot["expected_move_percent"],
            "risk_level": snapshot["risk_level"],
            "primary_driver": snapshot["primary_driver"],
            "reasoning_summary": snapshot["reasoning_summary"],
            "executive_summary": snapshot["sections"]["executive_summary"],
            "sections": snapshot["sections"],
            "agents": snapshot["agents"],
            "top_headlines": snapshot["top_headlines"],
            "as_of": snapshot["as_of"],
        }

    async def refresh_ticker_intelligence(self, ticker: str, allow_scrape: bool = False) -> dict:
        if not ticker or str(ticker).strip().lower() in ("none", "null", ""):
            raise ValueError(f"Invalid ticker: {ticker}")
            
        ticker = ticker.upper()
        # Non-blocking fetch from data engine
        price_data = await self.data_engine.get_price_data(ticker, allow_scrape=allow_scrape)
        news = await self.data_engine.get_news(ticker, max_items=10, allow_scrape=allow_scrape)
        sentiment_raw = await self.data_engine.get_social_sentiment(ticker, allow_scrape=allow_scrape)

        history = self.store.get_ohlcv_history(ticker, days=365 * 5)
        stats = self._compute_stats(history, price_data)
        news_score, top_headlines = self._summarize_news(ticker, news)
        sentiment = {
            "score": round(_safe_float(sentiment_raw.get("score")), 2),
            "mentions": int(_safe_float(sentiment_raw.get("mentions"))),
            "source": sentiment_raw.get("source", "none"),
            "top_headlines": top_headlines,
        }

        prediction = self._derive_prediction(ticker, price_data, stats, news_score, sentiment)
        risk = self._derive_risk(stats, price_data)
        built = self._build_sections(ticker, price_data, stats, news_score, top_headlines, sentiment, prediction, risk)

        recommendation = (
            "BUY"
            if prediction["prediction_direction"] == "UP" and prediction["confidence_score"] >= 60 and risk["risk_level"] != "HIGH"
            else "AVOID"
            if prediction["prediction_direction"] == "DOWN" and prediction["confidence_score"] >= 55
            else "HOLD"
        )
        should_invest = recommendation == "BUY"

        snapshot = {
            "ticker": ticker,
            "name": ticker,
            "sector": self._infer_sector(ticker),
            "as_of": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "recommendation": recommendation,
            "should_invest": should_invest,
            "prediction_direction": prediction["prediction_direction"],
            "confidence_score": prediction["confidence_score"],
            "expected_move_percent": prediction["expected_move_percent"],
            "risk_level": risk["risk_level"],
            "primary_driver": prediction["primary_driver"],
            "reasoning_summary": built["sections"]["verdict"],
            "price_data": price_data,
            "historical_stats": stats,
            "risk": risk,
            "sentiment": sentiment,
            "top_headlines": top_headlines,
            "news_count": len(news),
            "sections": built["sections"],
            "agents": built["agents"],
            "freshness": {
                "price_source": price_data.get("source_used", "unknown"),
                "stale": bool(price_data.get("is_estimated", False) or price_data.get("syncing", False)),
                "news_items": len(news),
            },
            "analysis": {},
        }
        snapshot["analysis"] = self._analysis_payload(snapshot)

        # Persist to DB for lightning fast future reads
        try:
            self.store.store_ticker_intelligence(ticker, snapshot)
        except Exception as e:
            logger.warning(f"Failed to persist intelligence snapshot for {ticker}: {e}")

        return snapshot

    async def get_ticker_intelligence(
        self,
        ticker: str,
        force_refresh: bool = False,
        max_age_minutes: int = 180,
    ) -> dict:
        ticker = ticker.upper()
        if not force_refresh:
            existing = self.store.get_ticker_intelligence(ticker)
            if existing and not self._is_stale(existing, max_age_minutes):
                return existing
        
        # In a request-response cycle, we don't allow blocking scrapes
        return await self.refresh_ticker_intelligence(ticker, allow_scrape=False)

    async def get_watchlist_intelligence(
        self,
        tickers: list[str] | None = None,
        force_refresh: bool = False,
        max_age_minutes: int = 180,
    ) -> list[dict]:
        tickers = [ticker.upper() for ticker in (tickers or settings.DEFAULT_WATCHLIST)]
        stored = {item["ticker"]: item for item in self.store.get_all_ticker_intelligence(tickers=tickers, limit=len(tickers) + 10)}
        results: list[dict] = []
        missing: list[str] = []

        for ticker in tickers:
            snapshot = stored.get(ticker)
            if force_refresh or self._is_stale(snapshot, max_age_minutes):
                missing.append(ticker)
            else:
                results.append(snapshot)

        if missing:
            # For watchlist requests, we NEVER block on missing scraping.
            # We return what we have (even if stale) and fire background tasks.
            for ticker in missing:
                snapshot = stored.get(ticker)
                if snapshot:
                    results.append(snapshot)
                # Task will warm this ticker for the *next* request
                asyncio.create_task(self.refresh_ticker_intelligence(ticker, allow_scrape=True))

        return sorted(results, key=lambda item: tickers.index(item["ticker"]) if item["ticker"] in tickers else 999)

    async def warm_watchlist_intelligence(self, tickers: list[str] | None = None):
        """Background task to fully update intelligence with staggered processing."""
        tickers = [ticker.upper() for ticker in (tickers or settings.DEFAULT_WATCHLIST)]
        logger.info(f"🦾 Staggered Intelligence Warming for {len(tickers)} tickers...")
        
        # Process in small batches to avoid CPU/RAM spikes
        batch_size = 5
        for i in range(0, len(tickers), batch_size):
            batch = tickers[i:i + batch_size]
            logger.debug(f"Warming batch: {', '.join(batch)}")
            
            # Concurrent within batch, but total batch concurrency is low
            await asyncio.gather(*[
                self.refresh_ticker_intelligence(t, allow_scrape=True) 
                for t in batch
            ], return_exceptions=True)
            
            # Polite delay between batches
            await asyncio.sleep(5)
            
        logger.info("✅ Staggered Intelligence Cache warming complete.")

    async def refresh_watchlist_intelligence(self, tickers: list[str] | None = None) -> list[dict]:
        return await self.get_watchlist_intelligence(tickers=tickers, force_refresh=True)

    def to_watchlist_record(self, snapshot: dict) -> dict:
        ticker = snapshot["ticker"]
        price = snapshot.get("price_data", {})
        risk = snapshot.get("risk", {})
        lat, lon = get_coords_for_ticker(ticker)
        return {
            "id": ticker,
            "name": snapshot.get("name", ticker),
            "ex": price.get("source_used", "intelligence"),
            "px": round(_safe_float(price.get("px")), 2),
            "chg": round(_safe_float(price.get("pct_chg"), _safe_float(price.get("chg"))), 2),
            "mcap": format_market_cap(_safe_float(price.get("mktcap"))),
            "vol": format_volume(_safe_float(price.get("volume"))),
            "pe": str(price.get("pe", 0)),
            "sector": snapshot.get("sector", "Global Equity"),
            "lat": lat,
            "lon": lon,
            "ohlcv": price.get("ohlcv", []),
            "risk": {
                "var": f"{risk.get('var_95', 0)}%",
                "beta": round(_safe_float(risk.get("beta"), 1.0), 2),
                "vol": risk.get("volatility_label", "Medium"),
            },
            "fundamentals": {
                "52w_high": _safe_float(price.get("week52_high")),
                "52w_low": _safe_float(price.get("week52_low")),
            },
            "stale": bool(snapshot.get("freshness", {}).get("stale", False)),
            "pct_chg": round(_safe_float(price.get("pct_chg"), _safe_float(price.get("chg"))), 2),
            "recommendation": snapshot.get("recommendation", "HOLD"),
            "confidence_score": snapshot.get("confidence_score", 0),
        }

    def to_prediction_record(self, snapshot: dict) -> dict:
        price = snapshot.get("price_data", {})
        px = round(_safe_float(price.get("px")), 2)
        direction = snapshot.get("prediction_direction", "SIDEWAYS")
        expected_move = _safe_float(snapshot.get("expected_move_percent"))
        multiplier = 1 + (expected_move / 100.0) * (1 if direction == "UP" else -1 if direction == "DOWN" else 0)
        return {
            "ticker": snapshot["ticker"],
            "name": snapshot.get("name", snapshot["ticker"]),
            "current_price": px,
            "predicted_price": round(px * multiplier, 2),
            "prediction_direction": direction,
            "confidence_score": round(_safe_float(snapshot.get("confidence_score")), 1),
            "expected_move_percent": round(expected_move, 2),
            "risk_level": snapshot.get("risk_level", "MEDIUM"),
            "reasoning_summary": snapshot.get("reasoning_summary", ""),
            "primary_driver": snapshot.get("primary_driver", "technical"),
            "source_link": "",
            "sector": snapshot.get("sector", "Global Equity"),
            "chg": round(_safe_float(price.get("pct_chg"), _safe_float(price.get("chg"))), 2),
            "recommendation": snapshot.get("recommendation", "HOLD"),
            "should_invest": bool(snapshot.get("should_invest")),
            "as_of": snapshot.get("as_of"),
        }


intelligence_service = IntelligenceService()
