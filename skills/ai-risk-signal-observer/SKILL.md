---
name: ai-risk-signal-observer
description: Run the Hermes-led daily frontier AI risk intelligence workflow — identify signals, triage, produce Chinese risk digest.
tags: [risk, ai-safety, daily-report, frontier-ai]
---

# AI Risk Signal Observer

Use this skill to run the Hermes-led daily frontier AI risk intelligence workflow.

## Purpose

Identify frontier AI risk signals from labs, eval organizations, policy labs, governments, arXiv, podcasts/interviews, conferences/forums, and trusted news sources.

The output is not a news summary. It is a concise Chinese risk intelligence digest with evidence and uncertainty.

## Core Questions

Every signal must answer:

1. What changed?
2. Why does it matter?
3. What should we watch next?

## Daily Workflow

1. Read due/high-priority sources from the registry through MCP tools when available, especially `risk_registry_list_due_sources` and `risk_registry_get_source`.
2. Use Hermes built-in web/search/browser/video/transcript/research tools where appropriate. Do not rely on backend collectors for judgment-heavy discovery.
3. Before deep triage, check history through `risk_raw_item_seen_check`, `risk_raw_item_search`, and when useful `risk_raw_item_duplicate_candidates`.
4. Store relevant discovered candidate evidence through `risk_raw_item_store`, preserving source URL, title, evidence text, metadata, and uncertainty. If the tool reports a duplicate, inspect the prior item before continuing.
5. For each relevant item:
   - classify relevance;
   - distinguish fact, research result, prediction, commentary;
   - extract claim-level evidence for podcast/interview/event material;
   - produce a signal only if it changes risk judgment.
6. Store a signal through `risk_signal_store` only after Hermes has judged the item to change risk understanding. Use `risk_signal_search` for historical signal lookup. Store benchmark/framework observations through `risk_benchmark_observation_store` when that backend service is available.
7. Store evidence/claim items through `risk_evidence_store`. Use `risk_evidence_search` to look up existing evidence linked to a signal or raw item. Evidence items capture claim-level detail (claim_text, evidence_url, evidence_excerpt, confidence, supports_signal) that supports or weakens a signal.
8. Generate a concise Chinese digest with sections:
   - 今日一句话总览；
   - Top Signals；
   - 政策/治理；
   - Benchmark 与评估；
   - 前沿实验室与模型发布；
   - 新型风险；
   - 风险框架与标准；
   - 播客/访谈重点；
   - 会议/论坛/峰会重点；
   - arXiv/研究趋势；
   - 需进一步深挖；
   - 来源健康状态。
9. Store the digest through `risk_digest_store`; use `risk_digest_search` for prior digest lookup.
10. Send via configured Hermes gateway.
11. Record source runs through `risk_source_run_record`. Delivery integration is handled by configured Hermes gateway/runtime later.

## Helper-Assisted Discovery (R1-09)

Source reliability helpers are deterministic collectors that fetch candidate items from configured sources. They do NOT judge risk, call LLMs, or store raw items. Use them to pre-filter what to triage.

## Model-Tiered Preprocessing (R1-11B)

An optional small/fast model can be used for low-risk advisory tasks:

- `risk_candidate_preprocess(title, url?, content_text?, source_id?, focus?, risk_domain?)` — returns advisory summary, evidence excerpt, possible risk domains, and lightweight classification. Output is **advisory only** — never treat it as final risk judgment.

### What small models may do (advisory only)

- Summarize long candidate text
- Extract evidence excerpts
- Suggest possible risk domains
- Provide lightweight relevance classification

### What small models must NOT do

- Make final risk signal decisions
- Replace Hermes judgment on what counts as a signal
- Determine severity or confidence scores
- Write final report sections

### Safety rule

Store final signals only after Hermes applies the quality rubric. Mark uncertainty and `needs_human_review` when relying on weak or advisory evidence.

### Helper types

| Type | What it does |
|------|-------------|
| `scrapling_official_page` | Scrapes an official page, extracts links matching include/exclude patterns |
| `rss` | Parses an RSS/Atom feed |
| `podcast_rss` | Parses a podcast RSS feed (episodes with enclosures) |
| `arxiv_query` | Queries the arXiv API with a configured search query |
| `manual` | No automated helper; Hermes must browse manually |
| `none` | No helper configured; Hermes must browse manually |

### Workflow with helpers

1. Call `risk_source_health_summary` to see helper coverage and known issues.
2. For each due source with a helper, call `risk_discovery_helper_preview(source_id, fetch=True)` to get candidate items.
3. Review candidates: these are raw links/titles, not triaged signals.
4. For interesting candidates, use Hermes built-in web/search/browser tools to read the full content.
5. Then follow the normal Daily Workflow (seen-check → raw_item_store → signal → digest).

### Important

- Helpers fetch structured data deterministically — they do not replace Hermes judgment.
- Always call `risk_raw_item_seen_check` before storing items found by helpers.
- Entries with `requires_human_review: true` may have stale URLs or other known issues.
- If a helper returns no candidates, the source may need manual browsing.

## Special Rules

### Safe AI Forum

SAIF means Safe AI Forum. Do not confuse it with Google Secure AI Framework. If Google Secure AI Framework is monitored, call it `google_secure_ai_framework`.

### Podcast / Interview

A podcast episode is not a signal by default. Use Hermes transcript/video/research capabilities when available, then extract claim-level items.

High-value claims include:

- frontier lab researchers' new statements;
- new eval or benchmark details;
- safety policy changes;
- deployment threshold changes;
- risk timeline predictions;
- disagreement with official documents.

No transcript means low confidence.

### Event / Conference

A conference being announced is usually not a signal. Upgrade only if there is:

- new statement;
- red line;
- safety commitment;
- policy guide;
- benchmark/eval/framework;
- important talk/materials relevant to AI risk.

### Evidence

Prefer primary sources. Always keep source URL. Mark `needs_human_review` for high-impact low-confidence claims.

**Rule: For each Top Signal, you MUST store at least one evidence item via `risk_evidence_store`.** Intermediate evidence objects are part of the product — do not only store the final digest.

Use `risk_evidence_store` to persist claim-level evidence linked to a signal or raw item. Use `risk_evidence_search` to look up existing evidence. Each evidence item should include:
- `claim_text`: what was claimed or observed
- `evidence_url`: primary source URL
- `evidence_excerpt`: relevant excerpt from the source
- `confidence`: 1-5 confidence level
- `supports_signal`: whether this evidence supports or weakens the linked signal
- `risk_domains`: relevant risk domains

If evidence excerpt is unavailable, set `needs_human_review: true` and include a `needs_review_reason`.

When using `risk_signal_store`, include the three-question fields: `what_changed`, `why_it_matters`, `what_to_watch_next`.

## Live Vault Logging (R1-13)

During a daily report or interactive run, you may use live Obsidian vault tools to record research progress in real time. Live logging is **optional and disabled by default**.

**Live vault tools:**

- `risk_live_run_start` — Start a live research run. Creates a run directory in the Obsidian vault.
- `risk_live_event_append` — Append a research event (source selected, candidate found, evidence extracted, signal stored, etc.). Supports `note_vault_path` for timeline wikilinks.
- `risk_live_note_upsert` — Write or update a source, candidate, evidence, or signal note within the live run. Supports `daily_report_date`, `related_signal_ids`, `related_evidence_ids`, `related_candidate_ids`, `related_source_ids`, `risk_domains` for bidirectional links.
- `risk_live_run_finalize` — End the live research run with a summary. Accepts `final_report_markdown` and `daily_report_date` to write the daily note immediately.
- `risk_live_daily_report_upsert` — Write or update the final daily report note in `00_Daily/YYYY-MM-DD.md`. Use when the final report is ready and you want it visible in Obsidian immediately.

**Auto-mirror (R1-13D):**

When live vault is enabled, `risk_signal_store`, `risk_evidence_store`, and `risk_raw_item_store` automatically create corresponding Obsidian notes in the active live run. You do NOT need to manually call `risk_live_note_upsert` for every signal or evidence — the system handles this automatically. You can still manually call `risk_live_note_upsert` to supplement or update note content.

**When to use:**

- At the start of daily-report or interactive mode, call `risk_live_run_start` if available.
- When selecting a source, append `source_selected`.
- When starting/completing a source check, append `source_check_started`/`source_check_completed`.
- When source fails, append `source_failed` and/or upsert a `failure` note.
- Signal/evidence/candidate notes are auto-mirrored — no manual `risk_live_note_upsert` needed.
- When digest is stored, append `digest_stored`.
- When the final report is ready, call `risk_live_daily_report_upsert` with the **full report markdown** as `report_markdown` (NOT a reference like "See digest xxx").
- At end, call `risk_live_run_finalize` with `final_report_markdown` (**full report markdown**, NOT a reference) and `daily_report_date`.

**Important:**

- If `risk_live_run_start` returns `live_logging_enabled: false`, **continue normally without live logging**.
- Live vault writing is **observational/persistence only** — it must not replace DB tools.
- You must still call: seen-check, raw item store, evidence store, signal store, digest store.
- **Do NOT write private chain-of-thought or hidden reasoning into Obsidian.** Live notes should contain observable research state only: source checked, candidate found, evidence excerpt, judgment summary, uncertainty, next step.
- All live vault writes are constrained to `OBSIDIAN_VAULT_PATH` — no arbitrary file writes.
- **Live immediate write vs export backfill**: `risk_live_daily_report_upsert` writes the daily note in real time during the run. `make obsidian-export` is for backfill, repair, and full consolidation — not for normal daily UX. You do NOT need to tell the user to run `make obsidian-export` to see the final report.
- **Full report required**: When calling `risk_live_daily_report_upsert` or `risk_live_run_finalize`, you MUST pass the complete report markdown as `report_markdown` or `final_report_markdown`. Do NOT pass a short reference like "See digest xxx" — this will corrupt the daily note.

## Modes

### Smoke-test mode

"Use the ai-risk-signal-observer skill in smoke-test mode."

- Do NOT browse the web or fetch URLs.
- Do NOT run a daily briefing or production digest.
- Do NOT triage or generate signals.
- Only call these safe deterministic state tools:
  - `risk_registry_summary` — verify registry is loaded.
  - `risk_registry_list_due_sources` — verify due-source listing works.
  - `risk_raw_item_seen_check` — verify seen-check with a fake URL.
- Report which MCP tools are available and whether the three smoke calls succeeded.

### Dry-run mode

"Use the ai-risk-signal-observer skill in dry-run mode."

- May browse/search only selected 3-5 sources.
- Must NOT post externally. Must NOT run cron. Must NOT build website.
- Must call `risk_raw_item_seen_check` before storing.
- Must call `risk_raw_item_store` for candidate items.
- Must call `risk_source_run_record` for each source.
- Must call `risk_signal_store` only after genuine risk judgment.
- Must call `risk_digest_store` with status `dry_run`.
- Chinese output, evidence URLs, uncertainty, labeled as dry run.

### Helper-assisted dry-run mode

"Use the ai-risk-signal-observer skill in helper-assisted dry-run mode."

Same as dry-run mode, plus:
- Must call `risk_source_health_summary` first.
- Must call `risk_discovery_helper_preview` for helper-enabled sources.
- `fetch=true` only for explicitly configured allowlisted URLs.
- Helper candidates are NOT final risk judgments.
- Include helper usage report in digest.

### Local daily-report mode

"Use the ai-risk-signal-observer skill in local daily-report mode."

This is the production-oriented local mode. Produce today's AI risk daily report.

- Do NOT post externally unless explicitly in future production mode.
- Do NOT run cron. Do NOT build website.
- Start with `risk_source_health_summary` to understand source availability.
- Call `risk_registry_list_due_sources`, select 5-8 sources with balanced coverage.
- Use `risk_discovery_helper_preview` before broad search.
- Call `risk_raw_item_seen_check` before storing.
- Store only not-seen items via `risk_raw_item_store`.
- Record every source via `risk_source_run_record`.
- Store signals only after risk judgment via `risk_signal_store`.
- Store final report via `risk_digest_store` with status `local_daily_report`.
- Write the report in Chinese per the report structure.
- Include evidence, uncertainty, helper usage, and follow-up items.

**Finalization sequence (must follow in order):**

1. `risk_digest_store` — store the digest to the backend DB first.
2. `risk_live_daily_report_upsert` — write the final report to Obsidian vault.
3. `risk_live_run_finalize` — close the live run with summary and quality score.

Do NOT finalize the live run before the digest is stored — if the digest store fails, fix the schema error and retry before proceeding to steps 2-3.

### Interactive observation mode

"Use the ai-risk-signal-observer skill in interactive observation mode."

Same as local daily-report mode, plus:
- Show progress and tool-call intentions as you work.
- Let the human observer follow your reasoning.
- Keep the run bounded but visible.
- **Expose editorial judgment, not just tool calls.** For each source and candidate, explain:
  - Why you chose this source over another
  - Why a candidate was judged as signal or non-signal
  - Where evidence is weak and how confident you are
  - Which items are included vs excluded
- **Override subagent severity assessments.** Subagents may assign severity 5; apply your own editorial calibration and explain the adjustment.
- **Examples of exposed judgment:**
  - "选择 anthropic_news 而非 google_deepmind_blog，因为 Anthropic 本周有 RSP 更新传闻"
  - "这条 TechCrunch 报道看起来是产品公告，缺乏风险维度，不升级为信号"
  - "子代理初始评估为 severity 5，我降至 4：框架识别了评估缺口但不代表能力跳升"

## Operational Patterns

### Subagent deep-read pattern

When scanning multiple sources, use `delegate_task` with browser toolset to deep-read long articles in parallel while you continue scanning other sources. This significantly reduces wall-clock time.

**Recommended parallel workflow:**

1. Run `risk_discovery_helper_preview` for 5-6 sources in parallel.
2. From helper results, identify 3-4 candidates worth deep-reading.
3. Launch `delegate_task` for deep-reads **in parallel with** `risk_raw_item_seen_check` — don't wait for deep-reads to finish before checking seen status.
4. When deep-read subagents complete, extract full UUIDs from their stored items/signals/evidence for use in your own downstream calls.
5. For any evidence_store calls referencing subagent-created signals, use the **full UUID** (not truncated) from the subagent output.

Rules for subagent delegation:
- Provide clear extraction goals (what to extract, in what language).
- Always include the source_id for seen-check and raw_item storage.
- Subagent signal stores may fail with schema errors — re-store from the main agent if needed.
- **Capture full UUIDs from subagent results.** Subagents may return truncated IDs in their summary text — always look for the full UUID in the tool_trace or structured output.
- Apply your own severity/confidence judgment; do not blindly accept subagent assessments.
- Verify subagent-found URLs before citing them in the digest.
- Subagents may hit `max_iterations` exit before completing all goals — check their summary for completeness and follow up on any gaps yourself.
- When a source is known to be blocked (e.g., OpenAI + Cloudflare), tell the subagent upfront so it can pivot to search engines immediately rather than wasting iterations on failed navigations.
- Subagents using search engines: Yahoo Search works reliably without CAPTCHAs; Google and DuckDuckGo may trigger CAPTCHAs.

### Article quality filters

Not every candidate warrants a deep-read investment:

- **TechCrunch "In Brief" articles**: Short summaries with limited information density. If the topic seems risk-relevant based on the title/excerpt, do a quick browser read yourself rather than delegating a full deep-read. Deep-read investment rarely pays off for these.
- **Press releases / product announcements**: May lack risk dimension entirely. Scan for safety/RSP/governance mentions before investing deep-read time.
- **arXiv preprints**: Focus on those with explicit safety/alignment/evaluation methodology. Pure capability papers (new SOTA on benign benchmarks) are low-priority unless they demonstrate capability jumps.

### Backend tool quirks

- `risk_signal_store` requires a `summary` field (string). Omitting it causes a validation error. The schema also requires `what_changed`, `why_it_matters`, `what_to_watch_next`, `title`, `risk_domains`, `signal_type`, `signal_date`, `severity`, `confidence`, and `evidence_url`. If it fails, retry with the same or slightly simplified payload. Common failures: (1) missing `summary`; (2) passing empty arrays for `source_ids`/`raw_item_ids`.
- **UUID format requirement**: `risk_evidence_store` and other tools that accept `signal_id` or `raw_item_id` require **full UUID strings** (e.g. `84496323-b568-4a00-b8ed-072236b27295`), NOT truncated/short IDs. Passing a short ID like `"ffc8780d"` causes `"badly formed hexadecimal UUID string"` validation error. When subagents store signals and return IDs, always capture the **full UUID** from their output for use in downstream evidence_store calls.
- `risk_benchmark_observation_store` is not yet implemented — do not rely on it.
- `risk_raw_item_store` deduplicates by canonical_url. Same article from a different source_id returns `is_duplicate: true` — do not re-store. Note: `is_duplicate: true` with a valid item in the response means the item was already stored by a subagent — you can use the returned `item.id` for linking evidence.
- `risk_source_run_record` may report `items_new: 0` even when items were stored — do not rely on it for counting; track new items separately.
- `risk_discovery_helper_preview` for AXRP returns navigation links (homepage, RSS, Patreon, etc.) instead of episode listings. The helper is not useful for AXRP episode discovery — browse manually or use the RSS feed URL (`https://axrp.net/feed.xml`).
- **Helper preview limit tuning**: High-volume sources like `arxiv_ai_safety` return very large payloads (~76K chars with `limit=20`). Use `limit=5-10` for arXiv and similar high-volume sources. Lower limits reduce context pressure and are sufficient since you'll deep-read only the top 2-3 candidates anyway.
- `risk_digest_store` requires a JSON `digest` parameter (not individual top-level fields). The JSON must contain `digest_date` (not `date`), `title`, and `body` (not `digest`). Common mistake: passing `date` and `digest` as top-level keys causes validation error. Correct shape: `{"digest_date": "2026-05-06", "title": "...", "body": "...", "status": "local_daily_report", "run_id": "...", "source_ids": [...], "summary": {...}}`. The `summary` field is a JSON object (not a string) with keys like `new_raw_items`, `new_signals`, `new_evidence_count`, `top_signals`, `sources_checked`, `helper_issues`.

### Source reliability

See `references/source-reliability.md` for consolidated source reliability notes from R1-08 through R1-05. Key points:
- **Most reliable**: TechCrunch RSS, AISI blog, Anthropic news
- **Frequently failing**: OpenAI (Cloudflare), arXiv API (rate-limit/policy), SAIF/IDAIS (timeout)
- **Low frequency**: Apollo blog, AXRP — check weekly, not daily

### Normal/production mode (future)

Not yet implemented. Will add external delivery when ready.

When the skill is invoked in **helper-assisted dry-run mode** (e.g. "use the ai-risk-signal-observer skill in helper-assisted dry-run mode"), follow these rules:

- This is non-production. Label all output accordingly.
- Must NOT post externally (no Feishu, WeCom, WeChat, Telegram, Discord, email, or any delivery channel).
- Must NOT run cron or schedule recurring tasks.
- Must NOT build or update the website.
- Must NOT browse broadly — prefer helper candidates over general search.
- Must call `risk_source_health_summary` first to understand helper coverage.
- Must call `risk_registry_list_due_sources` to get due sources.
- Select 3-5 sources, preferring sources with helper metadata.
- For helper-enabled sources, must call `risk_discovery_helper_preview(source_id, fetch=True, limit=10)`.
- Use `fetch=true` only for explicitly configured allowlisted source URLs.
- Treat helper candidates as candidate items only — NOT final risk judgments.
- Must call `risk_raw_item_seen_check` before storing any candidate.
- Must call `risk_raw_item_duplicate_candidates` if uncertain about duplication.
- Must call `risk_raw_item_store` only for not-seen candidates.
- Must call `risk_source_run_record` for every checked source. Include helper usage metadata.
- Must call `risk_signal_store` only after judging a genuine risk signal.
- Must call `risk_digest_store` with status `dry_run`.
- Must write the digest in Chinese.
- Digest must include: helper usage report, source reliability issues, and comparison to previous runs if applicable.
- Must include evidence URLs and uncertainty.
- Must explicitly label the output as non-production dry run.
- If helper preview returns 0 candidates, report why and fallback conservatively.
- `signals = 0` is acceptable if no genuine new signals found.
- `raw_items_new = 0` is acceptable if all candidates were already seen.

When the skill is invoked in dry-run mode (e.g. "use the ai-risk-signal-observer skill in dry-run mode"), follow these rules:

When the skill is invoked in dry-run mode (e.g. "use the ai-risk-signal-observer skill in dry-run mode"), follow these rules:

- May browse/search only the selected 3-5 sources.
- Must NOT post externally (no Feishu, WeCom, WeChat, Telegram, Discord, email, or any delivery channel).
- Must NOT run cron or schedule recurring tasks.
- Must NOT build or update the website.
- Must call `risk_raw_item_seen_check` before deep triage.
- Must call `risk_raw_item_store` for candidate evidence items.
- Must call `risk_raw_item_duplicate_candidates` when uncertain about duplication.
- Must call `risk_source_run_record` for each checked source.
- Must call `risk_signal_store` only after judging a genuine risk signal.
- Must call `risk_digest_store` with status `dry_run`.
- Must write output in Chinese.
- Must include evidence URLs and uncertainty.
- Must explicitly label the output as non-production dry run.
- Keep the run small and bounded.

When the skill is invoked in smoke-test mode (e.g. "use the ai-risk-signal-observer skill in smoke-test mode"), follow these restrictions:

- Do NOT browse the web or fetch URLs.
- Do NOT run a daily briefing or production digest.
- Do NOT triage or generate signals.
- Only call these safe deterministic state tools:
  - `risk_registry_summary` — verify registry is loaded.
  - `risk_registry_list_due_sources` — verify due-source listing works.
  - `risk_raw_item_seen_check` — verify seen-check with a fake URL (e.g. `https://example.com/hermes-risk-observer-smoke?utm_source=test`).
- Report which MCP tools are available and whether the three smoke calls succeeded.

This mode exists to validate Hermes-Agent ↔ backend integration without side effects.

## Output Style

Chinese, concise, evidence-backed. Avoid hype. Avoid claiming certainty when evidence is only a podcast prediction or news commentary.
