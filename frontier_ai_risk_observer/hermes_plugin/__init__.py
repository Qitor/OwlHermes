"""OwlHermes Hermes Plugin — Hermes-native Frontier AI Risk Intelligence Observer.

This package implements the Hermes plugin that registers high-level facade tools
(owl_risk_state, owl_risk_discovery, owl_live_vault, owl_report_quality,
owl_obsidian_export) for use by the Hermes-Agent runtime.

The plugin reuses existing backend services (ingestion, signals, evidence, digest,
live_research, registry, source_health, quality, obsidian) and does not duplicate
business logic.
"""

__version__ = "0.1.0"
