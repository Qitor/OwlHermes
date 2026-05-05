# R1-08: Automated Hermes Daily Dry Run

## Purpose

R1-08 produces the first real, non-production, Hermes-led AI risk observation dry run. Hermes uses its own web/search/research capabilities to inspect 3-5 real sources, then stores candidate items, source runs, and a dry-run digest through the backend MCP tools.

## Docker is NOT Required

R1-08 uses a local SQLite file-based dry-run database by default. No Docker, no local PostgreSQL.

PostgreSQL remains the production/shared-deployment target — it is not a local dry-run requirement.

## SQLite Dry-Run DB

- Default path: `.local/risk_observer_dryrun.db`
- Default URL: `sqlite:///./.local/risk_observer_dryrun.db`
- Initialized via `Base.metadata.create_all()` (not the Postgres-specific `schema.sql`)
- The directory `.local/` is gitignored

## How to Run

```bash
# Initialize the dry-run DB
make db-init-dryrun

# Check DB readiness
make db-check

# Run preflight checks (Hermes, registries, MCP, DB)
make r108-dry-run-preflight

# Run the automated Hermes dry run
make r108-run-hermes

# Inspect the dry-run DB state
make r108-inspect-state
```

## Run Artifacts

Each run creates a timestamped directory under `runs/r1_08/<timestamp>/`:

- `prompt.md` — exact prompt sent to Hermes
- `hermes_stdout.log` — captured stdout
- `hermes_stderr.log` — captured stderr
- `hermes_output.md` — combined output
- `summary.md` — compact run summary

Run artifacts are gitignored by default.

## Success Criteria

Minimum:
- At least one source run recorded
- At least one raw item stored (unless Hermes explains why not)
- One dry-run digest stored with status `dry_run`

Ideal:
- 3-5 source runs recorded
- 3-8 raw items stored
- 1 dry-run digest stored
- 1-3 candidate or actual signals stored (0 is acceptable if no genuine signals found)

## Known Limitations

- This is a non-production dry run. Output is not delivered externally.
- No Feishu, WeCom, WeChat posting occurs.
- No cron scheduling is configured.
- No website is built or updated.
- Hermes may not find new items if selected sources have no recent updates.
- The dry-run DB uses SQLite; production should use PostgreSQL.

## Non-Production Warning

**This is explicitly a non-production dry run. It does not deliver to Feishu, WeCom, WeChat, or any external channel.**
