# R1-15: Full Hermes Plugin + Bundled Skills Migration

## Summary

Migrated OwlHermes from MCP-only integration to a Hermes-native plugin with bundled skills. The plugin is now the preferred integration surface; MCP remains as legacy fallback.

## What Changed

### 1. Plugin Package (`frontier_ai_risk_observer/hermes_plugin/`)

A canonical Hermes plugin package providing 5 facade tools with action-based dispatch:

| Tool | Actions | Purpose |
|------|---------|---------|
| `owl_risk_state` | 11 | Deterministic state operations (seen_check, store_raw_item, store_evidence, store_signal, store_digest, etc.) |
| `owl_risk_discovery` | 8 | Source registry and discovery (registry_summary, list_due_sources, source_health, helper_preview, etc.) |
| `owl_live_vault` | 6 | Live Obsidian research logging (start_run, append_event, upsert_note, upsert_daily_report, finalize_run) |
| `owl_report_quality` | 4 | Report quality checks (check_report, review_queue_summary, quality_rubric_summary) |
| `owl_obsidian_export` | 4 | Vault export/backfill (export_latest, dry_run, inspect) |

Each tool uses JSON Schema with `action` enum + `payload` object. Handlers return JSON strings.

### 2. Plugin Distribution (`.hermes/plugins/owlhermes/`)

Project-local plugin directory with `plugin.yaml` manifest and `__init__.py` that imports `register` from the Python package. This allows `hermes plugins enable owlhermes` to discover the plugin when `HERMES_ENABLE_PROJECT_PLUGINS=true`.

### 3. Install Script (`scripts/install_hermes_plugin.py`)

Supports `--mode symlink|copy`, `--project-local`, and `--dry-run`. Creates the distribution directory from the Python package source.

### 4. Skill Refactoring (`skills/ai-risk-signal-observer/`)

SKILL.md rewritten to be concise and plugin-first. Detailed content split into 9 reference files:

- `source-policy.md` — source reliability tiers, helper types, no-anti-bot policy
- `signal-rubric.md` — 3 core questions, signal vs candidate, quality rules
- `evidence-policy.md` — evidence fields, storage, missing evidence handling
- `live-vault-workflow.md` — live vault actions, auto-mirror, rules
- `final-report-format.md` — Chinese report structure, quality requirements
- `plugin-tool-guide.md` — action-by-action mapping with payload examples
- `mcp-legacy-guide.md` — MCP fallback tools and known quirks
- `obsidian-review-workflow.md` — vault structure, review queue
- `source-reliability-known-issues.md` — failing sources, MCP failure patterns

### 5. Plugin-First Prompts

Three new prompt files using `owl_*` tool references with MCP fallback notes:
- `prompts/daily_report_plugin_prompt.md`
- `prompts/daily_report_plugin_finalize_prompt.md`
- `prompts/interactive_daily_report_plugin_prompt.md`

### 6. Interface Mode

`OWL_HERMES_INTERFACE_MODE` env var: `plugin` (plugin only), `mcp` (MCP only), `both` (default — plugin preferred, MCP available).

### 7. Makefile Targets

8 new targets: `plugin-install-local`, `plugin-install-local-copy`, `plugin-smoke`, `hermes-plugin-smoke`, `skill-smoke`, `daily-report-plugin`, `daily-report-live-vault-plugin`, `plugin-e2e`.

### 8. `/owl` Slash Command

Registers `/owl status|health|tools` command for quick status checks within Hermes sessions.

## Architecture

```
Plugin (preferred)                    MCP (legacy fallback)
┌─────────────────────┐              ┌──────────────────────┐
│ owl_risk_state      │              │ risk_raw_item_*      │
│ owl_risk_discovery  │              │ risk_registry_*      │
│ owl_live_vault      │              │ risk_signal_*        │
│ owl_report_quality  │              │ risk_evidence_*      │
│ owl_obsidian_export │              │ risk_live_*          │
│ /owl command        │              │ risk_digest_*        │
└────────┬────────────┘              └──────────┬───────────┘
         │                                      │
         ▼                                      ▼
   facades.py ──── services/ ──── db/ ──── models/
```

Both surfaces call the same deterministic backend services. The plugin surface is action-based (5 tools with enum actions), while MCP has 18+ individual tool functions.

## Migration Path

1. `make plugin-install-local` — install plugin to project-local `.hermes/plugins/`
2. `hermes plugins enable owlhermes` — or add to config.yaml
3. `make plugin-smoke` — verify plugin works
4. `make daily-report-plugin` — run daily report with plugin tools
5. MCP tools remain available if `OWL_HERMES_INTERFACE_MODE=mcp` or `both`

## Files Created/Modified

### Created
- `frontier_ai_risk_observer/hermes_plugin/` — 9 modules (init, manifest, schemas, facades, tools, hooks, cli_commands, skills, plugin, interface_mode)
- `.hermes/plugins/owlhermes/` — plugin.yaml, __init__.py
- `skills/ai-risk-signal-observer/references/` — 9 reference files
- `prompts/daily_report_plugin_prompt.md`
- `prompts/daily_report_plugin_finalize_prompt.md`
- `prompts/interactive_daily_report_plugin_prompt.md`
- `scripts/install_hermes_plugin.py`
- `scripts/plugin_smoke.py`
- `scripts/hermes_plugin_smoke.py`
- `scripts/skill_smoke.py`
- `tests/test_r15_plugin_migration.py` — 51 tests

### Modified
- `skills/ai-risk-signal-observer/SKILL.md` — rewritten plugin-first
- `scripts/daily_report.py` — added `--interface` argument
- `configs/hermes_config.example.yaml` — added plugin section
- `Makefile` — added 8 new targets
- `CLAUDE.md` — added plugin commands and status

## Test Results

- 703 tests pass (652 existing + 51 new R1-15 tests)
- `make plugin-smoke` — PASSED (10 checks)
- `make skill-smoke` — PASSED (22 checks)
- `make hermes-plugin-smoke` — WARNINGS (2: plugin not enabled in Hermes config yet)
- `make mcp-smoke` — PASSED
- `make source-health` — OK (0 invalid URLs)
