"""OwlHermes plugin registration for Hermes-Agent.

This module defines the `register(ctx)` function that Hermes calls when
loading the OwlHermes plugin. It registers:

- 5 facade tools (owl_risk_state, owl_risk_discovery, owl_live_vault,
  owl_report_quality, owl_obsidian_export)
- 1 slash command (/owl)

Skills are referenced via the skills/ external_dirs mechanism, not registered
through the plugin API (ctx.register_skill is not available in current Hermes).

Usage:
  1. Install plugin: make plugin-install-local
  2. Enable in ~/.hermes/config.yaml: plugins.enabled: [owlhermes]
  3. Or: hermes plugins enable owlhermes
"""

from __future__ import annotations

from typing import Any

from frontier_ai_risk_observer.hermes_plugin.cli_commands import _handle_owl_command
from frontier_ai_risk_observer.hermes_plugin.manifest import TOOLSET
from frontier_ai_risk_observer.hermes_plugin.schemas import ALL_PLUGIN_SCHEMAS
from frontier_ai_risk_observer.hermes_plugin.tools import TOOL_REGISTRATIONS


def register(ctx: Any) -> None:
    """Register all OwlHermes tools and commands with Hermes.

    Called once by the Hermes plugin loader when the plugin is enabled.
    """
    # Register tools
    for tool_name, _schema_override, handler in TOOL_REGISTRATIONS:
        # Find matching schema
        schema = _find_schema(tool_name)
        ctx.register_tool(
            name=tool_name,
            toolset=TOOLSET,
            schema=schema,
            handler=handler,
            description=schema.get("description", ""),
        )

    # Register slash command
    ctx.register_command(
        "owl",
        handler=_handle_owl_command,
        description="OwlHermes status, health, and tool listing",
    )


def _find_schema(tool_name: str) -> dict[str, Any]:
    """Find the schema dict for a tool by name."""
    for schema in ALL_PLUGIN_SCHEMAS:
        if schema.get("name") == tool_name:
            return schema
    return {
        "name": tool_name,
        "description": "",
        "parameters": {"type": "object", "properties": {}},
    }
