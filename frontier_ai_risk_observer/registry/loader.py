"""YAML source registry loader."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from yaml import YAMLError

from frontier_ai_risk_observer.core.config import get_settings


@dataclass(frozen=True)
class RegistryBundle:
    """Parsed registry files grouped by source modality."""

    sources: list[dict[str, Any]]
    podcasts: list[dict[str, Any]]
    events: list[dict[str, Any]]
    benchmarks: list[dict[str, Any]]


class RegistryError(RuntimeError):
    """Base class for registry loading errors."""


class RegistryFileMissingError(RegistryError):
    """Raised when an expected registry file is missing."""


class RegistryYamlError(RegistryError):
    """Raised when a registry file cannot be parsed as YAML."""


class RegistryShapeError(RegistryError):
    """Raised when a registry YAML file has an unexpected top-level shape."""


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        msg = f"Missing registry file: {path}"
        raise RegistryFileMissingError(msg)
    try:
        with path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}
    except YAMLError as exc:
        msg = f"Invalid YAML in registry file {path}: {exc}"
        raise RegistryYamlError(msg) from exc
    if not isinstance(loaded, dict):
        msg = f"Registry file must contain a mapping: {path}"
        raise RegistryShapeError(msg)
    return loaded


def _require_entry_list(raw: dict[str, Any], key: str, path: Path) -> list[dict[str, Any]]:
    entries = raw.get(key, [])
    if not isinstance(entries, list):
        msg = f"Registry key '{key}' must contain a list in {path}"
        raise RegistryShapeError(msg)
    if not all(isinstance(entry, dict) for entry in entries):
        msg = f"Registry key '{key}' must contain only mappings in {path}"
        raise RegistryShapeError(msg)
    return entries


def load_registry_bundle(registry_dir: Path | None = None) -> RegistryBundle:
    """Load all first-class source registry YAML files as raw dictionaries."""
    base_dir = registry_dir or get_settings().source_registry_dir
    sources_path = base_dir / "sources.yaml"
    podcasts_path = base_dir / "podcasts.yaml"
    events_path = base_dir / "events.yaml"
    benchmarks_path = base_dir / "benchmark_registry.yaml"

    sources = _load_yaml(sources_path)
    podcasts = _load_yaml(podcasts_path)
    events = _load_yaml(events_path)
    benchmarks = _load_yaml(benchmarks_path)

    return RegistryBundle(
        sources=_require_entry_list(sources, "sources", sources_path),
        podcasts=_require_entry_list(podcasts, "podcasts", podcasts_path),
        events=_require_entry_list(events, "events", events_path),
        benchmarks=_require_entry_list(benchmarks, "benchmarks", benchmarks_path),
    )


def load_validated_registry_bundle(registry_dir: Path | None = None) -> object:
    """Load and validate all first-class registry files."""
    from frontier_ai_risk_observer.registry.validators import validate_registry_bundle

    return validate_registry_bundle(load_registry_bundle(registry_dir))
