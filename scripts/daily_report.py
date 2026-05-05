"""Automated daily report runner.

Modes:
  --preflight   Verify all prerequisites without running Hermes.
  --run         Run the full automated daily report.
  --inspect     Inspect the dry-run DB and latest run artifacts.

This script launches Hermes-Agent as an external process using its
one-shot mode (``hermes -z <prompt> --yolo``). It does not replace
Hermes, implement crawlers, or fetch URLs. It does not reset the DB
by default.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPT_FILE = REPO_ROOT / "prompts" / "daily_report_prompt.md"
RUNS_DIR = REPO_ROOT / "runs" / "daily"
DRYRUN_DB_PATH = REPO_ROOT / ".local" / "risk_observer_dryrun.db"
DRYRUN_DB_URL = f"sqlite:///{DRYRUN_DB_PATH}"

HERMES_TIMEOUT_SECONDS = 1800  # 30 minutes


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


def create_run_dir() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = RUNS_DIR / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def run_hermes(run_dir: Path) -> bool:
    """Launch Hermes in one-shot mode with the daily report prompt."""
    prompt_text = PROMPT_FILE.read_text(encoding="utf-8")

    # Save prompt to run dir
    (run_dir / "prompt.md").write_text(prompt_text, encoding="utf-8")

    print(f"  Prompt saved: {run_dir / 'prompt.md'}")
    print(f"  Launching Hermes (timeout: {HERMES_TIMEOUT_SECONDS}s)...")
    print("  Hermes is producing today's AI risk daily report...\n")

    try:
        result = _run_cmd(
            ["hermes", "-z", prompt_text, "--yolo"],
            check=False,
            timeout=HERMES_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        print(f"  Hermes timed out after {HERMES_TIMEOUT_SECONDS}s")
        timeout_note = f"Hermes timed out after {HERMES_TIMEOUT_SECONDS}s\n"
        # text=True means stdout/stderr may be str or None
        stdout_partial = exc.stdout or ""
        stderr_partial = exc.stderr or ""
        if isinstance(stdout_partial, bytes):
            stdout_partial = stdout_partial.decode("utf-8", errors="replace")
        if isinstance(stderr_partial, bytes):
            stderr_partial = stderr_partial.decode("utf-8", errors="replace")
        (run_dir / "hermes_stdout.log").write_text(
            timeout_note + stdout_partial, encoding="utf-8",
        )
        (run_dir / "hermes_stderr.log").write_text(
            timeout_note + stderr_partial, encoding="utf-8",
        )
        (run_dir / "hermes_output.md").write_text(
            timeout_note + stdout_partial, encoding="utf-8",
        )
        (run_dir / "daily_report.md").write_text(
            timeout_note + stdout_partial, encoding="utf-8",
        )
        _write_summary(run_dir, 1, "TIMEOUT")
        return False

    # Save outputs
    (run_dir / "hermes_stdout.log").write_text(result.stdout, encoding="utf-8")
    (run_dir / "hermes_stderr.log").write_text(result.stderr, encoding="utf-8")
    (run_dir / "hermes_output.md").write_text(result.stdout, encoding="utf-8")
    (run_dir / "daily_report.md").write_text(result.stdout, encoding="utf-8")

    print(f"  Hermes exited with code: {result.returncode}")

    if result.stderr:
        print(f"  stderr preview: {result.stderr[:300]}")

    _write_summary(run_dir, result.returncode, "SUCCESS" if result.returncode == 0 else "ERROR")
    return result.returncode == 0


def _write_summary(run_dir: Path, exit_code: int, status: str) -> None:
    from frontier_ai_risk_observer.models.config import load_small_model_config

    sm_config = load_small_model_config()
    sm_info = sm_config.safe_repr()
    lines = [
        "# Daily Report Run Summary",
        "",
        f"- **Timestamp**: {run_dir.name}",
        f"- **Status**: {status}",
        f"- **Hermes exit code**: {exit_code}",
        "- **Prompt**: prompts/daily_report_prompt.md",
        "- **DB**: SQLite dry-run DB (existing data preserved)",
        f"- **Small model enabled**: {sm_info['enabled']}",
        f"- **Small model name**: {sm_info['model_name'] or '(none)'}",
        "- **risk_candidate_preprocess**: available",
        "",
        "- **Artifacts**:",
        "  - prompt.md",
        "  - hermes_stdout.log",
        "  - hermes_stderr.log",
        "  - hermes_output.md",
        "  - daily_report.md",
        "",
    ]
    # Add output preview if available
    output_path = run_dir / "hermes_output.md"
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
        description="Automated daily report runner",
    )
    parser.add_argument("--preflight", action="store_true", help="Run preflight only")
    parser.add_argument("--run", action="store_true", help="Run automated daily report")
    parser.add_argument("--inspect", action="store_true", help="Inspect DB and artifacts")
    parser.add_argument("--run-dir", type=str, default=None, help="Specific run dir to inspect")
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
        print("\n=== Running Automated Daily Report ===")
        print(f"  Run directory: {run_dir}")
        ok = run_hermes(run_dir)
        print("\n=== Post-Run Inspection ===")
        inspect_state(run_dir)
        print("\n=== Done ===")
        print(f"  Run directory: {run_dir}")
        print(f"  Daily report: {run_dir}/daily_report.md")
        print(f"  Status: {'SUCCESS' if ok else 'COMPLETED_WITH_ISSUES'}")
        sys.exit(0 if ok else 1)

    if args.inspect:
        run_dir = Path(args.run_dir) if args.run_dir else None
        inspect_state(run_dir)


if __name__ == "__main__":
    main()
