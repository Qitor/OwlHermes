# R1-11C: Two-Phase Daily Report Finalization

## Why Two-Phase Finalization

The daily report system has a quality loop (R1-11) and model tiering (R1-11B), but Hermes runs can still time out during the collection/research phase. When Hermes times out, the system is left without a final `daily_report.md` — only timeout logs and partial DB state.

Two-phase finalization ensures that `make daily-report` **always** produces a readable Chinese daily report, even if the collection phase times out.

## Phase A: Collection/Research

**Purpose**: Let Hermes act as the AI risk observer.

- Select sources
- Use helper preview where useful
- Browse selected sources
- Store raw items, signals, source runs
- Write and store a digest

**Behavior**:

- Uses `prompts/daily_report_prompt.md`
- Default timeout: 1800 seconds (30 minutes)
- Captures stdout/stderr on normal exit and timeout
- All partial Hermes work is preserved

## Phase B: Finalize/Report

**Purpose**: Produce the final Chinese daily report using already collected DB state.

Phase B runs automatically if Phase A:

- Times out
- Exits non-zero after doing some DB work
- Does not store a new digest
- Does not produce a readable `daily_report.md`
- Produces output that looks like logs or incomplete tool traces

Phase B is skipped only if Phase A clearly completed.

**Behavior**:

- Uses `prompts/daily_report_finalize_prompt.md`
- Default timeout: 600 seconds (10 minutes)
- **Does not browse the web**
- **Does not fetch URLs**
- **Does not call helper preview with fetch=true**
- **Does not select new sources**
- Uses only DB/MCP search/state tools
- Writes and stores the final Chinese report
- Mentions if Phase A timed out or only partially completed

## When Finalize Runs

| Condition | Phase B? |
|-----------|----------|
| Phase A timed out | Yes |
| Phase A exited non-zero | Yes |
| No new digest stored | Yes |
| `daily_report.md` missing or empty | Yes |
| Report is logs, not Chinese sections | Yes |
| Phase A produced complete Chinese report with digest | No |
| `--skip-finalize` flag | No |
| `--force-finalize` flag | Yes (always) |

## DB State Snapshots

The runner captures before/after snapshots:

- **Before Phase A**: `state_before.json`
- **After Phase A**: `state_after_phase_a.json`
- **After Phase B**: `state_after_phase_b.json`

Each snapshot contains:

- Raw item count
- Source run count
- Signal count
- Digest count
- Latest digest details
- Recent raw items (last 20)
- Recent source runs (last 20)
- Recent signals (last 20)

Snapshots work with SQLite and do not require Hermes.

## Artifacts

For each run under `runs/daily/YYYYMMDD_HHMMSS/`:

| File | Contents |
|------|----------|
| `prompt.md` | Phase A prompt |
| `finalize_prompt.md` | Phase B prompt (if run) |
| `phase_a_stdout.log` | Phase A Hermes stdout |
| `phase_a_stderr.log` | Phase A Hermes stderr |
| `phase_a_output.md` | Phase A output as Markdown |
| `phase_b_stdout.log` | Phase B Hermes stdout (if run) |
| `phase_b_stderr.log` | Phase B Hermes stderr (if run) |
| `phase_b_output.md` | Phase B output (if run) |
| `phase_b_skipped.md` | Explanation if Phase B skipped |
| `daily_report.md` | Final Chinese report |
| `summary.md` | Full run summary |
| `state_before.json` | DB state before Phase A |
| `state_after_phase_a.json` | DB state after Phase A |
| `state_after_phase_b.json` | DB state after Phase B |

## Configuration

### CLI Arguments

```
--collection-timeout-seconds  Phase A timeout (default: 1800)
--finalize-timeout-seconds    Phase B timeout (default: 600)
--skip-finalize               Skip Phase B even if needed
--force-finalize              Force Phase B even if Phase A completed
--prompt-file                 Override Phase A prompt file
--finalize-prompt-file        Override Phase B prompt file
--quality-check               Run quality check after generation
```

### Makefile Targets

```bash
make daily-report                # Two-phase daily report
make daily-report-preflight      # Preflight checks
make daily-report-inspect        # Inspect latest run
make daily-report-with-quality   # Daily report + quality check
make daily-report-finalize       # Force finalize on latest run
make daily-report-debug          # Show latest run artifacts
```

## How Partial Output Is Captured

When Hermes times out, `subprocess.TimeoutExpired` provides partial stdout/stderr. The runner:

1. Decodes bytes to string (UTF-8, error-replace)
2. Saves partial output to phase-specific log files
3. Writes partial output to `daily_report.md`
4. Marks Phase A as timed_out in summary

## Completion Detection

A completed report requires:

- Non-empty `daily_report.md`
- Chinese content (>20 CJK characters)
- At least one report section pattern (信号, 一句话总览, etc.)
- Not predominantly tool-call logs

The detection is deterministic and does not use LLMs.

## Quality Check Integration

After report generation, `--quality-check` runs the deterministic quality checker. The quality score is included in the summary. Quality check is soft — `make daily-report` does not fail solely due to low quality score.

## Why This Remains Hermes-Led

- Phase A: Hermes does all research, collection, and initial report writing
- Phase B: Hermes writes the final report based on DB state
- Python orchestrates, captures logs, and saves artifacts — but never writes report content

## No External Dependencies

- No Docker required
- No Postgres required (SQLite dry-run DB)
- No external delivery
- No website updates
- No cron configuration
