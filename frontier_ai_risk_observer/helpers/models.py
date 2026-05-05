"""Shared candidate item model for discovery helper output.

This is helper output only — it does NOT automatically store items.
Hermes decides whether to call risk_raw_item_store for any candidate.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class CandidateItem(BaseModel):
    """A candidate item discovered by a source helper."""

    source_id: str
    kind: str
    title: str
    url: str
    published_at: datetime | None = None
    summary: str | None = None
    content_text: str | None = None
    source_url: str
    discovery_method: str
    metadata: dict[str, Any] = {}
