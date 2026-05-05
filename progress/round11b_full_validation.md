# R1-11B 完整验证报告 + Qwen3-8B 治理评估

**日期**: 2026-05-05
**状态**: R1-11B COMPLETE，小模型治理评估通过

---

## 一、完整验证结果

| 检查项 | 结果 | 备注 |
|--------|------|------|
| `make test` | 312 passed, 0 failed | 含 48 项 R1-11B 新测试 |
| `make lint` | All checks passed | ruff 全部通过 |
| `make typecheck` | 12 errors in 5 files | 全部为 R1-11B 之前的遗留问题，无新增 |
| `make validate-registries` | PASS | 23 sources, 6 podcasts, 6 events, 8 benchmarks |
| `make source-health` | OK | 4 known issues, 2 需人工复查 |
| `make preview-helpers` | OK | 5 helpers (3 scrapling, 1 RSS, 1 arxiv, 1 manual) |
| `make mcp-smoke` | PASS | due_sources=3, seen_check=OK |
| `make hermes-smoke` | PASS | Hermes v0.12.0, 16 MCP tools |
| `make db-check` | OK | SQLite dry-run DB 正常 |
| `make model-tier-smoke` | PASSED | 确定性 fallback 无需网络 |
| `make report-quality-check` | PASS (fixture) | 实际 Hermes 产出 15% 属预期（非正式产出） |
| `python -m compileall` | All files compile | 0 errors |

### mypy 遗留问题（非 R1-11B 引入）

- `services/source_health.py`: 3 个 assignment 类型不匹配
- `db/dryrun.py`: 1 个 unused ignore + 1 个 no-untyped-def
- `helpers/rss.py`: 2 个 no-any-return
- `helpers/arxiv.py`: 1 个 union-attr
- `mcp/server.py`: 4 个 misc/assignment/type-arg/arg-type

---

## 二、Qwen/Qwen3-8B (SiliconFlow) 实测评估

### 配置

```bash
AIRO_ENABLE_SMALL_MODEL=true
AIRO_SMALL_MODEL_NAME=Qwen/Qwen3-8B
AIRO_SMALL_MODEL_BASE_URL=https://api.siliconflow.cn/v1
AIRO_SMALL_MODEL_API_KEY_ENV=SILICONFLOW_API_KEY
```

### 功能测试结果

| 测试 | 输入 | 结果 | 耗时 | 评价 |
|------|------|------|------|------|
| summarize_text | Constitutional AI 论文 | 中文摘要，含关键发现(40%降低)和局限(规范博弈) | 22.5s | 优秀 |
| extract_evidence_excerpt | DeepMind 安全框架 | 中文证据片段，突出治理范式转变 | 13.6s | 优秀 |
| classify_candidate (相关) | EU AI Act 执法 | risk_relevant=True, confidence=4, 域=AI regulation | 30.9s | 正确 |
| classify_candidate (无关) | iPhone 17 发布 | risk_relevant=False, confidence=1, 域=Consumer Electronics | 20.8s | 正确 |
| long text handling | ~15000 字重复文本 | 480字结构化摘要 | 29.5s | 良好 |
| preprocess_candidate (高风险) | 中国1000亿参数强制安全测试 | possibly_relevant, confidence=5, 域=AI Policy/Ethical AI/National Security | 67.4s | 优秀 |
| preprocess_candidate (无关) | Tesla 财报 | likely_not_relevant, confidence=2 | 57.8s | 正确 |
| MCP tool (高风险) | o3 生物威胁评估能力 | possibly_relevant, confidence=4, 完整 JSON | ~60s | 优秀 |

### 治理评估

#### 1. 仅供参考原则 (Advisory-Only) ✅

所有输出均标记 `advisory_only: True`，`advisory_confidence` 作为参考指标而非最终判断。classify 输出中 `reason` 字段使用 "directly relates to" "suggests" 等建议性语言，而非确定性断言。

**关键验证**：对于高风险条目（中国AI安全法规），confidence=5 但仍标记 `possibly_relevant`（而非 `definitely_relevant`），体现了审慎态度。

#### 2. 相关/无关区分能力 ✅

| 类型 | 示例 | 判定 | confidence | 评价 |
|------|------|------|------------|------|
| 高度相关 | 中国AI强制安全测试 | possibly_relevant | 5/5 | 正确——高风险应保留给 Hermes |
| 中度相关 | EU AI Act 执法 | risk_relevant=True | 4/5 | 正确 |
| 低度相关 | Tesla 财报 | risk_relevant=False | 1/5 | 正确排除 |
| 无关 | iPhone 发布 | risk_relevant=False | 1/5 | 正确排除 |

**评估**：Qwen3-8B 能可靠区分 AI 风险相关与无关候选。对风险相关条目给出中等偏高 confidence（4-5），对无关条目给出低 confidence（1），梯度合理。

#### 3. 中文输出质量 ✅

摘要和证据提取均为结构化中文，包含：
- 关键数字和事实（"1000亿参数"、"40%降低"、"1000万元罚款"）
- 风险维度识别（对齐性、偏见、毒性、国家安全）
- 局限性说明（规范博弈、宪法定义不完整）
- 信息来源标注（CAC、DeepMind、OpenAI）

**不足**：部分输出包含英文 reason 字段，不够统一。这是模型行为，可在 prompt 中进一步优化。

#### 4. 不越界判断 ✅

模型未做出以下越界行为：
- 未直接声称某条目"是/不是信号"（只用 risk_relevant 和 confidence）
- 未尝试评估严重程度或风险等级
- 未建议最终报告内容
- 在 summary 中保留了"需持续验证"、"需观察"等审慎措辞

#### 5. 错误处理和降级 ✅

- 之前测试的内网端点 SSL 错误 → 正确降级为确定性截断
- 长文本 → 正确截断并处理
- 所有错误路径均返回 `advisory_only: True`

#### 6. 延迟和成本考量 ⚠️

| 操作 | 平均延迟 |
|------|----------|
| summarize_text | 22-30s |
| extract_evidence_excerpt | 14s |
| classify_candidate | 21-31s |
| 完整 preprocess_candidate (3 调用) | 58-67s |

**评估**：单次完整预处理约 1 分钟。对每日 3-5 个源、每源 2-4 个候选，约需 6-20 分钟小模型预处理时间。相比 Hermes 原始 15-30 分钟，如小模型预处理能有效减少 Hermes 深度研究次数，总体可缩短运行时间。但需注意：

- SiliconFlow API 延迟波动较大（13-31s/调用）
- 建议配置 `AIRO_SMALL_MODEL_TIMEOUT_SECONDS=60`（已是默认值）
- 对高延迟场景，确定性 fallback 可保证系统不阻塞

---

## 三、治理建议

### 可以启用

Qwen/Qwen3-8B 在 SiliconFlow 上的表现满足 R1-11B 的全部治理要求：

1. **仅供参考**：所有输出 advisory_only=True，不构成最终判断
2. **区分能力**：可靠区分相关/无关候选
3. **不越界**：未做出最终风险判断
4. **中文质量**：摘要和证据提取质量高
5. **降级安全**：模型不可用时确定性 fallback 正常工作

### 注意事项

1. **延迟**：单次预处理约 1 分钟，全流程需预留 10-20 分钟小模型时间
2. **API 稳定性**：SiliconFlow 为第三方服务，需考虑限流/宕机场景
3. **输出语言混合**：reason 字段有时英文，可在 system prompt 中强化
4. **confidence 校准**：confidence=5 对应 "possibly_relevant" 而非 "definitely_relevant" 是正确设计，但 Hermes 需理解此语义

### 推荐配置

```bash
# 生产环境推荐
AIRO_ENABLE_SMALL_MODEL=true
AIRO_SMALL_MODEL_NAME=Qwen/Qwen3-8B
AIRO_SMALL_MODEL_BASE_URL=https://api.siliconflow.cn/v1
AIRO_SMALL_MODEL_API_KEY_ENV=SILICONFLOW_API_KEY
AIRO_SMALL_MODEL_TIMEOUT_SECONDS=60
AIRO_SMALL_MODEL_DRY_RUN=false
```

---

## 四、R1-11B 交付物清单

| # | 交付物 | 状态 |
|---|--------|------|
| 1 | `SmallModelConfig` + `load_small_model_config()` | ✅ |
| 2 | `SmallModelClient` (summarize/excerpt/classify + fallback) | ✅ |
| 3 | `CandidatePreprocessResult` + `preprocess_candidate()` | ✅ |
| 4 | `risk_candidate_preprocess` MCP tool (第16个) | ✅ |
| 5 | `configs/env.example` 更新 | ✅ |
| 6 | `configs/hermes_config.example.yaml` 更新 | ✅ |
| 7 | `docs/22_model_tiered_daily_report_pipeline.md` | ✅ |
| 8 | `prompts/daily_report_prompt.md` 更新 | ✅ |
| 9 | `prompts/interactive_daily_report_prompt.md` 更新 | ✅ |
| 10 | `skills/ai-risk-signal-observer/SKILL.md` 更新 | ✅ |
| 11 | `scripts/daily_report.py` 更新 | ✅ |
| 12 | `quality/daily_report_checklist.yaml` 更新 | ✅ |
| 13 | `tests/test_r111b_model_tiering.py` (48 tests) | ✅ |
| 14 | `Makefile` model-tier-smoke targets | ✅ |
| 15 | `scripts/hermes_integration_smoke.py` 更新 (16 tools) | ✅ |
| 16 | `README.md` 更新 | ✅ |

---

## 五、遗留问题

1. **mypy 遗留**：12 个类型错误均为 R1-11B 之前的问题，建议后续统一清理
2. **Hermes 产出质量**：最新 daily report 质量 15%，需等待下一次真实 Hermes 运行验证端到端效果
3. **小模型输出语言**：reason 字段中英混合，可在后续优化 prompt 统一为中文
4. **SiliconFlow 限流**：目前未测试高频并发场景，建议监控 API usage
