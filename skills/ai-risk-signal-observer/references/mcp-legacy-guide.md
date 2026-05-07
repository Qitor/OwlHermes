# MCP Legacy Guide

## Overview

OwlHermes originally used MCP (Model Context Protocol) as its primary integration surface with Hermes-Agent. Starting with R1-15, the Hermes plugin architecture is preferred.

MCP tools remain available as a **legacy fallback** for:
- Debugging plugin issues
- Environments where plugin loading is not yet configured
- Backward compatibility during transition

## MCP vs Plugin

| Aspect | Plugin (Preferred) | MCP (Legacy) |
|--------|-------------------|--------------|
| Surface | `owl_*` facade tools | `risk_*` individual tools |
| Registration | Hermes plugin system | MCP server (stdio) |
| Tool count | 5 facade tools | 23 individual tools |
| Action dispatch | `action` parameter | Separate function per tool |
| Config | `~/.hermes/config.yaml` plugins section | MCP server in config |
| State | Stateless per call | MCP server with session |

## When to Use MCP

- Plugin tools are unavailable (not installed or not enabled)
- Plugin tool returns an error
- Debugging backend service issues

## MCP Server Configuration

```yaml
# In ~/.hermes/config.yaml (legacy section)
mcp_servers:
  ai_risk_observer:
    command: .venv/bin/python
    args: ["-m", "frontier_ai_risk_observer.mcp.server"]
    env:
      DATABASE_URL: "sqlite:///./.local/risk_observer_dryrun.db"
      SOURCE_REGISTRY_DIR: "/path/to/source_registry"
    tools:
      include:
        - risk_raw_item_seen_check
        - risk_raw_item_store
        # ... (23 tools total)
```

## MCP Tool Quirks

See `references/source-reliability.md` for known MCP backend failure patterns including:
- `risk_raw_item_store` NoneType cascade failure
- Auto-disconnect after consecutive failures
- UUID format requirements
- Inconsistent field naming across tools
