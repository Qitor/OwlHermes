# 产品需求文档 PRD v2

## 1. 背景

前沿 AI 风险信号分散在实验室公告、system card、第三方评估、政府政策、技术论文、研究博客、新闻报道、播客访谈、会议议程、峰会声明和 workshop materials 中。单靠人工订阅容易漏掉关键变化，也很难形成一致、可追溯的历史知识库。

本产品要构建一个 Hermes-led “每日 AI 风险信号观测平台”，不是简单聚合新闻，也不是独立 crawler，而是持续回答：

> 今天有什么新信息会改变我们对前沿 AI 风险、能力边界、评估科学、监管走向和国际共识的判断？

## 2. 用户

### 主要用户

- AI safety / AI governance 研究人员；
- 政策研究、战略分析、智库团队；
- 需要追踪 frontier model safety 的机构；
- 关注 OpenAI / Anthropic / DeepMind / METR / AISI 等来源的中文读者；
- 需要每日/每周产出高质量风险简报的自媒体、研究组织或网站。

### 关键使用场景

1. 每天早上收到中文 AI 风险信号日报；
2. 在网站查看标准化 signal cards；
3. 按风险域筛选：autonomy、cyber、bio、deception、eval_integrity、policy、governance、agent_security 等；
4. 追踪某个 benchmark、模型、框架、机构或会议的变化；
5. 查看播客/访谈中的关键 claims；
6. 查看会议/峰会/论坛带来的共识变化；
7. 每周生成趋势报告；
8. 对某条信号发起深挖。

## 3. 产品定位

不要做成“AI 新闻列表”。

本产品的核心单元是 `risk signal`，它必须回答：

1. `what_changed`：相比此前，新事实是什么？
2. `why_it_matters`：为什么这会影响风险判断？
3. `what_to_watch_next`：接下来应该关注什么？

## 4. MVP 范围

### Round 1 包含

- 12–18 个高质量核心来源；
- Hermes-Agent 每日定时运行 domain workflow；
- Hermes built-in web/search/browser/video/transcript/research 能力用于 discovery 和 exploration；
- MCP-backed durable storage for raw items, claims, signals, digests；
- 可选确定性 helpers for RSS、podcast RSS、arXiv、sitemap、simple webpage diff；
- 信号 triage；
- 数据库存储；
- 中文日报；
- 飞书或企业微信推送；
- 极简网站展示；
- Hermes-Agent 作为核心 orchestrator。

### Round 1 不包含

- 全量音频自动转写；
- 所有会议视频解析；
- 大规模知识图谱；
- 多用户权限系统；
- 付费订阅；
- 自动事实核查全流程；
- 对所有国家政府网站的深度爬取。

## 5. 数据源类型

| 类型 | 示例 | MVP 处理方式 |
|---|---|---|
| `rss` | TechCrunch AI | optional deterministic helper + Hermes triage |
| `web_index` | METR blog, Anthropic news | Hermes exploration first; optional sitemap/simple diff helper |
| `manual_url` | framework pages | optional hash diff helper + Hermes interpretation |
| `arxiv` | AI safety query | optional deterministic helper + Hermes research workflow |
| `podcast_feed` | AXRP, Dwarkesh | Hermes transcript/video/research skills preferred; backend stores discoveries |
| `youtube_channel` | interviews, conference talks | Hermes video/transcript skills preferred; backend stores evidence |
| `event_page` | [un]prompted, IDAIS | Hermes research/browser workflow preferred; optional simple agenda diff helper |
| `summit_statement` | Seoul Declaration, Paris Summit | official statement monitoring |
| `benchmark_registry` | METR/AISI/Apollo/system card evals | manual registry + observation extraction |

## 6. 信号类型

- `policy_update`：政策、监管、政府公告、国际合作；
- `benchmark_change`：eval/benchmark 结果变化、新 benchmark、新能力阈值；
- `model_release_risk`：新模型发布与 system card 风险；
- `risk_framework`：RSP、Preparedness、FSF、SAIF/IDAIS policy guide、AISI 方法论等；
- `technical_risk`：cyber、bio、autonomy、deception、alignment、agent safety；
- `incident_or_misuse`：安全事件、滥用、模型越狱、agent hijacking；
- `consensus_signal`：多方共识、标准、联合声明；
- `lab_governance`：实验室治理结构、安全委员会、审计；
- `research_trend`：arXiv/论文趋势；
- `podcast_claim`：访谈中的新 claim、预测、立场或技术细节；
- `event_signal`：会议议程、talk、panel、声明、材料中的新信号；
- `meta_signal`：评估方法、监测能力、科学方法变化。

## 7. 输出形态

### 网站信号卡

每条信号包含：

- 标题；
- 来源；
- 日期；
- 中文摘要；
- `what_changed`；
- `why_it_matters`；
- `what_to_watch_next`；
- 风险域；
- 信号类型；
- 严重性；
- 置信度；
- 时效性；
- evidence level；
- claim type；
- 原文链接；
- 相关实体；
- 推荐行动；
- 是否需要人工复核。

### 日报

结构：

1. 今日一句话总览；
2. Top Signals；
3. 政策/治理；
4. Benchmark 与评估；
5. 前沿实验室与模型发布；
6. 新型风险；
7. 风险框架与标准；
8. 播客/访谈重点；
9. 会议/论坛/峰会重点；
10. arXiv/研究趋势；
11. 需进一步深挖；
12. 来源健康状态简报。

## 8. 关键指标

| 指标 | MVP 目标 |
|---|---:|
| 每日正常运行率 | ≥ 95% |
| 每日高质量信号数 | 5–10 |
| 重复信号比例 | < 20% |
| 每条信号可追溯来源 | 100% |
| primary source 覆盖率 | ≥ 80% |
| needs_human_review 标记准确性 | 人工抽检逐步提升 |
| 每日简报生成时间 | < 30 分钟 |
| 来源健康状态可见性 | 100% |

## 9. 非功能要求

- 可解释：每条信号必须可回溯原始来源；
- 安全：所有密钥放 `.env`，不要写入仓库；
- 可扩展：新增来源只改 registry；
- 可恢复：采集失败不会中断全局日报；
- 可审计：保存每次采集、triage、推送日志；
- 可降级：Hermes 不可用时，采集和网站仍可运行；只是缺少智能总结；
- 半自动优先：早期允许人工复核，不追求全自动幻觉式判断。
