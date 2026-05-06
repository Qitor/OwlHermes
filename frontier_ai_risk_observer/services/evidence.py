"""Minimal persistence for Hermes-extracted evidence/claims.

This module stores evidence items that Hermes has already extracted.
It does not fetch URLs, call LLMs, or make risk judgments.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from frontier_ai_risk_observer.db.models import SourceClaim
from frontier_ai_risk_observer.db.session import DatabaseUnavailableError


def store_evidence_item(
    session: Session,
    *,
    raw_item_id: str | None = None,
    signal_id: str | None = None,
    source_id: str | None = None,
    claim_text: str = "",
    claim_type: str = "hermes_extraction",
    evidence_url: str | None = None,
    evidence_title: str | None = None,
    evidence_excerpt: str | None = None,
    evidence_level: str = "secondary",
    confidence: int | None = None,
    supports_signal: bool | None = None,
    risk_domains: list[str] | None = None,
    entities: list[str] | None = None,
    needs_human_review: bool = False,
    metadata: dict[str, Any] | None = None,
) -> SourceClaim:
    """Store one evidence/claim item extracted by Hermes."""
    now = datetime.now(UTC)
    claim = SourceClaim(
        id=uuid.uuid4(),
        raw_item_id=uuid.UUID(raw_item_id) if raw_item_id else None,
        signal_id=uuid.UUID(signal_id) if signal_id else None,
        source_id=source_id,
        claim_text=claim_text,
        claim_type=claim_type,
        primary_source_url=evidence_url,
        evidence_title=evidence_title,
        evidence_excerpt=evidence_excerpt,
        evidence_level=evidence_level,
        confidence=confidence,
        supports_signal=supports_signal,
        risk_domains=risk_domains or [],
        entities=entities or [],
        needs_human_review=needs_human_review,
        metadata_=metadata or {},
        created_at=now,
    )
    try:
        session.add(claim)
        session.commit()
        session.refresh(claim)
    except SQLAlchemyError as exc:
        session.rollback()
        msg = f"Failed to store evidence item: {exc}"
        raise DatabaseUnavailableError(msg) from exc
    return claim


def search_evidence_items(
    session: Session,
    *,
    signal_id: str | None = None,
    raw_item_id: str | None = None,
    source_id: str | None = None,
    claim_type: str | None = None,
    limit: int = 50,
) -> list[SourceClaim]:
    """Search stored evidence items."""
    statement = select(SourceClaim).order_by(desc(SourceClaim.created_at))
    if signal_id is not None:
        statement = statement.where(
            SourceClaim.signal_id == uuid.UUID(signal_id)
        )
    if raw_item_id is not None:
        statement = statement.where(
            SourceClaim.raw_item_id == uuid.UUID(raw_item_id)
        )
    if source_id is not None:
        statement = statement.where(SourceClaim.source_id == source_id)
    if claim_type is not None:
        statement = statement.where(SourceClaim.claim_type == claim_type)
    return list(session.scalars(statement.limit(limit)).all())


def list_recent_evidence_items(
    session: Session,
    limit: int = 50,
) -> list[SourceClaim]:
    """List most recent evidence items."""
    return list(
        session.scalars(
            select(SourceClaim)
            .order_by(desc(SourceClaim.created_at))
            .limit(limit)
        ).all()
    )


def evidence_to_dict(claim: SourceClaim) -> dict[str, Any]:
    """Return a JSON-friendly evidence payload."""
    return {
        "id": str(claim.id),
        "raw_item_id": str(claim.raw_item_id) if claim.raw_item_id else None,
        "signal_id": str(claim.signal_id) if claim.signal_id else None,
        "source_id": claim.source_id,
        "claim_text": claim.claim_text,
        "claim_type": claim.claim_type,
        "evidence_url": claim.primary_source_url,
        "evidence_title": claim.evidence_title,
        "evidence_excerpt": claim.evidence_excerpt,
        "evidence_level": claim.evidence_level,
        "confidence": claim.confidence,
        "supports_signal": claim.supports_signal,
        "risk_domains": claim.risk_domains,
        "entities": claim.entities,
        "needs_human_review": claim.needs_human_review,
        "metadata": claim.metadata_,
        "created_at": claim.created_at.isoformat() if claim.created_at else None,
    }
