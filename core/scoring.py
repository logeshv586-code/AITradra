"""Shared scoring and prediction logic for AITradra agents."""

from typing import Any, Dict, Optional
import math

def calculate_technical_score(price: float, sma20: float, sma50: float, change_5d: float, change_20d: float) -> float:
    """Computes a technical score between -5.0 and +5.0."""
    score = 0.0
    if price > 0 and sma20 > 0:
        score += 1.25 if price >= sma20 else -1.25
    if sma20 > 0 and sma50 > 0:
        score += 1.0 if sma20 >= sma50 else -1.0
    
    # Momentum components
    score += max(min(change_5d / 2.5, 1.5), -1.5)
    score += max(min(change_20d / 4.0, 1.5), -1.5)
    
    return round(score, 2)

def calculate_consensus_verdict(
    tech_score: float, 
    news_sentiment: float, 
    social_sentiment: float,
    vol_ratio: float = 1.0
) -> Dict[str, Any]:
    """
    Calculates the final consensus verdict using weighted inputs.
    Weights: Technical (40%), News (40%), Social/Social (20%)
    """
    # Normalize scores to -1.0 to +1.0 for weighting
    # tech_score is approx -5 to +5, so / 5
    norm_tech = max(min(tech_score / 5.0, 1.0), -1.0)
    
    # news_sentiment is usually -1.0 to 1.0
    norm_news = max(min(news_sentiment, 1.0), -1.0)
    
    # social_sentiment is usually -1.0 to 1.0
    norm_social = max(min(social_sentiment, 1.0), -1.0)
    
    weighted_score = (norm_tech * 0.4) + (norm_news * 0.4) + (norm_social * 0.2)
    
    # Volume adjustment
    if vol_ratio > 2.0:
        # High volume confirms the direction if it's strong
        weighted_score *= 1.2
    
    weighted_score = max(min(weighted_score, 1.0), -1.0)
    
    if weighted_score >= 0.25:
        direction = "UP"
    elif weighted_score <= -0.25:
        direction = "DOWN"
    else:
        direction = "SIDEWAYS"
        
    return {
        "score": round(weighted_score, 3),
        "direction": direction,
        "is_strong": abs(weighted_score) >= 0.6
    }

def calibrate_confidence(
    base_score: float,
    data_points: int,
    headline_count: int,
    agreement_factor: float = 1.0
) -> float:
    """Calibrates confidence based on data depth and agent agreement."""
    # Base confidence around 40%
    confidence = 38.0 + (abs(base_score) * 25.0)
    
    # Data depth bonus
    data_bonus = min(data_points / 12.0, 20.0)
    
    # Catalyst bonus
    catalyst_bonus = min(headline_count * 2.0, 10.0)
    
    # Agreement bonus (if agents agree, confidence goes up)
    agreement_bonus = 10.0 * agreement_factor
    
    final_conf = min(max(confidence + data_bonus + catalyst_bonus + agreement_bonus, 35.0), 92.0)
    
    # Penalty for low data
    if data_points < 5 or headline_count == 0:
        final_conf = min(final_conf, 45.0)
        
    return round(final_conf, 1)

def get_recommendation(direction: str, confidence: float, risk_level: str) -> str:
    """Determines the final trade recommendation."""
    if direction == "UP" and confidence >= 60 and risk_level != "HIGH" and risk_level != "EXTREME":
        return "BUY"
    elif direction == "DOWN" and confidence >= 55:
        return "AVOID" # Or SELL if shorting is enabled
    else:
        return "HOLD"
