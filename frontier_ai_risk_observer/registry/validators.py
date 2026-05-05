"""Typed registry validation models and helpers."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from frontier_ai_risk_observer.registry.loader import RegistryBundle

Priority = Literal["high", "medium", "low"]


class RegistryValidationError(ValueError):
    """Raised when registry entries fail semantic validation."""

    def __init__(self, errors: Iterable[str]) -> None:
        self.errors = list(errors)
        super().__init__("\n".join(self.errors))


def _is_http_url(value: str) -> bool:
    return value.startswith(("http://", "https://")) and len(value.split("://", 1)[1]) > 0


def _require_http_url(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    if not value.strip():
        msg = f"{field_name} must be non-empty when provided"
        raise ValueError(msg)
    if not _is_http_url(value):
        msg = f"{field_name} must be an HTTP/HTTPS URL"
        raise ValueError(msg)
    return value


def _validate_non_empty_string(value: str, field_name: str) -> str:
    if not value.strip():
        msg = f"{field_name} must be non-empty"
        raise ValueError(msg)
    return value


def _validate_optional_string_list(value: list[str] | None, field_name: str) -> list[str] | None:
    if value is None:
        return None
    if any(not isinstance(item, str) or not item.strip() for item in value):
        msg = f"{field_name} must contain only non-empty strings"
        raise ValueError(msg)
    return value


class RegistryEntryModel(BaseModel):
    """Base model for registry entries.

    Extra fields are allowed during early R1 because the registry carries
    workflow hints for Hermes and optional deterministic helpers.
    """

    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    enabled: bool = True
    notes: str | None = None

    @field_validator("id", "name")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _validate_non_empty_string(value, "required text field")


class SourceEntry(RegistryEntryModel):
    """Entry from ``sources.yaml``."""

    category: str
    url: str
    collector: str | None = None
    collection_method: str | None = None
    priority: Priority | int | float | None = None
    source_priority: Priority | int | float | None = None
    tags: list[str] | None = None
    risk_domains: list[str] | None = None
    risk_focus: list[str] | None = None
    update_frequency: str | None = None
    owner: str | None = None
    # Helper metadata (R1-09)
    helper_type: Literal[
        "none", "scrapling_official_page", "rss", "official_page_links",
        "sitemap", "arxiv_query", "manual",
    ] | None = None
    feed_url: str | None = None
    sitemap_url: str | None = None
    query: str | None = None
    list_url: str | None = None
    scrapling_url: str | None = None
    link_include_patterns: list[str] | None = None
    link_exclude_patterns: list[str] | None = None
    max_items: int | None = None
    lookback_days: int | None = None
    requires_human_review: bool | None = None
    known_issues: str | None = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        return _validate_non_empty_string(value, "category")

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        return _require_http_url(value, "url") or value

    @field_validator(
        "tags", "risk_domains", "risk_focus",
        "link_include_patterns", "link_exclude_patterns",
    )
    @classmethod
    def validate_lists(cls, value: list[str] | None, info: Any) -> list[str] | None:
        return _validate_optional_string_list(value, str(info.field_name))

    @field_validator("feed_url", "sitemap_url", "list_url", "scrapling_url")
    @classmethod
    def validate_helper_urls(cls, value: str | None, info: Any) -> str | None:
        return _require_http_url(value, str(info.field_name))

    @model_validator(mode="after")
    def validate_collection_and_priority(self) -> SourceEntry:
        if not self.collector and not self.collection_method:
            msg = "collector or collection_method is required"
            raise ValueError(msg)
        if self.priority is None and self.source_priority is None:
            msg = "priority or source_priority is required"
            raise ValueError(msg)
        return self


class PodcastEntry(RegistryEntryModel):
    """Entry from ``podcasts.yaml``."""

    url: str | None = None
    feed_url: str | None = None
    collector: str | None = None
    collection_method: str | None = None
    transcript_url: str | None = None
    hosts: list[str] | None = None
    tags: list[str] | None = None
    risk_domains: list[str] | None = None
    risk_focus: list[str] | None = None
    priority: Priority | int | float | None = None
    # Helper metadata (R1-09)
    helper_type: Literal[
        "podcast_rss", "transcript_index", "scrapling_official_page", "manual",
    ] | None = None
    transcript_index_url: str | None = None
    scrapling_url: str | None = None
    max_items: int | None = None
    lookback_days: int | None = None
    known_issues: str | None = None
    requires_human_review: bool | None = None

    @field_validator("url", "feed_url", "transcript_url", "transcript_index_url", "scrapling_url")
    @classmethod
    def validate_urls(cls, value: str | None, info: Any) -> str | None:
        return _require_http_url(value, str(info.field_name))

    @field_validator("hosts", "tags", "risk_domains", "risk_focus")
    @classmethod
    def validate_lists(cls, value: list[str] | None, info: Any) -> list[str] | None:
        return _validate_optional_string_list(value, str(info.field_name))

    @model_validator(mode="after")
    def validate_location_and_collection(self) -> PodcastEntry:
        if not self.url and not self.feed_url:
            msg = "at least one of url or feed_url is required"
            raise ValueError(msg)
        if not self.collector and not self.collection_method:
            msg = "collector or collection_method is required"
            raise ValueError(msg)
        return self


class EventEntry(RegistryEntryModel):
    """Entry from ``events.yaml``."""

    url: str
    category: str | None = None
    event_type: str | None = None
    organizer: str | None = None
    location: str | None = None
    recurring: bool | None = None
    dates: str | list[str] | list[dict[str, Any]] | dict[str, Any] | None = None
    tags: list[str] | None = None
    risk_domains: list[str] | None = None
    risk_focus: list[str] | None = None
    priority: Priority | int | float | None = None
    # Helper metadata (R1-09)
    helper_type: Literal[
        "scrapling_official_page", "official_page_links", "event_page", "manual",
    ] | None = None
    current_url: str | None = None
    archive_urls: list[str] | None = None
    scrapling_url: str | None = None
    known_issues: str | None = None
    requires_human_review: bool | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        return _require_http_url(value, "url") or value

    @field_validator("current_url", "scrapling_url")
    @classmethod
    def validate_helper_urls(cls, value: str | None, info: Any) -> str | None:
        return _require_http_url(value, str(info.field_name))

    @field_validator("archive_urls")
    @classmethod
    def validate_archive_urls(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        for url in value:
            if not _is_http_url(url):
                msg = f"archive_urls must contain HTTP/HTTPS URLs, got: {url}"
                raise ValueError(msg)
        return value

    @field_validator("tags", "risk_domains", "risk_focus")
    @classmethod
    def validate_lists(cls, value: list[str] | None, info: Any) -> list[str] | None:
        return _validate_optional_string_list(value, str(info.field_name))

    @model_validator(mode="after")
    def validate_type(self) -> EventEntry:
        if not self.category and not self.event_type:
            msg = "category or event_type is required"
            raise ValueError(msg)
        return self


class BenchmarkEntry(RegistryEntryModel):
    """Entry from ``benchmark_registry.yaml``.

    The current registry uses ``risk_domains`` and ``source_ids`` as the
    durable watch target shape. Direct ``url`` / ``source_url`` fields are also
    accepted for future benchmark entries.
    """

    category: str | None = None
    risk_domain: str | None = None
    risk_domains: list[str] | None = None
    url: str | None = None
    source_url: str | None = None
    source_ids: list[str] | None = None
    owner: str | None = None
    benchmark_type: str | None = None
    trigger_threshold: str | int | float | None = None
    watch_fields: list[str] | None = None
    collection_method: str | None = None
    priority: Priority | int | float | None = None
    # Helper metadata (R1-09)
    helper_type: Literal[
        "scrapling_official_page", "official_page_links", "manual",
    ] | None = None
    watch_url: str | None = None
    scrapling_url: str | None = None
    known_issues: str | None = None
    requires_human_review: bool | None = None

    @field_validator("url", "source_url", "watch_url", "scrapling_url")
    @classmethod
    def validate_urls(cls, value: str | None, info: Any) -> str | None:
        return _require_http_url(value, str(info.field_name))

    @field_validator("risk_domains", "source_ids", "watch_fields")
    @classmethod
    def validate_lists(cls, value: list[str] | None, info: Any) -> list[str] | None:
        return _validate_optional_string_list(value, str(info.field_name))

    @model_validator(mode="after")
    def validate_target_and_domain(self) -> BenchmarkEntry:
        has_domain = bool(self.category or self.risk_domain or self.risk_domains)
        if not has_domain:
            msg = "category, risk_domain, or risk_domains is required"
            raise ValueError(msg)
        has_target = bool(self.url or self.source_url or self.source_ids)
        if not has_target:
            msg = "source_url, url, or source_ids is required"
            raise ValueError(msg)
        return self


class ValidatedRegistryBundle(BaseModel):
    """Validated registry entries grouped by source modality."""

    sources: list[SourceEntry]
    podcasts: list[PodcastEntry]
    events: list[EventEntry]
    benchmarks: list[BenchmarkEntry]


def summarize_registry(bundle: RegistryBundle) -> dict[str, int]:
    """Return counts for basic smoke validation."""
    return {
        "sources": len(bundle.sources),
        "podcasts": len(bundle.podcasts),
        "events": len(bundle.events),
        "benchmarks": len(bundle.benchmarks),
    }


def _format_validation_error(registry_name: str, index: int, exc: ValidationError) -> list[str]:
    entry = f"{registry_name}[{index}]"
    messages = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error["loc"])
        messages.append(f"{entry}.{location}: {error['msg']}")
    return messages


def _validate_unique_ids(registry_name: str, entries: list[RegistryEntryModel]) -> list[str]:
    seen: set[str] = set()
    duplicate_errors: list[str] = []
    for entry in entries:
        if entry.id in seen:
            duplicate_errors.append(f"{registry_name}: duplicate id '{entry.id}'")
        seen.add(entry.id)
    return duplicate_errors


def _validate_entries(
    registry_name: str,
    raw_entries: list[dict[str, Any]],
    model: type[RegistryEntryModel],
) -> tuple[list[RegistryEntryModel], list[str]]:
    validated: list[RegistryEntryModel] = []
    errors: list[str] = []

    for index, raw_entry in enumerate(raw_entries):
        try:
            validated.append(model.model_validate(raw_entry))
        except ValidationError as exc:
            errors.extend(_format_validation_error(registry_name, index, exc))

    errors.extend(_validate_unique_ids(registry_name, validated))
    return validated, errors


def validate_registry_bundle(bundle: RegistryBundle) -> ValidatedRegistryBundle:
    """Validate all registry entries and return typed entries."""
    source_entries, source_errors = _validate_entries("sources", bundle.sources, SourceEntry)
    podcast_entries, podcast_errors = _validate_entries("podcasts", bundle.podcasts, PodcastEntry)
    event_entries, event_errors = _validate_entries("events", bundle.events, EventEntry)
    benchmark_entries, benchmark_errors = _validate_entries(
        "benchmarks", bundle.benchmarks, BenchmarkEntry
    )

    errors = source_errors + podcast_errors + event_errors + benchmark_errors
    if errors:
        raise RegistryValidationError(errors)

    return ValidatedRegistryBundle(
        sources=[entry for entry in source_entries if isinstance(entry, SourceEntry)],
        podcasts=[entry for entry in podcast_entries if isinstance(entry, PodcastEntry)],
        events=[entry for entry in event_entries if isinstance(entry, EventEntry)],
        benchmarks=[entry for entry in benchmark_entries if isinstance(entry, BenchmarkEntry)],
    )
