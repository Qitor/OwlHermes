# R1-08 Hermes Daily Dry Run Prompt

Use the `ai-risk-signal-observer` skill in **dry-run mode**.

This is a controlled, non-production dry run. You must follow these constraints:

## Constraints

- Do NOT post to Feishu, WeCom, WeChat, Telegram, Discord, email, or any external delivery channel.
- Do NOT build or update the website.
- Do NOT run cron or schedule any recurring tasks.
- Do NOT browse broadly — only inspect the selected sources listed below.
- Do NOT generate production signals or digests — all output is labeled dry-run.
- Keep the run small and bounded.

## Step 1: Read due sources

Call `risk_registry_list_due_sources` with limit 10.

From the results, select exactly 3-5 sources that provide a balanced coverage set:
- one frontier lab source (e.g. anthropic_news, openai_news, google_deepmind_blog);
- one eval/safety lab source (e.g. arc_news, apollo_blog, metr_news);
- one policy/governance/coordination source (e.g. ai_safety_summit_series, nist_ai_rmframework);
- one podcast/event/benchmark source (e.g. ai_agent_security, latent_variations_podcast).

If a category has no available source, substitute with another high-priority source.

## Step 2: Inspect selected sources

For each selected source, use your built-in web/search/research tools to:
- Check the source URL or feed for recent updates;
- Identify any new or notable items published in the last 7 days;
- Note the item title, URL, and a brief description.

Do NOT fetch or read more than necessary for each source.

## Step 3: Seen-check and store candidates

For each candidate item you find:

1. Call `risk_raw_item_seen_check` with the item URL to check if it was already seen.
2. If not seen, call `risk_raw_item_store` with:
   - `source_id`: the registry source ID
   - `kind`: the source modality (e.g. "web_article", "podcast")
   - `url`: the item URL
   - `title`: the item title
   - `content_text`: a brief summary or evidence excerpt
3. If you are uncertain about duplication, call `risk_raw_item_duplicate_candidates` with the URL or title.

## Step 4: Record source runs

For each source you checked, call `risk_source_run_record` with:
- `source_id`: the registry source ID
- `kind`: the source type
- `status`: "success" if checked, "error" if failed
- `items_found`: number of candidate items found
- `items_new`: number of items stored (not duplicates)
- `items_duplicate`: number of items that were already seen

## Step 5: Judge signals (optional but encouraged)

If you find a genuine risk signal — something that changes risk understanding — call `risk_signal_store` with:
- `source_id`: the relevant source
- `title`: concise Chinese title
- `summary`: concise Chinese summary
- `signal_type`: e.g. "lab_update", "policy_change", "eval_result", "risk_framework"
- `risk_domain`: e.g. "frontier_model", "governance", "evaluation"
- `severity`: 1-5
- `confidence`: 1-5
- `evidence_url`: primary source URL

Only store a signal if you genuinely judge it to change risk understanding.
It is acceptable to store 0 signals if nothing meets the bar.

## Step 6: Write dry-run digest

Write a concise Chinese dry-run digest with these sections:

- **标识**: 明确标注"非生产 dry-run，仅供技术验证"
- **今日一句话总览**
- **已检查来源列表** (with source IDs and check status)
- **候选条目摘要** (for each raw item stored)
- **信号判断** (for each signal stored, or "本轮未发现高置信度新信号")
- **证据和不确定性**
- **需进一步深挖**

Then call `risk_digest_store` with:
- `digest_date`: today's date
- `title`: "R1-08 非生产 Dry Run 简报"
- `body`: the full Chinese digest text
- `status`: "dry_run"

## Output format

After completing all steps, provide a brief English summary of:
- How many sources were checked
- How many raw items were stored
- How many signals were stored (0 is acceptable)
- Whether the dry-run digest was stored
- Any issues encountered
