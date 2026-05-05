"""Service helpers for validated registry access."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal

from pydantic import BaseModel

from frontier_ai_risk_observer.registry.loader import load_registry_bundle
from frontier_ai_risk_observer.registry.validators import (
    BenchmarkEntry,
    EventEntry,
    PodcastEntry,
    SourceEntry,
    ValidatedRegistryBundle,
    summarize_registry,
    validate_registry_bundle,
)

RegistryKind = Literal["source", "podcast", "event", "benchmark"]
RegistryEntry = SourceEntry | PodcastEntry | EventEntry | BenchmarkEntry

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def load_validated_registry() -> ValidatedRegistryBundle:
    """Load and validate the configured registry files."""
    return validate_registry_bundle(load_registry_bundle())


def registry_summary() -> dict[str, int]:
    """Return registry group counts."""
    return summarize_registry(load_registry_bundle())


def model_to_dict(entry: BaseModel, kind: RegistryKind | None = None) -> dict[str, Any]:
    """Return a JSON-friendly registry entry."""
    payload = entry.model_dump(mode="json")
    if kind is not None:
        payload["kind"] = kind
    return payload


def list_sources(
    *,
    enabled: bool | None = None,
    category: str | None = None,
    priority: str | None = None,
    risk_domain: str | None = None,
) -> list[dict[str, Any]]:
    """List validated source registry entries."""
    entries = load_validated_registry().sources
    filtered = [
        entry
        for entry in entries
        if _matches_common(entry, enabled=enabled, priority=priority, risk_domain=risk_domain)
        and (category is None or entry.category == category)
    ]
    return [model_to_dict(entry, "source") for entry in filtered]


def get_source(source_id: str) -> dict[str, Any] | None:
    """Return one source entry by ID."""
    for entry in load_validated_registry().sources:
        if entry.id == source_id:
            return model_to_dict(entry, "source")
    return None


def list_podcasts(
    *,
    enabled: bool | None = None,
    priority: str | None = None,
    risk_domain: str | None = None,
) -> list[dict[str, Any]]:
    """List validated podcast registry entries."""
    return [
        model_to_dict(entry, "podcast")
        for entry in load_validated_registry().podcasts
        if _matches_common(entry, enabled=enabled, priority=priority, risk_domain=risk_domain)
    ]


def list_events(
    *,
    enabled: bool | None = None,
    category: str | None = None,
    event_type: str | None = None,
    risk_domain: str | None = None,
) -> list[dict[str, Any]]:
    """List validated event registry entries."""
    entries = load_validated_registry().events
    filtered = [
        entry
        for entry in entries
        if _matches_common(entry, enabled=enabled, risk_domain=risk_domain)
        and (category is None or entry.category == category)
        and (event_type is None or entry.event_type == event_type)
    ]
    return [model_to_dict(entry, "event") for entry in filtered]


def list_benchmarks(
    *,
    enabled: bool | None = None,
    risk_domain: str | None = None,
    priority: str | None = None,
) -> list[dict[str, Any]]:
    """List validated benchmark/framework watch entries."""
    return [
        model_to_dict(entry, "benchmark")
        for entry in load_validated_registry().benchmarks
        if _matches_common(entry, enabled=enabled, priority=priority, risk_domain=risk_domain)
    ]


def list_due_sources(
    *,
    limit: int | None = None,
    kind: RegistryKind | None = None,
    risk_domain: str | None = None,
) -> list[dict[str, Any]]:
    """Return enabled entries Hermes should consider for a daily run."""
    registry = load_validated_registry()
    entries: list[tuple[RegistryKind, RegistryEntry]] = []
    if kind in (None, "source"):
        entries.extend(("source", entry) for entry in registry.sources)
    if kind in (None, "podcast"):
        entries.extend(("podcast", entry) for entry in registry.podcasts)
    if kind in (None, "event"):
        entries.extend(("event", entry) for entry in registry.events)
    if kind in (None, "benchmark"):
        entries.extend(("benchmark", entry) for entry in registry.benchmarks)

    filtered = [
        (entry_kind, entry)
        for entry_kind, entry in entries
        if entry.enabled and _has_risk_domain(entry, risk_domain)
    ]
    filtered.sort(key=lambda item: (_priority_rank(getattr(item[1], "priority", None)), item[1].id))
    if limit is not None:
        filtered = filtered[:limit]
    return [model_to_dict(entry, entry_kind) for entry_kind, entry in filtered]


def find_registry_entry(source_id: str) -> tuple[RegistryKind, dict[str, Any]] | None:
    """Find an entry in any registry group by ID."""
    registry = load_validated_registry()
    groups: list[tuple[RegistryKind, Sequence[RegistryEntry]]] = [
        ("source", registry.sources),
        ("podcast", registry.podcasts),
        ("event", registry.events),
        ("benchmark", registry.benchmarks),
    ]
    for kind, entries in groups:
        for entry in entries:
            if entry.id == source_id:
                return kind, model_to_dict(entry, kind)
    return None


def _matches_common(
    entry: SourceEntry | PodcastEntry | EventEntry | BenchmarkEntry,
    *,
    enabled: bool | None = None,
    priority: str | None = None,
    risk_domain: str | None = None,
) -> bool:
    if enabled is not None and entry.enabled is not enabled:
        return False
    if priority is not None and str(getattr(entry, "priority", "")) != priority:
        return False
    return _has_risk_domain(entry, risk_domain)


def _has_risk_domain(
    entry: SourceEntry | PodcastEntry | EventEntry | BenchmarkEntry,
    risk_domain: str | None,
) -> bool:
    if risk_domain is None:
        return True
    domains = getattr(entry, "risk_domains", None) or getattr(entry, "risk_focus", None) or []
    return risk_domain in domains


def _priority_rank(priority: object) -> int:
    if isinstance(priority, int | float):
        return int(priority)
    return PRIORITY_ORDER.get(str(priority), 99)
