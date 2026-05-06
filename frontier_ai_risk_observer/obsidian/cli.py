"""Optional Obsidian CLI integration helpers.

Provides utilities for opening vaults and checking Obsidian availability.
Does not require Obsidian to be installed for export to work.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def is_obsidian_installed() -> bool:
    """Check if Obsidian app is available on macOS."""
    # Check for Obsidian in common macOS locations
    app_paths = [
        Path("/Applications/Obsidian.app"),
        Path.home() / "Applications" / "Obsidian.app",
    ]
    return any(p.exists() for p in app_paths)


def open_in_obsidian(vault_path: Path) -> bool:
    """Try to open a vault directory in Obsidian (macOS).

    Returns True if the open command succeeded.
    """
    if not vault_path.exists():
        return False

    # Try opening with Obsidian URI scheme first
    try:
        obsidian_uri = f"obsidian://open?vault={vault_path.name}"
        subprocess.run(
            ["open", obsidian_uri],
            check=False,
            capture_output=True,
            timeout=5,
        )
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Fallback: open the directory in Finder
    try:
        subprocess.run(
            ["open", str(vault_path)],
            check=False,
            capture_output=True,
            timeout=5,
        )
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def open_in_finder(path: Path) -> bool:
    """Open a path in Finder (macOS)."""
    if not path.exists():
        return False
    try:
        subprocess.run(["open", str(path)], check=False, capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_latest_export_dir(vault_base: Path) -> Path | None:
    """Find the latest exported vault directory."""
    vault = vault_base / "AI-Risk-Intelligence"
    if vault.exists():
        return vault
    return None


def get_live_run_dir(vault_base: Path, run_id: str) -> Path | None:
    """Find a specific live run directory under 08_Live_Runs."""
    run_dir = vault_base / "AI-Risk-Intelligence" / "08_Live_Runs" / run_id
    if run_dir.exists():
        return run_dir
    return None


def get_latest_live_run_dir(vault_base: Path) -> Path | None:
    """Find the most recent live run directory."""
    live_runs = vault_base / "AI-Risk-Intelligence" / "08_Live_Runs"
    if not live_runs.exists():
        return None
    run_dirs = sorted(
        [d for d in live_runs.iterdir() if d.is_dir()],
        key=lambda d: d.name,
        reverse=True,
    )
    return run_dirs[0] if run_dirs else None


def open_live_run(vault_base: Path, run_id: str | None = None) -> bool:
    """Open a live run directory in Obsidian or Finder.

    If run_id is None, opens the latest live run.
    """
    if run_id:
        run_dir = get_live_run_dir(vault_base, run_id)
    else:
        run_dir = get_latest_live_run_dir(vault_base)

    if not run_dir:
        return False
    return open_in_obsidian(run_dir) or open_in_finder(run_dir)
