"""Minimal MCP tool surface for Hermes state access.

The functions in this module are deterministic product-state adapters. They do
not fetch external URLs, run collectors, call LLMs, summarize, or decide risk.
If the optional Python MCP SDK is installed, running this module registers the
same functions as local stdio MCP tools.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any, Literal

from pydantic import ValidationError
from sqlalchemy.orm import Session

from frontier_ai_risk_observer.api.schemas import RawItemCreate, SourceRunCreate
from frontier_ai_risk_observer.db.models import RawItem, SourceRun
from frontier_ai_risk_observer.db.session import create_session_factory
from frontier_ai_risk_observer.mcp.schemas import (
    BenchmarkObservationStoreInput,
    CandidatePreprocessInput,
    DigestSearchInput,
    DigestStoreInput,
    DuplicateCandidatesInput,
    EvidenceSearchInput,
    EvidenceStoreInput,
    LiveDailyReportUpsertInput,
    LiveEventAppendInput,
    LiveNoteUpsertInput,
    LiveRunFinalizeInput,
    LiveRunStartInput,
    RawItemSearchInput,
    RawItemSeenCheckInput,
    SignalSearchInput,
    SignalStoreInput,
)
from frontier_ai_risk_observer.services import registry_service
from frontier_ai_risk_observer.services.digest import digest_to_dict, search_digests, store_digest
from frontier_ai_risk_observer.services.ingestion import (
    UnknownRegistrySourceError,
    create_raw_item,
    list_duplicate_candidates,
    list_raw_items,
    record_source_run,
    seen_raw_item,
)
from frontier_ai_risk_observer.services.signals import (
    search_signals,
    signal_to_dict,
    store_signal,
)

try:  # pragma: no cover - exercised only when MCP SDK is installed.
    from mcp.server.fastmcp import FastMCP as _FastMCP
except Exception:  # pragma: no cover
    _FastMCP = None


SessionFactory = Callable[[], Session]
_session_factory_override: SessionFactory | None = None
mcp = _FastMCP("ai-risk-signal-observer") if _FastMCP is not None else None


def set_session_factory_for_tests(factory: SessionFactory | None) -> None:
    """Inject a test session factory without exposing DB access as an MCP tool."""
    global _session_factory_override
    _session_factory_override = factory


def risk_registry_summary() -> dict[str, Any]:
    """Return registry group counts."""
    return {"ok": True, "registry": registry_service.registry_summary()}


def risk_registry_list_due_sources(
    limit: int | None = None,
    kind: str | None = None,
    risk_domain: str | None = None,
) -> dict[str, Any]:
    """List registry entries Hermes should consider for a daily run."""
    entries = registry_service.list_due_sources(
        limit=limit,
        kind=_registry_kind(kind),
        risk_domain=risk_domain,
    )
    return {"ok": True, "entries": entries, "count": len(entries)}


def risk_registry_get_source(source_id: str) -> dict[str, Any]:
    """Return one registry entry by ID from any registry group."""
    found = registry_service.find_registry_entry(source_id)
    if found is None:
        return {"ok": False, "error_type": "not_found", "source_id": source_id}
    kind, entry = found
    entry["kind"] = kind
    return {"ok": True, "source": entry}


def risk_raw_item_seen_check(
    url: str | None = None,
    content_hash: str | None = None,
    source_id: str | None = None,
    title: str | None = None,
) -> dict[str, Any]:
    """Check whether Hermes has already seen a raw item."""
    try:
        payload = RawItemSeenCheckInput(
            url=url,
            content_hash=content_hash,
            source_id=source_id,
            title=title,
        )
        with _session_scope() as session:
            match = seen_raw_item(
                session,
                url=payload.url,
                content_hash=payload.content_hash,
                source_id=payload.source_id,
                title=payload.title,
            )
    except (ValueError, ValidationError) as exc:
        return _error("validation_error", str(exc))
    except Exception as exc:  # noqa: BLE001
        return _error("database_unavailable", str(exc))
    if match is None:
        return {"ok": True, "seen": False}
    return {
        "ok": True,
        "seen": True,
        "match_type": match.match_type,
        "raw_item_id": str(match.item.id),
        "canonical_url": match.item.canonical_url,
        "dedup_key": match.dedup_key,
    }


def risk_raw_item_store(raw_item: dict[str, Any]) -> dict[str, Any]:
    """Store Hermes-discovered raw material without fetching or triage."""
    try:
        payload = RawItemCreate.model_validate(raw_item)
        with _session_scope() as session:
            result = create_raw_item(session, payload)
    except (UnknownRegistrySourceError, ValidationError, ValueError) as exc:
        return _error("validation_error", str(exc))
    except Exception as exc:  # noqa: BLE001
        return _error("database_unavailable", str(exc))

    # Auto-mirror to live vault as candidate note (best-effort)
    item_dict = _raw_item_to_dict(result.item)
    mirror_info = _auto_mirror_to_live_vault(
        "candidate",
        slug=item_dict.get("title", "untitled-item")[:60],
        title=item_dict.get("title", "Untitled Candidate"),
        body=(
            f"**URL**: {item_dict.get('canonical_url', 'N/A')}\n\n"
            f"**Source**: {item_dict.get('source_id', 'N/A')}\n\n"
            f"**Content**: {item_dict.get('content_text', '')[:2000]}"
        ),
        source_id=item_dict.get("source_id"),
    )

    return_item = {
        "ok": True,
        "item": item_dict,
        "is_duplicate": result.is_duplicate,
        "match_type": result.match_type,
    }
    if mirror_info.get("mirrored"):
        return_item["vault_mirror"] = mirror_info
    return return_item


def risk_raw_item_search(
    source_id: str | None = None,
    url: str | None = None,
    canonical_url: str | None = None,
    content_hash: str | None = None,
    dedup_key: str | None = None,
    ingestion_status: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Search raw item memory using deterministic filters."""
    try:
        payload = RawItemSearchInput(
            source_id=source_id,
            url=url,
            canonical_url=canonical_url,
            content_hash=content_hash,
            dedup_key=dedup_key,
            ingestion_status=ingestion_status,
            limit=limit,
        )
        with _session_scope() as session:
            items = list_raw_items(session, **payload.model_dump())
    except (ValidationError, ValueError) as exc:
        return _error("validation_error", str(exc))
    except Exception as exc:  # noqa: BLE001
        return _error("database_unavailable", str(exc))
    return {"ok": True, "items": [_raw_item_to_dict(item) for item in items], "count": len(items)}


def risk_raw_item_duplicate_candidates(
    url: str | None = None,
    content_hash: str | None = None,
    source_id: str | None = None,
    title: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Return deterministic duplicate candidates for Hermes review."""
    try:
        payload = DuplicateCandidatesInput(
            url=url,
            content_hash=content_hash,
            source_id=source_id,
            title=title,
            limit=limit,
        )
        with _session_scope() as session:
            matches = list_duplicate_candidates(session, **payload.model_dump())
    except (ValidationError, ValueError) as exc:
        return _error("validation_error", str(exc))
    except Exception as exc:  # noqa: BLE001
        return _error("database_unavailable", str(exc))
    candidates = [
        {"match_type": match.match_type, "item": _raw_item_to_dict(match.item)}
        for match in matches
    ]
    return {"ok": True, "candidates": candidates, "count": len(candidates)}


def risk_source_run_record(source_run: dict[str, Any]) -> dict[str, Any]:
    """Record a Hermes workflow or optional deterministic helper run."""
    try:
        payload = SourceRunCreate.model_validate(source_run)
        with _session_scope() as session:
            run = record_source_run(session, payload)
    except (UnknownRegistrySourceError, ValidationError, ValueError) as exc:
        return _error("validation_error", str(exc))
    except Exception as exc:  # noqa: BLE001
        return _error("database_unavailable", str(exc))
    return {"ok": True, "source_run": _source_run_to_dict(run)}


def risk_signal_store(signal: dict[str, Any]) -> dict[str, Any]:
    """Store a signal Hermes has already judged worth preserving."""
    try:
        payload = SignalStoreInput.model_validate(signal)
        with _session_scope() as session:
            stored = store_signal(session, payload)
    except (ValidationError, ValueError) as exc:
        return _error("validation_error", str(exc))
    except Exception as exc:  # noqa: BLE001
        return _error("database_unavailable", str(exc))

    # Build rich signal body from stored DB data (more reliable than Hermes input)
    stored_dict = signal_to_dict(stored)
    body_parts = []
    if stored_dict.get("what_changed"):
        body_parts.append(f"**什么改变了**: {stored_dict['what_changed']}")
    if stored_dict.get("why_it_matters"):
        body_parts.append(f"**为什么重要**: {stored_dict['why_it_matters']}")
    if stored_dict.get("what_to_watch_next"):
        body_parts.append(f"**接下来关注**: {stored_dict['what_to_watch_next']}")
    if stored_dict.get("summary"):
        body_parts.append(f"**摘要**: {stored_dict['summary']}")
    body_parts.append(
        f"**严重度**: {stored_dict.get('severity', 'N/A')}/5 | "
        f"**置信度**: {stored_dict.get('confidence', 'N/A')}/5"
    )
    if stored_dict.get("risk_domains"):
        body_parts.append(f"**风险域**: {', '.join(stored_dict['risk_domains'])}")
    if stored_dict.get("primary_source_url"):
        body_parts.append(f"**证据URL**: {stored_dict['primary_source_url']}")
    signal_body = "\n\n".join(body_parts)

    # Auto-mirror to live vault (best-effort)
    mirror_info = _auto_mirror_to_live_vault(
        "signal",
        slug=payload.title or "untitled-signal",
        title=payload.title or "Untitled Signal",
        body=signal_body,
        source_id=payload.source_id,
        link_ids={
            "related_evidence_ids": [],
            "related_source_ids": (
                [payload.source_id] if payload.source_id else []
            ),
        },
        risk_domains=payload.risk_domains,
        extra_metadata={
            "severity": stored_dict.get("severity"),
            "confidence": stored_dict.get("confidence"),
            "what_changed": stored_dict.get("what_changed", ""),
            "why_it_matters": stored_dict.get("why_it_matters", ""),
            "what_to_watch_next": stored_dict.get("what_to_watch_next", ""),
        },
    )

    result = {"ok": True, "signal": stored_dict}
    if mirror_info.get("mirrored"):
        result["vault_mirror"] = mirror_info
    return result


def risk_signal_search(
    source_id: str | None = None,
    signal_type: str | None = None,
    risk_domain: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Search stored Hermes-generated signals."""
    try:
        payload = SignalSearchInput(
            source_id=source_id,
            signal_type=signal_type,
            risk_domain=risk_domain,
            limit=limit,
        )
        with _session_scope() as session:
            signals = search_signals(session, **payload.model_dump())
    except (ValidationError, ValueError) as exc:
        return _error("validation_error", str(exc))
    except Exception as exc:  # noqa: BLE001
        return _error("database_unavailable", str(exc))
    return {"ok": True, "signals": [signal_to_dict(signal) for signal in signals]}


def risk_digest_store(digest: dict[str, Any]) -> dict[str, Any]:
    """Store a digest Hermes has already written."""
    try:
        payload = DigestStoreInput.model_validate(digest)
        with _session_scope() as session:
            stored = store_digest(session, payload)
    except (ValidationError, ValueError) as exc:
        return _error("validation_error", str(exc))
    except Exception as exc:  # noqa: BLE001
        return _error("database_unavailable", str(exc))

    # Best-effort Obsidian mirror when live vault enabled
    vault_warnings: list[str] = []
    try:
        from frontier_ai_risk_observer.obsidian.live_writer import LiveVaultConfig

        config = LiveVaultConfig.from_env()
        if config.live_logging_enabled:
            from frontier_ai_risk_observer.obsidian.daily_note import (
                upsert_daily_report_note,
            )

            # Discover signal/evidence note paths from auto-mirror
            signal_note_paths: list[str] = []
            evidence_note_paths: list[str] = []
            candidate_note_paths: list[str] = []
            run_id = _find_active_live_run(config)
            if run_id:
                signals_dir = (
                    config.vault_path / "AI-Risk-Intelligence"
                    / config.runs_dir_name / run_id / "Signals"
                )
                if signals_dir.exists():
                    for f in signals_dir.iterdir():
                        if f.suffix == ".md":
                            rel = f"08_Live_Runs/{run_id}/Signals/{f.stem}"
                            signal_note_paths.append(rel)

                evidence_dir = (
                    config.vault_path / "AI-Risk-Intelligence"
                    / config.runs_dir_name / run_id / "Evidence"
                )
                if evidence_dir.exists():
                    for f in evidence_dir.iterdir():
                        if f.suffix == ".md":
                            rel = f"08_Live_Runs/{run_id}/Evidence/{f.stem}"
                            evidence_note_paths.append(rel)

                candidates_dir = (
                    config.vault_path / "AI-Risk-Intelligence"
                    / config.runs_dir_name / run_id / "Candidates"
                )
                if candidates_dir.exists():
                    for f in candidates_dir.iterdir():
                        if f.suffix == ".md":
                            rel = f"08_Live_Runs/{run_id}/Candidates/{f.stem}"
                            candidate_note_paths.append(rel)

            upsert_daily_report_note(
                config.vault_path,
                report_date=payload.digest_date.isoformat(),
                report_markdown=stored.markdown_full,
                digest_id=str(stored.id),
                status=payload.status,
                run_id=run_id,
                signal_note_paths=signal_note_paths,
                evidence_note_paths=evidence_note_paths,
                candidate_note_paths=candidate_note_paths,
            )
    except Exception as exc:  # noqa: BLE001
        vault_warnings.append(f"Obsidian mirror failed: {exc}")

    result = {"ok": True, "digest": digest_to_dict(stored)}
    if vault_warnings:
        result["vault_warnings"] = vault_warnings
    return result


def risk_digest_search(
    digest_date: str | None = None,
    status: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Search stored Hermes-written digests."""
    try:
        payload = DigestSearchInput.model_validate(
            {"digest_date": digest_date, "status": status, "limit": limit}
        )
        with _session_scope() as session:
            digests = search_digests(session, **payload.model_dump())
    except (ValidationError, ValueError) as exc:
        return _error("validation_error", str(exc))
    except Exception as exc:  # noqa: BLE001
        return _error("database_unavailable", str(exc))
    return {"ok": True, "digests": [digest_to_dict(digest) for digest in digests]}


def risk_benchmark_observation_store(observation: dict[str, Any]) -> dict[str, Any]:
    """Validate benchmark observation input; persistence is deferred past R1-06."""
    try:
        payload = BenchmarkObservationStoreInput.model_validate(observation)
    except ValidationError as exc:
        return _error("validation_error", str(exc))
    return {
        "ok": False,
        "error_type": "not_implemented",
        "message": "Benchmark observation persistence is deferred until its service is added.",
        "benchmark_id": payload.benchmark_id,
    }


def risk_source_health_summary() -> dict[str, Any]:
    """Return source health summary including helper coverage and known issues."""
    from frontier_ai_risk_observer.services.source_health import source_health_summary

    return source_health_summary()


def risk_discovery_helper_preview(
    source_id: str,
    fetch: bool = False,
    limit: int = 10,
) -> dict[str, Any]:
    """Preview candidate items from discovery helpers for a given source.

    Does NOT fetch network by default (fetch=False).
    Does NOT store raw items or call LLMs.
    """

    from frontier_ai_risk_observer.registry.loader import load_registry_bundle
    from frontier_ai_risk_observer.registry.validators import validate_registry_bundle

    bundle = load_registry_bundle()
    validated = validate_registry_bundle(bundle)

    # Find the entry
    entry = None
    for group in (validated.sources, validated.podcasts, validated.events, validated.benchmarks):
        for e in group:
            if e.id == source_id:
                entry = e
                break
        if entry:
            break

    if entry is None:
        return {"ok": False, "error_type": "not_found", "source_id": source_id}

    helper_type = getattr(entry, "helper_type", None)
    if not helper_type or helper_type in ("none", "manual"):
        return {
            "ok": True,
            "source_id": source_id,
            "helper_type": helper_type,
            "candidates": [],
            "message": "No automated helper configured for this source.",
        }

    if not fetch:
        return {
            "ok": True,
            "source_id": source_id,
            "helper_type": helper_type,
            "would_fetch": True,
            "candidates": [],
            "message": "Set fetch=true to run the helper and retrieve candidates.",
        }

    # Fetch mode — run the appropriate helper
    try:
        candidates = _run_helper_for_entry(entry, limit)
        return {
            "ok": True,
            "source_id": source_id,
            "helper_type": helper_type,
            "candidates": [c.model_dump(mode="json") for c in candidates],
            "count": len(candidates),
        }
    except Exception as exc:  # noqa: BLE001
        return _error("helper_error", str(exc))


def _run_helper_for_entry(entry: Any, limit: int) -> list:
    """Run the appropriate helper for a registry entry. Network access required."""

    helper_type = getattr(entry, "helper_type", None)
    source_id = entry.id
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
        return arxiv_fetch(query=query, source_id=source_id, max_results=max_items)
    else:
        return []


def risk_evidence_store(evidence: dict[str, Any]) -> dict[str, Any]:
    """Store an evidence/claim item that Hermes has already extracted."""
    try:
        payload = EvidenceStoreInput.model_validate(evidence)
        with _session_scope() as session:
            from frontier_ai_risk_observer.services.evidence import (
                store_evidence_item,
            )
            stored = store_evidence_item(
                session,
                raw_item_id=payload.raw_item_id,
                signal_id=payload.signal_id,
                source_id=payload.source_id,
                claim_text=payload.claim_text,
                claim_type=payload.claim_type,
                evidence_url=payload.evidence_url,
                evidence_title=payload.evidence_title,
                evidence_excerpt=payload.evidence_excerpt,
                evidence_level=payload.evidence_level,
                confidence=payload.confidence,
                supports_signal=payload.supports_signal,
                risk_domains=payload.risk_domains,
                entities=payload.entities,
                needs_human_review=payload.needs_human_review,
                metadata=payload.metadata,
            )
    except (ValidationError, ValueError) as exc:
        return _error("validation_error", str(exc))
    except Exception as exc:  # noqa: BLE001
        return _error("database_unavailable", str(exc))

    # Auto-mirror to live vault (best-effort)
    from frontier_ai_risk_observer.services.evidence import evidence_to_dict

    stored_dict = evidence_to_dict(stored)
    body_parts = []
    if stored_dict.get("claim_text"):
        body_parts.append(f"**主张**: {stored_dict['claim_text']}")
    if stored_dict.get("claim_type"):
        body_parts.append(f"**类型**: {stored_dict['claim_type']}")
    if stored_dict.get("evidence_url"):
        body_parts.append(f"**证据URL**: {stored_dict['evidence_url']}")
    if stored_dict.get("evidence_excerpt"):
        excerpt = stored_dict["evidence_excerpt"]
        if len(excerpt) > 1000:
            excerpt = excerpt[:1000] + "..."
        body_parts.append(f"**摘录**: {excerpt}")
    conf = stored_dict.get("confidence")
    body_parts.append(f"**置信度**: {conf or 'N/A'}/5")
    if stored_dict.get("supports_signal") is not None:
        body_parts.append(f"**支撑信号**: {'是' if stored_dict['supports_signal'] else '否'}")
    if stored_dict.get("needs_human_review"):
        body_parts.append("**需人工审查**: 是")
    evidence_body = "\n\n".join(body_parts)

    claim_slug = (payload.claim_text or "untitled-evidence")[:60]
    mirror_info = _auto_mirror_to_live_vault(
        "evidence",
        slug=claim_slug,
        title=payload.evidence_title or claim_slug,
        body=evidence_body,
        source_id=payload.source_id,
        link_ids={
            "related_signal_ids": (
                [str(payload.signal_id)] if payload.signal_id else []
            ),
        },
        risk_domains=payload.risk_domains,
        extra_metadata={
            "confidence": payload.confidence,
            "needs_review": payload.needs_human_review,
            "needs_review_reason": (
                "Needs human review" if payload.needs_human_review else ""
            ),
        },
    )

    result = {"ok": True, "evidence": stored_dict}
    if mirror_info.get("mirrored"):
        result["vault_mirror"] = mirror_info
    return result


def risk_evidence_search(
    signal_id: str | None = None,
    raw_item_id: str | None = None,
    source_id: str | None = None,
    claim_type: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Search stored evidence/claim items."""
    try:
        payload = EvidenceSearchInput(
            signal_id=signal_id,
            raw_item_id=raw_item_id,
            source_id=source_id,
            claim_type=claim_type,
            limit=limit,
        )
        with _session_scope() as session:
            from frontier_ai_risk_observer.services.evidence import (
                evidence_to_dict,
                search_evidence_items,
            )
            items = search_evidence_items(
                session, **payload.model_dump(),
            )
    except (ValidationError, ValueError) as exc:
        return _error("validation_error", str(exc))
    except Exception as exc:  # noqa: BLE001
        return _error("database_unavailable", str(exc))
    return {
        "ok": True,
        "evidence": [evidence_to_dict(item) for item in items],
        "count": len(items),
    }


def risk_candidate_preprocess(
    title: str,
    url: str = "",
    content_text: str = "",
    source_id: str = "",
    focus: str = "",
    risk_domain: str = "",
) -> dict[str, Any]:
    """Advisory pre-processing for candidate items.

    May use a small/fast model if configured. Falls back to deterministic
    truncation if disabled. Output is advisory only — does NOT store
    anything, does NOT make final risk judgments.
    """
    try:
        payload = CandidatePreprocessInput(
            title=title,
            url=url,
            content_text=content_text,
            source_id=source_id,
            focus=focus,
            risk_domain=risk_domain,
        )
    except (ValidationError, ValueError) as exc:
        return _error("validation_error", str(exc))

    from frontier_ai_risk_observer.services.candidate_preprocess import preprocess_candidate

    result = preprocess_candidate(
        title=payload.title,
        url=payload.url,
        content_text=payload.content_text,
        source_id=payload.source_id,
        focus=payload.focus,
        risk_domain=payload.risk_domain,
    )
    return {
        "ok": True,
        "short_summary": result.short_summary,
        "evidence_excerpt": result.evidence_excerpt,
        "possible_risk_domains": result.possible_risk_domains,
        "advisory_relevance": result.advisory_relevance,
        "advisory_confidence": result.advisory_confidence,
        "notes": result.notes,
        "model_used": result.model_used,
        "advisory_only": result.advisory_only,
    }


# ---------------------------------------------------------------------------
# R1-13: Live Obsidian Research Logging
# ---------------------------------------------------------------------------


def risk_live_run_start(
    run_id: str | None = None,
    title: str = "",
) -> dict[str, Any]:
    """Start a live Obsidian research run.

    Creates the live run directory and initial notes in the Obsidian vault.
    If live logging is disabled, returns ok with live_logging_enabled=false.
    """
    try:
        payload = LiveRunStartInput(run_id=run_id, title=title)
    except ValidationError as exc:
        return _error("validation_error", str(exc))

    # Generate run_id if not provided
    from datetime import UTC, datetime

    actual_run_id = payload.run_id or datetime.now(UTC).strftime("%Y-%m-%d_%H%M%S")

    # Store research event in DB
    try:
        with _session_scope() as session:
            from frontier_ai_risk_observer.services.live_research import (
                store_research_event,
            )

            stored = store_research_event(
                session,
                run_id=actual_run_id,
                event_type="run_started",
                title=payload.title or actual_run_id,
            )
            event_id = str(stored.id)
    except (ValidationError, ValueError) as exc:
        return _error("validation_error", str(exc))
    except Exception as exc:
        return _error("database_unavailable", str(exc))

    # Write to Obsidian vault if live logging enabled
    live_logging_enabled = False
    vault_errors: list[str] = []
    try:
        from frontier_ai_risk_observer.obsidian.live_writer import LiveVaultConfig

        config = LiveVaultConfig.from_env()
        live_logging_enabled = config.live_logging_enabled
        if live_logging_enabled:
            from frontier_ai_risk_observer.obsidian.live_writer import LiveVaultWriter

            writer = LiveVaultWriter(config)
            result = writer.start_run(actual_run_id, title=payload.title)
            vault_errors = result.errors
    except ValueError as exc:
        vault_errors.append(str(exc))
    except Exception as exc:
        vault_errors.append(str(exc))

    return {
        "ok": True,
        "run_id": actual_run_id,
        "event_id": event_id,
        "live_logging_enabled": live_logging_enabled,
        "vault_errors": vault_errors,
    }


def risk_live_event_append(
    run_id: str,
    event_type: str,
    title: str = "",
    body: str | None = None,
    source_id: str | None = None,
    raw_item_id: str | None = None,
    signal_id: str | None = None,
    evidence_id: str | None = None,
    note_vault_path: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append a structured event to the live research log and timeline."""
    try:
        payload = LiveEventAppendInput(
            run_id=run_id,
            event_type=event_type,
            title=title,
            body=body,
            source_id=source_id,
            raw_item_id=raw_item_id,
            signal_id=signal_id,
            evidence_id=evidence_id,
            note_vault_path=note_vault_path,
            metadata=metadata or {},
        )
    except ValidationError as exc:
        return _error("validation_error", str(exc))

    # Store research event in DB
    try:
        with _session_scope() as session:
            from frontier_ai_risk_observer.services.live_research import (
                store_research_event,
            )

            stored = store_research_event(
                session,
                run_id=payload.run_id,
                event_type=payload.event_type,
                title=payload.title,
                body=payload.body,
                source_id=payload.source_id,
                raw_item_id=payload.raw_item_id,
                signal_id=payload.signal_id,
                evidence_id=payload.evidence_id,
                metadata=payload.metadata,
            )
            event_id = str(stored.id)
    except (ValidationError, ValueError) as exc:
        return _error("validation_error", str(exc))
    except Exception as exc:
        return _error("database_unavailable", str(exc))

    # Write to Obsidian vault if live logging enabled
    live_logging_enabled = False
    vault_errors: list[str] = []
    try:
        from frontier_ai_risk_observer.obsidian.live_writer import (
            LiveEvent,
            LiveVaultConfig,
            LiveVaultWriter,
        )

        config = LiveVaultConfig.from_env()
        live_logging_enabled = config.live_logging_enabled
        if live_logging_enabled:
            writer = LiveVaultWriter(config)
            event = LiveEvent(
                event_type=payload.event_type,
                title=payload.title,
                body=payload.body,
                source_id=payload.source_id,
                raw_item_id=payload.raw_item_id,
                signal_id=payload.signal_id,
                evidence_id=payload.evidence_id,
                metadata=payload.metadata,
                note_vault_path=payload.note_vault_path,
            )
            result = writer.append_event(payload.run_id, event)
            vault_errors = result.errors
    except ValueError as exc:
        vault_errors.append(str(exc))
    except Exception as exc:
        vault_errors.append(str(exc))

    return {
        "ok": True,
        "event_id": event_id,
        "live_logging_enabled": live_logging_enabled,
        "note_vault_path": payload.note_vault_path,
        "vault_errors": vault_errors,
    }


def risk_live_note_upsert(
    run_id: str,
    note_type: Literal["source", "candidate", "evidence", "signal", "failure"],
    slug: str,
    title: str,
    body: str,
    source_id: str | None = None,
    daily_report_date: str | None = None,
    related_signal_ids: list[str] | None = None,
    related_evidence_ids: list[str] | None = None,
    related_candidate_ids: list[str] | None = None,
    related_source_ids: list[str] | None = None,
    risk_domains: list[str] | None = None,
    confidence: int | None = None,
    severity: int | None = None,
    needs_review: bool = False,
    needs_review_reason: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Upsert a live note (source/candidate/evidence/signal) in the research vault."""
    try:
        payload = LiveNoteUpsertInput(
            run_id=run_id,
            note_type=note_type,
            slug=slug,
            title=title,
            body=body,
            source_id=source_id,
            daily_report_date=daily_report_date,
            related_signal_ids=related_signal_ids or [],
            related_evidence_ids=related_evidence_ids or [],
            related_candidate_ids=related_candidate_ids or [],
            related_source_ids=related_source_ids or [],
            risk_domains=risk_domains or [],
            confidence=confidence,
            severity=severity,
            needs_review=needs_review,
            needs_review_reason=needs_review_reason,
            metadata=metadata or {},
        )
    except ValidationError as exc:
        return _error("validation_error", str(exc))

    # note_type is validated by Pydantic Literal in the schema

    # Store research event in DB
    try:
        with _session_scope() as session:
            from frontier_ai_risk_observer.services.live_research import (
                store_research_event,
            )

            stored = store_research_event(
                session,
                run_id=payload.run_id,
                event_type=f"{payload.note_type}_note_upserted",
                title=payload.title,
                source_id=payload.source_id,
                metadata=payload.metadata,
            )
            event_id = str(stored.id)
    except (ValidationError, ValueError) as exc:
        return _error("validation_error", str(exc))
    except Exception as exc:
        return _error("database_unavailable", str(exc))

    # Write to Obsidian vault if live logging enabled
    live_logging_enabled = False
    vault_errors: list[str] = []
    notes_written = 0
    note_vault_path: str | None = None
    try:
        from frontier_ai_risk_observer.obsidian.live_writer import LiveVaultConfig, LiveVaultWriter

        config = LiveVaultConfig.from_env()
        live_logging_enabled = config.live_logging_enabled
        if live_logging_enabled:
            writer = LiveVaultWriter(config)
            link_info = {
                "daily_report_date": payload.daily_report_date,
                "related_signal_ids": payload.related_signal_ids,
                "related_evidence_ids": payload.related_evidence_ids,
                "related_candidate_ids": payload.related_candidate_ids,
                "related_source_ids": payload.related_source_ids,
                "risk_domains": payload.risk_domains,
                "confidence": payload.confidence,
                "severity": payload.severity,
                "needs_review": payload.needs_review,
                "needs_review_reason": payload.needs_review_reason,
            }
            if payload.note_type == "failure":
                result = writer.record_failure(
                    payload.run_id,
                    source_id=payload.slug,
                    failure_type="failure",
                    message=payload.body,
                    metadata={**payload.metadata, **link_info},
                )
            else:
                method_map = {
                    "source": writer.upsert_source_note,
                    "candidate": writer.upsert_candidate_note,
                    "evidence": writer.upsert_evidence_note,
                    "signal": writer.upsert_signal_note,
                }
                method = method_map[payload.note_type]
                result = method(
                    payload.run_id,
                    payload.slug,
                    title=payload.title,
                    body=payload.body,
                    metadata={**payload.metadata, **link_info},
                )
            notes_written = result.notes_written + result.notes_updated
            vault_errors = result.errors

            # Compute the vault-relative path for the created note
            from frontier_ai_risk_observer.obsidian.links import note_vault_relative_path

            subdir_map = {
                "source": "Sources",
                "candidate": "Candidates",
                "evidence": "Evidence",
                "signal": "Signals",
            }
            if payload.note_type in subdir_map:
                from frontier_ai_risk_observer.obsidian.markdown import slugify_filename

                subdir = subdir_map[payload.note_type]
                note_path = (
                    config.vault_path / "AI-Risk-Intelligence"
                    / config.runs_dir_name / payload.run_id
                    / subdir / f"{slugify_filename(payload.slug)}.md"
                )
                note_vault_path = note_vault_relative_path(config.vault_path, note_path)
    except ValueError as exc:
        vault_errors.append(str(exc))
    except Exception as exc:
        vault_errors.append(str(exc))

    return {
        "ok": True,
        "event_id": event_id,
        "note_type": payload.note_type,
        "slug": payload.slug,
        "notes_written": notes_written,
        "live_logging_enabled": live_logging_enabled,
        "note_vault_path": note_vault_path,
        "vault_errors": vault_errors,
    }


def risk_live_run_finalize(
    run_id: str,
    summary: dict[str, Any] | None = None,
    final_report_markdown: str | None = None,
    digest_id: str | None = None,
    daily_report_date: str | None = None,
    quality_score: int | None = None,
    signal_note_paths: list[str] | None = None,
    candidate_note_paths: list[str] | None = None,
    evidence_note_paths: list[str] | None = None,
    source_note_paths: list[str] | None = None,
    failure_note_paths: list[str] | None = None,
) -> dict[str, Any]:
    """Finalize a live Obsidian research run."""
    try:
        payload = LiveRunFinalizeInput(
            run_id=run_id,
            summary=summary or {},
            final_report_markdown=final_report_markdown,
            digest_id=digest_id,
            daily_report_date=daily_report_date,
            quality_score=quality_score,
            signal_note_paths=signal_note_paths or [],
            candidate_note_paths=candidate_note_paths or [],
            evidence_note_paths=evidence_note_paths or [],
            source_note_paths=source_note_paths or [],
            failure_note_paths=failure_note_paths or [],
        )
    except ValidationError as exc:
        return _error("validation_error", str(exc))

    # Store research event in DB
    try:
        with _session_scope() as session:
            from frontier_ai_risk_observer.services.live_research import (
                store_research_event,
            )

            stored = store_research_event(
                session,
                run_id=payload.run_id,
                event_type="run_finalized",
                title="Run finalized",
                metadata=payload.summary,
            )
            event_id = str(stored.id)
    except (ValidationError, ValueError) as exc:
        return _error("validation_error", str(exc))
    except Exception as exc:
        return _error("database_unavailable", str(exc))

    # Finalize Obsidian vault if live logging enabled
    live_logging_enabled = False
    vault_errors: list[str] = []
    daily_note_path: str | None = None
    linked_notes_summary: dict[str, int] = {}
    try:
        from frontier_ai_risk_observer.obsidian.live_writer import LiveVaultConfig, LiveVaultWriter

        config = LiveVaultConfig.from_env()
        live_logging_enabled = config.live_logging_enabled
        if live_logging_enabled:
            writer = LiveVaultWriter(config)
            result = writer.finalize_run(
                payload.run_id,
                summary=payload.summary,
                final_report_markdown=payload.final_report_markdown,
                digest_id=payload.digest_id,
                daily_report_date=payload.daily_report_date,
                quality_score=payload.quality_score,
                signal_note_paths=payload.signal_note_paths,
                candidate_note_paths=payload.candidate_note_paths,
                evidence_note_paths=payload.evidence_note_paths,
                source_note_paths=payload.source_note_paths,
                failure_note_paths=payload.failure_note_paths,
            )
            vault_errors = result.errors

            # If daily report was written, compute its path
            if payload.daily_report_date:
                daily_note_path = (
                    f"00_Daily/{payload.daily_report_date}.md"
                )
                linked_notes_summary = {
                    "signals": len(payload.signal_note_paths),
                    "candidates": len(payload.candidate_note_paths),
                    "evidence": len(payload.evidence_note_paths),
                    "sources": len(payload.source_note_paths),
                    "failures": len(payload.failure_note_paths),
                }
    except ValueError as exc:
        vault_errors.append(str(exc))
    except Exception as exc:
        vault_errors.append(str(exc))

    return {
        "ok": True,
        "run_id": payload.run_id,
        "event_id": event_id,
        "live_logging_enabled": live_logging_enabled,
        "daily_note_path": daily_note_path,
        "linked_notes_summary": linked_notes_summary,
        "vault_errors": vault_errors,
    }


def risk_live_daily_report_upsert(
    report_date: str,
    title: str = "",
    report_markdown: str = "",
    digest_id: str | None = None,
    run_id: str | None = None,
    status: str = "draft",
    summary: dict[str, Any] | None = None,
    signal_note_paths: list[str] | None = None,
    candidate_note_paths: list[str] | None = None,
    evidence_note_paths: list[str] | None = None,
    source_note_paths: list[str] | None = None,
    failure_note_paths: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write or update the final daily report note in the Obsidian vault.

    When live vault logging is enabled, writes the full report to
    ``00_Daily/YYYY-MM-DD.md`` immediately. This is the primary tool
    for ensuring the daily report is visible in Obsidian without
    requiring ``make obsidian-export``.
    """
    try:
        payload = LiveDailyReportUpsertInput(
            report_date=report_date,
            title=title,
            report_markdown=report_markdown,
            digest_id=digest_id,
            run_id=run_id,
            status=status,
            summary=summary or {},
            signal_note_paths=signal_note_paths or [],
            candidate_note_paths=candidate_note_paths or [],
            evidence_note_paths=evidence_note_paths or [],
            source_note_paths=source_note_paths or [],
            failure_note_paths=failure_note_paths or [],
            metadata=metadata or {},
        )
    except ValidationError as exc:
        return _error("validation_error", str(exc))

    # Store research event in DB
    try:
        with _session_scope() as session:
            from frontier_ai_risk_observer.services.live_research import (
                store_research_event,
            )

            stored = store_research_event(
                session,
                run_id=payload.run_id or "daily_report",
                event_type="digest_stored",
                title=payload.title or f"Daily Report {payload.report_date}",
                metadata=payload.summary,
            )
            event_id = str(stored.id)
    except (ValidationError, ValueError) as exc:
        return _error("validation_error", str(exc))
    except Exception as exc:
        return _error("database_unavailable", str(exc))

    # Write to Obsidian vault if live logging enabled
    live_logging_enabled = False
    vault_errors: list[str] = []
    daily_note_path: str | None = None
    live_run_path: str | None = None
    linked_notes_count = 0

    try:
        from frontier_ai_risk_observer.obsidian.live_writer import LiveVaultConfig

        config = LiveVaultConfig.from_env()
        live_logging_enabled = config.live_logging_enabled
        if live_logging_enabled:
            from frontier_ai_risk_observer.obsidian.daily_note import (
                upsert_daily_report_note,
            )

            write_result = upsert_daily_report_note(
                config.vault_path,
                report_date=payload.report_date,
                report_markdown=payload.report_markdown,
                digest_id=payload.digest_id,
                run_id=payload.run_id,
                status=payload.status,
                signal_note_paths=payload.signal_note_paths,
                candidate_note_paths=payload.candidate_note_paths,
                evidence_note_paths=payload.evidence_note_paths,
                source_note_paths=payload.source_note_paths,
                failure_note_paths=payload.failure_note_paths,
                metadata=payload.metadata,
            )
            daily_note_path = str(write_result.path)
            linked_notes_count = (
                len(payload.signal_note_paths)
                + len(payload.candidate_note_paths)
                + len(payload.evidence_note_paths)
                + len(payload.source_note_paths)
                + len(payload.failure_note_paths)
            )
            if payload.run_id:
                live_run_path = (
                    f"08_Live_Runs/{payload.run_id}/Live Research Log"
                )
    except ValueError as exc:
        vault_errors.append(str(exc))
    except Exception as exc:
        vault_errors.append(str(exc))

    return {
        "ok": True,
        "event_id": event_id,
        "daily_note_path": daily_note_path,
        "live_run_path": live_run_path,
        "linked_notes_count": linked_notes_count,
        "live_logging_enabled": live_logging_enabled,
        "warnings": vault_errors,
    }


def register_tools() -> None:
    """Register tool functions with FastMCP when the optional SDK is installed."""
    if mcp is None:
        return
    for tool in MCP_TOOL_FUNCTIONS:
        mcp.tool()(tool)


@contextmanager
def _session_scope() -> Iterator[Session]:
    factory = _session_factory_override or create_session_factory()
    with factory() as session:
        yield session


def _registry_kind(kind: str | None) -> registry_service.RegistryKind | None:
    if kind is None:
        return None
    if kind not in {"source", "podcast", "event", "benchmark"}:
        msg = f"Unknown registry kind: {kind}"
        raise ValueError(msg)
    return kind  # type: ignore[return-value]


def _raw_item_to_dict(item: RawItem) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "source_id": item.source_id,
        "modality": item.modality,
        "url": item.url,
        "canonical_url": item.canonical_url,
        "normalized_title": item.normalized_title,
        "title": item.title,
        "published_at": _iso(item.published_at),
        "fetched_at": item.fetched_at.isoformat(),
        "content_text": item.content_text,
        "content_hash": item.content_hash,
        "dedup_key": item.dedup_key,
        "metadata": item.metadata_,
        "status": item.status,
        "ingestion_status": item.ingestion_status,
        "first_seen_at": item.first_seen_at.isoformat(),
        "last_seen_at": item.last_seen_at.isoformat(),
        "seen_count": item.seen_count,
        "created_at": item.created_at.isoformat(),
    }


def _source_run_to_dict(run: SourceRun) -> dict[str, Any]:
    return {
        "id": str(run.id),
        "source_id": run.source_id,
        "source_type": run.source_type,
        "status": run.status,
        "started_at": _iso(run.started_at),
        "finished_at": _iso(run.finished_at),
        "items_found": run.items_found,
        "items_new": run.items_new,
        "items_duplicate": run.items_duplicate,
        "items_error": run.items_error,
        "error_message": run.error_message,
        "metadata": run.metadata_,
        "created_at": run.created_at.isoformat(),
    }


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def _find_active_live_run(config: Any) -> str | None:
    """Find the most recent active (non-finalized) live run in the vault.

    Scans the live runs directory for run directories that haven't been
    finalized yet (status: in_progress in frontmatter).
    """
    runs_dir = config.vault_path / "AI-Risk-Intelligence" / config.runs_dir_name
    if not runs_dir.exists():
        return None

    candidates: list[tuple[str, str]] = []  # (run_id, path)
    for entry in sorted(runs_dir.iterdir(), reverse=True):
        if not entry.is_dir():
            continue
        log_path = entry / "Live Research Log.md"
        if not log_path.exists():
            continue
        content = log_path.read_text(encoding="utf-8")
        # Only consider runs that are still in_progress
        if "status: in_progress" in content or "status: completed" in content:
            candidates.append((entry.name, content))

    # Prefer in_progress runs; fall back to most recent completed run
    for run_id, _ in candidates:
        if "status: in_progress" in _:
            return run_id
    # Return most recent completed run if within today
    if candidates:
        from datetime import UTC, datetime

        today = datetime.now(UTC).strftime("%Y-%m-%d")
        for run_id, _ in candidates:
            if run_id.startswith(today):
                return run_id
    return None


def _auto_mirror_to_live_vault(
    note_type: str,
    slug: str,
    title: str,
    body: str,
    *,
    source_id: str | None = None,
    link_ids: dict[str, list[str]] | None = None,
    risk_domains: list[str] | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Best-effort auto-mirror a signal/evidence/candidate note to live vault.

    Called from risk_signal_store, risk_evidence_store, and risk_raw_item_store
    to automatically create live notes even if Hermes doesn't explicitly call
    risk_live_note_upsert. Also appends events to the live research log/timeline.
    Returns info about what was mirrored.
    """
    mirror_info: dict[str, Any] = {
        "mirrored": False,
        "run_id": None,
        "note_path": None,
        "error": None,
    }
    try:
        from frontier_ai_risk_observer.obsidian.live_writer import (
            LiveVaultConfig,
            LiveVaultWriter,
        )

        config = LiveVaultConfig.from_env()
        if not config.live_logging_enabled:
            return mirror_info

        run_id = _find_active_live_run(config)
        if not run_id:
            return mirror_info

        mirror_info["run_id"] = run_id
        writer = LiveVaultWriter(config)

        metadata: dict[str, Any] = {"auto_mirrored": True}
        if source_id:
            metadata["source_id"] = source_id
        if link_ids:
            metadata.update(link_ids)
        if risk_domains:
            metadata["risk_domains"] = risk_domains
        if extra_metadata:
            metadata.update(extra_metadata)

        # Get today's date for daily_report_date in links
        from datetime import UTC, datetime

        today = datetime.now(UTC).strftime("%Y-%m-%d")
        metadata["daily_report_date"] = today

        # Compute note vault path for timeline wikilink
        from frontier_ai_risk_observer.obsidian.markdown import slugify_filename

        subdir_map = {
            "signal": "Signals",
            "evidence": "Evidence",
            "candidate": "Candidates",
            "source": "Sources",
        }
        subdir = subdir_map.get(note_type, "Candidates")
        safe_slug = slugify_filename(slug)
        note_vault_path = f"08_Live_Runs/{run_id}/{subdir}/{safe_slug}"

        method_map = {
            "signal": writer.upsert_signal_note,
            "evidence": writer.upsert_evidence_note,
            "candidate": writer.upsert_candidate_note,
            "source": writer.upsert_source_note,
        }
        method = method_map.get(note_type)
        if method:
            result = method(run_id, slug, title=title, body=body, metadata=metadata)
            if result.success:
                mirror_info["mirrored"] = True
                from frontier_ai_risk_observer.obsidian.links import note_vault_relative_path

                note_path = (
                    config.vault_path / "AI-Risk-Intelligence"
                    / config.runs_dir_name / run_id
                    / subdir / f"{safe_slug}.md"
                )
                mirror_info["note_path"] = note_vault_relative_path(
                    config.vault_path, note_path,
                )

                # Auto-append event to live research log + timeline
                event_type_map = {
                    "signal": "signal_stored",
                    "evidence": "evidence_stored",
                    "candidate": "candidate_stored",
                    "source": "source_checked",
                }
                from frontier_ai_risk_observer.obsidian.live_writer import LiveEvent

                event = LiveEvent(
                    event_type=event_type_map.get(note_type, "note"),
                    title=title,
                    body=body[:500] if body else None,
                    source_id=source_id,
                    note_vault_path=note_vault_path,
                )
                writer.append_event(run_id, event)
    except Exception as exc:  # noqa: BLE001
        mirror_info["error"] = str(exc)

    return mirror_info


def _error(error_type: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error_type": error_type, "message": message}


MCP_TOOL_FUNCTIONS = [
    risk_registry_summary,
    risk_registry_list_due_sources,
    risk_registry_get_source,
    risk_raw_item_seen_check,
    risk_raw_item_store,
    risk_raw_item_search,
    risk_raw_item_duplicate_candidates,
    risk_source_run_record,
    risk_signal_store,
    risk_signal_search,
    risk_digest_store,
    risk_digest_search,
    risk_benchmark_observation_store,
    risk_source_health_summary,
    risk_discovery_helper_preview,
    risk_candidate_preprocess,
    risk_evidence_store,
    risk_evidence_search,
    risk_live_run_start,
    risk_live_event_append,
    risk_live_note_upsert,
    risk_live_run_finalize,
    risk_live_daily_report_upsert,
]


register_tools()


if __name__ == "__main__":
    if mcp is None:
        raise RuntimeError(
            "Python MCP SDK is not installed. Install the optional MCP runtime "
            "before launching this module from Hermes."
        )
    mcp.run()
