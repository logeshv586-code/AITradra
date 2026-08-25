"""Fail-closed numeric validation helpers for market and execution evidence."""

from __future__ import annotations

import math
from typing import Any


def require_finite_number(value: Any, label: str) -> float:
    """Return ``value`` as float only when it is a real finite number.

    ``NaN`` and positive/negative infinity are intentionally rejected because
    ordinary comparisons such as ``value <= 0`` do not reliably catch NaN.
    """
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise AssertionError(f"{label} is not numeric: {value!r}") from exc

    if not math.isfinite(number):
        raise AssertionError(f"{label} is not finite: {value!r}")
    return number


def require_positive_finite(value: Any, label: str) -> float:
    """Return a finite float strictly greater than zero, otherwise fail closed."""
    number = require_finite_number(value, label)
    if number <= 0:
        raise AssertionError(f"{label} must be > 0: {number}")
    return number
