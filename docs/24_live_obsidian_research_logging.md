# R1-13: Live Obsidian Research Logging

## Overview

R1-13 adds live Obsidian vault writing during Hermes research runs. Instead of only exporting the vault after a run completes, Hermes can now write research progress to the vault in real time, making the vault a live research workspace.

**Why**: Users should feel the intelligent autonomous research process. Intermediate findings should be preserved as they happen. Obsidian becomes the human-facing, editable, long-term intelligence vault.

**SQLite is retained** as the fast runtime cache for seen-check, dedup, fast MCP state, source runs, raw items, signals, evidence, and digests. Obsidian vault is the human-readable layer.

## What Gets Logged

Live vault logging records **observable research state** only:

- Source checked / selected / completed / failed
- Candidate found / stored
- Evidence extracted
- Signal promoted / stored
- Digest stored
- Run started / finalized

**What must NOT be logged:**

- Private chain-of-thought or hidden reasoning
- Secrets or API keys
- Every minor thought — only meaningful research milestones

## Vault Directory Structure

Live runs are stored under `08_Live_Runs/`:

```
AI-Risk-Intelligence/
  08_Live_Runs/
    YYYY-MM-DD_HHMMSS/
      Live Research Log.md    # Main run log with all events
      Timeline.md             # Chronological timeline
      Failures.md             # Failed source checks
      Sources/
        <source_id>.md        # Per-source status notes
      Candidates/
        <candidate-slug>.md   # Per-candidate notes
      Evidence/
        <evidence-slug>.md    # Per-evidence notes
      Signals/
        <signal-slug>.md      # Per-signal notes
```

Final export (`make obsidian-export`) may consolidate live notes into `00_Daily/`, `01_Signals/`, `02_Candidates/`, `03_Evidence/`, `07_Runs/`.

## MCP Tools

Four new MCP tools for live vault logging:

| Tool | Purpose |
|------|---------|
| `risk_live_run_start` | Start a live research run |
| `risk_live_event_append` | Append a structured event to the log |
| `risk_live_note_upsert` | Write/update a source/candidate/evidence/signal note |
| `risk_live_run_finalize` | End the run with a summary |

### Event Types

| Event Type | When |
|------------|------|
| `run_started` | Run begins |
| `source_selected` | Source chosen for checking |
| `source_check_started` | Starting to check a source |
| `source_check_completed` | Source check done |
| `source_failed` | Source check failed |
| `candidate_found` | Candidate discovered |
| `candidate_seen_check` | Seen-check on candidate |
| `candidate_stored` | Candidate stored via `risk_raw_item_store` |
| `evidence_extracted` | Evidence item extracted |
| `signal_promoted` | Candidate promoted to signal |
| `signal_stored` | Signal stored via `risk_signal_store` |
| `digest_stored` | Digest stored via `risk_digest_store` |
| `run_finalized` | Run completed |
| `note` | General note |
| `warning` | Warning |

### Note Types for `risk_live_note_upsert`

Allowed: `source`, `candidate`, `evidence`, `signal`, `failure`. Arbitrary note types are rejected. The `failure` note type writes to `Failures.md` within the live run.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OBSIDIAN_VAULT_PATH` | (empty) | Vault root directory |
| `OBSIDIAN_LIVE_LOGGING_ENABLED` | `false` | Enable live logging |
| `OBSIDIAN_LIVE_RUNS_DIR` | `08_Live_Runs` | Directory name for live runs |
| `OBSIDIAN_LIVE_APPEND_TO_DAILY` | `true` | Append live run links to daily note |
| `OBSIDIAN_LIVE_OPEN_AFTER_START` | `false` | Open Obsidian after run starts |
| `OBSIDIAN_LIVE_EVENT_MAX_CHARS` | `4000` | Max chars per event body |
| `OBSIDIAN_LIVE_FLUSH_MODE` | `immediate` | `immediate` or `buffered` |

If `OBSIDIAN_LIVE_LOGGING_ENABLED=true` but `OBSIDIAN_VAULT_PATH` is not set, the tools return a clear error.

## Commands

```bash
make daily-report-live-vault       # Run daily report with live vault logging
make daily-report-live-vault-e2e   # Full E2E with requirements validation
make live-vault-inspect            # Inspect live vault runs
make obsidian-open-live-run        # Open latest live run in Obsidian/Finder
```

Script usage:

```bash
python scripts/inspect_live_vault.py --vault ~/Documents/airo
python scripts/inspect_live_vault.py --run-id 2026-05-05_143000 --json
python scripts/inspect_live_vault.py --latest --require-events 1 --require-finalized
python scripts/inspect_live_vault.py --latest --require-note-types source,candidate,evidence,signal --db-check
```

## Live vs Post-Run Export

| Aspect | Live Logging | Post-Run Export |
|--------|-------------|-----------------|
| When | During research | After completion |
| Content | Working notes, events, timeline | Consolidated, polished |
| Structure | `08_Live_Runs/YYYY-MM-DD_HHMMSS/` | `00_Daily/`, `01_Signals/`, etc. |
| Purpose | Real-time visibility | Final archive |
| Human edits | Preserved in generated blocks | Preserved in generated blocks |

## Security Constraints

- All vault writes are constrained to `OBSIDIAN_VAULT_PATH` — no arbitrary file writes
- No path traversal — resolved paths are validated against vault root
- Generated block markers preserve human content outside `<!-- BEGIN_AUTO_GENERATED -->` / `<!-- END_AUTO_GENERATED -->`
- Filenames use `slugify_filename()` — no unsafe characters
- Obsidian CLI is optional — direct Markdown writes work without it

## Obsidian CLI (Optional)

Obsidian CLI can automate Obsidian from the terminal. It is not required:

- Direct Markdown file writing is the core path
- CLI may be used for: opening latest notes, search, appending to daily note
- If Obsidian is not running, the first CLI command may launch it
- Set `OBSIDIAN_LIVE_OPEN_AFTER_START=true` to auto-open on run start

## R1-13B: E2E Validation & Research UX Hardening

R1-13B addresses critical gaps discovered during live vault E2E testing:

### Stateless Writer Fix

MCP tool calls are stateless — each call creates a fresh `LiveVaultWriter` instance. The `_active_runs` in-memory dict is never shared between calls. The fix: `_ensure_run_tracked()` auto-discovers run directories from filesystem when a run_id is not in the in-memory dict.

### Schema Hardening

- `note_type` in `LiveNoteUpsertInput` uses `Literal["source", "candidate", "evidence", "signal", "failure"]` for compile-time validation
- `event_type` and `body` have `Field(description=...)` annotations for Hermes discoverability
- `body` description explicitly states "Observable research state only. No chain-of-thought."

### COT Violation Detection

The inspect script checks for chain-of-thought phrases in live vault notes:
- English: "chain of thought", "hidden reasoning", "private reasoning", "inner monologue", "private thoughts"
- Chinese: "思维链", "内心独白", "隐含推理"

### Export Linking to Live Runs

- Daily export (`_export_daily`) links to the latest live run with a wikilink
- If a live run matches today's date, the `live_run_id` is added to frontmatter
- New `Live Run Index` in `99_Indexes/` lists recent live runs

### E2E Validation Target

`make daily-report-live-vault-e2e` runs the full pipeline with requirements:
- `--require-events 1`: at least 1 event must be recorded
- `--require-note-types source,candidate,evidence,signal`: all note types must have entries
- `--db-check`: cross-reference vault notes with DB research_events
- Quality check and Obsidian export are included

### Prompt Hardening

Prompts now explicitly mention:
- Pass `run_id` from `risk_live_run_start` to all subsequent live tool calls
- List allowed `event_type` values
- List allowed `note_type` values
- If live logging disabled, continue normally

## Live Vault UX Contract (R1-13C)

R1-13C closes the gap between live research and the final daily report, making Obsidian the primary human-facing interface for the entire research lifecycle.

### Immediate Daily Report Note Writing

When live vault is enabled, the final daily report appears in `00_Daily/YYYY-MM-DD.md` **immediately** when the run completes. Users no longer need to run `make obsidian-export` to see their daily report in Obsidian.

- `risk_live_run_finalize` now accepts optional `final_report_markdown` and `daily_report_date` fields. When provided, the finalizer writes (or updates) the daily note in `00_Daily/` before closing the run.
- `risk_live_daily_report_upsert` is a new dedicated MCP tool for explicitly writing or updating the daily report note at any point during or after a run. This decouples daily note writing from run finalization.
- Valuable intermediate research results are written as notes during the run, not only at the end.

### Bidirectional Links

All note types are connected via bidirectional wikilinks:

- Daily note links to its live run, and the live run links back to the daily note
- Signal notes link to their evidence, and evidence notes link back to their signals
- Candidate notes link to their source, and source notes link to candidates found from them
- `risk_live_note_upsert` now supports bidirectional link fields (`linked_signal_ids`, `linked_evidence_ids`, `linked_candidate_ids`, `linked_source_id`) that are rendered as wikilinks in both directions

Link resolution is handled by `obsidian/links.py`, which maintains a link index and ensures backlinks are written when forward links are created.

### Review Queue Live Integration

The review queue (`90_Review_Queue/`) is updated live during research runs:

- **Signals without evidence** are added to `needs-review.md` as soon as they are stored
- **Failed source checks** are added to `failed-sources.md` immediately
- **Evidence items needing review** (`needs_human_review=true`) appear in `needs-review.md` as they are extracted

This means the review queue is always current — no post-run export is required to surface items needing human attention.

### Digest Mirror to Obsidian

When `OBSIDIAN_LIVE_LOGGING_ENABLED=true`, `risk_digest_store` automatically mirrors the digest content to the daily note in `00_Daily/YYYY-MM-DD.md`. This ensures the Chinese-language intelligence summary is visible in Obsidian as soon as it is stored.

### Runner Safety Net

If a live run is interrupted (Hermes crash, timeout, network failure), the runner safety net ensures partial state is preserved:

- All notes written before the interruption remain in the vault
- The daily note reflects whatever content was written up to the interruption point
- A subsequent `risk_live_run_finalize` call (even from a new session) can complete the run and update the daily note
- The `run_id` is filesystem-based, so it survives process restarts

### UX Contract

**For normal live UX, `make obsidian-export` is no longer needed.** The daily report, signals, evidence, candidates, and review queue all appear in Obsidian during the live run.

`make obsidian-export` is reserved for:
- **Backfill** — populating the vault for dates before live logging was enabled
- **Repair** — regenerating notes that may be corrupted or out of sync
- **Full consolidation** — reconciling vault state with DB state after manual edits or schema changes

### New MCP Tool

| Tool | Purpose |
|------|---------|
| `risk_live_daily_report_upsert` | Write or update the daily report note in `00_Daily/` during or after a live run |

This brings the total MCP tool count to 23.

### Updated MCP Tools

| Tool | Change |
|------|--------|
| `risk_live_run_finalize` | Now accepts optional `final_report_markdown` and `daily_report_date` for immediate daily note write |
| `risk_live_note_upsert` | Now supports bidirectional link fields (`linked_signal_ids`, `linked_evidence_ids`, `linked_candidate_ids`, `linked_source_id`) |
| `risk_digest_store` | When live vault enabled, mirrors digest to Obsidian daily note |

### New Modules

| Module | Purpose |
|--------|---------|
| `obsidian/daily_note.py` | Daily report note creation, update, and frontmatter management for `00_Daily/` |
| `obsidian/links.py` | Bidirectional link resolution, backlink writing, and link index maintenance |
