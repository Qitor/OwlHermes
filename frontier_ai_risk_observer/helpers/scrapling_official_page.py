"""Scrapling-based official page extraction helper.

Uses Scrapling's Adaptor for HTML parsing and httpx for fetching.
Does NOT crawl recursively, use proxy rotation, bypass CAPTCHAs,
store raw items, call LLMs, or judge risk relevance.
"""

from __future__ import annotations

import re
from urllib.parse import urljoin

import httpx
from scrapling.parser import Adaptor

from frontier_ai_risk_observer.helpers.models import CandidateItem
from frontier_ai_risk_observer.services.dedup import canonicalize_url


def extract_candidates_from_html(
    html: str,
    source_id: str,
    base_url: str,
    kind: str = "web_article",
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
    limit: int = 10,
    discovery_method: str = "scrapling_official_page",
) -> list[CandidateItem]:
    """Extract candidate items from HTML content using Scrapling Adaptor.

    This is the primary offline-testable function. It does NOT fetch URLs.
    """
    adaptor = Adaptor(html)
    links = adaptor.css("a[href]")

    seen_urls: set[str] = set()
    candidates: list[CandidateItem] = []

    include_re = [re.compile(p) for p in (include_patterns or [])]
    exclude_re = [re.compile(p) for p in (exclude_patterns or [])]

    for link in links:
        href = link.attrib.get("href", "")
        if not href or href.startswith(("#", "javascript:", "mailto:")):
            continue

        absolute_url = urljoin(base_url, href)
        canonical = canonicalize_url(absolute_url)

        if not canonical or canonical in seen_urls:
            continue
        if canonical.startswith(("http://", "https://")) and _is_navigation_url(canonical):
            continue

        # Apply include/exclude patterns
        if include_re and not any(r.search(canonical) for r in include_re):
            continue
        if exclude_re and any(r.search(canonical) for r in exclude_re):
            continue

        seen_urls.add(canonical)
        title = (link.text or "").strip()
        if not title:
            title = canonical

        candidates.append(CandidateItem(
            source_id=source_id,
            kind=kind,
            title=title,
            url=canonical,
            source_url=base_url,
            discovery_method=discovery_method,
        ))

        if len(candidates) >= limit:
            break

    return candidates


def fetch_and_extract(
    url: str,
    source_id: str,
    kind: str = "web_article",
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
    limit: int = 10,
    timeout: float = 30.0,
) -> list[CandidateItem]:
    """Fetch an official page and extract candidate items.

    This function DOES fetch from the network. Do not call in default tests.
    """
    response = httpx.get(url, timeout=timeout, follow_redirects=True)
    response.raise_for_status()
    return extract_candidates_from_html(
        html=response.text,
        source_id=source_id,
        base_url=url,
        kind=kind,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        limit=limit,
        discovery_method="scrapling_official_page_fetch",
    )


_NAV_SUFFIXES = (
    "/about", "/contact", "/privacy", "/terms", "/login", "/signup",
    "/careers", "/jobs", "/press", "/faq", "/help", "/support",
    "/subscribe", "/newsletter", "/rss",
)


def _is_navigation_url(url: str) -> bool:
    """Skip common navigation/footer URLs."""
    lower = url.lower().rstrip("/")
    for suffix in _NAV_SUFFIXES:
        if lower.endswith(suffix):
            return True
    return False
