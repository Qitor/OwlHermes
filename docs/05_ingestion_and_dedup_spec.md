# Ingestion and Dedup Spec v3

## 1. Operating model

Ingestion is Hermes-led. The backend does not decide what matters by crawling everything. It provides durable state, deduplication, historical lookup, and storage APIs that Hermes calls through MCP.

Optional deterministic helper collectors may be used only for stable low-intelligence sources:

- RSS；
- podcast RSS；
- arXiv；
- sitemap；
- simple webpage hash/diff。

Judgment-heavy discovery, transcript/video handling, research exploration, risk triage, and digest writing belong to Hermes-Agent and the custom AI risk observer skill.

## 2. Ownership of each step

### Discovery

Owner: Hermes-Agent.

Hermes uses registry metadata, built-in web/search/browser/video/transcript/research capabilities, and the custom skill rubric to decide which sources to inspect and what evidence is worth preserving.

### Raw item persistence

Owner: deterministic backend through MCP.

When Hermes or an optional helper finds potentially relevant material, it stores a raw item with source, URL, title, evidence text, metadata, and provenance.

### Deduplication

Owner: deterministic backend.

The backend performs URL canonicalization, exact content hash checks, same-source normalized title checks, and historical lookup so Hermes can avoid treating old or duplicate material as new.

Round 1 dedup is deliberately deterministic and offline. It does not fetch URLs,
inspect remote canonical links, use embeddings, or ask an LLM whether two items
are similar.

### Risk signal triage

Owner: Hermes-Agent.

Hermes decides whether a raw item changes risk judgment, extracts claims, assigns uncertainty, and forms signals according to the custom skill.

### Digest generation

Owner: Hermes-Agent.

Hermes writes the Chinese digest using stored signals, claims, evidence, benchmark observations, and source health. The backend stores the final digest and delivery records.

## 3. Raw item contract

Every persisted raw item should follow this shape:

```json
{
  "source_id": "anthropic_news",
  "modality": "web_article",
  "url": "https://...",
  "canonical_url": "https://...",
  "title": "...",
  "normalized_title": "...",
  "author": "...",
  "published_at": "2026-05-04T00:00:00Z",
  "fetched_at": "2026-05-04T01:00:00Z",
  "content_text": "...",
  "content_html": "...",
  "metadata": {},
  "content_hash": "sha256...",
  "dedup_key": "url:https://...",
  "first_seen_at": "2026-05-04T01:00:00Z",
  "last_seen_at": "2026-05-04T01:00:00Z",
  "seen_count": 1,
  "ingestion_status": "new",
  "language": "en"
}
```

For Hermes-discovered items, `fetched_at` means “observed/stored by workflow”, not necessarily “fetched by backend crawler”.

## 4. Modalities

- `web_article`
- `rss_item`
- `pdf_report`
- `arxiv_paper`
- `framework_page`
- `podcast_episode`
- `podcast_transcript`
- `youtube_video`
- `conference_agenda`
- `conference_talk`
- `summit_statement`
- `benchmark_observation`

## 5. Dedup Layers

### 5.1 URL Canonicalization

- lower host；
- remove tracking params；
- normalize trailing slash；
- remove URL fragments；
- preserve arXiv version when needed。

### 5.2 Exact Content Hash

对 normalized text 做 SHA256。

### 5.3 Source Title Match

Round 1 使用 same source ID + normalized title 的精确匹配作为弱 dedup signal。它只帮助 Hermes 避免重复 triage，不代表 backend 已做语义相似度判断。

### 5.4 Matching Priority

R1-05 matching priority:

1. same canonical URL；
2. same exact content hash；
3. same source ID plus normalized title。

Suggested dedup keys:

- `url:<canonical_url>`；
- `hash:<content_hash>`；
- `title:<source_id>:<normalized_title>`。

### 5.5 Event-Level Cluster

多个 raw items 可对应一个事件，例如：

- 官方 model release；
- 新闻报道；
- podcast 访谈解释；
- benchmark 分析；
- 政策回应。

这些应聚成同一个 `event_cluster`，但保留各自 source claims。

## 6. Podcast / Transcript Ingestion

Round 1/2 应优先让 Hermes 使用 built-in video/transcript/research skills 获取 transcript 或 evidence。Backend 不在 MVP 中变成完整 transcript scraping/transcription platform。

Backend 负责存储：

- episode/talk metadata；
- transcript URL or transcript text when Hermes provides it；
- transcript status；
- claim-level evidence；
- associated raw item / claim / signal IDs。

没有 transcript 时，只能基于标题/description 产生低置信度 candidate，不得直接生成 high-priority signal。

## 7. Event / Conference Ingestion

Hermes 使用 browser/research workflow 识别 agenda、speakers、materials、videos、slides 和 statements。Backend 存储 Hermes 发现的结构化 evidence。

Event raw item 应尽量保存：

- agenda title；
- speaker；
- affiliation；
- talk/panel title；
- abstract；
- time；
- material links；
- video links；
- slides links；
- page snapshot hash when available。

如果 agenda 或 materials 变化，应生成 raw item，进入 Hermes triage。

## 8. Framework Diff

Framework watch 是 Hermes-led；simple webpage hash/diff helper 可以辅助稳定页面。

对 manual_url/framework_page 可保存：

- HTML/text snapshot hash；
- section hash；
- old/new diff when helper has prior snapshot；
- Hermes-generated interpretation；
- risk framework signal triage。

## 9. Failure Handling

- 单个 source fail 不影响全局流程；
- optional helper fail 记录 source run / source_health；
- Hermes research failure 应记录 skipped reason 或 needs_human_review；
- 连续失败 3 次后在日报 source health 中提示；
- podcast/video 大文件或 transcript failure 不应阻塞 daily digest。
