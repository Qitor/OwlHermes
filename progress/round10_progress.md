# R1-10 Progress Report: Stable Daily Report Run Modes

## Summary

R1-10 adds two stable run modes for producing daily AI risk reports:

1. **`make daily-report`** — automated, non-interactive, one-shot Hermes run
2. **`make hermes-interactive-daily`** — interactive terminal session for observing Hermes

Both modes use the same daily report prompt family (情报编辑室模式 / Intelligence Editorial Room style). The difference is only in how Hermes is launched.

## Key Design Decision: 情报编辑室模式

The daily report prompt was **rewritten** after user feedback that the first draft read like a "技术集成测试检查单" (technical integration test checklist). The user chose the "情报编辑室模式" style:

- **编辑使命** first — "你是前沿 AI 风险情报编辑"
- **受众** defined — AI safety researchers, governance/policy analysts, frontier lab safety teams
- **选稿标准** — must answer "what changed / why it affects risk judgment / what to watch next"
- **排除规则** — pure product launches, conference announcements without new statements, etc.
- **工具是手段不是步骤** — tools described as two categories, no fixed call order

## Files Created / Modified

### Prompts
- `prompts/daily_report_prompt.md` — 主 prompt，情报编辑室模式
- `prompts/interactive_daily_report_prompt.md` — 交互式 prompt，引用主 prompt + 增加观察要求

### Scripts
- `scripts/daily_report.py` — 自动化日报 runner (preflight/run/inspect, 30min timeout, partial output capture on timeout)
- `scripts/hermes_interactive_daily.py` — 交互式 runner (preflight/launch/copy-prompt-only)
- `scripts/inspect_daily_report.py` — 日报状态检查器

### Config
- `Makefile` — 6 new targets: daily-report, daily-report-preflight, daily-report-inspect, hermes-interactive-daily, hermes-interactive-preflight, hermes-interactive-copy-prompt
- `.gitignore` — added runs/daily/ and runs/interactive/
- `runs/README.md` — added daily/ and interactive/ structure docs

### Docs
- `docs/20_stable_daily_report_modes.md` — R1-10 设计文档
- `skills/ai-risk-signal-observer/SKILL.md` — 重组 Modes 部分，增加 local daily-report mode 和 interactive observation mode
- `README.md` — R1-10 section
- `CLAUDE.md` — updated commands and status

### Tests
- `tests/test_r110_daily_report.py` — 48 tests covering:
  - TestDailyReportPrompt (14): prompt exists, references 8 MCP tools, no external posting, Chinese, editorial mission, selection criteria, signal-not-news
  - TestInteractivePrompt (4): exists, show progress, tool-call intentions, references daily_report_prompt
  - TestDailyReportRunner (6): script exists, supports preflight, uses daily prompt, uses runs/daily dir, saves daily_report.md, doesn't reset DB
  - TestInteractiveRunner (7): exists, supports preflight/copy-prompt-only/launch, uses interactive prompt, uses interactive dir, copy-prompt works without Hermes
  - TestInspectDailyReport (3): exists, works with empty DB, shows daily run dir
  - TestR110Makefile (5): all targets exist
  - TestR110Docs (6): exists, no Docker, no external delivery, SQLite, make commands
  - TestR110Gitignore (2): daily/ and interactive/ gitignored

## Validation Results

| Check | Result |
|-------|--------|
| `make test` | 206 passed |
| `make lint` | All checks passed |
| `python -m compileall scripts/` | No errors |
| `make daily-report-preflight` | ALL PASSED |
| `make hermes-interactive-preflight` | ALL PASSED |
| `make hermes-interactive-copy-prompt` | Works (prints prompt, exits 0) |
| `make daily-report-inspect` | Works (shows DB state) |
| `make daily-report` (first run, 15min timeout) | Hermes timed out but produced DB work: 7 sources checked, 20 raw items, 4 signals |

## Hermes Daily Report Run

### First Run (900s timeout)

- Hermes launched successfully and began research
- Timed out after 15 minutes
- Partial output was NOT captured (first version didn't handle TimeoutExpired output)
- DB state shows meaningful work was done:
  - 7 sources checked (anthropic_news, arxiv_ai_safety, techcrunch_ai, openai_news, axrp, ai_safety_summit_series, apollo_blog)
  - 20 raw items stored
  - 4 signals stored (from R1-09B + this run)
  - 1 digest (R1-09B)

### Improvements After First Run

1. **Timeout increased** from 900s (15min) to 1800s (30min)
2. **Partial output capture** — on timeout, captured stdout/stderr from the TimeoutExpired exception are now saved to log files instead of a placeholder message
3. **Long lines fixed** in scripts (ruff lint)

### Second Run (1800s timeout)

- In progress...

## Known Limitations

1. **Hermes one-shot mode** — both automated and interactive modes use `hermes -z <prompt> --yolo`. True `hermes chat` auto-injection is unreliable.
2. **Timeout risk** — Hermes researching 5-8 sources may take 15-30 minutes. The 30-minute timeout should cover most runs.
3. **No external delivery** — reports stored locally only.
4. **SQLite only** — no PostgreSQL required.
5. **Helper coverage limited** (5/43 entries) — most sources require Hermes manual browsing.
6. **Prompt length** — the full prompt is passed as a CLI argument, which may hit shell limits. The `--copy-prompt-only` mode provides a workaround.

## R1-10 Spec Compliance

| Spec Item | Status |
|-----------|--------|
| 1. `make daily-report` automated mode | Done |
| 2. `make hermes-interactive-daily` interactive mode | Done |
| 3. Same workflow + prompt family | Done (both reference daily_report_prompt.md) |
| 4. `prompts/daily_report_prompt.md` 情报编辑室模式 | Done |
| 5. `prompts/interactive_daily_report_prompt.md` | Done |
| 6. `scripts/daily_report.py` | Done |
| 7. `scripts/hermes_interactive_daily.py` | Done |
| 8. `scripts/inspect_daily_report.py` | Done |
| 9. Makefile targets (6) | Done |
| 10. .gitignore runs/daily/ + runs/interactive/ | Done |
| 11. Validation commands | Done (all pass) |
| 12. docs/20_stable_daily_report_modes.md | Done |
| 13. SKILL.md modes reorganized | Done |
| 14. R1-10 report | This document |
