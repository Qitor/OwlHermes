# Codex Execution Guide

本文件说明如何让 Codex 来实现本项目。Codex 是开发工具；Hermes-Agent 是最终系统运行时。

## 1. 为什么需要从 Codex 文档改成 Codex 文档

Codex 会自动读取仓库中的 `AGENTS.md` 作为项目级指令，因此核心开发约束应放在仓库根目录的 `AGENTS.md`。任务说明应拆成小而明确的 task cards，便于 Codex CLI、IDE 或 Cloud task 按 PR 粒度执行。

## 2. 推荐启动方式

在新仓库中放入本文档包，然后运行：

```bash
codex
```

启动后让 Codex 先执行：

```text
Read AGENTS.md, README.md, docs/00_codex_master_prompt.md, and docs/15_round1_codex_task_cards.md. Then implement Task R1-01 only. Keep the diff small and run applicable validation commands.
```

如果使用非交互式方式，可把一个 task card 的全文作为 prompt。

## 3. Codex 工作粒度

推荐一轮只做一个 task card：

- R1-01 repo scaffold and Python packaging
- R1-02 database migration and schema loader
- R1-03 registry validation
- R1-04 ingestion interface and registry service API
- R1-05 raw item storage and dedup service
- R1-06 minimal MCP tools
- R1-07 Hermes skill integration smoke test
- R1-08 Hermes-led daily dry run
- R1-09 optional deterministic helpers
- R1-10 website/API minimal view

不要一轮同时做 backend、frontend、MCP、Hermes、delivery。这样会让 diff 过大，也会降低可验证性。

## 4. Codex 应遵循的实现原则

### 保持确定性边界

本仓库负责 registry validation、raw item persistence、dedup、historical lookup、source run records、API 和 MCP state tools。Hermes 负责 source prioritization、web/video/research exploration、triage、摘要、why matters、what to watch next、manual review 标记。不要把本仓库做成通用 crawler 或 agent runtime。

### 先做接口，再做完整覆盖

播客、会议、PDF、视频 transcript 在 Round 1 应优先复用 Hermes built-in skills/tools。后端先做 storage/interface，不要一开始引入复杂音频转写或 transcript scraping pipeline。

### 先本地可跑，再接真实部署

Round 1 应支持：

```bash
cp configs/env.example .env
python scripts/validate_registries.py
python scripts/smoke_mcp_server.py
python -m pytest
```

如果外部 API key 缺失，Hermes workflow 或 optional helper 应优雅跳过相关来源，并在 source run / health 中记录 skipped reason。

## 5. Codex 提交总结模板

每次任务完成时，Codex 应输出：

```text
Summary
- ...

Changed files
- ...

Validation
- command: result
- command: result

Known limitations
- ...

Next recommended task
- R1-XX ...
```

## 6. 权限和安全

Codex 不应读取或提交真实密钥。所有密钥必须通过 `.env` 或部署环境注入。默认不要使用绕过 sandbox/approval 的模式，除非在外部隔离环境中运行。

## 7. 与 Hermes-Agent 的衔接

Codex 要实现的是 Hermes 可调用的 backend 和 MCP product-state surface：

- Hermes 或 optional deterministic helper 发现材料后，通过 MCP 写入 `raw_items`；
- MCP tools 暴露 registry lookup、seen check、raw item store/search、claim/signal/digest/benchmark observation storage 等能力；
- Hermes skill 读取 MCP tools，完成 daily triage/digest/delivery；
- Hermes cron 负责每日触发；
- Hermes gateway 负责推送。

Codex 不应把 Hermes runtime 内嵌进 backend，也不应把 daily workflow 写死成 Python-only cron。
