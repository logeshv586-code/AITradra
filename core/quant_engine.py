"""
core/quant_engine.py
────────────────────────────────────────────────────────────────────────────────
QuantEngine — the platform's professional technical-analysis brain.

This is what makes the system answer like an EXPERT even with no LLM running:
instead of "SIDEWAYS, target = current price", every view is computed the way
a desk trader computes it:

  • ATR(14)              → realistic expected moves and stop distances
  • RSI(14), MACD        → momentum state and exhaustion
  • SMA20/50 structure   → trend regime classification
  • Swing highs/lows     → actual support/resistance levels
  • Volume ratio         → confirmation or divergence
  • Named setups         → "pullback in uptrend", "breakout watch",
                           "bear rally fade", "range trade" … not generic labels
  • Trade plans          → entry / stop / target1 / target2 with risk:reward,
                           anchored to levels and ATR, never to wishes

All pure-python (math only), works on the OHLCV bars the platform already
stores. Bars are accepted newest-first (knowledge-store order) or oldest-first.
"""

from __future__ import annotations

import math
from typing import Any, Optional

# ─────────────────────────────────────────────────────────────────────────────
# Indicator primitives
# ─────────────────────────────────────────────────────────────────────────────


def _f(value, default=0.0) -> float:
    try:
        out = float(value)
        return out if math.isfinite(out) else default
    except (TypeError, ValueError):
        return default


def normalize_bars(bars: list[dict]) -> list[dict]:
    """Return chronological bars with float o/h/l/c/v, tolerant of key styles."""
    if not bars:
        return []
    out = []
    for b in bars:
        close = _f(b.get("close", b.get("c")))
        if close <= 0:
            continue
        out.append({
            "open": _f(b.get("open", b.get("o")), close),
            "high": _f(b.get("high", b.get("h")), close),
            "low": _f(b.get("low", b.get("l")), close),
            "close": close,
            "volume": _f(b.get("volume", b.get("v"))),
        })
    if len(out) >= 2:
        # Detect newest-first (knowledge store) and flip to chronological
        first_date = str(bars[0].get("date", ""))
        last_date = str(bars[-1].get("date", ""))
        if first_date and last_date and first_date > last_date:
            out.reverse()
    return out


def atr(bars: list[dict], period: int = 14) -> float:
    """Average True Range — the honest unit of 'how far can this move'."""
    if len(bars) < 2:
        return 0.0
    trs = []
    for i in range(1, len(bars)):
        h, l, pc = bars[i]["high"], bars[i]["low"], bars[i - 1]["close"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    window = trs[-period:]
    return sum(window) / len(window) if window else 0.0


def rsi(closes: list[float], period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(len(closes) - period, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return round(100 - 100 / (1 + rs), 1)


def ema(closes: list[float], period: int) -> float:
    if not closes:
        return 0.0
    k = 2 / (period + 1)
    value = closes[0]
    for c in closes[1:]:
        value = c * k + value * (1 - k)
    return value


def macd_histogram(closes: list[float]) -> float:
    """MACD(12,26,9) histogram — momentum acceleration, not just direction."""
    if len(closes) < 26:
        return 0.0
    macd_series = []
    for i in range(26, len(closes) + 1):
        window = closes[:i]
        macd_series.append(ema(window, 12) - ema(window, 26))
    signal = ema(macd_series, 9) if len(macd_series) >= 9 else (
        sum(macd_series) / len(macd_series)
    )
    return macd_series[-1] - signal


def sma(closes: list[float], period: int) -> float:
    if not closes:
        return 0.0
    window = closes[-period:]
    return sum(window) / len(window)


def swing_levels(bars: list[dict], lookback: int = 90, wing: int = 2) -> dict:
    """
    Support/resistance from swing pivots (fractals), clustered within 0.75×ATR
    so five touches of the same zone count as ONE level, ranked by touches.
    """
    bars = bars[-lookback:]
    if len(bars) < wing * 2 + 1:
        return {"support": [], "resistance": []}
    a = atr(bars) or (bars[-1]["close"] * 0.02)
    highs, lows = [], []
    for i in range(wing, len(bars) - wing):
        window = bars[i - wing: i + wing + 1]
        if bars[i]["high"] == max(b["high"] for b in window):
            highs.append(bars[i]["high"])
        if bars[i]["low"] == min(b["low"] for b in window):
            lows.append(bars[i]["low"])

    def cluster(levels: list[float]) -> list[dict]:
        clusters: list[list[float]] = []
        for lv in sorted(levels):
            if clusters and abs(lv - clusters[-1][-1]) <= 0.75 * a:
                clusters[-1].append(lv)
            else:
                clusters.append([lv])
        ranked = [
            {"level": round(sum(c) / len(c), 2), "touches": len(c)}
            for c in clusters
        ]
        ranked.sort(key=lambda x: -x["touches"])
        return ranked

    price = bars[-1]["close"]
    support = [c for c in cluster(lows) if c["level"] < price][:4]
    resistance = [c for c in cluster(highs) if c["level"] > price][:4]
    support.sort(key=lambda x: -x["level"])       # nearest first
    resistance.sort(key=lambda x: x["level"])     # nearest first
    return {"support": support, "resistance": resistance}


def classify_regime(closes: list[float]) -> str:
    """TRENDING_UP / TRENDING_DOWN / RANGE_BOUND / VOLATILE_CHOP."""
    if len(closes) < 25:
        return "RANGE_BOUND"
    price = closes[-1]
    s20, s50 = sma(closes, 20), sma(closes, 50)
    s20_prev = sma(closes[:-5], 20) if len(closes) > 25 else s20
    slope = (s20 - s20_prev) / s20_prev * 100 if s20_prev else 0.0

    returns = [
        (closes[i] - closes[i - 1]) / closes[i - 1]
        for i in range(max(1, len(closes) - 20), len(closes))
        if closes[i - 1]
    ]
    vol = (sum(r * r for r in returns) / len(returns)) ** 0.5 * 100 if returns else 0.0

    if price > s20 > s50 and slope > 0.3:
        return "TRENDING_UP"
    if price < s20 < s50 and slope < -0.3:
        return "TRENDING_DOWN"
    if vol > 3.5:
        return "VOLATILE_CHOP"
    return "RANGE_BOUND"


# ─────────────────────────────────────────────────────────────────────────────
# The expert view — direction, conviction, setup, trade plan, commentary
# ─────────────────────────────────────────────────────────────────────────────


def expert_view(raw_bars: list[dict], price: Optional[float] = None) -> dict:
    """
    Compute a professional read of the chart. Returns a dict with:
      direction, bias, conviction, regime, setup, indicators, key_levels,
      trade_plan {entry, stop, target1, target2, risk_reward},
      expected_move_pct (1-week, ATR-based), commentary (expert sentences).
    """
    bars = normalize_bars(raw_bars)
    if len(bars) < 15:
        # A professional does not call a chart off a handful of bars.
        return _empty_view(price if price else (bars[-1]["close"] if bars else None))
    closes = [b["close"] for b in bars]
    px = _f(price, closes[-1]) or closes[-1]

    a = atr(bars)
    atr_pct = round(a / px * 100, 2) if px else 0.0
    r = rsi(closes)
    hist = macd_histogram(closes)
    s20, s50 = round(sma(closes, 20), 2), round(sma(closes, 50), 2)
    regime = classify_regime(closes)
    levels = swing_levels(bars)
    vols = [b["volume"] for b in bars if b["volume"] > 0]
    vol_ratio = round(vols[-1] / (sum(vols[-20:]) / len(vols[-20:])), 2) if len(vols) >= 5 else 1.0
    chg20 = round((closes[-1] - closes[-21]) / closes[-21] * 100, 2) if len(closes) > 21 else 0.0

    # ── Directional score: trend structure + momentum + confirmation ────────
    score = 0.0
    if px > s20 > s50:
        score += 2
    elif px < s20 < s50:
        score -= 2
    elif px > s20:
        score += 0.5
    elif px < s20:
        score -= 0.5
    if hist > 0:
        score += 1
    elif hist < 0:
        score -= 1
    if 55 <= r <= 72:
        score += 1          # healthy momentum
    elif r > 78:
        score -= 0.5        # stretched — chasing here is amateur hour
    elif 28 <= r <= 42:
        score -= 1
    elif r < 25:
        score += 0.5        # washed out — reversal risk for shorts
    score += max(-1.0, min(1.0, chg20 / 8))
    if vol_ratio >= 1.3:
        score += 0.5 if score > 0 else -0.5 if score < 0 else 0.0

    if score >= 2.0:
        direction = "UP"
    elif score <= -2.0:
        direction = "DOWN"
    else:
        direction = "SIDEWAYS"
    bias = "bullish" if score > 0.5 else "bearish" if score < -0.5 else "neutral"
    conviction = int(min(90, 42 + abs(score) * 9 + (5 if vol_ratio >= 1.3 else 0)))

    setup = _classify_setup(direction, regime, r, hist, px, s20, levels, a)
    plan = _trade_plan(direction, bias, px, a, levels)
    expected_move_pct = round(max(atr_pct * math.sqrt(5), 0.5), 2)  # ~1-week ATR move

    view = {
        "direction": direction,
        "bias": bias,
        "conviction": conviction,
        "score": round(score, 2),
        "regime": regime,
        "setup": setup["name"],
        "setup_action": setup["action"],
        "indicators": {
            "price": round(px, 2), "atr": round(a, 4), "atr_pct": atr_pct,
            "rsi14": r, "macd_hist": round(hist, 4),
            "sma20": s20, "sma50": s50,
            "volume_ratio": vol_ratio, "change_20d_pct": chg20,
        },
        "key_levels": levels,
        "trade_plan": plan,
        "expected_move_pct": expected_move_pct,
        "bars_used": len(bars),
    }
    view["commentary"] = _commentary(view)
    return view


def _empty_view(price) -> dict:
    px = _f(price)
    return {
        "direction": "SIDEWAYS", "bias": "neutral", "conviction": 25, "score": 0.0,
        "regime": "RANGE_BOUND", "setup": "insufficient_data",
        "setup_action": "Collect more price history before trading this name.",
        "indicators": {"price": px}, "key_levels": {"support": [], "resistance": []},
        "trade_plan": {"entry": px or None, "stop": None, "target1": None,
                       "target2": None, "risk_reward": None},
        "expected_move_pct": 0.0, "bars_used": 0,
        "commentary": "Not enough price history for a professional read — no trade.",
    }


def _classify_setup(direction, regime, r, hist, px, s20, levels, a) -> dict:
    near_support = bool(levels["support"]) and (px - levels["support"][0]["level"]) <= 1.2 * a
    near_resistance = bool(levels["resistance"]) and (levels["resistance"][0]["level"] - px) <= 1.2 * a

    if regime == "TRENDING_UP":
        if r >= 78:
            return {"name": "overbought_extension",
                    "action": "Trend is strong but stretched — let it pull back to the 20-day line before adding."}
        if abs(px - s20) <= 0.8 * a and r <= 60:
            return {"name": "pullback_in_uptrend",
                    "action": "Classic buy-the-dip zone: price resting on the rising 20-day average with momentum reset."}
        if near_resistance:
            return {"name": "breakout_watch",
                    "action": "Coiling under resistance in an uptrend — a volume close above it is the entry trigger."}
        return {"name": "momentum_continuation",
                "action": "Trend, momentum, and structure aligned — buy strength, trail the stop under the 20-day line."}
    if regime == "TRENDING_DOWN":
        if r >= 55:
            return {"name": "bear_rally_fade",
                    "action": "A bounce inside a downtrend — rallies into the falling 20-day line are exits, not entries."}
        if r <= 25:
            return {"name": "oversold_reversal_watch",
                    "action": "Deeply washed out — do not short here; wait for a base to form before touching the long side."}
        return {"name": "breakdown_risk",
                "action": "Lower highs, lower lows, momentum negative — stand aside or defend existing exposure."}
    if regime == "VOLATILE_CHOP":
        return {"name": "volatile_chop",
                "action": "Whipsaw conditions — size down or sit out; chop kills more accounts than crashes do."}
    if near_support:
        return {"name": "range_buy_zone",
                "action": "At the floor of the range with a tight, well-defined stop just below support."}
    if near_resistance:
        return {"name": "range_sell_zone",
                "action": "At the ceiling of the range — take profits or wait for a confirmed breakout to chase."}
    return {"name": "range_trade",
            "action": "Mid-range, no edge — the professional trade is patience until price reaches a level."}


def _trade_plan(direction, bias, px, a, levels) -> dict:
    if a <= 0 or px <= 0:
        return {"entry": round(px, 2) or None, "stop": None, "target1": None,
                "target2": None, "risk_reward": None}
    sup = levels["support"][0]["level"] if levels["support"] else None
    res = levels["resistance"][0]["level"] if levels["resistance"] else None

    if direction == "UP" or (direction == "SIDEWAYS" and bias == "bullish"):
        entry = px
        stop = sup - 0.25 * a if sup and (px - sup) <= 3 * a else entry - 1.5 * a
        target1 = res if res and (res - entry) >= 1.0 * a else entry + 2.0 * a
        target2 = entry + 3.5 * a
    elif direction == "DOWN" or (direction == "SIDEWAYS" and bias == "bearish"):
        entry = px
        stop = res + 0.25 * a if res and (res - px) <= 3 * a else entry + 1.5 * a
        target1 = sup if sup and (entry - sup) >= 1.0 * a else entry - 2.0 * a
        target2 = entry - 3.5 * a
    else:
        # True range trade: buy the floor, risk a quarter-ATR under it, sell the ceiling
        entry = sup if sup else px - 1.5 * a
        stop = entry - 0.75 * a
        target1 = res if res else px + 1.5 * a
        target2 = target1
    risk = abs(entry - stop)
    reward = abs(target1 - entry)
    rr = round(reward / risk, 2) if risk > 0 else None
    return {
        "entry": round(entry, 2), "stop": round(stop, 2),
        "target1": round(target1, 2), "target2": round(target2, 2),
        "risk_reward": rr,
    }


def _commentary(view: dict) -> str:
    ind = view["indicators"]
    plan = view["trade_plan"]
    lv = view["key_levels"]
    parts = []
    trend_txt = {
        "TRENDING_UP": "in an established uptrend (price above rising 20/50-day averages)",
        "TRENDING_DOWN": "in a confirmed downtrend (price below falling 20/50-day averages)",
        "RANGE_BOUND": "range-bound between well-defined levels",
        "VOLATILE_CHOP": "in high-volatility chop with no reliable structure",
    }[view["regime"]]
    parts.append(
        f"Price {ind.get('price')} is {trend_txt}; RSI {ind.get('rsi14')} with "
        f"{'positive' if ind.get('macd_hist', 0) > 0 else 'negative'} MACD momentum "
        f"and volume running {ind.get('volume_ratio', 1.0)}x its 20-day average."
    )
    if lv["support"] or lv["resistance"]:
        sup_txt = ", ".join(str(s["level"]) for s in lv["support"][:2]) or "none nearby"
        res_txt = ", ".join(str(r["level"]) for r in lv["resistance"][:2]) or "none nearby"
        parts.append(f"Key support {sup_txt}; resistance {res_txt}.")
    parts.append(view["setup_action"])
    if plan.get("stop") is not None and plan.get("risk_reward"):
        parts.append(
            f"The plan: entry near {plan['entry']}, stop {plan['stop']}, first target "
            f"{plan['target1']} — {plan['risk_reward']}:1 reward-to-risk with an expected "
            f"1-week move of ±{view['expected_move_pct']}% (ATR-based)."
        )
    return " ".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Expert desk note — the chat-facing answer when no LLM is available
# ─────────────────────────────────────────────────────────────────────────────


def desk_note(ticker: str, view: dict, headlines: Optional[list] = None,
              extra_context: str = "") -> str:
    """Format an expert_view as a trading-desk note. This is the LLM-free chat answer."""
    ind = view["indicators"]
    plan = view["trade_plan"]
    action = {
        "UP": "BUY / ACCUMULATE", "DOWN": "AVOID / REDUCE", "SIDEWAYS": "WAIT FOR LEVELS",
    }[view["direction"]]
    lines = [
        f"📋 {ticker} — Desk Note ({view['setup'].replace('_', ' ').title()})",
        "═" * 46,
        f"Call: {action}  |  Conviction: {view['conviction']}%  |  Regime: {view['regime'].replace('_', ' ').title()}",
        "",
        f"Read: {view['commentary']}",
    ]
    if plan.get("stop") is not None:
        lines += [
            "",
            "Trade plan:",
            f"  Entry  {plan['entry']}",
            f"  Stop   {plan['stop']}  (risk defined before reward — always)",
            f"  T1     {plan['target1']}   T2  {plan['target2']}"
            + (f"   R:R {plan['risk_reward']}:1" if plan.get("risk_reward") else ""),
        ]
    if headlines:
        lines += ["", "Tape (latest headlines):"]
        for h in headlines[:3]:
            txt = h.get("headline") if isinstance(h, dict) else str(h)
            lines.append(f"  • {str(txt)[:110]}")
    if extra_context:
        lines += ["", extra_context]
    lines += [
        "",
        f"Discipline: never risk more than the stop; RSI {ind.get('rsi14')} and "
        f"±{view['expected_move_pct']}% weekly ATR say size accordingly.",
    ]
    return "\n".join(lines)
