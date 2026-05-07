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

    # R1-14: Reliability reporting
    access_status_counts: Counter[str] = Counter()
    degraded_or_blocked: list[dict[str, str]] = []
    timeout_prone: list[dict[str, str]] = []
    collection_method_counts: Counter[str] = Counter()
    all_known_failures: list[dict[str, Any]] = []

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
        _check_reliability(
            entry, access_status_counts, degraded_or_blocked,
            timeout_prone, collection_method_counts, all_known_failures,
        )

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
        _check_reliability(
            entry, access_status_counts, degraded_or_blocked,
            timeout_prone, collection_method_counts, all_known_failures,
        )

    # Events
    for entry in validated.events:
        ht = getattr(entry, "helper_type", None) or "none"
        helper_counts[f"event:{ht}"] += 1
        if ht == "scrapling_official_page":
            scrapling_entries.append({"id": entry.id, "name": entry.name})
            if not getattr(entry, "scrapling_url", None):
                missing_scrapling_url.append({"id": entry.id, "name": entry.name})
        _check_issues(entry, known_issues_entries, human_review_entries, invalid_urls)
        _check_reliability(
            entry, access_status_counts, degraded_or_blocked,
            timeout_prone, collection_method_counts, all_known_failures,
        )

    # Benchmarks
    for entry in validated.benchmarks:
        ht = getattr(entry, "helper_type", None) or "none"
        helper_counts[f"benchmark:{ht}"] += 1
        _check_issues(entry, known_issues_entries, human_review_entries, invalid_urls)
        _check_reliability(
            entry, access_status_counts, degraded_or_blocked,
            timeout_prone, collection_method_counts, all_known_failures,
        )

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
        # R1-14: Reliability fields
        "access_status_counts": dict(access_status_counts),
        "degraded_or_blocked": degraded_or_blocked,
        "timeout_prone": timeout_prone,
        "collection_method_counts": dict(collection_method_counts),
        "recent_known_failures_count": len(all_known_failures),
        "recent_known_failures": all_known_failures[:10],
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


def _check_reliability(
    entry: Any,
    access_status_counts: Counter[str],
    degraded_or_blocked: list[dict[str, str]],
    timeout_prone: list[dict[str, str]],
    collection_method_counts: Counter[str],
    all_known_failures: list[dict[str, Any]],
) -> None:
    """R1-14: Collect reliability metadata from a registry entry."""
    status = getattr(entry, "access_status", None)
    if status:
        access_status_counts[status] += 1
        if status in ("degraded", "blocked"):
            degraded_or_blocked.append({
                "id": entry.id,
                "name": getattr(entry, "name", entry.id),
                "access_status": status,
            })
        elif status == "timeout_prone":
            timeout_prone.append({
                "id": entry.id,
                "name": getattr(entry, "name", entry.id),
                "access_status": status,
            })

    method = getattr(entry, "primary_collection_method", None)
    if method:
        collection_method_counts[method] += 1

    failures = getattr(entry, "known_failures", None) or []
    for failure in failures:
        all_known_failures.append({
            "id": entry.id,
            "type": failure.type,
            "message": failure.message,
        })
