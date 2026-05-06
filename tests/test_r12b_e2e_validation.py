"""R1-12B tests: Obsidian vault E2E validation, evidence placeholders, daily linking.

Tests cover:
- Inspect script counts and checks
- Evidence placeholder generation for signals without evidence
- Signals without evidence enter review queue
- Raw items produce candidate notes
- Source runs produce run notes
- Failed source runs appear in failed-sources.md
- Daily note links to signal/candidate/evidence/run notes
- Makefile targets exist
- Generated block markers present
"""

from __future__ import annotations

import json
import tempfile
import uuid
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from frontier_ai_risk_observer.db.models import (
    Base,
    Digest,
    RawItem,
    Signal,
    SourceClaim,
    SourceRun,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

NOW = datetime.now(UTC)
TODAY = date(2025, 5, 5)


def _make_session():
    """Create an in-memory SQLite session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        implicit_returning=False,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    return TestSession()


def _add_signal(session, title="测试信号", evidence_url=None, needs_review=False):
    sig = Signal(
        id=uuid.uuid4(),
        title_zh=title,
        summary_zh="摘要",
        what_changed="变化",
        why_it_matters="重要性",
        what_to_watch_next="后续",
        signal_type="frontier_capability",
        risk_domains=["capability_risk"],
        entities=[],
        source_ids=[],
        raw_item_ids=[],
        claim_ids=[],
        evidence_level="primary",
        claim_type="hermes_observation",
        severity=3,
        confidence=4,
        time_sensitivity=3,
        priority_score=0,
        signal_date=TODAY,
        needs_human_review=needs_review,
        status="draft",
        metadata_={},
        primary_source_url=evidence_url,
        created_at=NOW,
        updated_at=NOW,
    )
    session.add(sig)
    session.commit()
    return sig


def _add_raw_item(session, title="Test Raw Item", source_id="test_source"):
    item = RawItem(
        id=uuid.uuid4(),
        source_id=source_id,
        modality="text",
        title=title,
        ingestion_status="new",
        status="new",
        metadata_={},
        first_seen_at=NOW,
        last_seen_at=NOW,
        fetched_at=NOW,
        created_at=NOW,
    )
    session.add(item)
    session.commit()
    return item


def _add_source_run(session, source_id="test_source", status="success"):
    run = SourceRun(
        id=uuid.uuid4(),
        source_id=source_id,
        source_type="web",
        status=status,
        items_found=5,
        items_new=3,
        items_duplicate=2,
        metadata_={},
        created_at=NOW,
    )
    session.add(run)
    session.commit()
    return run


def _add_digest(session):
    digest = Digest(
        id=uuid.uuid4(),
        digest_date=TODAY,
        title="测试简报",
        markdown_full="# 测试简报\n\n今日信号概述。",
        markdown_short="摘要",
        signal_ids=[],
        status="local_daily_report",
        created_at=NOW,
        updated_at=NOW,
    )
    session.add(digest)
    session.commit()
    return digest


def _add_evidence(session, signal_id=None, claim_text="Test evidence"):
    claim = SourceClaim(
        id=uuid.uuid4(),
        signal_id=uuid.UUID(signal_id) if signal_id else None,
        claim_text=claim_text,
        claim_type="hermes_extraction",
        evidence_level="secondary",
        risk_domains=[],
        entities=[],
        metadata_={},
        needs_human_review=False,
        created_at=NOW,
    )
    session.add(claim)
    session.commit()
    return claim


def _run_export(db_session, tmp_path, export_date="2025-05-05", dry_run=False):
    """Helper to run export with injected session."""
    from frontier_ai_risk_observer.obsidian.exporter import (
        ObsidianExportConfig,
        ObsidianExporter,
    )

    config = ObsidianExportConfig(
        vault_path=Path(tmp_path),
        export_date=export_date,
        dry_run=dry_run,
    )
    exporter = ObsidianExporter(config)
    exporter._get_session = lambda: db_session
    return exporter.export()


# ===========================================================================
# Evidence Placeholder Tests
# ===========================================================================


class TestEvidencePlaceholders:
    """Tests for fallback evidence placeholder generation."""

    def test_signal_with_url_no_evidence_creates_placeholder(self):
        """Signal with evidence URL but no linked evidence gets a placeholder."""
        session = _make_session()
        _add_signal(session, evidence_url="https://example.com/rsp")
        _add_digest(session)

        with tempfile.TemporaryDirectory() as tmp:
            result = _run_export(session, tmp)
            # Should have 1 evidence placeholder
            assert result.evidence_notes >= 1
            evidence_dir = Path(tmp) / "AI-Risk-Intelligence" / "03_Evidence"
            evidence_files = list(evidence_dir.glob("*placeholder*.md"))
            assert len(evidence_files) >= 1
            content = evidence_files[0].read_text(encoding="utf-8")
            assert "placeholder" in content.lower() or "not yet captured" in content

    def test_signal_with_existing_evidence_no_placeholder(self):
        """Signal with already linked evidence should not get a placeholder."""
        session = _make_session()
        sig = _add_signal(session, evidence_url="https://example.com/rsp")
        _add_evidence(session, signal_id=str(sig.id))
        _add_digest(session)

        with tempfile.TemporaryDirectory() as tmp:
            _run_export(session, tmp)
            # Should have 1 real evidence, 0 placeholders
            evidence_dir = Path(tmp) / "AI-Risk-Intelligence" / "03_Evidence"
            placeholder_files = list(evidence_dir.glob("*placeholder*.md"))
            assert len(placeholder_files) == 0

    def test_signal_without_url_no_placeholder(self):
        """Signal without evidence URL should not get a placeholder note."""
        session = _make_session()
        _add_signal(session, evidence_url=None)
        _add_digest(session)

        with tempfile.TemporaryDirectory() as tmp:
            result = _run_export(session, tmp)
            # No evidence items at all
            assert result.evidence_notes == 0

    def test_placeholder_marked_needs_review(self):
        """Evidence placeholder should be marked as needing review."""
        session = _make_session()
        _add_signal(session, evidence_url="https://example.com/rsp")
        _add_digest(session)

        with tempfile.TemporaryDirectory() as tmp:
            _run_export(session, tmp)
            evidence_dir = Path(tmp) / "AI-Risk-Intelligence" / "03_Evidence"
            placeholder_files = list(evidence_dir.glob("*placeholder*.md"))
            assert len(placeholder_files) >= 1
            content = placeholder_files[0].read_text(encoding="utf-8")
            assert "needs_review: true" in content or "needs review" in content.lower()

    def test_placeholder_links_to_signal(self):
        """Evidence placeholder should link to the signal note."""
        session = _make_session()
        _add_signal(session, evidence_url="https://example.com/rsp")
        _add_digest(session)

        with tempfile.TemporaryDirectory() as tmp:
            _run_export(session, tmp)
            evidence_dir = Path(tmp) / "AI-Risk-Intelligence" / "03_Evidence"
            placeholder_files = list(evidence_dir.glob("*placeholder*.md"))
            content = placeholder_files[0].read_text(encoding="utf-8")
            assert "01_Signals" in content


# ===========================================================================
# Review Queue Tests
# ===========================================================================


class TestReviewQueue:
    """Tests for review queue population."""

    def test_signal_without_evidence_in_review_queue(self):
        """Signal with no evidence items should appear in review queue."""
        session = _make_session()
        _add_signal(session, evidence_url=None)
        _add_digest(session)

        with tempfile.TemporaryDirectory() as tmp:
            _run_export(session, tmp)
            review_path = Path(tmp) / "AI-Risk-Intelligence" / "90_Review_Queue" / "needs-review.md"
            assert review_path.exists()
            content = review_path.read_text(encoding="utf-8")
            assert "Without Evidence" in content or "no evidence" in content.lower()

    def test_needs_review_signal_in_queue(self):
        """Signal marked needs_human_review should appear in review queue."""
        session = _make_session()
        _add_signal(session, needs_review=True)
        _add_digest(session)

        with tempfile.TemporaryDirectory() as tmp:
            _run_export(session, tmp)
            review_path = Path(tmp) / "AI-Risk-Intelligence" / "90_Review_Queue" / "needs-review.md"
            content = review_path.read_text(encoding="utf-8")
            assert "Needing Review" in content

    def test_failed_source_in_review_queue(self):
        """Failed source runs should appear in failed-sources.md."""
        session = _make_session()
        _add_source_run(session, status="error")
        _add_digest(session)

        with tempfile.TemporaryDirectory() as tmp:
            _run_export(session, tmp)
            failed_path = (
                Path(tmp) / "AI-Risk-Intelligence"
                / "90_Review_Queue" / "failed-sources.md"
            )
            assert failed_path.exists()
            content = failed_path.read_text(encoding="utf-8")
            assert "test_source" in content
            assert "No failed sources" not in content


# ===========================================================================
# Candidate Notes Tests
# ===========================================================================


class TestCandidateNotes:
    """Tests that raw items produce candidate notes."""

    def test_raw_item_produces_candidate_note(self):
        """Raw item in DB should produce a candidate note."""
        session = _make_session()
        _add_raw_item(session)
        _add_digest(session)

        with tempfile.TemporaryDirectory() as tmp:
            result = _run_export(session, tmp)
            assert result.candidate_notes >= 1
            cand_dir = Path(tmp) / "AI-Risk-Intelligence" / "02_Candidates"
            cand_files = list(cand_dir.glob("*.md"))
            assert len(cand_files) >= 1
            content = cand_files[0].read_text(encoding="utf-8")
            assert "Test Raw Item" in content

    def test_candidate_note_has_review_checklist(self):
        """Candidate note should include a review checklist."""
        session = _make_session()
        _add_raw_item(session)
        _add_digest(session)

        with tempfile.TemporaryDirectory() as tmp:
            _run_export(session, tmp)
            cand_dir = Path(tmp) / "AI-Risk-Intelligence" / "02_Candidates"
            cand_files = list(cand_dir.glob("*.md"))
            content = cand_files[0].read_text(encoding="utf-8")
            assert "Review Checklist" in content
            assert "What changed" in content

    def test_candidate_note_has_source_link(self):
        """Candidate note should link to the source note."""
        session = _make_session()
        _add_raw_item(session, source_id="techcrunch_ai")
        _add_digest(session)

        with tempfile.TemporaryDirectory() as tmp:
            _run_export(session, tmp)
            cand_dir = Path(tmp) / "AI-Risk-Intelligence" / "02_Candidates"
            cand_files = list(cand_dir.glob("*.md"))
            content = cand_files[0].read_text(encoding="utf-8")
            assert "04_Sources" in content


# ===========================================================================
# Run Notes Tests
# ===========================================================================


class TestRunNotes:
    """Tests that source runs produce run notes."""

    def test_source_run_produces_run_note(self):
        """Source run in DB should produce a run note."""
        session = _make_session()
        _add_source_run(session)
        _add_digest(session)

        with tempfile.TemporaryDirectory() as tmp:
            result = _run_export(session, tmp)
            assert result.run_notes >= 1
            run_dir = Path(tmp) / "AI-Risk-Intelligence" / "07_Runs"
            run_files = list(run_dir.glob("*.md"))
            assert len(run_files) >= 1
            content = run_files[0].read_text(encoding="utf-8")
            assert "test_source" in content

    def test_failed_run_in_run_note_and_review(self):
        """Failed source run should appear in both 07_Runs and review queue."""
        session = _make_session()
        _add_source_run(session, status="error")
        _add_digest(session)

        with tempfile.TemporaryDirectory() as tmp:
            _run_export(session, tmp)
            # Check run note
            run_dir = Path(tmp) / "AI-Risk-Intelligence" / "07_Runs"
            run_files = list(run_dir.glob("*.md"))
            assert len(run_files) >= 1
            content = run_files[0].read_text(encoding="utf-8")
            assert "error" in content.lower()
            # Check review queue
            failed_path = (
                Path(tmp) / "AI-Risk-Intelligence" / "90_Review_Queue" / "failed-sources.md"
            )
            assert failed_path.exists()
            review_content = failed_path.read_text(encoding="utf-8")
            assert "test_source" in review_content


# ===========================================================================
# Daily Note Linking Tests
# ===========================================================================


class TestDailyNoteLinking:
    """Tests for daily note linking to other note types."""

    def test_daily_note_links_to_signals(self):
        """Daily note should contain links to signal index."""
        session = _make_session()
        _add_signal(session)
        _add_digest(session)

        with tempfile.TemporaryDirectory() as tmp:
            _run_export(session, tmp)
            daily_path = Path(tmp) / "AI-Risk-Intelligence" / "00_Daily" / "2025-05-05.md"
            content = daily_path.read_text(encoding="utf-8")
            assert "Signal Index" in content or "01_Signals" in content

    def test_daily_note_links_to_candidates(self):
        """Daily note should contain links to candidate index."""
        session = _make_session()
        _add_raw_item(session)
        _add_digest(session)

        with tempfile.TemporaryDirectory() as tmp:
            _run_export(session, tmp)
            daily_path = Path(tmp) / "AI-Risk-Intelligence" / "00_Daily" / "2025-05-05.md"
            content = daily_path.read_text(encoding="utf-8")
            assert "Candidate Index" in content or "02_Candidates" in content

    def test_daily_note_links_to_evidence(self):
        """Daily note should link to evidence when evidence exists."""
        session = _make_session()
        sig = _add_signal(session, evidence_url="https://example.com")
        _add_evidence(session, signal_id=str(sig.id))
        _add_digest(session)

        with tempfile.TemporaryDirectory() as tmp:
            _run_export(session, tmp)
            daily_path = Path(tmp) / "AI-Risk-Intelligence" / "00_Daily" / "2025-05-05.md"
            content = daily_path.read_text(encoding="utf-8")
            assert "Evidence" in content

    def test_daily_note_links_to_review_queue(self):
        """Daily note should link to review queue when items need review."""
        session = _make_session()
        _add_signal(session, needs_review=True)
        _add_digest(session)

        with tempfile.TemporaryDirectory() as tmp:
            _run_export(session, tmp)
            daily_path = Path(tmp) / "AI-Risk-Intelligence" / "00_Daily" / "2025-05-05.md"
            content = daily_path.read_text(encoding="utf-8")
            assert "Review" in content or "90_Review_Queue" in content

    def test_daily_note_has_intelligence_links_section(self):
        """Daily note should have a 'Linked Intelligence Objects' section."""
        session = _make_session()
        _add_signal(session)
        _add_digest(session)

        with tempfile.TemporaryDirectory() as tmp:
            _run_export(session, tmp)
            daily_path = Path(tmp) / "AI-Risk-Intelligence" / "00_Daily" / "2025-05-05.md"
            content = daily_path.read_text(encoding="utf-8")
            assert "Linked Intelligence" in content or "Intelligence Objects" in content

    def test_daily_note_frontmatter_counts(self):
        """Daily note frontmatter should include counts."""
        session = _make_session()
        _add_signal(session)
        _add_raw_item(session)
        _add_source_run(session)
        _add_digest(session)

        with tempfile.TemporaryDirectory() as tmp:
            _run_export(session, tmp)
            daily_path = Path(tmp) / "AI-Risk-Intelligence" / "00_Daily" / "2025-05-05.md"
            content = daily_path.read_text(encoding="utf-8")
            assert "signals_count:" in content
            assert "candidates_count:" in content or "runs_count:" in content


# ===========================================================================
# Generated Block Markers Tests
# ===========================================================================


class TestGeneratedBlockMarkers:
    """Tests for generated block marker presence."""

    def test_daily_note_has_markers(self):
        """Daily note should have generated block markers."""
        session = _make_session()
        _add_digest(session)

        with tempfile.TemporaryDirectory() as tmp:
            _run_export(session, tmp)
            daily_path = Path(tmp) / "AI-Risk-Intelligence" / "00_Daily" / "2025-05-05.md"
            content = daily_path.read_text(encoding="utf-8")
            assert "BEGIN_AUTO_GENERATED" in content
            assert "END_AUTO_GENERATED" in content

    def test_signal_note_has_markers(self):
        """Signal note should have generated block markers."""
        session = _make_session()
        _add_signal(session)
        _add_digest(session)

        with tempfile.TemporaryDirectory() as tmp:
            _run_export(session, tmp)
            sig_dir = Path(tmp) / "AI-Risk-Intelligence" / "01_Signals"
            sig_files = list(sig_dir.glob("*.md"))
            content = sig_files[0].read_text(encoding="utf-8")
            assert "BEGIN_AUTO_GENERATED" in content
            assert "END_AUTO_GENERATED" in content


# ===========================================================================
# Inspect Script Tests
# ===========================================================================


class TestInspectScript:
    """Tests for the inspect_obsidian_export.py script."""

    def test_inspect_counts_notes(self):
        """Inspect script should count notes correctly."""
        from scripts.inspect_obsidian_export import inspect_vault

        session = _make_session()
        _add_signal(session)
        _add_digest(session)

        with tempfile.TemporaryDirectory() as tmp:
            _run_export(session, tmp)
            result = inspect_vault(Path(tmp))
            assert result.daily_notes >= 1
            assert result.signal_notes >= 1

    def test_inspect_detects_markers(self):
        """Inspect script should detect generated block markers."""
        from scripts.inspect_obsidian_export import inspect_vault

        session = _make_session()
        _add_digest(session)

        with tempfile.TemporaryDirectory() as tmp:
            _run_export(session, tmp)
            result = inspect_vault(Path(tmp))
            assert result.generated_markers_present is True

    def test_inspect_detects_daily_signal_links(self):
        """Inspect should detect if daily note links to signals."""
        from scripts.inspect_obsidian_export import inspect_vault

        session = _make_session()
        _add_signal(session)
        _add_digest(session)

        with tempfile.TemporaryDirectory() as tmp:
            _run_export(session, tmp)
            result = inspect_vault(Path(tmp))
            assert result.daily_links_to_signals is True

    def test_inspect_checks_signal_fields(self):
        """Inspect should check signal three-question fields."""
        from scripts.inspect_obsidian_export import inspect_vault

        session = _make_session()
        _add_signal(session)
        _add_digest(session)

        with tempfile.TemporaryDirectory() as tmp:
            _run_export(session, tmp)
            result = inspect_vault(Path(tmp))
            assert result.signal_has_what_changed is True
            assert result.signal_has_why_it_matters is True
            assert result.signal_has_what_to_watch is True

    def test_inspect_json_output(self):
        """Inspect should produce valid JSON output."""
        session = _make_session()
        _add_digest(session)

        with tempfile.TemporaryDirectory() as tmp:
            _run_export(session, tmp)
            from dataclasses import asdict  # noqa: I001

            from scripts.inspect_obsidian_export import inspect_vault

            result = inspect_vault(Path(tmp))
            data = asdict(result)
            json_str = json.dumps(data, default=str)
            parsed = json.loads(json_str)
            assert "daily_notes" in parsed

    def test_inspect_missing_vault(self):
        """Inspect should report error for missing vault."""
        from scripts.inspect_obsidian_export import inspect_vault

        result = inspect_vault(Path("/nonexistent/path"))
        assert len(result.errors) > 0

    def test_inspect_detects_failed_sources(self):
        """Inspect should detect non-empty failed-sources.md."""
        from scripts.inspect_obsidian_export import inspect_vault

        session = _make_session()
        _add_source_run(session, status="error")
        _add_digest(session)

        with tempfile.TemporaryDirectory() as tmp:
            _run_export(session, tmp)
            result = inspect_vault(Path(tmp))
            assert result.failed_sources_exists is True
            assert result.failed_sources_non_empty is True


# ===========================================================================
# Makefile Target Tests
# ===========================================================================


class TestMakefileTargets:
    """Tests that R1-12B Makefile targets exist."""

    def test_obsidian_inspect_target(self):
        makefile = Path("Makefile").read_text(encoding="utf-8")
        assert "obsidian-inspect:" in makefile

    def test_daily_report_and_obsidian_e2e_target(self):
        makefile = Path("Makefile").read_text(encoding="utf-8")
        assert "daily-report-and-obsidian-e2e:" in makefile

    def test_e2e_target_requires_vault_path(self):
        makefile = Path("Makefile").read_text(encoding="utf-8")
        assert "OBSIDIAN_VAULT_PATH" in makefile


# ===========================================================================
# Documentation Tests
# ===========================================================================


class TestDocsR12B:
    """Tests that documentation covers R1-12B features."""

    def test_claude_md_mentions_obsidian_inspect(self):
        content = Path("CLAUDE.md").read_text(encoding="utf-8")
        assert "obsidian-inspect" in content

    def test_skill_mentions_evidence_must_store(self):
        content = Path("skills/ai-risk-signal-observer/SKILL.md").read_text(
            encoding="utf-8"
        )
        assert "MUST store at least one evidence" in content

    def test_daily_prompt_mentions_evidence_must(self):
        content = Path("prompts/daily_report_prompt.md").read_text(encoding="utf-8")
        assert "必须" in content and "evidence_store" in content

    def test_finalize_prompt_mentions_evidence_store(self):
        content = Path("prompts/daily_report_finalize_prompt.md").read_text(
            encoding="utf-8"
        )
        assert "risk_evidence_store" in content
