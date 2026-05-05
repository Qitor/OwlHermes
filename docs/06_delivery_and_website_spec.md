# Delivery and Website Spec v2

## 1. 推送渠道

优先顺序：

1. 飞书机器人；
2. 企业微信机器人；
3. 网站；
4. 邮件 newsletter；
5. 微信公众号/个人微信/其他渠道后续评估。

MVP 不应依赖个人微信作为唯一交付渠道。

## 2. 日报推送格式

飞书/企业微信短版：

```markdown
# 前沿 AI 风险信号日报｜YYYY-MM-DD

今日总览：一句话总结。

## Top Signals
1. [高] 标题 — why matters 简短说明
2. [中] 标题 — why matters 简短说明

## 播客/访谈
- 访谈对象/节目：关键 claim

## 会议/论坛
- 会议名：关键 agenda/statement/material update

## 需人工复核
- ...

完整版本：网站链接
```

## 3. 网站 MVP 页面

### 首页

- 今日 digest；
- Top signals；
- filter by risk domain；
- source health summary。

### Signals 页面

- 列表；
- 按日期、类型、风险域、source、priority 过滤；
- signal card。

### Signal Detail

- 中文摘要；
- what changed；
- why it matters；
- what to watch next；
- evidence snippets；
- source claims；
- related event cluster；
- raw item links；
- human review status。

### Sources 页面

- source list；
- last fetched；
- last success；
- fail count；
- modality；
- collector；
- health。

### Podcasts / Events 页面（Round 2）

- podcast episodes；
- transcripts status；
- extracted claims；
- event agenda changes；
- talks/materials。

### Benchmarks 页面（Round 3）

- benchmark registry；
- observations；
- trend/timeline。

## 4. API Endpoints

- `GET /api/signals`
- `GET /api/signals/{id}`
- `GET /api/digests/latest`
- `GET /api/digests/{date}`
- `GET /api/sources/health`
- `GET /api/podcasts/episodes`
- `GET /api/events`
- `GET /api/benchmarks`

MCP endpoints 可以复用 backend API，但 namespace 建议为 `/api/mcp/*`。
