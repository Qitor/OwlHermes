"""Live Obsidian vault writer for real-time research logging.

Writes research progress to the Obsidian vault during Hermes daily report runs.
All writes use generated-block markers to preserve human content.
Disabled live logging returns success without any I/O.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from frontier_ai_risk_observer.obsidian.markdown import (
    atomic_write,
    slugify_filename,
    wikilink,
    write_generated_note,
)


@dataclass
class LiveVaultConfig:
    """Configuration for live Obsidian vault logging."""

    vault_path: Path
    live_logging_enabled: bool = False
    runs_dir_name: str = "08_Live_Runs"
    append_to_daily: bool = True
    open_after_start: bool = False
    event_max_chars: int = 4000
    flush_mode: str = "immediate"  # "immediate" or "buffered"

    @classmethod
    def from_env(cls) -> LiveVaultConfig:
        """Load config from environment variables."""
        vault_path_str = os.environ.get("OBSIDIAN_VAULT_PATH", "")
        enabled = os.environ.get("OBSIDIAN_LIVE_LOGGING_ENABLED", "false").lower() in (
            "true",
            "1",
            "yes",
        )

        if enabled and not vault_path_str:
            raise ValueError(
                "OBSIDIAN_LIVE_LOGGING_ENABLED is true but OBSIDIAN_VAULT_PATH is not set"
            )

        vault_path = Path(vault_path_str) if vault_path_str else Path(".local/obsidian_vault")
        runs_dir = os.environ.get("OBSIDIAN_LIVE_RUNS_DIR", "08_Live_Runs")
        append_daily = os.environ.get("OBSIDIAN_LIVE_APPEND_TO_DAILY", "true").lower() in (
            "true",
            "1",
            "yes",
        )
        open_after = os.environ.get("OBSIDIAN_LIVE_OPEN_AFTER_START", "false").lower() in (
            "true",
            "1",
            "yes",
        )
        max_chars = int(os.environ.get("OBSIDIAN_LIVE_EVENT_MAX_CHARS", "4000"))
        flush_mode = os.environ.get("OBSIDIAN_LIVE_FLUSH_MODE", "immediate")

        if flush_mode not in ("immediate", "buffered"):
            raise ValueError(
                f"Invalid OBSIDIAN_LIVE_FLUSH_MODE '{flush_mode}'. "
                "Allowed: immediate, buffered"
            )

        return cls(
            vault_path=vault_path,
            live_logging_enabled=enabled,
            runs_dir_name=runs_dir,
            append_to_daily=append_daily,
            open_after_start=open_after,
            event_max_chars=max_chars,
            flush_mode=flush_mode,
        )


@dataclass
class LiveEvent:
    """A single research event for live logging."""

    event_type: str
    title: str
    body: str | None = None
    source_id: str | None = None
    raw_item_id: str | None = None
    signal_id: str | None = None
    evidence_id: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LiveWriteResult:
    """Result of a live vault write operation."""

    success: bool = True
    notes_written: int = 0
    notes_updated: int = 0
    errors: list[str] = field(default_factory=list)


# Allowed note types for risk_live_note_upsert
ALLOWED_NOTE_TYPES: frozenset[str] = frozenset({
    "source",
    "candidate",
    "evidence",
    "signal",
    "failure",
})

# Subdirectories within a live run
_LIVE_RUN_SUBDIRS = ["Sources", "Candidates", "Evidence", "Signals"]


class LiveVaultWriter:
    """Writes live research notes to an Obsidian vault.

    When live_logging_enabled is False, all methods return success
    without performing any I/O. This ensures disabled logging does
    not break Hermes workflows.
    """

    def __init__(self, config: LiveVaultConfig) -> None:
        self.config = config
        self._active_runs: dict[str, Path] = {}
        self._buffer: list[tuple[str, LiveEvent]] = []
        self._run_logs: dict[str, list[str]] = {}
        self._run_timelines: dict[str, list[str]] = {}

    def _vault_root(self) -> Path:
        """Return the AI-Risk-Intelligence root inside the vault."""
        return self.config.vault_path / "AI-Risk-Intelligence"

    def _run_dir(self, run_id: str) -> Path:
        """Return the live run directory for a given run_id."""
        return self._vault_root() / self.config.runs_dir_name / run_id

    def _check_path_safety(self, resolved: Path) -> None:
        """Ensure resolved path is under the vault root."""
        vault_resolved = self._vault_root().resolve()
        if not resolved.is_relative_to(vault_resolved):
            raise ValueError(
                f"Path escapes vault root: {resolved} is not under {vault_resolved}"
            )

    def _disabled_result(self) -> LiveWriteResult:
        """Return a success result for disabled live logging."""
        return LiveWriteResult(success=True, notes_written=0)

    def _truncate_body(self, body: str | None) -> str | None:
        """Truncate body to event_max_chars if needed."""
        if body is None:
            return None
        if len(body) <= self.config.event_max_chars:
            return body
        return body[: self.config.event_max_chars] + "\n...[truncated]"

    def _format_event_entry(self, event: LiveEvent) -> str:
        """Format a single event as a Markdown list entry."""
        ts = event.timestamp.strftime("%H:%M:%S")
        entry = f"- **{ts}** [{event.event_type}] {event.title}"
        if event.source_id:
            entry += f" — source: {event.source_id}"
        if event.body:
            truncated = self._truncate_body(event.body)
            entry += f"\n  > {truncated}"
        return entry

    def start_run(
        self,
        run_id: str,
        title: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> LiveWriteResult:
        """Start a live research run. Creates directory structure and initial notes."""
        if not self.config.live_logging_enabled:
            return self._disabled_result()

        run_dir = self._run_dir(run_id)

        # Create directory structure
        for subdir in _LIVE_RUN_SUBDIRS:
            (run_dir / subdir).mkdir(parents=True, exist_ok=True)

        # Write initial Live Research Log
        fm = {
            "type": "live_run",
            "run_id": run_id,
            "started_at": datetime.now(UTC).isoformat(),
            "status": "in_progress",
        }
        if title:
            fm["title"] = title
        if metadata:
            fm.update(metadata)

        log_body = f"# Live Research Log: {run_id}\n\nResearch run started.\n"
        log_path = run_dir / "Live Research Log.md"
        self._check_path_safety(log_path.resolve())
        write_generated_note(log_path, fm, log_body, f"Live Research Log: {run_id}")

        # Write initial Timeline
        timeline_fm = {"type": "timeline", "run_id": run_id}
        timeline_body = "# Timeline\n\n- Run started\n"
        timeline_path = run_dir / "Timeline.md"
        self._check_path_safety(timeline_path.resolve())
        write_generated_note(timeline_path, timeline_fm, timeline_body, f"Timeline: {run_id}")

        # Write initial Failures
        failures_fm = {"type": "failures", "run_id": run_id}
        failures_body = "# Failures\n\n*No failures recorded yet.*\n"
        failures_path = run_dir / "Failures.md"
        self._check_path_safety(failures_path.resolve())
        write_generated_note(failures_path, failures_fm, failures_body, f"Failures: {run_id}")

        # Track active run
        self._active_runs[run_id] = run_dir
        self._run_logs[run_id] = ["Research run started."]
        self._run_timelines[run_id] = ["- Run started"]

        # Append to daily note if configured
        if self.config.append_to_daily:
            self._append_to_daily(run_id)

        return LiveWriteResult(success=True, notes_written=3)

    def _ensure_run_tracked(self, run_id: str) -> Path | None:
        """Ensure a run directory is tracked. Returns run_dir or None."""
        if run_id in self._active_runs:
            return self._active_runs[run_id]
        # Auto-discover from filesystem (MCP calls are stateless)
        run_dir = self._run_dir(run_id)
        if run_dir.exists():
            self._active_runs[run_id] = run_dir
            return run_dir
        return None

    def append_event(
        self,
        run_id: str,
        event: LiveEvent,
    ) -> LiveWriteResult:
        """Append a research event to the live log and timeline."""
        if not self.config.live_logging_enabled:
            return self._disabled_result()

        run_dir = self._ensure_run_tracked(run_id)
        if run_dir is None:
            return LiveWriteResult(
                success=False, errors=[f"Run {run_id} not started"]
            )

        # Buffer if in buffered mode
        if self.config.flush_mode == "buffered":
            self._buffer.append((run_id, event))
            return LiveWriteResult(success=True, notes_written=0)

        # Immediate mode: write now
        return self._flush_events(run_id, [event])

    def flush_buffer(self, run_id: str) -> LiveWriteResult:
        """Flush buffered events for a run."""
        if not self.config.live_logging_enabled:
            return self._disabled_result()

        events = [(rid, ev) for rid, ev in self._buffer if rid == run_id]
        self._buffer = [(rid, ev) for rid, ev in self._buffer if rid != run_id]
        if not events:
            return LiveWriteResult(success=True, notes_written=0)
        return self._flush_events(run_id, [ev for _, ev in events])

    def _flush_events(
        self, run_id: str, events: list[LiveEvent]
    ) -> LiveWriteResult:
        """Write events to the log and timeline files."""
        run_dir = self._active_runs.get(run_id)
        if not run_dir:
            return LiveWriteResult(success=False, errors=[f"Run {run_id} not found"])

        log_path = run_dir / "Live Research Log.md"
        timeline_path = run_dir / "Timeline.md"

        written = 0
        for event in events:
            entry = self._format_event_entry(event)
            ts_full = event.timestamp.strftime("%H:%M:%S")
            timeline_entry = f"- **{ts_full}** [{event.event_type}] {event.title}"

            # Read existing content and append
            if log_path.exists():
                existing = log_path.read_text(encoding="utf-8")
                # Find end of generated block and append before it
                if "<!-- END_AUTO_GENERATED" in existing:
                    marker = "<!-- END_AUTO_GENERATED: hermes-ai-risk-observer -->"
                    existing = existing.replace(
                        marker,
                        f"{entry}\n\n{marker}",
                    )
                    atomic_write(log_path, existing)
                else:
                    # No markers — append at end
                    atomic_write(log_path, existing + "\n" + entry + "\n")
            else:
                atomic_write(log_path, entry + "\n")

            if timeline_path.exists():
                existing_tl = timeline_path.read_text(encoding="utf-8")
                if "<!-- END_AUTO_GENERATED" in existing_tl:
                    marker = "<!-- END_AUTO_GENERATED: hermes-ai-risk-observer -->"
                    existing_tl = existing_tl.replace(
                        marker,
                        f"{timeline_entry}\n{marker}",
                    )
                    atomic_write(timeline_path, existing_tl)
                else:
                    atomic_write(timeline_path, existing_tl + timeline_entry + "\n")

            written += 1

        return LiveWriteResult(success=True, notes_written=written)

    def upsert_source_note(
        self,
        run_id: str,
        source_id: str,
        title: str,
        body: str,
        metadata: dict[str, Any] | None = None,
    ) -> LiveWriteResult:
        """Write or update a source note within the live run."""
        return self._upsert_note(run_id, "Sources", source_id, title, body, metadata)

    def upsert_candidate_note(
        self,
        run_id: str,
        slug: str,
        title: str,
        body: str,
        metadata: dict[str, Any] | None = None,
    ) -> LiveWriteResult:
        """Write or update a candidate note within the live run."""
        safe_slug = slugify_filename(slug)
        return self._upsert_note(run_id, "Candidates", safe_slug, title, body, metadata)

    def upsert_evidence_note(
        self,
        run_id: str,
        slug: str,
        title: str,
        body: str,
        metadata: dict[str, Any] | None = None,
    ) -> LiveWriteResult:
        """Write or update an evidence note within the live run."""
        safe_slug = slugify_filename(slug)
        return self._upsert_note(run_id, "Evidence", safe_slug, title, body, metadata)

    def upsert_signal_note(
        self,
        run_id: str,
        slug: str,
        title: str,
        body: str,
        metadata: dict[str, Any] | None = None,
    ) -> LiveWriteResult:
        """Write or update a signal note within the live run."""
        safe_slug = slugify_filename(slug)
        return self._upsert_note(run_id, "Signals", safe_slug, title, body, metadata)

    def _upsert_note(
        self,
        run_id: str,
        subdir: str,
        filename_slug: str,
        title: str,
        body: str,
        metadata: dict[str, Any] | None = None,
    ) -> LiveWriteResult:
        """Generic upsert for a note within a live run subdirectory."""
        if not self.config.live_logging_enabled:
            return self._disabled_result()

        run_dir = self._active_runs.get(run_id)
        if not run_dir:
            # Auto-create run dir if missing
            run_dir = self._run_dir(run_id)
            for sd in _LIVE_RUN_SUBDIRS:
                (run_dir / sd).mkdir(parents=True, exist_ok=True)
            self._active_runs[run_id] = run_dir

        note_path = run_dir / subdir / f"{filename_slug}.md"
        self._check_path_safety(note_path.resolve())

        fm: dict[str, Any] = {
            "type": subdir.lower().rstrip("s"),
            "run_id": run_id,
        }
        if metadata:
            fm.update(metadata)

        is_update = note_path.exists()
        write_generated_note(note_path, fm, body, title)

        result = LiveWriteResult(success=True)
        if is_update:
            result.notes_updated = 1
        else:
            result.notes_written = 1
        return result

    def record_failure(
        self,
        run_id: str,
        source_id: str,
        failure_type: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> LiveWriteResult:
        """Record a failure in the Failures note."""
        if not self.config.live_logging_enabled:
            return self._disabled_result()

        run_dir = self._ensure_run_tracked(run_id)
        if not run_dir:
            return LiveWriteResult(
                success=False, errors=[f"Run {run_id} not started"]
            )

        failures_path = run_dir / "Failures.md"
        self._check_path_safety(failures_path.resolve())

        ts = datetime.now(UTC).strftime("%H:%M:%S")
        entry = (
            f"- **{ts}** [{failure_type}] {source_id}: {message}"
        )

        if failures_path.exists():
            existing = failures_path.read_text(encoding="utf-8")
            # Replace placeholder text
            if "*No failures recorded yet.*" in existing:
                existing = existing.replace(
                    "*No failures recorded yet.*",
                    entry,
                )
            elif "<!-- END_AUTO_GENERATED" in existing:
                marker = "<!-- END_AUTO_GENERATED: hermes-ai-risk-observer -->"
                existing = existing.replace(marker, f"{entry}\n{marker}")
            else:
                existing += "\n" + entry
            atomic_write(failures_path, existing)
        else:
            fm: dict[str, Any] = {"type": "failures", "run_id": run_id}
            if metadata:
                fm.update(metadata)
            write_generated_note(failures_path, fm, entry, "Failures")

        return LiveWriteResult(success=True, notes_written=1)

    def finalize_run(
        self,
        run_id: str,
        summary: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> LiveWriteResult:
        """Finalize a live research run."""
        if not self.config.live_logging_enabled:
            return self._disabled_result()

        run_dir = self._ensure_run_tracked(run_id)
        if not run_dir:
            return LiveWriteResult(
                success=False, errors=[f"Run {run_id} not started"]
            )

        # Flush any remaining buffer
        if self.config.flush_mode == "buffered":
            self.flush_buffer(run_id)

        # Update Live Research Log
        log_path = run_dir / "Live Research Log.md"
        if log_path.exists():
            existing = log_path.read_text(encoding="utf-8")
            now_iso = datetime.now(UTC).isoformat()

            # Update frontmatter status
            if "status: in_progress" in existing:
                existing = existing.replace(
                    "status: in_progress", "status: completed"
                )
            if "started_at:" in existing:
                # Add finalized_at after started_at line
                lines = existing.split("\n")
                new_lines = []
                for line in lines:
                    new_lines.append(line)
                    if line.startswith("started_at:"):
                        new_lines.append(f"finalized_at: {now_iso}")
                existing = "\n".join(new_lines)

            # Append summary
            summary_parts = ["\n## Run Finalized\n"]
            if summary:
                for k, v in summary.items():
                    summary_parts.append(f"- **{k}**: {v}")
            summary_parts.append(f"\nFinalized at: {now_iso}\n")

            summary_text = "\n".join(summary_parts)
            if "<!-- END_AUTO_GENERATED" in existing:
                marker = "<!-- END_AUTO_GENERATED: hermes-ai-risk-observer -->"
                existing = existing.replace(marker, f"{summary_text}\n{marker}")
            else:
                existing += summary_text

            atomic_write(log_path, existing)

        # Update daily note with completion
        if self.config.append_to_daily:
            self._append_completion_to_daily(run_id, summary)

        # Clean up tracking
        self._active_runs.pop(run_id, None)
        self._run_logs.pop(run_id, None)
        self._run_timelines.pop(run_id, None)

        return LiveWriteResult(success=True, notes_updated=1)

    def _append_to_daily(self, run_id: str) -> None:
        """Append a live run link to today's daily note."""
        daily_dir = self._vault_root() / "00_Daily"
        daily_dir.mkdir(parents=True, exist_ok=True)
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        daily_path = daily_dir / f"{today}.md"

        link = wikilink(
            f"{self.config.runs_dir_name}/{run_id}/Live Research Log",
            "Live Research Run",
        )
        entry = f"\n## Live Research\n\n- {link} ({run_id}) started\n"

        if daily_path.exists():
            existing = daily_path.read_text(encoding="utf-8")
            if link not in existing:
                if "<!-- END_AUTO_GENERATED" in existing:
                    marker = "<!-- END_AUTO_GENERATED: hermes-ai-risk-observer -->"
                    existing = existing.replace(marker, f"{entry}\n{marker}")
                    atomic_write(daily_path, existing)
                else:
                    atomic_write(daily_path, existing + entry)
        else:
            fm = {
                "type": "daily",
                "date": today,
            }
            body = f"# Daily Note: {today}\n{entry}\n"
            write_generated_note(daily_path, fm, body, f"Daily: {today}")

    def _append_completion_to_daily(
        self,
        run_id: str,
        summary: dict[str, Any] | None = None,
    ) -> None:
        """Append a completion marker to the daily note."""
        daily_dir = self._vault_root() / "00_Daily"
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        daily_path = daily_dir / f"{today}.md"

        if not daily_path.exists():
            return

        existing = daily_path.read_text(encoding="utf-8")
        completion = f"\n- Live run {run_id} completed"
        if summary:
            signal_count = summary.get("signal_count")
            if signal_count is not None:
                completion += f" — {signal_count} signals"

        already_marked = (
            run_id in existing
            and "completed" in existing.split(run_id)[-1]
        )
        if not already_marked:
            if "<!-- END_AUTO_GENERATED" in existing:
                marker = "<!-- END_AUTO_GENERATED: hermes-ai-risk-observer -->"
                existing = existing.replace(marker, f"{completion}\n{marker}")
                atomic_write(daily_path, existing)
