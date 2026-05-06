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
    return {
        "ok": True,
        "item": _raw_item_to_dict(result.item),
        "is_duplicate": result.is_duplicate,
        "match_type": result.match_type,
    }


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
    return {"ok": True, "signal": signal_to_dict(stored)}


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
    return {"ok": True, "digest": digest_to_dict(stored)}


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
    from frontier_ai_risk_observer.services.evidence import evidence_to_dict
    return {"ok": True, "evidence": evidence_to_dict(stored)}


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
        "vault_errors": vault_errors,
    }


def risk_live_note_upsert(
    run_id: str,
    note_type: Literal["source", "candidate", "evidence", "signal", "failure"],
    slug: str,
    title: str,
    body: str,
    source_id: str | None = None,
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
    try:
        from frontier_ai_risk_observer.obsidian.live_writer import LiveVaultConfig, LiveVaultWriter

        config = LiveVaultConfig.from_env()
        live_logging_enabled = config.live_logging_enabled
        if live_logging_enabled:
            writer = LiveVaultWriter(config)
            if payload.note_type == "failure":
                result = writer.record_failure(
                    payload.run_id,
                    source_id=payload.slug,
                    failure_type="failure",
                    message=payload.body,
                    metadata=payload.metadata,
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
                    metadata=payload.metadata,
                )
            notes_written = result.notes_written + result.notes_updated
            vault_errors = result.errors
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
        "vault_errors": vault_errors,
    }


def risk_live_run_finalize(
    run_id: str,
    summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Finalize a live Obsidian research run."""
    try:
        payload = LiveRunFinalizeInput(run_id=run_id, summary=summary or {})
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
    try:
        from frontier_ai_risk_observer.obsidian.live_writer import LiveVaultConfig, LiveVaultWriter

        config = LiveVaultConfig.from_env()
        live_logging_enabled = config.live_logging_enabled
        if live_logging_enabled:
            writer = LiveVaultWriter(config)
            result = writer.finalize_run(payload.run_id, summary=payload.summary)
            vault_errors = result.errors
    except ValueError as exc:
        vault_errors.append(str(exc))
    except Exception as exc:
        vault_errors.append(str(exc))

    return {
        "ok": True,
        "run_id": payload.run_id,
        "event_id": event_id,
        "live_logging_enabled": live_logging_enabled,
        "vault_errors": vault_errors,
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
]


register_tools()


if __name__ == "__main__":
    if mcp is None:
        raise RuntimeError(
            "Python MCP SDK is not installed. Install the optional MCP runtime "
            "before launching this module from Hermes."
        )
    mcp.run()
