# R1-07: Hermes-Agent Integration Smoke Test

This document describes how to verify that a real local Hermes-Agent installation can connect to this repository's MCP server and skill.

## Step 1: External Hermes Install

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
source ~/.zshrc   # or source ~/.bashrc for bash
hermes setup
hermes doctor
```

Hermes-Agent must remain external. Do not clone it into this repository.

## Step 2: Install Repo MCP Optional Dependency

```bash
cd /path/to/this/repo
make install                    # creates .venv and installs dev deps
.venv/bin/python -m pip install -e ".[mcp]"  # installs Python MCP SDK
```

## Step 3: Run Local Checks

```bash
make validate-registries
make mcp-smoke
make hermes-smoke
```

All three must pass before proceeding.

## Step 4: Apply or Manually Edit `~/.hermes/config.yaml`

### Option A: Auto-apply

```bash
make hermes-smoke-apply
```

This creates a timestamped backup of `~/.hermes/config.yaml`, then adds the MCP server block and skills external dir.

### Option B: Manual edit

Add the following to `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  ai_risk_observer:
    command: "/path/to/repo/.venv/bin/python"
    args:
      - "-m"
      - "frontier_ai_risk_observer.mcp.server"
    timeout: 120
    enabled: true
    tools:
      include:
        - risk_registry_summary
        - risk_registry_list_due_sources
        - risk_registry_get_source
        - risk_raw_item_seen_check
        - risk_raw_item_store
        - risk_raw_item_search
        - risk_raw_item_duplicate_candidates
        - risk_source_run_record
        - risk_signal_store
        - risk_signal_search
        - risk_digest_store
        - risk_digest_search
        - risk_benchmark_observation_store
      prompts: false
      resources: false
    env:
      SOURCE_REGISTRY_DIR: "/path/to/repo/source_registry"

skills:
  external_dirs:
    - "/path/to/repo/skills"
```

Replace `/path/to/repo` with the actual absolute path to this repository.

## Step 5: Reload Hermes MCP

If Hermes is already running, reload MCP config:

- In Hermes chat, type `/reload-mcp`
- Or restart Hermes

## Step 6: Manual Hermes Smoke Prompts

Launch `hermes chat` and run these prompts one at a time:

### Prompt A — Tool Discovery

```
Use the ai-risk-signal-observer skill in smoke-test mode. Do not browse the web. Do not fetch URLs. Tell me which risk observer MCP tools are available.
```

**Expected**: Hermes reports that `ai_risk_observer` MCP tools are available, listing at least `risk_registry_summary`, `risk_registry_list_due_sources`, and `risk_raw_item_seen_check`.

### Prompt B — Registry Summary and Due Sources

```
Use the ai-risk-signal-observer skill in smoke-test mode. Do not browse the web. Call the risk registry summary tool and list due sources with limit 5.
```

**Expected**: Hermes calls `risk_registry_summary` (returns group counts), then calls `risk_registry_list_due_sources(limit=5)` and lists the results.

### Prompt C — Fake URL Seen-Check

```
Use the ai-risk-signal-observer skill in smoke-test mode. Do not browse the web. Check whether this fake URL has been seen before: https://example.com/hermes-risk-observer-smoke?utm_source=test
```

**Expected**: Hermes calls `risk_raw_item_seen_check(url="https://example.com/hermes-risk-observer-smoke?utm_source=test")`. Without a database, this returns `{"ok": true, "seen": false}` or a controlled database_unavailable response.

## What This Verifies

- Hermes loads the `ai-risk-signal-observer` skill from `skills.external_dirs`
- Hermes discovers the `ai_risk_observer` MCP server via stdio
- Hermes sees allowlisted `risk_*` tools
- Hermes can call `risk_registry_summary`, `risk_registry_list_due_sources`, `risk_raw_item_seen_check`
- Hermes does not fetch external sources during smoke test
- Hermes does not generate production digest

## CLI Differences from Documented Commands

During R1-07 testing, we discovered that `hermes mcp add` with `--args "-m" "module.name"` fails because Hermes' argparse intercepts `-m` as its own flag. The workaround is to edit `~/.hermes/config.yaml` directly (which `make hermes-smoke-apply` does via PyYAML).

Verified with Hermes Agent v0.12.0 (2026.4.30):
- `hermes mcp list` works correctly
- `hermes mcp test <name>` works correctly
- `hermes skills list` shows external skills with `Source: local`
- `hermes -z "prompt" --yolo` can run one-shot prompts for automated testing

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `hermes` not found on PATH | Install externally (Step 1) |
| MCP SDK not installed | `pip install -e ".[mcp]"` in repo .venv |
| MCP server fails to start | Check `.venv/bin/python -m frontier_ai_risk_observer.mcp.server` |
| Hermes doesn't see MCP tools | Run `/reload-mcp` or restart Hermes |
| `hermes mcp test` fails | Check `SOURCE_REGISTRY_DIR` env var in MCP config |

## Next Step

After R1-07 passes, proceed to R1-08: Hermes-led daily dry run with 3-5 real sources, seen-check, raw item storage, and a non-production Chinese digest.
