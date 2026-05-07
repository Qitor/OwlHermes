"""Tool handlers for OwlHermes Hermes plugin.

Each handler receives (args: dict, **kwargs) and returns a JSON string.
Delegates to facade functions for actual logic.
"""

from __future__ import annotations

import json
from typing import Any

from frontier_ai_risk_observer.hermes_plugin.facades import (
    owl_live_vault,
    owl_obsidian_export,
    owl_report_quality,
    owl_risk_discovery,
    owl_risk_state,
)


def handle_owl_risk_state(args: dict[str, Any], **kwargs: Any) -> str:
    """Handle owl_risk_state tool calls."""
    action = args.get("action", "")
    payload = args.get("payload")
    result = owl_risk_state(action, payload)
    return json.dumps(result, ensure_ascii=False, default=str)


def handle_owl_risk_discovery(args: dict[str, Any], **kwargs: Any) -> str:
    """Handle owl_risk_discovery tool calls."""
    action = args.get("action", "")
    payload = args.get("payload")
    result = owl_risk_discovery(action, payload)
    return json.dumps(result, ensure_ascii=False, default=str)


def handle_owl_live_vault(args: dict[str, Any], **kwargs: Any) -> str:
    """Handle owl_live_vault tool calls."""
    action = args.get("action", "")
    payload = args.get("payload")
    result = owl_live_vault(action, payload)
    return json.dumps(result, ensure_ascii=False, default=str)


def handle_owl_report_quality(args: dict[str, Any], **kwargs: Any) -> str:
    """Handle owl_report_quality tool calls."""
    action = args.get("action", "")
    payload = args.get("payload")
    result = owl_report_quality(action, payload)
    return json.dumps(result, ensure_ascii=False, default=str)


def handle_owl_obsidian_export(args: dict[str, Any], **kwargs: Any) -> str:
    """Handle owl_obsidian_export tool calls."""
    action = args.get("action", "")
    payload = args.get("payload")
    result = owl_obsidian_export(action, payload)
    return json.dumps(result, ensure_ascii=False, default=str)


# Ordered list: (tool_name, schema, handler)
TOOL_REGISTRATIONS = [
    ("owl_risk_state", None, handle_owl_risk_state),
    ("owl_risk_discovery", None, handle_owl_risk_discovery),
    ("owl_live_vault", None, handle_owl_live_vault),
    ("owl_report_quality", None, handle_owl_report_quality),
    ("owl_obsidian_export", None, handle_owl_obsidian_export),
]
