"""Hermes-Agent integration smoke test for R1-07.

Supports two modes:
  --dry-run   (default) Print config snippet and verify local repo checks.
              Does not mutate ~/.hermes/config.yaml.
  --apply     Create a timestamped backup of ~/.hermes/config.yaml,
              then add/update this project's MCP server block and
              skills external_dirs.

Architecture constraints:
  - Hermes-Agent must remain external (not vendored into this repo).
  - This script only edits ~/.hermes/config.yaml, nothing else.
  - No secrets are written.
  - No delivery channels are configured.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
MCP_SERVER_NAME = "ai_risk_observer"
HERMES_CONFIG = Path.home() / ".hermes" / "config.yaml"

MCP_TOOL_ALLOWLIST = [
    "risk_registry_summary",
    "risk_registry_list_due_sources",
    "risk_registry_get_source",
    "risk_raw_item_seen_check",
    "risk_raw_item_store",
    "risk_raw_item_search",
    "risk_raw_item_duplicate_candidates",
    "risk_source_run_record",
    "risk_signal_store",
    "risk_signal_search",
    "risk_digest_store",
    "risk_digest_search",
    "risk_benchmark_observation_store",
    "risk_source_health_summary",
    "risk_discovery_helper_preview",
    "risk_candidate_preprocess",
]


def _run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def check_hermes_installed() -> str | None:
    """Return Hermes version string if installed, else None."""
    try:
        result = _run(["hermes", "--version"], check=False)
        if result.returncode == 0:
            return result.stdout.strip()
    except FileNotFoundError:
        pass
    return None


def check_repo_mcp_smoke() -> bool:
    """Run the repo-local MCP smoke check. Returns True on success."""
    python = str(REPO_ROOT / ".venv" / "bin" / "python")
    if not Path(python).exists():
        print("ERROR: .venv/bin/python not found. Run 'make install' first.")
        return False
    result = _run([python, "-m", "frontier_ai_risk_observer.mcp.smoke"], check=False)
    if result.returncode == 0:
        print("  MCP smoke: PASS")
        return True
    print(f"  MCP smoke: FAIL\n  stdout: {result.stdout}\n  stderr: {result.stderr}")
    return False


def check_mcp_sdk_installed() -> bool:
    """Check if the Python MCP SDK is importable."""
    python = str(REPO_ROOT / ".venv" / "bin" / "python")
    result = _run(
        [python, "-c", "from mcp.server.fastmcp import FastMCP; print('ok')"],
        check=False,
    )
    return result.returncode == 0 and "ok" in result.stdout


def check_validate_registries() -> bool:
    """Run registry validation. Returns True on success."""
    python = str(REPO_ROOT / ".venv" / "bin" / "python")
    result = _run([python, "scripts/validate_registries.py"], check=False)
    if result.returncode == 0:
        print("  Registry validation: PASS")
        return True
    print(f"  Registry validation: FAIL\n  stderr: {result.stderr}")
    return False


def generate_mcp_config_block() -> dict:
    """Generate the MCP server config block for Hermes."""
    python = str(REPO_ROOT / ".venv" / "bin" / "python")
    dryrun_db_path = REPO_ROOT / ".local" / "risk_observer_dryrun.db"
    return {
        "command": python,
        "args": ["-m", "frontier_ai_risk_observer.mcp.server"],
        "timeout": 120,
        "enabled": True,
        "tools": {
            "include": MCP_TOOL_ALLOWLIST,
            "prompts": False,
            "resources": False,
        },
        "env": {
            "DATABASE_URL": f"sqlite:///{dryrun_db_path}",
            "SOURCE_REGISTRY_DIR": str(REPO_ROOT / "source_registry"),
        },
    }


def generate_skills_config() -> list[str]:
    """Generate the skills external_dirs entry."""
    return [str(SKILLS_DIR)]


def print_dry_run_config() -> None:
    """Print the config block that should be added to ~/.hermes/config.yaml."""
    mcp_block = generate_mcp_config_block()
    skills_dirs = generate_skills_config()

    print("\n=== Hermes Config Snippet (add to ~/.hermes/config.yaml) ===\n")
    print("# AI Risk Signal Observer — MCP server")
    print("mcp_servers:")
    print(f"  {MCP_SERVER_NAME}:")
    for key, value in mcp_block.items():
        if isinstance(value, dict):
            print(f"    {key}:")
            for k, v in value.items():
                if isinstance(v, list):
                    print(f"      {k}:")
                    for item in v:
                        print(f"        - {item}")
                elif isinstance(v, bool):
                    print(f"      {k}: {'true' if v else 'false'}")
                else:
                    print(f"      {k}: {v}")
        elif isinstance(value, list):
            print(f"    {key}:")
            for item in value:
                print(f"      - {item}")
        elif isinstance(value, bool):
            print(f"    {key}: {'true' if value else 'false'}")
        else:
            print(f"    {key}: {json.dumps(value)}")

    print("\n# AI Risk Signal Observer — Skills external directory")
    print("skills:")
    print("  external_dirs:")
    for d in skills_dirs:
        print(f"    - {d}")

    print("\n=== Detected paths ===")
    print(f"  Repo root: {REPO_ROOT}")
    print(f"  Skills dir: {SKILLS_DIR}")
    print(f"  MCP server name: {MCP_SERVER_NAME}")
    print(f"  Tool count: {len(MCP_TOOL_ALLOWLIST)}")


def apply_config() -> bool:
    """Apply the MCP and skills config to ~/.hermes/config.yaml.

    Creates a timestamped backup first. Preserves existing config.
    Returns True on success.
    """
    if not HERMES_CONFIG.exists():
        print(f"ERROR: {HERMES_CONFIG} does not exist. Run 'hermes setup' first.")
        return False

    try:
        import yaml
    except ImportError:
        print("ERROR: PyYAML is required for --apply. Install with: pip install pyyaml")
        return False

    # Backup
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    backup_path = HERMES_CONFIG.with_name(f"config.yaml.bak.{timestamp}")
    shutil.copy2(HERMES_CONFIG, backup_path)
    print(f"  Backup saved: {backup_path}")

    # Read existing config
    with open(HERMES_CONFIG) as f:
        config = yaml.safe_load(f)

    # Add/update MCP server block
    mcp_block = generate_mcp_config_block()
    if "mcp_servers" not in config:
        config["mcp_servers"] = {}
    config["mcp_servers"][MCP_SERVER_NAME] = mcp_block
    print(f"  MCP server '{MCP_SERVER_NAME}' config added/updated")

    # Add skills external dir
    skills_dir_str = str(SKILLS_DIR)
    external_dirs = config.get("skills", {}).get("external_dirs", [])
    if external_dirs is None:
        external_dirs = []
    if skills_dir_str not in external_dirs:
        external_dirs.append(skills_dir_str)
    if "skills" not in config:
        config["skills"] = {}
    config["skills"]["external_dirs"] = external_dirs
    print(f"  skills.external_dirs updated: {external_dirs}")

    # Write updated config
    with open(HERMES_CONFIG, "w") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Hermes-Agent integration smoke test")
    parser.add_argument(
        "--apply", action="store_true",
        help="Apply config to ~/.hermes/config.yaml (with backup)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print config snippet only (default)",
    )
    args = parser.parse_args()

    print("=== R1-07: Hermes-Agent Integration Smoke Test ===\n")

    # 1. Check Hermes installation
    print("1. Checking Hermes-Agent installation...")
    version = check_hermes_installed()
    if version is None:
        print("  FAIL: Hermes-Agent is not installed.")
        print("  Install externally with:")
        install_url = (
            "https://raw.githubusercontent.com/NousResearch/"
            "hermes-agent/main/scripts/install.sh"
        )
        print(f"    curl -fsSL {install_url} | bash")
        print("  Do NOT proceed with fake integration.")
        sys.exit(1)
    print(f"  Hermes installed: {version}")

    # 2. Check MCP SDK
    print("\n2. Checking Python MCP SDK...")
    if check_mcp_sdk_installed():
        print("  MCP SDK: installed")
    else:
        print("  MCP SDK: not installed")
        print("  Install with: .venv/bin/python -m pip install -e '.[mcp]'")
        sys.exit(1)

    # 3. Repo-local checks
    print("\n3. Running repo-local checks...")
    registries_ok = check_validate_registries()
    mcp_ok = check_repo_mcp_smoke()

    if not (registries_ok and mcp_ok):
        print("\n  Repo-local checks FAILED. Fix before proceeding.")
        sys.exit(1)

    # 4. Print or apply config
    print(f"\n4. {'Applying' if args.apply else 'Printing'} Hermes config...")
    if args.apply:
        if not apply_config():
            print("\n  Config apply FAILED.")
            sys.exit(1)
    else:
        print_dry_run_config()

    # 5. Verify Hermes sees MCP server (if apply mode)
    if args.apply:
        print("\n5. Verifying Hermes MCP server registration...")
        result = _run(["hermes", "mcp", "list"], check=False)
        if result.returncode == 0:
            if MCP_SERVER_NAME in result.stdout:
                print(f"  Hermes sees MCP server '{MCP_SERVER_NAME}': YES")
            else:
                print(f"  Hermes sees MCP server '{MCP_SERVER_NAME}': NOT YET")
                print("  You may need to restart Hermes or run /reload-mcp in chat.")
        else:
            print(f"  hermes mcp list failed: {result.stderr}")

        print("\n6. Testing MCP server connection...")
        test_result = _run(["hermes", "mcp", "test", MCP_SERVER_NAME], check=False)
        if test_result.returncode == 0:
            print("  MCP test: PASS")
        else:
            print(f"  MCP test: returned {test_result.returncode}")
            print(f"  stdout: {test_result.stdout}")
            print(f"  stderr: {test_result.stderr}")

    # Summary
    print("\n=== Summary ===")
    print(f"  Hermes version: {version}")
    print("  MCP SDK installed: yes")
    print(f"  Registry validation: {'PASS' if registries_ok else 'FAIL'}")
    print(f"  MCP smoke: {'PASS' if mcp_ok else 'FAIL'}")
    print(f"  Config: {'applied' if args.apply else 'dry-run only'}")
    if args.apply:
        print(f"  Hermes config modified: {HERMES_CONFIG}")

    print("\n=== Next steps ===")
    if not args.apply:
        print("  1. Review the config snippet above")
        print("  2. Run with --apply to configure Hermes, or manually edit ~/.hermes/config.yaml")
        print("  3. Start Hermes and run smoke prompts")
        print("     from docs/16_hermes_integration_smoke_test.md")
    else:
        print("  1. Start Hermes: hermes chat")
        print("  2. Run smoke prompts from docs/16_hermes_integration_smoke_test.md")


if __name__ == "__main__":
    main()
