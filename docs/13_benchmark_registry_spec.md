# Benchmark Registry Spec

## 1. 目标

关键 benchmark/eval 变化是本产品的核心壁垒之一。它不能和普通新闻混在一起处理。

Benchmark/framework watch 是 Hermes-led workflow：Hermes 使用 built-in research/browser skills 和自定义 skill rubric 解释变化；backend 负责 registry、historical lookup、observation persistence 和 website/API data layer。可选 simple webpage diff helper 只负责稳定页面的 hash/diff signal，不负责风险判断。

## 2. Benchmark Registry

文件：

```text
source_registry/benchmark_registry.yaml
```

每个 benchmark entry：

```yaml
- id: metr_time_horizon
  name: METR time horizon / autonomy evaluations
  risk_domains: [autonomy, ai_rnd]
  source_ids: [metr_evaluations]
  observation_type: report_value
  extraction_method: manual_or_llm_assisted
  trigger_rules:
    - type: threshold_crossing
      description: Significant increase in task horizon or autonomous capability.
  notes: ...
```

## 3. Observation Schema

```json
{
  "benchmark_id": "metr_time_horizon",
  "model_name": "...",
  "observed_at": "2026-05-04",
  "value_text": "...",
  "value_numeric": null,
  "unit": null,
  "source_url": "https://...",
  "evidence": "...",
  "risk_interpretation": "...",
  "confidence": 4
}
```

## 4. 初期关注方向

- autonomy / long-horizon task capability；
- AI R&D assistance；
- cyber offensive capability；
- bio/chem assistance；
- deception / scheming / eval awareness；
- model control；
- agent reliability / tool use；
- safety cases / preparedness thresholds；
- open-weight misuse indicators。

## 5. Framework Diff

同时追踪：

- OpenAI Preparedness Framework；
- Anthropic Responsible Scaling Policy；
- Google DeepMind Frontier Safety Framework；
- UK AISI methods/reports；
- Safe AI Forum / IDAIS policy guide；
- Frontier AI Safety Commitments。

Framework diff 不是 benchmark，但应进入同一“risk framework / threshold”观察通道。Hermes 负责判断 diff 是否改变风险评估；backend 保存 diff evidence、benchmark observations、signals 和历史记录。
