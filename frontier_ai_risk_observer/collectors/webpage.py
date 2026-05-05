"""Optional webpage hash/diff helper placeholder.

Hermes should handle judgment-heavy web research. This module is only for
future stable sitemap or simple webpage hash/diff helpers.
"""

from __future__ import annotations

from frontier_ai_risk_observer.collectors.base import RawCollectedItem


def collect_webpage(source: dict[str, object]) -> list[RawCollectedItem]:
    """Return no items until optional webpage helper behavior is implemented."""
    _ = source
    return []
