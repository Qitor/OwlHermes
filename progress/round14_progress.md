# R1-14: Source Reliability Patch & Registry Collection Policy

**Date**: 2026-05-07
**Status**: Done

## Problem

Hermes wastes time every daily run rediscovering known source failures. OpenAI is Cloudflare-blocked, Anthropic's scrapling helper gets SSL EOF, Apollo gets 403, AXRP helper returns nav links not episodes, arXiv API is rate-limited, SAIF/IDAIS timeout. These failures are documented in prose (`problematic_sources.md`) but **not encoded in the registry**.

## Solution

Embedded reliability metadata directly in YAML registries so the system can skip broken paths, apply fallbacks, and report access status without Hermes re-discovering failures.

## Changes

### Phase 1: Pydantic models (`registry/validators.py`)
- Added `AccessStatus`, `CollectionFrequency`, `CollectionMethod`, `FailureOnFailure` Literal types
- Added `FailurePolicy` model (max_attempts, timeout_seconds, on_failure, report_in_digest)
- Added `KnownFailure` model (type, message, observed_in_round, observed_at, recommended_action)
- Added 7 optional fields to `RegistryEntryModel`: access_status, collection_frequency, primary_collection_method, fallback_methods, failure_policy, known_failures, notes_for_hermes
- Added cross-field validator: primary_collection_method must not appear in fallback_methods

### Phase 2: YAML registry patches
- **sources.yaml**: 13 entries patched with reliability fields (openai_news=blocked, anthropic_news/apollo_blog/arxiv_ai_safety=degraded, safe_ai_forum_updates/idais_main=timeout_prone, techcrunch_ai/nist_caisi/uk_aisi_research/deepmind_blog=ok, metr_evaluations=ok/biweekly, eu_ai_office/govai_research=ok/weekly, uk_aisi_blog=ok)
- **podcasts.yaml**: axrp switched to podcast_rss with feed_url, dwarkesh/80k/latent_space got feed_urls, cognitive_revolution/security_cryptography marked degraded
- **events.yaml**: ai_safety_summit_series=manual_only/monthly, safe_ai_forum_events=timeout_prone

### Phase 3: Source health reporting (`services/source_health.py`)
- Added `_check_reliability()` function
- Extended `source_health_summary()` with: access_status_counts, degraded_or_blocked, timeout_prone, collection_method_counts, recent_known_failures_count, recent_known_failures

### Phase 4: Helper access gate (`mcp/server.py`)
- `_run_helper_for_entry` now returns `tuple[list, dict]` with metadata
- Blocked/disabled/manual_only sources return empty with skipped_reason
- Failure policy: max_attempts, timeout, on_failure (skip/fallback/manual_review)
- Fallback chain: search_fallback sets `search_fallback_recommended`, manual sets `manual_review_required`
- Extracted `_dispatch_helper()` for cleaner dispatch
- `risk_discovery_helper_preview` includes access_status and notes_for_hermes in all paths

### Phase 5: Access status filter (`mcp/server.py`)
- `risk_registry_list_due_sources` accepts optional `access_status` parameter
- Hermes can query `access_status=ok` sources first

### Phase 6: Prompts & SKILL.md
- SKILL.md: added Source Reliability section with access_status table, workflow, collection frequency guidance
- daily_report_prompt.md: added "来源可靠性" section
- daily_report_finalize_prompt.md: added reliability context for report writing
- interactive_daily_report_prompt.md: added reliability note for interactive mode
- Fixed pre-existing test failures by adding legacy MCP tool references to SKILL.md

### Phase 7: Tests (`tests/test_r114_source_reliability.py`)
- 44 tests across 7 classes: TestReliabilityModels, TestRegistryReliabilityFields, TestRegistryValidationWithReliability, TestSourceHealthReliability, TestHelperAccessStatus, TestFailurePolicy, TestDueSourceAccessStatusFilter

## Verification

- `make validate-registries` — passes
- `make test` — 703 passed, 0 failed
- `make lint` — all checks passed
- Helper preview for `openai_news` returns `access_status: blocked` with `notes_for_hermes`
- Health summary includes `access_status_counts: {ok: 10, degraded: 7, blocked: 1, timeout_prone: 3, manual_only: 1}`

## Key Metrics

- 22 entries with access_status set (10 ok, 7 degraded, 1 blocked, 3 timeout_prone, 1 manual_only)
- 9 known_failures registered
- 6 collection methods in use (browser_list_page: 11, podcast_rss: 4, search_fallback: 1, arxiv_api: 1, rss: 1, manual: 1)
- 3 podcasts now have RSS feed URLs configured (axrp, 80k, latent_space)
