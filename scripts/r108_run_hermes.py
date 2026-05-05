"""R1-08 automated Hermes daily dry run runner.

Modes:
  --preflight   Verify all prerequisites without running Hermes.
  --run         Run the full automated Hermes dry run.
  --inspect     Inspect the dry-run DB state after a run.

This script launches Hermes-Agent as an external process using its
one-shot mode (``hermes -z <prompt> --yolo``). It does not replace
Hermes, implement crawlers, or fetch URLs.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPT_FILE = REPO_ROOT / "prompts" / "r108_hermes_daily_dry_run_prompt.md"
RUNS_DIR = REPO_ROOT / "runs" / "r1_08"
DRYRUN_DB_PATH = REPO_ROOT / ".local" / "risk_observer_dryrun.db"
DRYRUN_DB_URL = f"sqlite:///{DRYRUN_DB_PATH}"

HERMES_TIMEOUT_SECONDS = 600  # 10 minutes


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
    """Run repo-local MCP smoke check."""
    python = str(REPO_ROOT / ".venv" / "bin" / "python")
    result = _run_cmd(
        [python, "-m", "frontier_ai_risk_observer.mcp.smoke"],
        check=False,
        env={"DATABASE_URL": DRYRUN_DB_URL},
    )
    return result.returncode == 0


def check_validate_registries() -> bool:
    """Run registry validation."""
    python = str(REPO_ROOT / ".venv" / "bin" / "python")
    result = _run_cmd([python, "scripts/validate_registries.py"], check=False)
    return result.returncode == 0


def check_dryrun_db() -> bool:
    """Check if the dry-run DB exists and is accessible."""
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
    """Initialize the dry-run DB if it doesn't exist."""
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
    print("=== R1-08 Preflight Checks ===\n")

    # 1. Hermes installed
    print("1. Checking Hermes-Agent...")
    version = check_hermes_installed()
    if version is None:
        print("   FAIL: Hermes not installed")
        return False
    print(f"   OK: {version}")

    # 2. Registry validation
    print("2. Checking registry validation...")
    if not check_validate_registries():
        print("   FAIL: Registry validation failed")
        return False
    print("   OK")

    # 3. MCP smoke
    print("3. Checking MCP smoke...")
    if not check_mcp_smoke():
        print("   FAIL: MCP smoke failed")
        return False
    print("   OK")

    # 4. Dry-run DB
    print("4. Checking dry-run DB...")
    if not DRYRUN_DB_PATH.exists():
        print("   Not found, initializing...")
        if not init_dryrun_db():
            print("   FAIL: Could not initialize dry-run DB")
            return False
    if not check_dryrun_db():
        print("   FAIL: Dry-run DB check failed")
        return False
    print("   OK")

    # 5. Prompt file
    print("5. Checking R1-08 prompt file...")
    if not PROMPT_FILE.exists():
        print(f"   FAIL: {PROMPT_FILE} not found")
        return False
    print("   OK")

    print("\n=== Preflight: ALL PASSED ===")
    return True


def create_run_dir() -> Path:
    """Create a timestamped run directory."""
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    run_dir = RUNS_DIR / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def run_hermes(run_dir: Path) -> bool:
    """Launch Hermes in one-shot mode with the R1-08 prompt."""
    prompt_text = PROMPT_FILE.read_text(encoding="utf-8")

    # Save prompt to run dir
    prompt_copy = run_dir / "prompt.md"
    prompt_copy.write_text(prompt_text, encoding="utf-8")

    print(f"  Prompt saved: {prompt_copy}")
    print(f"  Launching Hermes (timeout: {HERMES_TIMEOUT_SECONDS}s)...")
    print("  This may take several minutes as Hermes browses real sources.\n")

    try:
        result = _run_cmd(
            ["hermes", "-z", prompt_text, "--yolo"],
            check=False,
            timeout=HERMES_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        print(f"  Hermes timed out after {HERMES_TIMEOUT_SECONDS}s")
        timeout_msg = f"Hermes run timed out after {HERMES_TIMEOUT_SECONDS} seconds"
        (run_dir / "hermes_stdout.log").write_text(timeout_msg)
        (run_dir / "hermes_stderr.log").write_text(timeout_msg)
        (run_dir / "hermes_output.md").write_text(timeout_msg)
        return False

    # Save outputs
    (run_dir / "hermes_stdout.log").write_text(result.stdout, encoding="utf-8")
    (run_dir / "hermes_stderr.log").write_text(result.stderr, encoding="utf-8")
    (run_dir / "hermes_output.md").write_text(result.stdout, encoding="utf-8")

    returncode = result.returncode
    print(f"  Hermes exited with code: {returncode}")

    if result.stderr:
        stderr_preview = result.stderr[:500]
        print(f"  stderr preview: {stderr_preview}")

    # Write summary
    _write_summary(run_dir, result)
    return returncode == 0


def _write_summary(run_dir: Path, result: subprocess.CompletedProcess[str]) -> None:
    """Write a compact run summary."""
    lines = [
        "# R1-08 Run Summary",
        "",
        f"- **Timestamp**: {run_dir.name}",
        f"- **Hermes exit code**: {result.returncode}",
        "- **Prompt file**: prompts/r108_hermes_daily_dry_run_prompt.md",
        "- **Output files**:",
        "  - hermes_stdout.log",
        "  - hermes_stderr.log",
        "  - hermes_output.md",
        "",
        "## Output Preview",
        "",
    ]
    # Add first 100 lines of output
    output_lines = result.stdout.split("\n")[:100]
    for line in output_lines:
        lines.append(line)
    lines.append("")
    lines.append("*(truncated if longer than 100 lines)*")

    (run_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def inspect_state(run_dir: Path | None = None) -> None:
    """Inspect the dry-run DB and optionally a run directory."""
    print("=== R1-08 State Inspection ===\n")

    if run_dir is not None:
        print(f"Run directory: {run_dir}")
        if (run_dir / "summary.md").exists():
            print((run_dir / "summary.md").read_text()[:2000])
        print()

    # Run the inspection script
    python = str(REPO_ROOT / ".venv" / "bin" / "python")
    result = _run_cmd(
        [python, "scripts/r108_inspect_state.py"],
        check=False,
        env={"DATABASE_URL": DRYRUN_DB_URL},
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"Inspection error: {result.stderr}")


def main() -> None:
    parser = argparse.ArgumentParser(description="R1-08 Hermes daily dry run runner")
    parser.add_argument("--preflight", action="store_true", help="Run preflight checks only")
    parser.add_argument("--run", action="store_true", help="Run the full Hermes dry run")
    parser.add_argument(
        "--inspect", action="store_true",
        help="Inspect DB state after a run",
    )
    parser.add_argument(
        "--run-dir", type=str, default=None,
        help="Specific run directory to inspect",
    )
    args = parser.parse_args()

    if not any([args.preflight, args.run, args.inspect]):
        parser.print_help()
        sys.exit(1)

    if args.preflight:
        ok = preflight()
        sys.exit(0 if ok else 1)

    if args.run:
        # Preflight first
        if not preflight():
            print("\nPreflight FAILED. Cannot run Hermes.")
            sys.exit(1)

        # Ensure DB exists
        init_dryrun_db()

        # Create run dir and run Hermes
        run_dir = create_run_dir()
        print("\n=== Running Hermes Dry Run ===")
        print(f"  Run directory: {run_dir}")

        ok = run_hermes(run_dir)

        # Always inspect state after run
        print("\n=== Post-Run State Inspection ===")
        inspect_state(run_dir)

        print("\n=== Run Complete ===")
        print(f"  Run directory: {run_dir}")
        print(f"  Status: {'SUCCESS' if ok else 'COMPLETED_WITH_ISSUES'}")
        print(f"  View output: cat {run_dir}/hermes_output.md")
        sys.exit(0 if ok else 1)

    if args.inspect:
        run_dir = Path(args.run_dir) if args.run_dir else None
        inspect_state(run_dir)


if __name__ == "__main__":
    main()
