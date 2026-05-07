"""Plugin smoke test — validates OwlHermes plugin package without Hermes runtime.

Checks:
  - hermes_plugin package imports
  - register(ctx) function exists
  - Plugin manifest exists and has expected fields
  - All 5 plugin tools are defined
  - Schemas validate
  - Facade functions return JSON-compatible data for invalid actions
  - Live vault disabled returns proper status
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    errors = []

    # 1. Import plugin package
    try:
        from frontier_ai_risk_observer.hermes_plugin import __version__
        print(f"[OK] Plugin package imports (version {__version__})")
    except Exception as e:
        errors.append(f"Plugin package import failed: {e}")
        print(f"[FAIL] Plugin package import: {e}")
        # Can't continue
        return 1

    # 2. register(ctx) exists
    try:
        from frontier_ai_risk_observer.hermes_plugin.plugin import register
        assert callable(register), "register is not callable"
        print("[OK] register(ctx) function exists")
    except Exception as e:
        errors.append(f"register(ctx) not found: {e}")
        print(f"[FAIL] register(ctx): {e}")

    # 3. Manifest
    try:
        from frontier_ai_risk_observer.hermes_plugin.manifest import (
            PLUGIN_NAME,
            PLUGIN_VERSION,
            PROVIDES_TOOLS,
        )
        assert PLUGIN_NAME == "owlhermes"
        assert len(PROVIDES_TOOLS) == 5
        print(
            f"[OK] Manifest: name={PLUGIN_NAME}, "
            f"version={PLUGIN_VERSION}, tools={PROVIDES_TOOLS}"
        )
    except Exception as e:
        errors.append(f"Manifest check failed: {e}")
        print(f"[FAIL] Manifest: {e}")

    # 4. plugin.yaml
    plugin_yaml = REPO_ROOT / ".hermes" / "plugins" / "owlhermes" / "plugin.yaml"
    if plugin_yaml.exists():
        print(f"[OK] plugin.yaml exists at {plugin_yaml}")
    else:
        errors.append(f"plugin.yaml not found at {plugin_yaml}")
        print("[FAIL] plugin.yaml: not found")

    # 5. Schemas
    try:
        from frontier_ai_risk_observer.hermes_plugin.schemas import ALL_PLUGIN_SCHEMAS
        assert len(ALL_PLUGIN_SCHEMAS) == 5
        for schema in ALL_PLUGIN_SCHEMAS:
            assert "name" in schema
            assert "description" in schema
            assert "parameters" in schema
            props = schema["parameters"].get("properties", {})
            assert "action" in props
            assert "payload" in props
            assert "enum" in props["action"]
        print("[OK] All 5 schemas validated")
    except Exception as e:
        errors.append(f"Schema validation failed: {e}")
        print(f"[FAIL] Schemas: {e}")

    # 6. Facade functions exist
    try:
        from frontier_ai_risk_observer.hermes_plugin.facades import (
            owl_live_vault,
            owl_obsidian_export,
            owl_report_quality,
            owl_risk_discovery,
            owl_risk_state,
        )
        print("[OK] All 5 facade functions importable")
    except Exception as e:
        errors.append(f"Facade import failed: {e}")
        print(f"[FAIL] Facades: {e}")

    # 7. Invalid action returns error
    try:
        result = owl_risk_state("invalid_action")
        assert result.get("ok") is False
        assert "invalid_action" in result.get("error", "")
        result = owl_risk_discovery("invalid_action")
        assert result.get("ok") is False
        result = owl_live_vault("invalid_action")
        assert result.get("ok") is False
        result = owl_report_quality("invalid_action")
        assert result.get("ok") is False
        result = owl_obsidian_export("invalid_action")
        assert result.get("ok") is False
        print("[OK] Invalid actions return proper errors")
    except Exception as e:
        errors.append(f"Invalid action test failed: {e}")
        print(f"[FAIL] Invalid actions: {e}")

    # 8. Live vault disabled status
    try:
        import os
        old = os.environ.get("OBSIDIAN_LIVE_LOGGING_ENABLED")
        os.environ["OBSIDIAN_LIVE_LOGGING_ENABLED"] = "false"
        result = owl_live_vault("start_run", {"run_id": "test"})
        assert result.get("ok") is True
        assert result.get("live_vault_enabled") is False
        if old is not None:
            os.environ["OBSIDIAN_LIVE_LOGGING_ENABLED"] = old
        else:
            os.environ.pop("OBSIDIAN_LIVE_LOGGING_ENABLED", None)
        print("[OK] Live vault disabled returns proper status")
    except Exception as e:
        errors.append(f"Live vault disabled test failed: {e}")
        print(f"[FAIL] Live vault disabled: {e}")

    # 9. Registry discovery (offline)
    try:
        result = owl_risk_discovery("registry_summary")
        assert result.get("ok") is True
        summary = result.get("summary", {})
        assert isinstance(summary, dict)
        print(f"[OK] Registry summary works offline: {summary}")
    except Exception as e:
        errors.append(f"Registry summary failed: {e}")
        print(f"[FAIL] Registry summary: {e}")

    # 10. Source health (offline)
    try:
        result = owl_risk_discovery("source_health")
        assert result.get("ok") is True
        print("[OK] Source health works offline")
    except Exception as e:
        errors.append(f"Source health failed: {e}")
        print(f"[FAIL] Source health: {e}")

    # Summary
    print(f"\n{'='*40}")
    if errors:
        print(f"FAILED: {len(errors)} error(s)")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("PASSED: All plugin smoke checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
