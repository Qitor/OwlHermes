"""Plugin manifest constants for OwlHermes."""

PLUGIN_NAME = "owlhermes"
PLUGIN_VERSION = "0.1.0"
PLUGIN_DESCRIPTION = "Hermes-native Frontier AI Risk Intelligence Observer"

TOOLSET = "owlhermes"

PROVIDES_TOOLS = [
    "owl_risk_state",
    "owl_risk_discovery",
    "owl_live_vault",
    "owl_report_quality",
    "owl_obsidian_export",
]

PROVIDES_HOOKS: list[str] = []
