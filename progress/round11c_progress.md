# R1-11C Progress: Two-Phase Daily Report Finalization

**Date**: 2026-05-05
**Status**: COMPLETE

## Summary

Added two-phase daily report finalization so `make daily-report` always produces a readable Chinese daily report, even if Hermes times out during collection.

## Files Created

| File | Purpose |
|------|---------|
| `prompts/daily_report_finalize_prompt.md` | Phase B finalize prompt (DB-only, no browsing) |
| `docs/22_two_phase_daily_report_finalization.md` | Full documentation |
| `tests/test_r111c_two_phase.py` | 45 tests |

## Files Modified

| File | Change |
|------|--------|
| `scripts/daily_report.py` | Complete rewrite: two-phase workflow, state snapshots, completion detection, CLI args |
| `frontier_ai_risk_observer/mcp/schemas.py` | Added what_changed, why_it_matters, what_to_watch_next, needs_review_reason to SignalStoreInput |
| `frontier_ai_risk_observer/services/signals.py` | Use explicit three-question fields; auto-mark review when missing |
| `prompts/daily_report_prompt.md` | Added "store digest before ending" and "skip slow sources" guidance |
| `Makefile` | Added daily-report-finalize, daily-report-debug targets |
| `README.md` | Added R1-11C section |
| `CLAUDE.md` | Updated commands, architecture, status |

## Two-Phase Architecture

| Phase | Purpose | Timeout | Browses? |
|-------|---------|---------|----------|
| **Phase A** (collection) | Hermes researches, collects evidence, stores items | 30 min | Yes |
| **Phase B** (finalize) | Hermes writes report from DB state only | 10 min | No |

Phase B runs automatically when Phase A times out, exits non-zero, or doesn't produce a complete Chinese report.

## Completion Detection

Deterministic detection (no LLM):
- Requires Chinese content (>20 CJK chars)
- Requires at least one report section pattern
- Rejects tool logs, tracebacks, timeout notes

## Signal Three-Question Fields

`risk_signal_store` now accepts:
- `what_changed` — what changed
- `why_it_matters` — why it affects risk judgment
- `what_to_watch_next` — what to watch next
- `needs_review_reason` — why human review is needed

Missing `what_changed` + `why_it_matters` auto-marks `needs_human_review=True`.

## State Snapshots

Before/after JSON snapshots capture:
- Raw item, source run, signal, digest counts
- Latest digest details
- Recent items (last 20 each)

## Validation Results

| Check | Result |
|-------|--------|
| `make test` | 357 passed |
| `make lint` | All checks passed |
| `make validate-registries` | PASS |
| `make mcp-smoke` | PASS |
| `make db-check` | OK |
| `make daily-report-preflight` | ALL PASSED (incl. finalize prompt) |
| `make hermes-smoke` | PASS (16 tools) |
| `make model-tier-smoke` | PASSED |
| `python -m compileall` | 0 errors |

## Test Coverage

45 R1-11C tests:
- TestFinalizePrompt (6): exists, no browsing, no fetching, digest_store, search tools, editorial
- TestDailyPromptBounded (3): 3-5 sources, prioritize completion, store digest
- TestCompletionDetection (6): complete, empty, English-only, timeout log, tool logs, traceback
- TestStateSnapshots (3): empty DB, save/load, compute delta
- TestRunnerCLIArgs (2): script imports, timeout defaults
- TestPhaseResult (2): defaults, timeout
- TestRunSummary (1): defaults
- TestShouldFinalize (3): timed out, no digest, complete
- TestSignalThreeQuestions (7): what_changed, why_it_matters, what_to_watch_next, needs_review_reason, missing marks review, explicit preferred, metadata fallback
- TestR111CMakefile (4): daily-report, with-quality, finalize, debug
- TestR111CDocs (7): exists, two phases, no browsing, SQLite, no Docker, timeout, Hermes-led
- TestR111CSmoke (1): smoke script
