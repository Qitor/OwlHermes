# 问题数据源清单

基于 R1-05 至 R1-13D 的实际运行经验，以下数据源的采集方式存在已知问题。

## 完全无法自动采集

| source_id | 名称 | 采集方式 | 问题 | 建议 |
|-----------|------|----------|------|------|
| `openai_news` | OpenAI News | 无 helper | Cloudflare 浏览器验证完全封锁所有自动化访问（直接导航、helper、复选框验证均失败） | 只能通过搜索引擎获取第三方报道（Yahoo Search 可用，Google/DuckDuckGo 可能触发 CAPTCHA） |
| `safe_ai_forum_updates` | Safe AI Forum Updates | 无 helper | 页面超时，无法加载 | 重试一次，失败则跳过并在日报中注明 |
| `idais_main` | International Dialogues on AI Safety | 无 helper | 页面超时，无法加载 | 重试一次，失败则跳过并在日报中注明 |

## Helper 配置但实际不可用

| source_id | 名称 | helper_type | 问题 | 建议 |
|-----------|------|-------------|------|------|
| `anthropic_news` | Anthropic News | `scrapling_official_page` | SSL EOF 错误，helper 完全失败 | 必须用浏览器手动导航；直接拼接文章 URL 可能 404，需从列表页提取链接 |
| `apollo_blog` | Apollo Research Blog | `scrapling_official_page` | 403 Forbidden，helper 完全失败 | 必须用浏览器手动导航；更新频率极低（最后文章 2026-01-20），可改为每周检查 |
| `axrp` | AXRP 播客 | `scrapling_official_page` | Helper 返回导航链接而非剧集列表，完全无法发现新节目 | 使用 RSS feed `https://axrp.net/feed.xml` 或手动浏览；registry 中未配置 feed_url |
| `arxiv_ai_safety` | arXiv AI Safety | `arxiv_query` | API 频繁被限速或用户策略封锁（R1-05、R1-09B 均失败） | 降级为浏览器搜索；考虑 OAI-PMH 端点或搜索引擎替代 |

## 可访问但有限制

| source_id | 名称 | 问题 | 建议 |
|-----------|------|------|------|
| `uk_aisi_blog` | UK AISI Blog | 单篇文章 URL 可能 404 | 必须从列表页提取链接，不要尝试拼接 URL |
| `eu_ai_office` | European AI Office | 主题过滤器 (topics=1666) 可能无效 | 使用 "Latest News" 板块替代 |
| `govai_research` | GovAI Research | 年份筛选器需要 JavaScript 交互 | 使用 browser_console 设置值；更新频率低（最后文章 2026-04-20），可改为每周检查 |
| `ai_safety_summit_series` | AI Safety Summit Series | URL 仅覆盖 2023 Bletchley 峰会，不追踪后续峰会（Seoul 2024、Paris 2025、India/Geneva） | 需人工审查确定每个峰会的官方页面 |

## 更新频率极低

| source_id | 名称 | 最后更新 | 建议 |
|-----------|------|----------|------|
| `apollo_blog` | Apollo Research Blog | 2026-01-20 | 改为每周检查，不要每日 |
| `metr_evaluations` | METR Evaluations | 2025-11-19 | 改为每两周检查 |
| `safe_ai_forum` | Safe AI Forum Updates | 2025-05（内容页） | 改为每周检查，且准备好超时回退 |
| `axrp` | AXRP 播客 | 不定期（低频） | 改为每周检查 |

## 播客源缺乏自动采集配置

以下 5 个播客源没有 `helper_type` 和 `feed_url`，完全依赖 Hermes 手动浏览，效率极低：

| source_id | 名称 | 建议改进 |
|-----------|------|----------|
| `dwarkesh_podcast` | Dwarkesh Podcast | 查找并配置 RSS feed URL |
| `eighty_thousand_hours_podcast` | 80,000 Hours Podcast | `https://80000hours.org/podcast/feed/` 可能可用 |
| `cognitive_revolution` | Cognitive Revolution | 查找并配置 RSS feed URL |
| `latent_space` | Latent Space | `https://www.latent.space/feed` 可能可用 |
| `security_cryptography_whatever` | Security Cryptography Whatever | 查找并配置 RSS feed URL |

## 已禁用

| source_id | 名称 | 状态 |
|-----------|------|------|
| `reuters_technology_ai` | Reuters Technology AI | `enabled: false`，待后续启用 |
| `google_secure_ai_framework_optional` | Google Secure AI Framework | `enabled: false`，可选源 |

## 可靠数据源（对比参考）

| source_id | 名称 | 采集方式 | 可靠性 |
|-----------|------|----------|--------|
| `techcrunch_ai` | TechCrunch AI | RSS | 最可靠，一次获取全部候选 |
| `nist_caisi` | NIST CAISI | 无 helper | 可靠，活跃发布 |
| `uk_aisi_research` | UK AISI Research | 无 helper | 可靠，活跃发布 |
| `deepmind_blog` | DeepMind Blog | 无 helper | 可通过浏览器+子代理正常访问 |

## 优先改进建议

1. **为播客源配置 RSS feed URL** — 影响最大，5 个播客源目前无自动采集
2. **为 `axrp` 添加 `feed_url: https://axrp.net/feed.xml`** — 最简单的修复
3. **`anthropic_news` 和 `apollo_blog` 的 scrapling helper 不可用** — 考虑改为 `manual` 或添加 RSS feed 发现逻辑
4. **`arxiv_ai_safety` 需要替代方案** — OAI-PMH 端点或基于搜索引擎的发现
5. **`openai_news` 需要搜索代理模式** — 目前完全依赖 Hermes 手动搜索引擎查询
