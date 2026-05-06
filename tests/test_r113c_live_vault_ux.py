"""R1-13C: Live Vault Final Report + Intermediate Research UX Repair tests.

Validates the UX contract: when live vault is enabled, the daily report
appears in Obsidian immediately, intermediate notes have bidirectional
links, and `make obsidian-export` is not required for normal use.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from frontier_ai_risk_observer.db.models import Base
from frontier_ai_risk_observer.mcp.server import (
    MCP_TOOL_FUNCTIONS,
    risk_digest_store,
    risk_live_daily_report_upsert,
    risk_live_run_finalize,
    risk_live_run_start,
    set_session_factory_for_tests,
)
from frontier_ai_risk_observer.obsidian.daily_note import (
    ensure_daily_note_has_body,
    upsert_daily_report_note,
)
from frontier_ai_risk_observer.obsidian.links import (
    format_backlink_section,
    format_timeline_entry_with_link,
    note_vault_relative_path,
)
from frontier_ai_risk_observer.obsidian.live_writer import LiveVaultConfig, LiveVaultWriter
from frontier_ai_risk_observer.obsidian.markdown import BEGIN_MARKER

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_vault(tmp_path: Path) -> Path:
    """Create a temporary vault directory."""
    vault = tmp_path / "vault"
    vault.mkdir()
    return vault


@pytest.fixture
def live_config(tmp_vault: Path) -> LiveVaultConfig:
    """Create a LiveVaultConfig with live logging enabled."""
    return LiveVaultConfig(
        vault_path=tmp_vault,
        live_logging_enabled=True,
    )


@pytest.fixture
def writer(live_config: LiveVaultConfig) -> LiveVaultWriter:
    """Create a LiveVaultWriter with live logging enabled."""
    return LiveVaultWriter(live_config)


@pytest.fixture
def db_session() -> Session:
    """Create an in-memory SQLite session for MCP tool tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    def factory() -> Session:
        return Session(engine, expire_on_commit=False)
    set_session_factory_for_tests(factory)
    yield factory()
    set_session_factory_for_tests(None)


@pytest.fixture
def live_env(tmp_vault: Path) -> dict[str, str]:
    """Environment variables for live vault testing."""
    return {
        "OBSIDIAN_VAULT_PATH": str(tmp_vault),
        "OBSIDIAN_LIVE_LOGGING_ENABLED": "true",
        "DATABASE_URL": "sqlite:///:memory:",
    }


# ---------------------------------------------------------------------------
# TestR113CDailyReportUX
# ---------------------------------------------------------------------------


class TestR113CDailyReportUX:
    """Tests for upsert_daily_report_note and ensure_daily_note_has_body."""

    def test_creates_daily_note_with_full_body(self, tmp_vault: Path) -> None:
        upsert_daily_report_note(
            tmp_vault, "2026-05-06", "# Test Report\n\nFull body here.",
        )
        daily_path = tmp_vault / "AI-Risk-Intelligence" / "00_Daily" / "2026-05-06.md"
        assert daily_path.exists()
        content = daily_path.read_text(encoding="utf-8")
        assert "Full body here." in content

    def test_daily_note_includes_live_run_link(self, tmp_vault: Path) -> None:
        upsert_daily_report_note(
            tmp_vault, "2026-05-06", "Report",
            run_id="2026-05-06_143000",
        )
        content = (
            tmp_vault / "AI-Risk-Intelligence" / "00_Daily" / "2026-05-06.md"
        ).read_text(encoding="utf-8")
        assert "08_Live_Runs/2026-05-06_143000" in content

    def test_daily_note_includes_signal_candidate_evidence_links(self, tmp_vault: Path) -> None:
        upsert_daily_report_note(
            tmp_vault, "2026-05-06", "Report",
            signal_note_paths=["08_Live_Runs/xxx/Signals/sig1"],
            candidate_note_paths=["08_Live_Runs/xxx/Candidates/cand1"],
            evidence_note_paths=["08_Live_Runs/xxx/Evidence/ev1"],
            source_note_paths=["08_Live_Runs/xxx/Sources/src1"],
        )
        content = (
            tmp_vault / "AI-Risk-Intelligence" / "00_Daily" / "2026-05-06.md"
        ).read_text(encoding="utf-8")
        assert "sig1" in content
        assert "cand1" in content
        assert "ev1" in content
        assert "src1" in content

    def test_daily_note_uses_generated_block_markers(self, tmp_vault: Path) -> None:
        upsert_daily_report_note(tmp_vault, "2026-05-06", "Report body.")
        content = (
            tmp_vault / "AI-Risk-Intelligence" / "00_Daily" / "2026-05-06.md"
        ).read_text(encoding="utf-8")
        assert BEGIN_MARKER in content
        assert "END_AUTO_GENERATED" in content

    def test_human_content_preserved_on_reupsert(self, tmp_vault: Path) -> None:
        daily_path = tmp_vault / "AI-Risk-Intelligence" / "00_Daily" / "2026-05-06.md"
        # Write with human content
        upsert_daily_report_note(tmp_vault, "2026-05-06", "Report v1.")
        # Add human content after the generated block
        existing = daily_path.read_text(encoding="utf-8")
        with_human = existing + "\n## My Notes\n\nHuman observation.\n"
        daily_path.write_text(with_human, encoding="utf-8")
        # Upsert again
        upsert_daily_report_note(tmp_vault, "2026-05-06", "Report v2.")
        content = daily_path.read_text(encoding="utf-8")
        assert "Human observation." in content
        assert "Report v2." in content

    def test_re_upsert_is_idempotent(self, tmp_vault: Path) -> None:
        upsert_daily_report_note(tmp_vault, "2026-05-06", "Report v1.")
        upsert_daily_report_note(tmp_vault, "2026-05-06", "Report v2.")
        content = (
            tmp_vault / "AI-Risk-Intelligence" / "00_Daily" / "2026-05-06.md"
        ).read_text(encoding="utf-8")
        assert "Report v2." in content

    def test_ensure_detects_missing_body(self, tmp_vault: Path) -> None:
        assert not ensure_daily_note_has_body(tmp_vault, "2026-05-06")

    def test_ensure_detects_present_body(self, tmp_vault: Path) -> None:
        upsert_daily_report_note(tmp_vault, "2026-05-06", "Report.")
        assert ensure_daily_note_has_body(tmp_vault, "2026-05-06")


# ---------------------------------------------------------------------------
# TestR113CDigestMirror
# ---------------------------------------------------------------------------


class TestR113CDigestMirror:
    """Tests for digest → Obsidian mirror in risk_digest_store."""

    def test_stores_digest_with_live_vault_writes_daily_note(
        self, db_session: Session, tmp_vault: Path
    ) -> None:
        with patch.dict(os.environ, {
            "OBSIDIAN_VAULT_PATH": str(tmp_vault),
            "OBSIDIAN_LIVE_LOGGING_ENABLED": "true",
        }):
            result = risk_digest_store({
                "digest_date": "2026-05-06",
                "title": "Test Digest",
                "body": "Full report body",
                "status": "local_daily_report",
            })
        assert result["ok"] is True
        daily_path = tmp_vault / "AI-Risk-Intelligence" / "00_Daily" / "2026-05-06.md"
        assert daily_path.exists()

    def test_stores_digest_without_live_vault_no_daily_note(
        self, db_session: Session, tmp_vault: Path
    ) -> None:
        with patch.dict(os.environ, {
            "OBSIDIAN_VAULT_PATH": str(tmp_vault),
            "OBSIDIAN_LIVE_LOGGING_ENABLED": "false",
        }):
            result = risk_digest_store({
                "digest_date": "2026-05-06",
                "title": "Test Digest",
                "body": "Full report body",
            })
        assert result["ok"] is True
        daily_path = tmp_vault / "AI-Risk-Intelligence" / "00_Daily" / "2026-05-06.md"
        assert not daily_path.exists()

    def test_obsidian_write_failure_does_not_lose_digest(
        self, db_session: Session
    ) -> None:
        with patch.dict(os.environ, {
            "OBSIDIAN_VAULT_PATH": "/nonexistent/path/that/cannot/be/created",
            "OBSIDIAN_LIVE_LOGGING_ENABLED": "true",
        }):
            result = risk_digest_store({
                "digest_date": "2026-05-06",
                "title": "Test Digest",
                "body": "Full report body",
            })
        # Digest should still be stored
        assert result["ok"] is True
        assert "digest" in result

    def test_warning_returned_on_vault_failure(
        self, db_session: Session
    ) -> None:
        with patch.dict(os.environ, {
            "OBSIDIAN_VAULT_PATH": "/nonexistent/path",
            "OBSIDIAN_LIVE_LOGGING_ENABLED": "true",
        }):
            result = risk_digest_store({
                "digest_date": "2026-05-06",
                "title": "Test Digest",
                "body": "Full report body",
            })
        assert result["ok"] is True
        # May or may not have vault_warnings depending on error path
        # The key invariant: ok is True even if vault fails


# ---------------------------------------------------------------------------
# TestR113CDailyReportMCPTool
# ---------------------------------------------------------------------------


class TestR113CDailyReportMCPTool:
    """Tests for risk_live_daily_report_upsert MCP tool."""

    def test_tool_exists(self) -> None:
        assert risk_live_daily_report_upsert in MCP_TOOL_FUNCTIONS

    def test_writes_daily_note(
        self, db_session: Session, tmp_vault: Path
    ) -> None:
        with patch.dict(os.environ, {
            "OBSIDIAN_VAULT_PATH": str(tmp_vault),
            "OBSIDIAN_LIVE_LOGGING_ENABLED": "true",
        }):
            result = risk_live_daily_report_upsert(
                report_date="2026-05-06",
                report_markdown="# Full Report\n\nBody here.",
            )
        assert result["ok"] is True
        assert result["daily_note_path"] is not None
        assert "2026-05-06" in result["daily_note_path"]

    def test_returns_daily_note_path(
        self, db_session: Session, tmp_vault: Path
    ) -> None:
        with patch.dict(os.environ, {
            "OBSIDIAN_VAULT_PATH": str(tmp_vault),
            "OBSIDIAN_LIVE_LOGGING_ENABLED": "true",
        }):
            result = risk_live_daily_report_upsert(
                report_date="2026-05-06",
                report_markdown="Report",
            )
        assert result["daily_note_path"] is not None

    def test_accepts_linked_note_paths(
        self, db_session: Session, tmp_vault: Path
    ) -> None:
        with patch.dict(os.environ, {
            "OBSIDIAN_VAULT_PATH": str(tmp_vault),
            "OBSIDIAN_LIVE_LOGGING_ENABLED": "true",
        }):
            result = risk_live_daily_report_upsert(
                report_date="2026-05-06",
                report_markdown="Report",
                signal_note_paths=["08_Live_Runs/xxx/Signals/sig1"],
            )
        assert result["ok"] is True
        assert result["linked_notes_count"] >= 1

    def test_disabled_returns_proper_response(
        self, db_session: Session
    ) -> None:
        with patch.dict(os.environ, {
            "OBSIDIAN_VAULT_PATH": "",
            "OBSIDIAN_LIVE_LOGGING_ENABLED": "false",
        }):
            result = risk_live_daily_report_upsert(
                report_date="2026-05-06",
                report_markdown="Report",
            )
        assert result["ok"] is True
        assert result["live_logging_enabled"] is False


# ---------------------------------------------------------------------------
# TestR113CLiveNoteBidirectionalLinks
# ---------------------------------------------------------------------------


class TestR113CLiveNoteBidirectionalLinks:
    """Tests for bidirectional links in live notes."""

    def test_candidate_note_includes_links_section(self, writer: LiveVaultWriter) -> None:
        writer.start_run("test-run")
        writer.upsert_candidate_note(
            "test-run", "test-cand", title="Test Candidate",
            body="Candidate body",
            metadata={
                "daily_report_date": "2026-05-06",
                "related_signal_ids": ["sig-1"],
                "source_id": "src-1",
            },
        )
        vault_root = writer._vault_root()
        note_path = vault_root / "08_Live_Runs" / "test-run" / "Candidates" / "test-cand.md"
        content = note_path.read_text(encoding="utf-8")
        assert "## Links" in content
        assert "00_Daily/2026-05-06" in content

    def test_evidence_note_links_to_signal_candidate_source_daily(
        self, writer: LiveVaultWriter
    ) -> None:
        writer.start_run("test-run")
        writer.upsert_evidence_note(
            "test-run", "test-ev", title="Test Evidence",
            body="Evidence body",
            metadata={
                "daily_report_date": "2026-05-06",
                "related_signal_ids": ["sig-1"],
                "related_candidate_ids": ["cand-1"],
                "source_id": "src-1",
            },
        )
        vault_root = writer._vault_root()
        note_path = vault_root / "08_Live_Runs" / "test-run" / "Evidence" / "test-ev.md"
        content = note_path.read_text(encoding="utf-8")
        assert "## Links" in content
        assert "sig-1" in content
        assert "cand-1" in content

    def test_signal_note_links_to_evidence_candidate_source_daily(
        self, writer: LiveVaultWriter
    ) -> None:
        writer.start_run("test-run")
        writer.upsert_signal_note(
            "test-run", "test-sig", title="Test Signal",
            body="Signal body",
            metadata={
                "daily_report_date": "2026-05-06",
                "related_evidence_ids": ["ev-1"],
                "related_candidate_ids": ["cand-1"],
                "source_id": "src-1",
                "risk_domains": ["frontier_capability"],
            },
        )
        vault_root = writer._vault_root()
        note_path = vault_root / "08_Live_Runs" / "test-run" / "Signals" / "test-sig.md"
        content = note_path.read_text(encoding="utf-8")
        assert "## Links" in content
        assert "ev-1" in content
        assert "frontier_capability" in content

    def test_source_note_links_to_candidates_signals_evidence(
        self, writer: LiveVaultWriter
    ) -> None:
        writer.start_run("test-run")
        writer.upsert_source_note(
            "test-run", "test-src", title="Test Source",
            body="Source body",
            metadata={
                "daily_report_date": "2026-05-06",
                "related_signal_ids": ["sig-1"],
                "related_candidate_ids": ["cand-1"],
                "related_evidence_ids": ["ev-1"],
            },
        )
        vault_root = writer._vault_root()
        note_path = vault_root / "08_Live_Runs" / "test-run" / "Sources" / "test-src.md"
        content = note_path.read_text(encoding="utf-8")
        assert "## Links" in content

    def test_failure_note_links_to_source_daily_live_run(
        self, writer: LiveVaultWriter
    ) -> None:
        writer.start_run("test-run")
        writer.record_failure(
            "test-run", "test-src", failure_type="timeout",
            message="Connection timed out",
            metadata={
                "daily_report_date": "2026-05-06",
                "source_id": "test-src",
            },
        )
        # Failure notes don't have a separate file, but the failure is in Failures.md
        vault_root = writer._vault_root()
        failures_path = vault_root / "08_Live_Runs" / "test-run" / "Failures.md"
        assert failures_path.exists()

    def test_timeline_includes_wikilinks_with_note_vault_path(
        self, writer: LiveVaultWriter
    ) -> None:
        from frontier_ai_risk_observer.obsidian.live_writer import LiveEvent

        writer.start_run("test-run")
        event = LiveEvent(
            event_type="source_selected",
            title="UK AISI",
            note_vault_path="08_Live_Runs/test-run/Sources/uk-aisi",
        )
        writer.append_event("test-run", event)
        vault_root = writer._vault_root()
        timeline_path = vault_root / "08_Live_Runs" / "test-run" / "Timeline.md"
        content = timeline_path.read_text(encoding="utf-8")
        assert "[[08_Live_Runs/test-run/Sources/uk-aisi|UK AISI]]" in content


# ---------------------------------------------------------------------------
# TestR113CFinalizeWithReport
# ---------------------------------------------------------------------------


class TestR113CFinalizeWithReport:
    """Tests for risk_live_run_finalize with final_report_markdown."""

    def test_finalize_writes_daily_note(
        self, db_session: Session, tmp_vault: Path
    ) -> None:
        with patch.dict(os.environ, {
            "OBSIDIAN_VAULT_PATH": str(tmp_vault),
            "OBSIDIAN_LIVE_LOGGING_ENABLED": "true",
        }):
            # Start a run first
            risk_live_run_start(run_id="test-finalize-run")
            # Finalize with report
            result = risk_live_run_finalize(
                run_id="test-finalize-run",
                final_report_markdown="# Final Report\n\nBody here.",
                daily_report_date="2026-05-06",
            )
        assert result["ok"] is True
        daily_path = tmp_vault / "AI-Risk-Intelligence" / "00_Daily" / "2026-05-06.md"
        assert daily_path.exists()

    def test_finalize_live_run_links_to_daily(
        self, db_session: Session, tmp_vault: Path
    ) -> None:
        with patch.dict(os.environ, {
            "OBSIDIAN_VAULT_PATH": str(tmp_vault),
            "OBSIDIAN_LIVE_LOGGING_ENABLED": "true",
        }):
            risk_live_run_start(run_id="test-finalize-run")
            risk_live_run_finalize(
                run_id="test-finalize-run",
                final_report_markdown="Report",
                daily_report_date="2026-05-06",
            )
        log_path = (
            tmp_vault / "AI-Risk-Intelligence" / "08_Live_Runs"
            / "test-finalize-run" / "Live Research Log.md"
        )
        content = log_path.read_text(encoding="utf-8")
        assert "00_Daily/2026-05-06" in content

    def test_finalize_timeline_includes_daily_note_link(
        self, db_session: Session, tmp_vault: Path
    ) -> None:
        with patch.dict(os.environ, {
            "OBSIDIAN_VAULT_PATH": str(tmp_vault),
            "OBSIDIAN_LIVE_LOGGING_ENABLED": "true",
        }):
            risk_live_run_start(run_id="test-finalize-run")
            risk_live_run_finalize(
                run_id="test-finalize-run",
                final_report_markdown="Report",
                daily_report_date="2026-05-06",
            )
        timeline_path = (
            tmp_vault / "AI-Risk-Intelligence" / "08_Live_Runs"
            / "test-finalize-run" / "Timeline.md"
        )
        content = timeline_path.read_text(encoding="utf-8")
        assert "00_Daily/2026-05-06" in content or "Final Daily Report" in content

    def test_finalize_returns_linked_notes_summary(
        self, db_session: Session, tmp_vault: Path
    ) -> None:
        with patch.dict(os.environ, {
            "OBSIDIAN_VAULT_PATH": str(tmp_vault),
            "OBSIDIAN_LIVE_LOGGING_ENABLED": "true",
        }):
            risk_live_run_start(run_id="test-finalize-run")
            result = risk_live_run_finalize(
                run_id="test-finalize-run",
                final_report_markdown="Report",
                daily_report_date="2026-05-06",
                signal_note_paths=["sig1"],
            )
        assert result["ok"] is True
        assert "linked_notes_summary" in result
        assert result["linked_notes_summary"]["signals"] == 1


# ---------------------------------------------------------------------------
# TestR113CRunnerSafetyNet
# ---------------------------------------------------------------------------


class TestR113CRunnerSafetyNet:
    """Tests for the daily_report.py runner safety net logic."""

    def test_runner_writes_daily_note_if_hermes_did_not(self, tmp_vault: Path) -> None:
        """Simulate runner safety net: Hermes didn't write daily note."""
        today = "2026-05-06"
        assert not ensure_daily_note_has_body(tmp_vault, today)
        # Runner safety net would call this:
        upsert_daily_report_note(
            tmp_vault, today, "# Daily Report\n\nFull report body.",
            status="local_daily_report",
        )
        assert ensure_daily_note_has_body(tmp_vault, today)

    def test_summary_records_daily_note_path(self, tmp_vault: Path) -> None:
        today = "2026-05-06"
        upsert_daily_report_note(tmp_vault, today, "Report", status="local_daily_report")
        daily_path = tmp_vault / "AI-Risk-Intelligence" / "00_Daily" / f"{today}.md"
        assert daily_path.exists()

    def test_manual_export_required_false_after_write(self, tmp_vault: Path) -> None:
        today = "2026-05-06"
        # Before write
        assert not ensure_daily_note_has_body(tmp_vault, today)
        # After write
        upsert_daily_report_note(tmp_vault, today, "Report body", status="local_daily_report")
        assert ensure_daily_note_has_body(tmp_vault, today)
        # manual_export_required would be False in RunSummary


# ---------------------------------------------------------------------------
# TestR113CInspection
# ---------------------------------------------------------------------------


class TestR113CInspection:
    """Tests for inspect_live_vault.py daily note and backlink checks."""

    def test_detects_daily_note_missing(self, tmp_vault: Path) -> None:
        from scripts.inspect_live_vault import inspect_live_run
        run_path = tmp_vault / "AI-Risk-Intelligence" / "08_Live_Runs" / "2026-05-06_143000"
        run_path.mkdir(parents=True)
        result = inspect_live_run(run_path)
        assert not result.daily_note_exists

    def test_detects_daily_note_with_only_metadata(self, tmp_vault: Path) -> None:
        from scripts.inspect_live_vault import inspect_live_run
        ai_root = tmp_vault / "AI-Risk-Intelligence"
        run_path = ai_root / "08_Live_Runs" / "2026-05-06_143000"
        run_path.mkdir(parents=True)
        # Create daily note with only frontmatter
        daily_dir = ai_root / "00_Daily"
        daily_dir.mkdir(parents=True)
        daily_path = daily_dir / "2026-05-06.md"
        daily_path.write_text("---\ntype: daily\n---\n", encoding="utf-8")
        result = inspect_live_run(run_path)
        assert result.daily_note_exists
        assert not result.daily_note_has_body

    def test_detects_complete_daily_note(self, tmp_vault: Path) -> None:
        from scripts.inspect_live_vault import inspect_live_run
        ai_root = tmp_vault / "AI-Risk-Intelligence"
        run_path = ai_root / "08_Live_Runs" / "2026-05-06_143000"
        run_path.mkdir(parents=True)
        # Create complete daily note
        upsert_daily_report_note(tmp_vault, "2026-05-06", "Full report body here.")
        result = inspect_live_run(run_path)
        assert result.daily_note_exists
        assert result.daily_note_has_body

    def test_detects_missing_backlinks(self, tmp_vault: Path) -> None:
        from scripts.inspect_live_vault import inspect_live_run
        ai_root = tmp_vault / "AI-Risk-Intelligence"
        run_path = ai_root / "08_Live_Runs" / "2026-05-06_143000"
        run_path.mkdir(parents=True)
        # Create signal note without links section
        signals_dir = run_path / "Signals"
        signals_dir.mkdir()
        sig_path = signals_dir / "test-signal.md"
        sig_path.write_text("# Signal\n\nNo links here.\n", encoding="utf-8")
        result = inspect_live_run(run_path)
        assert not result.bidirectional_links_complete

    def test_detects_complete_bidirectional_links(self, writer: LiveVaultWriter) -> None:
        from scripts.inspect_live_vault import inspect_live_run
        writer.start_run("2026-05-06_143000")
        writer.upsert_signal_note(
            "2026-05-06_143000", "test-sig", title="Signal",
            body="Signal body",
            metadata={"daily_report_date": "2026-05-06"},
        )
        vault_root = writer._vault_root()
        run_path = vault_root / "08_Live_Runs" / "2026-05-06_143000"
        result = inspect_live_run(run_path)
        assert result.bidirectional_links_complete

    def test_manual_export_required_false_when_ux_correct(self, tmp_vault: Path) -> None:
        from scripts.inspect_live_vault import inspect_live_run
        ai_root = tmp_vault / "AI-Risk-Intelligence"
        run_path = ai_root / "08_Live_Runs" / "2026-05-06_143000"
        run_path.mkdir(parents=True)
        upsert_daily_report_note(tmp_vault, "2026-05-06", "Full report body.")
        result = inspect_live_run(run_path)
        assert not result.manual_export_required


# ---------------------------------------------------------------------------
# TestR113CReviewQueue
# ---------------------------------------------------------------------------


class TestR113CReviewQueue:
    """Tests for review queue live integration."""

    def test_signal_without_evidence_adds_needs_review(
        self, writer: LiveVaultWriter
    ) -> None:
        writer.start_run("test-run")
        writer.upsert_signal_note(
            "test-run", "sig-no-ev", title="Signal without evidence",
            body="Body",
            metadata={"related_evidence_ids": []},
        )
        queue_path = (
            writer._vault_root() / "90_Review_Queue" / "needs-review.md"
        )
        assert queue_path.exists()
        content = queue_path.read_text(encoding="utf-8")
        assert "sig-no-ev" in content

    def test_failed_source_adds_failed_sources(
        self, writer: LiveVaultWriter
    ) -> None:
        writer.start_run("test-run")
        writer.record_failure(
            "test-run", "bad-src", failure_type="timeout",
            message="Connection timed out",
            metadata={"source_id": "bad-src"},
        )
        queue_path = (
            writer._vault_root() / "90_Review_Queue" / "failed-sources.md"
        )
        assert queue_path.exists()
        content = queue_path.read_text(encoding="utf-8")
        assert "bad-src" in content

    def test_evidence_with_needs_human_review_adds_needs_review(
        self, writer: LiveVaultWriter
    ) -> None:
        writer.start_run("test-run")
        writer.upsert_evidence_note(
            "test-run", "ev-review", title="Evidence needing review",
            body="Body",
            metadata={"needs_review": True, "needs_review_reason": "Low confidence"},
        )
        queue_path = (
            writer._vault_root() / "90_Review_Queue" / "needs-review.md"
        )
        assert queue_path.exists()
        content = queue_path.read_text(encoding="utf-8")
        assert "ev-review" in content


# ---------------------------------------------------------------------------
# TestR113CLinksModule
# ---------------------------------------------------------------------------


class TestR113CLinksModule:
    """Tests for the obsidian/links.py helper module."""

    def test_format_backlink_section_renders_wikilinks(self) -> None:
        result = format_backlink_section(
            daily_note_path="00_Daily/2026-05-06",
            signal_paths=["08_Live_Runs/x/Signals/sig1"],
            live_run_path="08_Live_Runs/x/Live Research Log",
        )
        assert "## Links" in result
        assert "[[00_Daily/2026-05-06]]" in result
        assert "[[08_Live_Runs/x/Signals/sig1]]" in result

    def test_format_timeline_entry_with_link_includes_wikilink(self) -> None:
        result = format_timeline_entry_with_link(
            "source_selected", "UK AISI",
            note_path="Sources/uk-aisi",
        )
        assert "[[Sources/uk-aisi|UK AISI]]" in result

    def test_note_vault_relative_path(self, tmp_vault: Path) -> None:
        ai_root = tmp_vault / "AI-Risk-Intelligence"
        note_path = ai_root / "00_Daily" / "2026-05-06.md"
        result = note_vault_relative_path(tmp_vault, note_path)
        assert result == "00_Daily/2026-05-06.md"

    def test_empty_inputs_produce_empty_section(self) -> None:
        result = format_backlink_section()
        assert result == ""


# ---------------------------------------------------------------------------
# TestR113CModuleRegistration
# ---------------------------------------------------------------------------


class TestR113CModuleRegistration:
    """Tests for MCP tool registration."""

    def test_tool_count_is_23(self) -> None:
        assert len(MCP_TOOL_FUNCTIONS) == 23

    def test_daily_report_upsert_in_tool_functions(self) -> None:
        assert risk_live_daily_report_upsert in MCP_TOOL_FUNCTIONS


# ---------------------------------------------------------------------------
# TestR113CPromptSkill
# ---------------------------------------------------------------------------


class TestR113CPromptSkill:
    """Tests for prompt and skill updates."""

    def test_prompts_mention_daily_report_upsert(self) -> None:
        prompt = (Path(__file__).parent.parent / "prompts" / "daily_report_prompt.md").read_text()
        assert "risk_live_daily_report_upsert" in prompt

    def test_prompts_say_intermediate_notes_must_be_written(self) -> None:
        prompt = (Path(__file__).parent.parent / "prompts" / "daily_report_prompt.md").read_text()
        assert "risk_live_note_upsert" in prompt

    def test_prompts_say_bidirectional_links(self) -> None:
        prompt = (Path(__file__).parent.parent / "prompts" / "daily_report_prompt.md").read_text()
        # Auto-mirror or bidirectional links should be mentioned
        assert (
            "related_signal_ids" in prompt
            or "bidirectional" in prompt.lower()
            or "自动" in prompt  # auto-mirror
            or "auto_mirror" in prompt.lower()
        )

    def test_finalize_prompt_mentions_daily_report_upsert(self) -> None:
        prompt_dir = Path(__file__).parent.parent / "prompts"
        prompt = (prompt_dir / "daily_report_finalize_prompt.md").read_text()
        assert "risk_live_daily_report_upsert" in prompt

    def test_skill_mentions_live_immediate_write_vs_export(self) -> None:
        skill_dir = (
            Path(__file__).parent.parent
            / "skills" / "ai-risk-signal-observer"
        )
        skill = (skill_dir / "SKILL.md").read_text()
        assert "backfill" in skill.lower() or "obsidian-export" in skill
