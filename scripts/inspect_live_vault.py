"""Inspect the live Obsidian vault research run directory.

Reports note counts, timeline entries, failures, DB event linkage,
and structural validation. No network, no Hermes required.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class LiveRunInspection:
    """Inspection result for a live vault run directory."""

    run_dir: str = ""
    run_id: str = ""
    source_notes: int = 0
    candidate_notes: int = 0
    evidence_notes: int = 0
    signal_notes: int = 0
    failures_count: int = 0
    timeline_exists: bool = False
    log_exists: bool = False
    failures_exists: bool = False
    finalized: bool = False
    generated_markers_present: bool = False
    event_type_counts: dict[str, int] = field(default_factory=dict)
    cot_violations: list[str] = field(default_factory=list)
    missing_note_types: list[str] = field(default_factory=list)
    db_event_count: int = 0
    db_event_type_counts: dict[str, int] = field(default_factory=dict)
    db_mismatch: bool = False
    errors: list[str] = field(default_factory=list)
    # R1-13C: daily note and bidirectional link checks
    daily_note_exists: bool = False
    daily_note_has_body: bool = False
    daily_note_links_to_live_run: bool = False
    live_run_links_to_daily: bool = False
    manual_export_required: bool = True
    bidirectional_links_complete: bool = False
    review_queue_count: int = 0
    warnings: list[str] = field(default_factory=list)


@dataclass
class LiveVaultInspection:
    """Inspection result for the full live vault."""

    vault_root: str = ""
    runs_dir_name: str = "08_Live_Runs"
    run_count: int = 0
    latest_run_id: str = ""
    runs: list[LiveRunInspection] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# Chain-of-thought phrases that must NOT appear in live notes
_COT_PHRASES = [
    "chain of thought",
    "hidden reasoning",
    "private reasoning",
    "inner monologue",
    "private thoughts",
    "思维链",
    "内心独白",
    "隐含推理",
]


def _check_cot_violations(content: str) -> list[str]:
    """Check for chain-of-thought phrases in note content."""
    lower = content.lower()
    return [p for p in _COT_PHRASES if p in lower]


def inspect_live_run(
    run_path: Path,
    runs_dir_name: str = "08_Live_Runs",
    db_path: Path | None = None,
) -> LiveRunInspection:
    """Inspect a single live run directory."""
    result = LiveRunInspection(
        run_dir=str(run_path),
        run_id=run_path.name,
    )

    if not run_path.exists():
        result.errors.append(f"Run directory not found: {run_path}")
        return result

    # Count notes per subdirectory
    note_type_map = {
        "Sources": ("source_notes", "source"),
        "Candidates": ("candidate_notes", "candidate"),
        "Evidence": ("evidence_notes", "evidence"),
        "Signals": ("signal_notes", "signal"),
    }
    for subdir_name, (count_field, note_type) in note_type_map.items():
        subdir = run_path / subdir_name
        if subdir.exists():
            count = len(list(subdir.glob("*.md")))
            setattr(result, count_field, count)
            result.event_type_counts[note_type] = count

    # Check key files
    log_path = run_path / "Live Research Log.md"
    result.log_exists = log_path.exists()
    if result.log_exists:
        content = log_path.read_text(encoding="utf-8")
        result.finalized = "status: completed" in content
        result.generated_markers_present = "BEGIN_AUTO_GENERATED" in content
        result.cot_violations.extend(_check_cot_violations(content))

    timeline_path = run_path / "Timeline.md"
    result.timeline_exists = timeline_path.exists()
    if result.timeline_exists:
        content = timeline_path.read_text(encoding="utf-8")
        result.cot_violations.extend(_check_cot_violations(content))

    failures_path = run_path / "Failures.md"
    result.failures_exists = failures_path.exists()
    if result.failures_exists:
        content = failures_path.read_text(encoding="utf-8")
        result.failures_count = sum(
            1 for line in content.split("\n") if line.startswith("- **")
        )
        result.cot_violations.extend(_check_cot_violations(content))

    # Check for missing expected note types
    for note_type in ["source", "candidate", "evidence", "signal"]:
        if result.event_type_counts.get(note_type, 0) == 0:
            result.missing_note_types.append(note_type)

    # Check DB events if db_path provided
    if db_path and db_path.exists():
        try:
            result.db_event_count, result.db_event_type_counts, result.db_mismatch = (
                _check_db_events(db_path, result.run_id, result.event_type_counts)
            )
        except Exception as exc:
            result.errors.append(f"DB check failed: {exc}")

    # Deduplicate COT violations
    result.cot_violations = list(set(result.cot_violations))

    # R1-13C: Daily note and bidirectional link checks
    _check_daily_note_and_links(run_path, result)

    # Review queue count
    _check_review_queue(run_path, result)

    # Warnings for UX issues
    _compute_ux_warnings(result)

    return result


def _check_daily_note_and_links(
    run_path: Path,
    result: LiveRunInspection,
) -> None:
    """Check daily note existence, body content, and bidirectional links."""
    # Find the vault AI-Risk-Intelligence root
    # run_path is like vault/AI-Risk-Intelligence/08_Live_Runs/YYYY-MM-DD_HHMMSS
    ai_root = run_path.parent.parent
    run_id = run_path.name

    # Extract date from run_id (format: YYYY-MM-DD_HHMMSS)
    date_part = run_id.split("_")[0] if "_" in run_id else ""
    if not date_part:
        return

    daily_path = ai_root / "00_Daily" / f"{date_part}.md"
    result.daily_note_exists = daily_path.exists()

    if not result.daily_note_exists:
        return

    content = daily_path.read_text(encoding="utf-8")

    # Check if daily note has body inside generated markers
    begin_marker = "<!-- BEGIN_AUTO_GENERATED: hermes-ai-risk-observer -->"
    end_marker = "<!-- END_AUTO_GENERATED: hermes-ai-risk-observer -->"
    if begin_marker in content and end_marker in content:
        start = content.index(begin_marker) + len(begin_marker)
        end = content.index(end_marker)
        body = content[start:end].strip()
        result.daily_note_has_body = len(body) > 0
    else:
        # Has content but no markers — might be from manual export
        result.daily_note_has_body = len(content.strip()) > 100

    # Check if daily note links to this live run
    result.daily_note_links_to_live_run = run_id in content

    # Check if live run links back to daily note
    log_path = run_path / "Live Research Log.md"
    if log_path.exists():
        log_content = log_path.read_text(encoding="utf-8")
        result.live_run_links_to_daily = (
            date_part in log_content
            or f"00_Daily/{date_part}" in log_content
        )

    # Compute manual_export_required
    result.manual_export_required = not result.daily_note_has_body

    # Check bidirectional link completeness
    _check_bidirectional_links(run_path, result, ai_root, date_part)


def _check_bidirectional_links(
    run_path: Path,
    result: LiveRunInspection,
    ai_root: Path,
    date_part: str,
) -> None:
    """Check if intermediate notes have proper bidirectional links."""
    all_linked = True

    # Check signal notes for links sections
    signals_dir = run_path / "Signals"
    if signals_dir.exists():
        for note in signals_dir.glob("*.md"):
            content = note.read_text(encoding="utf-8")
            if "## Links" not in content:
                all_linked = False
                break

    # Check evidence notes
    evidence_dir = run_path / "Evidence"
    if evidence_dir.exists():
        for note in evidence_dir.glob("*.md"):
            content = note.read_text(encoding="utf-8")
            if "## Links" not in content:
                all_linked = False
                break

    # Check candidate notes
    candidates_dir = run_path / "Candidates"
    if candidates_dir.exists():
        for note in candidates_dir.glob("*.md"):
            content = note.read_text(encoding="utf-8")
            if "## Links" not in content:
                all_linked = False
                break

    result.bidirectional_links_complete = all_linked


def _check_review_queue(
    run_path: Path,
    result: LiveRunInspection,
) -> None:
    """Check review queue entries."""
    ai_root = run_path.parent.parent
    queue_dir = ai_root / "90_Review_Queue"
    if not queue_dir.exists():
        return

    count = 0
    for queue_file in queue_dir.glob("*.md"):
        content = queue_file.read_text(encoding="utf-8")
        # Count list items
        for line in content.split("\n"):
            if line.startswith("- **"):
                count += 1
    result.review_queue_count = count


def _compute_ux_warnings(result: LiveRunInspection) -> None:
    """Compute UX warnings based on inspection results."""
    if result.log_exists and not result.daily_note_exists:
        result.warnings.append("Live run exists but no daily note")
    if result.daily_note_exists and not result.daily_note_has_body:
        result.warnings.append("Daily note has only metadata, no report body")
    if result.signal_notes > 0 and result.evidence_notes == 0:
        result.warnings.append("Signal notes exist but no evidence notes")
    if result.failures_count > 0 and result.review_queue_count == 0:
        result.warnings.append("Failures exist but absent from review queue")


def _check_db_events(
    db_path: Path,
    run_id: str,
    vault_counts: dict[str, int],
) -> tuple[int, dict[str, int], bool]:
    """Check ResearchEvent rows for a run_id in SQLite."""
    import sqlite3

    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*), event_type FROM research_events "
            "WHERE run_id = ? GROUP BY event_type",
            (run_id,),
        )
        type_counts = {}
        total = 0
        for count, etype in cur.fetchall():
            type_counts[etype] = count
            total += count

        # Check mismatch: if DB has events but vault has no corresponding notes
        mismatch = False
        for note_type in ["source", "candidate", "evidence", "signal"]:
            db_count = type_counts.get(f"{note_type}_note_upserted", 0)
            vault_count = vault_counts.get(note_type, 0)
            if db_count > 0 and vault_count == 0:
                mismatch = True
                break

        return total, type_counts, mismatch
    finally:
        conn.close()


def inspect_live_vault(
    vault_path: Path,
    db_path: Path | None = None,
) -> LiveVaultInspection:
    """Inspect the live vault's runs directory."""
    runs_dir_name = os.environ.get("OBSIDIAN_LIVE_RUNS_DIR", "08_Live_Runs")
    result = LiveVaultInspection(
        vault_root=str(vault_path),
        runs_dir_name=runs_dir_name,
    )

    live_runs_dir = vault_path / "AI-Risk-Intelligence" / runs_dir_name
    if not live_runs_dir.exists():
        result.errors.append(f"{runs_dir_name} directory not found")
        return result

    run_dirs = sorted(
        [d for d in live_runs_dir.iterdir() if d.is_dir()],
        reverse=True,
    )
    result.run_count = len(run_dirs)

    if run_dirs:
        result.latest_run_id = run_dirs[0].name

    for run_dir in run_dirs:
        run_inspection = inspect_live_run(run_dir, runs_dir_name, db_path)
        result.runs.append(run_inspection)

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect live Obsidian vault research runs",
    )
    parser.add_argument(
        "--vault", type=str, default=None,
        help="Vault base path (containing AI-Risk-Intelligence/)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output inspection as JSON",
    )
    parser.add_argument(
        "--run-id", type=str, default=None,
        help="Inspect a specific run ID",
    )
    parser.add_argument(
        "--latest", action="store_true",
        help="Inspect the latest live run only",
    )
    parser.add_argument(
        "--require-events", type=int, default=None,
        help="Fail if event count is less than N",
    )
    parser.add_argument(
        "--require-finalized", action="store_true",
        help="Fail if the run is not finalized",
    )
    parser.add_argument(
        "--require-note-types", type=str, default=None,
        help="Comma-separated note types that must have >0 notes "
             "(e.g. source,candidate,evidence,signal)",
    )
    parser.add_argument(
        "--db-check", action="store_true",
        help="Also check ResearchEvent rows in SQLite DB",
    )
    parser.add_argument(
        "--require-daily-note", action="store_true",
        help="Fail if daily note does not exist for the run date",
    )
    parser.add_argument(
        "--require-daily-body", action="store_true",
        help="Fail if daily note exists but has no report body",
    )
    args = parser.parse_args()

    vault_str = args.vault or os.environ.get(
        "OBSIDIAN_VAULT_PATH", ".local/obsidian_vault"
    )
    vault_path = Path(vault_str)

    # Determine DB path
    db_path: Path | None = None
    if args.db_check:
        repo_root = Path(__file__).resolve().parent.parent
        db_path = repo_root / ".local" / "risk_observer_dryrun.db"
        if not db_path.exists():
            db_path = None

    # Single run inspection
    if args.run_id:
        runs_dir_name = os.environ.get("OBSIDIAN_LIVE_RUNS_DIR", "08_Live_Runs")
        run_path = (
            vault_path / "AI-Risk-Intelligence" / runs_dir_name / args.run_id
        )
        inspection = inspect_live_run(run_path, runs_dir_name, db_path)
        _print_run(inspection, args.json)
        _check_requirements(inspection, args)
        return

    # Full vault inspection
    full_inspection = inspect_live_vault(vault_path, db_path)

    # --latest: only show the latest run
    if args.latest and full_inspection.runs:
        latest = full_inspection.runs[0]
        _print_run(latest, args.json)
        _check_requirements(latest, args)
        return

    if args.json:
        print(json.dumps(asdict(full_inspection), indent=2, ensure_ascii=False))
    else:
        print("=== Live Vault Inspection ===\n")
        print(f"  Vault root: {full_inspection.vault_root}")
        print(f"  Run count:  {full_inspection.run_count}")
        print(f"  Latest run: {full_inspection.latest_run_id or '(none)'}")
        for run in full_inspection.runs:
            _print_run(run, args.json)

    # Check requirements against latest run
    if full_inspection.runs:
        _check_requirements(full_inspection.runs[0], args)


def _print_run(inspection: LiveRunInspection, json_mode: bool) -> None:
    """Print a single run's inspection results."""
    if json_mode:
        print(json.dumps(asdict(inspection), indent=2, ensure_ascii=False))
        return

    print(f"\n  Run: {inspection.run_id}")
    print(f"    Path: {inspection.run_dir}")
    print(f"    Sources: {inspection.source_notes}  Candidates: {inspection.candidate_notes}")
    print(f"    Evidence: {inspection.evidence_notes}  Signals: {inspection.signal_notes}")
    print(f"    Failures: {inspection.failures_count}  Finalized: {inspection.finalized}")
    print(f"    Markers: {inspection.generated_markers_present}")
    print(f"    Daily note exists: {inspection.daily_note_exists}")
    print(f"    Daily note has body: {inspection.daily_note_has_body}")
    print(f"    Daily→Live link: {inspection.daily_note_links_to_live_run}")
    print(f"    Live→Daily link: {inspection.live_run_links_to_daily}")
    print(f"    Bidirectional links complete: {inspection.bidirectional_links_complete}")
    print(f"    Manual export required: {inspection.manual_export_required}")
    print(f"    Review queue items: {inspection.review_queue_count}")
    if inspection.event_type_counts:
        print(f"    Note type counts: {inspection.event_type_counts}")
    if inspection.db_event_count > 0:
        print(f"    DB events: {inspection.db_event_count}")
        print(f"    DB event types: {inspection.db_event_type_counts}")
        if inspection.db_mismatch:
            print("    WARNING: DB/vault mismatch detected")
    if inspection.cot_violations:
        print(f"    COT VIOLATIONS: {inspection.cot_violations}")
    if inspection.missing_note_types:
        print(f"    Missing note types: {inspection.missing_note_types}")
    if inspection.warnings:
        print(f"    UX WARNINGS: {inspection.warnings}")
    if inspection.errors:
        print(f"    Errors: {inspection.errors}")


def _check_requirements(
    inspection: LiveRunInspection,
    args: argparse.Namespace,
) -> None:
    """Check --require-* conditions and exit with error if not met."""
    failures: list[str] = []

    if args.require_events is not None:
        total_events = (
            inspection.source_notes
            + inspection.candidate_notes
            + inspection.evidence_notes
            + inspection.signal_notes
            + inspection.failures_count
        )
        if total_events < args.require_events:
            failures.append(
                f"Event count {total_events} < required {args.require_events}"
            )

    if args.require_finalized and not inspection.finalized:
        failures.append("Run not finalized")

    if args.require_note_types:
        required = [t.strip() for t in args.require_note_types.split(",")]
        for note_type in required:
            count = inspection.event_type_counts.get(note_type, 0)
            if count == 0:
                failures.append(f"Missing note type: {note_type}")

    if args.require_daily_note and not inspection.daily_note_exists:
        failures.append("Daily note does not exist for the run date")

    if args.require_daily_body and not inspection.daily_note_has_body:
        failures.append("Daily note exists but has no report body")

    if failures:
        print("\n  REQUIREMENT FAILURES:")
        for f in failures:
            print(f"    - {f}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
