# Live Vault Workflow

## Overview

Live Obsidian vault logging records research progress in real time during daily report runs. It is **optional and disabled by default**.

Enable with: `OBSIDIAN_LIVE_LOGGING_ENABLED=true` and `OBSIDIAN_VAULT_PATH` set.

## Live Vault Actions

### Start a Run

```
owl_live_vault(action="start_run", payload={
    "run_id": "optional-custom-id",
    "title": "Daily Report 2026-05-06"
})
```

### Append Events

```
owl_live_vault(action="append_event", payload={
    "run_id": "<run_id>",
    "event_type": "source_selected",
    "title": "Checking Anthropic news",
    "source_id": "anthropic_news"
})
```

Allowed event types: `run_started`, `source_selected`, `source_check_started`, `source_check_completed`, `source_failed`, `candidate_found`, `candidate_seen_check`, `candidate_stored`, `evidence_extracted`, `signal_promoted`, `signal_stored`, `digest_stored`, `run_finalized`, `note`, `warning`

### Upsert Notes

```
owl_live_vault(action="upsert_note", payload={
    "run_id": "<run_id>",
    "note_type": "signal",
    "slug": "anthropic-rsp-update",
    "title": "Anthropic RSP Capability Threshold Update",
    "body": "New capability threshold added for autonomous research..."
})
```

Note types: `source`, `candidate`, `evidence`, `signal`, `failure`

### Write Daily Report

```
owl_live_vault(action="upsert_daily_report", payload={
    "report_date": "2026-05-06",
    "report_markdown": "# Full report markdown here...",
    "digest_id": "<uuid>",
    "run_id": "<run_id>"
})
```

**MUST pass complete Markdown body** — do NOT pass references like "See digest xxx".

### Finalize Run

```
owl_live_vault(action="finalize_run", payload={
    "run_id": "<run_id>",
    "final_report_markdown": "# Full report markdown...",
    "daily_report_date": "2026-05-06",
    "quality_score": 90
})
```

### Inspect Latest

```
owl_live_vault(action="inspect_latest")
```

## Auto-Mirror

When live vault is enabled, `owl_risk_state(action="store_signal")` and `owl_risk_state(action="store_evidence")` automatically create corresponding Obsidian notes. You do NOT need to manually call `upsert_note` for every signal or evidence.

## Important Rules

- If `start_run` returns `live_vault_enabled: false`, **continue normally without live logging**
- Live vault is **observational/persistence only** — it must not replace DB tools
- You must still call: seen-check, raw_item_store, evidence_store, signal_store, digest_store
- **Do NOT write private chain-of-thought into Obsidian** — only observable research state
- All writes are constrained to `OBSIDIAN_VAULT_PATH` — no arbitrary file writes
- `make obsidian-export` is for backfill/repair, not normal daily UX
