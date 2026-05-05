"""Minimal persistence for Hermes-written digests.

Hermes writes the digest. The backend only stores and retrieves it.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from frontier_ai_risk_observer.db.models import Digest
from frontier_ai_risk_observer.db.session import DatabaseUnavailableError
from frontier_ai_risk_observer.mcp.schemas import DigestStoreInput


def store_digest(session: Session, payload: DigestStoreInput) -> Digest:
    """Create or update one Hermes-written digest."""
    markdown_short = payload.markdown_short or payload.body[:500]
    existing = session.scalars(
        select(Digest).where(
            Digest.digest_date == payload.digest_date,
            Digest.timezone == payload.timezone,
        )
    ).first()
    now = datetime.now(UTC)
    if existing is not None:
        existing.title = payload.title
        existing.markdown_full = payload.body
        existing.markdown_short = markdown_short
        existing.signal_ids = payload.signal_ids
        existing.status = payload.status
        existing.updated_at = now
        digest = existing
    else:
        digest = Digest(
            id=uuid.uuid4(),
            digest_date=payload.digest_date,
            timezone=payload.timezone,
            title=payload.title,
            markdown_full=payload.body,
            markdown_short=markdown_short,
            signal_ids=payload.signal_ids,
            status=payload.status,
            created_at=now,
            updated_at=now,
        )
        session.add(digest)
    try:
        session.commit()
        session.refresh(digest)
    except SQLAlchemyError as exc:
        session.rollback()
        msg = f"Failed to store digest: {exc}"
        raise DatabaseUnavailableError(msg) from exc
    return digest


def search_digests(
    session: Session,
    *,
    digest_date: object | None = None,
    status: str | None = None,
    limit: int = 20,
) -> list[Digest]:
    """Search stored digests with minimal deterministic filters."""
    statement = select(Digest).order_by(desc(Digest.digest_date), desc(Digest.created_at))
    if digest_date is not None:
        statement = statement.where(Digest.digest_date == digest_date)
    if status is not None:
        statement = statement.where(Digest.status == status)
    return list(session.scalars(statement.limit(limit)).all())


def digest_to_dict(digest: Digest) -> dict[str, Any]:
    """Return a JSON-friendly digest payload."""
    return {
        "id": str(digest.id),
        "digest_date": digest.digest_date.isoformat(),
        "timezone": digest.timezone,
        "title": digest.title,
        "body": digest.markdown_full,
        "markdown_short": digest.markdown_short,
        "signal_ids": digest.signal_ids,
        "status": digest.status,
        "created_at": digest.created_at.isoformat(),
        "updated_at": digest.updated_at.isoformat(),
    }
