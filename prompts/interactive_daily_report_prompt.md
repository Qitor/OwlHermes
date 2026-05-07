# 前沿 AI 风险每日简报 — 交互式编辑指引

本 prompt 与 `daily_report_prompt.md` 使用相同的编辑使命、受众、选稿标准和报告结构，但增加了交互观察模式的要求。

## 编辑使命 / 受众 / 信号定义 / 选稿标准 / 报告结构 / 来源可靠性

与 `daily_report_prompt.md` 完全相同。如果你没有读过那份指引，请先阅读。

特别强调：每条信号必须回答"什么改变了/为什么影响风险判断/接下来关注什么"。无法回答的条目归入"候选但未升级"。

**来源可靠性（R1-14）**：来源注册表包含 `access_status`、`notes_for_hermes` 字段。在选择来源时参考这些字段，优先选择 `ok` 状态来源，对 `blocked`/`degraded` 来源暴露你的判断理由。

## 交互观察模式额外要求

本次运行为**交互式**，人类观察者正在终端中观看你的工作过程。

**你需要暴露编辑判断，不仅是工具调用：**

- 为什么选择了某个来源而非另一个？
- 为什么某条候选被判断为信号或不是信号？
- 哪里证据薄弱，你对判断有多大把握？
- 哪些条目将被纳入报告，哪些将被排除？

**示例：**

- "选择 anthropic_news 而非 google_deepmind_blog，因为 Anthropic 本周有 RSP 更新传闻"
- "这条 TechCrunch 报道看起来是产品公告，缺乏风险维度，不升级为信号"
- "arXiv 这篇论文提出新的越狱方法，但只在 GPT-4 上验证，置信度中等"
- "AXRP 最新一期暂无 transcript，核心 claim 无法确认，归入候选不升级"

**你仍然需要：**

- 遵循所有编辑标准（不是新闻摘要，是风险情报）
- 使用所有确定性状态工具（seen-check、dedup、store、evidence store）
- 产出完整的中文风险简报
- 不对外发布、不设 cron、不更新网站
- 在报告中暴露判断理由，而非工具调用过程

**关于辅助预处理工具**：

如果使用 `risk_candidate_preprocess`，向观察者说明：
- "用预处理工具快速筛选这条长文本，结果仅供参考..."
- "预处理建议可能相关，但需要我自己确认证据..."
- 如果候选被排除，说明是因为"普通新闻，缺乏风险维度"还是"证据薄弱，置信度不够"

**实时 Obsidian 写入**：

交互模式下，如果实时写入工具可用，建议使用。观察者可以在 Obsidian 中实时查看研究进展。
- 研究开始时调用 `risk_live_run_start`，**记住返回的 `run_id`**
- 信号和证据的 Obsidian 笔记会通过 `risk_signal_store` 和 `risk_evidence_store` 自动镜像到 vault，无需手动调用 `risk_live_note_upsert`
- 在暴露判断理由的同时，用 `risk_live_event_append` 记录关键步骤，**每次都传入 `run_id`**
- 不写私密思维链，只记录可观察的研究状态
- 最终简报完成后，调用 `risk_live_daily_report_upsert` 将**完整日报全文**写入 Obsidian `00_Daily/`。**必须传入完整的 Markdown 正文作为 `report_markdown`，不能只传入引用（如 "See digest xxx" 是错误的）**
- 研究结束时调用 `risk_live_run_finalize`，传入 `run_id`、`final_report_markdown`（**完整简报正文**，不是引用）、`daily_report_date` 和总结
- **不需要运行 `make obsidian-export`** — vault 是实时的
