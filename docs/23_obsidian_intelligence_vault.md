# R1-12: Signal Evidence Persistence + Obsidian Intelligence Vault

## Overview

R1-12 adds two capabilities:

1. **Evidence/claim persistence** — Hermes can now store and search evidence items (claim-level detail) linked to signals or raw items
2. **Obsidian Intelligence Vault** — Export DB state into a structured Obsidian vault for human review, linking, and note-taking

## Evidence Persistence

### New MCP Tools

| Tool | Purpose |
|------|---------|
| `risk_evidence_store` | Store a claim-level evidence item |
| `risk_evidence_search` | Search evidence by signal_id, raw_item_id, source_id, or claim_type |

### Evidence Fields

| Field | Type | Description |
|-------|------|-------------|
| `raw_item_id` | uuid (optional) | Linked raw item |
| `signal_id` | uuid (optional) | Linked signal |
| `source_id` | string (optional) | Source identifier |
| `claim_text` | string | The claim or observation text |
| `claim_type` | string | Default: `hermes_extraction` |
| `evidence_url` | URL (optional) | Primary source URL |
| `evidence_title` | string (optional) | Title of the evidence |
| `evidence_excerpt` | string (optional) | Relevant excerpt |
| `evidence_level` | string | Default: `secondary` |
| `confidence` | int 1-5 (optional) | Confidence level |
| `supports_signal` | bool (optional) | Whether evidence supports or weakens the signal |
| `risk_domains` | list[str] | Relevant risk domains |
| `entities` | list[str] | Entities mentioned |
| `needs_human_review` | bool | Default: false |

### Model

Evidence uses the existing `SourceClaim` model with extended fields:
- `signal_id` (FK to signals)
- `source_id`
- `evidence_excerpt`
- `evidence_title`
- `supports_signal`

`raw_item_id` is now nullable (evidence can exist without a raw item).

## Obsidian Intelligence Vault

### Vault Structure

```
AI-Risk-Intelligence/
├── 00_Daily/          # Daily report notes
├── 01_Signals/        # Individual signal notes
├── 02_Candidates/     # Raw item/candidate notes
├── 03_Evidence/       # Evidence/claim notes
├── 04_Sources/        # Source registry notes
├── 05_Risk_Domains/   # Risk domain aggregation notes
├── 06_Entities/       # Entity notes (from registry)
├── 07_Runs/           # Source run notes
├── 08_Live_Runs/      # Live research run notes (R1-13)
├── 90_Review_Queue/   # Needs-review and failed-sources notes
└── 99_Indexes/        # Index notes with counts
```

### Generated Block Safety

All exported content is wrapped in markers:

```
<!-- BEGIN_AUTO_GENERATED: hermes-ai-risk-observer -->
... generated content ...
<!-- END_AUTO_GENERATED: hermes-ai-risk-observer -->
```

Human content outside these markers is preserved when re-exporting. If a note has no markers, the generated block is appended without overwriting.

### Commands

```bash
make obsidian-export            # Export DB state to Obsidian vault
make obsidian-export-dry-run    # Preview what would be exported
make obsidian-open-latest       # Export and open vault directory
make daily-report-and-obsidian  # Run daily report then export
```

Direct script usage:

```bash
python scripts/obsidian_export.py --latest                    # Export today
python scripts/obsidian_export.py --date 2025-05-05           # Specific date
python scripts/obsidian_export.py --latest --dry-run          # Preview only
python scripts/obsidian_export.py --latest --json             # JSON summary
python scripts/obsidian_export.py --latest --open             # Open after export
python scripts/obsidian_export.py --vault /path/to/vault      # Custom vault path
```

### Configuration

Environment variable `OBSIDIAN_VAULT_PATH` overrides the default vault location (`.local/obsidian_vault`).

### Signal Notes

Each signal note includes the three-question fields:
- **What Changed?** — what changed in the risk landscape
- **Why It Matters** — impact on risk judgment
- **What to Watch Next** — next observation point

Missing fields are highlighted with "*Missing — needs review*".

### Review Queue

Two notes in `90_Review_Queue/`:
- `needs-review.md` — signals and evidence items needing human review
- `failed-sources.md` — source runs with error status

## MCP Tool Count

With R1-13C, the MCP server exposes 23 tools (was 18):

| # | Tool | Added |
|---|------|-------|
| 1-13 | Original tools | R1-06 through R1-09 |
| 14 | `risk_source_health_summary` | R1-09 |
| 15 | `risk_discovery_helper_preview` | R1-09 |
| 16 | `risk_candidate_preprocess` | R1-11B |
| 17 | `risk_evidence_store` | R1-12 |
| 18 | `risk_evidence_search` | R1-12 |
| 19 | `risk_live_run_start` | R1-13 |
| 20 | `risk_live_event_append` | R1-13 |
| 21 | `risk_live_note_upsert` | R1-13 |
| 22 | `risk_live_run_finalize` | R1-13 |
| 23 | `risk_live_daily_report_upsert` | R1-13C |

## R1-12B: Real E2E Vault Population Validation

R1-12B ensures the Obsidian vault is populated with real signal/candidate/evidence/run content, not just indexes.

### Evidence Placeholders

When a signal has `primary_source_url` but no linked `SourceClaim` items, the exporter creates a placeholder evidence note:
- `claim_text`: "Evidence URL linked by Hermes; excerpt not yet captured."
- `needs_review: true` and `placeholder: true` in frontmatter
- Wikilink to the associated signal

### Daily Note Intelligence Links

Daily notes now include a "Linked Intelligence Objects" section with wikilinks to:
- Signal Index, Candidate Index, Evidence Index, Source Index, Run Index
- `failed-sources.md` and `needs-review.md`

Frontmatter includes: `signals_count`, `candidates_count`, `evidence_count`, `runs_count`, `failed_sources_count`.

### Review Queue Enhancement

`needs-review.md` now includes a "Signals Without Evidence" section listing signals with no linked SourceClaim items that aren't already in the needs-review list.

### Vault Inspection

```bash
make obsidian-inspect                         # Inspect vault contents
python scripts/inspect_obsidian_export.py --latest   # Inspect latest export
python scripts/inspect_obsidian_export.py --json      # JSON output
```

The inspect script validates: note counts per directory, daily-signal links, signal three-question fields, generated block markers, signals without evidence, and failed sources.

### E2E Target

```bash
make daily-report-and-obsidian-e2e   # Full pipeline: daily-report + quality + export + inspect
```

Requires `OBSIDIAN_VAULT_PATH` env var. Fails with instructions if not set.

## Design Principles

1. **Deterministic export** — the exporter reads only local DB state, no network calls
2. **Human-safe** — generated block markers preserve human content outside auto-generated blocks
3. **Atomic writes** — notes are written to `.tmp` then renamed
4. **Evidence links to signals** — evidence items can be linked to signals for traceability
5. **Conservative entities** — entity notes come only from source registry organizations, not extracted from content
6. **No LLM in export** — the Obsidian vault export is purely deterministic
