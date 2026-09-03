"""Multi-asset portfolio optimization helpers.

PyPortfolioOpt is used only when enough clean multi-asset history is supplied.
Failure or missing optional dependencies falls back to deterministic inverse-
volatility weights. Returned weights are advisory and are always clipped by the
central MAX_POSITION_PCT limit before any order sizing can use them.
"""

from __future__ import annotations

from math import isfinite
from typing import Any

import numpy as np
import pandas as pd


def _clean_price_frame(price_history: Any) -> pd.DataFrame:
    if isinstance(price_history, pd.DataFrame):
        frame = price_history.copy()
    elif isinstance(price_history, dict):
        frame = pd.DataFrame({str(k): pd.Series(v, dtype=float) for k, v in price_history.items()})
    else:
        return pd.DataFrame()

    if frame.empty:
        return frame
    frame = frame.apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan)
    frame = frame.dropna(axis=1, how="all").ffill().dropna(how="any")
    frame = frame.loc[:, frame.nunique(dropna=True) > 1]
    return frame


def _cap_and_normalize(weights: dict[str, float], max_weight: float) -> dict[str, float]:
    cap = max(0.0, min(float(max_weight), 1.0))
    cleaned = {
        str(asset): max(0.0, min(float(weight), cap))
        for asset, weight in weights.items()
        if isfinite(float(weight)) and float(weight) > 0
    }
    total = sum(cleaned.values())
    if total <= 0:
        return {}
    # Do not renormalize above the safety cap. Unallocated weight remains cash.
    return {asset: round(weight, 8) for asset, weight in cleaned.items()}


def inverse_volatility_allocation(price_history: Any, max_weight: float) -> dict[str, Any]:
    frame = _clean_price_frame(price_history)
    if frame.shape[1] < 2 or len(frame) < 30:
        return {"available": False, "method": "insufficient_multi_asset_history", "weights": {}}
    returns = frame.pct_change().dropna()
    vol = returns.std(ddof=1).replace(0, np.nan).dropna()
    if vol.empty:
        return {"available": False, "method": "insufficient_volatility", "weights": {}}
    inv = 1.0 / vol
    raw = (inv / inv.sum()).to_dict()
    return {
        "available": True,
        "method": "inverse_volatility_fallback",
        "weights": _cap_and_normalize(raw, max_weight),
        "assets": list(frame.columns),
        "observations": int(len(frame)),
    }


def hrp_allocation(price_history: Any, max_weight: float) -> dict[str, Any]:
    """Return Hierarchical Risk Parity weights using PyPortfolioOpt when available."""
    frame = _clean_price_frame(price_history)
    if frame.shape[1] < 2 or len(frame) < 30:
        return {"available": False, "method": "insufficient_multi_asset_history", "weights": {}}

    returns = frame.pct_change().dropna()
    if returns.empty:
        return {"available": False, "method": "insufficient_returns", "weights": {}}

    try:
        from pypfopt.hierarchical_portfolio import HRPOpt

        optimizer = HRPOpt(returns=returns)
        raw_weights = optimizer.optimize()
        weights = _cap_and_normalize(raw_weights, max_weight)
        return {
            "available": bool(weights),
            "method": "pypfopt_hrp",
            "weights": weights,
            "assets": list(frame.columns),
            "observations": int(len(frame)),
            "raw_weight_sum": round(float(sum(raw_weights.values())), 8),
            "cash_reserve_fraction": round(max(0.0, 1.0 - sum(weights.values())), 8),
        }
    except Exception as exc:
        fallback = inverse_volatility_allocation(frame, max_weight)
        fallback["pypfopt_error"] = type(exc).__name__
        return fallback
