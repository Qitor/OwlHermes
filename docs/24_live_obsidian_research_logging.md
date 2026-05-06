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
