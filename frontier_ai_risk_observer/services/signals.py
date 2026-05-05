"""Minimal persistence for Hermes-generated risk signals.

This module stores signals that Hermes has already judged worth preserving.
It does not perform scoring, triage, summarization, or LLM reasoning.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from frontier_ai_risk_observer.db.models import Signal
from frontier_ai_risk_observer.db.session import DatabaseUnavailableError
from frontier_ai_risk_observer.mcp.schemas import SignalStoreInput


def store_signal(session: Session, payload: SignalStoreInput) -> Signal:
    """Store one Hermes-generated signal card."""
    risk_domains = _risk_domains(payload.risk_domain, payload.risk_domains)
    source_ids = [payload.source_id] if payload.source_id else []
    raw_item_ids = [payload.raw_item_id] if payload.raw_item_id else []
    now = datetime.now(UTC)
    metadata = {
        "summary": payload.summary,
        "mcp_metadata": payload.metadata,
    }
    signal = Signal(
        id=uuid.uuid4(),
        title_zh=payload.title,
        summary_zh=payload.summary,
        what_changed=str(payload.metadata.get("what_changed", payload.summary)),
        why_it_matters=str(payload.metadata.get("why_it_matters", payload.summary)),
        what_to_watch_next=str(payload.metadata.get("what_to_watch_next", "")),
        signal_type=payload.signal_type,
        risk_domains=risk_domains,
        entities=list(payload.metadata.get("entities", [])),
        source_ids=source_ids,
        raw_item_ids=raw_item_ids,
        claim_ids=list(payload.metadata.get("claim_ids", [])),
        primary_source_url=str(payload.evidence_url) if payload.evidence_url else None,
        evidence_level=payload.evidence_level,
        claim_type=payload.claim_type,
        severity=payload.severity,
        confidence=payload.confidence,
        time_sensitivity=payload.time_sensitivity,
        priority_score=payload.priority_score,
        needs_human_review=payload.needs_human_review,
        status=payload.status,
        signal_date=payload.signal_date or date.today(),
        metadata_=metadata,
        created_at=now,
        updated_at=now,
    )
    try:
        session.add(signal)
        session.commit()
        session.refresh(signal)
    except SQLAlchemyError as exc:
        session.rollback()
        msg = f"Failed to store signal: {exc}"
        raise DatabaseUnavailableError(msg) from exc
    return signal


def search_signals(
    session: Session,
    *,
    source_id: str | None = None,
    signal_type: str | None = None,
    risk_domain: str | None = None,
    limit: int = 50,
) -> list[Signal]:
    """Search stored signals with minimal deterministic filters."""
    statement = select(Signal).order_by(desc(Signal.created_at)).limit(limit)
    if signal_type is not None:
        statement = statement.where(Signal.signal_type == signal_type)
    candidates = list(session.scalars(statement).all())
    if source_id is not None:
        candidates = [signal for signal in candidates if source_id in signal.source_ids]
    if risk_domain is not None:
        candidates = [signal for signal in candidates if risk_domain in signal.risk_domains]
    return candidates[:limit]


def signal_to_dict(signal: Signal) -> dict[str, Any]:
    """Return a JSON-friendly signal payload."""
    return {
        "id": str(signal.id),
        "title": signal.title_zh,
        "summary": signal.summary_zh,
        "risk_domains": signal.risk_domains,
        "signal_type": signal.signal_type,
        "severity": signal.severity,
        "confidence": signal.confidence,
        "evidence_url": signal.primary_source_url,
        "source_ids": signal.source_ids,
        "raw_item_ids": signal.raw_item_ids,
        "status": signal.status,
        "signal_date": signal.signal_date.isoformat(),
        "priority_score": str(signal.priority_score),
        "metadata": signal.metadata_,
        "created_at": signal.created_at.isoformat(),
    }


def _risk_domains(risk_domain: str | None, risk_domains: list[str]) -> list[str]:
    domains = list(risk_domains)
    if risk_domain and risk_domain not in domains:
        domains.append(risk_domain)
    return domains
