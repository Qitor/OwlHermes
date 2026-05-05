"""RSS/Atom feed helper using feedparser.

Does NOT store raw items, call LLMs, or judge risk relevance.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import feedparser

from frontier_ai_risk_observer.helpers.models import CandidateItem
from frontier_ai_risk_observer.services.dedup import canonicalize_url


def parse_rss_feed(
    feed_content: str,
    source_id: str,
    base_url: str,
    kind: str = "web_article",
    limit: int = 20,
    lookback_days: int | None = None,
    discovery_method: str = "rss",
) -> list[CandidateItem]:
    """Parse RSS/Atom feed content into candidate items.

    This is the offline-testable function. It does NOT fetch from the network.
    """
    feed = feedparser.parse(feed_content)
    candidates: list[CandidateItem] = []
    cutoff = _cutoff_datetime(lookback_days)

    for entry in feed.entries:
        url = _entry_link(entry)
        if not url:
            continue

        canonical = canonicalize_url(url)
        if not canonical:
            continue

        published_at = _entry_published(entry)
        if cutoff and published_at and published_at < cutoff:
            continue

        title = entry.get("title", "").strip() or canonical
        summary = entry.get("summary", "").strip() or None

        candidates.append(CandidateItem(
            source_id=source_id,
            kind=kind,
            title=title,
            url=canonical,
            published_at=published_at,
            summary=summary,
            source_url=base_url,
            discovery_method=discovery_method,
        ))

        if len(candidates) >= limit:
            break

    return candidates


def fetch_and_parse(
    feed_url: str,
    source_id: str,
    kind: str = "web_article",
    limit: int = 20,
    lookback_days: int | None = None,
    timeout: float = 30.0,
) -> list[CandidateItem]:
    """Fetch an RSS/Atom feed and parse it into candidate items.

    This function DOES fetch from the network. Do not call in default tests.
    """
    import httpx

    response = httpx.get(feed_url, timeout=timeout, follow_redirects=True)
    response.raise_for_status()
    return parse_rss_feed(
        feed_content=response.text,
        source_id=source_id,
        base_url=feed_url,
        kind=kind,
        limit=limit,
        lookback_days=lookback_days,
        discovery_method="rss_fetch",
    )


def _entry_link(entry: Any) -> str | None:
    link = entry.get("link")
    if link:
        return link
    for link_obj in entry.get("links", []):
        href = link_obj.get("href")
        if href:
            return href
    return None


def _entry_published(entry: Any) -> datetime | None:
    for field in ("published_parsed", "updated_parsed"):
        parsed = entry.get(field)
        if parsed:
            try:
                from time import mktime
                return datetime.fromtimestamp(mktime(parsed), tz=UTC)
            except Exception:
                pass
    return None


def _cutoff_datetime(lookback_days: int | None) -> datetime | None:
    if lookback_days is None:
        return None
    from datetime import timedelta
    return datetime.now(UTC) - timedelta(days=lookback_days)
