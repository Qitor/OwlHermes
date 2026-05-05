# 安全与运维

## 1. Secret 管理

所有密钥放：

- `~/.hermes/.env`：Hermes provider、gateway、API server 密钥；
- 项目 `.env`：数据库、后端、网站 API token；
- 不提交任何真实密钥。

必须加入 `.gitignore`：

```gitignore
.env
.env.*
!.env.example
*.pem
*.key
.hermes/
```

## 2. Hermes API Server 安全

若启用 Hermes API Server：

- 默认只绑定 `127.0.0.1`；
- 必须配置 `API_SERVER_KEY`；
- CORS 必须是显式 allowlist；
- 外网访问应经反向代理和认证；
- 不要让浏览器持有 Hermes bearer token；
- 由网站后端代理调用。

## 3. MCP 安全

MCP server 工具要限制能力：

- 不暴露任意 SQL；
- 不暴露任意 shell；
- 所有查询参数白名单；
- 后端 API token；
- 记录 audit logs。

## 4. Hermes Terminal 安全

生产环境建议：

- Hermes terminal backend 使用 Docker 或受限用户；
- 限制工作目录；
- 不把系统级密钥传入 agent 容器；
- dangerous command 需要人工批准；
- 生产 cron prompt 避免要求 Hermes 执行不必要的 shell 命令。

## 5. 数据安全

保存内容：

- 来源公开文本；
- 模型生成摘要；
- 信号 metadata。

不保存：

- 用户隐私聊天；
- 非公开内部文档；
- 未授权付费全文；
- 不必要的 cookies。

## 6. 监控

最低要求：

- 后端 `/api/health`；
- DB 连接检查；
- source health；
- 每日 digest 是否生成；
- delivery status；
- Hermes gateway status；
- cron list/status。

## 7. 备份

Postgres：

- 每日 `pg_dump`；
- 保留 14–30 天；
- 备份加密；
- 恢复演练。

文件：

- `sources.yaml`；
- skill；
- config examples；
- prompts；
- website build。

## 8. 日志

建议字段：

- request_id；
- source_id；
- collector；
- raw_item_id；
- signal_id；
- digest_id；
- channel；
- status；
- error_class；
- latency_ms。

## 9. 合规与版权

- 对新闻类内容只展示摘要；
- 付费内容只保留 metadata 和链接；
- 遵守 robots.txt 和 API terms；
- 对 arXiv 遵守访问节奏；
- 提供删除/纠错机制。

## 10. 运维命令示例

```bash
# Hermes gateway
hermes gateway status
hermes gateway start
hermes gateway stop

# Cron
hermes cron list
hermes cron status
hermes cron run <job_id>

# 后端
docker compose ps
docker compose logs -f risk-api
docker compose exec db psql -U risk -d risk_signals

# 数据库备份
pg_dump "$DATABASE_URL" > backup_$(date +%F).sql
```
