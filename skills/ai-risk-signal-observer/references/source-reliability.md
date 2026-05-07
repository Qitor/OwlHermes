# Source Reliability Notes

Consolidated from R1-08, R1-09B, R1-05, and R1-13 (2026-05-06) runs.

## Reliable sources (work consistently)

| Source | Method | Notes |
|--------|--------|-------|
| techcrunch_ai | RSS (`curl` feed) | Most reliable source. One fetch gets all candidates. Web scrape times out; always use RSS. |
| uk_aisi_research | Browser navigate | Research listing page loads well. Individual research pages accessible. Active publication frequency (3 papers in late Apr 2026). |
| uk_aisi_blog | Browser navigate | Blog listing page loads well. Individual article URLs may 404 — always extract links from listing page first. |
| nist_caisi | Browser navigate | Active publication (2 posts in first week of May 2026). Pages load reliably. High-value source for US government evaluation findings. |
| eu_ai_office | Browser navigate | News page accessible. Topic filter (topics=1666) may not work; use curated "Latest News" section on the AI policy landing page instead. |
| deepmind_blog | Browser + subagent | Main blog page loads reliably. No May 2026 content at time of scan. Individual article pages sometimes need console extraction. |
| govai_research | Browser navigate | Research page accessible. Year filter requires JavaScript interaction (use browser_console to set value). Low update frequency (last post Apr 2026). |

## Unreliable sources (frequent failures)

| Source | Issue | Workaround |
|--------|-------|------------|
| openai_news | Cloudflare browser challenge blocks ALL automated access (direct navigate, helper, even checkbox verification) | Use Yahoo Search to find OpenAI-related coverage from third-party sources. Google and DuckDuckGo may trigger CAPTCHAs. Store raw items with `discovery_method: search_engine_third_party` and flag for one-source verification. |
| arxiv_ai_safety | API rate-limited (R1-09B) or user-policy-blocked (R1-05) | No reliable workaround yet. Consider OAI-PMH endpoint or web search as fallback. |
| safe_ai_forum_updates | Page timeout | Retry once; if still fails, skip and note in digest |
| idais_main | Page timeout | Retry once; if still fails, skip and note in digest |
| anthropic_news (helper) | scrapling_official_page helper fails with SSL: UNEXPECTED_EOF_WHILE_READING | Use browser_navigate manually instead of helper. Direct article URLs may 404. |
| apollo_blog (helper) | scrapling_official_page helper fails with 403 Forbidden | Use browser_navigate manually. Very low update frequency (last post Jan 20, 2026). Check weekly only. |

## Conditionally reliable

| Source | Method | Notes |
|--------|--------|-------|
| axrp | Browser or RSS feed | Helper (scrapling_official_page) returns navigation links not episode listings — do NOT use helper for episode discovery. Use RSS feed at `https://axrp.net/feed.xml` or browse manually. Very low episode frequency. requires_human_review=true. |
| metr_evaluations | Browser navigate | Page loads. Very low update frequency (last evaluation Nov 19, 2025). Check weekly or biweekly. |
| safe_ai_forum | Browser navigate | Updates page accessible but stale (last update May 2025). Research page last update Feb 2026. Low frequency. |
| anthropic_news (manual) | Browser navigate | News listing page loads manually. Helper broken (SSL). Direct article URL construction may 404. |

## Helper coverage (current status as of 2026-05-06)

| Source | Helper type | Status |
|--------|------------|--------|
| anthropic_news | scrapling_official_page | BROKEN: SSL EOF error. Use browser manually. |
| apollo_blog | scrapling_official_page | BROKEN: 403 Forbidden. Use browser manually. |
| arxiv_ai_safety | arxiv_query | API unstable; degraded to browser search in R1-09B |
| techcrunch_ai | rss | Working reliably |
| axrp | scrapling_official_page | Returns navigation links, not episodes. Use RSS feed or manual browse instead. |

## Source frequency notes (as of 2026-05-06)

| Source | Last new content | Check frequency |
|--------|-----------------|-----------------|
| nist_caisi | May 5, 2026 | Daily |
| uk_aisi_research | Apr 28, 2026 | Daily |
| openai_news | May 5, 2026 (GPT-5.5 Instant) | Daily (via search engine) |
| deepmind_blog | Apr 30, 2026 | Daily |
| eu_ai_office | May 5, 2026 | Weekly |
| govai_research | Apr 20, 2026 | Weekly |
| safe_ai_forum | Feb 25, 2026 (research) | Weekly |
| apollo_blog | Jan 20, 2026 | Weekly/biweekly |
| metr_evaluations | Nov 19, 2025 | Biweekly |
| axrp | Feb 18, 2026 (ep 49) | Weekly |
| anthropic_news | May 5, 2026 | Daily (manual browse) |
