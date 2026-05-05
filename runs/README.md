# Run Artifacts

This directory stores output from Hermes-led dry runs and automated daily reports.

## Structure

- `r1_08/` — R1-08 automated Hermes daily dry run artifacts (gitignored)
- `r1_09b/` — R1-09B helper-assisted Hermes dry run artifacts (gitignored)
- `daily/` — R1-10 automated daily report artifacts (gitignored)
- `interactive/` — R1-10 interactive daily report artifacts (gitignored)

Each run creates a timestamped subdirectory:

```
daily/YYYYMMDD_HHMMSS/
  prompt.md           — exact prompt sent to Hermes
  hermes_stdout.log   — captured stdout
  hermes_stderr.log   — captured stderr
  hermes_output.md    — combined output
  daily_report.md     — final daily report
  summary.md          — compact run summary
```

## Note

Run artifacts are excluded from version control by default.
If sanitized examples need to be committed later, that must be done explicitly.
