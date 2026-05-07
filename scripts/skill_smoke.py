"""Skill smoke test — validates bundled skill files and plugin-first content.

Checks:
  - Main SKILL.md exists
  - All reference files exist
  - SKILL.md mentions plugin tools (owl_*)
  - SKILL.md mentions MCP fallback
  - Reference files contain expected content
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO_ROOT / "skills" / "ai-risk-signal-observer"
REFERENCES_DIR = SKILL_DIR / "references"

EXPECTED_REFERENCES = [
    "source-policy.md",
    "signal-rubric.md",
    "evidence-policy.md",
    "live-vault-workflow.md",
    "final-report-format.md",
    "plugin-tool-guide.md",
    "mcp-legacy-guide.md",
    "obsidian-review-workflow.md",
    "source-reliability-known-issues.md",
]


def main() -> int:
    errors = []

    # 1. SKILL.md exists
    skill_md = SKILL_DIR / "SKILL.md"
    if skill_md.exists():
        print("[OK] SKILL.md exists")
        content = skill_md.read_text(encoding="utf-8")
    else:
        errors.append("SKILL.md not found")
        print("[FAIL] SKILL.md not found")
        return 1

    # 2. Plugin-first language
    plugin_tools = ["owl_risk_state", "owl_risk_discovery", "owl_live_vault",
                    "owl_report_quality", "owl_obsidian_export"]
    found_tools = [t for t in plugin_tools if t in content]
    if len(found_tools) >= 3:
        print(f"[OK] SKILL.md mentions plugin tools: {found_tools}")
    else:
        errors.append(f"SKILL.md missing plugin tools (found {found_tools}, expected at least 3)")
        print(f"[FAIL] SKILL.md plugin tools: {found_tools}")

    # 3. MCP fallback
    if "MCP" in content or "mcp" in content.lower() or "risk_" in content:
        print("[OK] SKILL.md mentions MCP fallback")
    else:
        errors.append("SKILL.md does not mention MCP fallback")
        print("[FAIL] SKILL.md missing MCP fallback")

    # 4. References directory
    if REFERENCES_DIR.exists():
        print(f"[OK] References directory exists: {REFERENCES_DIR}")
    else:
        errors.append("References directory not found")
        print("[FAIL] References directory missing")
        return 1

    # 5. All expected references exist
    for ref_name in EXPECTED_REFERENCES:
        ref_path = REFERENCES_DIR / ref_name
        if ref_path.exists():
            print(f"[OK] Reference exists: {ref_name}")
        else:
            errors.append(f"Reference missing: {ref_name}")
            print(f"[FAIL] Reference missing: {ref_name}")

    # 6. Content checks
    content_checks = [
        ("source-policy.md", ["no_cloudflare_bypass", "No Cloudflare"]),
        ("signal-rubric.md", ["what changed", "why does it matter"]),
        ("evidence-policy.md", ["evidence_excerpt", "claim_text"]),
        ("live-vault-workflow.md", ["start_run", "finalize_run"]),
        ("plugin-tool-guide.md", ["owl_risk_state", "owl_risk_discovery"]),
        ("mcp-legacy-guide.md", ["MCP", "fallback"]),
    ]
    for ref_name, keywords in content_checks:
        ref_path = REFERENCES_DIR / ref_name
        if not ref_path.exists():
            continue
        content = ref_path.read_text(encoding="utf-8").lower()
        found = any(kw.lower() in content for kw in keywords)
        if found:
            print(f"[OK] {ref_name} has expected content")
        else:
            errors.append(f"{ref_name} missing expected keywords: {keywords}")
            print(f"[FAIL] {ref_name} content check failed")

    # 7. Source policy no anti-bot bypass
    sp = REFERENCES_DIR / "source-policy.md"
    if sp.exists():
        sp_content = sp.read_text(encoding="utf-8")
        if "no_cloudflare_bypass" in sp_content.lower().replace(" ", "") or \
           "No Cloudflare/CAPTCHA bypass" in sp_content:
            print("[OK] source-policy mentions no anti-bot bypass")
        else:
            errors.append("source-policy does not mention anti-bot bypass prohibition")
            print("[FAIL] source-policy anti-bot check")

    # Summary
    print(f"\n{'='*40}")
    if errors:
        print(f"FAILED: {len(errors)} error(s)")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("PASSED: All skill smoke checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
