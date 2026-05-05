# R1-09B: Helper-Assisted Hermes Dry Run

## Purpose

R1-09B runs a controlled, automated, non-production Hermes dry run that verifies Hermes can actually use the R1-09 helper layer. It proves that the helper-assisted workflow works end-to-end: source health check → helper preview → candidate triage → seen-check → raw item storage → source run recording → signal judgment → digest writing.

## How It Differs from R1-08 and R1-09

| Aspect | R1-08 | R1-09 | R1-09B |
|--------|-------|-------|--------|
| Discovery | Hermes manual browsing only | Helper modules exist but not integrated with Hermes | Hermes uses helper tools via MCP |
| Source selection | Hermes chooses freely | N/A (code only) | Prefer helper-enabled sources |
| Candidate source | Web/search only | Helper CandidateItems returned to code | Helper preview via MCP → Hermes triage |
| Seen-check/dedup | Tested | Tested in unit tests | Tested against R1-08 data in DB |
| Digest sections | Basic Chinese digest | N/A | Expanded with helper usage, source health |
| DB state | Fresh SQLite | N/A | Reuses R1-08 DB (tests dedup/seen-check) |

## What Success Means

### Minimum success

- Hermes calls `risk_source_health_summary`
- Hermes calls `risk_discovery_helper_preview` at least once
- Hermes checks 3-5 sources
- Hermes records source runs
- Hermes stores a dry-run digest with status `dry_run`
- Run artifacts saved under `runs/r1_09b/<timestamp>/`

### Ideal success

- Hermes uses helper preview for at least 2 sources
- Hermes stores candidate raw items or correctly identifies duplicates from R1-08
- Hermes reports whether helpers reduced broad search need
- Hermes records source reliability issues
- Hermes stores 1-3 signals only if genuinely warranted
- No uncontrolled duplicate raw items created

### Acceptable outcomes

- `signals = 0` is fine if no genuine new signal is found
- `raw_items_new = 0` is fine if all candidates were already seen, as long as seen-check/dedup is clearly reported
- Some helper fetches may return 0 candidates, but Hermes must report why

## Why This Is Still Non-Production

- Uses local SQLite dry-run DB, not PostgreSQL
- No delivery channels configured (no Feishu/WeCom/WeChat posting)
- No cron scheduling
- No website updates
- No production data

## Why Docker/Postgres Are Not Required

SQLite file-based dry-run DB is sufficient for validation. PostgreSQL remains the production target. No Docker containers are needed.

## How to Run

```bash
# Preflight checks
make r109b-dry-run-preflight

# Run the full helper-assisted Hermes dry run
make r109b-run-hermes

# Inspect DB state after the run
make r109b-inspect-state
```

## Where Artifacts Are Saved

```
runs/r1_09b/<timestamp>/
  prompt.md           — exact prompt sent to Hermes
  hermes_stdout.log   — captured stdout
  hermes_stderr.log   — captured stderr
  hermes_output.md    — combined output
  summary.md          — compact run summary with R1-08 comparison
```

Artifact directories are excluded from version control via `.gitignore`.

## How to Interpret State Counts

After running `make r109b-inspect-state`:

- **raw_items**: Total items in DB. Should increase if new candidates were found; should stay the same if all were already seen from R1-08.
- **source_runs**: Should have new entries for each source checked in this run.
- **signals**: May be 0. Only non-zero if Hermes judged a genuine new risk signal.
- **digests**: Should have a new entry with status `dry_run`.
- **Items seen more than once**: Indicates dedup/seen-check is working (candidates from R1-09B were already in R1-08 data).

## Known Limitations

- Helper coverage is limited (5/43 entries have helpers). Most sources still require manual browsing.
- Scrapling helpers extract links from a single page only — no recursive crawling.
- Some source URLs may have changed since the registry was last updated.
- The `podcast_rss` helper type exists but no podcast entries have RSS feed URLs configured yet.
- Benchmark observation storage is still a placeholder.

## What to Do If Helper Fetch Returns 0 Candidates

1. Check if the source URL is still valid.
2. Check if `link_include_patterns` are too restrictive.
3. Hermes should fallback to limited manual browsing for that source only.
4. Report the issue in the digest under 来源健康状态.
5. Consider marking the source `requires_human_review: true` if the issue persists.

## What to Do If Hermes Does Not Call Helper Tools

1. Verify Hermes config includes `risk_source_health_summary` and `risk_discovery_helper_preview` in the tools include list.
2. Run `make hermes-smoke` to verify the MCP server is registered.
3. Try `hermes mcp test ai_risk_observer` to verify connectivity.
4. If tools are not discovered, run `make hermes-smoke-apply` to update the config.
5. Restart Hermes or run `/reload-mcp` in chat.

## What to Do If Scrapling Extraction Returns Noisy Candidates

1. Check `link_include_patterns` and `link_exclude_patterns` — add patterns to filter noise.
2. Reduce `max_items` to limit candidate count.
3. Navigation URLs (about, contact, privacy, etc.) are automatically filtered.
4. If noise persists, consider switching the source to `helper_type: manual` temporarily.
