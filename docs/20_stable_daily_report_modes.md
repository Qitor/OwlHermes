# R1-10: Stable Daily Report Run Modes

## Purpose

R1-10 adds two stable run modes for producing daily AI risk reports:

1. **`make daily-report`** — automated, non-interactive, one-shot Hermes run
2. **`make hermes-interactive-daily`** — interactive terminal session where a human can observe Hermes working

Both modes use the same daily report workflow and prompt family. The difference is only in how Hermes is launched.

## Why Two Modes?

- **Automated mode** is for when you trust the pipeline and just want today's report. Hermes runs in one-shot mode (`hermes -z <prompt> --yolo`), produces a report, and exits.
- **Interactive mode** is for observing, debugging, or demonstrating how Hermes uses MCP tools and makes risk judgments. The human can watch each step in the terminal.

## How Both Modes Use Hermes-Agent

Both modes launch Hermes-Agent as the primary operator. Hermes:
- Selects sources from the registry
- Uses helper preview tools to get candidates
- Uses its own web/search/research to read and verify content
- Makes risk judgments
- Stores results via MCP tools
- Writes a Chinese daily report

The backend provides deterministic state (registry, seen-check, dedup, storage). Hermes provides judgment and research.

## How Both Modes Use MCP Tools and Helpers

Both modes give Hermes access to the same 15 MCP tools, including the two R1-09 helper tools:
- `risk_source_health_summary` — check source availability
- `risk_discovery_helper_preview` — preview candidate items

Helpers are used to reduce broad search. They do not replace Hermes judgment.

## How to Run

### Preflight

```bash
make daily-report-preflight       # Automated mode preflight
make hermes-interactive-preflight  # Interactive mode preflight
```

Both run the same checks: registry validation, source health, MCP smoke, Hermes smoke, DB readiness.

### Automated daily report

```bash
make daily-report
```

This runs preflight, launches Hermes in one-shot mode, and saves artifacts.

### Inspect the latest report

```bash
make daily-report-inspect
```

Shows DB state and the latest run directory.

### Interactive daily report

```bash
make hermes-interactive-daily
```

This runs preflight and launches Hermes with the interactive prompt. Hermes runs in the terminal so you can observe tool calls and progress.

If you want to see the prompt without launching Hermes:

```bash
make hermes-interactive-copy-prompt
```

## Where Artifacts Are Saved

```
runs/daily/YYYYMMDD_HHMMSS/
  prompt.md           — exact prompt used
  hermes_stdout.log   — captured stdout
  hermes_stderr.log   — captured stderr
  hermes_output.md    — combined output
  daily_report.md     — final daily report
  summary.md          — compact run summary

runs/interactive/YYYYMMDD_HHMMSS/
  prompt.md           — exact prompt used
```

Artifact directories are gitignored.

## What Success Looks Like

### Minimum

- Hermes launched automatically
- Daily report prompt was used
- At least 3 sources checked
- `risk_source_health_summary` called
- `risk_discovery_helper_preview` called for helper-enabled sources
- `risk_raw_item_seen_check` called before storing
- Source runs recorded
- Daily report digest stored
- `daily_report.md` artifact exists

### Ideal

- 5-8 sources checked with balanced coverage
- Helper preview used for at least 2 sources
- Candidate raw items stored or identified as duplicates
- 1-5 genuine risk signals stored
- Chinese daily report is readable and useful
- Report includes evidence links, uncertainty, helper usefulness

### Acceptable

- `signals = 0` if no genuine new signals
- `raw_items_new = 0` if all candidates already seen
- Some helper previews return 0 candidates

## Known Limitations

- Helper coverage is limited (5/43 entries). Most sources require Hermes manual browsing.
- Interactive mode uses one-shot `hermes -z <prompt> --yolo` because true `hermes chat` auto-injection is unreliable. The human can still observe tool calls in the output.
- No external delivery. Reports are stored locally only.
- SQLite only — no PostgreSQL required.

## No Docker Requirement

All runs use the local SQLite dry-run DB. No Docker containers needed.

## No External Delivery

Reports are stored in the local database and `runs/` directory. No Feishu/WeCom/WeChat/Telegram/Discord/email posting occurs.

## Quality Checking (R1-11)

After running a daily report, you can check its quality:

```bash
make report-quality-check        # Check latest daily report quality
make report-quality-review       # Write Markdown review artifact
make daily-report-with-quality   # Run daily report then check quality
```

The quality checker is deterministic (no LLMs). It checks for required sections, evidence links, uncertainty, signal-vs-news distinction, and anti-patterns. Score ranges 0-100:

- 80-100%: intelligence briefing quality
- 60-79%: acceptable but needs improvement
- 40-59%: closer to news dump or incomplete
- 0-39%: tool log, raw dump, or failed run artifact

See `docs/21_daily_report_quality_rubric.md` for the full quality bar.
