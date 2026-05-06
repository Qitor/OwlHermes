"""Immediate daily report note writer for live Obsidian vault.

Writes the final daily report to ``00_Daily/YYYY-MM-DD.md`` when a digest
or final report is available. This is the core fix for R1-13C: the daily
note must be written in real-time, not only during batch export.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from frontier_ai_risk_observer.obsidian.links import format_backlink_section
from frontier_ai_risk_observer.obsidian.markdown import (
    BEGIN_MARKER,
    WriteResult,
    write_generated_note,
)


def upsert_daily_report_note(
    vault_path: Path,
    report_date: str,
    report_markdown: str,
    *,
    digest_id: str | None = None,
    run_id: str | None = None,
    status: str = "draft",
    quality_score: int | None = None,
    sources_checked: int = 0,
    signals_count: int = 0,
    candidates_count: int = 0,
    evidence_count: int = 0,
    signal_note_paths: list[str] | None = None,
    candidate_note_paths: list[str] | None = None,
    evidence_note_paths: list[str] | None = None,
    source_note_paths: list[str] | None = None,
    failure_note_paths: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> WriteResult:
    """Write or update the final daily report note in the Obsidian vault.

    Creates ``00_Daily/YYYY-MM-DD.md`` with the full report body inside
    generated block markers and a ``## Links`` section for bidirectional
    navigation.

    **Override protection**: If the daily note already contains a full
    report (body > 200 chars inside generated markers), a shorter
    ``report_markdown`` will NOT overwrite it. Instead, only the
    frontmatter and links section are updated. This prevents Hermes from
    replacing a complete report with a lazy reference like
    "See digest abc123".
    """
    ai_root = vault_path / "AI-Risk-Intelligence"
    daily_dir = ai_root / "00_Daily"
    daily_dir.mkdir(parents=True, exist_ok=True)
    daily_path = daily_dir / f"{report_date}.md"

    # Build frontmatter
    frontmatter: dict[str, Any] = {
        "type": "daily",
        "date": report_date,
        "status": status,
    }
    if digest_id:
        frontmatter["digest_id"] = digest_id
    if run_id:
        frontmatter["run_id"] = run_id
    if quality_score is not None:
        frontmatter["quality_score"] = quality_score
    if sources_checked:
        frontmatter["sources_checked"] = sources_checked
    if signals_count:
        frontmatter["signals_count"] = signals_count
    if candidates_count:
        frontmatter["candidates_count"] = candidates_count
    if evidence_count:
        frontmatter["evidence_count"] = evidence_count
    if metadata:
        frontmatter.update(metadata)

    # Build live run path for linking
    live_run_path: str | None = None
    if run_id:
        live_run_path = f"08_Live_Runs/{run_id}/Live Research Log"

    # Build links section
    links_section = format_backlink_section(
        live_run_path=live_run_path,
        signal_paths=signal_note_paths,
        candidate_paths=candidate_note_paths,
        evidence_paths=evidence_note_paths,
        source_paths=source_note_paths,
        failure_paths=failure_note_paths,
    )

    # Override protection: don't let a short/lazy report replace a full one
    body = report_markdown + links_section
    if daily_path.exists() and len(report_markdown.strip()) < 200:
        existing = daily_path.read_text(encoding="utf-8")
        if BEGIN_MARKER in existing:
            end_marker = "<!-- END_AUTO_GENERATED: hermes-ai-risk-observer -->"
            if end_marker in existing:
                start = existing.index(BEGIN_MARKER) + len(BEGIN_MARKER)
                end = existing.index(end_marker)
                existing_body = existing[start:end].strip()
                # If existing body is substantial, keep it and only update
                # frontmatter + append/refresh links
                if len(existing_body) > 200:
                    # Replace links section only, keep existing report body
                    new_body = _replace_links_section(existing_body, links_section)
                    title = f"Daily Report: {report_date}"
                    return write_generated_note(
                        daily_path, frontmatter, new_body, title,
                    )

    title = f"Daily Report: {report_date}"
    return write_generated_note(daily_path, frontmatter, body, title)


def _replace_links_section(existing_body: str, new_links_section: str) -> str:
    """Replace the ## Links section in existing body, preserving the rest.

    If no ## Links section exists, append the new one.
    """
    links_marker = "\n## Links"
    if links_marker in existing_body:
        idx = existing_body.index(links_marker)
        return existing_body[:idx] + new_links_section
    return existing_body + new_links_section


def ensure_daily_note_has_body(vault_path: Path, report_date: str) -> bool:
    """Check if the daily note exists and has content inside generated markers.

    Used by the runner safety net to decide whether to write the daily note.
    """
    ai_root = vault_path / "AI-Risk-Intelligence"
    daily_path = ai_root / "00_Daily" / f"{report_date}.md"

    if not daily_path.exists():
        return False

    content = daily_path.read_text(encoding="utf-8")
    if BEGIN_MARKER not in content:
        return False

    # Check there's actual content between markers (not just whitespace)
    start = content.index(BEGIN_MARKER) + len(BEGIN_MARKER)
    end_marker = "<!-- END_AUTO_GENERATED: hermes-ai-risk-observer -->"
    if end_marker not in content:
        return False
    end = content.index(end_marker)
    body = content[start:end].strip()
    return len(body) > 0


def upsert_review_queue_note(
    vault_path: Path,
    queue_type: str,
    entries: list[dict[str, str]],
) -> WriteResult:
    """Write or update a review queue note.

    Args:
        vault_path: Obsidian vault root path.
        queue_type: ``"needs-review"`` or ``"failed-sources"``.
        entries: List of dicts with at least ``title`` and ``reason`` keys.

    Writes to ``90_Review_Queue/{queue_type}.md``.
    """
    ai_root = vault_path / "AI-Risk-Intelligence"
    queue_dir = ai_root / "90_Review_Queue"
    queue_dir.mkdir(parents=True, exist_ok=True)
    queue_path = queue_dir / f"{queue_type}.md"

    frontmatter: dict[str, Any] = {
        "type": "review_queue",
        "queue_type": queue_type,
    }

    lines = [f"# Review Queue: {queue_type}", ""]
    for entry in entries:
        title = entry.get("title", "Unknown")
        reason = entry.get("reason", "")
        source = entry.get("source", "")
        line = f"- **{title}**"
        if reason:
            line += f" — {reason}"
        if source:
            line += f" (source: {source})"
        lines.append(line)
    lines.append("")
    body = "\n".join(lines)

    return write_generated_note(
        queue_path, frontmatter, body, f"Review Queue: {queue_type}"
    )
