"""SQLAlchemy models mirroring ``schemas/schema.sql``."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for database models."""


JSON_EMPTY_ARRAY = text("'[]'")
JSON_EMPTY_OBJECT = text("'{}'")
JSON_TYPE = JSON().with_variant(JSONB(), "postgresql")
NOW = text("now()")
UUID_TYPE = Uuid(as_uuid=True)


class Source(Base):
    """Configured source from the source registry."""

    __tablename__ = "sources"
    __table_args__ = (CheckConstraint("priority IN ('high','medium','low')"),)

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    modality: Mapped[str] = mapped_column(Text, nullable=False)
    collector: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    feed_url: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_interval: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    risk_focus: Mapped[list[Any]] = mapped_column(
        JSON_TYPE, nullable=False, server_default=JSON_EMPTY_ARRAY
    )
    extractor_strategy: Mapped[dict[str, Any]] = mapped_column(
        JSON_TYPE, nullable=False, server_default=JSON_EMPTY_OBJECT
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=NOW
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=NOW
    )


class SourceHealth(Base):
    """Fetch health state for a configured source."""

    __tablename__ = "source_health"

    source_id: Mapped[str] = mapped_column(
        Text, ForeignKey("sources.id", ondelete="CASCADE"), primary_key=True
    )
    last_fetch_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consecutive_failures: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    last_error: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'unknown'"))
    metrics: Mapped[dict[str, Any]] = mapped_column(
        JSON_TYPE, nullable=False, server_default=JSON_EMPTY_OBJECT
    )


class SourceRun(Base):
    """Observation/check run recorded by Hermes or an optional helper."""

    __tablename__ = "source_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    source_id: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    items_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_new: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_duplicate: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_error: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON_TYPE, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )


class RawItem(Base):
    """Fetched raw material before Hermes triage."""

    __tablename__ = "raw_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, primary_key=True, default=uuid.uuid4
    )
    source_id: Mapped[str] = mapped_column(Text, ForeignKey("sources.id"), nullable=False)
    modality: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    canonical_url: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_title: Mapped[str | None] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=NOW
    )
    language: Mapped[str | None] = mapped_column(Text)
    content_text: Mapped[str | None] = mapped_column(Text)
    content_html: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(Text)
    dedup_key: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON_TYPE, nullable=False, server_default=JSON_EMPTY_OBJECT
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'new'"))
    ingestion_status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'new'")
    )
    duplicate_of: Mapped[uuid.UUID | None] = mapped_column(
        UUID_TYPE, ForeignKey("raw_items.id")
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=NOW
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=NOW
    )
    seen_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=NOW
    )


class EventCluster(Base):
    """Cluster for related raw items and claims pointing to one event."""

    __tablename__ = "event_clusters"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    canonical_event_key: Mapped[str | None] = mapped_column(Text, unique=True)
    entities: Mapped[list[Any]] = mapped_column(
        JSON_TYPE, nullable=False, server_default=JSON_EMPTY_ARRAY
    )
    risk_domains: Mapped[list[Any]] = mapped_column(
        JSON_TYPE, nullable=False, server_default=JSON_EMPTY_ARRAY
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=NOW
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=NOW
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON_TYPE, nullable=False, server_default=JSON_EMPTY_OBJECT
    )


class SourceClaim(Base):
    """Claim-level extraction / evidence item produced by Hermes."""

    __tablename__ = "source_claims"
    __table_args__ = (CheckConstraint("confidence BETWEEN 1 AND 5"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, primary_key=True, default=uuid.uuid4
    )
    raw_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID_TYPE, ForeignKey("raw_items.id", ondelete="CASCADE"), nullable=True
    )
    signal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID_TYPE, ForeignKey("signals.id"), nullable=True
    )
    source_id: Mapped[str | None] = mapped_column(Text)
    event_cluster_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID_TYPE, ForeignKey("event_clusters.id")
    )
    speaker: Mapped[str | None] = mapped_column(Text)
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[str] = mapped_column(Text, nullable=False)
    risk_domains: Mapped[list[Any]] = mapped_column(
        JSON_TYPE, nullable=False, server_default=JSON_EMPTY_ARRAY
    )
    entities: Mapped[list[Any]] = mapped_column(
        JSON_TYPE, nullable=False, server_default=JSON_EMPTY_ARRAY
    )
    evidence_level: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'secondary'")
    )
    evidence_quote: Mapped[str | None] = mapped_column(Text)
    evidence_excerpt: Mapped[str | None] = mapped_column(Text)
    evidence_title: Mapped[str | None] = mapped_column(Text)
    evidence_timestamp: Mapped[str | None] = mapped_column(Text)
    primary_source_url: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[int | None] = mapped_column(Integer)
    supports_signal: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True
    )
    should_promote_to_signal: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    needs_human_review: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON_TYPE, nullable=False, server_default=JSON_EMPTY_OBJECT
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=NOW
    )


class Signal(Base):
    """Risk signal card stored after Hermes triage and aggregation."""

    __tablename__ = "signals"
    __table_args__ = (
        CheckConstraint("severity BETWEEN 1 AND 5"),
        CheckConstraint("confidence BETWEEN 1 AND 5"),
        CheckConstraint("time_sensitivity BETWEEN 1 AND 5"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, primary_key=True, default=uuid.uuid4
    )
    event_cluster_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID_TYPE, ForeignKey("event_clusters.id")
    )
    title_zh: Mapped[str] = mapped_column(Text, nullable=False)
    summary_zh: Mapped[str] = mapped_column(Text, nullable=False)
    what_changed: Mapped[str] = mapped_column(Text, nullable=False)
    why_it_matters: Mapped[str] = mapped_column(Text, nullable=False)
    what_to_watch_next: Mapped[str] = mapped_column(Text, nullable=False)
    signal_type: Mapped[str] = mapped_column(Text, nullable=False)
    risk_domains: Mapped[list[Any]] = mapped_column(
        JSON_TYPE, nullable=False, server_default=JSON_EMPTY_ARRAY
    )
    entities: Mapped[list[Any]] = mapped_column(
        JSON_TYPE, nullable=False, server_default=JSON_EMPTY_ARRAY
    )
    source_ids: Mapped[list[Any]] = mapped_column(
        JSON_TYPE, nullable=False, server_default=JSON_EMPTY_ARRAY
    )
    raw_item_ids: Mapped[list[Any]] = mapped_column(
        JSON_TYPE, nullable=False, server_default=JSON_EMPTY_ARRAY
    )
    claim_ids: Mapped[list[Any]] = mapped_column(
        JSON_TYPE, nullable=False, server_default=JSON_EMPTY_ARRAY
    )
    primary_source_url: Mapped[str | None] = mapped_column(Text)
    evidence_level: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    time_sensitivity: Mapped[int] = mapped_column(Integer, nullable=False)
    priority_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    needs_human_review: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'draft'"))
    signal_date: Mapped[date] = mapped_column(
        Date, nullable=False, server_default=text("CURRENT_DATE")
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON_TYPE, nullable=False, server_default=JSON_EMPTY_OBJECT
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=NOW
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=NOW
    )


class BenchmarkRegistry(Base):
    """Registered benchmark, eval, or framework observation point."""

    __tablename__ = "benchmark_registry"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    risk_domains: Mapped[list[Any]] = mapped_column(
        JSON_TYPE, nullable=False, server_default=JSON_EMPTY_ARRAY
    )
    source_ids: Mapped[list[Any]] = mapped_column(
        JSON_TYPE, nullable=False, server_default=JSON_EMPTY_ARRAY
    )
    observation_type: Mapped[str] = mapped_column(Text, nullable=False)
    extraction_method: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'medium'"))
    trigger_rules: Mapped[list[Any]] = mapped_column(
        JSON_TYPE, nullable=False, server_default=JSON_EMPTY_ARRAY
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=NOW
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=NOW
    )


class BenchmarkObservation(Base):
    """Observed benchmark/eval/framework value linked to raw material or signals."""

    __tablename__ = "benchmark_observations"
    __table_args__ = (CheckConstraint("confidence BETWEEN 1 AND 5"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, primary_key=True, default=uuid.uuid4
    )
    benchmark_id: Mapped[str] = mapped_column(
        Text, ForeignKey("benchmark_registry.id"), nullable=False
    )
    model_name: Mapped[str | None] = mapped_column(Text)
    observed_at: Mapped[date | None] = mapped_column(Date)
    value_text: Mapped[str | None] = mapped_column(Text)
    value_numeric: Mapped[Decimal | None] = mapped_column(Numeric)
    unit: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[str | None] = mapped_column(Text)
    risk_interpretation: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[int | None] = mapped_column(Integer)
    raw_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID_TYPE, ForeignKey("raw_items.id")
    )
    signal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID_TYPE, ForeignKey("signals.id")
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON_TYPE, nullable=False, server_default=JSON_EMPTY_OBJECT
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=NOW
    )


class Digest(Base):
    """Daily or weekly digest generated by Hermes and stored by the backend."""

    __tablename__ = "digests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, primary_key=True, default=uuid.uuid4
    )
    digest_date: Mapped[date] = mapped_column(Date, nullable=False)
    timezone: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'Asia/Shanghai'")
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    markdown_full: Mapped[str] = mapped_column(Text, nullable=False)
    markdown_short: Mapped[str] = mapped_column(Text, nullable=False)
    signal_ids: Mapped[list[Any]] = mapped_column(
        JSON_TYPE, nullable=False, server_default=JSON_EMPTY_ARRAY
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'draft'"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=NOW
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=NOW
    )


class DeliveryEvent(Base):
    """Delivery status record after Hermes sends a digest through a gateway."""

    __tablename__ = "delivery_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, primary_key=True, default=uuid.uuid4
    )
    digest_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID_TYPE, ForeignKey("digests.id", ondelete="CASCADE")
    )
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    target: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=NOW
    )


class AuditLog(Base):
    """Append-only audit event for deterministic backend actions."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, primary_key=True, default=uuid.uuid4
    )
    actor: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    target_type: Mapped[str | None] = mapped_column(Text)
    target_id: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON_TYPE, nullable=False, server_default=JSON_EMPTY_OBJECT
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=NOW
    )


class ResearchEvent(Base):
    """Live research event logged during a Hermes daily report run."""

    __tablename__ = "research_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("''")
    )
    body: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[str | None] = mapped_column(Text)
    raw_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID_TYPE)
    signal_id: Mapped[uuid.UUID | None] = mapped_column(UUID_TYPE)
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(UUID_TYPE)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON_TYPE, nullable=False, server_default=JSON_EMPTY_OBJECT
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=NOW
    )
