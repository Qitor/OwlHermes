# Plugin Tool Guide

## OwlHermes Plugin Tools

OwlHermes provides 5 facade tools with action-based dispatch. Each tool takes `action` (required) and `payload` (optional object).

### owl_risk_state — Deterministic State Operations

| Action | Payload Fields | Description |
|--------|---------------|-------------|
| `seen_check` | `url`, `content_hash`, `source_id`, `title` | Check if a raw item has been seen before |
| `store_raw_item` | `source_id`, `title`, `url`, `content_text`, ... | Store a new candidate raw item |
| `search_raw_items` | `source_id`, `url`, `canonical_url`, `limit` | Search stored raw items |
| `duplicate_candidates` | `url`, `content_hash`, `source_id`, `title` | Find potential duplicates |
| `record_source_run` | `source_id`, `status`, `found_count`, `new_count` | Record a source check result |
| `store_evidence` | `signal_id`, `claim_text`, `evidence_url`, ... | Store evidence linked to a signal |
| `search_evidence` | `signal_id`, `raw_item_id`, `source_id` | Search evidence items |
| `store_signal` | `title`, `summary`, `risk_domains`, ... | Store a risk signal |
| `search_signals` | `source_id`, `signal_type`, `risk_domain` | Search stored signals |
| `store_digest` | `digest` (object with `digest_date`, `title`, `body`) | Store final report digest |
| `search_digests` | `digest_date`, `status`, `limit` | Search stored digests |

### owl_risk_discovery — Source Registry and Discovery

| Action | Payload Fields | Description |
|--------|---------------|-------------|
| `registry_summary` | — | Count of sources, podcasts, events, benchmarks |
| `list_due_sources` | `limit`, `kind`, `risk_domain` | List sources due for checking |
| `get_source` | `source_id` | Get details for a specific source |
| `source_health` | — | Source health summary with coverage |
| `helper_preview` | `source_id`, `fetch` | Preview candidate items from a helper |
| `feed_preview` | `source_id`, `fetch` | Preview RSS feed for a source |
| `sitemap_preview` | `source_id`, `fetch` | Preview scrapling helper for a source |
| `source_policy_summary` | — | Source reliability policy summary |

### owl_live_vault — Live Obsidian Research Logging

| Action | Payload Fields | Description |
|--------|---------------|-------------|
| `start_run` | `run_id`, `title`, `metadata` | Start a live research run |
| `append_event` | `run_id`, `event_type`, `title`, `body` | Append a research event |
| `upsert_note` | `run_id`, `note_type`, `slug`, `title`, `body` | Write/update a note |
| `upsert_daily_report` | `report_date`, `report_markdown`, `digest_id` | Write final daily report note |
| `finalize_run` | `run_id`, `final_report_markdown`, `daily_report_date` | End the live run |
| `inspect_latest` | — | Inspect recent live runs |

### owl_report_quality — Report Quality

| Action | Payload Fields | Description |
|--------|---------------|-------------|
| `check_report` | `report_text` or `report_path` | Check report quality |
| `latest_report_summary` | — | Summary of latest report quality |
| `review_queue_summary` | — | Count of items needing review |
| `quality_rubric_summary` | — | Quality checklist summary |

### owl_obsidian_export — Vault Export/Backfill

| Action | Payload Fields | Description |
|--------|---------------|-------------|
| `export_latest` | `export_date` | Export DB state to vault |
| `dry_run` | `export_date` | Preview export without writing |
| `inspect` | — | Inspect vault contents |
| `open_latest_if_available` | — | Open vault in Finder |

## Legacy MCP Fallback

If OwlHermes plugin tools are unavailable, use MCP legacy tools with equivalent semantics:

| Plugin Tool + Action | MCP Equivalent |
|---------------------|----------------|
| `owl_risk_state(seen_check)` | `risk_raw_item_seen_check` |
| `owl_risk_state(store_raw_item)` | `risk_raw_item_store` |
| `owl_risk_state(search_raw_items)` | `risk_raw_item_search` |
| `owl_risk_state(duplicate_candidates)` | `risk_raw_item_duplicate_candidates` |
| `owl_risk_state(record_source_run)` | `risk_source_run_record` |
| `owl_risk_state(store_evidence)` | `risk_evidence_store` |
| `owl_risk_state(search_evidence)` | `risk_evidence_search` |
| `owl_risk_state(store_signal)` | `risk_signal_store` |
| `owl_risk_state(search_signals)` | `risk_signal_search` |
| `owl_risk_state(store_digest)` | `risk_digest_store` |
| `owl_risk_state(search_digests)` | `risk_digest_search` |
| `owl_risk_discovery(registry_summary)` | `risk_registry_summary` |
| `owl_risk_discovery(list_due_sources)` | `risk_registry_list_due_sources` |
| `owl_risk_discovery(source_health)` | `risk_source_health_summary` |
| `owl_risk_discovery(helper_preview)` | `risk_discovery_helper_preview` |
| `owl_live_vault(start_run)` | `risk_live_run_start` |
| `owl_live_vault(append_event)` | `risk_live_event_append` |
| `owl_live_vault(upsert_note)` | `risk_live_note_upsert` |
| `owl_live_vault(upsert_daily_report)` | `risk_live_daily_report_upsert` |
| `owl_live_vault(finalize_run)` | `risk_live_run_finalize` |
