"""Pydantic input schemas for the minimal Hermes MCP state tools."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Literal

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
    what_changed: str = ""
    why_it_matters: str = ""
    what_to_watch_next: str = ""
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
    needs_review_reason: str = ""
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


class EvidenceStoreInput(BaseModel):
    """Input for storing an evidence/claim item."""

    raw_item_id: str | None = None
    signal_id: str | None = None
    source_id: str | None = None
    claim_text: str = ""
    claim_type: str = "hermes_extraction"
    evidence_url: str | None = None
    evidence_title: str | None = None
    evidence_excerpt: str | None = None
    evidence_level: str = "secondary"
    confidence: int | None = Field(default=None, ge=1, le=5)
    supports_signal: bool | None = None
    risk_domains: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    needs_human_review: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceSearchInput(BaseModel):
    """Input for searching evidence items."""

    signal_id: str | None = None
    raw_item_id: str | None = None
    source_id: str | None = None
    claim_type: str | None = None
    limit: int = Field(default=50, ge=1, le=500)


class CandidatePreprocessInput(BaseModel):
    """Input for advisory candidate pre-processing."""

    title: str
    url: str = ""
    content_text: str = ""
    source_id: str = ""
    focus: str = ""
    risk_domain: str = ""


# ---------------------------------------------------------------------------
# R1-13: Live Obsidian Research Logging
# ---------------------------------------------------------------------------


class LiveRunStartInput(BaseModel):
    """Input for starting a live research run."""

    run_id: str | None = None
    title: str = ""


class LiveEventAppendInput(BaseModel):
    """Input for appending an event to a live research run."""

    run_id: str
    event_type: str = Field(
        description=(
            "Event type. Allowed: run_started, source_selected, "
            "source_check_started, source_check_completed, source_failed, "
            "candidate_found, candidate_seen_check, candidate_stored, "
            "evidence_extracted, signal_promoted, signal_stored, "
            "digest_stored, run_finalized, note, warning"
        )
    )
    title: str = ""
    body: str | None = Field(
        default=None,
        description="Observable research state only. No chain-of-thought.",
    )
    source_id: str | None = None
    raw_item_id: str | None = None
    signal_id: str | None = None
    evidence_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LiveNoteUpsertInput(BaseModel):
    """Input for upserting a live note in the research vault."""

    run_id: str
    note_type: Literal["source", "candidate", "evidence", "signal", "failure"]
    slug: str = Field(
        description="Filename slug for the note. No path separators or ../ allowed."
    )
    title: str
    body: str = Field(
        description="Observable research state only. No chain-of-thought."
    )
    source_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LiveRunFinalizeInput(BaseModel):
    """Input for finalizing a live research run."""

    run_id: str
    summary: dict[str, Any] = Field(default_factory=dict)
