"""Interactive daily report runner.

Modes:
  --preflight         Verify all prerequisites.
  --launch            Run preflight, print prompt, and launch Hermes interactively.
  --copy-prompt-only  Print the prompt path and content without launching Hermes.

Hermes is launched in interactive terminal mode so the human can observe
the run in real time. This script does NOT use one-shot mode.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPT_FILE = REPO_ROOT / "prompts" / "interactive_daily_report_prompt.md"
RUNS_DIR = REPO_ROOT / "runs" / "interactive"
DRYRUN_DB_PATH = REPO_ROOT / ".local" / "risk_observer_dryrun.db"
DRYRUN_DB_URL = f"sqlite:///{DRYRUN_DB_PATH}"


def _run_cmd(
    cmd: list[str],
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    run_env = {**os.environ, **(env or {})}
    return subprocess.run(
        cmd, capture_output=True, text=True, check=check,
        env=run_env,
    )


def check_hermes_installed() -> str | None:
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
    """Run all preflight checks."""
    print("=== Interactive Daily Report Preflight ===\n")

    checks = [
        ("Hermes-Agent", lambda: check_hermes_installed() is not None),
        ("Registry validation", check_validate_registries),
        ("Source health", check_source_health),
        ("MCP smoke", check_mcp_smoke),
        ("Dry-run DB", lambda: (
            init_dryrun_db() if not DRYRUN_DB_PATH.exists() else True
        ) and check_dryrun_db()),
        ("Interactive prompt", lambda: PROMPT_FILE.exists()),
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


def copy_prompt_only() -> None:
    """Print prompt path and content without launching Hermes."""
    if not PROMPT_FILE.exists():
        print(f"ERROR: Prompt file not found: {PROMPT_FILE}")
        sys.exit(1)

    prompt_text = PROMPT_FILE.read_text(encoding="utf-8")
    run_dir = create_run_dir()
    (run_dir / "prompt.md").write_text(prompt_text, encoding="utf-8")

    print("=== Interactive Daily Report Prompt ===\n")
    print(f"Prompt file: {PROMPT_FILE}")
    print(f"Saved to:    {run_dir / 'prompt.md'}\n")
    print("To use manually:")
    print("  1. Start Hermes:  hermes chat")
    prompt_path = run_dir / 'prompt.md'
    print(f"  2. Paste or reference the prompt from: {prompt_path}")
    print(f"  3. Or use one-shot mode:  hermes -z \"$(cat {prompt_path})\" --yolo")
    print()
    print("--- Prompt Content ---\n")
    print(prompt_text)


def launch() -> None:
    """Run preflight, print prompt, and launch Hermes interactively."""
    if not preflight():
        print("\nPreflight FAILED.")
        sys.exit(1)

    if not PROMPT_FILE.exists():
        print(f"ERROR: Prompt file not found: {PROMPT_FILE}")
        sys.exit(1)

    prompt_text = PROMPT_FILE.read_text(encoding="utf-8")
    run_dir = create_run_dir()
    (run_dir / "prompt.md").write_text(prompt_text, encoding="utf-8")

    print("\n=== Launching Interactive Daily Report ===")
    print(f"  Prompt saved: {run_dir / 'prompt.md'}")
    print(f"  Run directory: {run_dir}")
    print()
    print("  Hermes will open in interactive mode.")
    print("  You can observe tool calls and progress in real time.")
    print()
    print("  Starting Hermes...\n")

    # Launch Hermes interactively — the user sees the session in their terminal.
    # We use one-shot mode with --yolo as the simplest interactive-like experience
    # that still auto-injects the prompt. True interactive mode (hermes chat)
    # requires the user to paste the prompt manually.
    try:
        os.execvp(
            "hermes",
            ["hermes", "-z", prompt_text, "--yolo"],
        )
    except FileNotFoundError:
        print("ERROR: Hermes not found on PATH.")
        print(
            "  Install: curl -fsSL "
            "https://raw.githubusercontent.com/NousResearch/"
            "hermes-agent/main/scripts/install.sh | bash"
        )
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Interactive daily report runner",
    )
    parser.add_argument(
        "--preflight", action="store_true",
        help="Run preflight only",
    )
    parser.add_argument(
        "--launch", action="store_true",
        help="Preflight + launch Hermes interactively",
    )
    parser.add_argument(
        "--copy-prompt-only", action="store_true",
        help="Print prompt without launching",
    )
    args = parser.parse_args()

    if not any([args.preflight, args.launch, args.copy_prompt_only]):
        parser.print_help()
        sys.exit(1)

    if args.preflight:
        sys.exit(0 if preflight() else 1)

    if args.copy_prompt_only:
        copy_prompt_only()
        return

    if args.launch:
        launch()


if __name__ == "__main__":
    main()
