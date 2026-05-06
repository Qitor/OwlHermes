# R1-13B Progress: Live Vault E2E Validation & Research UX Hardening

## Status: Complete

## Files Changed

1. `frontier_ai_risk_observer/obsidian/live_writer.py` — Added `_ensure_run_tracked()` for stateless MCP calls, added `failure` to `ALLOWED_NOTE_TYPES`, updated `append_event`/`record_failure`/`finalize_run` to use `_ensure_run_tracked()`
2. `frontier_ai_risk_observer/mcp/schemas.py` — Changed `note_type` to `Literal["source","candidate","evidence","signal","failure"]`, added `Field(description=...)` to `event_type`, `slug`, `body`
3. `frontier_ai_risk_observer/mcp/server.py` — Updated `risk_live_note_upsert` signature to `Literal` type, handle `failure` note_type separately, removed redundant `ALLOWED_NOTE_TYPES` check, added `from typing import Literal`
4. `frontier_ai_risk_observer/obsidian/exporter.py` — Added live run linking in `_export_daily()`, added `Live Run Index` to `_export_indexes()`
5. `frontier_ai_risk_observer/obsidian/markdown.py` — Changed `dict[str, object]` → `dict[str, Any]` for mypy compatibility
6. `scripts/inspect_live_vault.py` — Complete rewrite: COT violation detection, DB event checking, `--latest`, `--require-events`, `--require-finalized`, `--require-note-types`, `--db-check` flags, `_check_requirements()` exit code
7. `scripts/daily_report.py` — Fixed RunSummary dead code: `live_vault_enabled` and `live_run_dir` now assigned after run
8. `Makefile` — Added `daily-report-live-vault-e2e` target with requirements validation
9. `prompts/daily_report_prompt.md` — Added `run_id` passing guidance, listed event types and note types
10. `prompts/daily_report_finalize_prompt.md` — Added `run_id` guidance to finalize step
11. `prompts/interactive_daily_report_prompt.md` — Added `run_id` guidance
12. `tests/test_r113_live_vault.py` — Added 20 R1-13B tests across 6 new test classes
13. `tests/test_r12_obsidian_evidence.py` — Updated index count 7→8 for Live Run Index
14. `docs/24_live_obsidian_research_logging.md` — Added R1-13B section, failure note_type, E2E commands, inspect flags
15. `docs/23_obsidian_intelligence_vault.md` — Already had 08_Live_Runs (no changes needed)
16. `CLAUDE.md` — Added `daily-report-live-vault-e2e` command, updated R1-13B status
17. `README.md` — Added R1-13/R1-13B section with commands

## Validation Commands and Results

| Command | Result |
|---------|--------|
| `make validate-registries` | PASSED (23 sources, 6 podcasts, 6 events, 8 benchmarks) |
| `make db-check` | PASSED (SQLite connection ok) |
| `make lint` | PASSED (all checks passed) |
| `make test` | PASSED (538 tests, 0 failures) |
| `python -m compileall` | PASSED |
| R1-13B tests | PASSED (20 new tests, 6 test classes) |

## Test Results

- R1-13B tests: 20 passed, 0 failed
- R1-13 total tests: 72 passed
- Full suite: 538 passed, 0 failures

## GAPs Fixed

| GAP | Description | Fix |
|-----|-------------|-----|
| GAP 1 (Critical) | Stateless writer: `_active_runs` never shared between MCP calls | Added `_ensure_run_tracked()` auto-discovery from filesystem |
| GAP 2 | `note_type: str` not validated at schema level | Changed to `Literal["source","candidate","evidence","signal","failure"]` |
| GAP 3 | No `failure` note_type in upsert | Added `failure` to `ALLOWED_NOTE_TYPES`, handle separately in MCP tool |
| GAP 4 | No link between daily export and live runs | Added live run linking in `_export_daily()`, `live_run_id` in frontmatter |
| GAP 5 | No Live Run Index | Added to `_export_indexes()` with filesystem counting and recent runs list |
| GAP 6 | RunSummary dead code | Fixed: `live_vault_enabled` and `live_run_dir` now assigned after run |
| GAP 12 | Inspect script lacks validation | Added `--require-events`, `--require-finalized`, `--require-note-types`, `--db-check` |

## New Test Classes (R1-13B)

1. **TestR113BStatelessWriter** — 3 tests: auto-discover, append_event, finalize_run across stateless restarts
2. **TestR113BFailureNoteType** — 3 tests: in ALLOWED_NOTE_TYPES, schema accepts failure, schema rejects invalid
3. **TestR113BInspectEnhancements** — 4 tests: COT violation detection, inspect with COT, missing note types, requirements check
4. **TestR113BExportLiveRunLink** — 2 tests: Live Run Index created, daily note links to live runs
5. **TestR113BMakefileTargets** — 4 tests: E2E target, --require-events, --require-note-types, --db-check
6. **TestR113BPromptHardening** — 4 tests: daily/finalize/interactive prompts mention run_id, lists event types

## Report Items

1. **Files changed**: 17 modified files (see above)
2. **Commands passed**: All validation commands passed
3. **Stateless writer bug fixed**: Yes — `_ensure_run_tracked()` auto-discovers from filesystem
4. **COT violation detection**: Yes — inspect script checks 8 phrases (English + Chinese)
5. **Schema hardening**: Yes — Literal types, Field descriptions
6. **Export links to live runs**: Yes — daily note wikilinks to latest live run, frontmatter has `live_run_id`
7. **Live Run Index**: Yes — added to `99_Indexes/` with recent runs list
8. **E2E target**: Yes — `make daily-report-live-vault-e2e` with `--require-events`, `--require-note-types`, `--db-check`
9. **Prompt hardening**: Yes — run_id passing guidance, event_type and note_type lists
10. **RunSummary dead code fixed**: Yes — `live_vault_enabled` and `live_run_dir` assigned after run
11. **DB event checking in inspect**: Yes — `--db-check` queries `research_events` table
12. **Dependencies controlled**: Yes — no new dependencies
13. **Test count**: 538 total (518 original + 20 R1-13B)
14. **failure note_type**: Yes — added to ALLOWED_NOTE_TYPES, handled in MCP tool and writer
15. **Live run not executed**: Would require full Hermes run with OBSIDIAN_VAULT_PATH and OBSIDIAN_LIVE_LOGGING_ENABLED=true
16. **Private reasoning excluded**: Yes — prompts and schemas explicitly state no chain-of-thought; inspect script checks for violations
17. **Obsidian CLI remains optional**: Yes — all writes use direct Markdown
18. **SQLite retained**: Yes — ResearchEvent table unchanged; all existing tables intact
19. **Tool count**: 22 (unchanged from R1-13)
20. **Recommended next task**: R1-14 Obsidian Review Sync (bidirectional sync of human reviews back to DB)
