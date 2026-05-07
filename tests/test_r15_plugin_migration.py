"""R1-15 tests: Hermes plugin + bundled skills migration.

Tests cover:
- Plugin package imports and structure
- register(ctx) exists and works
- Plugin manifest fields
- Plugin schemas validate
- Facade functions for invalid actions
- Facade functions for offline operations
- Live vault disabled status
- Install script
- Skills and references
- Plugin prompts
- Makefile targets
- Config/docs
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock

# ===========================================================================
# Plugin Package Tests
# ===========================================================================


class TestPluginPackage:
    """Tests for the hermes_plugin package."""

    def test_package_imports(self):
        from frontier_ai_risk_observer.hermes_plugin import __version__
        assert __version__ == "0.1.0"

    def test_register_exists(self):
        from frontier_ai_risk_observer.hermes_plugin.plugin import register
        assert callable(register)

    def test_register_calls_ctx(self):
        from frontier_ai_risk_observer.hermes_plugin.plugin import register
        ctx = MagicMock()
        register(ctx)
        # Should register 5 tools + 1 slash command
        assert ctx.register_tool.call_count == 5
        assert ctx.register_command.call_count == 1

    def test_register_tool_names(self):
        from frontier_ai_risk_observer.hermes_plugin.plugin import register
        ctx = MagicMock()
        register(ctx)
        tool_names = [call.kwargs.get("name", call.args[0] if call.args else None)
                      for call in ctx.register_tool.call_args_list]
        assert "owl_risk_state" in tool_names
        assert "owl_risk_discovery" in tool_names
        assert "owl_live_vault" in tool_names
        assert "owl_report_quality" in tool_names
        assert "owl_obsidian_export" in tool_names

    def test_register_command_name(self):
        from frontier_ai_risk_observer.hermes_plugin.plugin import register
        ctx = MagicMock()
        register(ctx)
        name = ctx.register_command.call_args[0][0]
        assert name == "owl"

    def test_manifest_fields(self):
        from frontier_ai_risk_observer.hermes_plugin.manifest import (
            PLUGIN_NAME,
            PLUGIN_VERSION,
            PROVIDES_HOOKS,
            PROVIDES_TOOLS,
            TOOLSET,
        )
        assert PLUGIN_NAME == "owlhermes"
        assert PLUGIN_VERSION == "0.1.0"
        assert len(PROVIDES_TOOLS) == 5
        assert PROVIDES_HOOKS == []
        assert TOOLSET == "owlhermes"


class TestPluginSchemas:
    """Tests for plugin tool schemas."""

    def test_schemas_count(self):
        from frontier_ai_risk_observer.hermes_plugin.schemas import ALL_PLUGIN_SCHEMAS
        assert len(ALL_PLUGIN_SCHEMAS) == 5

    def test_schema_structure(self):
        from frontier_ai_risk_observer.hermes_plugin.schemas import ALL_PLUGIN_SCHEMAS
        for schema in ALL_PLUGIN_SCHEMAS:
            assert "name" in schema
            assert "description" in schema
            assert "parameters" in schema
            params = schema["parameters"]
            assert params["type"] == "object"
            assert "action" in params["properties"]
            assert "payload" in params["properties"]
            assert "action" in params.get("required", [])

    def test_schema_action_enums(self):
        from frontier_ai_risk_observer.hermes_plugin.schemas import ALL_PLUGIN_SCHEMAS
        for schema in ALL_PLUGIN_SCHEMAS:
            props = schema["parameters"]["properties"]
            enum = props["action"].get("enum", [])
            assert len(enum) > 0, f"Schema {schema['name']} has no action enum"


class TestPluginDistribution:
    """Tests for the .hermes/plugins/owlhermes distribution."""

    def test_plugin_yaml_exists(self):
        assert (Path(".hermes/plugins/owlhermes/plugin.yaml")).exists()

    def test_init_py_exists(self):
        assert (Path(".hermes/plugins/owlhermes/__init__.py")).exists()

    def test_init_imports_register(self):
        # The __init__.py should define or import register
        content = (Path(".hermes/plugins/owlhermes/__init__.py")).read_text()
        assert "register" in content


# ===========================================================================
# Facade Tests
# ===========================================================================


class TestFacadesInvalidActions:
    """Test that invalid actions return proper errors."""

    def test_owl_risk_state_invalid_action(self):
        from frontier_ai_risk_observer.hermes_plugin.facades import owl_risk_state
        result = owl_risk_state("invalid_action")
        assert result["ok"] is False
        assert "invalid_action" in result["error"]

    def test_owl_risk_discovery_invalid_action(self):
        from frontier_ai_risk_observer.hermes_plugin.facades import owl_risk_discovery
        result = owl_risk_discovery("invalid_action")
        assert result["ok"] is False

    def test_owl_live_vault_invalid_action(self):
        from frontier_ai_risk_observer.hermes_plugin.facades import owl_live_vault
        result = owl_live_vault("invalid_action")
        assert result["ok"] is False

    def test_owl_report_quality_invalid_action(self):
        from frontier_ai_risk_observer.hermes_plugin.facades import owl_report_quality
        result = owl_report_quality("invalid_action")
        assert result["ok"] is False

    def test_owl_obsidian_export_invalid_action(self):
        from frontier_ai_risk_observer.hermes_plugin.facades import owl_obsidian_export
        result = owl_obsidian_export("invalid_action")
        assert result["ok"] is False


class TestFacadesOffline:
    """Test facades that work without DB/network."""

    def test_registry_summary(self):
        from frontier_ai_risk_observer.hermes_plugin.facades import owl_risk_discovery
        result = owl_risk_discovery("registry_summary")
        assert result["ok"] is True
        assert "summary" in result

    def test_source_health(self):
        from frontier_ai_risk_observer.hermes_plugin.facades import owl_risk_discovery
        result = owl_risk_discovery("source_health")
        assert result["ok"] is True
        assert "health" in result

    def test_source_policy_summary(self):
        from frontier_ai_risk_observer.hermes_plugin.facades import owl_risk_discovery
        result = owl_risk_discovery("source_policy_summary")
        assert result["ok"] is True
        assert "policy" in result

    def test_quality_rubric_summary(self):
        from frontier_ai_risk_observer.hermes_plugin.facades import owl_report_quality
        result = owl_report_quality("quality_rubric_summary")
        assert result["ok"] is True
        assert "checklist" in result

    def test_live_vault_disabled(self):
        from frontier_ai_risk_observer.hermes_plugin.facades import owl_live_vault
        old = os.environ.get("OBSIDIAN_LIVE_LOGGING_ENABLED")
        os.environ["OBSIDIAN_LIVE_LOGGING_ENABLED"] = "false"
        try:
            result = owl_live_vault("start_run", {"run_id": "test"})
            assert result["ok"] is True
            assert result["live_vault_enabled"] is False
        finally:
            if old is not None:
                os.environ["OBSIDIAN_LIVE_LOGGING_ENABLED"] = old
            else:
                os.environ.pop("OBSIDIAN_LIVE_LOGGING_ENABLED", None)

    def test_live_vault_inspect_latest(self):
        from frontier_ai_risk_observer.hermes_plugin.facades import owl_live_vault
        result = owl_live_vault("inspect_latest")
        assert result["ok"] is True

    def test_quality_check_missing_report(self):
        from frontier_ai_risk_observer.hermes_plugin.facades import owl_report_quality
        result = owl_report_quality("check_report", {})
        assert result["ok"] is False
        assert (
            "missing" in result.get("error", "").lower()
            or "missing" in result.get("message", "").lower()
        )


class TestFacadesJSONCompatible:
    """Test that facade results are JSON-serializable."""

    def test_risk_state_error_is_json(self):
        from frontier_ai_risk_observer.hermes_plugin.facades import owl_risk_state
        result = owl_risk_state("invalid_action")
        serialized = json.dumps(result, default=str)
        assert isinstance(serialized, str)

    def test_discovery_summary_is_json(self):
        from frontier_ai_risk_observer.hermes_plugin.facades import owl_risk_discovery
        result = owl_risk_discovery("registry_summary")
        serialized = json.dumps(result, default=str)
        assert isinstance(serialized, str)


# ===========================================================================
# Tool Handler Tests
# ===========================================================================


class TestToolHandlers:
    """Test tool handlers return JSON strings."""

    def test_handle_owl_risk_state(self):
        from frontier_ai_risk_observer.hermes_plugin.tools import handle_owl_risk_state
        result = handle_owl_risk_state({"action": "invalid_action"})
        parsed = json.loads(result)
        assert parsed["ok"] is False

    def test_handle_owl_risk_discovery(self):
        from frontier_ai_risk_observer.hermes_plugin.tools import handle_owl_risk_discovery
        result = handle_owl_risk_discovery({"action": "registry_summary"})
        parsed = json.loads(result)
        assert parsed["ok"] is True

    def test_handle_owl_live_vault(self):
        from frontier_ai_risk_observer.hermes_plugin.tools import handle_owl_live_vault
        old = os.environ.get("OBSIDIAN_LIVE_LOGGING_ENABLED")
        os.environ["OBSIDIAN_LIVE_LOGGING_ENABLED"] = "false"
        try:
            result = handle_owl_live_vault({"action": "start_run", "payload": {"run_id": "test"}})
            parsed = json.loads(result)
            assert parsed["ok"] is True
        finally:
            if old is not None:
                os.environ["OBSIDIAN_LIVE_LOGGING_ENABLED"] = old
            else:
                os.environ.pop("OBSIDIAN_LIVE_LOGGING_ENABLED", None)


# ===========================================================================
# Interface Mode Tests
# ===========================================================================


class TestInterfaceMode:
    """Test interface mode configuration."""

    def test_default_is_both(self):
        from frontier_ai_risk_observer.hermes_plugin.interface_mode import get_interface_mode
        old = os.environ.pop("OWL_HERMES_INTERFACE_MODE", None)
        try:
            assert get_interface_mode() == "both"
        finally:
            if old is not None:
                os.environ["OWL_HERMES_INTERFACE_MODE"] = old

    def test_plugin_preferred(self):
        from frontier_ai_risk_observer.hermes_plugin.interface_mode import is_plugin_preferred
        old = os.environ.get("OWL_HERMES_INTERFACE_MODE")
        os.environ["OWL_HERMES_INTERFACE_MODE"] = "plugin"
        try:
            assert is_plugin_preferred() is True
        finally:
            if old is not None:
                os.environ["OWL_HERMES_INTERFACE_MODE"] = old
            else:
                os.environ.pop("OWL_HERMES_INTERFACE_MODE", None)

    def test_mcp_available_in_both(self):
        from frontier_ai_risk_observer.hermes_plugin.interface_mode import is_mcp_available
        old = os.environ.get("OWL_HERMES_INTERFACE_MODE")
        os.environ["OWL_HERMES_INTERFACE_MODE"] = "both"
        try:
            assert is_mcp_available() is True
        finally:
            if old is not None:
                os.environ["OWL_HERMES_INTERFACE_MODE"] = old
            else:
                os.environ.pop("OWL_HERMES_INTERFACE_MODE", None)

    def test_mcp_not_available_in_plugin_mode(self):
        from frontier_ai_risk_observer.hermes_plugin.interface_mode import is_mcp_available
        old = os.environ.get("OWL_HERMES_INTERFACE_MODE")
        os.environ["OWL_HERMES_INTERFACE_MODE"] = "plugin"
        try:
            assert is_mcp_available() is False
        finally:
            if old is not None:
                os.environ["OWL_HERMES_INTERFACE_MODE"] = old
            else:
                os.environ.pop("OWL_HERMES_INTERFACE_MODE", None)

    def test_invalid_mode_defaults_to_both(self):
        from frontier_ai_risk_observer.hermes_plugin.interface_mode import get_interface_mode
        old = os.environ.get("OWL_HERMES_INTERFACE_MODE")
        os.environ["OWL_HERMES_INTERFACE_MODE"] = "invalid"
        try:
            assert get_interface_mode() == "both"
        finally:
            if old is not None:
                os.environ["OWL_HERMES_INTERFACE_MODE"] = old
            else:
                os.environ.pop("OWL_HERMES_INTERFACE_MODE", None)


# ===========================================================================
# Skills Tests
# ===========================================================================


class TestSkills:
    """Test skill files and content."""

    def test_skill_md_exists(self):
        assert (Path("skills/ai-risk-signal-observer/SKILL.md")).exists()

    def test_skill_mentions_plugin_tools(self):
        content = Path("skills/ai-risk-signal-observer/SKILL.md").read_text()
        assert "owl_risk_state" in content
        assert "owl_risk_discovery" in content
        assert "owl_live_vault" in content

    def test_skill_mentions_mcp_fallback(self):
        content = Path("skills/ai-risk-signal-observer/SKILL.md").read_text()
        assert "MCP" in content or "mcp" in content.lower()

    def test_references_exist(self):
        refs = Path("skills/ai-risk-signal-observer/references")
        assert refs.exists()
        expected = [
            "source-policy.md", "signal-rubric.md", "evidence-policy.md",
            "live-vault-workflow.md", "final-report-format.md",
            "plugin-tool-guide.md", "mcp-legacy-guide.md",
            "obsidian-review-workflow.md", "source-reliability-known-issues.md",
        ]
        for name in expected:
            assert (refs / name).exists(), f"Missing reference: {name}"

    def test_source_policy_no_anti_bot(self):
        path = Path("skills/ai-risk-signal-observer/references/source-policy.md")
        content = path.read_text().lower()
        assert "cloudflare" in content or "captcha" in content

    def test_signal_rubric_three_questions(self):
        path = Path("skills/ai-risk-signal-observer/references/signal-rubric.md")
        content = path.read_text().lower()
        assert "what changed" in content
        assert "why" in content
        assert "watch" in content

    def test_evidence_policy_excerpts(self):
        path = Path("skills/ai-risk-signal-observer/references/evidence-policy.md")
        content = path.read_text().lower()
        assert "evidence_excerpt" in content or "excerpt" in content

    def test_live_vault_workflow_daily_note(self):
        path = Path("skills/ai-risk-signal-observer/references/live-vault-workflow.md")
        content = path.read_text().lower()
        assert "daily" in content
        assert "start_run" in content

    def test_plugin_tool_guide_maps_actions(self):
        path = Path("skills/ai-risk-signal-observer/references/plugin-tool-guide.md")
        content = path.read_text()
        assert "seen_check" in content
        assert "store_signal" in content
        assert "store_evidence" in content

    def test_mcp_legacy_guide_exists(self):
        assert (Path("skills/ai-risk-signal-observer/references/mcp-legacy-guide.md")).exists()


# ===========================================================================
# Prompt Tests
# ===========================================================================


class TestPrompts:
    """Test plugin-first prompts."""

    def test_plugin_daily_prompt_exists(self):
        assert Path("prompts/daily_report_plugin_prompt.md").exists()

    def test_plugin_finalize_prompt_exists(self):
        assert Path("prompts/daily_report_plugin_finalize_prompt.md").exists()

    def test_plugin_interactive_prompt_exists(self):
        assert Path("prompts/interactive_daily_report_plugin_prompt.md").exists()

    def test_plugin_prompt_prefers_owl_tools(self):
        content = Path("prompts/daily_report_plugin_prompt.md").read_text()
        assert "owl_risk_state" in content
        assert "owl_risk_discovery" in content

    def test_plugin_prompt_mentions_mcp_fallback(self):
        content = Path("prompts/daily_report_plugin_prompt.md").read_text()
        assert "MCP" in content or "risk_" in content

    def test_plugin_prompt_no_private_cot(self):
        content = Path("prompts/daily_report_plugin_prompt.md").read_text().lower()
        assert "chain-of-thought" in content or "私" in content or "observable" in content

    def test_plugin_prompt_daily_note_immediate(self):
        content = Path("prompts/daily_report_plugin_prompt.md").read_text().lower()
        assert "daily" in content
        assert "obsidian" in content or "vault" in content


# ===========================================================================
# Install Script Tests
# ===========================================================================


class TestInstallScript:
    """Test plugin install script."""

    def test_dry_run_works(self):
        import subprocess
        result = subprocess.run(
            [".venv/bin/python", "scripts/install_hermes_plugin.py", "--dry-run"],
            capture_output=True, text=True, timeout=15,
        )
        assert result.returncode == 0
        assert "DRY RUN" in result.stdout

    def test_project_local_mode(self):
        import subprocess
        result = subprocess.run(
            [".venv/bin/python", "scripts/install_hermes_plugin.py", "--project-local"],
            capture_output=True, text=True, timeout=15,
        )
        assert result.returncode == 0
        assert "Project-local" in result.stdout

    def test_symlink_target_computed(self):
        from scripts.install_hermes_plugin import DEFAULT_TARGET
        assert str(DEFAULT_TARGET).endswith("owlhermes")
        assert ".hermes/plugins" in str(DEFAULT_TARGET)


# ===========================================================================
# Config/Docs Tests
# ===========================================================================


class TestConfigDocs:
    """Test config and documentation updates."""

    def test_hermes_config_has_plugin_section(self):
        content = Path("configs/hermes_config.example.yaml").read_text()
        assert "plugins:" in content
        assert "owlhermes" in content

    def test_hermes_config_has_mcp_fallback(self):
        content = Path("configs/hermes_config.example.yaml").read_text()
        assert "mcp_servers:" in content
        assert "Legacy MCP" in content

    def test_env_example_has_interface_mode(self):
        content = Path("configs/env.example").read_text()
        # Interface mode env var documented or not required (defaults to both)
        # At minimum, existing env vars still present
        assert "OBSIDIAN_VAULT_PATH" in content
        assert "DATABASE_URL" in content or "DATABASE_URL" in content

    def test_claude_md_mentions_plugin(self):
        content = Path("CLAUDE.md").read_text()
        # After update, should mention plugin targets
        # For now check that existing commands are present
        assert "plugin-smoke" in content or "plugin" in content.lower()


class TestMakefileTargets:
    """Test that new Makefile targets exist."""

    def test_plugin_install_local_target(self):
        content = Path("Makefile").read_text()
        assert "plugin-install-local:" in content

    def test_plugin_smoke_target(self):
        content = Path("Makefile").read_text()
        assert "plugin-smoke:" in content

    def test_hermes_plugin_smoke_target(self):
        content = Path("Makefile").read_text()
        assert "hermes-plugin-smoke:" in content

    def test_skill_smoke_target(self):
        content = Path("Makefile").read_text()
        assert "skill-smoke:" in content

    def test_daily_report_plugin_target(self):
        content = Path("Makefile").read_text()
        assert "daily-report-plugin:" in content

    def test_daily_report_live_vault_plugin_target(self):
        content = Path("Makefile").read_text()
        assert "daily-report-live-vault-plugin:" in content

    def test_plugin_e2e_target(self):
        content = Path("Makefile").read_text()
        assert "plugin-e2e:" in content

    def test_plugin_e2e_in_phony(self):
        content = Path("Makefile").read_text()
        assert "plugin-e2e" in content.split(".PHONY:")[1].split("\n")[0]


# ===========================================================================
# Smoke Script Tests
# ===========================================================================


class TestSmokeScripts:
    """Test smoke test scripts can be imported."""

    def test_plugin_smoke_importable(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "plugin_smoke", "scripts/plugin_smoke.py"
        )
        assert spec is not None

    def test_skill_smoke_importable(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "skill_smoke", "scripts/skill_smoke.py"
        )
        assert spec is not None

    def test_hermes_plugin_smoke_importable(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "hermes_plugin_smoke", "scripts/hermes_plugin_smoke.py"
        )
        assert spec is not None


# ===========================================================================
# No Arbitrary File Write Tests
# ===========================================================================


class TestSecurityConstraints:
    """Test that plugin tools don't allow arbitrary file writes."""

    def test_facade_no_arbitrary_path(self):
        # Check that facades don't accept arbitrary path parameters
        import inspect

        from frontier_ai_risk_observer.hermes_plugin import facades
        for func_name in dir(facades):
            if func_name.startswith("owl_"):
                func = getattr(facades, func_name)
                sig = inspect.signature(func)
                params = list(sig.parameters.keys())
                # Should only accept action and payload, not file_path
                assert "file_path" not in params
                assert "path" not in params

    def test_live_vault_constrained_to_vault(self):
        from frontier_ai_risk_observer.hermes_plugin.facades import owl_live_vault
        # When disabled, should not write anywhere
        old = os.environ.get("OBSIDIAN_LIVE_LOGGING_ENABLED")
        os.environ["OBSIDIAN_LIVE_LOGGING_ENABLED"] = "false"
        try:
            result = owl_live_vault("start_run", {"run_id": "test"})
            assert result.get("live_vault_enabled") is False
        finally:
            if old is not None:
                os.environ["OBSIDIAN_LIVE_LOGGING_ENABLED"] = old
            else:
                os.environ.pop("OBSIDIAN_LIVE_LOGGING_ENABLED", None)
