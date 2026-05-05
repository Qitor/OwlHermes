# Codex Master Prompt — Hermes AI Risk Signal Observatory v3

你现在要用 **Codex** 实现一个基于 **Hermes-Agent** 的前沿 AI 风险信号观测平台。请严格遵循本文档包，不要把它做成泛 AI 新闻聚合器，也不要把 Hermes-Agent 替换成自研 agent runtime。

## 0. 产品目标

构建一个每日运行的 Hermes-led AI 风险情报系统。Hermes-Agent 作为 primary daily operator，使用内置 web/search/browser/video/transcript/research 能力和本项目的自定义 skill，从以下来源中识别真正重要的风险信号：

- frontier AI labs：OpenAI、Anthropic、Google DeepMind 等；
- eval / safety labs：METR、Apollo Research、UK AISI、NIST CAISI 等；
- policy / governance labs：GovAI、Safe AI Forum、IDAIS、FAR.AI 相关活动等；
- 政府与国际组织：EU AI Office、GOV.UK、OECD、AI summit 系列、International AI Safety Report；
- 论文：arXiv AI safety / evals / agents / cyber / bio / deception / governance；
- 播客与访谈：Dwarkesh Podcast、80,000 Hours、AXRP、Cognitive Revolution、Latent Space 等；
- 会议和论坛：Safe AI Forum / IDAIS、[un]prompted、AI Safety Summit / Seoul / Paris / India、相关 ML security / evals events；
- 权威新闻：TechCrunch AI、Reuters、The Verge、Wired、TIME 等作为辅助发现源。

系统最终输出：

1. 每日中文风险信号日报；
2. 网站信号卡和历史时间线；
3. benchmark/eval delta；
4. framework diff；
5. podcast/interview/event intelligence；
6. 飞书/企业微信/微信兼容渠道推送。

## 1. 必须基于 Hermes-Agent

Hermes-Agent 是产品运行时基础设施，Codex 是开发实现工具。不要混淆两者。

Hermes-Agent 应承担：

- MCP：连接自建 risk signal backend；
- skills：固化风险信号分析流程；
- cron：每日定时运行；
- built-in tools/skills：web/search/browser/video/transcript/research exploration；
- source prioritization、reasoning、risk triage；
- gateway：推送到 Feishu / WeCom / WeChat-compatible channel；
- API Server：后续可作为网站问答接口；
- memory/skills：记录 analyst preference 和日报风格。

不要重新实现 agent runtime、gateway、cron、memory，也不要把本仓库做成通用 crawler。

## 2. Codex 执行方式

Codex 应从仓库根目录读取 `AGENTS.md`，再按本文档包执行。每一轮任务都应该以小 PR/小 diff 完成，并在任务结束时输出：

- 修改了哪些文件；
- 如何运行；
- 运行了哪些测试；
- 还有哪些技术债；
- 下一步建议做什么。

不要一次性重写整个项目。优先完成可运行闭环，再扩展来源。

## 3. 架构边界

### 自建 backend

负责：

- registry loading；
- registry validation；
- durable raw item / claim / signal / digest / benchmark observation storage；
- deterministic dedup；
- historical lookup / similar item search；
- Postgres persistence；
- REST API；
- MCP server thin wrapper；
- website API；
- source run records、source health、audit logs；
- optional deterministic helpers for RSS、podcast RSS、arXiv、sitemap、simple webpage hash/diff。

### Hermes-Agent

负责：

- 使用内置 skills/tools 做 web/search/browser/video/transcript/research exploration；
- 调用 MCP tools 读取 registry、检查历史状态、写入 durable state；
- 对 raw items / newly discovered evidence 做 triage；
- 将 raw items 聚合为 signals；
- 生成中文 digest；
- 标记 needs_human_review；
- 推送日报；
- 回答“为什么重要/接下来关注什么”。

### Codex

负责实现代码、测试、配置模板、文档更新和本地验证；不负责长期运行调度。长期运行由 Hermes cron + backend service + deployment 环境承担。

## 4. Round 1 开工任务

请先实现垂直闭环 MVP，不要扩展到所有来源。

### Round 1 目标

实现以下能力：

1. 后端项目结构；
2. Postgres schema；
3. source registry loader；
4. ingestion interface + registry service API；
5. raw item storage + dedup service；
6. minimal MCP tools for registry/raw_items/signals/digests；
7. dedup：URL canonicalization + content hash + title similarity；
8. REST API；
9. MCP server 能连接 Hermes；
10. Hermes skill 能执行 daily workflow；
11. 生成一篇真实 digest；
12. source health 页面/API。

### Round 1 核心来源

必须先支持这些来源：

- METR blog/evaluations；
- Apollo Research blog；
- Anthropic news；
- OpenAI news；
- Google DeepMind blog；
- UK AISI research/blog；
- NIST CAISI；
- GovAI research；
- Safe AI Forum updates/research；
- IDAIS site/statements；
- arXiv AI safety query；
- TechCrunch AI feed；
- Dwarkesh Podcast feed/page；
- AXRP feed/transcripts；
- [un]prompted agenda/materials page。

播客、视频、会议材料优先让 Hermes 使用内置 transcript/video/research 能力探索；后端只负责存储 Hermes 发现的 episodes/talks/transcripts/claims/signals。RSS、arXiv、sitemap、简单网页 diff 等确定性 helpers 放在后续任务中补齐。

## 5. 信号卡硬性要求

每条 signal 必须有：

- `title_zh`
- `summary_zh`
- `what_changed`
- `why_it_matters`
- `what_to_watch_next`
- `signal_type`
- `risk_domains`
- `entities`
- `source_ids`
- `primary_source_url`
- `evidence_level`
- `claim_type`
- `severity`
- `confidence`
- `time_sensitivity`
- `priority_score`
- `needs_human_review`

如果缺少 primary source 或 evidence，必须降权或进入人工复核。

## 6. 播客/访谈特殊规则

播客和访谈不能按普通新闻处理。重点抽取：

- frontier lab 高管或研究员的新表述；
- safety policy / eval / deployment threshold 的变化；
- 对模型能力时间线的预测变化；
- 对安全框架、监管、国际合作的新立场；
- 研究人员透露的新 benchmark、实验、失败模式、部署经验；
- 与官方文件不一致或补充官方文件的表述。

一集 podcast 不等于一条 signal；一集 podcast 可产生 0–N 条 claims，再聚合为 signals。

## 7. 会议/论坛特殊规则

会议、峰会、workshop 的重点不是“某会议举办了”，而是：

- 是否出现新共识/联合声明；
- 是否有新安全承诺、red lines、policy guide；
- 是否出现跨国/跨实验室协作；
- 是否发布新 benchmark/eval/framework；
- 是否有 speaker agenda 暗示重要技术/安全方向变化；
- 是否有 slides/transcripts/videos 可抽取新 claims。

## 8. Codex 完成定义

Round 1 完成时，请交付：

- 可运行 README；
- `.env.example`；
- DB migration；
- collector tests；
- API tests；
- MCP smoke test；
- Hermes config example；
- sample digest；
- source health report；
- 技术债列表。

每次 Codex 任务完成前至少运行：

```bash
python -m pytest
python -m compileall .
python scripts/validate_registries.py
```

如果某条命令暂时无法运行，必须在总结中说明原因，并给出最小修复路径。
