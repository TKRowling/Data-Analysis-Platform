"""Correlation strength bands. The single source of truth for |r| thresholds.

Import from here rather than redeclaring 0.7 anywhere else. ``eda_service`` and
``relationship.pair_relationship`` should both use these.
"""
from __future__ import annotations

STRONG = 0.7
MODERATE = 0.4
# Above this, a "feature" is almost certainly derived from the target, not predictive of it.
LEAKAGE = 0.98


def strength(value: float | None) -> str:
    """Band an absolute correlation coefficient."""
    if value is None:
        return "undefined"
    magnitude = abs(float(value))
    if magnitude >= STRONG:
        return "strong"
    if magnitude >= MODERATE:
        return "moderate"
    return "weak"


def direction(value: float | None) -> str:
    if value is None:
        return "undefined"
    return "positive" if value >= 0 else "negative"