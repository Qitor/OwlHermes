"""R1-13: Tests for Live Obsidian Research Logging.

Tests cover:
- ResearchEvent DB model
- Live research service (store, search, to_dict)
- LiveVaultConfig (from_env, defaults, validation)
- LiveVaultWriter (all methods, disabled mode, body truncation, human content)
- MCP schemas and tool functions
- MCP server registration (tool count = 22)
- Inspect script
- Makefile targets
- Documentation mentions

Tests do NOT require Hermes, Obsidian app, Obsidian CLI, Docker,
PostgreSQL, or external network.
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from frontier_ai_risk_observer.db.models import Base, ResearchEvent
from frontier_ai_risk_observer.mcp.schemas import (
    LiveEventAppendInput,
    LiveNoteUpsertInput,
    LiveRunFinalizeInput,
    LiveRunStartInput,
)
from frontier_ai_risk_observer.obsidian.live_writer import (
    ALLOWED_NOTE_TYPES,
    LiveEvent,
    LiveVaultConfig,
    LiveVaultWriter,
)
from frontier_ai_risk_observer.services.live_research import (
    ALLOWED_EVENT_TYPES,
    research_event_to_dict,
    search_research_events,
    store_research_event,
)

NOW = datetime.now(UTC)


def _make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        implicit_returning=False,
    )
    Base.metadata.create_all(
        engine,
        tables=[ResearchEvent.__table__],
    )
    TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return TestSession()


# ---------------------------------------------------------------------------
# TestResearchEventModel
# ---------------------------------------------------------------------------


class TestResearchEventModel:
    def test_create_research_event(self):
        session = _make_session()
        event = ResearchEvent(
            run_id="test-run",
            event_type="run_started",
            title="Test Run",
            body="A test run",
            source_id="anthropic_news",
            metadata_={"key": "value"},
            created_at=NOW,
        )
        session.add(event)
        session.commit()
        assert event.id is not None
        assert event.run_id == "test-run"
        assert event.event_type == "run_started"

    def test_research_event_optional_fields(self):
        session = _make_session()
        event = ResearchEvent(
            run_id="r2",
            event_type="note",
            title="Note",
            created_at=NOW,
        )
        session.add(event)
        session.commit()
        assert event.body is None
        assert event.source_id is None
        assert event.raw_item_id is None
        assert event.signal_id is None
        assert event.evidence_id is None


# ---------------------------------------------------------------------------
# TestLiveResearchService
# ---------------------------------------------------------------------------


class TestLiveResearchService:
    def test_store_research_event(self):
        session = _make_session()
        event = store_research_event(
            session,
            run_id="run-1",
            event_type="run_started",
            title="Daily Report",
        )
        assert event.id is not None
        assert event.run_id == "run-1"
        assert event.event_type == "run_started"

    def test_store_research_event_invalid_type(self):
        session = _make_session()
        try:
            store_research_event(
                session,
                run_id="run-1",
                event_type="invalid_type",
            )
            raise AssertionError("Should have raised ValueError")
        except ValueError as e:
            assert "invalid_type" in str(e)

    def test_search_research_events(self):
        session = _make_session()
        store_research_event(session, run_id="r1", event_type="run_started")
        store_research_event(session, run_id="r1", event_type="source_selected")
        store_research_event(session, run_id="r2", event_type="run_started")
        results = search_research_events(session, run_id="r1")
        assert len(results) == 2
        results = search_research_events(session, event_type="run_started")
        assert len(results) == 2

    def test_search_with_source_id(self):
        session = _make_session()
        store_research_event(
            session, run_id="r1", event_type="source_selected", source_id="s1"
        )
        store_research_event(
            session, run_id="r1", event_type="source_selected", source_id="s2"
        )
        results = search_research_events(session, source_id="s1")
        assert len(results) == 1

    def test_research_event_to_dict(self):
        session = _make_session()
        event = store_research_event(
            session,
            run_id="r1",
            event_type="note",
            title="Test",
            body="body text",
            metadata={"key": "val"},
        )
        d = research_event_to_dict(event)
        assert d["run_id"] == "r1"
        assert d["event_type"] == "note"
        assert d["title"] == "Test"
        assert d["body"] == "body text"
        assert d["metadata"] == {"key": "val"}
        assert isinstance(d["id"], str)

    def test_store_with_uuid_refs(self):
        session = _make_session()
        sid = str(uuid.uuid4())
        event = store_research_event(
            session,
            run_id="r1",
            event_type="signal_stored",
            signal_id=sid,
        )
        assert str(event.signal_id) == sid


# ---------------------------------------------------------------------------
# TestLiveVaultConfig
# ---------------------------------------------------------------------------


class TestLiveVaultConfig:
    def test_defaults(self):
        config = LiveVaultConfig(vault_path=Path("/tmp/vault"))
        assert config.live_logging_enabled is False
        assert config.runs_dir_name == "08_Live_Runs"
        assert config.append_to_daily is True
        assert config.flush_mode == "immediate"

    def test_from_env_defaults(self):
        old = {k: os.environ.pop(k, None) for k in [
            "OBSIDIAN_VAULT_PATH",
            "OBSIDIAN_LIVE_LOGGING_ENABLED",
            "OBSIDIAN_LIVE_FLUSH_MODE",
        ]}
        try:
            config = LiveVaultConfig.from_env()
            assert config.live_logging_enabled is False
        finally:
            for k, v in old.items():
                if v is not None:
                    os.environ[k] = v

    def test_from_env_enabled(self):
        old = os.environ.copy()
        try:
            os.environ["OBSIDIAN_VAULT_PATH"] = "/tmp/test_vault"
            os.environ["OBSIDIAN_LIVE_LOGGING_ENABLED"] = "true"
            config = LiveVaultConfig.from_env()
            assert config.live_logging_enabled is True
            assert config.vault_path == Path("/tmp/test_vault")
        finally:
            os.environ.clear()
            os.environ.update(old)

    def test_from_env_missing_vault_path(self):
        old = os.environ.copy()
        try:
            os.environ.pop("OBSIDIAN_VAULT_PATH", None)
            os.environ["OBSIDIAN_LIVE_LOGGING_ENABLED"] = "true"
            try:
                LiveVaultConfig.from_env()
                raise AssertionError("Should have raised ValueError")
            except ValueError as e:
                assert "OBSIDIAN_VAULT_PATH" in str(e)
        finally:
            os.environ.clear()
            os.environ.update(old)

    def test_from_env_invalid_flush_mode(self):
        old = os.environ.copy()
        try:
            os.environ["OBSIDIAN_VAULT_PATH"] = "/tmp/v"
            os.environ["OBSIDIAN_LIVE_LOGGING_ENABLED"] = "true"
            os.environ["OBSIDIAN_LIVE_FLUSH_MODE"] = "invalid"
            try:
                LiveVaultConfig.from_env()
                raise AssertionError("Should have raised ValueError")
            except ValueError as e:
                assert "invalid" in str(e)
        finally:
            os.environ.clear()
            os.environ.update(old)


# ---------------------------------------------------------------------------
# TestLiveVaultWriter
# ---------------------------------------------------------------------------


class TestLiveVaultWriter:
    def test_disabled_mode_returns_success(self):
        config = LiveVaultConfig(
            vault_path=Path("/tmp/vault"),
            live_logging_enabled=False,
        )
        writer = LiveVaultWriter(config)
        result = writer.start_run("test-run")
        assert result.success is True
        assert result.notes_written == 0

    def test_start_run_creates_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = LiveVaultConfig(
                vault_path=Path(tmp),
                live_logging_enabled=True,
                append_to_daily=False,
            )
            writer = LiveVaultWriter(config)
            result = writer.start_run("2026-05-05_143000")
            assert result.success is True
            assert result.notes_written >= 3

            vault = Path(tmp) / "AI-Risk-Intelligence" / "08_Live_Runs" / "2026-05-05_143000"
            assert vault.exists()
            assert (vault / "Sources").exists()
            assert (vault / "Candidates").exists()
            assert (vault / "Evidence").exists()
            assert (vault / "Signals").exists()
            assert (vault / "Live Research Log.md").exists()
            assert (vault / "Timeline.md").exists()
            assert (vault / "Failures.md").exists()

    def test_append_event_updates_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = LiveVaultConfig(
                vault_path=Path(tmp),
                live_logging_enabled=True,
                append_to_daily=False,
            )
            writer = LiveVaultWriter(config)
            writer.start_run("r1")
            event = LiveEvent(
                event_type="source_selected",
                title="Anthropic News",
                source_id="anthropic_news",
            )
            result = writer.append_event("r1", event)
            assert result.success is True
            assert result.notes_written >= 1

    def test_append_event_unknown_run_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = LiveVaultConfig(
                vault_path=Path(tmp),
                live_logging_enabled=True,
            )
            writer = LiveVaultWriter(config)
            event = LiveEvent(event_type="note", title="test")
            result = writer.append_event("nonexistent", event)
            assert result.success is False

    def test_upsert_source_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = LiveVaultConfig(
                vault_path=Path(tmp),
                live_logging_enabled=True,
                append_to_daily=False,
            )
            writer = LiveVaultWriter(config)
            writer.start_run("r1")
            result = writer.upsert_source_note(
                "r1", "anthropic_news", "Anthropic News", "## Status\nChecked today"
            )
            assert result.success is True
            assert result.notes_written >= 1

            note_path = (
                Path(tmp) / "AI-Risk-Intelligence" / "08_Live_Runs" / "r1"
                / "Sources" / "anthropic_news.md"
            )
            assert note_path.exists()

    def test_upsert_candidate_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = LiveVaultConfig(
                vault_path=Path(tmp),
                live_logging_enabled=True,
                append_to_daily=False,
            )
            writer = LiveVaultWriter(config)
            writer.start_run("r1")
            result = writer.upsert_candidate_note(
                "r1", "new-ai-model", "New AI Model", "## Summary\nA new model release"
            )
            assert result.success is True
            note_path = (
                Path(tmp) / "AI-Risk-Intelligence" / "08_Live_Runs" / "r1"
                / "Candidates" / "new-ai-model.md"
            )
            assert note_path.exists()

    def test_upsert_evidence_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = LiveVaultConfig(
                vault_path=Path(tmp),
                live_logging_enabled=True,
                append_to_daily=False,
            )
            writer = LiveVaultWriter(config)
            writer.start_run("r1")
            result = writer.upsert_evidence_note(
                "r1", "claim-1", "Claim 1", "## Claim\nEvidence text"
            )
            assert result.success is True

    def test_upsert_signal_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = LiveVaultConfig(
                vault_path=Path(tmp),
                live_logging_enabled=True,
                append_to_daily=False,
            )
            writer = LiveVaultWriter(config)
            writer.start_run("r1")
            result = writer.upsert_signal_note(
                "r1", "signal-1", "Signal 1",
                "## What Changed\nSomething\n## Why It Matters\nRisk"
            )
            assert result.success is True

    def test_record_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = LiveVaultConfig(
                vault_path=Path(tmp),
                live_logging_enabled=True,
                append_to_daily=False,
            )
            writer = LiveVaultWriter(config)
            writer.start_run("r1")
            result = writer.record_failure(
                "r1", "openai_blog", "timeout", "Connection timed out"
            )
            assert result.success is True
            failures_path = (
                Path(tmp) / "AI-Risk-Intelligence" / "08_Live_Runs" / "r1"
                / "Failures.md"
            )
            content = failures_path.read_text(encoding="utf-8")
            assert "openai_blog" in content
            assert "timeout" in content

    def test_finalize_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = LiveVaultConfig(
                vault_path=Path(tmp),
                live_logging_enabled=True,
                append_to_daily=False,
            )
            writer = LiveVaultWriter(config)
            writer.start_run("r1")
            result = writer.finalize_run("r1", summary={"signal_count": 3})
            assert result.success is True
            log_path = (
                Path(tmp) / "AI-Risk-Intelligence" / "08_Live_Runs" / "r1"
                / "Live Research Log.md"
            )
            content = log_path.read_text(encoding="utf-8")
            assert "completed" in content
            assert "signal_count" in content

    def test_body_truncation(self):
        config = LiveVaultConfig(
            vault_path=Path("/tmp/v"),
            live_logging_enabled=False,
            event_max_chars=100,
        )
        writer = LiveVaultWriter(config)
        long_body = "x" * 200
        truncated = writer._truncate_body(long_body)
        assert len(truncated) < 200
        assert "truncated" in truncated

    def test_buffered_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = LiveVaultConfig(
                vault_path=Path(tmp),
                live_logging_enabled=True,
                append_to_daily=False,
                flush_mode="buffered",
            )
            writer = LiveVaultWriter(config)
            writer.start_run("r1")
            event = LiveEvent(event_type="note", title="Buffered note")
            result = writer.append_event("r1", event)
            # In buffered mode, events are buffered, not written
            assert result.success is True
            assert result.notes_written == 0
            # Flush to write
            flush_result = writer.flush_buffer("r1")
            assert flush_result.success is True
            assert flush_result.notes_written >= 1

    def test_human_content_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = LiveVaultConfig(
                vault_path=Path(tmp),
                live_logging_enabled=True,
                append_to_daily=False,
            )
            writer = LiveVaultWriter(config)
            writer.start_run("r1")

            # Add human content to a source note
            note_path = (
                Path(tmp) / "AI-Risk-Intelligence" / "08_Live_Runs" / "r1"
                / "Sources" / "test.md"
            )
            # Write note first
            writer.upsert_source_note("r1", "test", "Test", "## Status\nOK")
            content = note_path.read_text(encoding="utf-8")
            # Add human content outside markers
            human_content = content.replace(
                "<!-- END_AUTO_GENERATED: hermes-ai-risk-observer -->",
                "<!-- END_AUTO_GENERATED: hermes-ai-risk-observer -->"
                "\n\n## My Notes\nHuman observation here",
            )
            note_path.write_text(human_content, encoding="utf-8")

            # Update the note
            writer.upsert_source_note("r1", "test", "Test Updated", "## Status\nUpdated")
            new_content = note_path.read_text(encoding="utf-8")
            assert "My Notes" in new_content
            assert "Human observation here" in new_content

    def test_generated_markers_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = LiveVaultConfig(
                vault_path=Path(tmp),
                live_logging_enabled=True,
                append_to_daily=False,
            )
            writer = LiveVaultWriter(config)
            writer.start_run("r1")
            log_path = (
                Path(tmp) / "AI-Risk-Intelligence" / "08_Live_Runs" / "r1"
                / "Live Research Log.md"
            )
            content = log_path.read_text(encoding="utf-8")
            assert "BEGIN_AUTO_GENERATED" in content
            assert "END_AUTO_GENERATED" in content


# ---------------------------------------------------------------------------
# TestLiveMCPTools
# ---------------------------------------------------------------------------


class TestLiveMCPTools:
    def test_live_run_start_schema(self):
        schema = LiveRunStartInput(run_id="r1", title="Test")
        assert schema.run_id == "r1"

    def test_live_event_append_schema(self):
        schema = LiveEventAppendInput(
            run_id="r1", event_type="source_selected", title="Test"
        )
        assert schema.event_type == "source_selected"

    def test_live_note_upsert_schema_validates_note_type(self):
        # Valid
        schema = LiveNoteUpsertInput(
            run_id="r1", note_type="signal", slug="test", title="T", body="B"
        )
        assert schema.note_type == "signal"

    def test_live_run_finalize_schema(self):
        schema = LiveRunFinalizeInput(run_id="r1", summary={"count": 5})
        assert schema.summary["count"] == 5

    def test_allowed_event_types(self):
        assert "run_started" in ALLOWED_EVENT_TYPES
        assert "run_finalized" in ALLOWED_EVENT_TYPES
        assert "note" in ALLOWED_EVENT_TYPES
        assert "warning" in ALLOWED_EVENT_TYPES

    def test_allowed_note_types(self):
        assert "source" in ALLOWED_NOTE_TYPES
        assert "candidate" in ALLOWED_NOTE_TYPES
        assert "evidence" in ALLOWED_NOTE_TYPES
        assert "signal" in ALLOWED_NOTE_TYPES
        assert "failure" in ALLOWED_NOTE_TYPES

    def test_arbitrary_path_not_accepted(self):
        """Note types are constrained — arbitrary types rejected."""
        assert "arbitrary" not in ALLOWED_NOTE_TYPES
        assert "../etc" not in ALLOWED_NOTE_TYPES


# ---------------------------------------------------------------------------
# TestMCPServerRegistration
# ---------------------------------------------------------------------------


class TestMCPServerRegistration:
    def test_tool_count(self):
        from frontier_ai_risk_observer.mcp.server import MCP_TOOL_FUNCTIONS

        assert len(MCP_TOOL_FUNCTIONS) == 22

    def test_live_tools_registered(self):
        from frontier_ai_risk_observer.mcp.server import MCP_TOOL_FUNCTIONS

        names = [f.__name__ for f in MCP_TOOL_FUNCTIONS]
        assert "risk_live_run_start" in names
        assert "risk_live_event_append" in names
        assert "risk_live_note_upsert" in names
        assert "risk_live_run_finalize" in names


# ---------------------------------------------------------------------------
# TestInspectScript
# ---------------------------------------------------------------------------


class TestInspectScript:
    def test_inspect_empty_vault(self):
        with tempfile.TemporaryDirectory() as tmp:
            from scripts.inspect_live_vault import inspect_live_vault

            result = inspect_live_vault(Path(tmp))
            assert result.run_count == 0
            assert len(result.errors) > 0  # 08_Live_Runs not found

    def test_inspect_live_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            from scripts.inspect_live_vault import inspect_live_run

            run_dir = Path(tmp) / "r1"
            run_dir.mkdir()
            (run_dir / "Sources").mkdir()
            (run_dir / "Candidates").mkdir()
            (run_dir / "Evidence").mkdir()
            (run_dir / "Signals").mkdir()
            (run_dir / "Live Research Log.md").write_text(
                "status: completed\n<!-- BEGIN_AUTO_GENERATED -->\n<!-- END_AUTO_GENERATED -->",
                encoding="utf-8",
            )
            (run_dir / "Sources" / "s1.md").write_text("# S1", encoding="utf-8")
            (run_dir / "Signals" / "sig1.md").write_text("# Sig1", encoding="utf-8")

            result = inspect_live_run(run_dir)
            assert result.source_notes == 1
            assert result.signal_notes == 1
            assert result.finalized is True
            assert result.generated_markers_present is True

    def test_inspect_json_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            from dataclasses import asdict

            from scripts.inspect_live_vault import inspect_live_vault

            result = inspect_live_vault(Path(tmp))
            data = asdict(result)
            assert isinstance(data, dict)
            json_str = json.dumps(data, ensure_ascii=False)
            assert "run_count" in json_str


# ---------------------------------------------------------------------------
# TestMakefileTargets
# ---------------------------------------------------------------------------


class TestMakefileTargets:
    def test_daily_report_live_vault_target(self):
        makefile = Path("Makefile").read_text(encoding="utf-8")
        assert "daily-report-live-vault" in makefile

    def test_live_vault_inspect_target(self):
        makefile = Path("Makefile").read_text(encoding="utf-8")
        assert "live-vault-inspect" in makefile

    def test_obsidian_open_live_run_target(self):
        makefile = Path("Makefile").read_text(encoding="utf-8")
        assert "obsidian-open-live-run" in makefile


# ---------------------------------------------------------------------------
# TestDocs
# ---------------------------------------------------------------------------


class TestDocs:
    def test_claude_md_mentions_live_vault(self):
        content = Path("CLAUDE.md").read_text(encoding="utf-8")
        assert "daily-report-live-vault" in content
        assert "live-vault-inspect" in content

    def test_claude_md_tool_count_22(self):
        content = Path("CLAUDE.md").read_text(encoding="utf-8")
        assert "22" in content  # 22 tool functions

    def test_skill_mentions_live_vault(self):
        content = Path("skills/ai-risk-signal-observer/SKILL.md").read_text(encoding="utf-8")
        assert "risk_live_run_start" in content
        assert "Live Vault Logging" in content

    def test_skill_says_no_chain_of_thought(self):
        content = Path("skills/ai-risk-signal-observer/SKILL.md").read_text(encoding="utf-8")
        ct_lower = content.lower()
        assert (
            "chain-of-thought" in ct_lower
            or "思维链" in content
            or "private" in ct_lower
        )

    def test_daily_prompt_mentions_live_run(self):
        content = Path("prompts/daily_report_prompt.md").read_text(encoding="utf-8")
        assert "risk_live_run_start" in content

    def test_finalize_prompt_mentions_live_finalize(self):
        content = Path("prompts/daily_report_finalize_prompt.md").read_text(encoding="utf-8")
        assert "risk_live_run_finalize" in content

    def test_env_example_mentions_live_logging(self):
        content = Path("configs/env.example").read_text(encoding="utf-8")
        assert "OBSIDIAN_LIVE_LOGGING_ENABLED" in content

    def test_hermes_config_has_live_tools(self):
        content = Path("configs/hermes_config.example.yaml").read_text(encoding="utf-8")
        assert "risk_live_run_start" in content
        assert "risk_live_run_finalize" in content

    def test_docs_24_exists(self):
        assert Path("docs/24_live_obsidian_research_logging.md").exists()

    def test_docs_23_updated_tool_count(self):
        content = Path("docs/23_obsidian_intelligence_vault.md").read_text(encoding="utf-8")
        assert "22 tools" in content
        assert "risk_live_run_start" in content


# ---------------------------------------------------------------------------
# R1-13B: E2E Validation & Research UX Hardening Tests
# ---------------------------------------------------------------------------


class TestR113BStatelessWriter:
    """Tests for the stateless writer fix (GAP 1)."""

    def test_ensure_run_tracked_auto_discover(self):
        """_ensure_run_tracked should discover runs from filesystem."""
        with tempfile.TemporaryDirectory() as tmp:
            config = LiveVaultConfig(
                vault_path=Path(tmp),
                live_logging_enabled=True,
                append_to_daily=False,
            )
            writer = LiveVaultWriter(config)
            # Start a run with one writer instance
            writer.start_run("discover-test")
            # Create a new writer instance (simulates stateless MCP call)
            writer2 = LiveVaultWriter(config)
            result = writer2._ensure_run_tracked("discover-test")
            assert result is not None
            assert result.name == "discover-test"

    def test_append_event_after_stateless_restart(self):
        """append_event should work across MCP calls (stateless)."""
        with tempfile.TemporaryDirectory() as tmp:
            config = LiveVaultConfig(
                vault_path=Path(tmp),
                live_logging_enabled=True,
                append_to_daily=False,
            )
            # Start run with one writer
            writer1 = LiveVaultWriter(config)
            writer1.start_run("stateless-test")
            # Append event with a new writer instance
            writer2 = LiveVaultWriter(config)
            event = LiveEvent(event_type="note", title="Stateless event")
            result = writer2.append_event("stateless-test", event)
            assert result.success is True

    def test_finalize_run_after_stateless_restart(self):
        """finalize_run should work across MCP calls (stateless)."""
        with tempfile.TemporaryDirectory() as tmp:
            config = LiveVaultConfig(
                vault_path=Path(tmp),
                live_logging_enabled=True,
                append_to_daily=False,
            )
            writer1 = LiveVaultWriter(config)
            writer1.start_run("finalize-stateless")
            writer2 = LiveVaultWriter(config)
            result = writer2.finalize_run("finalize-stateless")
            assert result.success is True


class TestR113BFailureNoteType:
    """Tests for failure note_type in upsert (GAP 3)."""

    def test_failure_in_allowed_note_types(self):
        assert "failure" in ALLOWED_NOTE_TYPES

    def test_live_note_upsert_schema_accepts_failure(self):
        schema = LiveNoteUpsertInput(
            run_id="r1", note_type="failure", slug="test-fail",
            title="Fail", body="Error msg"
        )
        assert schema.note_type == "failure"

    def test_live_note_upsert_schema_rejects_invalid(self):
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            LiveNoteUpsertInput(
                run_id="r1", note_type="arbitrary", slug="x",
                title="T", body="B"
            )


class TestR113BInspectEnhancements:
    """Tests for enhanced inspect_live_vault.py (GAP 5, 12)."""

    def test_cot_violation_detection(self):
        from scripts.inspect_live_vault import _check_cot_violations

        assert _check_cot_violations("This uses chain of thought reasoning")
        assert _check_cot_violations("隐含推理过程")
        assert not _check_cot_violations("Source checked, no risk change")

    def test_inspect_with_cot_violations(self):
        with tempfile.TemporaryDirectory() as tmp:
            from scripts.inspect_live_vault import inspect_live_run

            run_dir = Path(tmp) / "r1"
            run_dir.mkdir()
            (run_dir / "Sources").mkdir()
            (run_dir / "Candidates").mkdir()
            (run_dir / "Evidence").mkdir()
            (run_dir / "Signals").mkdir()
            (run_dir / "Timeline.md").write_text(
                "Chain of thought: let me think about this\n",
                encoding="utf-8",
            )
            result = inspect_live_run(run_dir)
            assert len(result.cot_violations) > 0

    def test_inspect_missing_note_types(self):
        with tempfile.TemporaryDirectory() as tmp:
            from scripts.inspect_live_vault import inspect_live_run

            run_dir = Path(tmp) / "r1"
            run_dir.mkdir()
            # No subdirs — all note types missing
            result = inspect_live_run(run_dir)
            assert "source" in result.missing_note_types
            assert "candidate" in result.missing_note_types
            assert "evidence" in result.missing_note_types
            assert "signal" in result.missing_note_types

    def test_inspect_requirements_check(self):
        """Test --require-* flags via _check_requirements."""
        import argparse

        from scripts.inspect_live_vault import LiveRunInspection, _check_requirements

        inspection = LiveRunInspection(
            run_id="test",
            source_notes=2,
            candidate_notes=1,
            evidence_notes=0,
            signal_notes=1,
            failures_count=0,
            finalized=False,
        )
        args = argparse.Namespace(
            require_events=5,
            require_finalized=True,
            require_note_types="source,candidate,evidence,signal",
        )
        # Should fail: not enough events, not finalized, missing evidence
        try:
            _check_requirements(inspection, args)
            raise AssertionError("Should have raised SystemExit")
        except SystemExit:
            pass


class TestR113BExportLiveRunLink:
    """Tests for daily export linking to live runs (GAP 4)."""

    def test_export_creates_live_run_index(self):
        """Live Run Index should be created by export."""
        with tempfile.TemporaryDirectory() as tmp:
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
            from frontier_ai_risk_observer.obsidian.exporter import (
                ObsidianExportConfig,
                ObsidianExporter,
            )

            engine = create_engine(
                "sqlite:///:memory:",
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                implicit_returning=False,
            )
            Base.metadata.create_all(
                engine,
                tables=[
                    Digest.__table__, Signal.__table__, SourceRun.__table__,
                    RawItem.__table__, SourceClaim.__table__,
                ],
            )
            session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
            now = datetime.now(UTC)
            session.add(Digest(
                id=uuid.uuid4(), digest_date=date.today(),
                title="Test", markdown_full="# Test", markdown_short="T",
                status="draft", created_at=now, updated_at=now,
            ))
            session.commit()

            config = ObsidianExportConfig(vault_path=Path(tmp))
            exporter = ObsidianExporter(config)
            exporter._get_session = lambda: session
            exporter.export()

            index_path = Path(tmp) / "AI-Risk-Intelligence" / "99_Indexes" / "Live Run Index.md"
            assert index_path.exists()

    def test_export_links_live_run_in_daily(self):
        """Daily note should link to live runs if they exist."""
        with tempfile.TemporaryDirectory() as tmp:
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
            from frontier_ai_risk_observer.obsidian.exporter import (
                ObsidianExportConfig,
                ObsidianExporter,
            )

            engine = create_engine(
                "sqlite:///:memory:",
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                implicit_returning=False,
            )
            Base.metadata.create_all(
                engine,
                tables=[
                    Digest.__table__, Signal.__table__, SourceRun.__table__,
                    RawItem.__table__, SourceClaim.__table__,
                ],
            )
            session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
            now = datetime.now(UTC)
            session.add(Digest(
                id=uuid.uuid4(), digest_date=date.today(),
                title="Test", markdown_full="# Test", markdown_short="T",
                status="draft", created_at=now, updated_at=now,
            ))
            session.commit()

            # Create a live run directory
            live_run = Path(tmp) / "AI-Risk-Intelligence" / "08_Live_Runs" / "2026-05-05_120000"
            live_run.mkdir(parents=True)
            (live_run / "Sources").mkdir()
            (live_run / "Live Research Log.md").write_text("Test", encoding="utf-8")

            config = ObsidianExportConfig(vault_path=Path(tmp))
            exporter = ObsidianExporter(config)
            exporter._get_session = lambda: session
            exporter.export()

            today_str = date.today().isoformat()
            daily_path = (
                Path(tmp) / "AI-Risk-Intelligence" / "00_Daily" / f"{today_str}.md"
            )
            content = daily_path.read_text(encoding="utf-8")
            assert "Live Research Run" in content


class TestR113BMakefileTargets:
    """Tests for new Makefile targets."""

    def test_daily_report_live_vault_e2e_target(self):
        makefile = Path("Makefile").read_text(encoding="utf-8")
        assert "daily-report-live-vault-e2e" in makefile

    def test_e2e_target_requires_events(self):
        makefile = Path("Makefile").read_text(encoding="utf-8")
        assert "--require-events" in makefile

    def test_e2e_target_requires_note_types(self):
        makefile = Path("Makefile").read_text(encoding="utf-8")
        assert "--require-note-types" in makefile

    def test_e2e_target_db_check(self):
        makefile = Path("Makefile").read_text(encoding="utf-8")
        assert "--db-check" in makefile


class TestR113BPromptHardening:
    """Tests for prompt hardening (GAP 5)."""

    def test_daily_prompt_mentions_run_id(self):
        content = Path("prompts/daily_report_prompt.md").read_text(encoding="utf-8")
        assert "run_id" in content

    def test_daily_prompt_lists_event_types(self):
        content = Path("prompts/daily_report_prompt.md").read_text(encoding="utf-8")
        assert "source_selected" in content
        assert "candidate_found" in content
        assert "signal_stored" in content

    def test_finalize_prompt_mentions_run_id(self):
        content = Path("prompts/daily_report_finalize_prompt.md").read_text(encoding="utf-8")
        assert "run_id" in content

    def test_interactive_prompt_mentions_run_id(self):
        content = Path("prompts/interactive_daily_report_prompt.md").read_text(encoding="utf-8")
        assert "run_id" in content
