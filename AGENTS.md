# AGENTS.md — Codex 工作规则

## Repository purpose

This repository implements a **Hermes-Agent based frontier AI risk signal observatory**. Codex is the coding agent used to build the repo; Hermes-Agent remains the runtime/orchestration layer.

## Non-negotiable product rules

1. 本项目必须基于 Hermes-Agent，不要重建 agent runtime。
2. Hermes 负责 orchestration、source prioritization、research exploration、LLM triage、digest、gateway delivery；后端负责确定性状态、存储、去重、API。
3. 不要把本仓库做成 Hermes-Agent 的替代品，也不要实现通用 crawler/agent runtime；优先 Hermes-led workflow + 小型确定性 backend tools。
4. 确定性 collectors 只能作为稳定低智能来源的 helper，例如 RSS、podcast RSS、arXiv、sitemap、简单网页 hash/diff，不是主要情报层。
5. 不要把密钥写入代码或文档；使用 `.env`。
6. 所有新增来源必须先进入 registry，不允许散落在代码里。
7. SAIF 在本项目中指 **Safe AI Forum**，不是 Google Secure AI Framework。
8. 播客/访谈/会议材料是一级来源类型，不是 news fallback。
9. 第一版不要做成泛 AI 新闻聚合器；只保留会改变风险判断的高质量信号。

## Codex workflow

- Start by reading `README.md`, `docs/00_codex_master_prompt.md`, and `docs/14_codex_execution_guide.md`.
- Work in small, reviewable diffs. Prefer one task card from `docs/15_round1_codex_task_cards.md` per Codex session.
- Before editing, inspect existing files and preserve the architecture boundary.
- After editing, summarize changed files, commands run, failures, and next steps.
- Do not introduce new production dependencies without explaining why they are needed.
- If a task is ambiguous, make a grounded implementation decision and document it in `docs/08_open_questions_and_assumptions.md` instead of blocking.

## Priority order

Current priority: run a high-quality vertical MVP before expanding sources.

Must prioritize:

1. source registry validation;
2. backend project skeleton;
3. raw item ingestion;
4. deterministic dedup;
5. MCP surface;
6. Hermes daily workflow;
7. signal triage schema;
8. digest generation;
9. delivery integration;
10. source health.

Do not prioritize yet:

- complex auth/RBAC;
- paid subscriptions;
- large-scale crawlers;
- general-purpose crawler or agent runtime;
- recommendation algorithms;
- full knowledge graph;
- over-polished frontend.

## Expected verification commands

Run what applies to the files changed:

```bash
python -m compileall .
python -m pytest
python scripts/validate_registries.py
python scripts/smoke_mcp_server.py
```

If these scripts do not exist yet, create minimal versions as part of the relevant task card.

## Hermes-specific reminder

Files under `skills/` are Hermes-Agent skills, not Codex skills. Do not move or rewrite them as Codex skills unless explicitly asked. Codex may use separate development guidance in this `AGENTS.md`, while Hermes uses `skills/ai-risk-signal-observer/SKILL.md` during runtime.
