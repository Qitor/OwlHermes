# Source Reliability Policy

## Principles

1. **No Cloudflare/CAPTCHA bypass** — If a source is behind Cloudflare or CAPTCHA, do not attempt to bypass it. Use search engine fallback instead.
2. **Feed/sitemap/list page first** — Always check RSS feeds, sitemaps, or list pages before browsing individual articles. Helpers do this automatically.
3. **Known broken sources** — See "Frequently failing" section below.
4. **Search fallback only when allowed** — Use web search as a fallback, not primary discovery method. Direct source access is preferred.

## Source Reliability Tiers

### Most reliable / high-value

- TechCrunch RSS — consistent feed, broad AI coverage
- AISI blog — UK AI Safety Institute, government eval reports (2/4 signals in R1-13 run)
- Anthropic news — official announcements, RSP updates
- NIST CAISI — US government eval reports, high signal

### Moderate reliability

- DeepMind blog — occasional safety/alignment posts
- GovAI — JS-heavy pages, may timeout on browser
- EU AI Office — policy documents, slow updates
- arXiv API — rate-limit/policy, use `limit=5-10` for high-volume sources

### Frequently failing

- OpenAI — Cloudflare blocks direct browser access; use Yahoo Search fallback
- Apollo Blog — 403 Forbidden on scrapling helper and direct browse
- SAIF/IDAIS — timeout on long pages
- AXRP — no useful RSS episodes; check weekly, not daily

## Helper Types

| Type | What it does |
|------|-------------|
| `scrapling_official_page` | Scrapes an official page, extracts links matching include/exclude patterns |
| `rss` | Parses an RSS/Atom feed |
| `podcast_rss` | Parses a podcast RSS feed (episodes with enclosures) |
| `arxiv_query` | Queries the arXiv API with a configured search query |
| `manual` | No automated helper; Hermes must browse manually |
| `none` | No helper configured; Hermes must browse manually |

## Helper Workflow

1. Call `owl_risk_discovery(action="source_health")` to see helper coverage and known issues.
2. For each due source with a helper, call `owl_risk_discovery(action="helper_preview", payload={"source_id": "...", "fetch": true})` to get candidate items.
3. Review candidates: these are raw links/titles, not triaged signals.
4. For interesting candidates, use Hermes built-in web/search/browser tools to read the full content.
5. Then follow the normal Daily Workflow (seen-check → raw_item_store → signal → digest).

**Important:**
- Helpers fetch structured data deterministically — they do not replace Hermes judgment.
- Always call `owl_risk_state(action="seen_check")` before storing items found by helpers.
- Entries with `requires_human_review: true` may have stale URLs or other known issues.
- If a helper returns no candidates, the source may need manual browsing.
