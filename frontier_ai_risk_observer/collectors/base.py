"""Optional deterministic helper collector skeletons.

Hermes-Agent remains the primary operator for judgment-heavy discovery,
research, video/transcript handling, triage, and digest writing. Helpers in
this package are only for stable low-intelligence sources such as RSS,
podcast RSS, arXiv, sitemaps, and simple webpage hash/diff.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class RawCollectedItem:
    """Minimal raw item shape produced by collectors before persistence exists."""

    source_id: str
    title: str
    url: str
    content: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


class Collector(Protocol):
    """Protocol implemented by optional deterministic helper collectors."""

    def collect(self, source: dict[str, object]) -> list[RawCollectedItem]:
        """Collect helper raw items for a registry source."""
