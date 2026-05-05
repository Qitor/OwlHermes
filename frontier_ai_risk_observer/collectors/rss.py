"""Optional RSS helper placeholder.

Real network fetching is intentionally deferred. This helper should only
cover stable feeds and must write through the Hermes-facing ingestion
interface once implemented.
"""

from __future__ import annotations

from frontier_ai_risk_observer.collectors.base import RawCollectedItem


def collect_rss(source: dict[str, object]) -> list[RawCollectedItem]:
    """Return no items until optional RSS helper behavior is implemented."""
    _ = source
    return []
