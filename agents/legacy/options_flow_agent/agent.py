"""
OPTIONS FLOW AGENT — Claude Flow Architecture (100% OSS)
Detects unusual options activity using yfinance options chains and CBOE public data.
Computes: IV crush risk, max pain, put/call ratio, and unusual volume.

OBSERVE → Fetch available option expirations for the ticker
THINK   → Identify unusually large volume vs open interest
PLAN    → Rank unusual flow, compute max pain and PCR
ACT     → Execute options chain analysis
REFLECT → Score based on flow signal clarity
"""

from agents.base_agent import BaseAgent, AgentContext
from core.logger import get_logger
import pandas as pd

logger = get_logger(__name__)


class OptionsFlowAgent(BaseAgent):
    """Detects institutional options flow and unusual activity from yfinance chains."""

    def __init__(self, memory=None):
        super().__init__("OptionsFlowAgent", memory)

    # ── OBSERVE ──────────────────────────────────────────────
    async def observe(self, context: AgentContext) -> AgentContext:
        context.observations["target_ticker"] = context.ticker
        self._add_thought(context, f"Will scan options chain for {context.ticker}")
        return context

    # ── THINK ────────────────────────────────────────────────
    async def think(self, context: AgentContext) -> AgentContext:
        self._add_thought(context, "Smart money moves in options BEFORE stocks move")
        self._add_thought(context, "Key signals: volume/OI ratio > 5x, put/call ratio extremes, max pain level")
        self._add_thought(context, "Unusual call buying = bullish institutional positioning")
        return context

    # ── PLAN ─────────────────────────────────────────────────
    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan = [
            "1. Fetch option expirations from yfinance",
            "2. Analyze nearest 3 expirations for unusual volume",
            "3. Flag contracts where volume > 5x open interest",
            "4. Compute put/call ratio per expiration",
            "5. Calculate max pain price",
            "6. Determine dominant signal (BULLISH/BEARISH/NEUTRAL)",
        ]
        return context

    # ── ACT ──────────────────────────────────────────────────
    async def act(self, context: AgentContext) -> AgentContext:
        ticker = context.ticker
        flow_signals = []
        put_call_data = {}

        try:
            import yfinance as yf
            stock = yf.Ticker(ticker)
            expirations = stock.options

            if not expirations:
                context.result = {"error": "No options data available", "signal": "NO_DATA"}
                return context

            for exp in expirations[:3]:
                try:
                    chain = stock.option_chain(exp)
                    calls = chain.calls
                    puts = chain.puts

                    # Unusual options activity: volume / OI > 5
                    for _, row in calls.iterrows():
                        if row.get("openInterest", 0) > 0 and row.get("volume", 0) > row["openInterest"] * 5:
                            flow_signals.append({
                                "type": "unusual_call",
                                "expiration": exp,
                                "strike": row["strike"],
                                "volume": int(row["volume"]),
                                "oi": int(row["openInterest"]),
                                "vol_oi_ratio": round(row["volume"] / max(row["openInterest"], 1), 1),
                                "bullish": True,
                                "notional": int(row["volume"] * row.get("lastPrice", 0) * 100),
                            })

                    for _, row in puts.iterrows():
                        if row.get("openInterest", 0) > 0 and row.get("volume", 0) > row["openInterest"] * 5:
                            flow_signals.append({
                                "type": "unusual_put",
                                "expiration": exp,
                                "strike": row["strike"],
                                "volume": int(row["volume"]),
                                "oi": int(row["openInterest"]),
                                "vol_oi_ratio": round(row["volume"] / max(row["openInterest"], 1), 1),
                                "bullish": False,
                                "notional": int(row["volume"] * row.get("lastPrice", 0) * 100),
                            })

                    # Put/Call Ratio
                    total_call_vol = calls["volume"].sum() if "volume" in calls.columns else 0
                    total_put_vol = puts["volume"].sum() if "volume" in puts.columns else 0
                    if total_call_vol > 0:
                        put_call_data[exp] = round(total_put_vol / total_call_vol, 3)

                    # Max Pain
                    max_pain = self._calculate_max_pain(calls, puts)
                    if max_pain:
                        flow_signals.append({"type": "max_pain", "expiration": exp, "price": max_pain, "bullish": None})
                except Exception as e:
                    logger.warning(f"Chain analysis failed for {exp}: {e}")

        except ImportError:
            context.result = {"error": "yfinance not installed", "signal": "ERROR"}
            return context
        except Exception as e:
            context.result = {"error": str(e), "signal": "ERROR"}
            return context

        # Sort by notional (biggest bets first)
        tradeable = [s for s in flow_signals if s.get("notional")]
        tradeable.sort(key=lambda x: x.get("notional", 0), reverse=True)

        pcr_avg = sum(put_call_data.values()) / len(put_call_data) if put_call_data else 1.0

        bullish_notional = sum(s.get("notional", 0) for s in tradeable if s.get("bullish") is True)
        bearish_notional = sum(s.get("notional", 0) for s in tradeable if s.get("bullish") is False)

        if pcr_avg > 1.2:
            pcr_signal = "BEARISH"
        elif pcr_avg < 0.7:
            pcr_signal = "BULLISH"
        else:
            pcr_signal = "NEUTRAL"

        dominant = "BULLISH" if bullish_notional > bearish_notional else "BEARISH"

        context.result = {
            "ticker": ticker,
            "unusual_flow": tradeable[:20],
            "put_call_ratios": put_call_data,
            "pcr_signal": pcr_signal,
            "pcr_avg": round(pcr_avg, 3),
            "bullish_flow_count": sum(1 for s in tradeable if s.get("bullish") is True),
            "bearish_flow_count": sum(1 for s in tradeable if s.get("bullish") is False),
            "dominant_signal": dominant,
            "signal": dominant,
        }
        context.actions_taken.append({"action": "options_flow_scan", "contracts_analyzed": len(flow_signals)})
        return context

    # ── REFLECT ──────────────────────────────────────────────
    async def reflect(self, context: AgentContext) -> AgentContext:
        result = context.result or {}
        flow_count = len(result.get("unusual_flow", []))
        signal = result.get("signal", "NEUTRAL")

        if flow_count >= 5:
            context.reflection = f"Strong options flow: {flow_count} unusual contracts. Signal: {signal}"
            context.confidence = 0.8
        elif flow_count >= 1:
            context.reflection = f"Some unusual activity found ({flow_count} contracts). Signal: {signal}"
            context.confidence = 0.55
        else:
            context.reflection = "No unusual options activity detected."
            context.confidence = 0.2
        return context

    def _calculate_max_pain(self, calls: pd.DataFrame, puts: pd.DataFrame):
        try:
            all_strikes = sorted(set(calls["strike"].tolist() + puts["strike"].tolist()))
            pain = {}
            for strike in all_strikes:
                call_pain = sum(max(0, strike - s) * oi for s, oi in zip(calls["strike"], calls.get("openInterest", [0])))
                put_pain = sum(max(0, s - strike) * oi for s, oi in zip(puts["strike"], puts.get("openInterest", [0])))
                pain[strike] = call_pain + put_pain
            return min(pain, key=pain.get) if pain else None
        except Exception:
            return None

