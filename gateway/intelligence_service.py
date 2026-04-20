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
from agents.collector_agent import get_watchlist
from core.scoring import calculate_technical_score, calculate_consensus_verdict, calibrate_confidence
from llm.client import get_shared_llm

logger = get_logger(__name__)

POSITIVE_HEADLINE_KEYWORDS = {
    "beat", "beats", "bullish", "buyback", "expands", "growth", "gains", "jump", "jumps",
    "launch", "outperform", "partnership", "profit", "profits", "rally", "record", "rebound",
    "strong", "surge", "surges", "upgrade", "upgrades", "wins",
}

NEGATIVE_HEADLINE_KEYWORDS = {
    "antitrust", "bankruptcy", "bearish", "crash", "cuts", "cut", "decline", "delay", "downgrade",
    "downgrades", "drop", "drops", "fall", "falls", "fraud", "investigation", "lawsuit", "miss",
    "misses", "probe", "recall", "risk", "risks", "slump", "tariff", "war", "weak",
}

SECTOR_OVERRIDES = {
    "AAPL": "Technology",
    "GOOGL": "Technology",
    "MSFT": "Technology",
    "AMZN": "Consumer Internet",
    "NVDA": "Semiconductors",
    "TSLA": "EV & Mobility",
    "META": "Internet Platforms",
    "NFLX": "Media Streaming",
    "AMD": "Semiconductors",
    "INTC": "Semiconductors",
    "CRM": "Enterprise Software",
    "ADBE": "Enterprise Software",
    "PYPL": "Fintech",
    "SQ": "Fintech",
    "UBER": "Mobility",
    "ABNB": "Travel Platforms",
    "SPOT": "Media Streaming",
    "PLTR": "AI & Data",
    "SNOW": "Cloud Data",
    "SHOP": "E-Commerce Infrastructure",
    "ORCL": "Enterprise Software",
    "IBM": "Enterprise Software",
    "JPM": "Banks",
    "BAC": "Banks",
    "WFC": "Banks",
    "GS": "Investment Banking",
    "MS": "Investment Banking",
    "V": "Payments",
    "MA": "Payments",
    "JNJ": "Healthcare",
    "PFE": "Healthcare",
    "UNH": "Healthcare",
    "PG": "Consumer Staples",
    "KO": "Consumer Staples",
    "PEP": "Consumer Staples",
    "WMT": "Retail",
    "TGT": "Retail",
    "HD": "Retail",
    "XOM": "Energy",
    "CVX": "Energy",
    "RELIANCE.NS": "India Conglomerates",
    "TCS.NS": "India IT",
    "INFY.NS": "India IT",
    "HDFCBANK.NS": "India Banks",
    "ICICIBANK.NS": "India Banks",
    "SBIN.NS": "India Banks",
    "BHARTIARTL.NS": "India Telecom",
    "ITC.NS": "India Consumer",
    "TATAMOTORS.NS": "India Auto",
    "BABA": "China Internet",
    "TCEHY": "China Internet",
    "TSM": "Semiconductors",
    "SONY": "Consumer Electronics",
    "ASML": "Semiconductor Equipment",
    "NVO": "Healthcare",
    "NVS": "Healthcare",
    "SAP": "Enterprise Software",
    "SIE.DE": "Industrials",
    "LVMUY": "Luxury",
    "NSRGY": "Consumer Staples",
    "RY": "Banks",
    "TD": "Banks",
    "BHP": "Materials",
    "RIO": "Materials",
    "SPY": "US Equity ETF",
    "QQQ": "US Growth ETF",
    "DIA": "US Equity ETF",
    "IWM": "US Small Cap ETF",
    "VTI": "US Equity ETF",
    "VEA": "International ETF",
    "VWO": "Emerging Markets ETF",
    "GLD": "Gold ETF",
    "SLV": "Silver ETF",
    "USO": "Energy ETF",
    "TLT": "Treasury ETF",
}


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
        if upper in SECTOR_OVERRIDES:
            return SECTOR_OVERRIDES[upper]
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
            if abs(score) < 0.01:
                score = self._headline_sentiment_score(
                    item.get("headline", ""),
                    item.get("summary", ""),
                )
            total += score
            count += 1
            headlines.append({
                "headline": item.get("headline", f"{ticker} market update"),
                "source": item.get("source", "market_feed"),
                "published_at": item.get("published_at", ""),
                "sentiment_score": round(score, 2),
            })
        return (round(total / count, 3) if count else 0.0, headlines)

    def _headline_sentiment_score(self, headline: str, summary: str = "") -> float:
        text = f"{headline} {summary}".lower()
        positive_hits = sum(1 for word in POSITIVE_HEADLINE_KEYWORDS if word in text)
        negative_hits = sum(1 for word in NEGATIVE_HEADLINE_KEYWORDS if word in text)
        if "upside" in text:
            positive_hits += 1
        if "outlook" in text and "strong" in text:
            positive_hits += 1
        if "warning" in text or "concern" in text:
            negative_hits += 1
        raw_score = (positive_hits - negative_hits) * 0.18
        return round(max(min(raw_score, 0.9), -0.9), 2)

    def _derive_prediction(self, ticker: str, price_data: dict, stats: dict, news_score: float, sentiment: dict) -> dict:
        # Use shared scoring logic
        day_change = _safe_float(price_data.get("pct_chg"), _safe_float(price_data.get("chg")))
        range_position = self._range_position(price_data)
        tech_score = calculate_technical_score(
            price=_safe_float(price_data.get("px")),
            sma20=_safe_float(stats.get("sma20")),
            sma50=_safe_float(stats.get("sma50")),
            change_5d=_safe_float(stats.get("change_5d")),
            change_20d=_safe_float(stats.get("change_20d"))
        )

        if _safe_float(stats.get("points")) < 5:
            tech_score += max(min(day_change / 1.5, 1.0), -1.0)
            if range_position >= 68:
                tech_score += 0.8
            elif range_position <= 32:
                tech_score -= 0.8
        
        consensus = calculate_consensus_verdict(
            tech_score=tech_score,
            news_sentiment=news_score,
            social_sentiment=_safe_float(sentiment.get("score")),
            vol_ratio=_safe_float(stats.get("volume_ratio"), 1.0)
        )

        if consensus["direction"] == "SIDEWAYS":
            directional_bias = 0
            if tech_score >= 1.75:
                directional_bias += 1
            elif tech_score <= -1.75:
                directional_bias -= 1
            if news_score >= 0.18 or _safe_float(sentiment.get("score")) >= 0.22:
                directional_bias += 1
            elif news_score <= -0.18 or _safe_float(sentiment.get("score")) <= -0.22:
                directional_bias -= 1
            if range_position >= 72:
                directional_bias += 1
            elif range_position <= 28:
                directional_bias -= 1

            if directional_bias >= 2:
                consensus = {**consensus, "direction": "UP", "score": max(consensus["score"], 0.28)}
            elif directional_bias <= -2:
                consensus = {**consensus, "direction": "DOWN", "score": min(consensus["score"], -0.28)}
        
        # Determine primary driver
        if abs(news_score) >= 0.15:
            primary_driver = "news"
        elif abs(_safe_float(stats.get("change_20d"))) >= abs(news_score * 10):
            primary_driver = "technical"
        elif abs(_safe_float(sentiment.get("score"))) > 0.35 or abs(news_score) > 0.2:
            primary_driver = "sentiment"
        else:
            primary_driver = "macro"
            
        confidence = calibrate_confidence(
            base_score=consensus["score"],
            data_points=int(_safe_float(stats.get("points"))),
            headline_count=len(sentiment.get("top_headlines", [])),
            agreement_factor=1.2 if consensus["is_strong"] else 1.0
        )

        if len(sentiment.get("top_headlines", [])) >= 3 and abs(news_score) >= 0.15:
            confidence = max(confidence, 52.0)
        if consensus["direction"] != "SIDEWAYS" and (abs(tech_score) >= 1.75 or abs(day_change) >= 1.2):
            confidence = max(confidence, 58.0)

        volatility = _safe_float(stats.get("annualized_volatility"))
        expected_move = round(min(max(abs(consensus["score"]) * 5.2 + abs(day_change) * 0.8 + volatility / 18.0, 0.75), 12.0), 2)

        return {
            "ticker": ticker,
            "prediction_direction": consensus["direction"],
            "confidence_score": confidence,
            "expected_move_percent": expected_move,
            "primary_driver": primary_driver,
            "composite_score": consensus["score"],
        }

    def _derive_risk(self, ticker: str, stats: dict, price_data: dict) -> dict:
        volatility = _safe_float(stats.get("annualized_volatility"))
        max_drawdown = _safe_float(stats.get("max_drawdown"))
        beta = round(0.7 + min(volatility / 25.0, 1.8), 2)
        var_95 = round(min(max(volatility / 8.0, 0.8), 12.0), 1)

        if ticker.upper().endswith("-USD"):
            risk_level = "HIGH"
            vol_label = "High"
            beta = max(beta, 1.8)
            var_95 = max(var_95, 6.5)
        elif volatility >= 45 or max_drawdown >= 30:
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
        day_change = _safe_float(price_data.get("pct_chg"), _safe_float(price_data.get("chg")))
        range_position = risk["price_range_position"]

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
                f"Price is {day_change:+.2f}% on the session, trading at {range_position:.1f}% of its 52-week range, "
                f"with {headwind} headline flow and {risk['risk_level'].lower()} risk."
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

    def _data_quality_score(
        self,
        price_data: dict,
        stats: dict,
        news: list[dict],
        sentiment: dict,
    ) -> dict:
        price_points = 30 if _safe_float(price_data.get("px")) > 0 else 0
        history_points = min(_safe_float(stats.get("points")) / 60.0, 1.0) * 30
        news_points = min(len(news) / 6.0, 1.0) * 20
        sentiment_points = 10 if _safe_float(sentiment.get("mentions")) > 0 else 0
        source_points = 10 if price_data.get("source_used") not in {"unknown", "N/A", None, ""} else 0
        score = round(price_points + history_points + news_points + sentiment_points + source_points, 1)
        score = max(0.0, min(score, 100.0))
        return {
            "score": score,
            "grade": "HIGH" if score >= 75 else "MEDIUM" if score >= 45 else "LOW",
            "price_available": price_points > 0,
            "history_points": int(_safe_float(stats.get("points"))),
            "news_items": len(news),
            "sentiment_mentions": int(_safe_float(sentiment.get("mentions"))),
            "source": price_data.get("source_used", "unknown"),
        }

    def _adaptive_action_plan(self, prediction: dict, risk: dict, quality: dict) -> dict:
        direction = prediction.get("prediction_direction", "SIDEWAYS")
        confidence = _safe_float(prediction.get("confidence_score"))
        risk_level = risk.get("risk_level", "MEDIUM")
        quality_grade = quality.get("grade", "LOW")

        if quality_grade == "LOW":
            mode = "collect_more_evidence"
            next_actions = [
                "refresh price and OHLCV cache",
                "expand recent news evidence",
                "avoid decisive sizing until data quality improves",
            ]
        elif risk_level == "HIGH" and direction != "UP":
            mode = "capital_preservation"
            next_actions = [
                "tighten risk limits",
                "seek downside confirmation",
                "prefer watch or trim actions over new exposure",
            ]
        elif direction == "UP" and confidence >= 60 and risk_level != "HIGH":
            mode = "opportunity_seeking"
            next_actions = [
                "stage entries near support",
                "monitor headline drift",
                "re-score after the next price update",
            ]
        elif direction == "DOWN":
            mode = "defensive_research"
            next_actions = [
                "prioritize risk and catalyst checks",
                "avoid averaging down without fresh confirmation",
                "scan peers for relative weakness",
            ]
        else:
            mode = "confirmation_wait"
            next_actions = [
                "watch for volume confirmation",
                "compare technical and news agreement",
                "keep position sizing neutral",
            ]

        return {
            "mode": mode,
            "next_actions": next_actions,
            "learning_objective": (
                "increase confidence only when price, news, sentiment, and risk agents agree"
            ),
            "recheck_minutes": 30 if mode in {"opportunity_seeking", "capital_preservation"} else 60,
        }

    def _build_intelligence_profile(
        self,
        ticker: str,
        price_data: dict,
        stats: dict,
        news: list[dict],
        sentiment: dict,
        prediction: dict,
        risk: dict,
    ) -> dict:
        quality = self._data_quality_score(price_data, stats, news, sentiment)
        adaptive_plan = self._adaptive_action_plan(prediction, risk, quality)
        model_profile = get_shared_llm().runtime_profile()
        return {
            "version": "adaptive_intelligence_v1",
            "ticker": ticker,
            "generated_at": datetime.now().isoformat(),
            "model_router": model_profile,
            "data_quality": quality,
            "adaptive_plan": adaptive_plan,
            "agent_mesh": {
                "core_agents": [
                    "technical_agent",
                    "macro_agent",
                    "sentiment_agent",
                    "risk_agent",
                ],
                "advanced_layers": [
                    "query_router",
                    "mythic_orchestrator",
                    "critique_layer",
                    "quantic_layer",
                    "swarm_consensus",
                    "self_improvement_engine",
                ],
            },
            "active_signal": {
                "direction": prediction.get("prediction_direction", "SIDEWAYS"),
                "confidence_score": prediction.get("confidence_score", 0),
                "risk_level": risk.get("risk_level", "MEDIUM"),
                "primary_driver": prediction.get("primary_driver", "technical"),
            },
            "self_improvement": {
                "enabled": True,
                "feedback_loops": [
                    "prediction_logging",
                    "agent_health_telemetry",
                    "confidence_calibration",
                    "paper_trade_accuracy",
                ],
            },
        }

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
            "intelligence_profile": snapshot.get("intelligence_profile", {}),
            "adaptive_plan": snapshot.get("adaptive_plan", {}),
            "as_of": snapshot["as_of"],
        }

    def _ensure_intelligence_profile(self, snapshot: dict) -> dict:
        """Backfill adaptive metadata for cached snapshots created before this layer."""
        if not isinstance(snapshot, dict) or snapshot.get("intelligence_profile"):
            return snapshot

        price_data = snapshot.get("price_data", {})
        stats = snapshot.get("historical_stats", {})
        news = snapshot.get("top_headlines", [])
        sentiment = snapshot.get("sentiment", {})
        prediction = {
            "prediction_direction": snapshot.get("prediction_direction", "SIDEWAYS"),
            "confidence_score": snapshot.get("confidence_score", 0),
            "primary_driver": snapshot.get("primary_driver", "technical"),
        }
        risk = snapshot.get("risk", {"risk_level": snapshot.get("risk_level", "MEDIUM")})

        profile = self._build_intelligence_profile(
            snapshot.get("ticker", ""),
            price_data,
            stats,
            news,
            sentiment,
            prediction,
            risk,
        )
        snapshot["intelligence_profile"] = profile
        snapshot["adaptive_plan"] = profile.get("adaptive_plan", {})
        if "analysis" in snapshot and isinstance(snapshot["analysis"], dict):
            snapshot["analysis"]["intelligence_profile"] = profile
            snapshot["analysis"]["adaptive_plan"] = profile.get("adaptive_plan", {})
        return snapshot

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
        risk = self._derive_risk(ticker, stats, price_data)
        built = self._build_sections(ticker, price_data, stats, news_score, top_headlines, sentiment, prediction, risk)
        intelligence_profile = self._build_intelligence_profile(
            ticker,
            price_data,
            stats,
            news,
            sentiment,
            prediction,
            risk,
        )
        adaptive_plan = intelligence_profile.get("adaptive_plan", {})

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
            "intelligence_profile": intelligence_profile,
            "adaptive_plan": adaptive_plan,
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
                return self._ensure_intelligence_profile(existing)
        
        # In a request-response cycle, we don't allow blocking scrapes
        return await self.refresh_ticker_intelligence(ticker, allow_scrape=False)

    async def get_watchlist_intelligence(
        self,
        tickers: list[str] | None = None,
        force_refresh: bool = False,
        max_age_minutes: int = 180,
    ) -> list[dict]:
        tickers = [ticker.upper() for ticker in (tickers or get_watchlist())]
        stored = {
            item["ticker"]: self._ensure_intelligence_profile(item)
            for item in self.store.get_all_ticker_intelligence(
                tickers=tickers,
                limit=len(tickers) + 10,
            )
        }
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
        tickers = [ticker.upper() for ticker in (tickers or get_watchlist())]
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
        profile = snapshot.get("intelligence_profile", {})
        quality = profile.get("data_quality", {}) if isinstance(profile, dict) else {}
        plan = profile.get("adaptive_plan", {}) if isinstance(profile, dict) else {}
        lat, lon = get_coords_for_ticker(ticker)
        sector = snapshot.get("sector", "Global Equity")
        if sector in {"Global Equity", "India Equity", "Europe Equity"}:
            sector = self._infer_sector(ticker)
        return {
            "id": ticker,
            "name": snapshot.get("name", ticker),
            "ex": price.get("source_used", "intelligence"),
            "px": round(_safe_float(price.get("px")), 2),
            "chg": round(_safe_float(price.get("pct_chg"), _safe_float(price.get("chg"))), 2),
            "mcap": format_market_cap(_safe_float(price.get("mktcap"))),
            "vol": format_volume(_safe_float(price.get("volume"))),
            "pe": str(price.get("pe", 0)),
            "sector": sector,
            "lat": lat,
            "lng": lon,
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
            "intelligence_grade": quality.get("grade", "LOW"),
            "adaptive_mode": plan.get("mode", "confirmation_wait"),
        }

    def to_prediction_record(self, snapshot: dict) -> dict:
        price = snapshot.get("price_data", {})
        px = round(_safe_float(price.get("px")), 2)
        direction = snapshot.get("prediction_direction", "SIDEWAYS")
        expected_move = _safe_float(snapshot.get("expected_move_percent"))
        multiplier = 1 + (expected_move / 100.0) * (1 if direction == "UP" else -1 if direction == "DOWN" else 0)
        sector = snapshot.get("sector", "Global Equity")
        profile = snapshot.get("intelligence_profile", {})
        quality = profile.get("data_quality", {}) if isinstance(profile, dict) else {}
        if sector in {"Global Equity", "India Equity", "Europe Equity"}:
            sector = self._infer_sector(snapshot["ticker"])
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
            "sector": sector,
            "chg": round(_safe_float(price.get("pct_chg"), _safe_float(price.get("chg"))), 2),
            "recommendation": snapshot.get("recommendation", "HOLD"),
            "should_invest": bool(snapshot.get("should_invest")),
            "intelligence_grade": quality.get("grade", "LOW"),
            "as_of": snapshot.get("as_of"),
        }


intelligence_service = IntelligenceService()
