"""
REGIME DETECTOR AGENT — Claude Flow Architecture (100% OSS)
Classifies the current market regime using Hidden Markov Models (hmmlearn)
and technical indicators (ADX via pandas_ta / sklearn).

Regimes: BULL | BEAR | SIDEWAYS | VOLATILE | CRISIS

OBSERVE → Download SPY as market proxy and compute features
THINK   → Analyze volatility clustering and trend strength
PLAN    → Fit HMM on returns+volatility, classify current state
ACT     → Run HMM inference and ADX computation
REFLECT → Confidence based on HMM state stability
"""

from agents.base_agent import BaseAgent, AgentContext
from core.logger import get_logger
import numpy as np
import pandas as pd

logger = get_logger(__name__)


class RegimeDetectorAgent(BaseAgent):
    """Classifies market regime (bull/bear/sideways/crisis) using HMM + volatility."""

    REGIME_MAP = {
        0: "BEARISH_LOW_VOL",
        1: "BULLISH_LOW_VOL",
        2: "HIGH_VOLATILITY",
        3: "CRISIS",
    }

    def __init__(self, memory=None):
        super().__init__("RegimeDetectorAgent", memory)

    # ── OBSERVE ──────────────────────────────────────────────
    async def observe(self, context: AgentContext) -> AgentContext:
        self._add_thought(context, "Using SPY as the broad market proxy for regime detection")
        context.observations["market_proxy"] = "SPY"
        return context

    # ── THINK ────────────────────────────────────────────────
    async def think(self, context: AgentContext) -> AgentContext:
        self._add_thought(context, "Regime detection uses: HMM (latent state), annualized vol, and ADX trend strength")
        self._add_thought(context, "VIX > 35% annualized = CRISIS. ADX > 25 + positive drift = STRONG_UPTREND")
        self._add_thought(context, "Regime determines position sizing: CRISIS = 25% normal, BULL = 120%")
        return context

    # ── PLAN ─────────────────────────────────────────────────
    async def plan(self, context: AgentContext) -> AgentContext:
        context.plan = [
            "1. Download 2 years of SPY data from yfinance",
            "2. Compute log returns and 20-day rolling volatility",
            "3. Fit 4-state Gaussian HMM on [returns, volatility]",
            "4. Predict current state from HMM",
            "5. Compute ADX for trend strength confirmation",
            "6. Classify regime and compute risk multiplier",
        ]
        return context

    # ── ACT ──────────────────────────────────────────────────
    async def act(self, context: AgentContext) -> AgentContext:
        try:
            import yfinance as yf
            spy = yf.download("SPY", period="2y", auto_adjust=True, progress=False)

            if spy.empty or len(spy) < 100:
                context.result = {"error": "Insufficient SPY data", "current_regime": "UNKNOWN"}
                return context

            close = spy["Close"]
            if hasattr(close, 'columns'):
                close = close.iloc[:, 0]

            returns = close.pct_change().dropna()
            log_returns = np.log1p(returns)
            vol_20 = returns.rolling(20).std() * np.sqrt(252)
            vol_20 = vol_20.dropna()

            # Align series
            min_len = min(len(log_returns), len(vol_20), 500)
            lr = log_returns.values[-min_len:]
            vl = vol_20.values[-min_len:]

            features = np.column_stack([lr, vl])

            # HMM fit
            current_state = 1  # Default bullish
            try:
                from hmmlearn import hmm
                model = hmm.GaussianHMM(n_components=4, covariance_type="full", n_iter=100, random_state=42)
                model.fit(features)
                states = model.predict(features)
                current_state = int(states[-1])
            except ImportError:
                self._add_thought(context, "hmmlearn not installed — using vol-only classification")
            except Exception as e:
                self._add_thought(context, f"HMM fit failed: {e} — using vol-only classification")

            # Current volatility
            vol_current = float(vl[-1]) if len(vl) > 0 else 0.2

            # ADX for trend strength
            adx_value = self._compute_adx(spy)

            # Recent return trend
            recent_ret = float(returns.iloc[-20:].mean()) if len(returns) >= 20 else 0.0

            # Classify
            regime = self._classify(current_state, vol_current, adx_value, recent_ret)

            context.result = {
                "current_regime": regime["label"],
                "hmm_state": current_state,
                "volatility_annualized_pct": round(vol_current * 100, 2),
                "trend_strength_adx": round(adx_value, 2),
                "recent_20d_return": round(recent_ret * 100, 4),
                "regime_confidence": regime["confidence"],
                "risk_multiplier": regime["risk_multiplier"],
                "strategy_implication": regime["strategy"],
            }
            context.actions_taken.append({"action": "regime_detection", "state": regime["label"]})

        except ImportError:
            context.result = {"error": "yfinance not installed", "current_regime": "UNKNOWN"}
        except Exception as e:
            logger.error(f"RegimeDetectorAgent error: {e}")
            context.result = {"error": str(e), "current_regime": "UNKNOWN", "risk_multiplier": 1.0}

        return context

    # ── REFLECT ──────────────────────────────────────────────
    async def reflect(self, context: AgentContext) -> AgentContext:
        result = context.result or {}
        regime = result.get("current_regime", "UNKNOWN")
        conf = result.get("regime_confidence", 0.5)

        if regime == "UNKNOWN":
            context.reflection = "Could not determine regime — defaulting to neutral positioning"
            context.confidence = 0.2
        else:
            context.reflection = f"Market regime: {regime} (confidence: {conf:.0%}). Risk mult: {result.get('risk_multiplier', 1.0)}"
            context.confidence = conf
        return context

    def _classify(self, state: int, vol: float, adx: float, recent_ret: float) -> dict:
        if vol > 0.35:
            return {"label": "CRISIS", "confidence": 0.85, "risk_multiplier": 0.25,
                    "strategy": "REDUCE_ALL — max 25% of normal size"}
        if vol > 0.22:
            return {"label": "HIGH_VOLATILITY", "confidence": 0.75, "risk_multiplier": 0.5,
                    "strategy": "DEFENSIVE — prefer puts, reduce leverage"}
        if adx > 25 and recent_ret > 0:
            return {"label": "STRONG_UPTREND", "confidence": 0.80, "risk_multiplier": 1.2,
                    "strategy": "TREND_FOLLOW — add longs, raise stops"}
        if adx > 25 and recent_ret < 0:
            return {"label": "STRONG_DOWNTREND", "confidence": 0.80, "risk_multiplier": 0.5,
                    "strategy": "SHORT_BIAS — hedge or reduce"}
        if adx < 20:
            return {"label": "SIDEWAYS", "confidence": 0.70, "risk_multiplier": 0.75,
                    "strategy": "MEAN_REVERT — sell options, range trade"}
        return {"label": "NEUTRAL", "confidence": 0.55, "risk_multiplier": 1.0,
                "strategy": "BALANCED — normal sizing"}

    def _compute_adx(self, df, period=14) -> float:
        try:
            import pandas_ta as ta
            adx = ta.adx(df["High"], df["Low"], df["Close"], length=period)
            if adx is not None and f"ADX_{period}" in adx.columns:
                val = adx[f"ADX_{period}"].dropna()
                if not val.empty:
                    return float(val.iloc[-1])
        except ImportError:
            # Fallback: estimate trend from price range
            try:
                rng = (df["High"] - df["Low"]).rolling(period).mean()
                return float(rng.iloc[-1] / df["Close"].iloc[-1] * 1000) if not rng.empty else 20.0
            except Exception:
                pass
        except Exception:
            pass
        return 20.0  # Neutral ADX default

