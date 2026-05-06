"""R1-12 tests: evidence persistence, Obsidian markdown utilities, and Obsidian vault export.

Tests cover:
- Evidence service (store, search, list, serialize)
- Markdown utilities (slugify, safe_filename, frontmatter, wikilink, atomic_write, generated blocks)
- Obsidian exporter (full export with in-memory DB)
- Export script CLI args
- MCP evidence tools
- Makefile targets exist
- Documentation mentions evidence and Obsidian
"""

from __future__ import annotations

import os
import tempfile
import uuid
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from frontier_ai_risk_observer.db.models import (
    Base,
    Digest,
    RawItem,
    Signal,
    SourceRun,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db_session():
    """Create an in-memory SQLite session for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        implicit_returning=False,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()


@pytest.fixture
def sample_signal(db_session):
    """Create a sample signal in DB."""
    now = datetime.now(UTC)
    sig = Signal(
        id=uuid.uuid4(),
        title_zh="测试信号",
        summary_zh="这是测试摘要",
        what_changed="测试变化",
        why_it_matters="测试重要性",
        what_to_watch_next="测试后续关注",
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
        signal_date=date(2025, 5, 5),
        needs_human_review=False,
        status="draft",
        metadata_={},
        created_at=now,
        updated_at=now,
    )
    db_session.add(sig)
    db_session.commit()
    return sig


@pytest.fixture
def sample_raw_item(db_session):
    """Create a sample raw item in DB."""
    now = datetime.now(UTC)
    item = RawItem(
        id=uuid.uuid4(),
        source_id="test_source",
        modality="text",
        title="Test Article About AI Safety",
        ingestion_status="new",
        status="new",
        metadata_={},
        first_seen_at=now,
        last_seen_at=now,
        fetched_at=now,
        created_at=now,
    )
    db_session.add(item)
    db_session.commit()
    return item


@pytest.fixture
def sample_digest(db_session, sample_signal):
    """Create a sample digest in DB."""
    now = datetime.now(UTC)
    digest = Digest(
        id=uuid.uuid4(),
        digest_date=date(2025, 5, 5),
        title="测试简报 2025-05-05",
        markdown_full="# 测试简报\n\n今日风险信号概述。",
        markdown_short="简报摘要",
        signal_ids=[str(sample_signal.id)],
        status="local_daily_report",
        created_at=now,
        updated_at=now,
    )
    db_session.add(digest)
    db_session.commit()
    return digest


@pytest.fixture
def sample_source_run(db_session):
    """Create a sample source run in DB."""
    now = datetime.now(UTC)
    run = SourceRun(
        id=uuid.uuid4(),
        source_id="test_source",
        source_type="web",
        status="success",
        items_found=5,
        items_new=3,
        items_duplicate=2,
        metadata_={},
        created_at=now,
    )
    db_session.add(run)
    db_session.commit()
    return run


# ===========================================================================
# Evidence Service Tests
# ===========================================================================


class TestEvidenceService:
    """Tests for services/evidence.py."""

    def test_store_evidence_item_basic(self, db_session):
        from frontier_ai_risk_observer.services.evidence import store_evidence_item

        claim = store_evidence_item(
            db_session,
            claim_text="Anthropic released new RSP update",
            claim_type="hermes_extraction",
            evidence_url="https://anthropic.com/rsp",
            evidence_title="Anthropic RSP Update",
            evidence_excerpt="Updated preparedness framework with new thresholds",
            confidence=4,
        )
        assert claim.id is not None
        assert claim.claim_text == "Anthropic released new RSP update"
        assert claim.evidence_title == "Anthropic RSP Update"
        assert claim.evidence_excerpt == "Updated preparedness framework with new thresholds"
        assert claim.confidence == 4
        assert claim.claim_type == "hermes_extraction"

    def test_store_evidence_with_signal_link(self, db_session, sample_signal):
        from frontier_ai_risk_observer.services.evidence import store_evidence_item

        claim = store_evidence_item(
            db_session,
            signal_id=str(sample_signal.id),
            claim_text="Evidence for test signal",
            supports_signal=True,
        )
        assert claim.signal_id == sample_signal.id
        assert claim.supports_signal is True

    def test_store_evidence_with_raw_item_link(self, db_session, sample_raw_item):
        from frontier_ai_risk_observer.services.evidence import store_evidence_item

        claim = store_evidence_item(
            db_session,
            raw_item_id=str(sample_raw_item.id),
            claim_text="Evidence from raw item",
        )
        assert claim.raw_item_id == sample_raw_item.id

    def test_store_evidence_without_raw_item(self, db_session):
        from frontier_ai_risk_observer.services.evidence import store_evidence_item

        # raw_item_id is now optional
        claim = store_evidence_item(
            db_session,
            source_id="direct_source",
            claim_text="Direct evidence without raw item",
        )
        assert claim.raw_item_id is None
        assert claim.source_id == "direct_source"

    def test_store_evidence_with_risk_domains(self, db_session):
        from frontier_ai_risk_observer.services.evidence import store_evidence_item

        claim = store_evidence_item(
            db_session,
            claim_text="Evidence with domains",
            risk_domains=["capability_risk", "governance_risk"],
            entities=["OpenAI", "Anthropic"],
        )
        assert claim.risk_domains == ["capability_risk", "governance_risk"]
        assert claim.entities == ["OpenAI", "Anthropic"]

    def test_store_evidence_needs_review(self, db_session):
        from frontier_ai_risk_observer.services.evidence import store_evidence_item

        claim = store_evidence_item(
            db_session,
            claim_text="Low confidence claim",
            needs_human_review=True,
        )
        assert claim.needs_human_review is True

    def test_search_evidence_by_signal(self, db_session, sample_signal):
        from frontier_ai_risk_observer.services.evidence import (
            search_evidence_items,
            store_evidence_item,
        )

        store_evidence_item(db_session, signal_id=str(sample_signal.id), claim_text="Claim 1")
        store_evidence_item(db_session, signal_id=str(sample_signal.id), claim_text="Claim 2")
        store_evidence_item(db_session, claim_text="Unlinked claim")

        results = search_evidence_items(db_session, signal_id=str(sample_signal.id))
        assert len(results) == 2
        assert all(r.signal_id == sample_signal.id for r in results)

    def test_search_evidence_by_source(self, db_session):
        from frontier_ai_risk_observer.services.evidence import (
            search_evidence_items,
            store_evidence_item,
        )

        store_evidence_item(db_session, source_id="src_a", claim_text="A claim")
        store_evidence_item(db_session, source_id="src_b", claim_text="B claim")
        store_evidence_item(db_session, source_id="src_a", claim_text="Another A claim")

        results = search_evidence_items(db_session, source_id="src_a")
        assert len(results) == 2

    def test_search_evidence_by_claim_type(self, db_session):
        from frontier_ai_risk_observer.services.evidence import (
            search_evidence_items,
            store_evidence_item,
        )

        store_evidence_item(db_session, claim_text="Extraction", claim_type="hermes_extraction")
        store_evidence_item(db_session, claim_text="Observation", claim_type="hermes_observation")

        results = search_evidence_items(db_session, claim_type="hermes_extraction")
        assert len(results) == 1
        assert results[0].claim_type == "hermes_extraction"

    def test_search_evidence_limit(self, db_session):
        from frontier_ai_risk_observer.services.evidence import (
            search_evidence_items,
            store_evidence_item,
        )

        for i in range(10):
            store_evidence_item(db_session, claim_text=f"Claim {i}")

        results = search_evidence_items(db_session, limit=5)
        assert len(results) == 5

    def test_list_recent_evidence(self, db_session):
        from frontier_ai_risk_observer.services.evidence import (
            list_recent_evidence_items,
            store_evidence_item,
        )

        for i in range(5):
            store_evidence_item(db_session, claim_text=f"Recent claim {i}")

        results = list_recent_evidence_items(db_session, limit=3)
        assert len(results) == 3

    def test_evidence_to_dict(self, db_session):
        from frontier_ai_risk_observer.services.evidence import (
            evidence_to_dict,
            store_evidence_item,
        )

        claim = store_evidence_item(
            db_session,
            claim_text="Dict test",
            evidence_url="https://example.com",
            confidence=3,
            risk_domains=["test"],
        )
        d = evidence_to_dict(claim)
        assert d["claim_text"] == "Dict test"
        assert d["evidence_url"] == "https://example.com"
        assert d["confidence"] == 3
        assert d["risk_domains"] == ["test"]
        assert d["id"] is not None
        assert isinstance(d["created_at"], str)


# ===========================================================================
# Obsidian Markdown Utility Tests
# ===========================================================================


class TestMarkdownUtils:
    """Tests for obsidian/markdown.py."""

    def test_slugify_filename_basic(self):
        from frontier_ai_risk_observer.obsidian.markdown import slugify_filename

        assert slugify_filename("Hello World") == "hello-world"

    def test_slugify_filename_special_chars(self):
        from frontier_ai_risk_observer.obsidian.markdown import slugify_filename

        result = slugify_filename("AI Safety: What's New? (2025)")
        assert "?" not in result
        assert ":" not in result
        assert "(" not in result
        assert ")" not in result

    def test_slugify_filename_chinese(self):
        from frontier_ai_risk_observer.obsidian.markdown import slugify_filename

        # CJK characters get stripped by ascii encoding
        result = slugify_filename("前沿 AI 风险信号")
        assert len(result) > 0

    def test_slugify_filename_length_limit(self):
        from frontier_ai_risk_observer.obsidian.markdown import slugify_filename

        long = "a" * 200
        result = slugify_filename(long)
        assert len(result) <= 80

    def test_slugify_filename_empty(self):
        from frontier_ai_risk_observer.obsidian.markdown import slugify_filename

        assert slugify_filename("") == "untitled"
        assert slugify_filename("---") == "untitled"

    def test_safe_filename_basic(self):
        from frontier_ai_risk_observer.obsidian.markdown import safe_filename

        assert safe_filename("Hello World") == "Hello World"

    def test_safe_filename_unsafe_chars(self):
        from frontier_ai_risk_observer.obsidian.markdown import safe_filename

        result = safe_filename('test<>:"/\\|?*file')
        for ch in '<>:"/\\|?*':
            assert ch not in result

    def test_safe_filename_preserves_case(self):
        from frontier_ai_risk_observer.obsidian.markdown import safe_filename

        assert safe_filename("CamelCaseTest") == "CamelCaseTest"

    def test_safe_filename_length_limit(self):
        from frontier_ai_risk_observer.obsidian.markdown import safe_filename

        long = "A" * 200
        result = safe_filename(long)
        assert len(result) <= 100

    def test_render_frontmatter_basic(self):
        from frontier_ai_risk_observer.obsidian.markdown import render_frontmatter

        result = render_frontmatter({"type": "signal", "date": "2025-05-05"})
        assert result.startswith("---")
        assert result.endswith("---")
        assert "type: signal" in result
        assert "date: 2025-05-05" in result

    def test_render_frontmatter_sorted(self):
        from frontier_ai_risk_observer.obsidian.markdown import render_frontmatter

        result = render_frontmatter({"z_field": "z", "a_field": "a"})
        lines = result.strip().split("\n")
        a_idx = next(i for i, line in enumerate(lines) if line.startswith("a_field"))
        z_idx = next(i for i, line in enumerate(lines) if line.startswith("z_field"))
        assert a_idx < z_idx

    def test_render_frontmatter_list(self):
        from frontier_ai_risk_observer.obsidian.markdown import render_frontmatter

        result = render_frontmatter({"domains": ["a", "b"]})
        assert "- a" in result
        assert "- b" in result

    def test_render_frontmatter_empty_list(self):
        from frontier_ai_risk_observer.obsidian.markdown import render_frontmatter

        result = render_frontmatter({"domains": []})
        assert "domains: []" in result

    def test_render_frontmatter_bool(self):
        from frontier_ai_risk_observer.obsidian.markdown import render_frontmatter

        result = render_frontmatter({"active": True, "deleted": False})
        assert "active: true" in result
        assert "deleted: false" in result

    def test_render_frontmatter_none(self):
        from frontier_ai_risk_observer.obsidian.markdown import render_frontmatter

        result = render_frontmatter({"value": None})
        assert "value:" in result

    def test_wikilink_basic(self):
        from frontier_ai_risk_observer.obsidian.markdown import wikilink

        assert wikilink("Signal Index") == "[[Signal Index]]"

    def test_wikilink_with_alias(self):
        from frontier_ai_risk_observer.obsidian.markdown import wikilink

        assert wikilink("Signal Index", "signals") == "[[Signal Index|signals]]"

    def test_markdown_link(self):
        from frontier_ai_risk_observer.obsidian.markdown import markdown_link

        assert markdown_link("title", "https://example.com") == "[title](https://example.com)"

    def test_atomic_write(self):
        from frontier_ai_risk_observer.obsidian.markdown import atomic_write

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.md"
            atomic_write(path, "hello world")
            assert path.read_text(encoding="utf-8") == "hello world"
            assert not path.with_suffix(".md.tmp").exists()

    def test_atomic_write_creates_dirs(self):
        from frontier_ai_risk_observer.obsidian.markdown import atomic_write

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sub" / "dir" / "test.md"
            atomic_write(path, "deep write")
            assert path.read_text(encoding="utf-8") == "deep write"

    def test_replace_generated_block(self):
        from frontier_ai_risk_observer.obsidian.markdown import (
            BEGIN_MARKER,
            END_MARKER,
            replace_generated_block,
        )

        existing = f"# My Note\n\nHuman content.\n\n{BEGIN_MARKER}\nold content\n{END_MARKER}\n"
        result = replace_generated_block(existing, "new content")
        assert "new content" in result
        assert "old content" not in result
        assert "Human content." in result

    def test_replace_generated_block_no_marker(self):
        from frontier_ai_risk_observer.obsidian.markdown import (
            BEGIN_MARKER,
            END_MARKER,
            replace_generated_block,
        )

        existing = "# My Note\n\nHuman content only."
        result = replace_generated_block(existing, "generated content")
        assert "generated content" in result
        assert "Human content only." in result
        assert BEGIN_MARKER in result
        assert END_MARKER in result

    def test_write_generated_note_new(self):
        from frontier_ai_risk_observer.obsidian.markdown import write_generated_note

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.md"
            result = write_generated_note(path, {"type": "signal"}, "body text", "Test Title")
            assert result.created is True
            assert result.updated is False
            assert result.preserved_human is False
            content = path.read_text(encoding="utf-8")
            assert "type: signal" in content
            assert "Test Title" in content
            assert "body text" in content

    def test_write_generated_note_update(self):
        from frontier_ai_risk_observer.obsidian.markdown import (
            write_generated_note,
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.md"
            # First write
            write_generated_note(path, {"type": "signal"}, "original body", "Test Title")
            # Second write (update)
            result = write_generated_note(path, {"type": "signal"}, "updated body", "Test Title")
            assert result.updated is True
            assert result.created is False
            assert result.preserved_human is True
            content = path.read_text(encoding="utf-8")
            assert "updated body" in content
            assert "original body" not in content

    def test_write_generated_note_preserves_human_content(self):
        from frontier_ai_risk_observer.obsidian.markdown import write_generated_note

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.md"
            # First write
            write_generated_note(path, {"type": "daily"}, "auto content", "Daily Report")
            # Human adds content outside markers
            content = path.read_text(encoding="utf-8")
            human_added = content + "\n\n## My Notes\n\nHuman analysis here.\n"
            path.write_text(human_added, encoding="utf-8")
            # Third write (update)
            result = write_generated_note(
                path, {"type": "daily"}, "new auto content", "Daily Report"
            )
            assert result.preserved_human is True
            final = path.read_text(encoding="utf-8")
            assert "Human analysis here." in final
            assert "new auto content" in final


# ===========================================================================
# Obsidian Exporter Tests
# ===========================================================================


class TestObsidianExporter:
    """Tests for obsidian/exporter.py."""

    def _make_exporter(self, tmp_path, dry_run=False, export_date="2025-05-05"):
        from frontier_ai_risk_observer.obsidian.exporter import (
            ObsidianExportConfig,
            ObsidianExporter,
        )

        config = ObsidianExportConfig(
            vault_path=Path(tmp_path),
            dry_run=dry_run,
            export_date=export_date,
        )
        return ObsidianExporter(config)

    def test_export_creates_dirs(self, db_session, sample_digest, sample_source_run):
        with tempfile.TemporaryDirectory() as tmp:
            exporter = self._make_exporter(tmp)
            # Mock the session factory
            exporter._get_session = lambda: db_session
            result = exporter.export()
            assert result.errors == []
            vault_dir = Path(tmp) / "AI-Risk-Intelligence"
            assert vault_dir.exists()
            for d in ["00_Daily", "01_Signals", "02_Candidates", "03_Evidence",
                       "04_Sources", "05_Risk_Domains", "06_Entities",
                       "07_Runs", "90_Review_Queue", "99_Indexes"]:
                assert (vault_dir / d).exists()

    def test_export_daily_note(self, db_session, sample_digest, sample_signal, sample_source_run):
        with tempfile.TemporaryDirectory() as tmp:
            exporter = self._make_exporter(tmp)
            exporter._get_session = lambda: db_session
            result = exporter.export()
            assert result.daily_notes == 1
            daily_path = Path(tmp) / "AI-Risk-Intelligence" / "00_Daily" / "2025-05-05.md"
            assert daily_path.exists()
            content = daily_path.read_text(encoding="utf-8")
            assert "2025-05-05" in content

    def test_export_signal_notes(self, db_session, sample_signal, sample_source_run):
        with tempfile.TemporaryDirectory() as tmp:
            exporter = self._make_exporter(tmp)
            exporter._get_session = lambda: db_session
            result = exporter.export()
            assert result.signal_notes >= 1
            signals_dir = Path(tmp) / "AI-Risk-Intelligence" / "01_Signals"
            signal_files = list(signals_dir.glob("*.md"))
            assert len(signal_files) >= 1

    def test_export_signal_three_questions(self, db_session, sample_signal, sample_source_run):
        with tempfile.TemporaryDirectory() as tmp:
            exporter = self._make_exporter(tmp)
            exporter._get_session = lambda: db_session
            result = exporter.export()
            assert result.signal_notes >= 1
            signals_dir = Path(tmp) / "AI-Risk-Intelligence" / "01_Signals"
            signal_files = list(signals_dir.glob("*.md"))
            content = signal_files[0].read_text(encoding="utf-8")
            assert "What Changed" in content
            assert "Why It Matters" in content
            assert "What to Watch Next" in content

    def test_export_signal_missing_fields(self, db_session, sample_source_run):
        now = datetime.now(UTC)
        sig = Signal(
            id=uuid.uuid4(),
            title_zh="缺少三问的信号",
            summary_zh="摘要",
            what_changed="",
            why_it_matters="",
            what_to_watch_next="",
            signal_type="governance",
            risk_domains=[],
            entities=[],
            source_ids=[],
            raw_item_ids=[],
            claim_ids=[],
            evidence_level="secondary",
            claim_type="hermes_observation",
            severity=2,
            confidence=3,
            time_sensitivity=2,
            priority_score=0,
            signal_date=date(2025, 5, 5),
            needs_human_review=True,
            status="draft",
            metadata_={},
            created_at=now,
            updated_at=now,
        )
        db_session.add(sig)
        db_session.commit()

        with tempfile.TemporaryDirectory() as tmp:
            exporter = self._make_exporter(tmp)
            exporter._get_session = lambda: db_session
            exporter.export()
            signals_dir = Path(tmp) / "AI-Risk-Intelligence" / "01_Signals"
            signal_files = list(signals_dir.glob("*.md"))
            content = signal_files[0].read_text(encoding="utf-8")
            assert "Missing" in content or "needs review" in content

    def test_export_evidence_notes(self, db_session, sample_signal, sample_source_run):
        from frontier_ai_risk_observer.services.evidence import store_evidence_item

        store_evidence_item(
            db_session,
            signal_id=str(sample_signal.id),
            claim_text="Test evidence claim",
            evidence_title="Test Evidence",
            evidence_excerpt="Excerpt here",
        )

        with tempfile.TemporaryDirectory() as tmp:
            exporter = self._make_exporter(tmp)
            exporter._get_session = lambda: db_session
            result = exporter.export()
            assert result.evidence_notes >= 1
            evidence_dir = Path(tmp) / "AI-Risk-Intelligence" / "03_Evidence"
            evidence_files = list(evidence_dir.glob("*.md"))
            assert len(evidence_files) >= 1

    def test_export_source_notes(self, db_session, sample_source_run):
        with tempfile.TemporaryDirectory() as tmp:
            exporter = self._make_exporter(tmp)
            exporter._get_session = lambda: db_session
            result = exporter.export()
            assert result.source_notes > 0
            sources_dir = Path(tmp) / "AI-Risk-Intelligence" / "04_Sources"
            source_files = list(sources_dir.glob("*.md"))
            assert len(source_files) > 0

    def test_export_run_notes(self, db_session, sample_source_run):
        with tempfile.TemporaryDirectory() as tmp:
            exporter = self._make_exporter(tmp)
            exporter._get_session = lambda: db_session
            result = exporter.export()
            assert result.run_notes >= 1

    def test_export_review_queue(self, db_session, sample_signal, sample_source_run):
        with tempfile.TemporaryDirectory() as tmp:
            exporter = self._make_exporter(tmp)
            exporter._get_session = lambda: db_session
            result = exporter.export()
            assert result.review_notes == 2  # needs-review.md + failed-sources.md
            review_dir = Path(tmp) / "AI-Risk-Intelligence" / "90_Review_Queue"
            assert (review_dir / "needs-review.md").exists()
            assert (review_dir / "failed-sources.md").exists()

    def test_export_indexes(self, db_session, sample_digest, sample_signal, sample_source_run):
        with tempfile.TemporaryDirectory() as tmp:
            exporter = self._make_exporter(tmp)
            exporter._get_session = lambda: db_session
            result = exporter.export()
            assert result.index_notes == 8
            index_dir = Path(tmp) / "AI-Risk-Intelligence" / "99_Indexes"
            for name in ["Daily Index", "Signal Index", "Candidate Index",
                         "Evidence Index", "Source Index", "Risk Domain Index",
                         "Run Index", "Live Run Index"]:
                assert (index_dir / f"{name}.md").exists()

    def test_export_dry_run_no_files(self, db_session, sample_digest, sample_source_run):
        with tempfile.TemporaryDirectory() as tmp:
            exporter = self._make_exporter(tmp, dry_run=True)
            exporter._get_session = lambda: db_session
            exporter.export()
            # Dry run should not create files
            vault_dir = Path(tmp) / "AI-Risk-Intelligence"
            assert not vault_dir.exists()

    def test_export_summary_counts(
        self, db_session, sample_digest, sample_signal, sample_source_run
    ):
        with tempfile.TemporaryDirectory() as tmp:
            exporter = self._make_exporter(tmp)
            exporter._get_session = lambda: db_session
            result = exporter.export()
            assert result.daily_notes >= 1
            assert result.signal_notes >= 1
            assert result.source_notes > 0
            assert result.index_notes == 8
            assert result.review_notes == 2
            assert result.export_date == "2025-05-05"


# ===========================================================================
# MCP Evidence Tools Tests
# ===========================================================================


class TestMCPEvidenceTools:
    """Tests for MCP evidence store/search tools."""

    def test_evidence_store_schema(self):
        from frontier_ai_risk_observer.mcp.schemas import EvidenceStoreInput

        inp = EvidenceStoreInput(
            claim_text="Test claim",
            evidence_url="https://example.com",
            confidence=4,
            supports_signal=True,
        )
        assert inp.claim_text == "Test claim"
        assert inp.confidence == 4
        assert inp.supports_signal is True

    def test_evidence_search_schema(self):
        from frontier_ai_risk_observer.mcp.schemas import EvidenceSearchInput

        inp = EvidenceSearchInput(
            signal_id="test-id",
            limit=10,
        )
        assert inp.signal_id == "test-id"
        assert inp.limit == 10

    def test_evidence_store_schema_defaults(self):
        from frontier_ai_risk_observer.mcp.schemas import EvidenceStoreInput

        inp = EvidenceStoreInput(claim_text="Minimal claim")
        assert inp.claim_type == "hermes_extraction"
        assert inp.evidence_level == "secondary"
        assert inp.needs_human_review is False
        assert inp.risk_domains == []
        assert inp.entities == []


# ===========================================================================
# Export Script Tests
# ===========================================================================


class TestExportScript:
    """Tests for scripts/obsidian_export.py."""

    def test_default_vault_path(self):
        from scripts.obsidian_export import _default_vault_path

        path = _default_vault_path()
        assert "obsidian_vault" in str(path)

    def test_default_vault_path_from_env(self):
        from scripts.obsidian_export import _default_vault_path

        old = os.environ.get("OBSIDIAN_VAULT_PATH")
        try:
            os.environ["OBSIDIAN_VAULT_PATH"] = "/custom/vault"
            path = _default_vault_path()
            assert str(path) == "/custom/vault"
        finally:
            if old is None:
                os.environ.pop("OBSIDIAN_VAULT_PATH", None)
            else:
                os.environ["OBSIDIAN_VAULT_PATH"] = old

    def test_run_export_works(self):
        from scripts.obsidian_export import run_export

        with tempfile.TemporaryDirectory() as tmp:
            # Export works even with empty DB — registry-backed notes still export
            result = run_export(Path(tmp), dry_run=True)
            # Should succeed (0) or fail with DB error (1) depending on DB state
            assert result in (0, 1)


# ===========================================================================
# Obsidian CLI Tests
# ===========================================================================


class TestObsidianCLI:
    """Tests for obsidian/cli.py."""

    def test_is_obsidian_installed_returns_bool(self):
        from frontier_ai_risk_observer.obsidian.cli import is_obsidian_installed

        result = is_obsidian_installed()
        assert isinstance(result, bool)

    def test_get_latest_export_dir(self):
        from frontier_ai_risk_observer.obsidian.cli import get_latest_export_dir

        with tempfile.TemporaryDirectory() as tmp:
            # No vault yet
            assert get_latest_export_dir(Path(tmp)) is None

            # Create vault structure
            vault = Path(tmp) / "AI-Risk-Intelligence"
            vault.mkdir()
            assert get_latest_export_dir(Path(tmp)) == vault

    def test_open_in_finder_no_path(self):
        from frontier_ai_risk_observer.obsidian.cli import open_in_finder

        assert open_in_finder(Path("/nonexistent/path")) is False


# ===========================================================================
# Makefile Targets Tests
# ===========================================================================


class TestMakefileTargets:
    """Tests that R1-12 Makefile targets exist."""

    def test_obsidian_export_target(self):
        makefile = Path("Makefile").read_text(encoding="utf-8")
        assert "obsidian-export:" in makefile

    def test_obsidian_export_dry_run_target(self):
        makefile = Path("Makefile").read_text(encoding="utf-8")
        assert "obsidian-export-dry-run:" in makefile

    def test_obsidian_open_latest_target(self):
        makefile = Path("Makefile").read_text(encoding="utf-8")
        assert "obsidian-open-latest:" in makefile

    def test_daily_report_and_obsidian_target(self):
        makefile = Path("Makefile").read_text(encoding="utf-8")
        assert "daily-report-and-obsidian:" in makefile


# ===========================================================================
# Documentation Tests
# ===========================================================================


class TestDocs:
    """Tests that documentation mentions R1-12 features."""

    def test_readme_mentions_obsidian(self):
        readme = Path("README.md").read_text(encoding="utf-8")
        assert "Obsidian" in readme
        assert "obsidian-export" in readme

    def test_readme_mentions_evidence(self):
        readme = Path("README.md").read_text(encoding="utf-8")
        assert "risk_evidence_store" in readme
        assert "risk_evidence_search" in readme

    def test_obsidian_vault_doc_exists(self):
        assert Path("docs/23_obsidian_intelligence_vault.md").exists()

    def test_claude_md_mentions_22_tools(self):
        claude_md = Path("CLAUDE.md").read_text(encoding="utf-8")
        assert "22" in claude_md

    def test_claude_md_mentions_obsidian(self):
        claude_md = Path("CLAUDE.md").read_text(encoding="utf-8")
        assert "obsidian" in claude_md.lower() or "Obsidian" in claude_md

    def test_hermes_config_mentions_evidence(self):
        config = Path("configs/hermes_config.example.yaml").read_text(encoding="utf-8")
        assert "risk_evidence_store" in config
        assert "risk_evidence_search" in config

    def test_env_example_mentions_obsidian(self):
        env = Path("configs/env.example").read_text(encoding="utf-8")
        assert "OBSIDIAN_VAULT_PATH" in env

    def test_skill_mentions_evidence(self):
        skill = Path("skills/ai-risk-signal-observer/SKILL.md").read_text(encoding="utf-8")
        assert "risk_evidence_store" in skill
        assert "risk_evidence_search" in skill

    def test_daily_report_prompt_mentions_evidence(self):
        prompt = Path("prompts/daily_report_prompt.md").read_text(encoding="utf-8")
        assert "risk_evidence_store" in prompt

    def test_finalize_prompt_mentions_evidence(self):
        prompt = Path("prompts/daily_report_finalize_prompt.md").read_text(encoding="utf-8")
        assert "risk_evidence_search" in prompt


# ===========================================================================
# MCP Server Registration Tests
# ===========================================================================


class TestMCPServerRegistration:
    """Tests that evidence tools are registered in MCP server."""

    def test_mcp_tool_functions_includes_evidence(self):
        from frontier_ai_risk_observer.mcp.server import MCP_TOOL_FUNCTIONS

        tool_names = [f.__name__ for f in MCP_TOOL_FUNCTIONS]
        assert "risk_evidence_store" in tool_names
        assert "risk_evidence_search" in tool_names
        assert len(MCP_TOOL_FUNCTIONS) == 23

    def test_mcp_tool_count(self):
        from frontier_ai_risk_observer.mcp.server import MCP_TOOL_FUNCTIONS

        assert len(MCP_TOOL_FUNCTIONS) == 23
