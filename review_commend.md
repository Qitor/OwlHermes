# Hermes-Agent 核心架构评估

评估日期：2026-05-04  
评估范围：Hermes 官方 guides、当前仓库文档、后端/MCP/collector/skill 代码骨架。

## 结论

当前整体架构**基本符合**最初产品设计：它仍然是一个以 Hermes-Agent 为核心的智能风险信号采集器，而不是自研 agent runtime 或泛 AI 新闻聚合器。

更准确地说，当前设计是：

> Hermes-led signal observation with deterministic backend state

也就是：

- Hermes 负责发现、阅读、判断、总结、推送；
- backend 负责 registry、状态、去重、历史、审计、网站/API 数据；
- MCP 负责把 backend 的确定性产品能力暴露给 Hermes；
- optional collectors 只作为 RSS、podcast RSS、arXiv、sitemap、简单网页 hash/diff 等低智能 helper。

目前没有发现已经实质性偏离最初产品定位的实现。但有一个需要提前控制的风险：`collectors/` 和 `workers/daily_run.py` 后续如果继续扩张，容易从 helper 变成 backend-led crawler/daily workflow，从而削弱 Hermes 作为 primary operator 的地位。

## Hermes 官方指南带来的架构判断

Hermes guides 支持当前分工。

1. Daily briefing bot guide 展示的核心模式是：cron 定时启动 Hermes fresh session，Hermes 搜索/阅读/总结，再通过 messaging delivery 推送。这与本项目“每日 AI 风险信号日报”的工作流高度匹配。  
   参考：https://hermes-agent.nousresearch.com/docs/guides/daily-briefing-bot/

2. Cron guides 明确说明 cron job 是 fresh agent session，prompt 必须 self-contained；同时 cron 可以附加 skills。这说明本项目不应把 daily workflow 写死进 Python backend，而应把稳定 workflow 放进 Hermes skill + self-contained cron prompt。  
   参考：https://hermes-agent.nousresearch.com/docs/user-guide/features/cron  
   参考：https://hermes-agent.nousresearch.com/docs/developer-guide/cron-internals

3. Automate with cron guide 把 script 定位为机械数据收集/diff，把 agent 定位为判断“变化是否有意义”。这正好对应本项目的边界：backend/helper 可以做 fetch/diff/hash，Hermes 做是否构成风险信号的判断。  
   参考：https://hermes-agent.nousresearch.com/docs/guides/automate-with-cron/

4. MCP guide 把 MCP 定位为连接外部工具/内部 API 的 clean RPC layer，并强调最小可用 tool surface、工具过滤和安全暴露。这与当前 `mcp_server_scaffold/` 和 `configs/hermes_config.example.yaml` 的薄 MCP wrapper 方向一致。  
   参考：https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp  
   参考：https://hermes-agent.nousresearch.com/docs/guides/use-mcp-with-hermes/

5. Skills guide 支持把领域工作流封装成 `SKILL.md`，再由 cron 或会话加载。这与 `skills/ai-risk-signal-observer/SKILL.md` 的定位一致：它应该是 Hermes runtime 的领域流程说明，而不是 Codex skill 或 backend 逻辑。  
   参考：https://hermes-agent.nousresearch.com/docs/user-guide/features/skills/

## 当前架构符合点

### 1. 产品定位没有变成新闻聚合器

`README.md`、`docs/01_product_requirements.md`、`docs/02_hermes_based_architecture.md` 都反复强调核心单元是 `risk signal`，必须回答：

- `what_changed`
- `why_it_matters`
- `what_to_watch_next`

这与最初“只保留会改变风险判断的高质量信号”的设计一致。

### 2. Hermes 与 backend 的边界清晰

当前文档把 Hermes 放在 Layer 1，负责：

- cron / scheduling；
- web/search/browser/video/transcript/research；
- source prioritization；
- reasoning / triage；
- digest writing；
- gateway delivery。

backend 则负责：

- registry loading / validation；
- raw_items / claims / signals / digests / benchmark observations；
- dedup / historical lookup；
- source health / audit logs；
- REST API / website API。

这正好对应“智能判断在 Hermes，确定性状态在 backend”。

### 3. MCP surface 当前方向正确

`frontier_ai_risk_observer/mcp/server.py` 暴露的是产品状态工具，例如：

- `risk_registry_list_due_sources`
- `risk_raw_item_seen_check`
- `risk_raw_item_store`
- `risk_claim_store`
- `risk_signal_store`
- `risk_digest_store`
- `risk_benchmark_observation_store`
- `risk_source_run_record`

这些不是通用 crawler 工具，也没有暴露任意 SQL 或任意网络抓取能力。这个方向符合 Hermes MCP guide 中“最小有用 surface”的安全模型。

### 4. 数据模型支持审计与历史追踪

`schemas/schema.sql` 已经覆盖：

- `sources`
- `source_runs`
- `raw_items`
- `source_claims`
- `signals`
- `benchmark_observations`
- `digests`
- `delivery_events`
- `audit_logs`

这说明 backend 正在承担 durable state、history、audit、website data layer，而不是试图承担 agent reasoning。

### 5. optional collectors 目前没有越界

`frontier_ai_risk_observer/collectors/rss.py` 和 `webpage.py` 目前只是 placeholder，并且注释明确说：

- RSS helper 只覆盖稳定 feed；
- webpage helper 只做 future stable sitemap/hash/diff；
- judgment-heavy web research 交给 Hermes。

这符合原始边界。

## 当前偏离风险

### 风险 1：`workers/daily_run.py` 可能变成 backend cron

当前 `workers/daily_run.py` 只是 placeholder，没有问题。但如果后续在这里实现完整 daily workflow，例如 source selection、抓取、triage、digest、delivery，就会偏离 Hermes-led design。

建议：

- `workers/daily_run.py` 只能用于本地 dry-run、sample replay、helper orchestration；
- production daily workflow 应由 Hermes cron + Hermes skill + MCP tools 驱动；
- 不要把 digest generation 和 triage 判断写成 Python 主流程。

### 风险 2：R1-09 deterministic helpers 容易膨胀成 crawler

R1-09 包含 RSS、podcast RSS、arXiv、sitemap、simple webpage hash/diff。这个范围合理，但实现时需要严控：

- 不做通用网页 crawler；
- 不做复杂 browser automation pipeline；
- 不做 podcast/audio transcript pipeline；
- 不做会议视频解析；
- 不做跨站点 discovery graph。

helper 的输出应只是 raw item / changed page / feed item / hash diff，再由 Hermes 判断是否重要。

### 风险 3：MCP tool 命名与 Hermes 注册名需要对齐

Hermes MCP docs 说明 MCP tools 会以 `mcp_<server_name>_<tool_name>` 注册。当前 skill 里直接写 `risk_registry_list_due_sources` 等工具名，在实际 Hermes 中可能需要确认 agent 是否能自然匹配，或在 prompt/config 中明确“这些工具来自 ai_risk_signal MCP server，注册名可能带 `mcp_ai_risk_signal_` 前缀”。

建议在 R1-06/R1-07 smoke test 中验证真实 Hermes 工具名，并同步更新：

- `skills/ai-risk-signal-observer/SKILL.md`
- `configs/hermes_config.example.yaml`
- `prompts/daily_signal_collection_prompt.md`

### 风险 4：缺少端到端 Hermes dry run

目前仓库已有 backend/API/schema/MCP placeholder，但还没有真正证明：

```text
Hermes cron -> skill -> MCP due sources -> Hermes research -> raw item store -> signal store -> digest store -> gateway delivery
```

这不是架构偏离，但会让边界停留在文档层面。R1-07 和 R1-08 应优先完成。

## 是否偏离最初产品设计

总体判断：**没有明显偏离。**

当前实现仍然围绕最初目标：

- 不是泛 AI 新闻聚合器；
- 不 vendor Hermes-Agent；
- 不重建 agent runtime；
- 不把 backend 做成智能 crawler；
- source 必须先进 registry；
- 播客/访谈/会议材料被视为一级来源；
- SAIF 已按 Safe AI Forum 处理；
- MVP 优先垂直闭环而不是扩大来源。

但是，产品还没有完全进入“以 Hermes 为核心的可运行智能信号采集器”状态，因为 MCP server、Hermes skill integration、daily dry run、delivery record 仍处于早期。当前更像是一个**方向正确的 Hermes-ready backend scaffold**。

## 建议的架构收紧原则

后续实现建议坚持以下规则：

1. Hermes-first：任何涉及“是否重要、为什么重要、怎么总结、是否推送”的逻辑，都默认放在 Hermes skill/prompt 中。
2. Backend-state-only：backend 只做 registry、storage、dedup、history、audit、API、website data。
3. MCP-thin-wrapper：MCP 只包装 backend product-state capability，不暴露通用 fetch、browser、SQL、shell。
4. Helper-limited：deterministic helpers 只能处理稳定、低智能、可测试的输入，并写回同一 ingestion interface。
5. Self-contained cron：Hermes daily cron prompt 必须包含完整任务目标、source selection 规则、输出格式、MCP 使用说明和 delivery 要求。
6. Evidence-first：没有 primary source 或证据不足的 signal 必须降权或进入 `needs_human_review`。
7. Registry-gated：新增来源只能通过 registry 进入，不允许散落在代码里。

## 下一步优先级

建议下一步不要扩展 source 数量，而是完成 Hermes vertical MVP：

1. R1-06：实现最小 MCP tools，并提供 `scripts/smoke_mcp_server.py`。
2. R1-07：验证 Hermes 能加载 `skills/ai-risk-signal-observer/SKILL.md` 和 MCP tool surface。
3. R1-08：做一次 sample daily dry run，证明 raw item -> claim/signal -> digest 的状态写入链路。
4. R1-11：记录 Hermes gateway delivery result，不在 backend 自建推送 runtime。

一句话总结：

> 当前架构没有跑偏；它是正确的 Hermes-led observatory 雏形。接下来最重要的不是写更多 collectors，而是把 Hermes cron + skill + MCP + backend state 的垂直闭环跑通。
