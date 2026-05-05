# R1-09: Scrapling Source Reliability Helpers

## Overview

R1-09 adds deterministic discovery helpers that fetch candidate items from configured sources. Helpers are **collectors only** — they do not judge risk, call LLMs, store raw items, or triage. Hermes remains the judgment layer.

## Architecture

```
Registry YAML → validators (helper metadata) → helpers/ modules → CandidateItem → MCP preview tool → Hermes triage
```

### Key constraint

Scrapling is used via `Adaptor` (HTML parser only, no Playwright). Network fetching uses `httpx` (already a dependency). The `Fetcher` class is NOT used because it requires Playwright and `curl_cffi`.

## Helper Types

| Type | Module | Input | Output |
|------|--------|-------|--------|
| `scrapling_official_page` | `helpers/scrapling_official_page.py` | URL, include/exclude patterns | Candidate links from page |
| `rss` | `helpers/rss.py` | RSS/Atom feed URL | Feed entries |
| `podcast_rss` | `helpers/podcast.py` | Podcast RSS URL | Episodes with enclosures |
| `arxiv_query` | `helpers/arxiv.py` | arXiv query string | arXiv papers |

Each helper has two functions:
- An **offline-testable parser** (e.g. `extract_candidates_from_html()`, `parse_rss_feed()`)
- A **network-fetching wrapper** (e.g. `fetch_and_extract()`, `fetch_and_parse()`)

## CandidateItem Model

```python
class CandidateItem(BaseModel):
    source_id: str
    kind: str           # "article", "podcast_episode", "paper", "event", "benchmark_update"
    title: str
    url: str
    published_at: datetime | None
    summary: str | None
    content_text: str | None
    source_url: str
    discovery_method: str  # "scrapling_official_page", "rss", "podcast_rss", "arxiv_query"
    metadata: dict[str, Any]
```

## Registry Extension

Each registry entry now supports helper metadata fields:

- `helper_type` — which helper to use (Literal enum)
- `scrapling_url`, `feed_url`, `query` — helper-specific URL/query
- `link_include_patterns`, `link_exclude_patterns` — URL filtering for scrapling
- `max_items`, `lookback_days` — fetch limits
- `known_issues`, `requires_human_review` — operational metadata

Validators check that helper URLs are present when `helper_type` requires them, and that pattern lists contain valid regex.

## MCP Tools

Two new tools added to the MCP server:

1. **`risk_source_health_summary()`** — returns helper coverage counts, entries needing human review, invalid URLs, known issues. No database or network access required.

2. **`risk_discovery_helper_preview(source_id, fetch=False, limit=10)`** — preview candidates for a source. With `fetch=False` reports what would happen. With `fetch=True` actually runs the helper and returns candidates. Does NOT store raw items.

## CLI Scripts

- `scripts/check_source_health.py` — prints source health summary as JSON
- `scripts/preview_discovery_helpers.py` — preview helpers with `--source-id`, `--kind`, `--fetch`, `--limit` flags

## Makefile Targets

- `make source-health` — run source health check
- `make preview-helpers` — list all sources with helpers
- `make r109-helper-preflight` — validate registries + source health + MCP smoke + helper preview

## Testing

- `tests/fixtures/` — HTML, RSS, and arXiv XML fixtures for offline parser testing
- `tests/test_r109_helpers.py` — comprehensive tests for all helpers, registry validation, source health, MCP tools

## Key Design Decisions

1. **Scrapling Adaptor only** — Fetcher requires Playwright; Adaptor is pure Python HTML parsing.
2. **No recursive crawling** — scrapling_official_page extracts links from a single page only.
3. **No auto-storage** — helpers return candidates; Hermes decides what to store.
4. **No LLM calls** — helpers are deterministic.
5. **fetch=False by default** — `risk_discovery_helper_preview` requires explicit opt-in for network access.
