"""Hermes-led ingestion API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from frontier_ai_risk_observer.api.schemas import (
    DuplicateCandidateRead,
    RawItemCreate,
    RawItemIngestResult,
    RawItemRead,
    RawItemSeenRead,
    SourceRunCreate,
    SourceRunRead,
)
from frontier_ai_risk_observer.db.models import RawItem, SourceRun
from frontier_ai_risk_observer.db.session import DatabaseUnavailableError, get_db_session
from frontier_ai_risk_observer.services.ingestion import (
    UnknownRegistrySourceError,
    create_raw_item,
    list_duplicate_candidates,
    list_raw_items,
    record_source_run,
    seen_raw_item,
)

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/raw-items", response_model=RawItemIngestResult)
def create_raw_item_route(
    payload: RawItemCreate,
    session: Annotated[Session, Depends(get_db_session)],
) -> RawItemIngestResult:
    """Store raw material discovered by Hermes or an optional helper."""
    try:
        result = create_raw_item(session, payload)
    except UnknownRegistrySourceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DatabaseUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return RawItemIngestResult(
        item=_raw_item_to_read(result.item),
        is_duplicate=result.is_duplicate,
        match_type=result.match_type,
    )


@router.get("/raw-items", response_model=list[RawItemRead])
def list_raw_items_route(
    session: Annotated[Session, Depends(get_db_session)],
    source_id: str | None = None,
    url: str | None = None,
    canonical_url: str | None = None,
    content_hash: str | None = None,
    dedup_key: str | None = None,
    ingestion_status: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
) -> list[RawItemRead]:
    """List raw items for deterministic history checks."""
    try:
        items = list_raw_items(
            session,
            source_id=source_id,
            url=url,
            canonical_url=canonical_url,
            content_hash=content_hash,
            dedup_key=dedup_key,
            ingestion_status=ingestion_status,
            limit=limit,
        )
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=f"Database is unavailable: {exc}") from exc
    return [_raw_item_to_read(item) for item in items]


@router.get("/raw-items/seen", response_model=RawItemSeenRead)
def seen_raw_item_route(
    session: Annotated[Session, Depends(get_db_session)],
    url: str | None = None,
    content_hash: str | None = None,
    source_id: str | None = None,
    title: str | None = None,
) -> RawItemSeenRead:
    """Check whether a raw item was already seen."""
    try:
        match = seen_raw_item(
            session,
            url=url,
            content_hash=content_hash,
            source_id=source_id,
            title=title,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=f"Database is unavailable: {exc}") from exc
    if match is None:
        return RawItemSeenRead(seen=False)
    return RawItemSeenRead(
        seen=True,
        match_type=match.match_type,
        raw_item_id=match.item.id,
        canonical_url=match.item.canonical_url,
        dedup_key=match.dedup_key,
    )


@router.get("/raw-items/duplicates", response_model=list[DuplicateCandidateRead])
def duplicate_candidates_route(
    session: Annotated[Session, Depends(get_db_session)],
    url: str | None = None,
    content_hash: str | None = None,
    source_id: str | None = None,
    title: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[DuplicateCandidateRead]:
    """Return deterministic possible duplicate candidates."""
    try:
        matches = list_duplicate_candidates(
            session,
            url=url,
            content_hash=content_hash,
            source_id=source_id,
            title=title,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=f"Database is unavailable: {exc}") from exc
    return [
        DuplicateCandidateRead(item=_raw_item_to_read(match.item), match_type=match.match_type)
        for match in matches
    ]


@router.post("/source-runs", response_model=SourceRunRead)
def source_run_route(
    payload: SourceRunCreate,
    session: Annotated[Session, Depends(get_db_session)],
) -> SourceRunRead:
    """Record a source observation/check run without triggering collection."""
    try:
        return _source_run_to_read(record_source_run(session, payload))
    except UnknownRegistrySourceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DatabaseUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _raw_item_to_read(item: RawItem) -> RawItemRead:
    return RawItemRead(
        id=item.id,
        source_id=item.source_id,
        modality=item.modality,
        url=item.url,
        canonical_url=item.canonical_url,
        normalized_title=item.normalized_title,
        title=item.title,
        published_at=item.published_at,
        fetched_at=item.fetched_at,
        content_text=item.content_text,
        content_hash=item.content_hash,
        dedup_key=item.dedup_key,
        metadata=item.metadata_,
        status=item.status,
        ingestion_status=item.ingestion_status,
        first_seen_at=item.first_seen_at,
        last_seen_at=item.last_seen_at,
        seen_count=item.seen_count,
        created_at=item.created_at,
    )


def _source_run_to_read(run: SourceRun) -> SourceRunRead:
    return SourceRunRead(
        id=run.id,
        source_id=run.source_id,
        source_type=run.source_type,
        status=run.status,
        started_at=run.started_at,
        finished_at=run.finished_at,
        items_found=run.items_found,
        items_new=run.items_new,
        items_duplicate=run.items_duplicate,
        items_error=run.items_error,
        error_message=run.error_message,
        metadata=run.metadata_,
        created_at=run.created_at,
    )
