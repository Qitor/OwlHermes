"""Source health reporting service.

Reports helper coverage, known issues, and entries requiring human review.
Does NOT fetch from the network by default.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from frontier_ai_risk_observer.registry.loader import load_registry_bundle
from frontier_ai_risk_observer.registry.validators import validate_registry_bundle


def source_health_summary() -> dict[str, Any]:
    """Return a source health summary without fetching network."""
    bundle = load_registry_bundle()
    validated = validate_registry_bundle(bundle)

    helper_counts: Counter[str] = Counter()
    known_issues_entries: list[dict[str, str]] = []
    human_review_entries: list[dict[str, str]] = []
    scrapling_entries: list[dict[str, str]] = []
    missing_scrapling_url: list[dict[str, str]] = []
    missing_feed_url: list[dict[str, str]] = []
    invalid_urls: list[dict[str, str]] = []

    # Sources
    for entry in validated.sources:
        ht = getattr(entry, "helper_type", None) or "none"
        helper_counts[f"source:{ht}"] += 1
        if ht == "scrapling_official_page":
            scrapling_entries.append({"id": entry.id, "name": entry.name})
            if not getattr(entry, "scrapling_url", None) and not getattr(entry, "list_url", None):
                missing_scrapling_url.append({"id": entry.id, "name": entry.name})
        if ht in ("rss",) and not getattr(entry, "feed_url", None):
            missing_feed_url.append({"id": entry.id, "name": entry.name})
        _check_issues(entry, known_issues_entries, human_review_entries, invalid_urls)

    # Podcasts
    for entry in validated.podcasts:
        ht = getattr(entry, "helper_type", None) or "none"
        helper_counts[f"podcast:{ht}"] += 1
        if ht == "scrapling_official_page":
            scrapling_entries.append({"id": entry.id, "name": entry.name})
            if not getattr(entry, "scrapling_url", None):
                missing_scrapling_url.append({"id": entry.id, "name": entry.name})
        if ht == "podcast_rss" and not getattr(entry, "feed_url", None):
            missing_feed_url.append({"id": entry.id, "name": entry.name})
        _check_issues(entry, known_issues_entries, human_review_entries, invalid_urls)

    # Events
    for entry in validated.events:
        ht = getattr(entry, "helper_type", None) or "none"
        helper_counts[f"event:{ht}"] += 1
        if ht == "scrapling_official_page":
            scrapling_entries.append({"id": entry.id, "name": entry.name})
            if not getattr(entry, "scrapling_url", None):
                missing_scrapling_url.append({"id": entry.id, "name": entry.name})
        _check_issues(entry, known_issues_entries, human_review_entries, invalid_urls)

    # Benchmarks
    for entry in validated.benchmarks:
        ht = getattr(entry, "helper_type", None) or "none"
        helper_counts[f"benchmark:{ht}"] += 1
        _check_issues(entry, known_issues_entries, human_review_entries, invalid_urls)

    return {
        "ok": True,
        "helper_coverage": dict(helper_counts),
        "scrapling_entries": scrapling_entries,
        "missing_scrapling_url": missing_scrapling_url,
        "missing_feed_url": missing_feed_url,
        "known_issues_count": len(known_issues_entries),
        "known_issues": known_issues_entries[:10],
        "requires_human_review_count": len(human_review_entries),
        "requires_human_review": human_review_entries[:10],
        "invalid_urls_count": len(invalid_urls),
        "invalid_urls": invalid_urls[:10],
    }


def _check_issues(
    entry: Any,
    known_issues: list[dict[str, str]],
    human_review: list[dict[str, str]],
    invalid_urls: list[dict[str, str]],
) -> None:
    ki = getattr(entry, "known_issues", None)
    if ki:
        known_issues.append({"id": entry.id, "known_issues": ki})
    hr = getattr(entry, "requires_human_review", None)
    if hr:
        human_review.append({"id": entry.id, "name": getattr(entry, "name", entry.id)})
    # Check URL validity
    for url_field in ("url", "feed_url", "scrapling_url", "list_url", "current_url", "watch_url"):
        url_val = getattr(entry, url_field, None)
        if url_val and not _is_valid_url(url_val):
            invalid_urls.append({"id": entry.id, "field": url_field, "url": url_val})


def _is_valid_url(url: str) -> bool:
    return url.startswith(("http://", "https://")) and len(url.split("://", 1)[1]) > 0
