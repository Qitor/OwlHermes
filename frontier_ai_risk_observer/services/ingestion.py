"""Service helpers for Hermes-led ingestion primitives."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from frontier_ai_risk_observer.api.schemas import RawItemCreate, SourceRunCreate
from frontier_ai_risk_observer.db.models import RawItem, Source, SourceRun
from frontier_ai_risk_observer.db.session import DatabaseUnavailableError
from frontier_ai_risk_observer.services.dedup import (
    RAW_ITEM_STATUS_NEW,
    build_dedup_key,
    canonicalize_url,
    compute_content_hash,
    normalize_title,
)
from frontier_ai_risk_observer.services.registry_service import find_registry_entry


class UnknownRegistrySourceError(ValueError):
    """Raised when ingestion references a source ID absent from registry files."""


@dataclass(frozen=True)
class RawItemIngested:
    """Stored raw item plus dedup metadata."""

    item: RawItem
    is_duplicate: bool
    match_type: str | None = None


@dataclass(frozen=True)
class RawItemMatch:
    """Deterministic raw item match for seen-check and duplicate candidates."""

    item: RawItem
    match_type: str
    dedup_key: str | None


def create_raw_item(session: Session, payload: RawItemCreate) -> RawItemIngested:
    """Create or touch a raw item without fetching, triage, or external calls."""
    try:
        _ensure_source(session, payload.source_id, payload.source_type or payload.kind or "source")
        now = datetime.now(UTC)
        canonical_url = _payload_canonical_url(payload)
        content_hash = payload.content_hash or compute_content_hash(payload.content_text)
        normalized_title = normalize_title(payload.title)

        match = find_duplicate_raw_item(
            session,
            url=canonical_url,
            content_hash=content_hash,
            source_id=payload.source_id,
            title=payload.title,
        )
        if match is not None:
            match.item.last_seen_at = now
            match.item.seen_count = (match.item.seen_count or 0) + 1
            session.commit()
            session.refresh(match.item)
            return RawItemIngested(
                item=match.item,
                is_duplicate=True,
                match_type=match.match_type,
            )

        dedup_key = build_dedup_key(
            canonical_url=canonical_url,
            content_hash=content_hash,
            source_id=payload.source_id,
            normalized_title=normalized_title,
        )
        item = RawItem(
            id=uuid.uuid4(),
            source_id=payload.source_id,
            modality=payload.source_type or payload.kind or "source",
            url=str(payload.url) if payload.url else None,
            canonical_url=canonical_url,
            title=payload.title,
            normalized_title=normalized_title,
            published_at=payload.published_at,
            fetched_at=payload.retrieved_at or now,
            content_text=payload.content_text,
            content_hash=content_hash,
            dedup_key=dedup_key,
            metadata_=payload.metadata,
            status=RAW_ITEM_STATUS_NEW,
            ingestion_status=RAW_ITEM_STATUS_NEW,
            first_seen_at=now,
            last_seen_at=now,
            seen_count=1,
            created_at=now,
        )
        session.add(item)
        session.commit()
        session.refresh(item)
    except SQLAlchemyError as exc:
        session.rollback()
        msg = f"Failed to store raw item: {exc}"
        raise DatabaseUnavailableError(msg) from exc
    return RawItemIngested(item=item, is_duplicate=False)


def list_raw_items(
    session: Session,
    *,
    source_id: str | None = None,
    url: str | None = None,
    canonical_url: str | None = None,
    content_hash: str | None = None,
    dedup_key: str | None = None,
    ingestion_status: str | None = None,
    limit: int = 50,
) -> list[RawItem]:
    """List raw items for simple history/dedup checks."""
    statement = select(RawItem).order_by(
        desc(RawItem.last_seen_at), desc(RawItem.fetched_at), desc(RawItem.created_at)
    )
    if source_id is not None:
        statement = statement.where(RawItem.source_id == source_id)
    if url is not None:
        url_key = canonicalize_url(url)
        statement = statement.where(or_(RawItem.url == url, RawItem.canonical_url == url_key))
    if canonical_url is not None:
        statement = statement.where(RawItem.canonical_url == canonicalize_url(canonical_url))
    if content_hash is not None:
        statement = statement.where(RawItem.content_hash == content_hash)
    if dedup_key is not None:
        statement = statement.where(RawItem.dedup_key == dedup_key)
    if ingestion_status is not None:
        statement = statement.where(RawItem.ingestion_status == ingestion_status)
    return list(session.scalars(statement.limit(limit)).all())


def seen_raw_item(
    session: Session,
    *,
    url: str | None = None,
    content_hash: str | None = None,
    source_id: str | None = None,
    title: str | None = None,
) -> RawItemMatch | None:
    """Return the first raw item matching deterministic dedup inputs."""
    if not any([url, content_hash, source_id and title]):
        msg = "At least one of url, content_hash, or source_id plus title is required"
        raise ValueError(msg)
    return find_duplicate_raw_item(
        session,
        url=url,
        content_hash=content_hash,
        source_id=source_id,
        title=title,
    )


def list_duplicate_candidates(
    session: Session,
    *,
    url: str | None = None,
    content_hash: str | None = None,
    source_id: str | None = None,
    title: str | None = None,
    limit: int = 20,
) -> list[RawItemMatch]:
    """Return deterministic duplicate candidates in matching-priority order."""
    if not any([url, content_hash, source_id and title]):
        msg = "At least one of url, content_hash, or source_id plus title is required"
        raise ValueError(msg)

    candidates: list[RawItemMatch] = []
    seen_ids: set[uuid.UUID] = set()
    for match in _iter_dedup_matches(
        session,
        url=url,
        content_hash=content_hash,
        source_id=source_id,
        title=title,
        limit=limit,
    ):
        if match.item.id in seen_ids:
            continue
        seen_ids.add(match.item.id)
        candidates.append(match)
        if len(candidates) >= limit:
            break
    return candidates


def find_duplicate_raw_item(
    session: Session,
    *,
    url: str | None = None,
    content_hash: str | None = None,
    source_id: str | None = None,
    title: str | None = None,
) -> RawItemMatch | None:
    """Find one duplicate using canonical URL, content hash, then title."""
    return next(
        _iter_dedup_matches(
            session,
            url=url,
            content_hash=content_hash,
            source_id=source_id,
            title=title,
            limit=1,
        ),
        None,
    )


def record_source_run(session: Session, payload: SourceRunCreate) -> SourceRun:
    """Record one source observation/check run."""
    _ensure_source(session, payload.source_id, payload.source_type or payload.kind or "source")
    run = SourceRun(
        id=uuid.uuid4(),
        source_id=payload.source_id,
        source_type=payload.source_type or payload.kind or "source",
        status=payload.status,
        started_at=payload.started_at,
        finished_at=payload.finished_at,
        items_found=payload.items_found,
        items_new=payload.items_new,
        items_duplicate=payload.items_duplicate,
        items_error=payload.items_error,
        error_message=payload.error_message,
        metadata_=payload.metadata,
        created_at=datetime.now(UTC),
    )
    try:
        session.add(run)
        session.commit()
        session.refresh(run)
    except SQLAlchemyError as exc:
        session.rollback()
        msg = f"Failed to record source run: {exc}"
        raise DatabaseUnavailableError(msg) from exc
    return run


def _iter_dedup_matches(
    session: Session,
    *,
    url: str | None,
    content_hash: str | None,
    source_id: str | None,
    title: str | None,
    limit: int,
) -> Iterator[RawItemMatch]:
    canonical_url = canonicalize_url(url) if url else None
    normalized_title = normalize_title(title)

    # Matching priority is intentionally simple and stable:
    # canonical URL, exact content hash, then same source plus normalized title.
    if canonical_url:
        key = build_dedup_key(canonical_url=canonical_url)
        statement = _ordered_raw_items().where(RawItem.canonical_url == canonical_url)
        for item in session.scalars(statement.limit(limit)).all():
            yield RawItemMatch(item=item, match_type="canonical_url", dedup_key=key)
    if content_hash:
        key = build_dedup_key(content_hash=content_hash)
        statement = _ordered_raw_items().where(RawItem.content_hash == content_hash)
        for item in session.scalars(statement.limit(limit)).all():
            yield RawItemMatch(item=item, match_type="content_hash", dedup_key=key)
    if source_id and normalized_title:
        key = build_dedup_key(source_id=source_id, normalized_title=normalized_title)
        statement = _ordered_raw_items().where(
            RawItem.source_id == source_id,
            RawItem.normalized_title == normalized_title,
        )
        for item in session.scalars(statement.limit(limit)).all():
            yield RawItemMatch(item=item, match_type="source_title", dedup_key=key)


def _ordered_raw_items() -> Any:
    return select(RawItem).order_by(
        desc(RawItem.last_seen_at), desc(RawItem.fetched_at), desc(RawItem.created_at)
    )


def _payload_canonical_url(payload: RawItemCreate) -> str | None:
    raw_url = payload.canonical_url or payload.url
    return canonicalize_url(str(raw_url)) if raw_url else None


def _ensure_source(session: Session, source_id: str, fallback_kind: str) -> None:
    existing = session.get(Source, source_id)
    if existing is not None:
        return

    found = find_registry_entry(source_id)
    if found is None:
        msg = f"source_id '{source_id}' is not present in registry"
        raise UnknownRegistrySourceError(msg)

    kind, entry = found
    risk_focus = entry.get("risk_focus") or entry.get("risk_domains") or []
    collector = entry.get("collector") or entry.get("collection_method") or "hermes_workflow"
    source = Source(
        id=source_id,
        name=str(entry.get("name")),
        category=str(entry.get("category") or entry.get("event_type") or kind),
        modality=str(entry.get("modality") or fallback_kind),
        collector=str(collector),
        url=entry.get("url"),
        feed_url=entry.get("feed_url"),
        priority=str(entry.get("priority") or "medium"),
        refresh_interval=str(entry.get("refresh_interval") or "manual"),
        enabled=bool(entry.get("enabled", True)),
        risk_focus=risk_focus,
        extractor_strategy=entry.get("extractor_strategy") or {},
        notes=entry.get("notes"),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(source)
