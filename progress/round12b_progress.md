# R1-12B Progress: Real E2E Vault Population Validation

## Goal

Ensure `make daily-report-and-obsidian-e2e` produces a populated AI Risk Intelligence Vault with signal/candidate/evidence/run notes — not just source/domain indexes.

## Files Created

1. `scripts/inspect_obsidian_export.py` — Vault inspection script with `VaultInspection` dataclass, `inspect_vault()` function, and CLI (--vault, --json, --date, --latest)

## Files Changed

2. `frontier_ai_risk_observer/obsidian/exporter.py` — Added `_export_evidence_placeholders()` for signals with URL but no SourceClaim; enhanced `_export_daily()` with "Linked Intelligence Objects" section (wikilinks + frontmatter counts); enhanced `_export_review_queue()` with "Signals Without Evidence" section; type annotations fixed for mypy
3. `frontier_ai_risk_observer/obsidian/markdown.py` — Type annotations: `dict[str, object]` for frontmatter params
4. `tests/test_r12b_e2e_validation.py` — 35 tests across 9 test classes: TestEvidencePlaceholders, TestReviewQueue, TestCandidateNotes, TestRunNotes, TestDailyNoteLinking, TestGeneratedBlockMarkers, TestInspectScript, TestMakefileTargets, TestDocsR12B
5. `Makefile` — Added `obsidian-inspect` and `daily-report-and-obsidian-e2e` targets
6. `CLAUDE.md` — Added `obsidian-inspect` and `daily-report-and-obsidian-e2e` commands; updated implementation status for R1-12B
7. `docs/23_obsidian_intelligence_vault.md` — Added R1-12B section: evidence placeholders, daily note linking, review queue enhancement, vault inspection, E2E target
8. `prompts/daily_report_prompt.md` — Strengthened evidence storage: "必须用 risk_evidence_store 存储至少一条支撑证据"; added what_changed/why_it_matters/what_to_watch_next requirement for signal_store
9. `prompts/daily_report_finalize_prompt.md` — Added step 4 (risk_evidence_search), step 6 (MUST store evidence for each Top Signal), needs_human_review guidance
10. `skills/ai-risk-signal-observer/SKILL.md` — Added bold rule: "For each Top Signal, you MUST store at least one evidence item via risk_evidence_store"; added intermediate evidence guidance, needs_review_reason, three-question fields reminder

## Commands Run

11. Validation commands and results:
    - `make validate-registries` — PASSED (23 sources, 6 podcasts, 6 events, 8 benchmarks)
    - `make db-check` — PASSED (SQLite connection ok)
    - `make lint` — PASSED (all checks passed)
    - `make test` — PASSED (466 tests, 0 failures)
    - `make typecheck` — obsidian/ module clean; 12 pre-existing errors in other modules
    - `make source-health` — OK (4 known issues, 2 need human review)
    - `make obsidian-export-dry-run` — PASSED
    - `make obsidian-export` — PASSED
    - `make obsidian-inspect` — PASSED

## Test Results

12. `tests/test_r12b_e2e_validation.py`: 35 tests, 35 passed, 0 failed
13. Full suite: 466 tests passed, 0 failures

## Vault Counts (empty DB, no daily report run yet)

14. Daily notes: 1, Signal notes: 0, Candidate notes: 0, Evidence notes: 0, Source notes: 43, Risk domain notes: 77, Entity notes: 0, Run notes: 0, Review notes: 2, Index notes: 7

## Key Features Implemented

15. Evidence placeholders: Signals with `primary_source_url` but no linked SourceClaim items get placeholder evidence notes with `needs_review: true` and `placeholder: true`
16. Daily note linking: "Linked Intelligence Objects" section with wikilinks to all note types; frontmatter includes signal/candidate/evidence/run/failed-source counts
17. Review queue enhancement: "Signals Without Evidence" section in needs-review.md
18. Vault inspection: `inspect_vault()` checks note counts, daily-signal links, signal three-question fields, generated block markers, signals without evidence, failed sources content

## Pre-existing Type Errors (Not R1-12B)

12 errors in: `services/source_health.py` (3), `helpers/rss.py` (2), `helpers/arxiv.py` (1), `db/dryrun.py` (2), `mcp/server.py` (4). None introduced by R1-12B.
