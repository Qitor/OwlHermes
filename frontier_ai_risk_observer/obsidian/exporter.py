"""Obsidian Intelligence Vault exporter.

Reads DB state and produces a structured Obsidian vault with daily,
signal, candidate, evidence, source, risk domain, run, review, and
index notes. All reads are from local SQLite — no network, no Hermes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from frontier_ai_risk_observer.obsidian.markdown import (
    slugify_filename,
    wikilink,
    write_generated_note,
)

VAULT_DIRS = [
    "00_Daily",
    "01_Signals",
    "02_Candidates",
    "03_Evidence",
    "04_Sources",
    "05_Risk_Domains",
    "06_Entities",
    "07_Runs",
    "08_Live_Runs",
    "90_Review_Queue",
    "99_Indexes",
]


@dataclass
class ObsidianExportConfig:
    """Configuration for Obsidian vault export."""

    vault_path: Path
    include_signals: bool = True
    include_candidates: bool = True
    include_evidence: bool = True
    include_source_runs: bool = True
    include_failed_sources: bool = True
    max_raw_items: int = 50
    max_source_runs: int = 50
    export_date: str | None = None
    dry_run: bool = False


@dataclass
class ExportSummary:
    """Summary of what was exported."""

    vault_path: str = ""
    export_date: str = ""
    daily_notes: int = 0
    signal_notes: int = 0
    candidate_notes: int = 0
    evidence_notes: int = 0
    source_notes: int = 0
    risk_domain_notes: int = 0
    entity_notes: int = 0
    run_notes: int = 0
    review_notes: int = 0
    index_notes: int = 0
    errors: list[str] = field(default_factory=list)


class ObsidianExporter:
    """Export DB state to an Obsidian Intelligence Vault."""

    def __init__(self, config: ObsidianExportConfig) -> None:
        self.config = config
        self.vault = config.vault_path / "AI-Risk-Intelligence"
        self.summary = ExportSummary(vault_path=str(self.vault))
        self._db_session: Any = None

    def _get_session(self) -> Any:
        """Get a DB session using the dry-run DB."""
        if self._db_session is not None:
            return self._db_session
        from frontier_ai_risk_observer.db.session import create_db_engine, create_session_factory

        repo_root = Path(__file__).resolve().parent.parent.parent
        db_path = repo_root / ".local" / "risk_observer_dryrun.db"
        engine = create_db_engine(f"sqlite:///{db_path}")
        factory = create_session_factory(engine)
        self._db_session = factory()
        return self._db_session

    def _ensure_dirs(self) -> None:
        """Create vault directory structure."""
        for d in VAULT_DIRS:
            (self.vault / d).mkdir(parents=True, exist_ok=True)

    def export(self) -> ExportSummary:
        """Run full export."""
        today = self.config.export_date or date.today().isoformat()
        self.summary.export_date = today

        if not self.config.dry_run:
            self._ensure_dirs()

        session = self._get_session()
        try:
            self._export_daily(session, today)
            if self.config.include_signals:
                self._export_signals(session, today)
            if self.config.include_candidates:
                self._export_candidates(session, today)
            if self.config.include_evidence:
                self._export_evidence(session, today)
            self._export_evidence_placeholders(session, today)
            self._export_sources(session)
            self._export_risk_domains(session, today)
            self._export_entities(session, today)
            if self.config.include_source_runs:
                self._export_runs(session, today)
            self._export_review_queue(session, today)
            self._export_indexes(session, today)
        except Exception as exc:  # noqa: BLE001
            self.summary.errors.append(str(exc))
        finally:
            session.close()

        return self.summary

    def _write_note(
        self, rel_path: str, frontmatter: dict[str, Any], body: str, title: str
    ) -> bool:
        """Write a note. Returns True if written."""
        path = self.vault / rel_path
        if self.config.dry_run:
            return True
        write_generated_note(path, frontmatter, body, title)
        return True

    def _export_daily(self, session: Any, today: str) -> None:
        """Export daily report note."""
        from sqlalchemy import func, select

        from frontier_ai_risk_observer.db.models import (
            Digest,
            RawItem,
            Signal,
            SourceClaim,
            SourceRun,
        )

        # Get latest digest
        digest = session.scalar(
            select(Digest).order_by(Digest.created_at.desc()).limit(1)
        )
        all_signal_count = session.scalar(select(func.count(Signal.id))) or 0
        all_candidate_count = session.scalar(select(func.count(RawItem.id))) or 0
        all_evidence_count = session.scalar(select(func.count(SourceClaim.id))) or 0
        all_run_count = session.scalar(select(func.count(SourceRun.id))) or 0
        failed_run_count = session.scalar(
            select(func.count(SourceRun.id)).where(SourceRun.status == "error")
        ) or 0
        review_signal_count = session.scalar(
            select(func.count(Signal.id)).where(
                Signal.needs_human_review == True  # noqa: E712
            )
        ) or 0

        body_parts = []
        if digest:
            body_parts.append(digest.markdown_full)
        else:
            # Try reading from latest run artifact
            repo_root = Path(__file__).resolve().parent.parent.parent
            runs_dir = repo_root / "runs" / "daily"
            if runs_dir.exists():
                run_dirs = sorted(runs_dir.iterdir(), reverse=True)
                for rd in run_dirs[:1]:
                    report = rd / "daily_report.md"
                    if report.exists():
                        body_parts.append(report.read_text(encoding="utf-8"))

        body = "\n\n---\n\n".join(body_parts) if body_parts else "*No daily report available.*"

        # Add linked sections
        links = []
        links.append("## Linked Intelligence Objects\n")
        if all_signal_count > 0:
            links.append(f"**Signals**: {all_signal_count} — see {wikilink('Signal Index')}")
        if all_candidate_count > 0:
            links.append(
                f"**Candidates**: {all_candidate_count} — see "
                f"{wikilink('Candidate Index')}"
            )
        if all_evidence_count > 0:
            links.append(
                f"**Evidence**: {all_evidence_count} — see "
                f"{wikilink('Evidence Index')}"
            )
        links.append(
            f"**Sources**: see {wikilink('Source Index')} for registry"
        )
        if all_run_count > 0:
            links.append(
                f"**Source Runs**: {all_run_count} — see {wikilink('Run Index')}"
            )
        if failed_run_count > 0:
            links.append(
                f"**Failed Sources**: {failed_run_count} — see "
                f"{wikilink('90_Review_Queue/failed-sources')}"
            )
        if review_signal_count > 0:
            links.append(
                f"**Review Queue**: {review_signal_count} signals need review — see "
                f"{wikilink('90_Review_Queue/needs-review')}"
            )
        # Link to live runs if any exist
        live_runs_dir = self.vault / "08_Live_Runs"
        live_run_id_for_fm: str | None = None
        if live_runs_dir.exists():
            live_run_dirs = sorted(
                [d for d in live_runs_dir.iterdir() if d.is_dir()],
                reverse=True,
            )
            if live_run_dirs:
                latest_live = live_run_dirs[0].name
                links.append(
                    f"**Live Research Run**: "
                    f"{wikilink(f'08_Live_Runs/{latest_live}/Live Research Log')} "
                    f"({latest_live})"
                )
                # Check for today's live runs
                today_live = [d for d in live_run_dirs if d.name.startswith(today)]
                if today_live:
                    live_run_id_for_fm = today_live[0].name

        links.append(f"See {wikilink('Daily Index')} for past reports")
        links.append("")
        links.append("*本地非生产运行 | Local Daily Report*")

        body += "\n\n---\n\n" + "\n".join(links)

        frontmatter = {
            "type": "daily_report",
            "date": today,
            "status": digest.status if digest else "unknown",
            "generated_by": "hermes-agent",
            "signals_count": all_signal_count,
            "candidates_count": all_candidate_count,
            "evidence_count": all_evidence_count,
            "runs_count": all_run_count,
            "failed_sources": failed_run_count,
        }
        if digest:
            frontmatter["digest_id"] = str(digest.id)
        if live_run_id_for_fm:
            frontmatter["live_run_id"] = live_run_id_for_fm

        self._write_note(f"00_Daily/{today}.md", frontmatter, body, f"Daily Report {today}")
        self.summary.daily_notes = 1

    def _export_signals(self, session: Any, today: str) -> None:
        """Export signal notes."""
        from sqlalchemy import select

        from frontier_ai_risk_observer.db.models import Signal

        signals = list(session.scalars(
            select(Signal).order_by(Signal.created_at.desc()).limit(100)
        ).all())

        for sig in signals:
            slug = slugify_filename(sig.title_zh)
            sig_date = sig.signal_date.isoformat()
            filename = f"{sig_date}_{slug}.md"

            what_changed = sig.what_changed or "*Missing — needs review*"
            why_it_matters = sig.why_it_matters or "*Missing — needs review*"
            what_to_watch = sig.what_to_watch_next or "*Missing — needs review*"

            body_parts = [
                f"## Summary\n{sig.summary_zh}\n",
                f"## What Changed?\n{what_changed}\n",
                f"## Why It Matters\n{why_it_matters}\n",
                f"## What to Watch Next\n{what_to_watch}\n",
            ]

            if sig.primary_source_url:
                body_parts.append(f"## Evidence URL\n{sig.primary_source_url}\n")

            if sig.source_ids:
                src_links = [wikilink(f"04_Sources/{s}") for s in sig.source_ids]
                body_parts.append("## Sources\n" + " | ".join(src_links) + "\n")

            if sig.needs_human_review:
                body_parts.append("## Review\n*This signal needs human review.*\n")

            frontmatter = {
                "type": "signal",
                "date": sig_date,
                "signal_id": str(sig.id),
                "signal_type": sig.signal_type,
                "risk_domains": sig.risk_domains,
                "severity": sig.severity,
                "confidence": sig.confidence,
                "needs_review": sig.needs_human_review,
            }
            if sig.source_ids:
                frontmatter["source_ids"] = sig.source_ids

            body_text = "\n".join(body_parts)
            self._write_note(
                f"01_Signals/{filename}", frontmatter, body_text, sig.title_zh
            )

        self.summary.signal_notes = len(signals)

    def _export_candidates(self, session: Any, today: str) -> None:
        """Export candidate raw item notes."""
        from sqlalchemy import select

        from frontier_ai_risk_observer.db.models import RawItem

        items = list(session.scalars(
            select(RawItem).order_by(RawItem.last_seen_at.desc())
            .limit(self.config.max_raw_items)
        ).all())

        for item in items:
            slug = slugify_filename(item.title)
            first_seen = item.first_seen_at.date().isoformat() if item.first_seen_at else today
            filename = f"{first_seen}_{slug}.md"

            body_parts = [f"## Title\n{item.title}\n"]
            if item.canonical_url:
                body_parts.append(f"## URL\n{item.canonical_url}\n")
            if item.content_text:
                excerpt = item.content_text[:1000]
                if len(item.content_text) > 1000:
                    excerpt += "..."
                body_parts.append(f"## Content Excerpt\n{excerpt}\n")
            body_parts.append(f"## Source\n{wikilink(f'04_Sources/{item.source_id}')}\n")
            body_parts.append(f"## Seen Count\n{item.seen_count}\n")
            body_parts.append(
                "## Review Checklist\n"
                "- Is this a risk signal?\n"
                "- What changed?\n"
                "- Why does it matter?\n"
                "- What to watch next?\n"
            )

            frontmatter = {
                "type": "candidate",
                "date": first_seen,
                "raw_item_id": str(item.id),
                "source_id": item.source_id,
                "ingestion_status": item.ingestion_status,
                "seen_count": item.seen_count,
            }
            if item.canonical_url:
                frontmatter["url"] = item.canonical_url

            body_text = "\n".join(body_parts)
            self._write_note(
                f"02_Candidates/{filename}", frontmatter, body_text, item.title
            )

        self.summary.candidate_notes = len(items)

    def _export_evidence(self, session: Any, today: str) -> None:
        """Export evidence/claim notes."""
        from frontier_ai_risk_observer.services.evidence import list_recent_evidence_items

        items = list_recent_evidence_items(session, limit=50)

        for claim in items:
            title = claim.evidence_title or claim.claim_text[:60] or "Evidence"
            slug = slugify_filename(title)
            claim_date = claim.created_at.date().isoformat() if claim.created_at else today
            filename = f"{claim_date}_{slug}.md"

            body_parts = [f"## Claim\n{claim.claim_text}\n"]
            if claim.evidence_excerpt:
                body_parts.append(f"## Evidence Excerpt\n{claim.evidence_excerpt}\n")
            if claim.primary_source_url:
                body_parts.append(f"## Evidence URL\n{claim.primary_source_url}\n")
            if claim.signal_id:
                body_parts.append(f"## Linked Signal\n{wikilink(f'Signal {claim.signal_id}')}\n")
            if claim.source_id:
                body_parts.append(f"## Source\n{wikilink(f'04_Sources/{claim.source_id}')}\n")
            if claim.needs_human_review:
                body_parts.append("## Review\n*This evidence needs human review.*\n")

            frontmatter = {
                "type": "evidence",
                "date": claim_date,
                "evidence_id": str(claim.id),
                "claim_type": claim.claim_type,
                "confidence": claim.confidence,
                "needs_review": claim.needs_human_review,
            }
            if claim.signal_id:
                frontmatter["signal_id"] = str(claim.signal_id)
            if claim.source_id:
                frontmatter["source_id"] = claim.source_id

            self._write_note(f"03_Evidence/{filename}", frontmatter, "\n".join(body_parts), title)

        self.summary.evidence_notes = len(items)

    def _export_evidence_placeholders(self, session: Any, today: str) -> None:
        """Create evidence placeholder notes for signals with evidence URLs but
        no linked evidence items. Also marks signals without evidence for review.
        """
        from sqlalchemy import select

        from frontier_ai_risk_observer.db.models import Signal, SourceClaim

        signals = list(session.scalars(
            select(Signal).order_by(Signal.created_at.desc()).limit(100)
        ).all())

        placeholder_count = 0
        for sig in signals:
            # Check if signal already has linked evidence
            existing_evidence = session.scalar(
                select(SourceClaim).where(
                    SourceClaim.signal_id == sig.id
                ).limit(1)
            )
            if existing_evidence:
                continue

            # Signal has no evidence items
            if sig.primary_source_url:
                # Create a placeholder evidence note from the signal URL
                sig_slug = slugify_filename(sig.title_zh)
                sig_date = sig.signal_date.isoformat()
                title = f"Evidence for: {sig.title_zh[:50]}"
                slug = slugify_filename(title)
                filename = f"{sig_date}_{slug}_placeholder.md"

                body_parts = [
                    "## Claim\nEvidence URL linked by Hermes; "
                    "excerpt not yet captured.\n",
                    f"## Evidence URL\n{sig.primary_source_url}\n",
                    f"## Linked Signal\n{wikilink(f'01_Signals/{sig_date}_{sig_slug}')}\n",
                    "## Review\n"
                    "*Placeholder evidence — needs human review.*\n",
                ]

                frontmatter = {
                    "type": "evidence",
                    "date": sig_date,
                    "signal_id": str(sig.id),
                    "claim_type": "placeholder_evidence",
                    "confidence": None,
                    "needs_review": True,
                    "placeholder": True,
                }
                body_text = "\n".join(body_parts)
                self._write_note(
                    f"03_Evidence/{filename}", frontmatter, body_text, title
                )
                placeholder_count += 1
            else:
                # Signal has no evidence URL at all — already handled
                # in review queue export
                pass

        if placeholder_count > 0:
            self.summary.evidence_notes += placeholder_count

    def _export_sources(self, session: Any) -> None:
        """Export source notes from registry."""
        from frontier_ai_risk_observer.registry.loader import load_registry_bundle
        from frontier_ai_risk_observer.registry.validators import validate_registry_bundle

        bundle = load_registry_bundle()
        validated = validate_registry_bundle(bundle)

        all_entries: list[tuple[str, dict[str, Any]]] = []
        for group_name, group in [
            ("source", validated.sources),
            ("podcast", validated.podcasts),
            ("event", validated.events),
            ("benchmark", validated.benchmarks),
        ]:
            for entry in group:  # type: ignore[attr-defined]
                all_entries.append((group_name, entry.model_dump(mode="json")))

        for kind, entry in all_entries:
            source_id = entry.get("id", "unknown")
            name = entry.get("name", source_id)

            body_parts = [f"## {name}\n"]
            body_parts.append(f"**Kind**: {kind}\n")
            if entry.get("url"):
                body_parts.append(f"**URL**: {entry['url']}\n")
            if entry.get("helper_type"):
                body_parts.append(f"**Helper**: {entry['helper_type']}\n")
            if entry.get("known_issues"):
                body_parts.append(f"**Known Issues**: {entry['known_issues']}\n")
            if entry.get("risk_focus"):
                body_parts.append(f"**Risk Focus**: {', '.join(entry['risk_focus'])}\n")
            body_parts.append(f"**Priority**: {entry.get('priority', 'medium')}\n")

            frontmatter = {
                "type": "source",
                "source_id": source_id,
                "kind": kind,
                "enabled": entry.get("enabled", True),
                "priority": entry.get("priority", "medium"),
            }

            self._write_note(f"04_Sources/{source_id}.md", frontmatter, "\n".join(body_parts), name)

        self.summary.source_notes = len(all_entries)

    def _export_risk_domains(self, session: Any, today: str) -> None:
        """Export risk domain notes."""
        from sqlalchemy import select

        from frontier_ai_risk_observer.db.models import Signal

        # Collect unique risk domains from signals
        signals = list(session.scalars(select(Signal).limit(200)).all())
        domain_signals: dict[str, list[Signal]] = {}
        for sig in signals:
            for domain in sig.risk_domains:
                domain_signals.setdefault(domain, []).append(sig)

        # Also add domains from registry risk_focus fields
        from frontier_ai_risk_observer.registry.loader import load_registry_bundle
        bundle = load_registry_bundle()
        for group in (bundle.sources, bundle.podcasts, bundle.events):
            for entry in group:
                if isinstance(entry, dict):
                    for domain in entry.get("risk_focus", []):
                        if isinstance(domain, str) and domain not in domain_signals:
                            domain_signals[domain] = []

        for domain, sigs in domain_signals.items():
            slug = slugify_filename(domain)
            body_parts = [f"## Risk Domain: {domain}\n"]
            body_parts.append(f"**Signal count**: {len(sigs)}\n")
            if sigs:
                body_parts.append("### Recent Signals\n")
                for sig in sigs[:10]:
                    sig_slug = slugify_filename(sig.title_zh)
                    sig_date_str = sig.signal_date.isoformat()
                    link = wikilink(f"01_Signals/{sig_date_str}_{sig_slug}")
                    body_parts.append(f"- {link}")
                body_parts.append("")

            frontmatter = {
                "type": "risk_domain",
                "domain": domain,
                "signal_count": len(sigs),
            }
            body_text = "\n".join(body_parts)
            self._write_note(
                f"05_Risk_Domains/{slug}.md", frontmatter, body_text, domain
            )

        self.summary.risk_domain_notes = len(domain_signals)

    def _export_entities(self, session: Any, today: str) -> None:
        """Export entity notes (conservative, from known sources only)."""
        from frontier_ai_risk_observer.registry.loader import load_registry_bundle

        bundle = load_registry_bundle()
        entities: set[str] = set()
        for group in (bundle.sources, bundle.podcasts, bundle.events):
            for entry in group:
                if isinstance(entry, dict) and entry.get("organization"):
                    entities.add(entry["organization"])

        for entity in entities:
            slug = slugify_filename(entity)
            body = f"## {entity}\n\n*Entity extracted from source registry.*\n"
            frontmatter = {"type": "entity", "name": entity}
            self._write_note(f"06_Entities/{slug}.md", frontmatter, body, entity)

        self.summary.entity_notes = len(entities)

    def _export_runs(self, session: Any, today: str) -> None:
        """Export run notes."""
        from sqlalchemy import select

        from frontier_ai_risk_observer.db.models import SourceRun

        runs = list(session.scalars(
            select(SourceRun).order_by(SourceRun.created_at.desc())
            .limit(self.config.max_source_runs)
        ).all())

        for run in runs:
            run_date = run.created_at.date().isoformat() if run.created_at else today
            filename = f"{run_date}_{run.source_id}_{str(run.id)[:8]}.md"

            body_parts = [
                f"## Source Run: {run.source_id}\n",
                f"**Status**: {run.status}\n",
                f"**Items found**: {run.items_found}\n",
                f"**Items new**: {run.items_new}\n",
                f"**Duplicates**: {run.items_duplicate}\n",
                f"**Errors**: {run.items_error}\n",
            ]
            if run.error_message:
                body_parts.append(f"**Error**: {run.error_message}\n")

            frontmatter = {
                "type": "source_run",
                "date": run_date,
                "source_id": run.source_id,
                "status": run.status,
                "items_found": run.items_found,
                "items_new": run.items_new,
            }

            body_text = "\n".join(body_parts)
            self._write_note(
                f"07_Runs/{filename}", frontmatter, body_text,
                f"Run {run.source_id}",
            )

        self.summary.run_notes = len(runs)

    def _export_review_queue(self, session: Any, today: str) -> None:
        """Export review queue notes."""
        from sqlalchemy import select

        from frontier_ai_risk_observer.db.models import Signal, SourceClaim, SourceRun

        # Needs review
        review_signals = list(session.scalars(
            select(Signal).where(Signal.needs_human_review == True)  # noqa: E712
            .limit(50)
        ).all())
        review_evidence = list(session.scalars(
            select(SourceClaim).where(SourceClaim.needs_human_review == True)  # noqa: E712
            .limit(50)
        ).all())

        # Signals without evidence (no linked SourceClaim)
        all_signals = list(session.scalars(
            select(Signal).limit(100)
        ).all())
        signals_without_evidence: list[Signal] = []
        for sig in all_signals:
            has_evidence = session.scalar(
                select(SourceClaim).where(
                    SourceClaim.signal_id == sig.id
                ).limit(1)
            )
            if not has_evidence and sig not in review_signals:
                signals_without_evidence.append(sig)

        body_parts = ["# Needs Review\n"]
        if review_signals:
            body_parts.append("## Signals Needing Review\n")
            for sig in review_signals:
                sig_slug = slugify_filename(sig.title_zh)
                sig_date_str = sig.signal_date.isoformat()
                link = wikilink(f"01_Signals/{sig_date_str}_{sig_slug}")
                body_parts.append(f"- {link} — {sig.title_zh}")
            body_parts.append("")
        if signals_without_evidence:
            body_parts.append("## Signals Without Evidence\n")
            for sig in signals_without_evidence:
                sig_slug = slugify_filename(sig.title_zh)
                sig_date_str = sig.signal_date.isoformat()
                link = wikilink(f"01_Signals/{sig_date_str}_{sig_slug}")
                body_parts.append(f"- {link} — no evidence items linked")
            body_parts.append("")
        if review_evidence:
            body_parts.append("## Evidence Needing Review\n")
            for ev in review_evidence:
                title = ev.evidence_title or ev.claim_text[:50] or "Evidence"
                body_parts.append(f"- {title}")
            body_parts.append("")
        if not review_signals and not signals_without_evidence and not review_evidence:
            body_parts.append("*No items need review.*\n")

        frontmatter = {"type": "review_queue", "date": today}
        body_text = "\n".join(body_parts)
        self._write_note(
            "90_Review_Queue/needs-review.md", frontmatter, body_text,
            "Needs Review",
        )

        # Failed sources
        failed_runs = list(session.scalars(
            select(SourceRun).where(SourceRun.status == "error").limit(50)
        ).all())

        body_parts = ["# Failed Sources\n"]
        if failed_runs:
            for run in failed_runs:
                err = run.error_message or "Unknown error"
                body_parts.append(f"- **{run.source_id}**: {err}")
            body_parts.append("")
        else:
            body_parts.append("*No failed sources.*\n")

        frontmatter = {"type": "failed_sources", "date": today}
        body_text = "\n".join(body_parts)
        self._write_note(
            "90_Review_Queue/failed-sources.md", frontmatter, body_text,
            "Failed Sources",
        )

        self.summary.review_notes = 2

    def _export_indexes(self, session: Any, today: str) -> None:
        """Export index notes."""
        from sqlalchemy import func, select

        from frontier_ai_risk_observer.db.models import (
            Digest,
            RawItem,
            Signal,
            SourceClaim,
            SourceRun,
        )

        indexes = {
            "Daily Index": ("00_Daily", "daily_report"),
            "Signal Index": ("01_Signals", "signal"),
            "Candidate Index": ("02_Candidates", "candidate"),
            "Evidence Index": ("03_Evidence", "evidence"),
            "Source Index": ("04_Sources", "source"),
            "Risk Domain Index": ("05_Risk_Domains", "risk_domain"),
            "Run Index": ("07_Runs", "source_run"),
            "Live Run Index": ("08_Live_Runs", "live_run"),
        }

        counts = {
            "Daily Index": session.scalar(select(func.count(Digest.id))) or 0,
            "Signal Index": session.scalar(select(func.count(Signal.id))) or 0,
            "Candidate Index": session.scalar(select(func.count(RawItem.id))) or 0,
            "Evidence Index": session.scalar(select(func.count(SourceClaim.id))) or 0,
            "Source Index": 0,  # filled from registry
            "Risk Domain Index": 0,
            "Run Index": session.scalar(select(func.count(SourceRun.id))) or 0,
            "Live Run Index": 0,  # filled from filesystem
        }

        # Count live runs from filesystem
        live_runs_dir = self.vault / "08_Live_Runs"
        if live_runs_dir.exists():
            counts["Live Run Index"] = len(
                [d for d in live_runs_dir.iterdir() if d.is_dir()]
            )

        for index_name, (folder, note_type) in indexes.items():
            body = f"# {index_name}\n\n**Total**: {counts.get(index_name, 0)} items\n\n"
            body += f"*See the {folder}/ folder for all notes.*\n"

            # For Live Run Index, list recent runs
            if index_name == "Live Run Index" and live_runs_dir.exists():
                run_dirs = sorted(
                    [d for d in live_runs_dir.iterdir() if d.is_dir()],
                    reverse=True,
                )
                if run_dirs:
                    body += "\n### Recent Runs\n"
                    for rd in run_dirs[:10]:
                        link = wikilink(f"08_Live_Runs/{rd.name}/Live Research Log")
                        body += f"- {link}\n"

            frontmatter = {"type": "index", "index_for": note_type}
            self._write_note(f"99_Indexes/{index_name}.md", frontmatter, body, index_name)

        self.summary.index_notes = len(indexes)
