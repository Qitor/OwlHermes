# Source Modality Spec

## 1. 为什么需要 modality

AI 风险信号不只来自网页文章。播客、访谈、会议议程、slides、system card、framework diff、benchmark observation 都需要不同处理方式。

`category` 表示来源属性，`modality` 表示内容形态。

例如：

```yaml
category: podcast
modality: podcast_episode
collector: podcast_feed
```

## 2. Allowed Modalities

- `web_article`
- `rss_feed`
- `pdf_report`
- `arxiv_paper`
- `framework_page`
- `podcast_episode`
- `podcast_transcript`
- `youtube_video`
- `conference_agenda`
- `conference_materials`
- `summit_statement`
- `benchmark_observation`

## 3. Collector / Workflow Hints

`collector` is a registry hint for Hermes workflow selection and optional deterministic helpers. It does not mean this repository should implement a general crawler for every source type.

- `rss`
- `web_index`
- `manual_url`
- `arxiv`
- `podcast_feed`
- `youtube_channel`
- `event_page`
- `agenda_diff`
- `benchmark_registry`

## 4. Extractor Strategy

每个 source 必须声明 `extractor_strategy`：

```yaml
extractor_strategy:
  list_selector: null
  title_selector: null
  date_selector: null
  content_selector: null
  transcript_source: official|youtube_caption|none
  diff_mode: full_text|section_hash|agenda_items
  requires_js: false
  rate_limit_seconds: 10
```

Round 1 可以允许很多字段为 null，但字段结构必须存在，便于逐步硬化。

## 5. Source Priority

- `high`：一手或核心风险来源；
- `medium`：高质量二手/补充来源；
- `low`：探索性来源，默认更严格筛选。

## 6. Registry Validation

启动时必须检查：

- id 唯一；
- category 合法；
- modality 合法；
- collector 合法；
- url/feed_url 至少一个存在；
- risk_focus 非空；
- enabled 为 bool；
- refresh_interval 合法。
