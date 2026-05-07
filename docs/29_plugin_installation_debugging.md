# R1-15: Plugin Installation & Debugging Guide

## Installation

### Project-local install (recommended)

```bash
make plugin-install-local
```

This creates a symlink from `.hermes/plugins/owlhermes/` to the Python package. Requires `HERMES_ENABLE_PROJECT_PLUGINS=true` for Hermes to discover project-local plugins.

### Copy-based install

```bash
make plugin-install-local-copy
```

Copies files instead of symlinking. Useful if symlinks don't work in your setup.

### Manual install

```bash
python scripts/install_hermes_plugin.py --mode symlink
python scripts/install_hermes_plugin.py --mode copy
python scripts/install_hermes_plugin.py --project-local  # install to project-local
python scripts/install_hermes_plugin.py --dry-run        # preview only
```

## Enabling the Plugin

### Via CLI

```bash
hermes plugins enable owlhermes
```

### Via config.yaml

Add to `~/.hermes/config.yaml`:

```yaml
plugins:
  enabled:
    - owlhermes
```

### Project-local plugins

If using `.hermes/plugins/` inside the project directory:

```bash
export HERMES_ENABLE_PROJECT_PLUGINS=true
```

Or add to your shell profile.

## Smoke Tests

```bash
make plugin-smoke          # Verify plugin package, schemas, facades work
make skill-smoke           # Verify SKILL.md and reference files
make hermes-plugin-smoke   # Verify Hermes can discover the plugin
make mcp-smoke             # Verify legacy MCP still works
```

## Running Daily Reports

```bash
# Plugin-first (preferred)
make daily-report-plugin

# With live vault
OBSIDIAN_VAULT_PATH=~/Documents/airo make daily-report-live-vault-plugin

# Legacy MCP mode
make daily-report

# Force specific interface
python scripts/daily_report.py --run --interface plugin
python scripts/daily_report.py --run --interface mcp
python scripts/daily_report.py --run --interface auto
```

## Troubleshooting

### Plugin not found by Hermes

1. Check plugin directory exists: `ls .hermes/plugins/owlhermes/`
2. Check `plugin.yaml` exists inside it
3. Check `__init__.py` exists and imports `register`
4. Verify `HERMES_ENABLE_PROJECT_PLUGINS=true` is set (for project-local plugins)
5. Run `hermes plugins list` to see enabled plugins
6. Check `~/.hermes/config.yaml` has `plugins.enabled: [owlhermes]`

### `make plugin-smoke` fails

1. Check `.venv` is set up: `make install`
2. Check `frontier_ai_risk_observer` package is installed: `.venv/bin/python -c "from frontier_ai_risk_observer.hermes_plugin import __version__; print(__version__)"`
3. Check DATABASE_URL is set or defaults to SQLite dry-run DB

### `make hermes-plugin-smoke` shows warnings

Warnings about "owlhermes not in config" are expected before enabling. Run:

```bash
hermes plugins enable owlhermes
```

Or manually edit `~/.hermes/config.yaml`.

### Database errors

Plugin tools need DATABASE_URL. Default is `sqlite:///./.local/risk_observer_dryrun.db`. Initialize:

```bash
make db-init-dryrun
```

### Interface mode not working

Check `OWL_HERMES_INTERFACE_MODE` env var:

```bash
echo $OWL_HERMES_INTERFACE_MODE
# Valid values: plugin, mcp, both (default)
```

### Live vault not writing

1. Check `OBSIDIAN_LIVE_LOGGING_ENABLED=true` is set
2. Check `OBSIDIAN_VAULT_PATH` points to an existing directory
3. When disabled, live vault tools return `live_vault_enabled: false` (this is normal)

### `/owl` command not working

The `/owl` slash command is only available inside a Hermes session with the plugin enabled. It won't work outside Hermes.

## Architecture Decision: Why 5 Tools Instead of 18+

The original MCP surface has 18+ individual tool functions (`risk_raw_item_seen_check`, `risk_raw_item_store`, etc.). The plugin uses 5 action-based facade tools because:

1. Hermes plugin tool registration is cleaner with fewer, composable tools
2. Action dispatch pattern allows adding new actions without tool registration changes
3. Each tool maps to a domain (state, discovery, vault, quality, export)
4. Easier for Hermes to manage tool permissions and descriptions
5. MCP tools still available as fallback via `OWL_HERMES_INTERFACE_MODE=mcp`
