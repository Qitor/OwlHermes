# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Frontier AI Risk Signal Observer (`frontier-ai-risk-observer`) — a deterministic backend that supports an external Hermes-Agent runtime for orchestrating daily AI risk intelligence workflows. Targets AI safety/governance/policy teams with Chinese-language risk intelligence. The backend **never** fetches external URLs, runs collectors, calls LLMs, summarizes, or triages — it only stores, retrieves, deduplicates, and validates.

## Commands

```bash
make install          # Create .venv, pip install -e ".[dev]"
make test             # Run pytest
make lint             # Run ruff check .
make typecheck        # Run mypy frontier_ai_risk_observer
make run-api          # Start uvicorn on 127.0.0.1:8787
make db-init          # Apply schemas/schema.sql to PostgreSQL
make db-init-dryrun   # Initialize local SQLite dry-run DB (.local/risk_observer_dryrun.db)
make db-check         # Check DB readiness (works with SQLite or Postgres)
make db-reset-dryrun  # Delete and reinitialize the dry-run DB
make validate-registries  # Validate all YAML registries
make mcp-smoke        # Run MCP server smoke check
make hermes-smoke     # Dry-run Hermes integration check (no config mutation)
make hermes-smoke-apply  # Apply MCP+skills config to ~/.hermes/config.yaml (with backup)
make r108-dry-run-preflight  # Run all R1-08 preflight checks
make r108-run-hermes  # Automatically launch Hermes dry run
make r108-inspect-state  # Inspect dry-run DB contents
make source-health    # Check source health and helper coverage
make preview-helpers  # List all sources with helpers
make r109-helper-preflight  # Validate registries + health + MCP + helpers
make r109b-dry-run-preflight  # Run all R1-09B preflight checks
make r109b-run-hermes  # Launch helper-assisted Hermes dry run
make r109b-inspect-state  # Inspect dry-run DB after R1-09B run
make daily-report-preflight    # Preflight for automated daily report
make daily-report             # Run two-phase daily report (collection + finalize)
make daily-report-inspect     # Inspect latest daily report run
make daily-report-with-quality   # Run daily report then check quality
make daily-report-finalize    # Force finalize phase on latest run
make daily-report-debug       # Show latest run artifacts and summary
make hermes-interactive-preflight  # Preflight for interactive daily report
make hermes-interactive-daily      # Launch Hermes interactive daily report
make hermes-interactive-copy-prompt # Print prompt without launching
make report-quality-check        # Check latest daily report quality (deterministic, no LLM)
make report-quality-review       # Write Markdown quality review
make model-tier-smoke            # Test candidate preprocess (no network/API keys)
make model-tier-smoke-live       # Test with live small model (if configured)
```

Run a single test: `.venv/bin/python -m pytest tests/test_dedup_service.py`
Run a specific test: `.venv/bin/python -m pytest tests/test_api.py::test_health`

## Architecture

**Hermes owns judgment/orchestration; the backend owns deterministic state and tools.**

Data flow: Source Registry (YAML) → Hermes-Agent (external, daily workflow) → Backend API (store/retrieve/dedup) → MCP Server (16 tool functions for Hermes)

### Key layers

- **`api/`** — FastAPI app with three route groups: `/registry/*` (YAML-backed, no DB), `/ingestion/*` (raw item CRUD, seen-check, dedup, source runs), health/version
- **`registry/`** — Loads 5 YAML files from `source_registry/` with Pydantic validators: sources (22), podcasts (6), events (6), benchmarks (9), risk_keywords
- **`services/dedup.py` + `services/ingestion.py`** — Dedup pipeline: canonicalize URL → SHA-256 content hash → normalize title → build dedup key (canonical URL > content hash > source_id + normalized title). On match: increment seen_count, update last_seen_at
- **`db/`** — SQLAlchemy 2.0 (mapped_column style) models for 11 tables, session factory, schema init via raw SQL
- **`mcp/`** — FastMCP server exposing 16 tool functions that Hermes calls via MCP protocol
- **`collectors/`** — Placeholder only (return empty lists). Real collection deferred to Hermes-Agent
- **`helpers/`** — R1-09 deterministic discovery helpers (scrapling_official_page, rss, podcast, arxiv). Return CandidateItems, do NOT store or judge
- **`quality/`** — R1-11 report quality checker (deterministic, no LLMs). Reads `quality/daily_report_checklist.yaml`, runs section-detection and anti-pattern checks, produces 0-100 score
- **`models/`** — R1-11B model-tiering: `SmallModelClient` for optional small/fast model (advisory only), `SmallModelConfig` from env vars, `candidate_preprocess` service
- **`workers/`** — Placeholder daily_run returning not_implemented

### Database

PostgreSQL 16 with 11 tables for production. SQLite file-based dry-run DB for local development (`make db-init-dryrun`). Schema applied via `schemas/schema.sql` for Postgres, `Base.metadata.create_all()` for SQLite. Alembic installed but not used yet.

### Testing

Tests use in-memory SQLite (`StaticPool`) as PostgreSQL stand-in. FastAPI `TestClient` for API tests. `monkeypatch` for env vars. Session factory injection via `set_session_factory_for_tests()` for MCP tests.

## Implementation Status

R1-01 through R1-09B are done. R1-10 (stable daily report run modes) is done. R1-11 (daily report quality loop) is done. R1-11B (model-tiered daily report pipeline) is done. R1-11C (two-phase daily report finalization) is done — Phase A collection + Phase B finalize, state snapshots, completion detection, signal three-question fields. R1-12+ (website, production delivery) are TODO.

### Hermes Integration

Hermes-Agent is external (not vendored). Integration via `~/.hermes/config.yaml`:
- MCP server `ai_risk_observer`: stdio command launching `.venv/bin/python -m frontier_ai_risk_observer.mcp.server`
- Skills external dir: `skills/` directory
- 16 `risk_*` tools allowlisted, prompts/resources disabled
- `hermes mcp add` CLI has `-m` flag parsing issues; use YAML editing instead (`make hermes-smoke-apply`)
- MCP SDK is an optional dependency: `pip install -e ".[mcp]"`

## Product Rules (from AGENTS.md)

- Must be Chinese-language risk intelligence, not a news aggregator
- Must identify signals from frontier AI labs, eval labs, policy labs, governments, arXiv, podcasts, interviews, conferences
- Dedup is deterministic — no LLM in the dedup pipeline
- Backend never fetches external URLs or calls LLMs
