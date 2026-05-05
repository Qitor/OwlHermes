# Round 1 Codex Task Cards

每个 task card 应作为一个独立 Codex 会话或一个小 PR 完成。不要跨卡大范围修改。Round 1 目标是 Hermes-led signal observation with deterministic backend state，不是大型 crawler。

## R1-01 — Repo scaffold and packaging

Goal: 创建可运行的 Python backend 项目骨架。

Scope:
- `pyproject.toml`
- backend package
- `tests/`
- `.env.example` or reuse `configs/env.example`

Acceptance:
- `python -m compileall frontier_ai_risk_observer tests` passes.
- `python -m pytest` runs with placeholder tests.
- README explains local setup.

## R1-02 — Database foundation

Goal: 将 `schemas/schema.sql` 接入本地初始化流程，并建立 SQLAlchemy/session 基础。

Scope:
- DB connection settings
- schema init command
- model/session placeholders or models
- test database instructions

Acceptance:
- DB init can apply schema to a configured Postgres instance.
- Failure mode is clear if DB is unavailable.
- Default tests do not require real Postgres.

## R1-03 — Registry validation

Goal: 校验 source registries 的结构和必填字段。

Scope:
- `scripts/validate_registries.py`
- registry dataclasses or pydantic models
- tests for invalid registry examples

Acceptance:
- Validates `source_registry/sources.yaml`, `podcasts.yaml`, `events.yaml`, `benchmark_registry.yaml`.
- Fails with useful error message on missing id/url/category.

## R1-04 — Ingestion interface and registry service API

Goal: 为 Hermes-led discovery 提供 registry lookup 和 raw item ingestion contract。

Scope:
- service functions for registry lookup / due source listing
- raw item input schema
- API routes or service methods for storing Hermes-discovered raw items
- no real collectors

Acceptance:
- Hermes-facing API/service can list due sources.
- Raw item payload can be validated before persistence.
- Tests cover valid/invalid ingestion payloads.

## R1-05 — Raw item storage and dedup service

Goal: 实现 URL canonicalization、content hash、title similarity 和 historical seen check。

Scope:
- raw item persistence service
- dedup utilities
- seen-check and similar-item search
- source run / audit record hooks if needed

Acceptance:
- Duplicate URLs do not create duplicate raw items.
- Same title from multiple URLs can be grouped or flagged.
- Tests cover URL normalization and seen-check behavior.

## R1-06 — Minimal MCP tools

Goal: 将 durable backend state 暴露给 Hermes-Agent。

Scope:
- MCP tools for registry/raw_items/signals/digests
- tool names emphasize product-state capabilities
- smoke test script

Acceptance:
- `make mcp-smoke` verifies tool imports and basic registry access without Hermes.
- Tools include registry due-source listing, raw item seen check/store/search, duplicate candidates, source run recording, signal storage/search, and digest storage/search.
- No general-purpose crawler tool is exposed.

## R1-07 — Custom Hermes skill integration smoke test

Goal: 让 Hermes 可以发现 custom skill 和 MCP tool surface。

Scope:
- `configs/hermes_config.example.yaml`
- `skills/ai-risk-signal-observer/SKILL.md`
- smoke test instructions

Acceptance:
- README documents external Hermes setup at a high level without vendoring Hermes.
- Skill daily workflow references actual MCP product-state tool names.

## R1-08 — Hermes-led daily dry run

Goal: 用 sample inputs 模拟 Hermes daily workflow：registry -> research result -> raw item -> signal -> digest。

Scope:
- dry-run script or documented manual flow
- sample data fallback
- output report

Acceptance:
- Runs without real secrets.
- Produces raw item count, candidate signal count, digest record/status.
- Clearly separates Hermes judgment from backend state writes.

## R1-09 — Optional deterministic helpers

Goal: 为稳定低智能来源添加 optional helpers，不替代 Hermes research。

Scope:
- RSS helper
- podcast RSS helper
- arXiv helper
- sitemap helper
- simple webpage hash/diff helper
- source health result object

Acceptance:
- Helpers can be run independently when network is available.
- Network failures do not crash whole run.
- Helpers write through the same ingestion interface.

## R1-10 — Minimal website/API view

Goal: 极简展示 digest、signals、source health / run state。

Scope:
- minimal API routes or website scaffold integration
- no complex auth

Acceptance:
- Local page or API displays latest digest and source health/run state.
- README documents how to run it.

## R1-11 — Delivery dry run

Goal: 模拟 Hermes gateway delivery result and backend delivery record。

Scope:
- delivery event storage API/tool
- deterministic sample digest
- Feishu/WeCom dry-run stub only if needed

Acceptance:
- Delivery stub logs intended target without requiring real webhook.
- Delivery event is recorded in backend state.

## R1-12 — End-to-end review and Round 2 plan

Goal: Codex 整理 Round 1 技术债和下一轮计划。

Scope:
- update `docs/03_implementation_plan.md`
- update `docs/08_open_questions_and_assumptions.md`
- add `docs/16_round2_plan.md`

Acceptance:
- Lists known limitations.
- Separates must-fix, should-fix, later.
- Round 2 focuses on signal quality, calibration, benchmark/framework observation, and podcast/event claim evidence.
