"""Obsidian Intelligence Vault export script.

Exports DB state (digests, signals, candidates, evidence, sources,
risk domains, entities, runs, review queue, indexes) into a structured
Obsidian vault. All reads are from local SQLite — no network, no Hermes.

Usage:
    python scripts/obsidian_export.py --latest
    python scripts/obsidian_export.py --date 2025-05-05
    python scripts/obsidian_export.py --latest --dry-run
    python scripts/obsidian_export.py --latest --json
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DRYRUN_DB_PATH = REPO_ROOT / ".local" / "risk_observer_dryrun.db"
DRYRUN_DB_URL = f"sqlite:///{DRYRUN_DB_PATH}"
DEFAULT_VAULT_PATH = REPO_ROOT / ".local" / "obsidian_vault"


def _default_vault_path() -> Path:
    """Resolve default vault path from env or standard location."""
    env_path = os.environ.get("OBSIDIAN_VAULT_PATH")
    if env_path:
        return Path(env_path)
    return DEFAULT_VAULT_PATH


def run_export(
    vault_path: Path,
    export_date: str | None = None,
    dry_run: bool = False,
    json_output: bool = False,
    open_vault: bool = False,
) -> int:
    """Run the Obsidian export. Returns exit code."""
    from frontier_ai_risk_observer.obsidian.exporter import (
        ObsidianExportConfig,
        ObsidianExporter,
    )

    # Ensure DB exists
    if not DRYRUN_DB_PATH.exists():
        print("ERROR: Dry-run DB not found. Run 'make db-init-dryrun' first.")
        return 1

    config = ObsidianExportConfig(
        vault_path=vault_path,
        export_date=export_date,
        dry_run=dry_run,
    )

    print("=== Obsidian Intelligence Vault Export ===\n")
    print(f"  Vault path: {vault_path / 'AI-Risk-Intelligence'}")
    print(f"  Export date: {export_date or 'today'}")
    print(f"  Dry run: {dry_run}")
    print()

    exporter = ObsidianExporter(config)
    summary = exporter.export()

    if json_output:
        print(json.dumps(asdict(summary), indent=2, ensure_ascii=False, default=str))
    else:
        print("Export summary:")
        print(f"  Daily notes:     {summary.daily_notes}")
        print(f"  Signal notes:    {summary.signal_notes}")
        print(f"  Candidate notes: {summary.candidate_notes}")
        print(f"  Evidence notes:  {summary.evidence_notes}")
        print(f"  Source notes:    {summary.source_notes}")
        print(f"  Risk domain notes: {summary.risk_domain_notes}")
        print(f"  Entity notes:    {summary.entity_notes}")
        print(f"  Run notes:       {summary.run_notes}")
        print(f"  Review notes:    {summary.review_notes}")
        print(f"  Index notes:     {summary.index_notes}")
        if summary.errors:
            print("\n  Errors:")
            for err in summary.errors:
                print(f"    - {err}")

    if not dry_run and open_vault:
        vault_dir = vault_path / "AI-Risk-Intelligence"
        if vault_dir.exists():
            print(f"\n  Opening vault: {vault_dir}")
            try:
                subprocess.run(["open", str(vault_dir)], check=False)  # macOS
            except FileNotFoundError:
                pass

    if summary.errors:
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export DB state to an Obsidian Intelligence Vault",
    )
    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument(
        "--latest", action="store_true",
        help="Export using today's date (default)",
    )
    date_group.add_argument(
        "--date", type=str, default=None,
        help="Export for a specific date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--vault", type=str, default=None,
        help="Vault path (default: .local/obsidian_vault or OBSIDIAN_VAULT_PATH env)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview what would be exported without writing files",
    )
    parser.add_argument(
        "--open", action="store_true",
        help="Open the vault directory after export (macOS)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output summary as JSON",
    )
    args = parser.parse_args()

    vault_path = Path(args.vault) if args.vault else _default_vault_path()
    export_date = args.date  # None means "today" in the exporter

    # Set DATABASE_URL for the session factory
    os.environ.setdefault("DATABASE_URL", DRYRUN_DB_URL)

    sys.exit(run_export(
        vault_path=vault_path,
        export_date=export_date,
        dry_run=args.dry_run,
        json_output=args.json,
        open_vault=args.open,
    ))


if __name__ == "__main__":
    main()
