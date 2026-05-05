import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from frontier_ai_risk_observer.registry.loader import (
    RegistryFileMissingError,
    RegistryYamlError,
    load_registry_bundle,
)
from frontier_ai_risk_observer.registry.validators import (
    RegistryValidationError,
    summarize_registry,
    validate_registry_bundle,
)


def test_registry_yaml_files_load() -> None:
    bundle = load_registry_bundle(Path("source_registry"))
    summary = summarize_registry(bundle)

    assert summary["sources"] > 0
    assert summary["podcasts"] > 0
    assert summary["events"] > 0
    assert summary["benchmarks"] > 0


def test_current_registry_files_pass_validation() -> None:
    bundle = load_registry_bundle(Path("source_registry"))
    validated = validate_registry_bundle(bundle)

    assert len(validated.sources) == len(bundle.sources)
    assert len(validated.podcasts) == len(bundle.podcasts)
    assert len(validated.events) == len(bundle.events)
    assert len(validated.benchmarks) == len(bundle.benchmarks)


def test_loader_reports_missing_registry_file(tmp_path: Path) -> None:
    with pytest.raises(RegistryFileMissingError, match="Missing registry file"):
        load_registry_bundle(tmp_path)


def test_loader_reports_invalid_yaml(tmp_path: Path) -> None:
    _write_registry_dir(tmp_path)
    (tmp_path / "sources.yaml").write_text("sources: [", encoding="utf-8")

    with pytest.raises(RegistryYamlError, match="Invalid YAML"):
        load_registry_bundle(tmp_path)


def test_duplicate_ids_fail_with_useful_error(tmp_path: Path) -> None:
    _write_registry_dir(
        tmp_path,
        sources=[
            _source(id="duplicate"),
            _source(id="duplicate", url="https://example.org/other"),
        ],
    )

    with pytest.raises(RegistryValidationError, match="duplicate id 'duplicate'"):
        validate_registry_bundle(load_registry_bundle(tmp_path))


def test_missing_required_fields_fail_with_useful_error(tmp_path: Path) -> None:
    broken = _source()
    broken.pop("name")
    _write_registry_dir(tmp_path, sources=[broken])

    with pytest.raises(RegistryValidationError, match="sources\\[0\\].name"):
        validate_registry_bundle(load_registry_bundle(tmp_path))


def test_invalid_url_fields_fail(tmp_path: Path) -> None:
    _write_registry_dir(tmp_path, podcasts=[_podcast(url="not-a-url")])

    with pytest.raises(RegistryValidationError, match="podcasts\\[0\\].url"):
        validate_registry_bundle(load_registry_bundle(tmp_path))


def test_disabled_entries_are_accepted(tmp_path: Path) -> None:
    _write_registry_dir(tmp_path, sources=[_source(enabled=False)])

    validated = validate_registry_bundle(load_registry_bundle(tmp_path))

    assert validated.sources[0].enabled is False


def test_cli_validation_succeeds_on_current_registry_files() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/validate_registries.py"],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0
    assert "Registry validation passed" in result.stdout


def _write_registry_dir(
    base: Path,
    *,
    sources: list[dict[str, object]] | None = None,
    podcasts: list[dict[str, object]] | None = None,
    events: list[dict[str, object]] | None = None,
    benchmarks: list[dict[str, object]] | None = None,
) -> None:
    files = {
        "sources.yaml": {"version": 1, "sources": sources or [_source()]},
        "podcasts.yaml": {"version": 1, "podcasts": podcasts or [_podcast()]},
        "events.yaml": {"version": 1, "events": events or [_event()]},
        "benchmark_registry.yaml": {"version": 1, "benchmarks": benchmarks or [_benchmark()]},
    }
    for filename, payload in files.items():
        (base / filename).write_text(yaml.safe_dump(payload), encoding="utf-8")


def _source(
    *,
    id: str = "source_one",
    url: str = "https://example.com/source",
    enabled: bool = True,
) -> dict[str, object]:
    return {
        "id": id,
        "name": "Source One",
        "category": "frontier_ai_lab",
        "url": url,
        "collector": "web_index",
        "priority": "high",
        "enabled": enabled,
    }


def _podcast(url: str = "https://example.com/podcast") -> dict[str, object]:
    return {
        "id": "podcast_one",
        "name": "Podcast One",
        "url": url,
        "collector": "podcast_feed",
        "enabled": True,
    }


def _event() -> dict[str, object]:
    return {
        "id": "event_one",
        "name": "Event One",
        "category": "conference",
        "url": "https://example.com/event",
        "enabled": True,
    }


def _benchmark() -> dict[str, object]:
    return {
        "id": "benchmark_one",
        "name": "Benchmark One",
        "risk_domains": ["autonomy"],
        "source_ids": ["source_one"],
        "enabled": True,
    }
