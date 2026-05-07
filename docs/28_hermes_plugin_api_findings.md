# R1-15: Hermes Plugin API Findings

## Confirmed API

### Plugin Directory Structure

Each plugin lives in a directory containing:
- `plugin.yaml` — manifest
- `__init__.py` — must define `register(ctx)`

### Plugin Sources (priority order, later overrides earlier)

1. **Bundled** — `<hermes-agent>/plugins/<name>/`
2. **User** — `~/.hermes/plugins/<name>/`
3. **Project** — `./.hermes/plugins/<name>/` (requires `HERMES_ENABLE_PROJECT_PLUGINS=true`)
4. **Pip** — packages exposing `hermes_agent.plugins` entry-point group

### plugin.yaml Manifest Fields

```yaml
name: string          # Required
version: string       # Optional
description: string   # Optional
author: string        # Optional
kind: string          # "standalone" (default) | "backend" | "exclusive" | "platform"
requires_env: list    # Optional list of env var names or {name, description} dicts
provides_tools: list  # Optional list of tool names
provides_hooks: list  # Optional list of hook names
key: string           # Optional registry key (defaults to name)
```

### register(ctx) Function

Must be defined in `__init__.py`. Receives a `PluginContext` instance.

### PluginContext API

```python
ctx.register_tool(
    name: str,           # Tool name (e.g. "owl_risk_state")
    toolset: str,        # Toolset grouping (e.g. "owlhermes")
    schema: dict,        # JSON Schema for tool parameters
    handler: Callable,   # Handler: (args: dict, **kwargs) -> str (JSON string)
    check_fn: Callable | None = None,  # Availability check: () -> bool
    requires_env: list | None = None,  # Env vars required
    is_async: bool = False,
    description: str = "",
    emoji: str = "",
)

ctx.register_hook(
    hook_name: str,      # One of VALID_HOOKS
    handler: Callable,   # Hook handler
)

ctx.register_cli_command(
    name: str,
    help: str,
    setup_fn: Callable,  # Receives argparse subparser
    handler_fn: Callable | None = None,
    description: str = "",
)

ctx.register_command(
    name: str,           # Slash command name (e.g. "owl")
    handler: Callable,   # (raw_args: str) -> str | None
    description: str = "",
    args_hint: str = "",
)
```

### Tool Schema Format

JSON Schema with `name`, `description`, and `parameters`:

```python
MY_TOOL_SCHEMA = {
    "name": "my_tool",
    "description": "What the tool does",
    "parameters": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["action1", "action2"]},
            "payload": {"type": "object"},
        },
        "required": ["action"],
    },
}
```

### Tool Handler Signature

```python
def handle_my_tool(args: dict, **kwargs) -> str:
    action = args.get("action")
    # ... handle action ...
    return json.dumps({"ok": True, "result": ...})
```

Returns a JSON string. Use `tool_result(data)` and `tool_error(message)` helpers from `tools.registry`.

### Plugin Enable/Install Flow

1. `hermes plugins install <git-url>` — install from Git
2. For local plugins: symlink or copy to `~/.hermes/plugins/<name>/`
3. `hermes plugins enable <name>` — add to `plugins.enabled` in config
4. Config location: `~/.hermes/config.yaml` → `plugins.enabled: [owlhermes]`

### Project-Local Plugins

- Place in `./.hermes/plugins/<name>/`
- Requires `HERMES_ENABLE_PROJECT_PLUGINS=true` env var
- Useful for repo-local development

## Chosen Layout

```text
frontier_ai_risk_observer/hermes_plugin/
  __init__.py         # Package init, version
  plugin.py           # register(ctx) function
  tools.py            # Tool handlers
  schemas.py          # Tool JSON schemas
  facades.py          # High-level action routing, reuses services
  hooks.py            # Optional hooks (minimal/no-op initially)
  cli_commands.py     # Optional CLI commands
  skills.py           # Bundled skill registration
  manifest.py         # Python manifest representation

.hermes/plugins/owlhermes/
  plugin.yaml         # Hermes plugin manifest
  __init__.py         # Thin wrapper, imports from hermes_plugin
  skills/
    ai-risk-signal-observer/
      SKILL.md
      references/...
```

## Uncertainties

- **Skill bundling via plugin**: Hermes plugins register tools but skill registration API (`ctx.register_skill`) was not found in the PluginContext class. Skills are likely managed via the `skills/` external_dirs mechanism. The plugin can reference skill paths but may not be able to auto-register them.
- **Handler kwargs**: Tool handlers receive `(args: dict, **kwargs)`. The kwargs may include `parent_agent`, `task_id`, etc. but this isn't documented for plugin authors — just pass through.
- **Return format**: Handlers return JSON strings. The `tool_result()` and `tool_error()` helpers are internal to Hermes, not available to external plugins. Our plugin should return `json.dumps(...)` directly.

## Confirmed vs Inferred

| Item | Status |
|------|--------|
| plugin.yaml + __init__.py required | Confirmed |
| register(ctx) entry point | Confirmed |
| ctx.register_tool API | Confirmed |
| ctx.register_hook API | Confirmed |
| ctx.register_command API | Confirmed |
| ctx.register_cli_command API | Confirmed |
| Tool schema format (JSON Schema) | Confirmed |
| Handler returns JSON string | Confirmed |
| plugins.enabled in config.yaml | Confirmed |
| ~/.hermes/plugins/ user directory | Confirmed |
| Project plugins require env var | Confirmed |
| ctx.register_skill | NOT FOUND — skills use external_dirs |
| tool_result/tool_error available to plugins | Inferred — internal, use json.dumps |
