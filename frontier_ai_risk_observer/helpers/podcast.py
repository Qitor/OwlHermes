"""Podcast RSS feed helper.

Parses podcast RSS to extract episode metadata.
Does NOT download audio, fetch transcripts, summarize episodes,
store raw items, call LLMs, or judge risk relevance.
"""

from __future__ import annotations

from frontier_ai_risk_observer.helpers.models import CandidateItem
from frontier_ai_risk_observer.helpers.rss import parse_rss_feed


def parse_podcast_feed(
    feed_content: str,
    source_id: str,
    base_url: str,
    limit: int = 10,
    lookback_days: int | None = None,
) -> list[CandidateItem]:
    """Parse podcast RSS feed content into candidate items.

    This is the offline-testable function. It does NOT fetch from the network.
    """
    return parse_rss_feed(
        feed_content=feed_content,
        source_id=source_id,
        base_url=base_url,
        kind="podcast_episode",
        limit=limit,
        lookback_days=lookback_days,
        discovery_method="podcast_rss",
    )


def fetch_and_parse(
    feed_url: str,
    source_id: str,
    limit: int = 10,
    lookback_days: int | None = None,
    timeout: float = 30.0,
) -> list[CandidateItem]:
    """Fetch a podcast RSS feed and parse it.

    This function DOES fetch from the network. Do not call in default tests.
    """
    import httpx

    response = httpx.get(feed_url, timeout=timeout, follow_redirects=True)
    response.raise_for_status()
    return parse_podcast_feed(
        feed_content=response.text,
        source_id=source_id,
        base_url=feed_url,
        limit=limit,
        lookback_days=lookback_days,
    )
