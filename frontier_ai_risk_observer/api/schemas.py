"""Pydantic schemas for API request and response bodies."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class RawItemCreate(BaseModel):
    """Raw material discovered by Hermes or an optional deterministic helper."""

    source_id: str
    source_type: str | None = None
    kind: str | None = None
    url: HttpUrl | None = None
    canonical_url: HttpUrl | None = None
    title: str
    published_at: datetime | None = None
    retrieved_at: datetime | None = None
    content_text: str | None = None
    content_hash: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_kind(self) -> RawItemCreate:
        if not self.source_type and not self.kind:
            self.kind = "source"
        return self


class RawItemRead(BaseModel):
    """Stored raw item response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_id: str
    modality: str
    url: str | None
    canonical_url: str | None
    normalized_title: str | None
    title: str
    published_at: datetime | None
    fetched_at: datetime
    content_text: str | None
    content_hash: str | None
    dedup_key: str | None
    metadata: dict[str, Any]
    status: str
    ingestion_status: str
    first_seen_at: datetime
    last_seen_at: datetime
    seen_count: int
    created_at: datetime


class RawItemIngestResult(BaseModel):
    """Result of deterministic raw item memory ingestion."""

    item: RawItemRead
    is_duplicate: bool
    match_type: str | None = None


class RawItemSeenRead(BaseModel):
    """Seen-check response for Hermes historical lookup."""

    seen: bool
    match_type: str | None = None
    raw_item_id: uuid.UUID | None = None
    canonical_url: str | None = None
    dedup_key: str | None = None


class DuplicateCandidateRead(BaseModel):
    """Deterministic duplicate candidate response."""

    item: RawItemRead
    match_type: str


class SourceRunCreate(BaseModel):
    """Observation/check run for a source."""

    source_id: str
    source_type: str | None = None
    kind: str | None = None
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    items_found: int = 0
    items_new: int = 0
    items_duplicate: int = 0
    items_error: int = 0
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_kind(self) -> SourceRunCreate:
        if not self.source_type and not self.kind:
            self.kind = "source"
        return self


class SourceRunRead(BaseModel):
    """Stored source run response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_id: str
    source_type: str
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    items_found: int
    items_new: int
    items_duplicate: int
    items_error: int
    error_message: str | None
    metadata: dict[str, Any]
    created_at: datetime
