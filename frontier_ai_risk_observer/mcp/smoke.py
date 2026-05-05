"""Local smoke checks for the MCP state-tool adapter.

This command does not require Hermes-Agent. Database-backed tools report a
controlled unavailable response if no local database is configured.
"""

from __future__ import annotations

import json

from frontier_ai_risk_observer.mcp import server


def main() -> None:
    """Run minimal import and tool smoke checks."""
    summary = server.risk_registry_summary()
    due = server.risk_registry_list_due_sources(limit=3)
    seen = server.risk_raw_item_seen_check(url="https://example.com/offline-smoke")
    payload = {
        "registry_summary_ok": summary.get("ok") is True,
        "due_sources_count": due.get("count"),
        "seen_check_controlled": "ok" in seen,
        "seen_check_ok": seen.get("ok"),
        "seen_check_error_type": seen.get("error_type"),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    if not payload["registry_summary_ok"] or payload["due_sources_count"] is None:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
