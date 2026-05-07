"""Install OwlHermes plugin into Hermes plugins directory.

Supports:
  --mode symlink   Symlink .hermes/plugins/owlhermes to ~/.hermes/plugins/owlhermes
  --mode copy      Copy files (safer for remote installs)
  --target         Override target directory (default: ~/.hermes/plugins/owlhermes)
  --project-local  Install as project-local plugin (.hermes/plugins/ already in place)
  --dry-run        Preview without making changes
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_SOURCE = REPO_ROOT / ".hermes" / "plugins" / "owlhermes"
DEFAULT_TARGET = Path.home() / ".hermes" / "plugins" / "owlhermes"


def main() -> int:
    parser = argparse.ArgumentParser(description="Install OwlHermes plugin for Hermes")
    parser.add_argument("--mode", choices=["symlink", "copy"], default="symlink")
    parser.add_argument("--target", type=str, default=str(DEFAULT_TARGET))
    parser.add_argument("--project-local", action="store_true",
                        help="Plugin is already in .hermes/plugins/ (project-local)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.project_local:
        print("Project-local plugin mode — no installation needed.")
        print("Ensure HERMES_ENABLE_PROJECT_PLUGINS=true is set.")
        print(f"Plugin location: {PLUGIN_SOURCE}")
        if not PLUGIN_SOURCE.exists():
            print(f"ERROR: Plugin source not found at {PLUGIN_SOURCE}")
            return 1
        print("\nNext steps:")
        print("  1. Set HERMES_ENABLE_PROJECT_PLUGINS=true")
        print("  2. Or: hermes plugins enable owlhermes")
        return 0

    target = Path(args.target)

    if not PLUGIN_SOURCE.exists():
        print(f"ERROR: Plugin source not found at {PLUGIN_SOURCE}")
        return 1

    print("Installing OwlHermes plugin:")
    print(f"  Source: {PLUGIN_SOURCE}")
    print(f"  Target: {target}")
    print(f"  Mode:   {args.mode}")

    if args.dry_run:
        print("\n[DRY RUN] No changes made.")
        if args.mode == "symlink":
            print(f"  Would create symlink: {target} -> {PLUGIN_SOURCE}")
        else:
            print(f"  Would copy: {PLUGIN_SOURCE}/ -> {target}/")
        print_next_steps()
        return 0

    # Handle existing target
    if target.exists():
        if target.is_symlink():
            print(f"  Removing existing symlink: {target}")
            target.unlink()
        elif target.is_dir():
            backup = target.with_name(target.name + ".bak")
            print(f"  Backing up existing directory: {target} -> {backup}")
            if backup.exists():
                shutil.rmtree(backup)
            shutil.move(str(target), str(backup))

    # Ensure parent exists
    target.parent.mkdir(parents=True, exist_ok=True)

    if args.mode == "symlink":
        target.symlink_to(PLUGIN_SOURCE)
        print(f"  Created symlink: {target} -> {PLUGIN_SOURCE}")
    else:
        shutil.copytree(str(PLUGIN_SOURCE), str(target))
        print(f"  Copied: {PLUGIN_SOURCE}/ -> {target}/")

    print("\nInstallation complete!")
    print_next_steps()
    return 0


def print_next_steps() -> None:
    print("\nNext steps:")
    print("  1. Enable plugin in ~/.hermes/config.yaml:")
    print("       plugins:")
    print("         enabled:")
    print("           - owlhermes")
    print("  2. Or: hermes plugins enable owlhermes")
    print("  3. Set environment variables:")
    print("       DATABASE_URL=sqlite:///./.local/risk_observer_dryrun.db")
    print("       SOURCE_REGISTRY_DIR=<repo>/source_registry")
    print("       OBSIDIAN_VAULT_PATH=<vault-path>  # optional")
    print("  4. Run: make plugin-smoke")


if __name__ == "__main__":
    raise SystemExit(main())
