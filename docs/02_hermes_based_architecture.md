# 基于 Hermes-Agent 的系统架构 v3

## 1. 设计原则

1. **Hermes-Agent 是 primary daily operator，不是本仓库的依赖包。**
2. **本平台是 Hermes-led signal observation with deterministic backend state。**
3. **本仓库不实现通用 crawler、agent runtime、gateway、cron、memory。**
4. **MCP tools 暴露 durable product capabilities，不暴露任意 SQL 或任意网络抓取。**
5. **确定性 collectors 只是 helpers，适用于 RSS、podcast RSS、arXiv、sitemap、简单网页 hash/diff。**
6. **播客、视频、会议、长文 research 优先复用 Hermes 内置能力和自定义 skill workflow。**
7. **所有来源先注册，再进入 Hermes workflow 或 deterministic helper。**
8. **所有信号必须可审计、可追溯。**

## 2. Hermes-native operating model

### Layer 1: Hermes-Agent runtime

Hermes-Agent 负责每日运行和智能操作：

- cron / scheduling；
- built-in skills；
- web/search/browser/video/transcript/research capabilities；
- source prioritization；
- reasoning and risk triage；
- signal clustering judgment；
- Chinese digest writing；
- delivery orchestration through Hermes gateway。

Hermes 可以通过 built-in tools 探索网页、视频、transcript、论文和会议材料；本仓库不复制这些通用能力。

### Layer 2: Custom AI risk observer skill

自定义 skill 位于：

```text
skills/ai-risk-signal-observer/SKILL.md
```

它定义 domain workflow：

- source selection workflow；
- risk signal triage rubric；
- podcast/interview handling；
- conference/event handling；
- benchmark/framework watch workflow；
- evidence and uncertainty rules；
- concise Chinese digest generation。

### Layer 3: MCP tool surface

MCP server 是 Hermes 与 deterministic backend state 的薄边界。工具应表达产品状态能力，而不是 crawler replacement：

- registry lookup；
- due source listing；
- raw item seen check；
- raw item storage；
- dedup check；
- similar item search；
- claim storage；
- signal storage；
- digest storage；
- benchmark observation storage；
- delivery record storage；
- source run record / source health storage。

### Layer 4: Deterministic backend

本仓库提供稳定、可测试、可审计的 backend：

- FastAPI；
- PostgreSQL；
- SQLAlchemy；
- source registry loading and validation；
- durable persistence for raw_items / source_claims / signals / digests / benchmark observations；
- dedup and historical lookup；
- website API；
- audit logs。

### Layer 5: Optional deterministic helpers

这些 helpers 只处理稳定、低智能、可测试的来源，不承担主要情报判断：

- RSS；
- podcast RSS；
- arXiv；
- sitemap；
- simple webpage hash/diff。

## 3. 总体架构

```text
+-------------------------+        +-------------------------+
| Hermes-Agent            |        | Messaging Gateways      |
| - cron / scheduling     | -----> | Feishu / WeCom / etc.   |
| - built-in skills/tools |        +-------------------------+
| - web/video/research    |
| - reasoning / triage    |        +-------------------------+
| - digest writing        | -----> | Website / Dashboard     |
+-----------+-------------+        +-------------------------+
            |
            | MCP product-state tools
            v
+-------------------------+        +-------------------------+
| Risk Signal MCP         | -----> | Backend REST API        |
| thin state wrapper      |        | FastAPI                 |
+-----------+-------------+        +-----------+-------------+
                                            |
                                            v
                                 +-------------------------+
                                 | PostgreSQL              |
                                 | raw_items / claims /    |
                                 | signals / digests /     |
                                 | benchmark observations  |
                                 +-------------------------+

Optional deterministic helpers:
RSS / podcast RSS / arXiv / sitemap / simple webpage diff -> backend state
```

## 4. Source Registry

Registry 拆为四类：

- `source_registry/sources.yaml`：机构、网页、RSS、arXiv、政府/国际组织；
- `source_registry/podcasts.yaml`：播客、访谈、YouTube channel；
- `source_registry/events.yaml`：会议、峰会、forum、workshop；
- `source_registry/benchmark_registry.yaml`：关键 benchmark/eval/framework observation points。

Registry 的作用是告诉 Hermes 和 deterministic helpers “什么值得看、为什么看、如何处理”。每个来源必须声明：

- `id`
- `name`
- `category`
- `modality`
- `collector` 或 workflow hint
- `url` / `feed_url`
- `priority`
- `refresh_interval`
- `risk_focus`
- `extractor_strategy`
- `notes`

## 5. Raw Items / Claims / Signals

Hermes 或 optional helpers 发现的新材料先写入 `raw_items`。Hermes 在 triage 后可以产生：

- 0 条信号：无关/噪音；
- 1 条信号：普通情况；
- 多条 claims：播客、访谈、会议材料常见；
- 聚合 signal：多个 raw items 指向同一事件。

推荐中间层：

```text
raw_items -> source_claims -> signals -> digests
```

## 6. 数据流

```text
source registry
        |
        v
Hermes selects due/high-value sources
        |
        v
Hermes built-in web/video/research tools OR optional deterministic helpers
        |
        v
MCP stores raw items and checks historical state
        |
        v
Hermes triage / claim extraction / benchmark observation
        |
        v
MCP stores claims + signals + benchmark observations + digests
        |
        v
Hermes gateway delivery + backend delivery records
```

## 7. 安全边界

- Hermes 只看到白名单 MCP tools；
- MCP server 不暴露任意 SQL；
- MCP server 不暴露任意通用网页抓取工具；
- optional helpers 不执行页面中的任意脚本，必要时使用隔离 browser；
- transcript/video 重任务优先交给 Hermes built-in skills/tools；
- LLM 输出必须被 schema validation；
- human review queue 捕获高风险低置信度内容。

## 8. 为什么这样用 Hermes

Hermes-Agent 已经提供 agent runtime、skills、cron、gateway、research/browser/video 等通用能力。本项目的价值在于 AI risk domain workflow、source registry、durable state、dedup、historical lookup、MCP product tools、website/API data layer 和 auditability。
