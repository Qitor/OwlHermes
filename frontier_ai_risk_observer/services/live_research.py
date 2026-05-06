"""Live research event persistence service.

Stores and retrieves ResearchEvent records in SQLite for audit and replay.
Does NOT write to the Obsidian vault — that is handled by LiveVaultWriter.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from frontier_ai_risk_observer.db.models import ResearchEvent

ALLOWED_EVENT_TYPES: frozenset[str] = frozenset({
    "run_started",
    "source_selected",
    "source_check_started",
    "source_check_completed",
    "source_failed",
    "candidate_found",
    "candidate_seen_check",
    "candidate_stored",
    "evidence_extracted",
    "signal_promoted",
    "signal_stored",
    "digest_stored",
    "run_finalized",
    "note",
    "warning",
})


def store_research_event(
    session: Session,
    *,
    run_id: str,
    event_type: str,
    title: str = "",
    body: str | None = None,
    source_id: str | None = None,
    raw_item_id: str | None = None,
    signal_id: str | None = None,
    evidence_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ResearchEvent:
    """Store a research event in the database.

    Raises ValueError if event_type is not in ALLOWED_EVENT_TYPES.
    """
    if event_type not in ALLOWED_EVENT_TYPES:
        raise ValueError(
            f"Invalid event_type '{event_type}'. "
            f"Allowed: {', '.join(sorted(ALLOWED_EVENT_TYPES))}"
        )

    raw_item_uuid: uuid.UUID | None = None
    if raw_item_id is not None:
        raw_item_uuid = uuid.UUID(raw_item_id)

    signal_uuid: uuid.UUID | None = None
    if signal_id is not None:
        signal_uuid = uuid.UUID(signal_id)

    evidence_uuid: uuid.UUID | None = None
    if evidence_id is not None:
        evidence_uuid = uuid.UUID(evidence_id)

    event = ResearchEvent(
        run_id=run_id,
        event_type=event_type,
        title=title,
        body=body,
        source_id=source_id,
        raw_item_id=raw_item_uuid,
        signal_id=signal_uuid,
        evidence_id=evidence_uuid,
        metadata_=metadata or {},
        created_at=datetime.now(UTC),
    )
    try:
        session.add(event)
        session.commit()
        session.refresh(event)
    except SQLAlchemyError:
        session.rollback()
        raise
    return event


def search_research_events(
    session: Session,
    *,
    run_id: str | None = None,
    event_type: str | None = None,
    source_id: str | None = None,
    limit: int = 100,
) -> list[ResearchEvent]:
    """Search research events with optional filters."""
    stmt = select(ResearchEvent).order_by(ResearchEvent.created_at.desc())
    if run_id is not None:
        stmt = stmt.where(ResearchEvent.run_id == run_id)
    if event_type is not None:
        stmt = stmt.where(ResearchEvent.event_type == event_type)
    if source_id is not None:
        stmt = stmt.where(ResearchEvent.source_id == source_id)
    stmt = stmt.limit(limit)
    return list(session.scalars(stmt).all())


def research_event_to_dict(event: ResearchEvent) -> dict[str, Any]:
    """Serialize a ResearchEvent to a JSON-friendly dict."""
    return {
        "id": str(event.id),
        "run_id": event.run_id,
        "event_type": event.event_type,
        "title": event.title,
        "body": event.body,
        "source_id": event.source_id,
        "raw_item_id": str(event.raw_item_id) if event.raw_item_id else None,
        "signal_id": str(event.signal_id) if event.signal_id else None,
        "evidence_id": str(event.evidence_id) if event.evidence_id else None,
        "metadata": event.metadata_,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }
