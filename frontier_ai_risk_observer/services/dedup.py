"""Deterministic raw item normalization and dedup helpers.

These helpers never fetch remote pages or inspect external canonical links.
Hermes owns discovery and judgment; this module only normalizes local inputs.
"""

from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_QUERY_PARAMS = {
    "fbclid",
    "gclid",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
}

RAW_ITEM_STATUS_NEW = "new"
RAW_ITEM_STATUS_TRIAGE_PENDING = "triage_pending"
RAW_ITEM_STATUS_SEEN_DUPLICATE = "seen_duplicate"
RAW_ITEM_STATUS_TRIAGED = "triaged"
RAW_ITEM_STATUS_IGNORED = "ignored"
RAW_ITEM_STATUS_ERROR = "error"

RAW_ITEM_STATUSES = {
    RAW_ITEM_STATUS_NEW,
    RAW_ITEM_STATUS_TRIAGE_PENDING,
    RAW_ITEM_STATUS_SEEN_DUPLICATE,
    RAW_ITEM_STATUS_TRIAGED,
    RAW_ITEM_STATUS_IGNORED,
    RAW_ITEM_STATUS_ERROR,
}


def canonicalize_url(url: str) -> str:
    """Return a conservative deterministic URL canonicalization."""
    stripped = url.strip()
    if not stripped:
        return stripped

    parts = urlsplit(stripped)
    scheme = parts.scheme.lower()
    hostname = (parts.hostname or "").lower()
    netloc = hostname
    if parts.port is not None:
        netloc = f"{netloc}:{parts.port}"
    if parts.username:
        userinfo = parts.username
        if parts.password:
            userinfo = f"{userinfo}:{parts.password}"
        netloc = f"{userinfo}@{netloc}"

    path = parts.path
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    query_pairs = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in TRACKING_QUERY_PARAMS
    ]
    query = urlencode(query_pairs, doseq=True)
    return urlunsplit((scheme, netloc, path, query, ""))


def normalize_title(title: str | None) -> str | None:
    """Normalize a title for exact deterministic matching."""
    if title is None:
        return None
    normalized = re.sub(r"\s+", " ", title.casefold()).strip()
    return normalized or None


def compute_content_hash(text: str | None) -> str | None:
    """Compute a deterministic SHA-256 hash for normalized text content."""
    if text is None:
        return None
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return None
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def build_dedup_key(
    *,
    canonical_url: str | None = None,
    content_hash: str | None = None,
    source_id: str | None = None,
    normalized_title: str | None = None,
) -> str | None:
    """Build the preferred deterministic dedup key for local matching."""
    if canonical_url:
        return f"url:{canonical_url}"
    if content_hash:
        return f"hash:{content_hash}"
    if source_id and normalized_title:
        return f"title:{source_id}:{normalized_title}"
    return None
