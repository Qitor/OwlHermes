# Signal Taxonomy and Scoring v2

## 1. 信号不是新闻

一个 raw item 只有在满足以下条件之一时才应升级为 signal：

- 改变了对 frontier model 能力或风险的判断；
- 更新了安全框架、政策、承诺或监管结构；
- 提供了新的 eval/benchmark/methodology；
- 揭示了新的 misuse/incident/failure mode；
- 体现了国际共识或分歧的变化；
- 来自可信访谈/会议且包含新的实质性 claim；
- 对已有事件提供了更权威的一手证据。

## 2. Signal Types

- `policy_update`
- `benchmark_change`
- `model_release_risk`
- `risk_framework`
- `technical_risk`
- `incident_or_misuse`
- `consensus_signal`
- `lab_governance`
- `research_trend`
- `podcast_claim`
- `event_signal`
- `meta_signal`

## 3. Risk Domains

- `autonomy`
- `ai_rnd`
- `cyber`
- `biosecurity`
- `chemical_risk`
- `deception`
- `scheming`
- `eval_awareness`
- `eval_integrity`
- `model_control`
- `alignment`
- `interpretability`
- `misuse`
- `agent_security`
- `frontier_governance`
- `international_coordination`
- `open_weight_risk`
- `deployment_governance`
- `safety_case`

## 4. Evidence Level

| level | 含义 |
|---|---|
| `primary_official` | 官方原文、官方报告、官方 system card、政府公告 |
| `primary_transcript` | 一手访谈 transcript、会议视频 transcript、官方会议材料 |
| `third_party_research` | METR/Apollo/AISI/GovAI/FAR 等研究或评估 |
| `peer_review_or_preprint` | arXiv / conference paper |
| `reputable_news` | Reuters、TechCrunch、TIME、The Verge、Wired 等报道 |
| `commentary` | 专栏、博客、个人观点 |
| `unverified_social` | 社交媒体传闻，默认 needs_human_review |

## 5. Claim Type

- `factual_update`
- `evaluation_result`
- `methodology_change`
- `policy_commitment`
- `governance_position`
- `expert_prediction`
- `risk_warning`
- `incident_report`
- `agenda_signal`
- `framework_diff`
- `benchmark_delta`

## 6. Scoring

### 6.1 Severity: 1–5

- 1：轻微信息，背景噪音；
- 2：对某个细分领域有参考价值；
- 3：会影响一个风险域的判断；
- 4：会影响多个风险域或重要机构/政策判断；
- 5：重大风险、重大政策、重大 eval 结果或广泛国际影响。

### 6.2 Confidence: 1–5

- 1：传闻或低质量来源；
- 2：单一二手来源；
- 3：可信来源但证据有限；
- 4：一手来源或可信研究；
- 5：官方/多来源一致/有数据支持。

### 6.3 Time Sensitivity: 1–5

- 1：长期背景；
- 2：周级别关注；
- 3：本周需要关注；
- 4：今天/明天需要处理；
- 5：立即关注或可能迅速扩散。

### 6.4 Source Priority

- high：1.0
- medium：0.7
- low：0.4

### 6.5 Priority Score

```text
priority_score =
  severity * 0.42
+ confidence * 0.25
+ time_sensitivity * 0.20
+ source_priority * 5 * 0.13
```

## 7. Human Review Rules

自动标记 `needs_human_review = true`：

- severity >= 4 且 confidence <= 3；
- evidence_level in `commentary`, `unverified_social`；
- podcast/interview 中的 expert prediction 被升级为 high priority；
- 涉及具体人物争议、国家安全、bio/cyber 可操作细节；
- LLM 无法确认 primary_source_url；
- 与已有官方来源冲突。

## 8. Triage Output JSON

Hermes 必须输出可验证 JSON：

```json
{
  "is_signal": true,
  "title_zh": "...",
  "summary_zh": "...",
  "what_changed": "...",
  "why_it_matters": "...",
  "what_to_watch_next": "...",
  "signal_type": "technical_risk",
  "risk_domains": ["cyber", "agent_security"],
  "entities": ["Anthropic", "Codex"],
  "evidence_level": "primary_transcript",
  "claim_type": "risk_warning",
  "primary_source_url": "https://...",
  "severity": 3,
  "confidence": 4,
  "time_sensitivity": 3,
  "needs_human_review": false,
  "evidence_snippets": [
    {"url": "https://...", "quote": "short quote", "timestamp": "00:12:31"}
  ]
}
```
