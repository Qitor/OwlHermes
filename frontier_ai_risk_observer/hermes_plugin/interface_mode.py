"""Interface mode configuration for OwlHermes.

Controls whether plugin tools or MCP tools are the preferred integration surface.

OWL_HERMES_INTERFACE_MODE:
  - "plugin" — plugin tools preferred, MCP not used
  - "mcp"    — MCP tools only (legacy)
  - "both"   — both available, plugin preferred (default for transition)
"""

from __future__ import annotations

import os

VALID_MODES = frozenset({"plugin", "mcp", "both"})


def get_interface_mode() -> str:
    """Return the current interface mode from env var."""
    mode = os.getenv("OWL_HERMES_INTERFACE_MODE", "both").lower()
    if mode not in VALID_MODES:
        return "both"
    return mode


def is_plugin_preferred() -> bool:
    """Return True if plugin tools are preferred."""
    return get_interface_mode() in ("plugin", "both")


def is_mcp_available() -> bool:
    """Return True if MCP tools are available as fallback."""
    return get_interface_mode() in ("mcp", "both")
