"""Neutral statistical confidence utilities shared by research and trading gates.

This module intentionally has no knowledge of brokers, trading modes, research
ratings, or live authorization. Domain layers may depend on these pure functions
without depending on each other.
"""

from __future__ import annotations

import math


def wilson_lower_bound(
    successes: int,
    total: int,
    z: float = 1.959963984540054,
) -> float:
    """Return the Wilson-score lower confidence bound for a binomial rate."""
    if total <= 0:
        return 0.0
    total = int(total)
    successes = max(0, min(int(successes), total))
    p = successes / total
    z2 = z * z
    denominator = 1.0 + z2 / total
    centre = p + z2 / (2.0 * total)
    margin = z * math.sqrt((p * (1.0 - p) + z2 / (4.0 * total)) / total)
    return max(0.0, min(1.0, (centre - margin) / denominator))
