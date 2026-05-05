"""R1-09: Comprehensive tests for discovery helpers, registry validation,
source health, and MCP tools.
"""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Scrapling official page helper
# ---------------------------------------------------------------------------

class TestScraplingOfficialPage:
    """Tests for scrapling_official_page helper (offline)."""

    def test_extract_candidates_from_html_basic(self):
        from frontier_ai_risk_observer.helpers.scrapling_official_page import (
            extract_candidates_from_html,
        )

        html = (FIXTURES_DIR / "anthropic_news.html").read_text()
        candidates = extract_candidates_from_html(
            html=html,
            source_id="anthropic_news",
            base_url="https://www.anthropic.com",
        )
        # Should find the 4 article links, skip nav links
        assert len(candidates) == 4
        urls = [c.url for c in candidates]
        assert any("introducing-claude" in u for u in urls)
        assert any("election-safeguards" in u for u in urls)

    def test_extract_candidates_filters_navigation(self):
        from frontier_ai_risk_observer.helpers.scrapling_official_page import (
            extract_candidates_from_html,
        )

        html = (FIXTURES_DIR / "anthropic_news.html").read_text()
        candidates = extract_candidates_from_html(
            html=html,
            source_id="anthropic_news",
            base_url="https://www.anthropic.com",
        )
        # /about and /careers should be filtered as navigation
        urls = [c.url for c in candidates]
        assert not any(u.endswith("/about") for u in urls)
        assert not any(u.endswith("/careers") for u in urls)

    def test_extract_candidates_skip_javascript_and_anchors(self):
        from frontier_ai_risk_observer.helpers.scrapling_official_page import (
            extract_candidates_from_html,
        )

        html = (FIXTURES_DIR / "anthropic_news.html").read_text()
        candidates = extract_candidates_from_html(
            html=html,
            source_id="anthropic_news",
            base_url="https://www.anthropic.com",
        )
        for c in candidates:
            assert not c.url.startswith("javascript:")
            assert not c.url.startswith("#")

    def test_include_patterns(self):
        from frontier_ai_risk_observer.helpers.scrapling_official_page import (
            extract_candidates_from_html,
        )

        html = (FIXTURES_DIR / "anthropic_news.html").read_text()
        candidates = extract_candidates_from_html(
            html=html,
            source_id="anthropic_news",
            base_url="https://www.anthropic.com",
            include_patterns=["/news/"],
        )
        # Only links with /news/ in URL
        assert all("/news/" in c.url for c in candidates)
        assert len(candidates) >= 3  # At least 3 news links

    def test_exclude_patterns(self):
        from frontier_ai_risk_observer.helpers.scrapling_official_page import (
            extract_candidates_from_html,
        )

        html = (FIXTURES_DIR / "anthropic_news.html").read_text()
        candidates = extract_candidates_from_html(
            html=html,
            source_id="anthropic_news",
            base_url="https://www.anthropic.com",
            exclude_patterns=["election"],
        )
        urls = [c.url for c in candidates]
        assert not any("election" in u for u in urls)

    def test_limit(self):
        from frontier_ai_risk_observer.helpers.scrapling_official_page import (
            extract_candidates_from_html,
        )

        html = (FIXTURES_DIR / "anthropic_news.html").read_text()
        candidates = extract_candidates_from_html(
            html=html,
            source_id="anthropic_news",
            base_url="https://www.anthropic.com",
            limit=2,
        )
        assert len(candidates) == 2

    def test_dedup_urls(self):
        from frontier_ai_risk_observer.helpers.scrapling_official_page import (
            extract_candidates_from_html,
        )

        html = (
            '<html><body>'
            '<a href="/news/item1">Item 1</a>'
            '<a href="/news/item1">Item 1 again</a>'
            '</body></html>'
        )
        candidates = extract_candidates_from_html(
            html=html,
            source_id="test",
            base_url="https://example.com",
        )
        assert len(candidates) == 1

    def test_empty_html(self):
        from frontier_ai_risk_observer.helpers.scrapling_official_page import (
            extract_candidates_from_html,
        )

        candidates = extract_candidates_from_html(
            html="<html><body></body></html>",
            source_id="test",
            base_url="https://example.com",
        )
        assert candidates == []

    def test_candidate_item_fields(self):
        from frontier_ai_risk_observer.helpers.scrapling_official_page import (
            extract_candidates_from_html,
        )

        html = '<html><body><a href="/news/test-article">Test Article</a></body></html>'
        candidates = extract_candidates_from_html(
            html=html,
            source_id="test_source",
            base_url="https://example.com",
        )
        assert len(candidates) == 1
        c = candidates[0]
        assert c.source_id == "test_source"
        assert c.kind == "web_article"
        assert c.title == "Test Article"
        assert c.url.startswith("https://example.com/news/test-article")
        assert c.source_url == "https://example.com"
        assert c.discovery_method == "scrapling_official_page"


# ---------------------------------------------------------------------------
# RSS helper
# ---------------------------------------------------------------------------

class TestRSSHelper:
    """Tests for RSS helper (offline)."""

    def test_parse_rss_feed_basic(self):
        from frontier_ai_risk_observer.helpers.rss import parse_rss_feed

        feed = (FIXTURES_DIR / "techcrunch_ai_rss.xml").read_text()
        candidates = parse_rss_feed(
            feed_content=feed,
            source_id="techcrunch_ai",
            base_url="https://example.com/feed/",
        )
        assert len(candidates) == 3
        assert candidates[0].title == "Test Article One"
        assert candidates[0].discovery_method == "rss"

    def test_parse_rss_feed_strips_tracking(self):
        from frontier_ai_risk_observer.helpers.rss import parse_rss_feed

        feed = (FIXTURES_DIR / "techcrunch_ai_rss.xml").read_text()
        candidates = parse_rss_feed(
            feed_content=feed,
            source_id="techcrunch_ai",
            base_url="https://example.com/feed/",
        )
        # Article 2 has utm_source param; canonicalize should strip it
        article2 = candidates[1]
        assert "utm_source" not in article2.url

    def test_parse_rss_feed_limit(self):
        from frontier_ai_risk_observer.helpers.rss import parse_rss_feed

        feed = (FIXTURES_DIR / "techcrunch_ai_rss.xml").read_text()
        candidates = parse_rss_feed(
            feed_content=feed,
            source_id="techcrunch_ai",
            base_url="https://example.com/feed/",
            limit=1,
        )
        assert len(candidates) == 1

    def test_parse_rss_feed_published_at(self):
        from frontier_ai_risk_observer.helpers.rss import parse_rss_feed

        feed = (FIXTURES_DIR / "techcrunch_ai_rss.xml").read_text()
        candidates = parse_rss_feed(
            feed_content=feed,
            source_id="techcrunch_ai",
            base_url="https://example.com/feed/",
        )
        assert candidates[0].published_at is not None

    def test_parse_rss_feed_summary(self):
        from frontier_ai_risk_observer.helpers.rss import parse_rss_feed

        feed = (FIXTURES_DIR / "techcrunch_ai_rss.xml").read_text()
        candidates = parse_rss_feed(
            feed_content=feed,
            source_id="techcrunch_ai",
            base_url="https://example.com/feed/",
        )
        assert candidates[0].summary is not None

    def test_parse_rss_feed_empty(self):
        from frontier_ai_risk_observer.helpers.rss import parse_rss_feed

        candidates = parse_rss_feed(
            feed_content="<rss><channel></channel></rss>",
            source_id="test",
            base_url="https://example.com",
        )
        assert candidates == []


# ---------------------------------------------------------------------------
# Podcast helper
# ---------------------------------------------------------------------------

class TestPodcastHelper:
    """Tests for podcast RSS helper (offline)."""

    def test_parse_podcast_feed_basic(self):
        from frontier_ai_risk_observer.helpers.podcast import parse_podcast_feed

        feed = (FIXTURES_DIR / "axrp_podcast_rss.xml").read_text()
        candidates = parse_podcast_feed(
            feed_content=feed,
            source_id="axrp",
            base_url="https://example.com/podcast/",
        )
        assert len(candidates) == 2
        assert candidates[0].kind == "podcast_episode"
        assert candidates[0].discovery_method == "podcast_rss"

    def test_parse_podcast_feed_episode_titles(self):
        from frontier_ai_risk_observer.helpers.podcast import parse_podcast_feed

        feed = (FIXTURES_DIR / "axrp_podcast_rss.xml").read_text()
        candidates = parse_podcast_feed(
            feed_content=feed,
            source_id="axrp",
            base_url="https://example.com/podcast/",
        )
        titles = [c.title for c in candidates]
        assert "Episode 42: AI Safety with Guest" in titles
        assert "Episode 41: Eval Methodology" in titles


# ---------------------------------------------------------------------------
# arXiv helper
# ---------------------------------------------------------------------------

class TestArxivHelper:
    """Tests for arXiv helper (offline)."""

    def test_build_query_url(self):
        from frontier_ai_risk_observer.helpers.arxiv import build_query_url

        url = build_query_url("cat:cs.AI", max_results=10)
        assert "export.arxiv.org/api/query" in url
        assert "max_results=10" in url
        assert "sortBy=submittedDate" in url

    def test_parse_arxiv_atom_basic(self):
        from frontier_ai_risk_observer.helpers.arxiv import parse_arxiv_atom

        atom = (FIXTURES_DIR / "arxiv_response.xml").read_text()
        candidates = parse_arxiv_atom(atom, source_id="arxiv_test")
        assert len(candidates) == 2
        assert candidates[0].kind == "arxiv_paper"
        assert candidates[0].discovery_method == "arxiv_query"

    def test_parse_arxiv_atom_titles(self):
        from frontier_ai_risk_observer.helpers.arxiv import parse_arxiv_atom

        atom = (FIXTURES_DIR / "arxiv_response.xml").read_text()
        candidates = parse_arxiv_atom(atom, source_id="arxiv_test")
        titles = [c.title for c in candidates]
        assert "Test Paper on AI Safety" in titles
        assert "Another Test Paper on Alignment" in titles

    def test_parse_arxiv_atom_urls(self):
        from frontier_ai_risk_observer.helpers.arxiv import parse_arxiv_atom

        atom = (FIXTURES_DIR / "arxiv_response.xml").read_text()
        candidates = parse_arxiv_atom(atom, source_id="arxiv_test")
        assert candidates[0].url.startswith("http://arxiv.org/abs/")

    def test_parse_arxiv_atom_published_at(self):
        from frontier_ai_risk_observer.helpers.arxiv import parse_arxiv_atom

        atom = (FIXTURES_DIR / "arxiv_response.xml").read_text()
        candidates = parse_arxiv_atom(atom, source_id="arxiv_test")
        assert candidates[0].published_at is not None

    def test_parse_arxiv_atom_limit(self):
        from frontier_ai_risk_observer.helpers.arxiv import parse_arxiv_atom

        atom = (FIXTURES_DIR / "arxiv_response.xml").read_text()
        candidates = parse_arxiv_atom(atom, source_id="arxiv_test", limit=1)
        assert len(candidates) == 1

    def test_parse_arxiv_atom_empty(self):
        from frontier_ai_risk_observer.helpers.arxiv import parse_arxiv_atom

        atom = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'
        candidates = parse_arxiv_atom(atom, source_id="test")
        assert candidates == []

    def test_parse_arxiv_atom_summary(self):
        from frontier_ai_risk_observer.helpers.arxiv import parse_arxiv_atom

        atom = (FIXTURES_DIR / "arxiv_response.xml").read_text()
        candidates = parse_arxiv_atom(atom, source_id="arxiv_test")
        assert candidates[0].summary is not None


# ---------------------------------------------------------------------------
# CandidateItem model
# ---------------------------------------------------------------------------

class TestCandidateItemModel:
    """Tests for the CandidateItem shared model."""

    def test_create_minimal(self):
        from frontier_ai_risk_observer.helpers.models import CandidateItem

        item = CandidateItem(
            source_id="test",
            kind="web_article",
            title="Test",
            url="https://example.com/test",
            source_url="https://example.com",
            discovery_method="rss",
        )
        assert item.source_id == "test"
        assert item.published_at is None
        assert item.summary is None
        assert item.metadata == {}

    def test_create_full(self):
        from datetime import datetime

        from frontier_ai_risk_observer.helpers.models import CandidateItem

        item = CandidateItem(
            source_id="test",
            kind="podcast_episode",
            title="Test Episode",
            url="https://example.com/ep1",
            published_at=datetime(2026, 5, 4),
            summary="A test episode",
            content_text="Full content",
            source_url="https://example.com/feed",
            discovery_method="podcast_rss",
            metadata={"duration": 3600},
        )
        assert item.published_at is not None
        assert item.metadata["duration"] == 3600

    def test_model_dump_json(self):
        from frontier_ai_risk_observer.helpers.models import CandidateItem

        item = CandidateItem(
            source_id="test",
            kind="web_article",
            title="Test",
            url="https://example.com/test",
            source_url="https://example.com",
            discovery_method="scrapling_official_page",
        )
        dumped = item.model_dump(mode="json")
        assert dumped["source_id"] == "test"
        assert isinstance(dumped, dict)


# ---------------------------------------------------------------------------
# Registry validation with helper metadata
# ---------------------------------------------------------------------------

class TestRegistryHelperMetadata:
    """Tests for registry validation of helper metadata fields."""

    def test_source_entry_helper_type_valid(self):
        from frontier_ai_risk_observer.registry.validators import SourceEntry

        entry = SourceEntry(
            id="test",
            name="Test",
            category="lab",
            url="https://example.com",
            collector="manual",
            collection_method="manual",
            priority="high",
            helper_type="scrapling_official_page",
            scrapling_url="https://example.com/news",
        )
        assert entry.helper_type == "scrapling_official_page"

    def test_source_entry_helper_type_invalid(self):
        from pydantic import ValidationError

        from frontier_ai_risk_observer.registry.validators import SourceEntry

        with pytest.raises(ValidationError):
            SourceEntry(
                id="test",
                name="Test",
                category="lab",
                url="https://example.com",
                collector="manual",
                collection_method="manual",
                priority="high",
                helper_type="nonexistent_type",
            )

    def test_source_entry_scrapling_url_invalid(self):
        from pydantic import ValidationError

        from frontier_ai_risk_observer.registry.validators import SourceEntry

        with pytest.raises(ValidationError):
            SourceEntry(
                id="test",
                name="Test",
                category="lab",
                url="https://example.com",
                collector="manual",
                collection_method="manual",
                priority="high",
                scrapling_url="not-a-url",
            )

    def test_source_entry_include_patterns(self):
        from frontier_ai_risk_observer.registry.validators import SourceEntry

        entry = SourceEntry(
            id="test",
            name="Test",
            category="lab",
            url="https://example.com",
            collector="manual",
            collection_method="manual",
            priority="high",
            link_include_patterns=["/news/", "/research/"],
        )
        assert len(entry.link_include_patterns) == 2

    def test_source_entry_empty_pattern_rejected(self):
        from pydantic import ValidationError

        from frontier_ai_risk_observer.registry.validators import SourceEntry

        with pytest.raises(ValidationError):
            SourceEntry(
                id="test",
                name="Test",
                category="lab",
                url="https://example.com",
                collector="manual",
                collection_method="manual",
                priority="high",
                link_include_patterns=["/news/", ""],
            )

    def test_podcast_entry_helper_type_valid(self):
        from frontier_ai_risk_observer.registry.validators import PodcastEntry

        entry = PodcastEntry(
            id="test",
            name="Test",
            feed_url="https://example.com/feed",
            collector="manual",
            collection_method="manual",
            helper_type="podcast_rss",
        )
        assert entry.helper_type == "podcast_rss"

    def test_event_entry_helper_type_valid(self):
        from frontier_ai_risk_observer.registry.validators import EventEntry

        entry = EventEntry(
            id="test",
            name="Test",
            url="https://example.com",
            category="summit",
            helper_type="manual",
            known_issues="URL may be stale",
        )
        assert entry.helper_type == "manual"
        assert entry.known_issues is not None

    def test_benchmark_entry_helper_type_valid(self):
        from frontier_ai_risk_observer.registry.validators import BenchmarkEntry

        entry = BenchmarkEntry(
            id="test",
            name="Test",
            category="safety",
            source_url="https://example.com",
            helper_type="scrapling_official_page",
            scrapling_url="https://example.com/benchmark",
        )
        assert entry.helper_type == "scrapling_official_page"

    def test_event_entry_archive_urls_invalid(self):
        from pydantic import ValidationError

        from frontier_ai_risk_observer.registry.validators import EventEntry

        with pytest.raises(ValidationError):
            EventEntry(
                id="test",
                name="Test",
                url="https://example.com",
                category="summit",
                archive_urls=["not-a-url"],
            )


# ---------------------------------------------------------------------------
# Source health service
# ---------------------------------------------------------------------------

class TestSourceHealth:
    """Tests for source health reporting."""

    def test_source_health_summary_structure(self):
        from frontier_ai_risk_observer.services.source_health import source_health_summary

        summary = source_health_summary()
        assert summary["ok"] is True
        assert "helper_coverage" in summary
        assert "scrapling_entries" in summary
        assert "missing_scrapling_url" in summary
        assert "missing_feed_url" in summary
        assert "known_issues_count" in summary
        assert "requires_human_review_count" in summary
        assert "invalid_urls_count" in summary

    def test_source_health_helper_coverage(self):
        from frontier_ai_risk_observer.services.source_health import source_health_summary

        summary = source_health_summary()
        coverage = summary["helper_coverage"]
        # Should have at least some source entries with helpers
        has_helper = any(
            "scrapling_official_page" in key or "rss" in key or "arxiv_query" in key
            for key in coverage
        )
        assert has_helper

    def test_source_health_known_issues(self):
        from frontier_ai_risk_observer.services.source_health import source_health_summary

        summary = source_health_summary()
        # Should have at least one known issue (from registry entries)
        assert isinstance(summary["known_issues_count"], int)


# ---------------------------------------------------------------------------
# MCP tool: risk_source_health_summary
# ---------------------------------------------------------------------------

class TestMCPSourceHealth:
    """Tests for the risk_source_health_summary MCP tool."""

    def test_returns_ok(self):
        from frontier_ai_risk_observer.mcp.server import risk_source_health_summary

        result = risk_source_health_summary()
        assert result["ok"] is True
        assert "helper_coverage" in result or "registry" in result


# ---------------------------------------------------------------------------
# MCP tool: risk_discovery_helper_preview
# ---------------------------------------------------------------------------

class TestMCPDiscoveryHelperPreview:
    """Tests for the risk_discovery_helper_preview MCP tool."""

    def test_nonexistent_source(self):
        from frontier_ai_risk_observer.mcp.server import risk_discovery_helper_preview

        result = risk_discovery_helper_preview(source_id="nonexistent_source_12345")
        assert result["ok"] is False
        assert result["error_type"] == "not_found"

    def test_no_fetch_returns_would_fetch(self):
        from frontier_ai_risk_observer.mcp.server import risk_discovery_helper_preview

        # Find a source with a helper
        from frontier_ai_risk_observer.registry.loader import load_registry_bundle
        from frontier_ai_risk_observer.registry.validators import validate_registry_bundle

        bundle = load_registry_bundle()
        validated = validate_registry_bundle(bundle)

        source_id = None
        for entry in validated.sources:
            ht = getattr(entry, "helper_type", None)
            if ht and ht not in ("none", "manual"):
                source_id = entry.id
                break

        if source_id is None:
            pytest.skip("No source with helper configured")

        result = risk_discovery_helper_preview(source_id=source_id, fetch=False)
        assert result["ok"] is True
        assert result.get("would_fetch") is True or result.get("candidates") is not None

    def test_manual_source_returns_empty(self):
        from frontier_ai_risk_observer.mcp.server import risk_discovery_helper_preview
        from frontier_ai_risk_observer.registry.loader import load_registry_bundle
        from frontier_ai_risk_observer.registry.validators import validate_registry_bundle

        bundle = load_registry_bundle()
        validated = validate_registry_bundle(bundle)

        source_id = None
        for group in (
            validated.sources,
            validated.podcasts,
            validated.events,
            validated.benchmarks,
        ):
            for entry in group:
                ht = getattr(entry, "helper_type", None)
                if ht == "manual":
                    source_id = entry.id
                    break
            if source_id:
                break

        if source_id is None:
            pytest.skip("No source with helper_type=manual")

        result = risk_discovery_helper_preview(source_id=source_id, fetch=False)
        assert result["ok"] is True
        assert result["candidates"] == []


# ---------------------------------------------------------------------------
# Preview discovery helpers script
# ---------------------------------------------------------------------------

class TestPreviewScript:
    """Tests for the preview_discovery_helpers script logic."""

    def test_preview_source_not_found(self):
        from scripts.preview_discovery_helpers import preview_source

        result = preview_source("nonexistent_source_12345")
        assert result["ok"] is False

    def test_preview_source_no_fetch(self):
        from frontier_ai_risk_observer.registry.loader import load_registry_bundle
        from frontier_ai_risk_observer.registry.validators import validate_registry_bundle
        from scripts.preview_discovery_helpers import preview_source

        bundle = load_registry_bundle()
        validated = validate_registry_bundle(bundle)

        source_id = None
        for entry in validated.sources:
            ht = getattr(entry, "helper_type", None)
            if ht and ht not in ("none", "manual"):
                source_id = entry.id
                break

        if source_id is None:
            pytest.skip("No source with helper configured")

        result = preview_source(source_id, fetch=False)
        assert result["ok"] is True
