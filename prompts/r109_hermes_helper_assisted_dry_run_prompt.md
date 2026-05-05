# R1-09B: Helper-Assisted Daily Dry Run Prompt

You are running a **helper-assisted daily dry run** for the AI Risk Signal Observatory.

Use the `ai-risk-signal-observer` skill in **helper-assisted dry-run mode**.

## Constraints

- This is a **NON-PRODUCTION DRY RUN**. Label all output accordingly.
- Do NOT post externally (no Feishu, WeCom, WeChat, Telegram, Discord, email).
- Do NOT schedule recurring tasks or cron jobs.
- Do NOT build or update the website.
- Use the local SQLite dry-run database only.
- Write output in Chinese.
- Do NOT browse broadly. Prefer helper candidates over general search.

## Step 1: Source Health Check

Call `risk_source_health_summary` to understand helper coverage and known issues.

Review the output for:
- Which sources have helpers vs. need manual browsing
- Sources marked `requires_human_review`
- Invalid URLs or known issues

## Step 2: Select 3-5 Sources

Call `risk_registry_list_due_sources` with limit 10.

Select **3-5 sources**, preferring sources with helper metadata:
- `anthropic_news` (frontier AI lab, helper: scrapling_official_page)
- `apollo_blog` (eval/safety lab, helper: scrapling_official_page)
- `arxiv_ai_safety` (research, helper: arxiv_query)
- `techcrunch_ai` (news, helper: rss)
- `axrp` (podcast, helper: scrapling_official_page)

Include at least:
- one frontier lab source if possible
- one eval/safety lab source if possible
- one research/arXiv/news source if possible
- one podcast/event source if possible

## Step 3: Helper Preview for Selected Sources

For each selected source that has a helper configured:
- Call `risk_discovery_helper_preview(source_id="<source_id>", fetch=True, limit=10)`
- Use `fetch=true` **only** for these explicitly configured allowlisted source URLs:
  - anthropic_news: https://www.anthropic.com/news
  - apollo_blog: https://www.apolloresearch.ai/blog/
  - arxiv_ai_safety: arXiv API query
  - techcrunch_ai: https://techcrunch.com/category/artificial-intelligence/feed/
  - axrp: https://axrp.net/
- Review the candidates — these are raw links/titles, NOT final risk judgments.
- If helper preview returns 0 candidates, report why and fallback conservatively (use limited web search only for that source).

## Step 4: Triage Candidates

For each interesting candidate from Step 3:
1. Use your built-in web/search tools to read the full content if needed — but only for candidate items, not broad search.
2. Call `risk_raw_item_seen_check(url="<candidate_url>")` before storing.
3. If uncertain about duplication, call `risk_raw_item_duplicate_candidates(url="<candidate_url>")`.
4. If NOT seen, call `risk_raw_item_store(raw_item={...})` with source_id, url, title, content_text.
5. If the item genuinely changes risk understanding, call `risk_signal_store(signal={...})`.

## Step 5: Record Source Runs

Call `risk_source_run_record(source_run={...})` for **every** source you checked, whether via helper or manually.

Include helper usage notes in metadata where possible:
```json
{"helper_used": true, "helper_type": "scrapling_official_page", "candidates_count": 5}
```

## Step 6: Write Dry-Run Digest

Call `risk_digest_store(digest={...})` with status `dry_run`.

The Chinese digest must include these sections:
- **非生产 dry-run 标识** (non-production label)
- 今日一句话总览
- Top Signals
- 政策/治理
- Benchmark 与评估
- 前沿实验室与模型发布
- 新型风险
- 风险框架与标准
- 播客/访谈重点
- 会议/论坛/峰会重点
- arXiv/研究趋势
- 需进一步深挖
- **Helper 使用情况** (which helpers were used, how many candidates each returned, whether they reduced broad search need)
- **来源健康状态** (source reliability issues, stale URLs, entries needing human review)
- **与 R1-08 对比** (comparison to previous dry run: more/fewer sources checked, helper usefulness, duplicate detection)

Include evidence URLs and uncertainty markers throughout.

## Important Reminders

- Helper candidates are NOT final risk judgments. You must still evaluate each candidate.
- Always call `risk_raw_item_seen_check` BEFORE `risk_raw_item_store`.
- Call `risk_signal_store` ONLY after you judge an item to be a genuine risk signal.
- `signals = 0` is acceptable if no genuine new signals are found.
- `raw_items_new = 0` is acceptable if all candidates were already seen (R1-08 data exists in DB).
- Report helper fetch failures or empty results transparently.
