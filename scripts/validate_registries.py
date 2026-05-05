"""Validate AI risk observer registry YAML files."""

from __future__ import annotations

import argparse
from pathlib import Path

from frontier_ai_risk_observer.registry.loader import RegistryError, load_registry_bundle
from frontier_ai_risk_observer.registry.validators import (
    RegistryValidationError,
    summarize_registry,
    validate_registry_bundle,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "registry_dir",
        nargs="?",
        default="source_registry",
        help=(
            "Directory containing sources.yaml, podcasts.yaml, events.yaml, "
            "and benchmark_registry.yaml."
        ),
    )
    return parser


def main() -> int:
    """CLI entrypoint."""
    args = build_parser().parse_args()
    registry_dir = Path(args.registry_dir)

    try:
        bundle = load_registry_bundle(registry_dir)
        validated = validate_registry_bundle(bundle)
    except (RegistryError, RegistryValidationError) as exc:
        print("Registry validation failed:")
        print(exc)
        return 1

    summary = summarize_registry(bundle)
    enabled_counts = {
        "sources": sum(1 for entry in validated.sources if entry.enabled),
        "podcasts": sum(1 for entry in validated.podcasts if entry.enabled),
        "events": sum(1 for entry in validated.events if entry.enabled),
        "benchmarks": sum(1 for entry in validated.benchmarks if entry.enabled),
    }
    print(
        "Registry validation passed: "
        f"{summary['sources']} sources ({enabled_counts['sources']} enabled), "
        f"{summary['podcasts']} podcasts ({enabled_counts['podcasts']} enabled), "
        f"{summary['events']} events ({enabled_counts['events']} enabled), "
        f"{summary['benchmarks']} benchmarks ({enabled_counts['benchmarks']} enabled)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
