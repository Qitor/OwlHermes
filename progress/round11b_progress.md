# R1-11B Progress: Model-Tiered Daily Report Pipeline

**Date**: 2026-05-04
**Status**: COMPLETE

## Summary

Added model tiering to the daily report pipeline. A small/fast model (e.g., glm4.5-air) can now handle advisory pre-processing tasks (summarization, evidence extraction, lightweight classification) while Hermes retains all final risk judgment. The system is fully optional — when disabled, deterministic fallbacks handle everything.

## Files Created

| File | Purpose |
|------|---------|
| `frontier_ai_risk_observer/models/__init__.py` | Package init |
| `frontier_ai_risk_observer/models/config.py` | `SmallModelConfig` dataclass + `load_small_model_config()` |
| `frontier_ai_risk_observer/models/small_model.py` | `SmallModelClient` with summarize/excerpt/classify methods + deterministic fallbacks |
| `frontier_ai_risk_observer/services/candidate_preprocess.py` | `preprocess_candidate()` service + `CandidatePreprocessResult` |
| `frontier_ai_risk_observer/mcp/schemas.py` | `CandidatePreprocessInput` Pydantic model |
| `docs/22_model_tiered_daily_report_pipeline.md` | Full documentation |
| `tests/test_r111b_model_tiering.py` | 48 tests covering all components |

## Files Modified

| File | Change |
|------|--------|
| `frontier_ai_risk_observer/mcp/server.py` | Added `risk_candidate_preprocess` tool (16th MCP tool) |
| `configs/env.example` | Added 9 small-model env vars |
| `configs/hermes_config.example.yaml` | Added `risk_candidate_preprocess` to tool allowlist |
| `prompts/daily_report_prompt.md` | Added advisory preprocessing guidance + run bounds |
| `prompts/interactive_daily_report_prompt.md` | Added advisory status explanation |
| `skills/ai-risk-signal-observer/SKILL.md` | Added R1-11B section with may/must-NOT-do lists |
| `scripts/daily_report.py` | Added small model info to run summary |
| `quality/daily_report_checklist.yaml` | Added `avoids_advisory_as_final_evidence` check |
| `frontier_ai_risk_observer/quality/report_quality.py` | Added advisory-as-evidence anti-pattern check |
| `Makefile` | Added `model-tier-smoke` and `model-tier-smoke-live` targets |
| `README.md` | Added R1-11B section with three-tier table |
| `CLAUDE.md` | Updated architecture + commands |

## Three-Tier Architecture

| Tier | Responsible for |
|------|----------------|
| **Strong model (Hermes)** | Final risk signal judgment, report writing |
| **Small/fast model** | Candidate summaries, evidence excerpts, lightweight classification (advisory only) |
| **Deterministic Python** | Dedup, source health, quality checks, DB state |

## Key Safety Properties

- Small model output is ALWAYS marked `advisory_only: true`
- Small model must NOT make final risk signal decisions
- API keys read from named env vars, never logged
- Deterministic fallback when small model is disabled or unavailable
- Timeout and error handling returns graceful fallback, never raises to caller

## Validation Results

| Check | Result |
|-------|--------|
| `make test` | 312 passed |
| `make lint` | All checks passed |
| `make typecheck` | 12 pre-existing errors (1 R1-11B fixed) |
| `make validate-registries` | 23 sources, 6 podcasts, 6 events, 8 benchmarks |
| `make source-health` | OK (4 known issues, 2 need human review) |
| `make mcp-smoke` | OK |
| `make db-check` | OK |
| `make model-tier-smoke` | PASSED |
| `make report-quality-check` | OK (fixture passes; live run low-score expected) |
| `python -m compileall` | All files compile |

## Live Endpoint Test

Tested with user-provided endpoint (`glm4.5-air` at `https://pmqqqgec8pc9c8mbjm8bcac58epcdgbg.openapi-sj.sii.edu.cn/v1`). SSL connection failed (likely requires VPN/internal network). System correctly fell back to deterministic truncation with `advisory_only: True`.

## Test Coverage

48 R1-11B tests across 12 test classes:
- TestSmallModelConfig (7): disabled by default, env vars, secrets, API key, timeout, dry_run
- TestSmallModelClient (9): unavailable, fallback methods, available when configured, timeout, redaction, mocked endpoint
- TestCandidatePreprocess (6): deterministic fallback, advisory_only, domains, no storage, long text, mocked model
- TestMCPTool (5): imports, advisory output, disabled mode, no network, in MCP_TOOL_FUNCTIONS
- TestDailyPromptModelTiering (4): preprocessing, advisory, final judgment, run bounds
- TestInteractivePromptModelTiering (2): preprocess tool, advisory status
- TestSkillModelTiering (3): tiering, advisory-only, preprocess tool
- TestConfigFiles (2): env vars, hermes config
- TestDocs (5): exists, tiers, safety, configuration, disabling
- TestR111BMakefile (1): model-tier-smoke target
- TestQualityCheckerAdvisory (2): checklist, good report passes
- TestModelTierSmoke (1): smoke script runs
