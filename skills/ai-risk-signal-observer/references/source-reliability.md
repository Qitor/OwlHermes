# Source Reliability Notes

Consolidated from R1-08, R1-09B, and R1-05 (2026-05-05) runs.

## Reliable sources (work consistently)

| Source | Method | Notes |
|--------|--------|-------|
| techcrunch_ai | RSS (`curl` feed) | Most reliable source. One fetch gets all candidates. Web scrape times out; always use RSS. |
| uk_aisi_blog | Browser navigate | Blog listing page loads well. Individual article URLs may 404 — always extract links from listing page first. |
| anthropic_news | Browser navigate | News listing page loads well. Direct article URL construction may 404 — extract links from listing page. Low update frequency (days between posts). |

## Unreliable sources (frequent failures)

| Source | Issue | Workaround |
|--------|-------|------------|
| openai_news | Cloudflare browser challenge blocks automated access | Use TechCrunch RSS or web search to find OpenAI-related news instead |
| arxiv_ai_safety | API rate-limited (R1-09B) or user-policy-blocked (R1-05) | No reliable workaround yet. Consider OAI-PMH endpoint or web search as fallback. |
| safe_ai_forum_updates | Page timeout | Retry once; if still fails, skip and note in digest |
| idais_main | Page timeout | Retry once; if still fails, skip and note in digest |
| apollo_blog | Very low update frequency | R1-08 and R1-09B both found zero new items. Check weekly only. |

## Conditionally reliable

| Source | Method | Notes |
|--------|--------|-------|
| deepmind_blog | Browser + subagent | Main blog page loads. Individual article pages sometimes need subagent with console extraction. Rich content — often 2-3 risk-relevant articles per scan. |
| axrp | Browser | Very low episode frequency. Latest episode was #49 (Feb 18). Check weekly only. requires_human_review=true. |

## Helper coverage

| Source | Helper type | Status |
|--------|------------|--------|
| anthropic_news | scrapling_official_page | Simulated in R1-09B; works via browser |
| apollo_blog | scrapling_official_page | Simulated in R1-09B; no new content found |
| arxiv_ai_safety | arxiv_query | API unstable; degraded to browser search in R1-09B |
| techcrunch_ai | rss | Working reliably |
| axrp | scrapling_official_page | Simulated in R1-09B; no new episodes |
