# R1-09B Progress Report: Helper-Assisted Hermes Dry Run

**Date:** 2026-05-04
**Status:** Complete
**Previous round:** R1-09 (Scrapling Source Reliability Helpers)

---

## R1-09B Objective

Run a controlled, automated, non-production Hermes dry run that verifies Hermes can actually use the R1-09 helper layer end-to-end.

---

## Delivered Items

### 1. Refined Prompt

`prompts/r109_hermes_helper_assisted_dry_run_prompt.md` — fully self-contained, specifies:
- Use `ai-risk-signal-observer` skill in helper-assisted dry-run mode
- Non-production, no external posting, no cron, no website
- Step 1: `risk_source_health_summary`
- Step 2: `risk_registry_list_due_sources`, select 3-5 sources (prefer helper-enabled)
- Step 3: `risk_discovery_helper_preview` with `fetch=true` for allowlisted URLs only
- Step 4: Triage candidates (seen-check → store → signal)
- Step 5: `risk_source_run_record` with helper metadata
- Step 6: `risk_digest_store` with status `dry_run`
- Digest must include: helper usage, source health, R1-08 comparison
- Explicit: seen-check before store, candidates are NOT risk judgments

### 2. R1-09B Hermes Runner

`scripts/r109b_run_hermes.py` — analogous to R1-08 runner with:
- `--preflight`: Hermes check, registry validation, source health, helper preview, MCP smoke, DB check, prompt file
- `--run`: Full automated Hermes dry run (15 min timeout)
- `--inspect`: Post-run state inspection
- Saves artifacts under `runs/r1_09b/<timestamp>/`
- Does NOT reset DB by default (keeps R1-08 data for seen-check/dedup testing)

### 3. R1-09B State Inspector

`scripts/r109b_inspect_state.py` — extends R1-08 inspector with:
- Helper-assisted source run detection (`helper_used` in metadata)
- Seen/dedup stats (items seen more than once)
- `seen_count` in raw item display
- Works with SQLite dry-run DB

### 4. Makefile Targets

| Target | Purpose |
|--------|---------|
| `make r109b-dry-run-preflight` | Full preflight (registries + health + helpers + MCP + Hermes + DB + runner preflight) |
| `make r109b-run-hermes` | Launch helper-assisted Hermes dry run |
| `make r109b-inspect-state` | Inspect dry-run DB after run |

### 5. SKILL.md Updated

Added **helper-assisted dry-run mode** with clear rules:
- Call `risk_source_health_summary` first
- Call `risk_discovery_helper_preview` for helper-enabled sources
- `fetch=true` only for explicitly configured allowlisted URLs
- Candidates are NOT final risk judgments
- Seen-check before store
- Helper usage metadata in source runs
- Digest includes helper usage and source reliability

### 6. Documentation

`docs/19_r109b_helper_assisted_hermes_dry_run.md` — purpose, differences from R1-08/R1-09, success criteria, troubleshooting (0 candidates, Hermes not calling tools, noisy Scrapling output)

### 7. Tests

`tests/test_r109b_dry_run.py` — 42 tests covering:
- Prompt references all 7 required MCP tools
- Prompt says non-production, no external posting, candidates not judgments, seen-check before store
- Prompt mentions selected sources, fetch=true allowlisted, dry_run status, Chinese digest
- Runner supports --preflight, locates prompt, uses r1_09b/ dir, doesn't reset DB, has timeout, saves artifacts, uses --yolo
- Inspector uses SQLite, shows table counts, helper-assisted runs, seen_count, redacts credentials, works with empty DB
- Docs mention no Docker, no production delivery, Makefile commands, artifact location, helper fetch empty
- Makefile has r109b targets
- Gitignore has runs/r1_09b/

### 8. Config/Git Updates

- `.gitignore`: Added `runs/r1_09b/`
- `runs/README.md`: Updated with R1-09B structure
- `README.md`: Added R1-09B section
- `CLAUDE.md`: Updated with 15 MCP tools, helpers layer, new Makefile commands, R1-09B status

---

## Hermes Run Results

**Run timestamp:** 20260504T212018
**Hermes exit code:** 0 (success)
**Run directory:** `runs/r1_09b/20260504T212018/`

### Sources Checked

| Source | Helper Type | Candidates | Stored |
|--------|-------------|-----------|--------|
| anthropic_news | scrapling_official_page | 7 | 3 |
| apollo_blog | scrapling_official_page | 0 | 0 |
| arxiv_ai_safety | arxiv_query (fell back to browser) | 1 | 1 |
| techcrunch_ai | rss | 15→5 filtered | 4 |
| axrp | scrapling_official_page | 0 | 0 |

### MCP Tools Called by Hermes

1. `risk_source_health_summary` — YES
2. `risk_discovery_helper_preview` — YES (for multiple sources)
3. `risk_registry_list_due_sources` — YES
4. `risk_raw_item_seen_check` — YES
5. `risk_raw_item_store` — YES (8 new items)
6. `risk_source_run_record` — YES (5 source runs)
7. `risk_signal_store` — YES (3 new signals)
8. `risk_digest_store` — YES (status: dry_run)

### Signals Stored (3 new, 4 total in DB)

1. **前沿实验室趋同于限制高风险模型访问** (severity 4/5) — OpenAI restricts GPT-5.5 Cyber after criticizing Anthropic for limiting Mythos
2. **五角大楼在机密网络部署AI** (severity 4/5) — DOD contracts with Nvidia/Microsoft/AWS
3. **Open Problems in Frontier AI Risk Management** (severity 3/5) — 81-page systematic review from Oxford/Cornell/MIT

### Digest

Stored with status `dry_run`, date 2026-05-04, timezone Asia/Shanghai. Contains Chinese digest with helper usage report and R1-08 comparison.

### Raw Items

13 total in DB (5 from R1-08, 8 new from R1-09B). All new items from R1-09B are `status: new`, `seen_count: 1`.

### Source Runs

9 total (4 from R1-08, 5 new from R1-09B). R1-09B runs: anthropic_news, apollo_blog, arxiv_ai_safety, techcrunch_ai, axrp.

---

## R1-08 vs R1-09B Comparison

| Metric | R1-08 | R1-09B | Change |
|--------|-------|--------|--------|
| Sources checked | 4 | 5 | +1 |
| Helper tools used | 0 | 5 | New capability |
| Raw items stored | 5 | 8 | +3 |
| Duplicate/seen items | 0 | 0 | Same |
| Signals stored | 1 | 3 (+1 from R1-08 = 4 total) | +2 new |
| Digest stored | 1 (dry_run) | 1 (dry_run) | Replaced |
| Max signal severity | 3/5 | 4/5 | Higher |
| Broad search needed | Yes (all sources) | Partial (helpers for 5/5) | Reduced |
| Anthropic URL extraction | Manual, some 404s | Helper-assisted, successful | Improved |
| Stale source tracking | Not reported | Reported (AXRP, apollo_blog) | Now tracked |

---

## Validation Results

| Check | Result |
|-------|--------|
| Registry validation | PASS (23 sources, 6 podcasts, 6 events, 8 benchmarks) |
| Source health | PASS (4 known issues, 2 human review, 0 invalid URLs) |
| Preview helpers | PASS (6 helpers configured) |
| R1-09 helper preflight | PASS |
| MCP smoke | PASS |
| Hermes smoke | PASS |
| DB check | PASS |
| R1-09B preflight | PASS (7/7 checks) |
| R1-09B Hermes run | SUCCESS (exit code 0) |
| Test suite | **158/158 passed** |
| Lint (ruff) | All checks passed |
| Compile check | OK |

---

## Remaining Source Reliability Issues

| Source | Issue |
|--------|-------|
| arXiv API | Rate-limited during R1-09B; fell back to browser search |
| AXRP | No RSS feed, Scrapling returned 0 candidates; requires human review |
| apollo_blog | Updated infrequently; 0 candidates from helper |
| ai_safety_summit_series | Stale 2023 URL; needs manual page identification |
| TechCrunch | Web page timeout; RSS feed worked as fallback |

---

## Files Created or Changed

### Created
- `scripts/r109b_run_hermes.py`
- `scripts/r109b_inspect_state.py`
- `docs/19_r109b_helper_assisted_hermes_dry_run.md`
- `tests/test_r109b_dry_run.py`
- `runs/r1_09b/20260504T212018/` (prompt.md, hermes_stdout.log, hermes_stderr.log, hermes_output.md, summary.md)

### Changed
- `prompts/r109_hermes_helper_assisted_dry_run_prompt.md` — refined per spec
- `Makefile` — added r109b-dry-run-preflight, r109b-run-hermes, r109b-inspect-state
- `.gitignore` — added runs/r1_09b/
- `runs/README.md` — updated with R1-09B structure
- `skills/ai-risk-signal-observer/SKILL.md` — added helper-assisted dry-run mode
- `README.md` — added R1-09B section
- `CLAUDE.md` — updated MCP tools count, helpers layer, new commands, implementation status

---

## Recommended Next Task

Helper-assisted discovery is working. The main remaining gap is **helper coverage**: only 5/43 entries have helpers. Two directions:

1. **R1-10: Minimal website/API view** — expose signals, digests, source health via a web interface. The helper-assisted pipeline is adequate for daily signal collection.

2. **R1-09C: Helper coverage expansion** — add RSS feeds for podcasts (Dwarkesh, 80k Hours, etc.), add sitemap helpers for benchmarks, add Scrapling helpers for DeepMind/OpenAI/UK AISI blogs. This would reduce the number of sources requiring manual browsing from ~38 to ~15.

**Recommendation:** R1-10 (website) — the pipeline is functional and produces real signals. A website would make the output visible and provide a foundation for production delivery. Helper coverage can be expanded incrementally in future rounds.
