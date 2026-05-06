"""Bidirectional link formatting helpers for Obsidian vault notes.

Pure functions — no file I/O, no network, no DB access.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from frontier_ai_risk_observer.obsidian.markdown import wikilink


def format_backlink_section(
    *,
    daily_note_path: str | None = None,
    live_run_path: str | None = None,
    signal_paths: list[str] | None = None,
    candidate_paths: list[str] | None = None,
    evidence_paths: list[str] | None = None,
    source_paths: list[str] | None = None,
    failure_paths: list[str] | None = None,
    risk_domains: list[str] | None = None,
) -> str:
    """Render a ``## Links`` section with wikilinks grouped by type.

    Returns an empty string if no links are provided.
    """
    groups: list[tuple[str, list[str]]] = []

    if daily_note_path:
        groups.append(("Daily Report", [wikilink(daily_note_path)]))
    if live_run_path:
        groups.append(("Live Run", [wikilink(live_run_path)]))
    if signal_paths:
        groups.append(("Related Signals", [wikilink(p) for p in signal_paths]))
    if candidate_paths:
        groups.append(("Related Candidates", [wikilink(p) for p in candidate_paths]))
    if evidence_paths:
        groups.append(("Related Evidence", [wikilink(p) for p in evidence_paths]))
    if source_paths:
        groups.append(("Source", [wikilink(p) for p in source_paths]))
    if failure_paths:
        groups.append(("Failures", [wikilink(p) for p in failure_paths]))
    if risk_domains:
        groups.append(("Risk Domains", [wikilink(p) for p in risk_domains]))

    if not groups:
        return ""

    lines = ["\n## Links", ""]
    for label, links in groups:
        lines.append(f"### {label}")
        for link in links:
            lines.append(f"- {link}")
        lines.append("")
    return "\n".join(lines)


def format_timeline_entry_with_link(
    event_type: str,
    title: str,
    note_path: str | None = None,
) -> str:
    """Return a timeline entry with optional wikilink.

    Example: ``- **06:44:38** [source_selected] [[Sources/uk_aisi|UK AISI]]``
    """
    ts = datetime.now(UTC).strftime("%H:%M:%S")
    if note_path:
        return f"- **{ts}** [{event_type}] {wikilink(note_path, title)}"
    return f"- **{ts}** [{event_type}] {title}"


def note_vault_relative_path(
    vault_root: Path,
    note_path: Path,
) -> str:
    """Return path relative to ``AI-Risk-Intelligence/`` for use in wikilinks.

    Falls back to the note filename if the path is not under the vault root.
    """
    ai_root = vault_root / "AI-Risk-Intelligence"
    try:
        return str(note_path.relative_to(ai_root))
    except ValueError:
        return note_path.name
