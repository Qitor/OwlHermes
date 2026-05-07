"""OwlHermes plugin CLI commands — optional.

Registers `/owl` slash command for quick status checks within Hermes sessions.
"""

from __future__ import annotations


def _handle_owl_command(raw_args: str) -> str:
    """Handle /owl slash command in Hermes sessions.

    Subcommands:
      status   — show OwlHermes plugin status
      health   — run source health check
      tools    — list available plugin tools
    """
    args = raw_args.strip().split()
    sub = args[0] if args else "status"

    if sub in ("status", ""):
        return _owl_status()
    if sub == "health":
        return _owl_health()
    if sub == "tools":
        return _owl_tools()

    return f"Unknown subcommand: {sub}\nUsage: /owl [status|health|tools]"


def _owl_status() -> str:
    """Show OwlHermes plugin status."""
    import os
    lines = ["=== OwlHermes Plugin Status ==="]
    lines.append("Version: 0.1.0")
    tools = [
        "owl_risk_state", "owl_risk_discovery", "owl_live_vault",
        "owl_report_quality", "owl_obsidian_export",
    ]
    lines.append(f"Tools: {', '.join(tools)}")
    db_url = os.getenv("DATABASE_URL", "sqlite:///./.local/risk_observer_dryrun.db")
    lines.append(f"Database: {db_url.split('/')[-1]}")
    vault_path = os.getenv("OBSIDIAN_VAULT_PATH", "(not set)")
    lines.append(f"Vault: {vault_path}")
    live = os.getenv("OBSIDIAN_LIVE_LOGGING_ENABLED", "false")
    lines.append(f"Live vault: {'enabled' if live.lower() in ('true', '1', 'yes') else 'disabled'}")
    return "\n".join(lines)


def _owl_health() -> str:
    """Run source health check."""
    try:
        from frontier_ai_risk_observer.services.source_health import source_health_summary
        health = source_health_summary()
        ok = health.get("ok", False)
        status = "OK" if ok else "ISSUES"
        invalid = health.get("invalid_urls_count", 0)
        needs_review = health.get("requires_human_review_count", 0)
        return f"Source health: {status} | Invalid URLs: {invalid} | Needs review: {needs_review}"
    except Exception as exc:
        return f"Health check failed: {exc}"


def _owl_tools() -> str:
    """List available plugin tools."""
    tools = [
        ("owl_risk_state", "State ops (seen_check, store_raw_item, ...)"),
        ("owl_risk_discovery", "Discovery (source_health, list_due_sources, ...)"),
        ("owl_live_vault", "Live vault (start_run, append_event, ...)"),
        ("owl_report_quality", "Quality (check_report, review_queue_summary, ...)"),
        ("owl_obsidian_export", "Export (export_latest, dry_run, inspect, ...)"),
    ]
    lines = ["=== OwlHermes Plugin Tools ==="]
    for name, desc in tools:
        lines.append(f"  {name}: {desc}")
    return "\n".join(lines)
