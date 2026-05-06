"""Inspect an Obsidian Intelligence Vault export.

Reads the vault directory and reports note counts, content checks,
and structural validation. No network, no DB, no Hermes required.

Usage:
    python scripts/inspect_obsidian_export.py --vault .local/obsidian_vault
    python scripts/inspect_obsidian_export.py --latest
    python scripts/inspect_obsidian_export.py --vault .local/obsidian_vault --json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_VAULT_PATH = REPO_ROOT / ".local" / "obsidian_vault"

BEGIN_MARKER = "<!-- BEGIN_AUTO_GENERATED: hermes-ai-risk-observer -->"
END_MARKER = "<!-- END_AUTO_GENERATED: hermes-ai-risk-observer -->"


@dataclass
class VaultInspection:
    """Result of inspecting an Obsidian vault export."""

    vault_root: str = ""
    daily_notes: int = 0
    signal_notes: int = 0
    candidate_notes: int = 0
    evidence_notes: int = 0
    source_notes: int = 0
    risk_domain_notes: int = 0
    entity_notes: int = 0
    run_notes: int = 0
    review_notes: int = 0
    index_notes: int = 0
    latest_daily_path: str = ""
    daily_links_to_signals: bool = False
    signal_has_what_changed: bool = False
    signal_has_why_it_matters: bool = False
    signal_has_what_to_watch: bool = False
    signal_has_evidence: bool = False
    evidence_notes_exist: bool = False
    failed_sources_exists: bool = False
    failed_sources_non_empty: bool = False
    generated_markers_present: bool = False
    signals_without_evidence: int = 0
    errors: list[str] = field(default_factory=list)


def _count_md_files(directory: Path) -> int:
    """Count .md files in a directory."""
    if not directory.exists():
        return 0
    return len(list(directory.glob("*.md")))


def _latest_md(directory: Path) -> Path | None:
    """Find the most recently modified .md file in a directory."""
    if not directory.exists():
        return None
    files = sorted(directory.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def _read_note(path: Path) -> str:
    """Read a note file safely."""
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _check_signal_fields(content: str) -> dict[str, bool]:
    """Check if signal note content includes three-question fields."""
    return {
        "what_changed": bool(re.search(r"What Changed", content, re.IGNORECASE)),
        "why_it_matters": bool(re.search(r"Why It Matters", content, re.IGNORECASE)),
        "what_to_watch": bool(re.search(r"What to Watch", content, re.IGNORECASE)),
        "has_evidence": bool(
            re.search(r"Evidence URL", content, re.IGNORECASE)
            or re.search(r"evidence_url", content, re.IGNORECASE)
        ),
    }


def inspect_vault(vault_path: Path) -> VaultInspection:
    """Inspect an Obsidian vault and return structural analysis."""
    vault = vault_path / "AI-Risk-Intelligence"
    result = VaultInspection(vault_root=str(vault))

    if not vault.exists():
        result.errors.append(f"Vault not found: {vault}")
        return result

    # Count notes by directory
    result.daily_notes = _count_md_files(vault / "00_Daily")
    result.signal_notes = _count_md_files(vault / "01_Signals")
    result.candidate_notes = _count_md_files(vault / "02_Candidates")
    result.evidence_notes = _count_md_files(vault / "03_Evidence")
    result.source_notes = _count_md_files(vault / "04_Sources")
    result.risk_domain_notes = _count_md_files(vault / "05_Risk_Domains")
    result.entity_notes = _count_md_files(vault / "06_Entities")
    result.run_notes = _count_md_files(vault / "07_Runs")
    result.review_notes = _count_md_files(vault / "90_Review_Queue")
    result.index_notes = _count_md_files(vault / "99_Indexes")

    # Latest daily note
    latest_daily = _latest_md(vault / "00_Daily")
    if latest_daily:
        result.latest_daily_path = str(latest_daily)
        daily_content = _read_note(latest_daily)

        # Check if daily note links to signals
        result.daily_links_to_signals = bool(
            re.search(r"\[\[.*Signal", daily_content)
            or re.search(r"Signal Index", daily_content)
        )

        # Check for generated block markers
        result.generated_markers_present = (
            BEGIN_MARKER in daily_content and END_MARKER in daily_content
        )

    # Check signal notes for three-question fields
    signals_dir = vault / "01_Signals"
    if signals_dir.exists():
        signal_files = list(signals_dir.glob("*.md"))
        if signal_files:
            # Check first signal note
            sample_content = _read_note(signal_files[0])
            fields = _check_signal_fields(sample_content)
            result.signal_has_what_changed = fields["what_changed"]
            result.signal_has_why_it_matters = fields["why_it_matters"]
            result.signal_has_what_to_watch = fields["what_to_watch"]
            result.signal_has_evidence = fields["has_evidence"]

            # Count signals without evidence
            signals_without = 0
            for sf in signal_files:
                content = _read_note(sf)
                if not re.search(r"Evidence URL", content, re.IGNORECASE):
                    signals_without += 1
            result.signals_without_evidence = signals_without

    # Check evidence notes
    result.evidence_notes_exist = result.evidence_notes > 0

    # Check failed-sources.md
    failed_path = vault / "90_Review_Queue" / "failed-sources.md"
    result.failed_sources_exists = failed_path.exists()
    if result.failed_sources_exists:
        content = _read_note(failed_path)
        result.failed_sources_non_empty = bool(
            content.strip() and "No failed sources" not in content
        )

    return result


def _print_inspection(result: VaultInspection) -> None:
    """Print human-readable inspection results."""
    print("=== Obsidian Vault Inspection ===\n")
    print(f"  Vault root: {result.vault_root}\n")
    print("  Note counts:")
    print(f"    Daily notes:       {result.daily_notes}")
    print(f"    Signal notes:      {result.signal_notes}")
    print(f"    Candidate notes:   {result.candidate_notes}")
    print(f"    Evidence notes:    {result.evidence_notes}")
    print(f"    Source notes:      {result.source_notes}")
    print(f"    Risk domain notes: {result.risk_domain_notes}")
    print(f"    Entity notes:      {result.entity_notes}")
    print(f"    Run notes:         {result.run_notes}")
    print(f"    Review notes:      {result.review_notes}")
    print(f"    Index notes:       {result.index_notes}")
    print()
    print(f"  Latest daily note: {result.latest_daily_path or '(none)'}")
    print(f"  Daily links to signals: {result.daily_links_to_signals}")
    print(f"  Generated markers present: {result.generated_markers_present}")
    print()
    print("  Signal quality:")
    print(f"    Has 'What Changed?': {result.signal_has_what_changed}")
    print(f"    Has 'Why It Matters?': {result.signal_has_why_it_matters}")
    print(f"    Has 'What to Watch Next?': {result.signal_has_what_to_watch}")
    print(f"    Has evidence: {result.signal_has_evidence}")
    print(f"    Signals without evidence: {result.signals_without_evidence}")
    print()
    print("  Evidence:")
    print(f"    Evidence notes exist: {result.evidence_notes_exist}")
    print()
    print("  Review queue:")
    print(f"    failed-sources.md exists: {result.failed_sources_exists}")
    print(f"    failed-sources.md non-empty: {result.failed_sources_non_empty}")

    if result.errors:
        print()
        print("  Errors:")
        for err in result.errors:
            print(f"    - {err}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect an Obsidian Intelligence Vault export",
    )
    parser.add_argument(
        "--vault", type=str, default=None,
        help="Vault base path (containing AI-Risk-Intelligence/)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output inspection results as JSON",
    )
    parser.add_argument(
        "--date", type=str, default=None,
        help="Filter by date (YYYY-MM-DD) — currently informational",
    )
    parser.add_argument(
        "--latest", action="store_true",
        help="Use default vault path",
    )
    args = parser.parse_args()

    if args.vault:
        vault_path = Path(args.vault)
    else:
        env_path = os.environ.get("OBSIDIAN_VAULT_PATH")
        if env_path:
            vault_path = Path(env_path)
        else:
            vault_path = DEFAULT_VAULT_PATH

    result = inspect_vault(vault_path)

    if args.json:
        print(json.dumps(asdict(result), indent=2, ensure_ascii=False, default=str))
    else:
        _print_inspection(result)

    if result.errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
