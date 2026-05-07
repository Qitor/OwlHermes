"""Tool schemas for OwlHermes Hermes plugin.

Each schema follows the Hermes tool schema format:
  {name, description, parameters: {type: "object", properties, required}}

All tools use an action-based dispatch pattern with a required `action` field
and an optional `payload` object.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# owl_risk_state — Deterministic state operations
# ---------------------------------------------------------------------------

OWL_RISK_STATE_SCHEMA = {
    "name": "owl_risk_state",
    "description": (
        "Deterministic state operations for AI risk intelligence. "
        "Actions: seen_check, store_raw_item, search_raw_items, "
        "duplicate_candidates, record_source_run, store_evidence, "
        "search_evidence, store_signal, search_signals, store_digest, "
        "search_digests."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "seen_check",
                    "store_raw_item",
                    "search_raw_items",
                    "duplicate_candidates",
                    "record_source_run",
                    "store_evidence",
                    "search_evidence",
                    "store_signal",
                    "search_signals",
                    "store_digest",
                    "search_digests",
                ],
                "description": "The state operation to perform.",
            },
            "payload": {
                "type": "object",
                "description": "Action-specific parameters. See tool guide for details.",
            },
        },
        "required": ["action"],
    },
}

# ---------------------------------------------------------------------------
# owl_risk_discovery — Source registry and discovery helper operations
# ---------------------------------------------------------------------------

OWL_RISK_DISCOVERY_SCHEMA = {
    "name": "owl_risk_discovery",
    "description": (
        "Source registry and discovery helper operations. "
        "Actions: registry_summary, list_due_sources, get_source, "
        "source_health, helper_preview, feed_preview, sitemap_preview, "
        "source_policy_summary."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "registry_summary",
                    "list_due_sources",
                    "get_source",
                    "source_health",
                    "helper_preview",
                    "feed_preview",
                    "sitemap_preview",
                    "source_policy_summary",
                ],
                "description": "The discovery operation to perform.",
            },
            "payload": {
                "type": "object",
                "description": "Action-specific parameters.",
            },
        },
        "required": ["action"],
    },
}

# ---------------------------------------------------------------------------
# owl_live_vault — Live Obsidian research logging
# ---------------------------------------------------------------------------

OWL_LIVE_VAULT_SCHEMA = {
    "name": "owl_live_vault",
    "description": (
        "Live Obsidian research logging for AI risk intelligence. "
        "Actions: start_run, append_event, upsert_note, "
        "upsert_daily_report, finalize_run, inspect_latest."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "start_run",
                    "append_event",
                    "upsert_note",
                    "upsert_daily_report",
                    "finalize_run",
                    "inspect_latest",
                ],
                "description": "The live vault operation to perform.",
            },
            "payload": {
                "type": "object",
                "description": "Action-specific parameters.",
            },
        },
        "required": ["action"],
    },
}

# ---------------------------------------------------------------------------
# owl_report_quality — Report quality and review
# ---------------------------------------------------------------------------

OWL_REPORT_QUALITY_SCHEMA = {
    "name": "owl_report_quality",
    "description": (
        "Report quality checking and review queue operations. "
        "Actions: check_report, latest_report_summary, "
        "review_queue_summary, quality_rubric_summary."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "check_report",
                    "latest_report_summary",
                    "review_queue_summary",
                    "quality_rubric_summary",
                ],
                "description": "The quality operation to perform.",
            },
            "payload": {
                "type": "object",
                "description": "Action-specific parameters.",
            },
        },
        "required": ["action"],
    },
}

# ---------------------------------------------------------------------------
# owl_obsidian_export — Obsidian vault export/backfill
# ---------------------------------------------------------------------------

OWL_OBSIDIAN_EXPORT_SCHEMA = {
    "name": "owl_obsidian_export",
    "description": (
        "Obsidian vault export and backfill operations. "
        "Actions: export_latest, dry_run, inspect, open_latest_if_available."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "export_latest",
                    "dry_run",
                    "inspect",
                    "open_latest_if_available",
                ],
                "description": "The export operation to perform.",
            },
            "payload": {
                "type": "object",
                "description": "Action-specific parameters.",
            },
        },
        "required": ["action"],
    },
}

# Ordered list for registration
ALL_PLUGIN_SCHEMAS = [
    OWL_RISK_STATE_SCHEMA,
    OWL_RISK_DISCOVERY_SCHEMA,
    OWL_LIVE_VAULT_SCHEMA,
    OWL_REPORT_QUALITY_SCHEMA,
    OWL_OBSIDIAN_EXPORT_SCHEMA,
]
