# R1-09 Progress Report: Scrapling Source Reliability Helpers

**Date:** 2026-05-04
**Status:** Complete
**Previous round:** R1-08 (Automated Hermes Daily Dry Run)

---

## R1-09 Objective

Add Scrapling-powered source reliability helpers as mandatory deterministic collectors. Helpers fetch candidate items from configured sources but do NOT judge risk, call LLMs, store raw items, or triage. Hermes remains the judgment layer.

---

## Delivered Items

### 1. Dependency

- `scrapling>=0.4` added to `pyproject.toml`
- Uses `scrapling.parser.Adaptor` only (HTML parser, no Playwright needed)
- Network fetching uses `httpx` (already a dependency)

### 2. Registry Validation Extension

All 4 entry models in `registry/validators.py` extended with helper metadata fields:

| Entry type | New fields |
|-----------|-----------|
| `SourceEntry` | `helper_type` (7 values), `feed_url`, `sitemap_url`, `query`, `list_url`, `scrapling_url`, `link_include_patterns`, `link_exclude_patterns`, `max_items`, `lookback_days`, `requires_human_review`, `known_issues` |
| `PodcastEntry` | `helper_type` (4 values), `transcript_index_url`, `scrapling_url`, `max_items`, `lookback_days`, `known_issues`, `requires_human_review` |
| `EventEntry` | `helper_type` (4 values), `current_url`, `archive_urls`, `scrapling_url`, `known_issues`, `requires_human_review` |
| `BenchmarkEntry` | `helper_type` (3 values), `watch_url`, `scrapling_url`, `known_issues`, `requires_human_review` |

Validators enforce: HTTP/HTTPS URLs for helper URLs, non-empty strings for pattern lists, Literal enums for `helper_type`.

### 3. Registry Entries Updated

| Source ID | helper_type | Notes |
|-----------|-------------|-------|
| `anthropic_news` | `scrapling_official_page` | `scrapling_url`, `link_include_patterns: ["/news/", "/research/", "/policy/"]`, `max_items: 10` |
| `apollo_blog` | `scrapling_official_page` | `scrapling_url`, `max_items: 10`, `known_issues` |
| `arxiv_ai_safety` | `arxiv_query` | `max_items: 20`, `lookback_days: 7` |
| `techcrunch_ai` | `rss` | `feed_url`, `max_items: 15`, `lookback_days: 7` |
| `axrp` (podcast) | `scrapling_official_page` | `scrapling_url`, `requires_human_review: true`, `known_issues` |
| `ai_safety_summit_series` (event) | `manual` | `known_issues` about stale 2023 URL, `requires_human_review: true` |

### 4. CandidateItem Model

`helpers/models.py` — shared Pydantic model for helper output:

```python
class CandidateItem(BaseModel):
    source_id: str
    kind: str           # "web_article", "podcast_episode", "arxiv_paper", etc.
    title: str
    url: str
    published_at: datetime | None
    summary: str | None
    content_text: str | None
    source_url: str
    discovery_method: str
    metadata: dict[str, Any] = {}
```

### 5. Helper Modules

Each helper has an **offline-testable parser** and a **network-fetching wrapper**:

| Module | Parser function | Network function |
|--------|----------------|-----------------|
| `helpers/scrapling_official_page.py` | `extract_candidates_from_html()` | `fetch_and_extract()` |
| `helpers/rss.py` | `parse_rss_feed()` | `fetch_and_parse()` |
| `helpers/podcast.py` | `parse_podcast_feed()` | `fetch_and_parse()` |
| `helpers/arxiv.py` | `parse_arxiv_atom()` | `fetch_and_parse()` |

Design constraints:
- No recursive crawling
- No LLM calls
- No auto-storage of raw items
- Scrapling helper filters navigation URLs (`/about`, `/careers`, `/privacy`, etc.)
- Include/exclude patterns use regex
- RSS/podcast respect `lookback_days` cutoff
- arXiv builds deterministic query URLs with `sortBy=submittedDate`

### 6. Source Health Service

`services/source_health.py` — reports:
- Helper coverage counts per registry group
- Scrapling entries and missing scrapling/feed URLs
- Known issues and entries requiring human review
- Invalid URLs

CLI: `scripts/check_source_health.py`

### 7. Preview Discovery Helpers Script

`scripts/preview_discovery_helpers.py` — flags:
- `--source-id` — preview a specific source
- `--kind` — filter by registry kind
- `--limit` — max candidates
- `--fetch` — actually fetch from network (off by default)

### 8. MCP Tools (2 new, 15 total)

| Tool | Purpose |
|------|---------|
| `risk_source_health_summary()` | Returns helper coverage, known issues, human review entries, invalid URLs |
| `risk_discovery_helper_preview(source_id, fetch=False, limit=10)` | Preview candidates for a source; `fetch=False` by default |

### 9. Makefile Targets

| Target | Purpose |
|--------|---------|
| `make source-health` | Run source health check |
| `make preview-helpers` | List all sources with helpers |
| `make r109-helper-preflight` | Validate registries + health + MCP + helpers |

### 10. Skill Update

`skills/ai-risk-signal-observer/SKILL.md` — added "Helper-Assisted Discovery (R1-09)" section with:
- Available MCP tools for helpers
- Helper type descriptions
- Workflow: health check → preview → triage → manual fallback
- Important notes about `requires_human_review` and `fetch=False` default

### 11. R1-09 Prompt

`prompts/r109_hermes_helper_assisted_dry_run_prompt.md` — self-contained prompt for helper-assisted dry run with 6-step workflow.

### 12. Documentation

`docs/18_r109_scrapling_source_reliability_helpers.md` — architecture, helper types, CandidateItem model, registry extension, MCP tools, CLI scripts, Makefile targets, testing, design decisions.

### 13. README Update

`README.md` — added R1-09 section with helper types table, new MCP tools, and Makefile commands.

### 14. Tests

`tests/test_r109_helpers.py` — 46 tests in 9 test classes:

| Class | Tests | Coverage |
|-------|-------|----------|
| `TestScraplingOfficialPage` | 9 | Basic extraction, nav filtering, JS/anchor skip, include/exclude patterns, limit, dedup, empty HTML, field validation |
| `TestRSSHelper` | 6 | Basic parsing, tracking param strip, limit, published_at, summary, empty feed |
| `TestPodcastHelper` | 2 | Basic parsing, episode titles |
| `TestArxivHelper` | 7 | Query URL, Atom parsing, titles, URLs, published_at, limit, empty feed, summary |
| `TestCandidateItemModel` | 3 | Minimal create, full create, model_dump JSON |
| `TestRegistryHelperMetadata` | 9 | Valid/invalid helper_type, URL validation, patterns, all 4 entry types |
| `TestSourceHealth` | 3 | Structure, helper coverage, known issues |
| `TestMCPSourceHealth` | 1 | Returns ok |
| `TestMCPDiscoveryHelperPreview` | 3 | Not found, no-fetch preview, manual source |
| `TestPreviewScript` | 2 | Not found, no-fetch |

Test fixtures in `tests/fixtures/`:
- `anthropic_news.html` — 4 article links + navigation links
- `techcrunch_ai_rss.xml` — 3-item RSS feed
- `axrp_podcast_rss.xml` — 2-episode podcast RSS
- `arxiv_response.xml` — 2-entry arXiv Atom feed

---

## Validation Results

| Check | Result |
|-------|--------|
| Registry validation | 23 sources (21 enabled), 6 podcasts, 6 events, 8 benchmarks |
| Source health | 4 sources with helpers, 2 require human review, 0 invalid URLs, 4 known issues |
| Preview helpers | 6 helpers configured |
| MCP smoke | PASS (3 due sources, registry ok, seen-check controlled) |
| Test suite | **116/116 passed** (46 new R1-09 tests + 70 existing) |
| Lint (ruff) | All checks passed |
| Compile check | All modules OK |
| DB check | Connection ok |

---

## Current Helper Coverage Summary

| Group | With helper | Without helper | Manual |
|-------|------------|----------------|--------|
| Sources (23) | 4 (2 scrapling, 1 rss, 1 arxiv) | 19 | 0 |
| Podcasts (6) | 1 (1 scrapling) | 5 | 0 |
| Events (6) | 0 | 5 | 1 |
| Benchmarks (8) | 0 | 8 | 0 |

**Most sources still rely on Hermes manual browsing.** Expanding helper coverage is a natural next step.

---

## Known Issues Carried Forward

| ID | Issue |
|----|-------|
| `apollo_blog` | R1-08 found no recent items; blog may update infrequently |
| `anthropic_news` | Direct article URL construction may return 404; prefer link extraction from listing page |
| `axrp` | No RSS feed URL found; R1-08 found no recent episodes |
| `ai_safety_summit_series` | URL points to 2023 Bletchley Park summit; no single page tracks full summit chain |

---

## Implementation Rounds Summary

| Round | Status | Summary |
|-------|--------|---------|
| R1-01 | Done | Backend skeleton, API, registry loader |
| R1-02 | Done | PostgreSQL database, schema, session |
| R1-03 | Done | Registry validation |
| R1-04 | Done | Ingestion and registry API |
| R1-05 | Done | Raw item memory, deterministic dedup |
| R1-06 | Done | Minimal MCP state tools (13 tools) |
| R1-07 | Done | Real Hermes-Agent integration smoke test |
| R1-08 | Done | Automated Hermes daily dry run (5 raw items, 1 signal, 1 digest) |
| R1-09 | Done | Scrapling source reliability helpers (15 MCP tools, 4 helper types) |
| R1-10+ | TODO | Awaiting product manager direction |

---

## MCP Tools Inventory (15 total)

1. `risk_registry_summary`
2. `risk_registry_list_due_sources`
3. `risk_registry_get_source`
4. `risk_raw_item_seen_check`
5. `risk_raw_item_store`
6. `risk_raw_item_search`
7. `risk_raw_item_duplicate_candidates`
8. `risk_source_run_record`
9. `risk_signal_store`
10. `risk_signal_search`
11. `risk_digest_store`
12. `risk_digest_search`
13. `risk_benchmark_observation_store`
14. `risk_source_health_summary`
15. `risk_discovery_helper_preview`

---

## Potential R1-10 Directions

These are observations, not decisions — awaiting product manager input:

1. **Expand helper coverage** — only 5/43 entries have automated helpers; add RSS feeds for podcasts, sitemap helpers for benchmarks
2. **Production delivery** — Feishu/WeCom/WeChat gateway integration for Chinese risk digests
3. **Website/API** — public-facing dashboard for signals, digests, source health
4. **Benchmark observation persistence** — currently a validated placeholder; add real storage service
5. **Signal scoring/taxonomy** — structured signal classification beyond raw storage
6. **Hermes cron scheduling** — automated daily runs via Hermes cron instead of manual `make r108-run-hermes`
7. **PostgreSQL migration** — move from SQLite dry-run to real PostgreSQL for production
