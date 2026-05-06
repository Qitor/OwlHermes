# Hermes AI Risk Signal Observatory — Codex 开工文档包 v3

本包用于让 Codex 直接开始实现一个**基于 Hermes-Agent 的前沿 AI 风险信号观测平台**。

v3 相比 v2 的核心修改：

0. **开发执行工具从 Claude Code 改为 Codex**：新增 Codex 专用 `AGENTS.md`、`docs/00_codex_master_prompt.md`、`docs/14_codex_execution_guide.md`、`docs/15_round1_codex_task_cards.md`、`configs/codex_config.example.toml`。


1. **SAIF 已修正为 Safe AI Forum**，不再误写为 Google Secure AI Framework。
2. 数据源范围从网页/RSS/论文扩展到：
   - 播客与长访谈；
   - YouTube/视频访谈；
   - 国际会议、峰会、workshop、论坛议程；
   - 会议材料、slides、transcripts、policy guide、联合声明；
   - benchmark/eval registry 与框架 diff。
3. 重新收窄 MVP：先做 12–18 个高质量核心来源，跑通端到端闭环；不要一开始追求全量覆盖。
4. 强化“情报产品”定位：每条信号必须回答 `what changed / why it matters / what to watch next`。
5. 增加 source modality 规范、podcast/event monitoring 规范、benchmark registry 规范。

## 产品定位

这不是一个 AI 新闻聚合器，而是一个面向 AI safety / AI governance / frontier model policy 团队的：

> 前沿 AI 风险情报雷达（frontier AI risk intelligence layer）

每天由 Hermes-Agent 主导，从 frontier AI labs、eval labs、policy labs、政府/国际组织、论文、播客、访谈、会议和权威媒体中识别真正会改变风险判断的信息，并把证据、raw items、claims、signals、digests 沉淀为可检索、可审计、可追踪的后端状态。

## 推荐执行方式

Codex 应先阅读：

1. `AGENTS.md`
2. `docs/00_codex_master_prompt.md`
3. `docs/01_product_requirements.md`
4. `docs/02_hermes_based_architecture.md`
5. `docs/03_implementation_plan.md`
6. `docs/11_source_modality_spec.md`
7. `docs/12_podcast_event_monitoring_spec.md`
8. `docs/14_codex_execution_guide.md`
9. `docs/15_round1_codex_task_cards.md`
10. `source_registry/sources.yaml`
11. `source_registry/podcasts.yaml`
12. `source_registry/events.yaml`
13. `source_registry/benchmark_registry.yaml`

然后严格按 `docs/15_round1_codex_task_cards.md` 中的 R1 task cards 执行。建议一个 Codex 会话只做一个 task card，不要一次性尝试完成全部系统。

## Hermes-Agent 使用边界

Hermes-Agent 应承担：

- cron 定时触发每日工作流；
- 通过 MCP 调用后端工具；
- 使用内置 skills/tools 进行 web/search/browser/video/transcript/research exploration；
- 使用 `skills/ai-risk-signal-observer/SKILL.md` 固化 AI risk domain workflow；
- 做 source prioritization、triage、打分、摘要、聚类建议；
- 生成中文日报、周报和网站摘要；
- 通过 gateway 推送到飞书/企业微信/微信等渠道。

自建后端承担：

- source registry 读取；
- registry validation；
- durable raw item / claim / signal / digest / benchmark observation persistence；
- dedup、historical lookup、similar item search；
- Postgres 存储；
- 网站 API；
- source run records、source health 与审计日志；
- 可选确定性 helpers：RSS、podcast RSS、arXiv、sitemap、简单网页 hash/diff。

原则：**Hermes-led signal observation with deterministic backend state**。判断型 discovery、research、triage、digest 由 Hermes 处理；本仓库提供小而可靠的状态和工具，不替代 Hermes-Agent，不实现通用 crawler/agent runtime。

## 目录

- `docs/`：产品、架构、实施、Codex 执行、数据源、播客/会议、benchmark、验收文档。
- `source_registry/`：网页/机构、播客、会议、benchmark 数据源注册表。
- `skills/ai-risk-signal-observer/SKILL.md`：Hermes skill。
- `frontier_ai_risk_observer/mcp/`：R1-06 MCP state-tool adapter；`mcp_server_scaffold/` 仅保留兼容 launcher。
- `schemas/schema.sql`：PostgreSQL schema。
- `prompts/`：Hermes triage、digest、podcast/event prompts。
- `configs/`：Hermes、Codex、Docker、环境变量配置模板。
- `tests/`：验收 checklist。

## R1-01 本地开发

R1-01 只建立 Python backend 骨架、最小 API、registry loader、MCP placeholder 和 smoke tests；不实现真实 collectors、数据库迁移、Hermes runtime 集成、推送或网站。

```bash
make install
make test
make lint
make typecheck
make run-api
```

手动运行 API：

```bash
uvicorn frontier_ai_risk_observer.api.main:app --host 127.0.0.1 --port 8787 --reload
```

当前可用端点：

- `GET /health`
- `GET /version`

## R1-02 数据库基础

R1-02 接入 PostgreSQL 数据库基础。`schemas/schema.sql` 是第一版 schema 的 source of truth；当前使用直接初始化命令执行该 SQL，暂不引入 Alembic migration 历史。

默认本地连接使用：

```bash
DATABASE_URL=postgresql+psycopg://risk:risk@localhost:5432/risk_signal
```

也可以用环境变量覆盖：

```bash
export DATABASE_URL=postgresql+psycopg://risk:risk@localhost:5432/risk_signal
make db-check
make db-init
```

数据库相关命令：

```bash
make db-check   # 执行 SELECT 1 readiness 检查
make db-init    # 执行 schemas/schema.sql 初始化本地 PostgreSQL
```

健康检查分工：

- `GET /health`：轻量进程健康检查，不连接数据库。
- `GET /ready`：数据库 readiness 检查；数据库未配置或不可连接时返回 `503` 和受控错误 JSON。

Hermes-Agent 是外部 runtime 依赖，本仓库不 vendor、不下载、不运行 Hermes-Agent。后续 R1 任务会通过 MCP server 和 Hermes skill 对接；本仓库只负责确定性 backend、registry、storage、API 和网站/API 组件。

## R1-03 Registry validation

R1-03 为四个 registry 文件加入本地验证：

- `source_registry/sources.yaml`
- `source_registry/podcasts.yaml`
- `source_registry/events.yaml`
- `source_registry/benchmark_registry.yaml`

运行：

```bash
make validate-registries
```

该命令只读取本地 YAML 并检查必填字段、URL 形状、ID 唯一性和基本类型；不会 fetch 外部来源，也不会调用任何外部 API。

Hermes cron / Daily Briefing integration 会在后续任务中处理。后续 cron prompt 必须是 self-contained，因为 Hermes cron 会启动新的 agent session，不继承当前聊天上下文。Gateway daemon 和 delivery channel 也保持为外部 Hermes runtime 能力。

不要把 `NousResearch/hermes-agent` 或 `nesquena/hermes-webui` clone/vendor/submodule 到本仓库。Hermes-Agent 后续单独安装和配置；Hermes-WebUI 是可选外部工具，不是本产品依赖。

## R1-04 Ingestion and registry API

R1-04 增加 Hermes-led ingestion 的第一组确定性 API。这些端点只读取 registry 或写入本地数据库状态；不会 fetch URL、不会调用外部 API、不会执行 collector。

Registry endpoints:

- `GET /registry`
- `GET /registry/sources`
- `GET /registry/sources/{source_id}`
- `GET /registry/podcasts`
- `GET /registry/events`
- `GET /registry/benchmarks`
- `GET /registry/due-sources`

Ingestion endpoints:

- `POST /ingestion/raw-items`
- `GET /ingestion/raw-items`
- `GET /ingestion/raw-items/seen`
- `POST /ingestion/source-runs`

这些端点为后续 Hermes HTTP/MCP wrappers 提供 registry lookup、due-source selection、raw item persistence、seen-check/history lookup 和 source run recording primitives。

## R1-05 Raw item memory and deterministic dedup

R1-05 为 Hermes 发现的 candidate items 增加后端记忆与离线去重。Backend 不 fetch URL、不读取网页、不做 triage；Hermes 仍负责 discovery、reading、judgment 和 digest。

Raw item ingestion now:

- canonicalizes URLs by lowercasing scheme/host, removing fragments, removing common tracking params such as `utm_*`, `fbclid`, and `gclid`, and preserving meaningful query params;
- computes a SHA-256 `content_hash` from normalized `content_text` when the caller does not provide one;
- stores `normalized_title`, `dedup_key`, `first_seen_at`, `last_seen_at`, `seen_count`, and `ingestion_status`;
- dedups deterministically by canonical URL, then exact content hash, then same source ID plus normalized title.

Updated ingestion endpoints:

- `POST /ingestion/raw-items` returns `{ item, is_duplicate, match_type }` and increments `seen_count` for repeats instead of creating uncontrolled duplicates.
- `GET /ingestion/raw-items/seen` accepts `url`, `content_hash`, `source_id`, and `title`, and returns match metadata.
- `GET /ingestion/raw-items/duplicates` returns deterministic duplicate candidates for Hermes review.
- `GET /ingestion/raw-items` supports filters for `canonical_url`, `dedup_key`, and `ingestion_status` in addition to the R1-04 filters.

## R1-06 Minimal MCP state tools

R1-06 exposes the smallest useful MCP-facing state surface for later Hermes-led daily runs. These tools are deterministic backend adapters only: they do not fetch external sources, run collectors, call LLMs, summarize, triage, or generate digests.

MCP tool functions now live in `frontier_ai_risk_observer.mcp.server`:

- `risk_registry_summary`
- `risk_registry_list_due_sources`
- `risk_registry_get_source`
- `risk_raw_item_seen_check`
- `risk_raw_item_store`
- `risk_raw_item_search`
- `risk_raw_item_duplicate_candidates`
- `risk_source_run_record`
- `risk_signal_store`
- `risk_signal_search`
- `risk_digest_store`
- `risk_digest_search`
- `risk_benchmark_observation_store`

`risk_signal_store` and `risk_digest_store` persist Hermes-generated outputs; they do not create or judge those outputs. Benchmark observation storage is exposed as a validated placeholder until the dedicated persistence service is added.

Local smoke check:

```bash
make mcp-smoke
```

The smoke command does not require Hermes-Agent. Registry checks run locally; DB-backed checks return a controlled unavailable response when no database is configured.

The optional Python MCP runtime is only needed when launching `python -m frontier_ai_risk_observer.mcp.server` as a real MCP server from Hermes. Hermes-Agent remains external, is not installed by this repo, and real Hermes integration begins in R1-07.

## R1-08 Automated Hermes Daily Dry Run

R1-08 runs the first real, non-production, Hermes-led daily dry run.

Key design decisions:

- **No Docker required.** Uses a local SQLite file-based dry-run database by default.
- **PostgreSQL remains the production target.** SQLite is only for local dry runs.
- **Hermes runs automatically.** `make r108-run-hermes` launches Hermes in one-shot mode.
- **Run artifacts saved** under `runs/r1_08/<timestamp>/`.
- **No production delivery.** No Feishu/WeCom/WeChat posting.

```bash
make db-init-dryrun      # Initialize local SQLite dry-run DB
make db-check            # Check DB readiness
make r108-dry-run-preflight  # Run all preflight checks
make r108-run-hermes     # Automatically launch Hermes dry run
make r108-inspect-state  # Inspect dry-run DB contents
```

The Hermes dry run:

1. Selects 3-5 real sources from the registry
2. Uses Hermes built-in web/search/research to inspect them
3. Stores candidate items via `risk_raw_item_store`
4. Records source runs via `risk_source_run_record`
5. Stores signals via `risk_signal_store` (if genuine signals found)
6. Writes a Chinese dry-run digest via `risk_digest_store` with status `dry_run`

## R1-09 Scrapling Source Reliability Helpers

R1-09 adds deterministic discovery helpers that pre-fetch candidate items from configured sources. Helpers are **collectors only** — they do NOT judge risk, call LLMs, store raw items, or triage. Hermes remains the judgment layer.

Key design decisions:

- **Scrapling uses `Adaptor` only** (HTML parser). The `Fetcher` class requires Playwright and is NOT used.
- **Network fetching uses httpx** (already a dependency).
- **No recursive crawling.** Scrapling helper extracts links from a single page.
- **fetch=False by default.** `risk_discovery_helper_preview` requires explicit opt-in for network access.

Helper types:

| Type | What it does |
|------|-------------|
| `scrapling_official_page` | Extracts links from an official page matching include/exclude patterns |
| `rss` | Parses RSS/Atom feeds |
| `podcast_rss` | Parses podcast RSS feeds |
| `arxiv_query` | Queries the arXiv API |
| `manual` | No automated helper; Hermes must browse manually |

New MCP tools:

- `risk_source_health_summary` — helper coverage, known issues, entries needing human review
- `risk_discovery_helper_preview` — preview candidates for a source (fetch=False by default)

```bash
make source-health          # Check source health and helper coverage
make preview-helpers        # List all sources with helpers
make r109-helper-preflight  # Validate registries + health + MCP + helpers
```

## R1-09B Helper-Assisted Hermes Dry Run

R1-09B runs a helper-assisted Hermes dry run that verifies Hermes can use the R1-09 helper layer end-to-end. Unlike R1-08 (manual browsing only), Hermes now starts with `risk_source_health_summary`, then uses `risk_discovery_helper_preview` to get candidate items before triage.

Key differences from R1-08:

- **Helper-assisted discovery** — Hermes calls `risk_discovery_helper_preview` for sources with configured helpers
- **R1-08 data preserved** — the dry-run DB keeps R1-08 data so seen-check and dedup can be tested
- **Helper usage reporting** — digest includes helper usefulness and source reliability issues
- **No DB reset by default** — keeping prior data enables duplicate detection testing

```bash
make r109b-dry-run-preflight  # Run all preflight checks
make r109b-run-hermes         # Launch helper-assisted Hermes dry run
make r109b-inspect-state      # Inspect dry-run DB contents
```

## R1-10 Stable Daily Report Run Modes

R1-10 adds two stable run modes for producing daily AI risk reports:

1. **`make daily-report`** — automated, non-interactive Hermes run with preflight
2. **`make hermes-interactive-daily`** — interactive session where a human can observe Hermes working

Both modes use the same daily report prompt (情报编辑室模式 / Intelligence Editorial Room style). The prompt defines editorial mission, audience, and selection criteria; tool calls are means not ordered steps.

Key design decisions:

- **No Docker, no PostgreSQL required.** Both modes use the local SQLite dry-run DB.
- **No external delivery.** Reports stored locally only.
- **Artifacts saved** under `runs/daily/<timestamp>/` and `runs/interactive/<timestamp>/`.
- **Hermes one-shot mode** (`hermes -z <prompt> --yolo`) used for both modes; interactive mode lets the human observe in the terminal.
- **30-minute timeout** for automated runs (Hermes may take 15-30 minutes for full research).
- **Improved timeout handling** — partial output captured even if Hermes times out.

```bash
make daily-report-preflight       # Preflight checks
make daily-report                 # Run automated daily report
make daily-report-inspect         # Inspect latest run and DB state
make hermes-interactive-preflight  # Interactive mode preflight
make hermes-interactive-daily      # Launch interactive session
make hermes-interactive-copy-prompt  # Print prompt without launching
```

Daily report prompt design (情报编辑室模式):

- **编辑使命**: 你是前沿 AI 风险情报编辑 (frontier AI risk intelligence editor)
- **受众**: AI safety researchers, governance/policy analysts, frontier lab safety teams
- **选稿标准**: must answer "what changed / why it affects risk judgment / what to watch next"
- **排除规则**: pure product launches, conference announcements without new statements, etc.
- **报告结构**: 一句话总览 → 信号 → 来源扫描摘要 → 需跟进
- **工具使用**: deterministic state tools + Hermes own capabilities, no fixed call order

## R1-11 Daily Report Quality Loop

R1-11 defines, tests, and enforces what a high-quality AI risk intelligence daily report means. The daily report must become a concise intelligence product — not a news digest, not a tool-call log, not a raw source summary.

Key components:

- **Quality rubric** (`docs/21_daily_report_quality_rubric.md`) — defines product mission, what counts as a signal, what to filter out, evaluation dimensions, required sections, style guide
- **Quality checklist** (`quality/daily_report_checklist.yaml`) — structured checks that scripts can read
- **Quality checker** (`scripts/check_daily_report_quality.py`) — deterministic checker with `--report`, `--latest`, `--json`, `--fail-under SCORE`, `--write-review PATH`
- **Updated prompts** — daily_report_prompt.md strengthened with signal definition, filter rules, candidate items section, uncertainty section; interactive prompt exposes editorial judgment

Signal quality principle: every true signal must answer:

1. What changed?
2. Why does this affect AI risk judgment?
3. What should we watch next?

```bash
make report-quality-check        # Check latest daily report quality
make report-quality-review       # Write Markdown review artifact
make daily-report-with-quality   # Run daily report then check quality
```

Quality score interpretation:

- 80-100%: intelligence briefing quality
- 60-79%: acceptable but needs improvement
- 40-59%: closer to news dump or incomplete
- 0-39%: tool log, raw dump, or failed run artifact

## R1-11B Model-Tiered Daily Report Pipeline

R1-11B adds model tiering to make daily report generation faster and more reliable, while preserving quality.

Three tiers:

| Tier | Responsible for |
|------|----------------|
| **Strong model (Hermes)** | Final risk signal judgment, report writing |
| **Small/fast model** | Candidate summaries, evidence excerpts, lightweight classification (advisory only) |
| **Deterministic Python** | Dedup, source health, quality checks, DB state |

Small model output is always advisory only — it never makes final risk judgments.

```bash
make model-tier-smoke       # Test candidate preprocess (no network/API keys)
make model-tier-smoke-live  # Test with live small model (if configured)
```

Configuration (optional, disabled by default):

```bash
AIRO_ENABLE_SMALL_MODEL=true
AIRO_SMALL_MODEL_NAME=glm4.5-air
AIRO_SMALL_MODEL_BASE_URL=https://your-endpoint/v1
AIRO_SMALL_MODEL_API_KEY_ENV=INF_API_KEY
```

See `docs/22_model_tiered_daily_report_pipeline.md` for full details.

## R1-11C Two-Phase Daily Report Finalization

R1-11C makes `make daily-report` reliable. Even if Hermes times out during the collection phase, the system produces a readable Chinese daily report.

Two phases:

| Phase | Purpose | Timeout |
|-------|---------|---------|
| **Phase A** (collection/research) | Hermes selects sources, collects evidence, stores items/signals | 30 min |
| **Phase B** (finalize/report) | Hermes writes report from DB state only (no browsing) | 10 min |

Phase B runs automatically if Phase A times out, exits non-zero, or doesn't produce a complete report. Phase B uses only local DB state — no web browsing, no URL fetching.

```bash
make daily-report                # Two-phase daily report
make daily-report-preflight      # Preflight checks
make daily-report-inspect        # Inspect latest run
make daily-report-with-quality   # Daily report + quality check
make daily-report-finalize       # Force finalize on latest run
make daily-report-debug          # Show latest run artifacts
```

`risk_signal_store` now accepts explicit `what_changed`, `why_it_matters`, `what_to_watch_next`, and `needs_review_reason` fields. Missing three-question reasoning automatically marks signals for human review.

See `docs/22_two_phase_daily_report_finalization.md` for full details.

## R1-12 Signal Evidence Persistence + Obsidian Intelligence Vault

R1-12 adds evidence/claim persistence and Obsidian vault export for human review and note-taking.

**Evidence persistence:**

Two new MCP tools allow Hermes to store and search claim-level evidence linked to signals or raw items:

- `risk_evidence_store` — store evidence with claim_text, evidence_url, evidence_excerpt, confidence, supports_signal
- `risk_evidence_search` — search evidence by signal_id, raw_item_id, source_id, claim_type

The existing `SourceClaim` model is extended with `signal_id`, `source_id`, `evidence_excerpt`, `evidence_title`, `supports_signal` fields.

**Obsidian Intelligence Vault:**

After a daily report, export DB state to a structured Obsidian vault with daily notes, signal notes, candidate notes, evidence notes, source notes, risk domain notes, entity notes, run notes, review queue, and index notes.

```bash
make obsidian-export            # Export DB state to Obsidian vault
make obsidian-export-dry-run    # Preview what would be exported
make obsidian-open-latest       # Export and open vault directory
make daily-report-and-obsidian  # Run daily report then export
```

Generated content is wrapped in `<!-- BEGIN_AUTO_GENERATED -->...<!-- END_AUTO_GENERATED -->` markers, preserving human content outside these blocks on re-export.

See `docs/23_obsidian_intelligence_vault.md` for full details.

## R1-13 Live Obsidian Research Logging

R1-13 adds live Obsidian vault writing during Hermes research runs, making the vault a real-time research workspace instead of only post-run export.

**Four new MCP tools:**

- `risk_live_run_start` — start a live research run, creating `08_Live_Runs/{run_id}/` with subdirectories
- `risk_live_event_append` — append research events (source selected, candidate found, evidence extracted, signal stored, etc.)
- `risk_live_note_upsert` — write or update source/candidate/evidence/signal notes in real time
- `risk_live_run_finalize` — end the run with a summary

**R1-13B enhancements:** stateless writer fix (MCP calls are stateless), COT violation detection, schema hardening (Literal types, field descriptions), export linking to live runs, Live Run Index, E2E validation target with requirements.

**R1-13C live vault UX repair:** daily report notes written to `00_Daily/` immediately during live runs; bidirectional links between all note types (daily, signals, evidence, candidates, sources); review queue (`90_Review_Queue/`) updated live; new `risk_live_daily_report_upsert` MCP tool (23 total); `risk_live_run_finalize` extended with `final_report_markdown` for immediate daily note write; `risk_digest_store` mirrors to Obsidian when live vault enabled; runner safety net preserves partial state on interruption. `make obsidian-export` is no longer needed for normal live UX — reserved for backfill, repair, and full consolidation only.

```bash
make daily-report-live-vault       # Run daily report with live vault logging
make daily-report-live-vault-e2e   # Full E2E with requirements validation
make live-vault-inspect            # Inspect live vault structure and content
make obsidian-open-live-run        # Open latest live run in Obsidian/Finder
```

Live logging is **disabled by default** — set `OBSIDIAN_LIVE_LOGGING_ENABLED=true` and `OBSIDIAN_VAULT_PATH` to enable. See `docs/24_live_obsidian_research_logging.md` for details.

## 第一阶段成功标准

第一阶段不要追求漂亮网站。成功标准是：

- 每日可稳定拉取核心来源；
- 能识别 5–10 条高质量风险信号；
- 每条信号有 evidence、primary source、claim type、置信度、why matters；
- 飞书/企业微信能收到中文日报；
- 网站能展示 digest、signals、sources health；
- 所有流程可通过 Hermes cron + MCP + skill 触发。


## Codex 启动建议

在仓库根目录运行 Codex 后，第一条指令建议使用：

```text
Read AGENTS.md, README.md, docs/00_codex_master_prompt.md, and docs/15_round1_codex_task_cards.md. Implement R1-01 only. Keep the diff small and run applicable validation commands.
```

完成 R1-01 后再继续 R1-02，以此类推。
