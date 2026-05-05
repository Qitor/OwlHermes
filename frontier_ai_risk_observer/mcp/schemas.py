"""Pydantic input schemas for the minimal Hermes MCP state tools."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, HttpUrl

from frontier_ai_risk_observer.api.schemas import RawItemCreate, SourceRunCreate


class RawItemSeenCheckInput(BaseModel):
    """Input for deterministic raw item seen-check."""

    url: str | None = None
    content_hash: str | None = None
    source_id: str | None = None
    title: str | None = None


class RawItemSearchInput(BaseModel):
    """Input for deterministic raw item history search."""

    source_id: str | None = None
    url: str | None = None
    canonical_url: str | None = None
    content_hash: str | None = None
    dedup_key: str | None = None
    ingestion_status: str | None = None
    limit: int = Field(default=50, ge=1, le=500)


class DuplicateCandidatesInput(BaseModel):
    """Input for deterministic duplicate candidate search."""

    url: str | None = None
    content_hash: str | None = None
    source_id: str | None = None
    title: str | None = None
    limit: int = Field(default=20, ge=1, le=100)


class SignalStoreInput(BaseModel):
    """Minimal signal persistence input for Hermes-generated signal cards."""

    raw_item_id: str | None = None
    source_id: str | None = None
    title: str
    summary: str
    risk_domain: str | None = None
    risk_domains: list[str] = Field(default_factory=list)
    signal_type: str
    severity: int = Field(ge=1, le=5)
    confidence: int = Field(ge=1, le=5)
    evidence_url: HttpUrl | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    evidence_level: str = "primary"
    claim_type: str = "hermes_observation"
    time_sensitivity: int = Field(default=3, ge=1, le=5)
    priority_score: Decimal = Decimal("0")
    needs_human_review: bool = False
    status: str = "draft"
    signal_date: date | None = None


class SignalSearchInput(BaseModel):
    """Input for minimal signal search."""

    source_id: str | None = None
    signal_type: str | None = None
    risk_domain: str | None = None
    limit: int = Field(default=50, ge=1, le=500)


class DigestStoreInput(BaseModel):
    """Minimal digest persistence input for a Hermes-written digest."""

    digest_date: date
    title: str
    body: str
    language: str = "zh"
    status: str = "draft"
    metadata: dict[str, Any] = Field(default_factory=dict)
    timezone: str = "Asia/Shanghai"
    markdown_short: str | None = None
    signal_ids: list[str] = Field(default_factory=list)


class DigestSearchInput(BaseModel):
    """Input for digest lookup."""

    digest_date: date | None = None
    status: str | None = None
    limit: int = Field(default=20, ge=1, le=200)


class BenchmarkObservationStoreInput(BaseModel):
    """Placeholder input for later benchmark observation persistence."""

    benchmark_id: str
    source_url: HttpUrl
    observed_at: date | None = None
    value_text: str | None = None
    value_numeric: Decimal | None = None
    unit: str | None = None
    evidence: str | None = None
    confidence: int | None = Field(default=None, ge=1, le=5)
    raw_item_id: str | None = None
    signal_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


McpRawItemCreate = RawItemCreate
McpSourceRunCreate = SourceRunCreate


class CandidatePreprocessInput(BaseModel):
    """Input for advisory candidate pre-processing."""

    title: str
    url: str = ""
    content_text: str = ""
    source_id: str = ""
    focus: str = ""
    risk_domain: str = ""
