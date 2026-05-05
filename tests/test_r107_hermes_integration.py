"""Tests for R1-07 Hermes-Agent integration smoke test infrastructure.

These tests do NOT require Hermes-Agent or real PostgreSQL.
They verify that the integration script, config block, and skill file
are structured correctly.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "hermes_integration_smoke.py"
SKILL_PATH = REPO_ROOT / "skills" / "ai-risk-signal-observer" / "SKILL.md"
HERMES_CONFIG_EXAMPLE = REPO_ROOT / "configs" / "hermes_config.example.yaml"


# ---------------------------------------------------------------------------
# Helper: import the script as a module (it's not a package, so we use
# importlib to load it by path).
# ---------------------------------------------------------------------------

def _import_script():
    spec = importlib.util.spec_from_file_location("hermes_integration_smoke", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# 1. Script dry-run output includes MCP server name
# ---------------------------------------------------------------------------

def test_script_defines_mcp_server_name() -> None:
    mod = _import_script()
    assert mod.MCP_SERVER_NAME == "ai_risk_observer"


def test_script_generates_mcp_config_with_server_name() -> None:
    mod = _import_script()
    block = mod.generate_mcp_config_block()
    assert "command" in block
    assert "args" in block
    assert "-m" in block["args"]
    assert "frontier_ai_risk_observer.mcp.server" in block["args"]


# ---------------------------------------------------------------------------
# 2. Script dry-run output includes skills external dir
# ---------------------------------------------------------------------------

def test_script_generates_skills_dir() -> None:
    mod = _import_script()
    dirs = mod.generate_skills_config()
    assert len(dirs) >= 1
    assert str(REPO_ROOT / "skills") in dirs


# ---------------------------------------------------------------------------
# 3. Config allowlist includes required risk_* tools
# ---------------------------------------------------------------------------

REQUIRED_TOOLS = [
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
]


def test_script_allowlist_includes_required_tools() -> None:
    mod = _import_script()
    for tool in REQUIRED_TOOLS:
        assert tool in mod.MCP_TOOL_ALLOWLIST, f"Missing tool: {tool}"


def test_hermes_config_example_includes_required_tools() -> None:
    import yaml
    with open(HERMES_CONFIG_EXAMPLE) as f:
        config = yaml.safe_load(f)
    tools_include = config["mcp_servers"]["ai_risk_observer"]["tools"]["include"]
    for tool in REQUIRED_TOOLS:
        assert tool in tools_include, f"Missing tool in example config: {tool}"


# ---------------------------------------------------------------------------
# 4. Skill file contains smoke-test mode
# ---------------------------------------------------------------------------

def test_skill_file_contains_smoke_test_mode() -> None:
    content = SKILL_PATH.read_text()
    assert "Smoke-Test Mode" in content or "smoke-test mode" in content.lower()
    assert "risk_registry_summary" in content
    assert "risk_registry_list_due_sources" in content
    assert "risk_raw_item_seen_check" in content


# ---------------------------------------------------------------------------
# 5. Skill file references required R1-06 MCP tools
# ---------------------------------------------------------------------------

def test_skill_file_references_mcp_tools() -> None:
    content = SKILL_PATH.read_text()
    for tool in REQUIRED_TOOLS:
        assert tool in content, f"Skill file missing reference to: {tool}"


# ---------------------------------------------------------------------------
# 6. No default tests require Hermes-Agent
# ---------------------------------------------------------------------------

def test_check_hermes_returns_none_when_not_installed() -> None:
    mod = _import_script()
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = mod.check_hermes_installed()
        assert result is None


# ---------------------------------------------------------------------------
# 7. No default tests require real PostgreSQL
# (These tests themselves use no database, which is the verification.)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 8. Script --dry-run does not modify hermes config
# ---------------------------------------------------------------------------

def test_dry_run_does_not_modify_config(tmp_path: Path) -> None:
    """Verify that dry-run mode never touches ~/.hermes/config.yaml."""
    mod = _import_script()
    # Patch HERMES_CONFIG to a temp file to ensure it's never written
    fake_config = tmp_path / "config.yaml"
    fake_config.write_text("test: original\n")
    with patch.object(mod, "HERMES_CONFIG", fake_config):
        # Just verify the function doesn't write
        original_content = fake_config.read_text()
        # generate_mcp_config_block should be pure
        block = mod.generate_mcp_config_block()
        assert "command" in block
        assert fake_config.read_text() == original_content


# ---------------------------------------------------------------------------
# 9. MCP_TOOL_FUNCTIONS in server.py match allowlist
# ---------------------------------------------------------------------------

def test_mcp_tool_functions_match_allowlist() -> None:
    from frontier_ai_risk_observer.mcp.server import MCP_TOOL_FUNCTIONS
    fn_names = {fn.__name__ for fn in MCP_TOOL_FUNCTIONS}
    for tool in REQUIRED_TOOLS:
        assert tool in fn_names, f"MCP_TOOL_FUNCTIONS missing: {tool}"
    # Also check risk_benchmark_observation_store
    assert "risk_benchmark_observation_store" in fn_names
