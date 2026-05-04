"""
AXIOM Core Scoring Engine — The Money Formula.

Implements the canonical signal math from signal-architecture.md:
  Weighted Score = Tech×0.40 + News×0.35 + Social×0.15 + Vol×0.10
  Conviction Multiplier = 1.2× when volume > 1.5× average

All trading decisions flow through these functions.
"""

from typing import Any, Dict, List, Optional
import math


# ─── Layer 2: Consensus Verdict ─────────────────────────────────────────────

def calculate_consensus_verdict(
    tech_score: float,
    news_sentiment: float,
    social_sentiment: float,
    vol_ratio: float = 1.0,
) -> Dict[str, Any]:
    """
    Calculates the final consensus verdict using weighted fusion.

    Weights (from signal-architecture.md):
      Technical:      40%
      News Sentiment: 35%
      Social/Retail:  15%
      Volume Delta:   10%

    Args:
        tech_score:       Normalized -1.0 to +1.0
        news_sentiment:   Normalized -1.0 to +1.0
        social_sentiment: Normalized -1.0 to +1.0
        vol_ratio:        Current volume / 20-day average (e.g. 1.5 = 50% above)

    Returns:
        dict with score, direction, is_strong, verdict
    """
    # Clamp inputs to valid range
    tech = max(min(tech_score, 1.0), -1.0)
    news = max(min(news_sentiment, 1.0), -1.0)
    social = max(min(social_sentiment, 1.0), -1.0)

    # Volume contribution: deviation from average
    vol_delta = max(min((vol_ratio - 1.0), 1.0), -1.0)

    # Weighted blend — canonical formula
    base_score = (
        tech * 0.40
        + news * 0.35
        + social * 0.15
        + vol_delta * 0.10
    )

    # Conviction multiplier for high volume confirmation
    if vol_ratio > 1.5:
        base_score *= 1.2

    # Clamp final score
    base_score = max(min(base_score, 1.0), -1.0)

    # Verdict thresholds — stricter than before to prevent over-trading
    if base_score > 0.15:
        direction = "BUY"
    elif base_score < -0.15:
        direction = "SELL"
    else:
        direction = "HOLD"

    is_strong = abs(base_score) > 0.45

    return {
        "score": round(base_score, 4),
        "direction": direction,
        "is_strong": is_strong,
    }


# ─── Layer 3: Confidence Calibration ────────────────────────────────────────

def calibrate_confidence(
    base_score: float,
    data_points: int,
    headline_count: int,
    agreement_factor: float = 1.0,
) -> float:
    """
    Calibrates confidence (0-100 scale) based on data depth and agent agreement.

    Three pillars (from signal-architecture.md):
      1. Score magnitude → base confidence
      2. Data quality    → multiplier
      3. News freshness  → multiplier
      4. Agreement       → bonus

    Args:
        base_score:       Consensus score magnitude (0.0 to 1.0)
        data_points:      Number of OHLCV bars available
        headline_count:   Number of news articles analyzed
        agreement_factor: 1.0 = neutral, >1.0 = agents agree, <1.0 = disagree

    Returns:
        Calibrated confidence value (0.0 to 100.0)
    """
    # Base confidence from score magnitude
    score_conf = min(0.95, abs(base_score) * 1.5 + 0.3)

    # Data quality multiplier (full confidence at 100+ bars)
    data_quality = min(1.0, data_points / 100)

    # News freshness multiplier (full at 10+ articles)
    news_quality = min(1.0, headline_count / 10)

    # Composite: score × data × news + base floor
    conf = score_conf * data_quality * 0.5 + news_quality * 0.3 + 0.2

    # Agreement bonus/penalty
    conf *= agreement_factor

    # Convert to 0-100 scale, clamp
    final = max(10.0, min(95.0, conf * 100))

    # Penalty for insufficient data
    if data_points < 5:
        final = min(final, 40.0)
    if headline_count == 0:
        final = min(final, 45.0)

    return round(final, 1)


# ─── Layer 5: Verdict with Confidence Gating ────────────────────────────────

def get_recommendation(
    direction: str,
    confidence: float,
    risk_level: str = "MEDIUM",
) -> str:
    """
    Determines the final trade recommendation with confidence gating.

    From risk-framework.md:
      score > 0.65 AND confidence >= 65 → BUY
      score < -0.65 AND confidence >= 65 → SELL
      confidence < 50 → HOLD (never trade doubt)

    Args:
        direction:  "BUY" / "SELL" / "HOLD"
        confidence: 0-100 scale
        risk_level: "LOW" / "MEDIUM" / "HIGH" / "EXTREME"
    """
    # EXTREME risk always blocks
    if risk_level == "EXTREME":
        return "HOLD"

    # Confidence gating — never trade doubt
    if confidence < 50:
        return "HOLD"

    # HIGH risk requires higher confidence
    if risk_level == "HIGH" and confidence < 70:
        return "HOLD"

    if direction == "BUY" and confidence >= 65:
        if confidence >= 80:
            return "STRONG BUY"
        return "BUY"
    elif direction == "SELL" and confidence >= 65:
        if confidence >= 80:
            return "STRONG SELL"
        return "SELL"

    return "HOLD"


# ─── Kelly Criterion Position Sizing ────────────────────────────────────────

def calculate_kelly_size(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    max_position_pct: float = 0.10,
    safety_factor: float = 0.5,
) -> float:
    """
    Calculates optimal position size using Kelly Criterion with half-Kelly safety.

    From risk-framework.md:
      K = W - (1-W)/R
      Half-Kelly = K × 0.5 (safety factor)
      Final = min(half_kelly, risk_parity, hard_cap)

    Args:
        win_rate:         Historical win rate (0.0 to 1.0)
        avg_win:          Average winning trade return (as decimal, e.g. 0.05 = 5%)
        avg_loss:         Average losing trade return (as positive decimal, e.g. 0.03 = 3%)
        max_position_pct: Hard cap on position size (default 10%)
        safety_factor:    Fraction of Kelly to use (default 0.5 = half-Kelly)

    Returns:
        Optimal position size as fraction of portfolio (0.0 to max_position_pct)
    """
    if avg_loss <= 0 or win_rate <= 0 or win_rate >= 1.0:
        return max_position_pct * 0.3  # Minimum default when insufficient data

    win_loss_ratio = avg_win / avg_loss
    kelly_raw = win_rate - (1.0 - win_rate) / win_loss_ratio

    # Apply safety factor (half-Kelly)
    kelly_safe = max(0.0, kelly_raw * safety_factor)

    # Never exceed hard cap
    return min(kelly_safe, max_position_pct)


# ─── Conviction-Based Sizing Multiplier ─────────────────────────────────────

def get_sizing_multiplier(confidence: float) -> float:
    """
    Returns position sizing multiplier based on conviction level.

    From risk-framework.md:
      confidence >= 80: 1.0  (full position)
      confidence >= 65: 0.6  (60% position)
      confidence >= 50: 0.3  (30% position)
      confidence <  50: 0.0  (BLOCK — do not trade)
    """
    if confidence >= 80:
        return 1.0
    elif confidence >= 65:
        return 0.6
    elif confidence >= 50:
        return 0.3
    return 0.0


# ─── Volatility Regime Classification ───────────────────────────────────────

def classify_volatility_regime(annualized_vol: float) -> Dict[str, Any]:
    """
    Classifies the current volatility regime and returns risk multiplier.

    From risk-framework.md:
      ann_vol > 0.40:  CRISIS   → risk_multiplier = 0.25
      ann_vol > 0.25:  HIGH     → risk_multiplier = 0.50
      ann_vol > 0.12:  NORMAL   → risk_multiplier = 1.00
      else:            LOW      → risk_multiplier = 1.20
    """
    if annualized_vol > 0.40:
        return {"regime": "CRISIS", "risk_multiplier": 0.25}
    elif annualized_vol > 0.25:
        return {"regime": "HIGH", "risk_multiplier": 0.50}
    elif annualized_vol > 0.12:
        return {"regime": "NORMAL", "risk_multiplier": 1.00}
    else:
        return {"regime": "LOW", "risk_multiplier": 1.20}


# ─── ATR-Based Stop-Loss and Take-Profit ────────────────────────────────────

def calculate_atr(ohlcv_bars: List[dict], period: int = 14) -> float:
    """
    Calculates the Average True Range from OHLCV bars.

    ATR = Average of True Range over `period` bars.
    True Range = max(High-Low, |High-PrevClose|, |Low-PrevClose|)

    Args:
        ohlcv_bars: List of dicts with high, low, close keys (most recent first)
        period:     ATR lookback period (default 14)

    Returns:
        ATR value (price units), or 0.0 if insufficient data
    """
    if len(ohlcv_bars) < period + 1:
        return 0.0

    true_ranges = []
    for i in range(min(period, len(ohlcv_bars) - 1)):
        bar = ohlcv_bars[i]
        prev_bar = ohlcv_bars[i + 1]

        high = bar.get("high", bar.get("High", 0))
        low = bar.get("low", bar.get("Low", 0))
        prev_close = prev_bar.get("close", prev_bar.get("Close", 0))

        if high == 0 or low == 0 or prev_close == 0:
            continue

        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close),
        )
        true_ranges.append(tr)

    if not true_ranges:
        return 0.0

    return sum(true_ranges) / len(true_ranges)


def calculate_stop_target(
    entry_price: float,
    atr: float,
    direction: str = "BUY",
    stop_multiplier: float = 2.0,
    target_multiplier: float = 3.0,
) -> Dict[str, float]:
    """
    Calculates ATR-based stop-loss and take-profit levels.

    From risk-framework.md:
      Stop  = Entry ± (ATR × stop_multiplier)
      Target = Entry ± (ATR × target_multiplier)
      R:R ratio = target_multiplier / stop_multiplier

    Args:
        entry_price:       Current price / entry price
        atr:               Average True Range value
        direction:         "BUY" (long) or "SELL" (short)
        stop_multiplier:   ATR multiplier for stop (default 2.0)
        target_multiplier: ATR multiplier for target (default 3.0)

    Returns:
        dict with stop_loss, take_profit, risk_reward_ratio
    """
    if atr <= 0 or entry_price <= 0:
        # Fallback to percentage-based
        if direction == "BUY":
            return {
                "stop_loss": round(entry_price * 0.95, 2),
                "take_profit": round(entry_price * 1.10, 2),
                "risk_reward_ratio": 2.0,
            }
        else:
            return {
                "stop_loss": round(entry_price * 1.05, 2),
                "take_profit": round(entry_price * 0.90, 2),
                "risk_reward_ratio": 2.0,
            }

    stop_distance = atr * stop_multiplier
    target_distance = atr * target_multiplier

    if direction == "BUY":
        stop_loss = entry_price - stop_distance
        take_profit = entry_price + target_distance
    else:
        stop_loss = entry_price + stop_distance
        take_profit = entry_price - target_distance

    rr = target_multiplier / stop_multiplier if stop_multiplier > 0 else 0

    return {
        "stop_loss": round(stop_loss, 2),
        "take_profit": round(take_profit, 2),
        "risk_reward_ratio": round(rr, 2),
    }


# ─── Technical Score Computation ────────────────────────────────────────────

def calculate_technical_score(
    price: float,
    sma20: float,
    sma50: float,
    rsi: float = 50.0,
    macd_hist: float = 0.0,
    adx: float = 20.0,
    bb_pct_b: float = 0.5,
    vol_ratio: float = 1.0,
) -> float:
    """
    Computes a composite technical score from multiple indicators.

    Weights:
      Trend (SMA crossover):  25%
      RSI momentum:           20%
      MACD histogram:         20%
      ADX trend strength:     15%
      Bollinger %B:           10%
      Volume:                 10%

    Returns: score between -1.0 and +1.0
    """
    score = 0.0

    # 1. Trend: Price vs SMA20, SMA20 vs SMA50 (25%)
    if price > 0 and sma20 > 0:
        trend_score = 0.0
        if price > sma20:
            trend_score += 0.5
        else:
            trend_score -= 0.5
        if sma20 > 0 and sma50 > 0:
            if sma20 > sma50:
                trend_score += 0.5  # Golden cross zone
            else:
                trend_score -= 0.5  # Death cross zone
        score += trend_score * 0.25

    # 2. RSI (20%) — oversold = bullish, overbought = bearish
    if rsi > 0:
        if rsi < 30:
            rsi_score = 0.8  # Oversold → bullish
        elif rsi < 40:
            rsi_score = 0.4
        elif rsi > 70:
            rsi_score = -0.8  # Overbought → bearish
        elif rsi > 60:
            rsi_score = -0.3
        else:
            rsi_score = 0.0  # Neutral zone
        score += rsi_score * 0.20

    # 3. MACD histogram (20%)
    macd_score = max(min(macd_hist / 2.0, 1.0), -1.0)
    score += macd_score * 0.20

    # 4. ADX trend strength (15%) — amplifies direction
    if adx > 25:
        # Strong trend: amplify the current direction
        direction_sign = 1.0 if score > 0 else (-1.0 if score < 0 else 0)
        adx_boost = min((adx - 25) / 25, 1.0) * direction_sign
        score += adx_boost * 0.15
    else:
        # Weak trend: slight mean-reversion bias
        score += (-0.1 if score > 0 else 0.1) * 0.15

    # 5. Bollinger %B (10%) — position within bands
    # %B < 0 = below lower band (oversold), %B > 1 = above upper band (overbought)
    if bb_pct_b < 0.2:
        bb_score = 0.6  # Near lower band → bullish
    elif bb_pct_b > 0.8:
        bb_score = -0.6  # Near upper band → bearish
    else:
        bb_score = (0.5 - bb_pct_b) * 0.5  # Slight pull to center
    score += bb_score * 0.10

    # 6. Volume confirmation (10%)
    if vol_ratio > 1.5:
        vol_score = 0.5 if score > 0 else -0.5  # Confirms current direction
    elif vol_ratio < 0.5:
        vol_score = -0.2  # Low volume = uncertainty
    else:
        vol_score = 0.0
    score += vol_score * 0.10

    return round(max(min(score, 1.0), -1.0), 4)


# ─── Risk Score Computation ─────────────────────────────────────────────────

def calculate_risk_score(confidence: float, has_errors: bool = False) -> float:
    """
    Calculates risk score (0.0 to 1.0, higher = more risky).

    From risk-framework.md:
      Approved trades: 0.2 + (1.0 - confidence/100) × 0.5
      Blocked trades:  0.8 to 1.0
    """
    if has_errors:
        return 0.9

    base = 0.2 + (1.0 - confidence / 100) * 0.5
    return round(max(0.0, min(1.0, base)), 2)
