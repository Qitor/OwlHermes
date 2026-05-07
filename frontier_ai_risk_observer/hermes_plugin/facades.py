# type: ignore[attr-defined,type-arg,no-untyped-def,no-untyped-call]
"""High-level facade functions for OwlHermes plugin tools.

Each facade function corresponds to one of the 5 plugin tools and dispatches
actions to existing backend services. Returns JSON-compatible dicts.
Does not duplicate business logic — delegates to:
  - services/ingestion (raw items, source runs, seen-check, dedup)
  - services/signals (store, search)
  - services/evidence (store, search)
  - services/digest (store, search)
  - services/registry_service (source registry queries)
  - services/source_health (health summary)
  - services/live_research (research events)
  - obsidian/live_writer (live vault writes)
  - obsidian/exporter (full vault export)
  - quality/report_quality (quality checks)
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Session helper
# ---------------------------------------------------------------------------

def _get_session() -> Any:
    """Create a new DB session from environment configuration."""
    from frontier_ai_risk_observer.db.session import create_db_engine, create_session_factory

    db_url = os.getenv("DATABASE_URL", "sqlite:///./.local/risk_observer_dryrun.db")
    engine = create_db_engine(db_url)
    factory = create_session_factory(engine)
    return factory()


def _error(error_type: str, message: str) -> dict[str, Any]:
    """Return a standardized error dict."""
    return {"ok": False, "error": error_type, "message": message}


def _ok(**kwargs: Any) -> dict[str, Any]:
    """Return a standardized success dict."""
    return {"ok": True, **kwargs}


# ---------------------------------------------------------------------------
# owl_risk_state — Deterministic state operations
# ---------------------------------------------------------------------------

_RISK_STATE_ACTIONS = frozenset({
    "seen_check", "store_raw_item", "search_raw_items",
    "duplicate_candidates", "record_source_run",
    "store_evidence", "search_evidence",
    "store_signal", "search_signals",
    "store_digest", "search_digests",
})


def owl_risk_state(action: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Handle owl_risk_state actions."""
    if action not in _RISK_STATE_ACTIONS:
        return _error(
            "invalid_action",
            f"Unknown action: {action}. "
            f"Allowed: {sorted(_RISK_STATE_ACTIONS)}",
        )
    payload = payload or {}

    try:
        if action == "seen_check":
            return _risk_state_seen_check(payload)
        if action == "store_raw_item":
            return _risk_state_store_raw_item(payload)
        if action == "search_raw_items":
            return _risk_state_search_raw_items(payload)
        if action == "duplicate_candidates":
            return _risk_state_duplicate_candidates(payload)
        if action == "record_source_run":
            return _risk_state_record_source_run(payload)
        if action == "store_evidence":
            return _risk_state_store_evidence(payload)
        if action == "search_evidence":
            return _risk_state_search_evidence(payload)
        if action == "store_signal":
            return _risk_state_store_signal(payload)
        if action == "search_signals":
            return _risk_state_search_signals(payload)
        if action == "store_digest":
            return _risk_state_store_digest(payload)
        if action == "search_digests":
            return _risk_state_search_digests(payload)
    except Exception as exc:
        return _error("internal_error", str(exc))

    return _error("unhandled_action", action)  # pragma: no cover


def _risk_state_seen_check(payload: dict) -> dict[str, Any]:
    from frontier_ai_risk_observer.services.ingestion import seen_raw_item
    session = _get_session()
    try:
        match = seen_raw_item(
            session,
            url=payload.get("url"),
            content_hash=payload.get("content_hash"),
            source_id=payload.get("source_id"),
            title=payload.get("title"),
        )
        if match is None:
            return _ok(seen=False)
        return _ok(seen=True, match_type=match.match_type, dedup_key=match.dedup_key)
    finally:
        session.close()


def _risk_state_store_raw_item(payload: dict) -> dict[str, Any]:
    from frontier_ai_risk_observer.api.schemas import RawItemCreate
    from frontier_ai_risk_observer.services.ingestion import create_raw_item
    session = _get_session()
    try:
        raw_create = RawItemCreate.model_validate(payload)
        result = create_raw_item(session, raw_create)
        return _ok(
            item=_raw_item_to_dict(result.item),
            is_duplicate=result.is_duplicate,
            match_type=result.match_type,
        )
    except Exception as exc:
        return _error("validation_error", str(exc))
    finally:
        session.close()


def _risk_state_search_raw_items(payload: dict) -> dict[str, Any]:
    from frontier_ai_risk_observer.services.ingestion import list_raw_items
    session = _get_session()
    try:
        items = list_raw_items(
            session,
            source_id=payload.get("source_id"),
            url=payload.get("url"),
            canonical_url=payload.get("canonical_url"),
            content_hash=payload.get("content_hash"),
            dedup_key=payload.get("dedup_key"),
            limit=payload.get("limit", 50),
        )
        return _ok(items=[_raw_item_to_dict(i) for i in items], count=len(items))
    finally:
        session.close()


def _risk_state_duplicate_candidates(payload: dict) -> dict[str, Any]:
    from frontier_ai_risk_observer.services.ingestion import list_duplicate_candidates
    session = _get_session()
    try:
        matches = list_duplicate_candidates(
            session,
            url=payload.get("url"),
            content_hash=payload.get("content_hash"),
            source_id=payload.get("source_id"),
            title=payload.get("title"),
            limit=payload.get("limit", 20),
        )
        return _ok(
            candidates=[
                {"item": _raw_item_to_dict(m.item), "match_type": m.match_type}
                for m in matches
            ],
            count=len(matches),
        )
    finally:
        session.close()


def _risk_state_record_source_run(payload: dict) -> dict[str, Any]:
    from frontier_ai_risk_observer.api.schemas import SourceRunCreate
    from frontier_ai_risk_observer.services.ingestion import record_source_run
    session = _get_session()
    try:
        run_create = SourceRunCreate.model_validate(payload)
        run = record_source_run(session, run_create)
        return _ok(run=_source_run_to_dict(run))
    except Exception as exc:
        return _error("validation_error", str(exc))
    finally:
        session.close()


def _risk_state_store_evidence(payload: dict) -> dict[str, Any]:
    from frontier_ai_risk_observer.services.evidence import evidence_to_dict, store_evidence_item
    session = _get_session()
    try:
        claim = store_evidence_item(session, **payload)
        return _ok(evidence=evidence_to_dict(claim))
    except Exception as exc:
        return _error("validation_error", str(exc))
    finally:
        session.close()


def _risk_state_search_evidence(payload: dict) -> dict[str, Any]:
    from frontier_ai_risk_observer.services.evidence import evidence_to_dict, search_evidence_items
    session = _get_session()
    try:
        items = search_evidence_items(
            session,
            signal_id=payload.get("signal_id"),
            raw_item_id=payload.get("raw_item_id"),
            source_id=payload.get("source_id"),
            claim_type=payload.get("claim_type"),
            limit=payload.get("limit", 50),
        )
        return _ok(items=[evidence_to_dict(i) for i in items], count=len(items))
    finally:
        session.close()


def _risk_state_store_signal(payload: dict) -> dict[str, Any]:
    from frontier_ai_risk_observer.mcp.schemas import SignalStoreInput
    from frontier_ai_risk_observer.services.signals import signal_to_dict, store_signal
    session = _get_session()
    try:
        signal_input = SignalStoreInput.model_validate(payload)
        signal = store_signal(session, signal_input)
        return _ok(signal=signal_to_dict(signal))
    except Exception as exc:
        return _error("validation_error", str(exc))
    finally:
        session.close()


def _risk_state_search_signals(payload: dict) -> dict[str, Any]:
    from frontier_ai_risk_observer.services.signals import search_signals, signal_to_dict
    session = _get_session()
    try:
        signals = search_signals(
            session,
            source_id=payload.get("source_id"),
            signal_type=payload.get("signal_type"),
            risk_domain=payload.get("risk_domain"),
            limit=payload.get("limit", 50),
        )
        return _ok(signals=[signal_to_dict(s) for s in signals], count=len(signals))
    finally:
        session.close()


def _risk_state_store_digest(payload: dict) -> dict[str, Any]:
    from frontier_ai_risk_observer.mcp.schemas import DigestStoreInput
    from frontier_ai_risk_observer.services.digest import digest_to_dict, store_digest
    session = _get_session()
    try:
        digest_input = DigestStoreInput.model_validate(payload)
        digest = store_digest(session, digest_input)
        return _ok(digest=digest_to_dict(digest))
    except Exception as exc:
        return _error("validation_error", str(exc))
    finally:
        session.close()


def _risk_state_search_digests(payload: dict) -> dict[str, Any]:
    from frontier_ai_risk_observer.services.digest import digest_to_dict, search_digests
    session = _get_session()
    try:
        digests = search_digests(
            session,
            digest_date=payload.get("digest_date"),
            status=payload.get("status"),
            limit=payload.get("limit", 20),
        )
        return _ok(digests=[digest_to_dict(d) for d in digests], count=len(digests))
    finally:
        session.close()


# ---------------------------------------------------------------------------
# owl_risk_discovery — Source registry and discovery
# ---------------------------------------------------------------------------

_DISCOVERY_ACTIONS = frozenset({
    "registry_summary", "list_due_sources", "get_source",
    "source_health", "helper_preview",
    "feed_preview", "sitemap_preview", "source_policy_summary",
})


def owl_risk_discovery(action: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Handle owl_risk_discovery actions."""
    if action not in _DISCOVERY_ACTIONS:
        return _error(
            "invalid_action",
            f"Unknown action: {action}. "
            f"Allowed: {sorted(_DISCOVERY_ACTIONS)}",
        )
    payload = payload or {}

    try:
        if action == "registry_summary":
            from frontier_ai_risk_observer.services.registry_service import registry_summary
            return _ok(summary=registry_summary())
        if action == "list_due_sources":
            from frontier_ai_risk_observer.services.registry_service import list_due_sources
            sources = list_due_sources(
                limit=payload.get("limit"),
                kind=payload.get("kind"),
                risk_domain=payload.get("risk_domain"),
            )
            return _ok(sources=sources, count=len(sources))
        if action == "get_source":
            from frontier_ai_risk_observer.services.registry_service import get_source
            source = get_source(payload.get("source_id", ""))
            if source is None:
                return _error("not_found", f"Source not found: {payload.get('source_id')}")
            return _ok(source=source)
        if action == "source_health":
            from frontier_ai_risk_observer.services.source_health import source_health_summary
            return _ok(health=source_health_summary())
        if action == "helper_preview":
            return _discovery_helper_preview(payload)
        if action == "feed_preview":
            return _discovery_feed_preview(payload)
        if action == "sitemap_preview":
            return _discovery_sitemap_preview(payload)
        if action == "source_policy_summary":
            return _discovery_source_policy_summary()
    except Exception as exc:
        return _error("internal_error", str(exc))

    return _error("unhandled_action", action)  # pragma: no cover


def _discovery_helper_preview(payload: dict) -> dict[str, Any]:
    from frontier_ai_risk_observer.helpers import get_helper_for_source
    source_id = payload.get("source_id", "")
    fetch = payload.get("fetch", False)
    helper = get_helper_for_source(source_id)
    if helper is None:
        return _ok(helper_available=False, source_id=source_id)
    try:
        candidates = helper(fetch=fetch)
        return _ok(
            helper_available=True,
            source_id=source_id,
            candidates=[
                {
                    "title": c.title,
                    "url": c.url,
                    "source_id": c.source_id,
                    "content_snippet": (c.content_text or "")[:500],
                }
                for c in candidates[:20]
            ],
            count=len(candidates[:20]),
        )
    except Exception as exc:
        return _ok(helper_available=True, source_id=source_id, error=str(exc))


def _discovery_feed_preview(payload: dict) -> dict[str, Any]:
    """Preview RSS feed for a source (if helper type is rss)."""
    from frontier_ai_risk_observer.services.registry_service import get_source
    source_id = payload.get("source_id", "")
    source = get_source(source_id)
    if source is None:
        return _error("not_found", f"Source not found: {source_id}")
    helper_type = source.get("helper_type", "")
    if helper_type != "rss":
        return _ok(feed_available=False, source_id=source_id, helper_type=helper_type)
    return _discovery_helper_preview({"source_id": source_id, "fetch": payload.get("fetch", False)})


def _discovery_sitemap_preview(payload: dict) -> dict[str, Any]:
    """Preview scrapling helper for a source (if helper type is scrapling_official_page)."""
    from frontier_ai_risk_observer.services.registry_service import get_source
    source_id = payload.get("source_id", "")
    source = get_source(source_id)
    if source is None:
        return _error("not_found", f"Source not found: {source_id}")
    helper_type = source.get("helper_type", "")
    if helper_type != "scrapling_official_page":
        return _ok(sitemap_available=False, source_id=source_id, helper_type=helper_type)
    return _discovery_helper_preview({"source_id": source_id, "fetch": payload.get("fetch", False)})


def _discovery_source_policy_summary() -> dict[str, Any]:
    """Return source reliability policy summary."""
    return _ok(
        policy={
            "no_cloudflare_bypass": True,
            "no_captcha_bypass": True,
            "prefer_feed_first": True,
            "search_fallback_only_when_allowed": True,
            "known_broken_sources": [
                "axrp — no RSS feed, R1-08 found no recent episodes",
                "ai_safety_summit_series — URL points to 2023 summit only",
            ],
        }
    )


# ---------------------------------------------------------------------------
# owl_live_vault — Live Obsidian research logging
# ---------------------------------------------------------------------------

_LIVE_VAULT_ACTIONS = frozenset({
    "start_run", "append_event", "upsert_note",
    "upsert_daily_report", "finalize_run", "inspect_latest",
})


def owl_live_vault(action: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Handle owl_live_vault actions."""
    if action not in _LIVE_VAULT_ACTIONS:
        return _error(
            "invalid_action",
            f"Unknown action: {action}. "
            f"Allowed: {sorted(_LIVE_VAULT_ACTIONS)}",
        )
    payload = payload or {}

    try:
        config = _get_live_vault_config()
        if not config.live_logging_enabled and action != "inspect_latest":
            return _ok(live_vault_enabled=False, action=action,
                       message="Live vault disabled. Set OBSIDIAN_LIVE_LOGGING_ENABLED=true.")

        if action == "start_run":
            return _live_vault_start_run(config, payload)
        if action == "append_event":
            return _live_vault_append_event(config, payload)
        if action == "upsert_note":
            return _live_vault_upsert_note(config, payload)
        if action == "upsert_daily_report":
            return _live_vault_upsert_daily_report(config, payload)
        if action == "finalize_run":
            return _live_vault_finalize_run(config, payload)
        if action == "inspect_latest":
            return _live_vault_inspect_latest(config)
    except Exception as exc:
        return _error("internal_error", str(exc))

    return _error("unhandled_action", action)  # pragma: no cover


def _get_live_vault_config():
    from frontier_ai_risk_observer.obsidian.live_writer import LiveVaultConfig
    return LiveVaultConfig.from_env()


def _live_vault_start_run(config, payload: dict) -> dict[str, Any]:
    from frontier_ai_risk_observer.obsidian.live_writer import LiveVaultWriter
    writer = LiveVaultWriter(config)
    run_id = payload.get("run_id")
    title = payload.get("title", "")
    metadata = payload.get("metadata")
    result = writer.start_run(run_id=run_id or "", title=title, metadata=metadata)
    return _ok(
        live_vault_enabled=True,
        run_id=run_id or "",
        notes_written=result.notes_written,
        errors=result.errors,
    )


def _live_vault_append_event(config, payload: dict) -> dict[str, Any]:
    from frontier_ai_risk_observer.obsidian.live_writer import LiveEvent, LiveVaultWriter
    writer = LiveVaultWriter(config)
    run_id = payload.get("run_id", "")
    event = LiveEvent(
        event_type=payload.get("event_type", "note"),
        title=payload.get("title", ""),
        body=payload.get("body"),
        source_id=payload.get("source_id"),
        raw_item_id=payload.get("raw_item_id"),
        signal_id=payload.get("signal_id"),
        evidence_id=payload.get("evidence_id"),
        metadata=payload.get("metadata", {}),
        note_vault_path=payload.get("note_vault_path"),
    )
    result = writer.append_event(run_id=run_id, event=event)
    return _ok(live_vault_enabled=True, run_id=run_id,
               notes_written=result.notes_written, errors=result.errors)


def _live_vault_upsert_note(config, payload: dict) -> dict[str, Any]:
    from frontier_ai_risk_observer.obsidian.live_writer import LiveVaultWriter
    writer = LiveVaultWriter(config)
    run_id = payload.get("run_id", "")
    note_type = payload.get("note_type", "note")
    slug = payload.get("slug", "untitled")
    title = payload.get("title", "Untitled")
    body = payload.get("body", "")
    source_id = payload.get("source_id")
    metadata = payload.get("metadata")

    dispatch = {
        "source": writer.upsert_source_note,
        "candidate": writer.upsert_candidate_note,
        "evidence": writer.upsert_evidence_note,
        "signal": writer.upsert_signal_note,
        "failure": writer.record_failure,
    }
    handler = dispatch.get(note_type)
    if handler is None:
        return _error("invalid_note_type", f"Unknown note_type: {note_type}")

    if note_type == "source":
        result = handler(run_id=run_id, source_id=source_id or slug,
                         title=title, body=body, metadata=metadata)
    elif note_type == "failure":
        result = handler(run_id=run_id, source_id=source_id or slug,
                         failure_type=payload.get("failure_type", "error"),
                         message=body, metadata=metadata)
    else:
        result = handler(run_id=run_id, slug=slug, title=title, body=body, metadata=metadata)

    return _ok(live_vault_enabled=True, run_id=run_id, note_type=note_type,
               notes_written=result.notes_written, errors=result.errors)


def _live_vault_upsert_daily_report(config, payload: dict) -> dict[str, Any]:
    from frontier_ai_risk_observer.obsidian.daily_note import upsert_daily_report_note
    report_date = payload.get("report_date", date.today().isoformat())
    report_markdown = payload.get("report_markdown", "")
    if not report_markdown:
        return _error("missing_field", "report_markdown is required")

    vault_path = config.vault_path / "AI-Risk-Intelligence"
    try:
        result = upsert_daily_report_note(
            vault_path=vault_path,
            report_date=report_date,
            report_markdown=report_markdown,
            digest_id=payload.get("digest_id"),
            run_id=payload.get("run_id"),
            status=payload.get("status", "draft"),
            summary=payload.get("summary", {}),
            signal_note_paths=payload.get("signal_note_paths", []),
            candidate_note_paths=payload.get("candidate_note_paths", []),
            evidence_note_paths=payload.get("evidence_note_paths", []),
            source_note_paths=payload.get("source_note_paths", []),
            failure_note_paths=payload.get("failure_note_paths", []),
            metadata=payload.get("metadata", {}),
        )
        return _ok(live_vault_enabled=True, report_date=report_date, written=result.success)
    except Exception as exc:
        return _error("write_error", str(exc))


def _live_vault_finalize_run(config, payload: dict) -> dict[str, Any]:
    from frontier_ai_risk_observer.obsidian.live_writer import LiveVaultWriter
    writer = LiveVaultWriter(config)
    run_id = payload.get("run_id", "")
    result = writer.finalize_run(
        run_id=run_id,
        summary=payload.get("summary"),
        metadata=payload.get("metadata"),
        final_report_markdown=payload.get("final_report_markdown"),
        digest_id=payload.get("digest_id"),
        daily_report_date=payload.get("daily_report_date"),
        quality_score=payload.get("quality_score"),
        signal_note_paths=payload.get("signal_note_paths", []),
        candidate_note_paths=payload.get("candidate_note_paths", []),
        evidence_note_paths=payload.get("evidence_note_paths", []),
        source_note_paths=payload.get("source_note_paths", []),
        failure_note_paths=payload.get("failure_note_paths", []),
    )
    return _ok(live_vault_enabled=True, run_id=run_id,
               notes_written=result.notes_written, errors=result.errors)


def _live_vault_inspect_latest(config) -> dict[str, Any]:
    vault_path = config.vault_path / "AI-Risk-Intelligence"
    live_dir = vault_path / config.runs_dir_name
    if not live_dir.exists():
        return _ok(live_vault_enabled=config.live_logging_enabled,
                   live_runs_exist=False, run_count=0)
    run_dirs = sorted([d for d in live_dir.iterdir() if d.is_dir()], reverse=True)
    runs = []
    for rd in run_dirs[:10]:
        log_path = rd / "Live Research Log.md"
        runs.append({
            "run_id": rd.name,
            "has_log": log_path.exists(),
            "subdirs": [p.name for p in rd.iterdir() if p.is_dir()],
        })
    return _ok(
        live_vault_enabled=config.live_logging_enabled,
        live_runs_exist=True,
        run_count=len(run_dirs),
        recent_runs=runs,
    )


# ---------------------------------------------------------------------------
# owl_report_quality — Report quality and review
# ---------------------------------------------------------------------------

_REPORT_QUALITY_ACTIONS = frozenset({
    "check_report", "latest_report_summary",
    "review_queue_summary", "quality_rubric_summary",
})


def owl_report_quality(action: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Handle owl_report_quality actions."""
    if action not in _REPORT_QUALITY_ACTIONS:
        return _error(
            "invalid_action",
            f"Unknown action: {action}. "
            f"Allowed: {sorted(_REPORT_QUALITY_ACTIONS)}",
        )
    payload = payload or {}

    try:
        if action == "check_report":
            return _quality_check_report(payload)
        if action == "latest_report_summary":
            return _quality_latest_report_summary()
        if action == "review_queue_summary":
            return _quality_review_queue_summary()
        if action == "quality_rubric_summary":
            return _quality_rubric_summary()
    except Exception as exc:
        return _error("internal_error", str(exc))

    return _error("unhandled_action", action)  # pragma: no cover


def _quality_check_report(payload: dict) -> dict[str, Any]:
    from frontier_ai_risk_observer.quality.report_quality import check_report
    text = payload.get("report_text", "")
    if not text:
        report_path = payload.get("report_path")
        if report_path and Path(report_path).exists():
            text = Path(report_path).read_text(encoding="utf-8")
        else:
            return _error("missing_input", "report_text or report_path required")
    report = check_report(text)
    return _ok(
        score=report.score_percent,
        max_score=int(report.max_score),
        passed=len(report.failed_checks) == 0,
        failed_checks=report.failed_checks,
        anti_patterns=report.anti_patterns,
        suggestions=report.suggestions,
    )


def _quality_latest_report_summary() -> dict[str, Any]:
    """Find and summarize the latest daily report."""
    runs_dir = Path("runs/daily")
    if not runs_dir.exists():
        return _ok(found=False, message="No daily report runs found")
    run_dirs = sorted([d for d in runs_dir.iterdir() if d.is_dir()], reverse=True)
    if not run_dirs:
        return _ok(found=False, message="No daily report runs found")
    latest = run_dirs[0]
    report_path = latest / "daily_report.md"
    if not report_path.exists():
        return _ok(found=True, run_dir=latest.name, report_exists=False)
    text = report_path.read_text(encoding="utf-8")
    from frontier_ai_risk_observer.quality.report_quality import check_report
    report = check_report(text)
    return _ok(
        found=True,
        run_dir=latest.name,
        report_exists=True,
        score=report.score_percent,
        failed_checks=report.failed_checks,
        anti_patterns=report.anti_patterns,
    )


def _quality_review_queue_summary() -> dict[str, Any]:
    """Summarize the review queue from the DB."""
    session = _get_session()
    try:
        from sqlalchemy import func, select

        from frontier_ai_risk_observer.db.models import Signal, SourceClaim, SourceRun
        signals_needs_review = session.scalar(
            select(func.count(Signal.id)).where(Signal.needs_human_review == True)  # noqa: E712
        ) or 0
        evidence_needs_review = session.scalar(
            select(func.count(SourceClaim.id)).where(SourceClaim.needs_human_review == True)  # noqa: E712
        ) or 0
        failed_runs = session.scalar(
            select(func.count(SourceRun.id)).where(SourceRun.status == "error")
        ) or 0
        return _ok(
            signals_needs_review=signals_needs_review,
            evidence_needs_review=evidence_needs_review,
            failed_source_runs=failed_runs,
        )
    finally:
        session.close()


def _quality_rubric_summary() -> dict[str, Any]:
    """Return the quality rubric checklist summary."""
    from frontier_ai_risk_observer.quality.report_quality import load_checklist
    checklist = load_checklist()
    items = []
    for item in checklist:
        items.append({
            "check_id": item.get("check_id", ""),
            "name": item.get("name", ""),
            "weight": item.get("weight", 0),
        })
    return _ok(checklist=items, count=len(items))


# ---------------------------------------------------------------------------
# owl_obsidian_export — Obsidian vault export/backfill
# ---------------------------------------------------------------------------

_EXPORT_ACTIONS = frozenset({
    "export_latest", "dry_run", "inspect", "open_latest_if_available",
})


def owl_obsidian_export(action: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Handle owl_obsidian_export actions."""
    if action not in _EXPORT_ACTIONS:
        return _error(
            "invalid_action",
            f"Unknown action: {action}. "
            f"Allowed: {sorted(_EXPORT_ACTIONS)}",
        )
    payload = payload or {}

    try:
        if action == "export_latest":
            return _export_latest(payload, dry_run=False)
        if action == "dry_run":
            return _export_latest(payload, dry_run=True)
        if action == "inspect":
            return _export_inspect(payload)
        if action == "open_latest_if_available":
            return _export_open_latest()
    except Exception as exc:
        return _error("internal_error", str(exc))

    return _error("unhandled_action", action)  # pragma: no cover


def _export_latest(payload: dict, dry_run: bool) -> dict[str, Any]:
    from frontier_ai_risk_observer.obsidian.exporter import ObsidianExportConfig, ObsidianExporter
    vault_path = Path(os.getenv("OBSIDIAN_VAULT_PATH", ".local/obsidian_vault"))
    config = ObsidianExportConfig(
        vault_path=vault_path,
        export_date=payload.get("export_date"),
        dry_run=dry_run,
    )
    exporter = ObsidianExporter(config)
    summary = exporter.export()
    return _ok(
        dry_run=dry_run,
        daily_notes=summary.daily_notes,
        signal_notes=summary.signal_notes,
        candidate_notes=summary.candidate_notes,
        evidence_notes=summary.evidence_notes,
        source_notes=summary.source_notes,
        risk_domain_notes=summary.risk_domain_notes,
        entity_notes=summary.entity_notes,
        run_notes=summary.run_notes,
        review_notes=summary.review_notes,
        index_notes=summary.index_notes,
        errors=summary.errors,
    )


def _export_inspect(payload: dict) -> dict[str, Any]:
    """Run vault inspection."""
    from scripts.inspect_obsidian_export import inspect_vault
    vault_path = Path(os.getenv("OBSIDIAN_VAULT_PATH", ".local/obsidian_vault"))
    result = inspect_vault(vault_path)
    from dataclasses import asdict
    return _ok(inspection=asdict(result))


def _export_open_latest() -> dict[str, Any]:
    """Try to open the latest vault export in Obsidian/Finder."""
    try:
        from frontier_ai_risk_observer.obsidian.cli import open_in_finder
        vault_path = Path(os.getenv("OBSIDIAN_VAULT_PATH", ".local/obsidian_vault"))
        vault_dir = vault_path / "AI-Risk-Intelligence"
        if not vault_dir.exists():
            return _ok(opened=False, message="Vault directory does not exist")
        success = open_in_finder(vault_dir)
        return _ok(opened=success)
    except Exception as exc:
        return _ok(opened=False, message=str(exc))


# ---------------------------------------------------------------------------
# Serialization helpers (lightweight, for facade output)
# ---------------------------------------------------------------------------

def _raw_item_to_dict(item) -> dict[str, Any]:
    """Convert a RawItem ORM object to a dict."""
    return {
        "id": str(item.id),
        "source_id": item.source_id,
        "title": item.title,
        "url": item.url,
        "canonical_url": item.canonical_url,
        "content_hash": item.content_hash,
        "dedup_key": item.dedup_key,
        "seen_count": item.seen_count,
        "ingestion_status": item.ingestion_status,
    }


def _source_run_to_dict(run) -> dict[str, Any]:
    """Convert a SourceRun ORM object to a dict."""
    return {
        "id": str(run.id),
        "source_id": run.source_id,
        "status": run.status,
        "found_count": run.found_count,
        "new_count": run.new_count,
        "duplicate_count": run.duplicate_count,
        "error_message": run.error_message,
    }
