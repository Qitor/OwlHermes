# R1-11 Progress Report: Daily Report Quality Loop

## Summary

R1-11 defines, tests, and enforces what a high-quality AI risk intelligence daily report means. The daily report must be a concise intelligence product — not a news digest, not a tool-call log, not a raw source summary.

## Files Created

### Quality Rubric
- `docs/21_daily_report_quality_rubric.md` — defines product mission, what counts as a signal, what to filter out, evaluation dimensions, required sections, style guide

### Quality Checklist
- `quality/daily_report_checklist.yaml` — 18 structured checks with IDs, descriptions, weights (total 111 points)

### Quality Checker Module
- `frontier_ai_risk_observer/quality/__init__.py`
- `frontier_ai_risk_observer/quality/report_quality.py` — deterministic quality checker (no LLMs, no network)

### Quality Checker Script
- `scripts/check_daily_report_quality.py` — CLI with `--report`, `--latest`, `--json`, `--fail-under SCORE`, `--write-review PATH`

### Test Fixtures
- `tests/fixtures/reports/good_daily_report.md` — passes most checks (81%)
- `tests/fixtures/reports/bad_tool_log_report.md` — fails (9%)
- `tests/fixtures/reports/bad_news_dump_report.md` — fails (23%)
- `tests/fixtures/reports/no_signal_report.md` — passes (89%)

### Tests
- `tests/test_r111_quality.py` — 58 tests covering rubric, checklist, quality module, script, prompts, Makefile, fixtures

## Files Modified

### Prompts
- `prompts/daily_report_prompt.md` — strengthened with: explicit signal definition, filter rules, candidate items section, uncertainty section, "not news" instruction, "every signal must answer 3 questions", "0 signals is ok", "avoid tool logs", "quality over quantity"
- `prompts/interactive_daily_report.md` — updated to expose editorial judgment (why a source was selected, why a candidate is/isn't a signal, where evidence is weak), not just tool calls

### Config
- `Makefile` — added `report-quality-check`, `report-quality-review`, `daily-report-with-quality` targets
- `README.md` — added R1-11 section
- `CLAUDE.md` — added quality commands, quality/ module in architecture, updated status
- `docs/20_stable_daily_report_modes.md` — added Quality Checking section

## Validation Results

| Check | Result |
|-------|--------|
| `make test` | 264 passed |
| `make lint` | All checks passed |
| `make typecheck` (quality module) | Success |
| `python -m compileall` | No errors |
| `make validate-registries` | PASS |
| `make source-health` | PASS (4 known issues) |
| `make mcp-smoke` | PASS |
| `make hermes-smoke` | PASS |
| `make db-check` | PASS |
| `make report-quality-check` | Works (scores latest report) |
| `make report-quality-review` | Works (writes Markdown review) |

## Quality Scores

### Fixture Scores
| Fixture | Score | Classification |
|---------|-------|---------------|
| good_daily_report.md | 81% | Intelligence briefing quality |
| no_signal_report.md | 89% | Intelligence briefing quality |
| bad_news_dump_report.md | 23% | News dump |
| bad_tool_log_report.md | 9% | Tool log |

### Latest Real Daily Report
The latest `runs/daily/20260504_223632/daily_report.md` scored **11%** — it is a timeout artifact ("Hermes timed out after 1800s"), not a real report. This confirms the quality checker correctly identifies failed/incomplete run artifacts.

## Quality Checker Design

The checker is fully deterministic:
- No LLMs
- No network calls
- No Postgres/Hermes dependencies
- Uses regex-based section detection and anti-pattern matching
- 18 checks, each with a weight (total 111 points)
- Score ranges 0-100%
- Anti-pattern detection: tool_log, raw_item_dump, no_evidence_links, hype_language, agi_sensationalism, news_headline_only

## R1-11 Spec Compliance

| Spec Item | Status |
|-----------|--------|
| 1. Quality rubric doc | Done |
| 2. Quality checklist YAML | Done (18 checks) |
| 3. Report quality checker script | Done |
| 4. Makefile targets (3) | Done |
| 5. Updated daily report prompt | Done |
| 6. Finalize prompt | N/A (doesn't exist yet) |
| 7. Updated interactive prompt | Done |
| 8. Quality module | Done |
| 9. Sample report fixtures (4) | Done |
| 10. Tests (58) | Done |
| 11. Updated docs/README/CLAUDE.md | Done |
| 12. Optional quality gate target | Done (`daily-report-with-quality`) |
| 13. Validation commands | All pass |
| 14. Quality check on latest report | Done (11% — timeout artifact) |
| 15. Dependencies controlled | No new heavy deps |
| 16. Results report | This document |

## Recommended Next Task

**R1-12 Obsidian Vault Export** — quality infrastructure is ready. The quality checker can score real reports once Hermes produces them. The next logical step is making reports accessible to researchers (Obsidian vault export) before iterating further on report quality.

Alternatively, **R1-11B** if a real Hermes daily report run is available and shows quality issues that need prompt/report iteration.
