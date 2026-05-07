# Final Report Format

## Chinese Risk Intelligence Digest

The report is written in Chinese, not because it needs translation, but because:
- Target users think and work in Chinese
- "Risk intelligence" has specific meaning in Chinese context
- Chinese can convey uncertainty and judgment nuances more precisely
- Keep English terms when they are the best expression

## Report Structure

```
前沿 AI 风险每日简报 | YYYY-MM-DD

■ 一句话总览
  Today's most significant change in risk landscape, one sentence.

■ 信号
  Each signal includes:
  - 标题（中文）
  - 变化：什么改变了
  - 影响：对哪种风险判断的影响
  - 观察：接下来关注什么
  - 证据：primary source URL
  - 置信度：高/中/低 + 原因

■ 候选但未升级为信号的条目
  - Brief list of considered-but-not-promoted items
  - Reason for non-promotion

■ 来源扫描摘要
  - Which sources were scanned
  - Which had new findings, which didn't
  - Helper tool effectiveness

■ 证据和不确定性
  - Evidence gaps
  - Unverified claims
  - Low-confidence areas

■ 需跟进
  - Source reliability issues
  - High-impact low-confidence items
  - Suggested deep-dive directions
```

## Quality Requirements

- **0 high-confidence signals is acceptable** — explicitly state "no signals found" with source check evidence
- **Quality over quantity** — 2 well-reasoned signals > 10 weak ones
- **No tool call logs** — readers care about judgment, not process
- **Don't mechanically translate English titles** — restate in Chinese with risk context
- **Don't list all raw items** — report is not a discovery dump
- **Don't overfill** — if only 1 signal, 1 is enough
- **Avoid hype** — no "revolutionary", "breakthrough", "unprecedented" without evidence
- **Avoid AGI doomerism** — don't amplify timeline speculation without credible evidence

## Storage

```
owl_risk_state(action="store_digest", payload={
    "digest": {
        "digest_date": "2026-05-06",
        "title": "前沿 AI 风险每日简报 | 2026-05-06",
        "body": "<full markdown>",
        "status": "local_daily_report",
        "source_ids": ["anthropic_news", "openai_news"],
        "summary": {"new_raw_items": 5, "new_signals": 2, ...}
    }
})
```
