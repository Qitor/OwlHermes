# Podcast and Event Monitoring Spec

## 1. 播客/访谈为什么重要

前沿实验室研究员、高管、政策专家经常在长访谈中透露比官方公告更丰富的信息，例如：

- 对能力时间线的判断；
- 安全框架背后的动机；
- 对监管/国际合作的看法；
- 新的 eval、benchmark、失败模式；
- 组织内部安全流程的解释。

这些不是新闻，但可能是高价值情报。

## 2. Hermes-native monitoring model

Podcast、YouTube/video、conference talk、slides、transcript 和 event materials 应优先由 Hermes-Agent 使用 built-in video/transcript/browser/research skills 处理。Backend 不应在 MVP 中变成完整 transcript scraping、video downloading 或 audio transcription platform。

Backend 负责保存 Hermes 识别出的 durable state：

- episodes；
- talks；
- transcript URLs or transcript text when available；
- materials links；
- raw items；
- claims；
- benchmark observations；
- signals；
- evidence and uncertainty metadata。

## 3. Podcast Workflow

```text
Hermes reads registry due sources
  -> Hermes uses built-in podcast/video/transcript/research tools
  -> MCP checks whether episode/talk/raw item was seen before
  -> MCP stores raw item or transcript metadata
  -> Hermes extracts claim-level evidence
  -> MCP stores claims/signals/benchmark observations
  -> Hermes writes digest
```

Optional deterministic podcast RSS helper may list new episodes, but it does not replace Hermes claim extraction or risk triage.

## 4. Transcript Priority

1. 官方 transcript；
2. Hermes-accessible YouTube captions；
3. podcast website transcript；
4. Hermes-supported transcription workflow if explicitly available；
5. metadata-only fallback。

没有 transcript 时，只能基于标题/description 产生低置信度 candidate，不得直接生成 high-priority signal。

## 5. Podcast Claim Schema

```json
{
  "episode_id": "...",
  "speaker": "...",
  "claim_text": "...",
  "claim_type": "expert_prediction",
  "risk_domains": ["autonomy"],
  "evidence_timestamp": "00:42:10",
  "evidence_quote": "short quote",
  "confidence": 3,
  "should_promote_to_signal": false
}
```

## 6. Event / Conference Workflow

```text
Hermes reads event registry
  -> Hermes uses browser/research tools for agenda/materials
  -> optional sitemap/simple diff helper flags stable page changes
  -> MCP stores raw item/material metadata
  -> Hermes extracts talk/statement claims
  -> MCP stores event signals and evidence
```

## 7. Event Signal Examples

应升级为 signal：

- 发布联合声明；
- 多国/多实验室 red lines；
- 新 benchmark/eval talk；
- 新安全承诺；
- 高可信专家公开改变立场；
- 会议材料透露新技术风险或治理方案。

不应升级为 signal：

- 普通会议报名开放；
- 无明确 AI risk 相关性的 panel；
- 纯营销内容；
- 没有材料和证据的标题党。

## 8. [un]prompted 处理建议

`[un]prompted` 应作为 AI security / ML security / agentic AI 安全事件源。重点关注：

- autonomous cyber capabilities；
- AI code/security agents；
- malware/vulnerability discovery；
- MCP/security tooling；
- talks by Anthropic、DeepMind、OpenAI、security researchers；
- slides/videos/materials updates。

## 9. Digest 栏目

日报中新增：

```markdown
## 播客/访谈
- 节目 / 嘉宾：关键 claim；为什么重要；证据链接。

## 会议/论坛
- 会议 / talk / statement：新信息；为什么重要；后续关注。
```
