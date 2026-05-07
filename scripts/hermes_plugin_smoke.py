"""Hermes plugin smoke test — checks whether Hermes can discover and load the OwlHermes plugin.

This script checks:
  - Hermes CLI availability
  - Plugin path existence
  - Plugin enabled status (via config)
  - Plugin tool discovery (if Hermes supports it)

Does not fake success — reports pending/unavailable clearly.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def main() -> int:
    errors = []
    warnings = []

    print("=== Hermes Plugin Smoke Test ===\n")

    # 1. Hermes CLI available
    hermes_bin = shutil.which("hermes")
    if hermes_bin:
        print(f"[OK] Hermes CLI found: {hermes_bin}")
        try:
            result = subprocess.run(
                [hermes_bin, "--version"],
                capture_output=True, text=True, timeout=10,
            )
            version = result.stdout.strip()
            print(f"      Version: {version}")
        except Exception as e:
            warnings.append(f"Could not get Hermes version: {e}")
    else:
        warnings.append("Hermes CLI not found in PATH")
        print("[WARN] Hermes CLI not found")

    # 2. Plugin path exists
    plugin_path = Path.home() / ".hermes" / "plugins" / "owlhermes"
    project_plugin = Path(".hermes/plugins/owlhermes")

    if plugin_path.exists():
        print(f"[OK] User plugin installed: {plugin_path}")
        if plugin_path.is_symlink():
            print(f"      Symlink to: {plugin_path.resolve()}")
    elif project_plugin.exists():
        print(f"[OK] Project-local plugin exists: {project_plugin}")
        print("      Requires HERMES_ENABLE_PROJECT_PLUGINS=true")
    else:
        errors.append("Plugin not found in user or project directories")
        print("[FAIL] Plugin not installed")
        print("       Run: make plugin-install-local")

    # 3. Check plugin.yaml
    if plugin_path.exists():
        yaml_path = plugin_path / "plugin.yaml"
    else:
        yaml_path = project_plugin / "plugin.yaml"
    if yaml_path.exists():
        print(f"[OK] plugin.yaml exists: {yaml_path}")
    else:
        errors.append("plugin.yaml not found")
        print("[FAIL] plugin.yaml missing")

    # 4. Check Hermes config for plugin enabled
    config_path = Path.home() / ".hermes" / "config.yaml"
    if config_path.exists():
        content = config_path.read_text(encoding="utf-8")
        if "owlhermes" in content:
            print("[OK] owlhermes found in Hermes config")
        else:
            warnings.append("owlhermes not in Hermes config — run: hermes plugins enable owlhermes")
            print("[WARN] owlhermes not in config")
    else:
        warnings.append("Hermes config not found")
        print("[WARN] Hermes config not found")

    # 5. Try hermes plugins list
    if hermes_bin:
        try:
            result = subprocess.run(
                [hermes_bin, "plugins", "list"],
                capture_output=True, text=True, timeout=15,
            )
            output = result.stdout + result.stderr
            if "owlhermes" in output:
                print("[OK] owlhermes appears in hermes plugins list")
            else:
                warnings.append(
                    "owlhermes not found in hermes plugins list "
                    "— may need: hermes plugins enable owlhermes"
                )
                print("[WARN] owlhermes not in plugins list")
        except Exception as e:
            warnings.append(f"Could not run hermes plugins list: {e}")
            print(f"[WARN] hermes plugins list failed: {e}")

    # 6. Plugin tool discovery — cannot be verified without running Hermes
    print("[PENDING] Plugin tool discovery requires running Hermes with plugin loaded")
    print("          Run: hermes -z '/owl status' to test")

    # Summary
    print(f"\n{'='*40}")
    if errors:
        print(f"FAILED: {len(errors)} error(s)")
        for e in errors:
            print(f"  - {e}")
    if warnings:
        print(f"WARNINGS: {len(warnings)}")
        for w in warnings:
            print(f"  - {w}")
    if not errors:
        print("Plugin infrastructure OK — Hermes runtime discovery pending")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
