"""Automated daily report runner with two-phase finalization.

Modes:
  --preflight   Verify all prerequisites without running Hermes.
  --run         Run the full two-phase automated daily report.
  --inspect     Inspect the dry-run DB and latest run artifacts.

Two phases:
  Phase A (collection/research): Hermes selects sources, collects evidence,
  stores raw items and signals. Uses daily_report_prompt.md.
  Phase B (finalize/report): If Phase A didn't produce a complete report,
  Hermes writes a Chinese report using only DB state. Uses
  daily_report_finalize_prompt.md. No browsing.

This script launches Hermes-Agent as an external process using its
one-shot mode (``hermes -z <prompt> --yolo``). It does not replace
Hermes, implement crawlers, or fetch URLs. It does not reset the DB
by default.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPT_FILE = REPO_ROOT / "prompts" / "daily_report_prompt.md"
FINALIZE_PROMPT_FILE = REPO_ROOT / "prompts" / "daily_report_finalize_prompt.md"
RUNS_DIR = REPO_ROOT / "runs" / "daily"
DRYRUN_DB_PATH = REPO_ROOT / ".local" / "risk_observer_dryrun.db"
DRYRUN_DB_URL = f"sqlite:///{DRYRUN_DB_PATH}"

COLLECTION_TIMEOUT_DEFAULT = 1800  # 30 minutes
FINALIZE_TIMEOUT_DEFAULT = 600  # 10 minutes


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class StateSnapshot:
    """DB state counts at a point in time."""

    raw_item_count: int = 0
    source_run_count: int = 0
    signal_count: int = 0
    digest_count: int = 0
    latest_digest_id: str | None = None
    latest_digest_date: str | None = None
    latest_digest_title: str | None = None
    latest_digest_status: str | None = None
    recent_raw_items: list[dict[str, Any]] = field(default_factory=list)
    recent_source_runs: list[dict[str, Any]] = field(default_factory=list)
    recent_signals: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class PhaseResult:
    """Result from running one Hermes phase."""

    exit_code: int = -1
    timed_out: bool = False
    stdout: str = ""
    stderr: str = ""
    stdout_length: int = 0


@dataclass
class RunSummary:
    """Summary for the full two-phase run."""

    timestamp: str = ""
    prompt_file: str = ""
    finalize_prompt_file: str = ""
    phase_a_status: str = "not_run"
    phase_a_exit_code: int = -1
    phase_a_timed_out: bool = False
    phase_a_timed_out_seconds: int = 0
    phase_a_db_delta_raw_items: int = 0
    phase_a_db_delta_source_runs: int = 0
    phase_a_db_delta_signals: int = 0
    phase_a_db_delta_digests: int = 0
    finalize_needed: bool = False
    finalize_reason: str = ""
    phase_b_status: str = "not_run"
    phase_b_exit_code: int = -1
    phase_b_timed_out: bool = False
    phase_b_timed_out_seconds: int = 0
    phase_b_db_delta_digests: int = 0
    final_report_path: str = ""
    daily_report_completed: bool = False
    digest_stored: bool = False
    quality_score: int | None = None
    quality_max: int | None = None
    known_issues: list[str] = field(default_factory=list)
    next_suggested_command: str = ""
    small_model_enabled: bool = False
    small_model_name: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_cmd(
    cmd: list[str],
    check: bool = True,
    env: dict[str, str] | None = None,
    timeout: int | None = None,
) -> subprocess.CompletedProcess[str]:
    run_env = {**os.environ, **(env or {})}
    return subprocess.run(
        cmd, capture_output=True, text=True, check=check,
        env=run_env, timeout=timeout,
    )


def check_hermes_installed() -> str | None:
    """Return Hermes version string if installed, else None."""
    try:
        result = _run_cmd(["hermes", "--version"], check=False)
        if result.returncode == 0:
            return result.stdout.strip().split("\n")[0]
    except FileNotFoundError:
        pass
    return None


def check_mcp_smoke() -> bool:
    python = str(REPO_ROOT / ".venv" / "bin" / "python")
    result = _run_cmd(
        [python, "-m", "frontier_ai_risk_observer.mcp.smoke"],
        check=False,
        env={"DATABASE_URL": DRYRUN_DB_URL},
    )
    return result.returncode == 0


def check_validate_registries() -> bool:
    python = str(REPO_ROOT / ".venv" / "bin" / "python")
    result = _run_cmd([python, "scripts/validate_registries.py"], check=False)
    return result.returncode == 0


def check_source_health() -> bool:
    python = str(REPO_ROOT / ".venv" / "bin" / "python")
    result = _run_cmd([python, "scripts/check_source_health.py"], check=False)
    return result.returncode == 0


def check_helper_preview_nofetch() -> bool:
    python = str(REPO_ROOT / ".venv" / "bin" / "python")
    result = _run_cmd(
        [python, "scripts/preview_discovery_helpers.py"],
        check=False,
    )
    return result.returncode == 0


def check_dryrun_db() -> bool:
    if not DRYRUN_DB_PATH.exists():
        return False
    python = str(REPO_ROOT / ".venv" / "bin" / "python")
    result = _run_cmd(
        [python, "-m", "frontier_ai_risk_observer.db.check"],
        check=False,
        env={"DATABASE_URL": DRYRUN_DB_URL},
    )
    return result.returncode == 0


def init_dryrun_db() -> bool:
    if DRYRUN_DB_PATH.exists():
        return True
    python = str(REPO_ROOT / ".venv" / "bin" / "python")
    result = _run_cmd(
        [python, "-m", "frontier_ai_risk_observer.db.dryrun"],
        check=False,
        env={"DATABASE_URL": DRYRUN_DB_URL},
    )
    return result.returncode == 0


# ---------------------------------------------------------------------------
# State snapshots
# ---------------------------------------------------------------------------


def capture_state_snapshot() -> StateSnapshot:
    """Capture current DB state. Works with SQLite. Does not require Hermes."""
    snap = StateSnapshot()
    try:
        from frontier_ai_risk_observer.db.session import create_session_factory

        factory = create_session_factory(DRYRUN_DB_URL)
        with factory() as session:
            from sqlalchemy import func, select

            from frontier_ai_risk_observer.db.models import Digest, RawItem, Signal, SourceRun

            snap.raw_item_count = session.scalar(
                select(func.count(RawItem.id))
            ) or 0
            snap.source_run_count = session.scalar(
                select(func.count(SourceRun.id))
            ) or 0
            snap.signal_count = session.scalar(
                select(func.count(Signal.id))
            ) or 0
            snap.digest_count = session.scalar(
                select(func.count(Digest.id))
            ) or 0

            # Latest digest
            latest = session.scalar(
                select(Digest).order_by(Digest.created_at.desc()).limit(1)
            )
            if latest:
                snap.latest_digest_id = str(latest.id)
                snap.latest_digest_date = latest.digest_date.isoformat()
                snap.latest_digest_title = latest.title
                snap.latest_digest_status = latest.status

            # Recent items (last 20)
            for item in session.scalars(
                select(RawItem).order_by(
                    RawItem.last_seen_at.desc()
                ).limit(20)
            ).all():
                snap.recent_raw_items.append({
                    "id": str(item.id),
                    "title": item.title,
                    "source_id": item.source_id,
                    "canonical_url": item.canonical_url,
                    "seen_count": item.seen_count,
                    "first_seen_at": item.first_seen_at.isoformat()
                    if item.first_seen_at else None,
                })

            for run in session.scalars(
                select(SourceRun).order_by(
                    SourceRun.created_at.desc()
                ).limit(20)
            ).all():
                snap.recent_source_runs.append({
                    "id": str(run.id),
                    "source_id": run.source_id,
                    "status": run.status,
                    "items_found": run.items_found,
                    "items_new": run.items_new,
                    "created_at": run.created_at.isoformat()
                    if run.created_at else None,
                })

            for sig in session.scalars(
                select(Signal).order_by(Signal.created_at.desc()).limit(20)
            ).all():
                snap.recent_signals.append({
                    "id": str(sig.id),
                    "title": sig.title_zh,
                    "signal_type": sig.signal_type,
                    "confidence": sig.confidence,
                    "created_at": sig.created_at.isoformat()
                    if sig.created_at else None,
                })
    except Exception as exc:  # noqa: BLE001
        # Snapshot is best-effort; don't fail the run
        snap.known_issues = [f"State snapshot partial: {exc}"]
    return snap


def save_snapshot(snap: StateSnapshot, path: Path) -> None:
    """Save snapshot as JSON."""
    data = asdict(snap)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str),
                    encoding="utf-8")


def compute_delta(before: StateSnapshot, after: StateSnapshot) -> dict[str, int]:
    """Compute count deltas between two snapshots."""
    return {
        "raw_items": after.raw_item_count - before.raw_item_count,
        "source_runs": after.source_run_count - before.source_run_count,
        "signals": after.signal_count - before.signal_count,
        "digests": after.digest_count - before.digest_count,
    }


# ---------------------------------------------------------------------------
# Completion detection
# ---------------------------------------------------------------------------

_CHINESE_REPORT_PATTERNS = [
    r"一句话总览",
    r"今日总览",
    r"今日概览",
    r"■\s*信号",
    r"##\s*信号",
    r"#\s*信号",
    r"信号\s*\d",
    r"Top.?Signal",
    r"风险信号",
]

_INCOMPLETE_PATTERNS = [
    r"timed out",
    r"Traceback",
    r"KeyboardInterrupt",
    r"Calling tool",
    r"Tool call",
    r"risk_raw_item_store\(",
    r"risk_source_run_record\(",
]


def _has_cjk(text: str) -> bool:
    """Check if text has meaningful Chinese content."""
    return len(re.findall(r"[\u4e00-\u9fff]", text)) > 20


def report_looks_complete(text: str) -> bool:
    """Determine if the output looks like a completed Chinese report."""
    if not text or not text.strip():
        return False

    # Must have Chinese content
    if not _has_cjk(text):
        return False

    # Must have at least one report section
    section_found = any(
        re.search(p, text, re.IGNORECASE) for p in _CHINESE_REPORT_PATTERNS
    )
    if not section_found:
        return False

    # Must not be predominantly tool logs
    incomplete_count = sum(
        len(re.findall(p, text, re.IGNORECASE)) for p in _INCOMPLETE_PATTERNS
    )
    if incomplete_count > 5:
        return False

    return True


# ---------------------------------------------------------------------------
# Hermes execution
# ---------------------------------------------------------------------------


def run_hermes_phase(
    prompt_text: str,
    run_dir: Path,
    phase_name: str,
    timeout_seconds: int,
) -> PhaseResult:
    """Run one Hermes phase. Returns PhaseResult with all output."""
    result = PhaseResult()
    result.phase_a_timed_out = False if phase_name == "finalize" else False

    try:
        proc = _run_cmd(
            ["hermes", "-z", prompt_text, "--yolo"],
            check=False,
            timeout=timeout_seconds,
        )
        result.exit_code = proc.returncode
        result.stdout = proc.stdout or ""
        result.stderr = proc.stderr or ""
        result.stdout_length = len(result.stdout)
        result.timed_out = False
    except subprocess.TimeoutExpired as exc:
        result.timed_out = True
        result.exit_code = -1
        stdout_partial = exc.stdout or ""
        stderr_partial = exc.stderr or ""
        if isinstance(stdout_partial, bytes):
            stdout_partial = stdout_partial.decode("utf-8", errors="replace")
        if isinstance(stderr_partial, bytes):
            stderr_partial = stderr_partial.decode("utf-8", errors="replace")
        result.stdout = stdout_partial
        result.stderr = stderr_partial
        result.stdout_length = len(result.stdout)
    except FileNotFoundError:
        result.exit_code = -1
        result.stderr = "Hermes binary not found on PATH"
    except Exception as exc:  # noqa: BLE001
        result.exit_code = -1
        result.stderr = f"Hermes invocation error: {type(exc).__name__}: {exc}"

    # Save artifacts
    (run_dir / f"{phase_name}_stdout.log").write_text(
        result.stdout, encoding="utf-8"
    )
    (run_dir / f"{phase_name}_stderr.log").write_text(
        result.stderr, encoding="utf-8"
    )
    (run_dir / f"{phase_name}_output.md").write_text(
        result.stdout, encoding="utf-8"
    )

    return result


# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------


def preflight() -> bool:
    """Run all preflight checks. Returns True if all pass."""
    print("=== Daily Report Preflight ===\n")

    checks = [
        ("Hermes-Agent", lambda: check_hermes_installed() is not None),
        ("Registry validation", check_validate_registries),
        ("Source health", check_source_health),
        ("Helper preview (no-fetch)", check_helper_preview_nofetch),
        ("MCP smoke", check_mcp_smoke),
        ("Dry-run DB", lambda: (
            init_dryrun_db() if not DRYRUN_DB_PATH.exists() else True
        ) and check_dryrun_db()),
        ("Daily report prompt", lambda: PROMPT_FILE.exists()),
        ("Finalize prompt", lambda: FINALIZE_PROMPT_FILE.exists()),
    ]

    for i, (name, check_fn) in enumerate(checks, 1):
        print(f"{i}. Checking {name}...")
        ok = check_fn()
        if not ok:
            print(f"   FAIL: {name}")
            return False
        label = "OK"
        if name == "Hermes-Agent":
            label = f"OK: {check_hermes_installed()}"
        elif name == "Dry-run DB":
            label = "OK (preserving existing data)"
        print(f"   {label}")

    print("\n=== Preflight: ALL PASSED ===")
    return True


# ---------------------------------------------------------------------------
# Run orchestration
# ---------------------------------------------------------------------------


def create_run_dir() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = RUNS_DIR / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _should_finalize(
    phase_a: PhaseResult,
    run_dir: Path,
    state_before: StateSnapshot,
    state_after_a: StateSnapshot,
    delta_a: dict[str, int],
) -> tuple[bool, str]:
    """Determine if Phase B finalize should run."""
    # Skip if Phase A produced a complete report
    report_path = run_dir / "daily_report.md"
    if report_path.exists() and report_looks_complete(report_path.read_text(encoding="utf-8")):
        return False, "Phase A produced complete report"

    # Skip if Hermes stdout looks like a complete report
    if phase_a.stdout and report_looks_complete(phase_a.stdout):
        return False, "Phase A output looks complete"

    # Run finalize if any of these conditions
    if phase_a.timed_out:
        return True, "Phase A timed out"
    if phase_a.exit_code != 0:
        return True, f"Phase A exited non-zero (code={phase_a.exit_code})"
    if delta_a.get("digests", 0) == 0:
        return True, "No new digest stored after Phase A"
    if not report_path.exists() or not report_path.read_text(encoding="utf-8").strip():
        return True, "daily_report.md is missing or empty"

    # Check if the report looks incomplete (logs, no Chinese sections)
    if report_path.exists():
        text = report_path.read_text(encoding="utf-8")
        if not report_looks_complete(text):
            return True, "Report does not appear to be a complete Chinese briefing"

    return False, "Phase A appears complete"


def run_two_phase(
    run_dir: Path,
    collection_timeout: int = COLLECTION_TIMEOUT_DEFAULT,
    finalize_timeout: int = FINALIZE_TIMEOUT_DEFAULT,
    skip_finalize: bool = False,
    force_finalize: bool = False,
    prompt_file: Path | None = None,
    finalize_prompt_file: Path | None = None,
    quality_check: bool = False,
) -> RunSummary:
    """Run the two-phase daily report workflow."""
    summary = RunSummary()
    summary.timestamp = run_dir.name
    summary.phase_a_timed_out_seconds = collection_timeout
    summary.phase_b_timed_out_seconds = finalize_timeout

    # Load small model config
    try:
        from frontier_ai_risk_observer.models.config import load_small_model_config
        sm_config = load_small_model_config()
        sm_info = sm_config.safe_repr()
        summary.small_model_enabled = sm_info.get("enabled", False)
        summary.small_model_name = sm_info.get("model_name", "")
    except Exception:  # noqa: BLE001
        pass

    # Determine prompt files
    prompt_path = prompt_file or PROMPT_FILE
    finalize_path = finalize_prompt_file or FINALIZE_PROMPT_FILE
    summary.prompt_file = str(prompt_path.relative_to(REPO_ROOT))
    summary.finalize_prompt_file = str(finalize_path.relative_to(REPO_ROOT))

    # --- Phase A: Collection/Research ---
    print("\n=== Phase A: Collection/Research ===")

    # Capture state before
    state_before = capture_state_snapshot()
    save_snapshot(state_before, run_dir / "state_before.json")

    # Read and save prompt
    prompt_text = prompt_path.read_text(encoding="utf-8")
    (run_dir / "prompt.md").write_text(prompt_text, encoding="utf-8")

    print(f"  Prompt: {prompt_path.name}")
    print(f"  Timeout: {collection_timeout}s")
    print("  Hermes is researching today's AI risk signals...\n")

    phase_a = run_hermes_phase(prompt_text, run_dir, "phase_a", collection_timeout)

    # Write daily_report.md from Phase A output
    (run_dir / "daily_report.md").write_text(phase_a.stdout, encoding="utf-8")

    summary.phase_a_status = "timed_out" if phase_a.timed_out else (
        "completed" if phase_a.exit_code == 0 else "error"
    )
    summary.phase_a_exit_code = phase_a.exit_code
    summary.phase_a_timed_out = phase_a.timed_out

    print(f"  Phase A: {summary.phase_a_status}")
    if phase_a.timed_out:
        print(f"  Timed out after {collection_timeout}s")
    else:
        print(f"  Exit code: {phase_a.exit_code}")
    if phase_a.stderr:
        print(f"  stderr: {phase_a.stderr[:300]}")

    # Capture state after Phase A
    state_after_a = capture_state_snapshot()
    save_snapshot(state_after_a, run_dir / "state_after_phase_a.json")
    delta_a = compute_delta(state_before, state_after_a)
    summary.phase_a_db_delta_raw_items = delta_a["raw_items"]
    summary.phase_a_db_delta_source_runs = delta_a["source_runs"]
    summary.phase_a_db_delta_signals = delta_a["signals"]
    summary.phase_a_db_delta_digests = delta_a["digests"]

    print(f"  DB delta: +{delta_a['raw_items']} items, "
          f"+{delta_a['source_runs']} runs, "
          f"+{delta_a['signals']} signals, "
          f"+{delta_a['digests']} digests")

    # --- Decide if finalize needed ---
    if skip_finalize:
        finalize_needed = False
        finalize_reason = "Finalize skipped by --skip-finalize"
    elif force_finalize:
        finalize_needed = True
        finalize_reason = "Finalize forced by --force-finalize"
    else:
        finalize_needed, finalize_reason = _should_finalize(
            phase_a, run_dir, state_before, state_after_a, delta_a
        )

    summary.finalize_needed = finalize_needed
    summary.finalize_reason = finalize_reason

    # --- Phase B: Finalize/Report ---
    if finalize_needed:
        print(f"\n=== Phase B: Finalize ({finalize_reason}) ===")

        # Read finalize prompt
        finalize_text = finalize_path.read_text(encoding="utf-8")
        (run_dir / "finalize_prompt.md").write_text(finalize_text, encoding="utf-8")

        print(f"  Prompt: {finalize_path.name}")
        print(f"  Timeout: {finalize_timeout}s")
        print("  Hermes is writing the final report from DB state...\n")

        phase_b = run_hermes_phase(
            finalize_text, run_dir, "phase_b", finalize_timeout
        )

        summary.phase_b_status = "timed_out" if phase_b.timed_out else (
            "completed" if phase_b.exit_code == 0 else "error"
        )
        summary.phase_b_exit_code = phase_b.exit_code
        summary.phase_b_timed_out = phase_b.timed_out

        print(f"  Phase B: {summary.phase_b_status}")

        # If Phase B produced output, use it as the final report
        if phase_b.stdout and phase_b.stdout.strip():
            (run_dir / "daily_report.md").write_text(
                phase_b.stdout, encoding="utf-8"
            )

        # Capture state after Phase B
        state_after_b = capture_state_snapshot()
        save_snapshot(state_after_b, run_dir / "state_after_phase_b.json")
        delta_b_digests = state_after_b.digest_count - state_after_a.digest_count
        summary.phase_b_db_delta_digests = delta_b_digests
        summary.digest_stored = delta_b_digests > 0 or delta_a["digests"] > 0

        print(f"  DB delta: +{delta_b_digests} digests")
    else:
        print(f"\n  Phase B: SKIPPED ({finalize_reason})")
        (run_dir / "phase_b_skipped.md").write_text(
            f"Phase B skipped: {finalize_reason}\n",
            encoding="utf-8",
        )
        summary.phase_b_status = "skipped"
        summary.digest_stored = delta_a["digests"] > 0

    # --- Final report check ---
    report_path = run_dir / "daily_report.md"
    summary.final_report_path = str(report_path)
    if report_path.exists():
        text = report_path.read_text(encoding="utf-8")
        summary.daily_report_completed = report_looks_complete(text)
    else:
        summary.daily_report_completed = False

    # --- Quality check ---
    if quality_check:
        try:
            python = str(REPO_ROOT / ".venv" / "bin" / "python")
            result = _run_cmd(
                [python, "scripts/check_daily_report_quality.py",
                 "--report", str(report_path)],
                check=False,
            )
            if result.returncode == 0 or result.stdout:
                # Parse score from output
                score_match = re.search(r"Score:\s*(\d+)/(\d+)", result.stdout)
                if score_match:
                    summary.quality_score = int(score_match.group(1))
                    summary.quality_max = int(score_match.group(2))
        except Exception:  # noqa: BLE001
            pass

    # --- Next suggested command ---
    if summary.daily_report_completed:
        summary.next_suggested_command = "make daily-report-inspect"
    else:
        summary.next_suggested_command = (
            "make daily-report-debug  # Report incomplete — inspect artifacts"
        )

    # --- Known issues ---
    issues: list[str] = []
    if phase_a.timed_out:
        issues.append("Phase A timed out")
    if phase_a.stderr and "error" in phase_a.stderr.lower():
        issues.append("Phase A had stderr errors")
    if finalize_needed and summary.phase_b_timed_out:
        issues.append("Phase B timed out")
    if not summary.daily_report_completed:
        issues.append("Final report does not appear complete")
    summary.known_issues = issues

    return summary


def _write_summary(run_dir: Path, summary: RunSummary) -> None:
    """Write summary.md for the run."""
    lines = [
        "# Daily Report Run Summary",
        "",
        f"- **Timestamp**: {summary.timestamp}",
        f"- **Prompt**: {summary.prompt_file}",
        f"- **Finalize prompt**: {summary.finalize_prompt_file}",
        "",
        "## Phase A: Collection/Research",
        "",
        f"- **Status**: {summary.phase_a_status}",
        f"- **Exit code**: {summary.phase_a_exit_code}",
        f"- **Timed out**: {summary.phase_a_timed_out}"
        + (f" (after {summary.phase_a_timed_out_seconds}s)" if summary.phase_a_timed_out else ""),
        f"- **DB delta**: +{summary.phase_a_db_delta_raw_items} raw items, "
        f"+{summary.phase_a_db_delta_source_runs} source runs, "
        f"+{summary.phase_a_db_delta_signals} signals, "
        f"+{summary.phase_a_db_delta_digests} digests",
        "",
        "## Phase B: Finalize/Report",
        "",
        f"- **Needed**: {summary.finalize_needed}",
        f"- **Reason**: {summary.finalize_reason}",
        f"- **Status**: {summary.phase_b_status}",
    ]
    if summary.phase_b_status not in ("skipped", "not_run"):
        lines += [
            f"- **Exit code**: {summary.phase_b_exit_code}",
            f"- **Timed out**: {summary.phase_b_timed_out}"
            + (
                f" (after {summary.phase_b_timed_out_seconds}s)"
                if summary.phase_b_timed_out
                else ""
            ),
            f"- **DB delta**: +{summary.phase_b_db_delta_digests} digests",
        ]
    lines += [
        "",
        "## Final Result",
        "",
        f"- **Report path**: {summary.final_report_path}",
        f"- **Report completed**: {summary.daily_report_completed}",
        f"- **Digest stored**: {summary.digest_stored}",
        f"- **Small model enabled**: {summary.small_model_enabled}",
        f"- **Small model name**: {summary.small_model_name or '(none)'}",
        "- **risk_candidate_preprocess**: available",
    ]
    if summary.quality_score is not None:
        pct = round(summary.quality_score / summary.quality_max * 100) if summary.quality_max else 0
        lines.append(f"- **Quality score**: {summary.quality_score}/{summary.quality_max} ({pct}%)")
    lines += [
        "",
        "## Known Issues",
        "",
    ]
    if summary.known_issues:
        for issue in summary.known_issues:
            lines.append(f"- {issue}")
    else:
        lines.append("- None")
    lines += [
        "",
        "## Next Step",
        "",
        "```bash",
        f"{summary.next_suggested_command}",
        "```",
        "",
    ]

    # Add output preview
    output_path = run_dir / "daily_report.md"
    if output_path.exists():
        output_lines = output_path.read_text(encoding="utf-8").split("\n")[:80]
        lines.append("## Output Preview")
        lines.append("")
        for line in output_lines:
            lines.append(line)
        lines.append("")
        lines.append("*(truncated if longer)*")

    (run_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def inspect_state(run_dir: Path | None = None) -> None:
    """Inspect the dry-run DB and optionally a run directory."""
    print("=== Daily Report State Inspection ===\n")

    if run_dir is not None:
        print(f"Run directory: {run_dir}")
        if (run_dir / "daily_report.md").exists():
            print(f"Daily report: {run_dir / 'daily_report.md'}")
        if (run_dir / "summary.md").exists():
            print()
            print((run_dir / "summary.md").read_text()[:2000])
        # Show if finalize was used
        if (run_dir / "phase_b_skipped.md").exists():
            print("\nPhase B: SKIPPED")
        elif (run_dir / "phase_b_stdout.log").exists():
            print("\nPhase B: RAN (finalize)")
        print()

    # Run the inspection script
    python = str(REPO_ROOT / ".venv" / "bin" / "python")
    result = _run_cmd(
        [python, "scripts/inspect_daily_report.py"],
        check=False,
        env={"DATABASE_URL": DRYRUN_DB_URL},
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"Inspection error: {result.stderr}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Automated daily report runner (two-phase)",
    )
    parser.add_argument("--preflight", action="store_true", help="Run preflight only")
    parser.add_argument("--run", action="store_true", help="Run two-phase daily report")
    parser.add_argument("--inspect", action="store_true", help="Inspect DB and artifacts")
    parser.add_argument("--run-dir", type=str, default=None, help="Specific run dir to inspect")
    parser.add_argument(
        "--collection-timeout-seconds", type=int,
        default=COLLECTION_TIMEOUT_DEFAULT,
        help=f"Phase A timeout (default: {COLLECTION_TIMEOUT_DEFAULT})",
    )
    parser.add_argument(
        "--finalize-timeout-seconds", type=int,
        default=FINALIZE_TIMEOUT_DEFAULT,
        help=f"Phase B timeout (default: {FINALIZE_TIMEOUT_DEFAULT})",
    )
    parser.add_argument(
        "--skip-finalize", action="store_true",
        help="Skip Phase B even if needed",
    )
    parser.add_argument(
        "--force-finalize", action="store_true",
        help="Force Phase B even if Phase A completed",
    )
    parser.add_argument(
        "--prompt-file", type=str, default=None,
        help="Override Phase A prompt file",
    )
    parser.add_argument(
        "--finalize-prompt-file", type=str, default=None,
        help="Override Phase B prompt file",
    )
    parser.add_argument(
        "--quality-check", action="store_true",
        help="Run quality check after report generation",
    )
    args = parser.parse_args()

    if not any([args.preflight, args.run, args.inspect]):
        parser.print_help()
        sys.exit(1)

    if args.preflight:
        sys.exit(0 if preflight() else 1)

    if args.run:
        if not preflight():
            print("\nPreflight FAILED. Cannot run.")
            sys.exit(1)
        init_dryrun_db()
        run_dir = create_run_dir()

        prompt_file = Path(args.prompt_file) if args.prompt_file else None
        finalize_file = Path(args.finalize_prompt_file) if args.finalize_prompt_file else None

        print(f"\n  Run directory: {run_dir}")
        summary = run_two_phase(
            run_dir,
            collection_timeout=args.collection_timeout_seconds,
            finalize_timeout=args.finalize_timeout_seconds,
            skip_finalize=args.skip_finalize,
            force_finalize=args.force_finalize,
            prompt_file=prompt_file,
            finalize_prompt_file=finalize_file,
            quality_check=args.quality_check,
        )
        _write_summary(run_dir, summary)

        print("\n=== Post-Run Inspection ===")
        inspect_state(run_dir)
        print("\n=== Done ===")
        print(f"  Run directory: {run_dir}")
        print(f"  Daily report: {run_dir}/daily_report.md")
        print(f"  Phase A: {summary.phase_a_status}")
        if summary.finalize_needed:
            print(f"  Phase B: {summary.phase_b_status}")
        print(f"  Report completed: {summary.daily_report_completed}")
        status = (
            "SUCCESS" if summary.daily_report_completed
            else "COMPLETED_WITH_ISSUES"
        )
        print(f"  Status: {status}")
        sys.exit(0 if summary.daily_report_completed else 1)

    if args.inspect:
        run_dir = Path(args.run_dir) if args.run_dir else None
        inspect_state(run_dir)


if __name__ == "__main__":
    main()
