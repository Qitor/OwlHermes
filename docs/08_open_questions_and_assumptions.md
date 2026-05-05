# Open Questions and Assumptions v2

## 1. 已修正

- `SAIF` 在本项目中指 **Safe AI Forum**，不是 Google Secure AI Framework。
- Google Secure AI Framework 可作为安全框架来源候选，但不能用 `saif` id，避免混淆。若后续加入，使用 `google_secure_ai_framework`。

## 2. 当前假设

1. 第一阶段优先中文日报。
2. 推送优先飞书/企业微信。
3. 个人微信不作为 MVP 唯一渠道。
4. 播客/视频第一阶段先抓 metadata 和已有 transcript，不强制自动转写。
5. 会议/论坛第一阶段先抓 agenda/materials diff，不强制解析全部视频。
6. 网站第一阶段只做内部/半公开 dashboard，不做复杂用户系统。
7. Hermes-Agent 已部署在可运行 cron 和 gateway 的环境中。

## 3. 需要用户后续决定

- 自有网站域名、部署平台、是否公开；
- 飞书/企业微信群机器人配置；
- 是否需要微信公众号同步；
- 是否允许下载/转写播客音频；
- 是否允许 YouTube captions 抓取；
- 日报发送时间与时区；
- 是否需要英文版 digest；
- 是否要加入非英文来源，例如中文、日文、韩文、法文政策源。

## 4. 风险

### 数据源不稳定

部分实验室和会议网站没有稳定 feed，应优先由 Hermes 使用 browser/research workflow 探索；必要时再用 sitemap/simple hash diff helper 辅助。

### 播客噪音

访谈中有大量观点、预测和背景信息，必须 claim-level 抽取，不要把整集节目当成一条 signal。

### 会议议程噪音

会议举办本身不一定是 signal。只有 agenda、talk、statement、materials 体现风险判断变化时才升级。

### 评分漂移

LLM 对 severity/confidence 的评分会漂移，需要 calibration set。

### 事实核查

新闻和访谈可能有二手解释或夸张表达。所有 signal 必须保留 evidence level 和 primary source。
