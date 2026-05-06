# R1-12 Progress Report: Signal Evidence Persistence + Obsidian Intelligence Vault

**Date**: 2026-05-05
**Status**: Complete

## What was implemented

### 1. Evidence/Claim Persistence

- Extended `SourceClaim` model with `signal_id`, `source_id`, `evidence_excerpt`, `evidence_title`, `supports_signal` fields
- Made `raw_item_id` nullable (evidence can exist without a raw item)
- Changed `evidence_level` default to `'secondary'`
- New service: `services/evidence.py` with `store_evidence_item()`, `search_evidence_items()`, `list_recent_evidence_items()`, `evidence_to_dict()`
- New MCP tools: `risk_evidence_store`, `risk_evidence_search` (total: 18 tools, was 16)
- New Pydantic schemas: `EvidenceStoreInput`, `EvidenceSearchInput`

### 2. Obsidian Intelligence Vault

- **Markdown utilities** (`obsidian/markdown.py`): `slugify_filename`, `safe_filename`, `render_frontmatter`, `wikilink`, `markdown_link`, `atomic_write`, `replace_generated_block`, `write_generated_note`
- **Exporter service** (`obsidian/exporter.py`): `ObsidianExporter` with export methods for daily, signal, candidate, evidence, source, risk domain, entity, run, review queue, and index notes
- **CLI integration** (`obsidian/cli.py`): Obsidian app detection, vault opening, Finder opening
- **Export script** (`scripts/obsidian_export.py`): CLI with `--latest`, `--date`, `--vault`, `--dry-run`, `--open`, `--json` flags

### 3. Vault Structure

```
AI-Risk-Intelligence/
├── 00_Daily/          # Daily report notes
├── 01_Signals/        # Individual signal notes (with three-question fields)
├── 02_Candidates/     # Raw item/candidate notes (with review checklist)
├── 03_Evidence/       # Evidence/claim notes
├── 04_Sources/        # Source registry notes (43 sources)
├── 05_Risk_Domains/   # Risk domain aggregation notes (77 domains)
├── 06_Entities/       # Entity notes (from registry organizations)
├── 07_Runs/           # Source run notes
├── 90_Review_Queue/   # needs-review.md + failed-sources.md
└── 99_Indexes/        # 7 index notes with counts
```

### 4. Generated Block Safety

All auto-generated content is wrapped in `<!-- BEGIN_AUTO_GENERATED: hermes-ai-risk-observer -->...<!-- END_AUTO_GENERATED: hermes-ai-risk-observer -->` markers. Re-exporting preserves human content outside these markers.

### 5. Makefile Targets

- `make obsidian-export` — export DB state to Obsidian vault
- `make obsidian-export-dry-run` — preview without writing
- `make obsidian-open-latest` — export and open vault
- `make daily-report-and-obsidian` — run daily report then export

### 6. Config Updates

- `configs/env.example` — added `OBSIDIAN_VAULT_PATH`
- `configs/hermes_config.example.yaml` — added `risk_evidence_store`, `risk_evidence_search`

### 7. Prompt/Skill Updates

- `skills/ai-risk-signal-observer/SKILL.md` — step 7 for evidence storage, evidence guidance section
- `prompts/daily_report_prompt.md` — added `risk_evidence_store`, `risk_evidence_search`
- `prompts/daily_report_finalize_prompt.md` — added `risk_evidence_search`
- `prompts/interactive_daily_report_prompt.md` — added evidence store

### 8. Documentation

- `docs/23_obsidian_intelligence_vault.md` — full R1-12 documentation
- `README.md` — R1-12 section
- `CLAUDE.md` — updated tool count to 18, added obsidian/ and evidence service layers

## Test Results

- **74 new tests** in `tests/test_r12_obsidian_evidence.py`
- Categories: evidence service (13), markdown utils (25), Obsidian exporter (13), MCP schemas (3), export script (3), CLI (3), Makefile targets (4), documentation (10), MCP registration (2)
- **Full suite**: 431 passed, 0 failed
- **Lint**: All checks passed on R1-12 files

## Bugs Fixed During Implementation

1. **Exporter used `session.scalar(select(Signal))` instead of `session.scalar(select(func.count(Signal.id)))`** — SQLite returned a Signal object that couldn't be compared with `or 0`
2. **Exporter called `bundle.get()` on `RegistryBundle` dataclass** — fixed to use attribute access (`bundle.sources`, etc.)
3. **Exporter `_get_session` passed URL string to `create_session_factory`** — fixed to create engine first via `create_db_engine`
4. **`_yaml_scalar` f-string used Python 3.12 nested quote syntax** — fixed for Python 3.11 compatibility

## Actual Export Test

Ran `make obsidian-export` with fresh DB:

```
Daily notes:     1
Signal notes:    0
Candidate notes: 0
Evidence notes:  0
Source notes:    43
Risk domain notes: 77
Entity notes:    0
Run notes:       0
Review notes:    2
Index notes:     7
```

Vault created at `.local/obsidian_vault/AI-Risk-Intelligence/` with 130 Markdown files. The daily note contains the full Chinese risk briefing from the most recent Hermes run, with proper frontmatter and generated block markers.

## Files Created/Modified

### Created
- `frontier_ai_risk_observer/services/evidence.py`
- `frontier_ai_risk_observer/obsidian/__init__.py` (already existed)
- `frontier_ai_risk_observer/obsidian/markdown.py`
- `frontier_ai_risk_observer/obsidian/exporter.py`
- `frontier_ai_risk_observer/obsidian/cli.py`
- `scripts/obsidian_export.py`
- `tests/test_r12_obsidian_evidence.py`
- `docs/23_obsidian_intelligence_vault.md`

### Modified
- `frontier_ai_risk_observer/db/models.py` — extended SourceClaim
- `frontier_ai_risk_observer/mcp/schemas.py` — added EvidenceStoreInput, EvidenceSearchInput
- `frontier_ai_risk_observer/mcp/server.py` — added risk_evidence_store, risk_evidence_search
- `configs/env.example` — OBSIDIAN_VAULT_PATH
- `configs/hermes_config.example.yaml` — evidence tools
- `skills/ai-risk-signal-observer/SKILL.md` — evidence storage guidance
- `prompts/daily_report_prompt.md` — evidence tools
- `prompts/daily_report_finalize_prompt.md` — evidence search
- `prompts/interactive_daily_report_prompt.md` — evidence store
- `Makefile` — obsidian-export targets
- `README.md` — R1-12 section
- `CLAUDE.md` — 18 tools, obsidian layer, evidence service
