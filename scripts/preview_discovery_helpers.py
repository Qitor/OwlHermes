"""Preview discovery helper output for registry sources.

Without --fetch, prints which helper would be used.
With --fetch, runs the configured helper for allowlisted source URLs.
Does NOT store raw items, call Hermes, or call LLMs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_registry():
    from frontier_ai_risk_observer.registry.loader import load_registry_bundle
    from frontier_ai_risk_observer.registry.validators import validate_registry_bundle
    bundle = load_registry_bundle()
    return validate_registry_bundle(bundle)


def _get_helper_info(entry: object) -> dict:
    return {
        "id": getattr(entry, "id", ""),
        "name": getattr(entry, "name", ""),
        "helper_type": getattr(entry, "helper_type", None),
        "scrapling_url": getattr(entry, "scrapling_url", None),
        "list_url": getattr(entry, "list_url", None),
        "feed_url": getattr(entry, "feed_url", None),
        "max_items": getattr(entry, "max_items", None),
        "lookback_days": getattr(entry, "lookback_days", None),
    }


def preview_source(source_id: str, fetch: bool = False, limit: int = 10) -> dict:
    """Preview helper output for a single source."""
    validated = _load_registry()

    # Find the entry
    for entry in validated.sources:
        if entry.id == source_id:
            return _preview_entry(entry, fetch, limit)
    for entry in validated.podcasts:
        if entry.id == source_id:
            return _preview_entry(entry, fetch, limit)
    for entry in validated.events:
        if entry.id == source_id:
            return _preview_entry(entry, fetch, limit)
    for entry in validated.benchmarks:
        if entry.id == source_id:
            return _preview_entry(entry, fetch, limit)

    return {"ok": False, "error": f"source_id '{source_id}' not found"}


def _preview_entry(entry: object, fetch: bool, limit: int) -> dict:
    helper_type = getattr(entry, "helper_type", None)
    info = _get_helper_info(entry)

    if not helper_type or helper_type == "none" or helper_type == "manual":
        return {"ok": True, "helper_type": helper_type, "candidates": [], "info": info}

    if not fetch:
        return {
            "ok": True,
            "helper_type": helper_type,
            "would_fetch": True,
            "candidates": [],
            "info": info,
            "note": "Use --fetch to actually run the helper.",
        }

    # Fetch mode
    try:
        candidates = _run_helper(entry, limit)
        return {
            "ok": True,
            "helper_type": helper_type,
            "candidates": [c.model_dump(mode="json") for c in candidates],
            "count": len(candidates),
            "info": info,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "info": info}


def _run_helper(entry: object, limit: int) -> list:

    helper_type = getattr(entry, "helper_type", None)
    source_id = getattr(entry, "id", "")
    max_items = getattr(entry, "max_items", None) or limit

    if helper_type == "scrapling_official_page":
        from frontier_ai_risk_observer.helpers.scrapling_official_page import fetch_and_extract
        url = (
            getattr(entry, "scrapling_url", None)
            or getattr(entry, "list_url", None)
            or getattr(entry, "url", None)
        )
        if not url:
            return []
        return fetch_and_extract(
            url=url,
            source_id=source_id,
            include_patterns=getattr(entry, "link_include_patterns", None),
            exclude_patterns=getattr(entry, "link_exclude_patterns", None),
            limit=max_items,
        )
    elif helper_type == "rss":
        from frontier_ai_risk_observer.helpers.rss import fetch_and_parse
        feed_url = getattr(entry, "feed_url", None)
        if not feed_url:
            return []
        return fetch_and_parse(
            feed_url=feed_url,
            source_id=source_id,
            limit=max_items,
            lookback_days=getattr(entry, "lookback_days", None),
        )
    elif helper_type == "podcast_rss":
        from frontier_ai_risk_observer.helpers.podcast import fetch_and_parse as podcast_fetch
        feed_url = getattr(entry, "feed_url", None)
        if not feed_url:
            return []
        return podcast_fetch(
            feed_url=feed_url,
            source_id=source_id,
            limit=max_items,
            lookback_days=getattr(entry, "lookback_days", None),
        )
    elif helper_type == "arxiv_query":
        from frontier_ai_risk_observer.helpers.arxiv import fetch_and_parse as arxiv_fetch
        query = getattr(entry, "query", None)
        if not query:
            return []
        return arxiv_fetch(
            query=query,
            source_id=source_id,
            max_results=max_items,
        )
    else:
        return []


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview discovery helper output")
    parser.add_argument(
        "--source-id", type=str, help="Specific source ID to preview",
    )
    parser.add_argument(
        "--kind", type=str,
        help="Filter by registry kind (source/podcast/event/benchmark)",
    )
    parser.add_argument(
        "--limit", type=int, default=10, help="Max candidates",
    )
    parser.add_argument(
        "--fetch", action="store_true",
        help="Actually fetch from network (off by default)",
    )
    args = parser.parse_args()

    if args.source_id:
        result = preview_source(args.source_id, fetch=args.fetch, limit=args.limit)
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
        return

    # List all entries with helper metadata
    validated = _load_registry()
    groups = [
        ("sources", validated.sources),
        ("podcasts", validated.podcasts),
        ("events", validated.events),
        ("benchmarks", validated.benchmarks),
    ]
    for group_name, entries in groups:
        if args.kind and group_name != f"{args.kind}s":
            continue
        for entry in entries:
            ht = getattr(entry, "helper_type", None)
            if not ht or ht == "none":
                continue
            info = _get_helper_info(entry)
            print(json.dumps(info, ensure_ascii=False))


if __name__ == "__main__":
    main()
