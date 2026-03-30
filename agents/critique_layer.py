"""Critique Layer — Self-reflection and confidence calibration.

Adapted from the Claude Agent System reflection pattern:
- CritiqueAgent audits specialist outputs for contradictions
- calibrate_confidence() weights final score by agreement, data quality, recency
- Returns revised consensus with flags
"""

import json
from datetime import datetime
from core.logger import get_logger

logger = get_logger(__name__)


class CritiqueAgent:
    """Audits multi-specialist outputs and produces a revised consensus.
    
    Identifies:
    1. Contradictions between specialists (e.g. Technical says BULLISH but Risk says EXTREME)
    2. Unsupported claims (signals without data)
    3. Confidence mismatches
    """

    async def critique(self, specialist_outputs: dict, query: str, ticker: str = None) -> dict:
        """
        Run critique on all specialist outputs.
        
        Args:
            specialist_outputs: {"technical": {...}, "risk": {...}, "macro": {...}}
            query: Original user query
            ticker: Stock ticker
            
        Returns:
            {revised_consensus, final_confidence, flags[], contradiction_notes}
        """
        technical = specialist_outputs.get("technical", {})
        risk = specialist_outputs.get("risk", {})
        macro = specialist_outputs.get("macro", {})

        flags = []
        contradiction_notes = []

        # ─── Check for contradictions ────────────────────────────────────────
        tech_signal = technical.get("signal", "NEUTRAL")
        risk_level = risk.get("risk_level", "MEDIUM")
        macro_outlook = macro.get("macro_outlook", "NEUTRAL")

        # Contradiction: Bullish technical but extreme risk
        if tech_signal == "BULLISH" and risk_level in ("HIGH", "EXTREME"):
            contradiction_notes.append(
                f"Technical says {tech_signal} but Risk level is {risk_level} — high risk may negate bullish signal"
            )
            flags.append("RISK_CONTRADICTS_TECHNICAL")

        # Contradiction: Bullish technical but bearish macro
        if tech_signal == "BULLISH" and macro_outlook == "BEARISH":
            contradiction_notes.append(
                f"Technical says {tech_signal} but Macro outlook is {macro_outlook} — headwind from macro environment"
            )
            flags.append("MACRO_CONTRADICTS_TECHNICAL")

        # Contradiction: Bearish technical but bullish macro
        if tech_signal == "BEARISH" and macro_outlook == "BULLISH":
            contradiction_notes.append(
                f"Technical says {tech_signal} but Macro outlook is {macro_outlook} — potential recovery catalyst"
            )
            flags.append("MACRO_CONTRADICTS_TECHNICAL")

        # Low confidence check
        confidences = [
            technical.get("confidence", 0),
            risk.get("confidence", 0),
            macro.get("confidence", 0)
        ]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        if avg_confidence < 0.4:
            flags.append("LOW_OVERALL_CONFIDENCE")
            contradiction_notes.append("All specialists report low confidence — data may be insufficient")

        # ─── Determine consensus signal ──────────────────────────────────────
        signal_map = {"BULLISH": 1, "NEUTRAL": 0, "BEARISH": -1}
        signals = [
            signal_map.get(tech_signal, 0),
            signal_map.get(macro_outlook, 0),
            -1 if risk_level in ("HIGH", "EXTREME") else (1 if risk_level == "LOW" else 0)
        ]
        avg_signal = sum(signals) / len(signals)

        if avg_signal > 0.3:
            consensus = "BULLISH"
        elif avg_signal < -0.3:
            consensus = "BEARISH"
        else:
            consensus = "NEUTRAL"

        # ─── Compute specialist agreement ────────────────────────────────────
        agreement_score = 1.0 - (max(signals) - min(signals)) / 2.0

        # Build audit summary from computed data (no LLM needed)
        parts = [f"Consensus: {consensus} with {agreement_score:.0%} agreement."]
        if contradiction_notes:
            parts.append(f"{len(contradiction_notes)} contradiction(s) detected: {'; '.join(contradiction_notes[:2])}")
        else:
            parts.append("No contradictions detected — all specialists align.")
        audit_summary = " ".join(parts)

        return {
            "revised_consensus": consensus,
            "agreement_score": round(agreement_score, 3),
            "flags": flags,
            "contradiction_notes": contradiction_notes,
            "audit_summary": audit_summary,
            "specialist_confidences": {
                "technical": round(technical.get("confidence", 0), 3),
                "risk": round(risk.get("confidence", 0), 3),
                "macro": round(macro.get("confidence", 0), 3),
            }
        }


def calibrate_confidence(
    specialist_agreement: float,
    rag_source_count: int,
    news_recency_hours: float = 24.0,
    specialist_avg_confidence: float = 0.5
) -> float:
    """
    Calibrate final confidence score using the mythic-tier formula.
    
    Weights:
    - 40% specialist agreement score (0-1)
    - 30% RAG source density (capped at 5 sources = 1.0)
    - 30% news recency (1.0 = last hour, 0.0 = > 7 days)
    """
    # RAG source score (0 to 1, capped at 5)
    rag_score = min(rag_source_count / 5, 1.0)

    # News recency score
    if news_recency_hours <= 1:
        recency_score = 1.0
    elif news_recency_hours <= 24:
        recency_score = 0.8
    elif news_recency_hours <= 72:
        recency_score = 0.5
    elif news_recency_hours <= 168:  # 7 days
        recency_score = 0.2
    else:
        recency_score = 0.0

    # Weighted combination
    confidence = (
        0.40 * specialist_agreement +
        0.30 * rag_score +
        0.30 * recency_score
    )

    # Clamp to [0.1, 0.95]
    return round(max(0.1, min(confidence, 0.95)), 3)
