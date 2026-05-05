# 实施计划 v3

## 总体策略

先做 “Hermes-led signal observation with deterministic backend state”。不要一开始追求 50+ sources，也不要把本仓库做成大型 crawler。Hermes-Agent 是 primary daily operator；本仓库提供 registry、storage、dedup、MCP tools、API 和可选 deterministic helpers。

## Round 1 — Hermes-native vertical MVP

### 目标

跑通：

```text
Hermes source selection / research
  -> MCP-backed raw item storage
  -> dedup and historical lookup
  -> Hermes triage / claims / signals
  -> MCP persistence
  -> Chinese digest
  -> delivery record
  -> minimal website/API view
```

### 必做任务

1. R1-01 repository scaffold。
2. R1-02 database foundation。
3. R1-03 registry validation。
4. R1-04 ingestion interface and registry service API。
5. R1-05 raw item storage and dedup service。
6. R1-06 minimal MCP tools for registry/raw_items/signals/digests。
7. R1-07 custom Hermes skill integration smoke test。
8. R1-08 Hermes-led daily dry run。
9. R1-09 optional deterministic helpers for RSS、podcast RSS、arXiv、sitemap、simple webpage diff。
10. R1-10 minimal website/API view。
11. R1-11 delivery dry run。
12. R1-12 end-to-end review and Round 2 plan。

### Round 1 来源

优先让 Hermes workflow 覆盖这些高价值来源，并把结果通过 MCP 写入后端：

- METR；
- Apollo Research；
- Anthropic；
- OpenAI；
- Google DeepMind；
- UK AISI；
- NIST CAISI；
- GovAI；
- Safe AI Forum；
- IDAIS；
- arXiv；
- TechCrunch AI；
- AXRP；
- Dwarkesh Podcast；
- [un]prompted。

RSS、podcast RSS、arXiv、sitemap、simple webpage diff 可以在 R1-09 作为 helper 加速稳定来源，但不是主要 intelligence layer。

### 验收

- Hermes-led daily dry run 可以读取 registry、探索来源、检查历史状态并存储 raw items；
- DB 有 raw_items、source_claims、signals、digests；
- 至少生成 5 条合格 signals；
- 每条 signal 有 primary_source_url 和 why_it_matters；
- digest 可通过 Hermes gateway dry run 推送或模拟；
- source run / health / audit state 可见。

## Round 2 — Podcast / Event Intelligence

### 目标

让播客/访谈/会议成为可靠信号来源，同时继续优先复用 Hermes built-in video/transcript/research skills。

### 任务

1. 明确 Hermes transcript/video workflow 和后端 storage contract。
2. 为 podcast episode 建 claim persistence pipeline。
3. 为 event page 建 agenda/material evidence storage。
4. 支持 videos/slides/materials registry metadata。
5. 支持 long-form claim evidence：timestamp、speaker、quote snippet、url。
6. 建立 claim-level evidence 和 uncertainty rules。
7. 更新 digest 模板，加入“播客/访谈”和“会议/论坛”。

### 验收

- 一集 AXRP 或 Dwarkesh episode 可由 Hermes 抽取 0–N 条 claims 并通过 MCP 存储；
- 一个 event page 更新可触发 agenda/materials raw item；
- podcast claims 不会无证据地升级为 high-confidence signal。

## Round 3 — Benchmark / Framework Delta

### 目标

形成区别于普通新闻聚合器的核心壁垒。

### 任务

1. 完善 `benchmark_registry.yaml` validation。
2. 支持 benchmark observations storage/search。
3. 支持 Hermes-led framework watch：RSP、Preparedness、FSF、AISI methods、IDAIS policy guide。
4. 支持 model/eval relation。
5. 支持 threshold crossing detection。
6. 网站增加 benchmark timeline。

### 验收

- 能展示某 benchmark 最近变化；
- 能展示某 framework 页面的观察历史；
- 日报能把 benchmark delta 独立成栏目。

## Round 4 — Quality / Calibration

### 目标

让风险评分稳定、日报可信。

### 任务

1. 建 30 条历史 calibration set。
2. 为 severity/confidence/time_sensitivity 写 examples。
3. 加 prompt regression tests。
4. 加 human review queue。
5. 加 false positive / false negative 复盘机制。

## Round 5 — Productization

### 目标

让平台可持续运行。

### 任务

1. 管理后台；
2. 人工编辑/确认；
3. 邮件/订阅；
4. 网站搜索；
5. weekly/monthly report；
6. 用户反馈闭环。
