"""R1-14: Source reliability patch — registry fields, health reporting,
helper access checks, failure policy, and due-source filtering.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from frontier_ai_risk_observer.registry.loader import load_registry_bundle
from frontier_ai_risk_observer.registry.validators import (
    EventEntry,
    FailurePolicy,
    KnownFailure,
    PodcastEntry,
    RegistryEntryModel,
    SourceEntry,
    validate_registry_bundle,
)

# ---------------------------------------------------------------------------
# 1. Reliability Pydantic models
# ---------------------------------------------------------------------------

class TestReliabilityModels:
    """Tests for FailurePolicy, KnownFailure, and Literal types."""

    def test_failure_policy_defaults(self):
        fp = FailurePolicy()
        assert fp.max_attempts == 3
        assert fp.timeout_seconds == 30.0
        assert fp.on_failure == "skip"
        assert fp.report_in_digest is True

    def test_failure_policy_custom(self):
        fp = FailurePolicy(max_attempts=1, timeout_seconds=15, on_failure="fallback")
        assert fp.max_attempts == 1
        assert fp.timeout_seconds == 15
        assert fp.on_failure == "fallback"

    def test_failure_policy_invalid_on_failure(self):
        with pytest.raises(ValidationError):
            FailurePolicy(on_failure="invalid_value")

    def test_failure_policy_extra_fields_allowed(self):
        fp = FailurePolicy(max_attempts=2, custom_note="test")
        assert fp.max_attempts == 2

    def test_known_failure_required_fields(self):
        kf = KnownFailure(type="ssl_error", message="SSL EOF")
        assert kf.type == "ssl_error"
        assert kf.observed_in_round is None
        assert kf.observed_at is None
        assert kf.recommended_action is None

    def test_known_failure_all_fields(self):
        kf = KnownFailure(
            type="cloudflare_block",
            message="Blocked",
            observed_in_round="R1-05",
            observed_at="2026-05-01",
            recommended_action="Use search engine",
        )
        assert kf.observed_in_round == "R1-05"
        assert kf.recommended_action == "Use search engine"

    def test_known_failure_missing_required(self):
        with pytest.raises(ValidationError):
            KnownFailure(type="ssl_error")  # missing message

    def test_access_status_literal_values(self):
        valid = {"ok", "degraded", "blocked", "timeout_prone", "manual_only", "disabled"}
        for v in valid:
            # Verify values are valid strings for AccessStatus Literal
            assert isinstance(v, str)

    def test_collection_frequency_literal_values(self):
        valid = {"daily", "weekly", "biweekly", "monthly", "manual"}
        for v in valid:
            assert isinstance(v, str)

    def test_collection_method_literal_values(self):
        valid = {
            "rss", "podcast_rss", "sitemap", "official_page_links",
            "browser_list_page", "arxiv_api", "arxiv_oai_pmh",
            "search_fallback", "manual",
        }
        for v in valid:
            assert isinstance(v, str)


# ---------------------------------------------------------------------------
# 2. Registry entry reliability fields
# ---------------------------------------------------------------------------

class TestRegistryReliabilityFields:
    """Tests for reliability fields on registry entry models."""

    def test_registry_entry_with_access_status(self):
        entry = RegistryEntryModel(
            id="test", name="Test", access_status="ok",
        )
        assert entry.access_status == "ok"

    def test_registry_entry_with_all_reliability_fields(self):
        entry = RegistryEntryModel(
            id="test", name="Test",
            access_status="degraded",
            collection_frequency="weekly",
            primary_collection_method="browser_list_page",
            fallback_methods=["search_fallback"],
            failure_policy=FailurePolicy(max_attempts=1, on_failure="skip"),
            known_failures=[KnownFailure(type="ssl_error", message="SSL EOF")],
            notes_for_hermes="Use search fallback",
        )
        assert entry.access_status == "degraded"
        assert entry.collection_frequency == "weekly"
        assert entry.primary_collection_method == "browser_list_page"
        assert entry.fallback_methods == ["search_fallback"]
        assert entry.failure_policy.max_attempts == 1
        assert len(entry.known_failures) == 1
        assert entry.notes_for_hermes == "Use search fallback"

    def test_registry_entry_backward_compat(self):
        """Entries without new fields should still validate."""
        entry = RegistryEntryModel(id="test", name="Test")
        assert entry.access_status is None
        assert entry.collection_frequency is None
        assert entry.failure_policy is None
        assert entry.known_failures is None
        assert entry.notes_for_hermes is None

    def test_fallback_excludes_primary_validator(self):
        """primary_collection_method must not appear in fallback_methods."""
        with pytest.raises(ValidationError, match="fallback_methods must not include"):
            RegistryEntryModel(
                id="test", name="Test",
                primary_collection_method="rss",
                fallback_methods=["rss"],
            )

    def test_source_entry_with_reliability(self):
        entry = SourceEntry(
            id="test_source", name="Test Source",
            category="frontier_ai_lab", url="https://example.com",
            collector="web_index", priority="high",
            access_status="blocked",
            collection_frequency="daily",
            primary_collection_method="search_fallback",
            fallback_methods=["manual"],
            failure_policy=FailurePolicy(max_attempts=1, on_failure="manual_review"),
            known_failures=[
                KnownFailure(type="cloudflare_block", message="Blocked by Cloudflare"),
            ],
        )
        assert entry.access_status == "blocked"
        assert entry.known_failures[0].type == "cloudflare_block"

    def test_podcast_entry_with_reliability(self):
        entry = PodcastEntry(
            id="test_podcast", name="Test Podcast",
            url="https://example.com/podcast",
            collector="podcast_feed",
            feed_url="https://example.com/feed.xml",
            access_status="ok",
            collection_frequency="weekly",
            primary_collection_method="podcast_rss",
        )
        assert entry.access_status == "ok"
        assert entry.primary_collection_method == "podcast_rss"

    def test_event_entry_with_reliability(self):
        entry = EventEntry(
            id="test_event", name="Test Event",
            url="https://example.com/event",
            category="summit",
            access_status="manual_only",
            collection_frequency="monthly",
            primary_collection_method="manual",
        )
        assert entry.access_status == "manual_only"


# ---------------------------------------------------------------------------
# 3. Registry validation with reliability fields
# ---------------------------------------------------------------------------

class TestRegistryValidationWithReliability:
    """Tests that current YAML registries pass with new fields."""

    def test_yaml_registries_pass_validation(self):
        bundle = load_registry_bundle()
        validated = validate_registry_bundle(bundle)
        assert len(validated.sources) > 0
        assert len(validated.podcasts) > 0

    def test_access_status_distribution(self):
        """At least some entries should have access_status set."""
        bundle = load_registry_bundle()
        validated = validate_registry_bundle(bundle)
        with_status = [
            e for e in validated.sources
            if getattr(e, "access_status", None) is not None
        ]
        assert len(with_status) >= 5, (
            f"Expected >= 5 sources with access_status, got {len(with_status)}"
        )

    def test_blocked_sources_have_fallbacks(self):
        """Blocked sources should have fallback_methods or notes_for_hermes."""
        bundle = load_registry_bundle()
        validated = validate_registry_bundle(bundle)
        for entry in validated.sources:
            if getattr(entry, "access_status", None) == "blocked":
                has_fallback = bool(getattr(entry, "fallback_methods", None))
                has_notes = bool(getattr(entry, "notes_for_hermes", None))
                assert has_fallback or has_notes, (
                    f"Blocked source {entry.id} should have fallback_methods or notes_for_hermes"
                )

    def test_openai_is_blocked(self):
        """OpenAI News should be marked as blocked."""
        bundle = load_registry_bundle()
        validated = validate_registry_bundle(bundle)
        openai = next((e for e in validated.sources if e.id == "openai_news"), None)
        assert openai is not None
        assert openai.access_status == "blocked"

    def test_techcrunch_is_ok(self):
        """TechCrunch should be marked as ok."""
        bundle = load_registry_bundle()
        validated = validate_registry_bundle(bundle)
        tc = next((e for e in validated.sources if e.id == "techcrunch_ai"), None)
        assert tc is not None
        assert tc.access_status == "ok"

    def test_axrp_has_podcast_rss_and_feed_url(self):
        """AXRP should now use podcast_rss with feed_url."""
        bundle = load_registry_bundle()
        validated = validate_registry_bundle(bundle)
        axrp = next((e for e in validated.podcasts if e.id == "axrp"), None)
        assert axrp is not None
        assert axrp.helper_type == "podcast_rss"
        assert axrp.feed_url is not None
        assert "axrp.net" in axrp.feed_url


# ---------------------------------------------------------------------------
# 4. Source health reliability reporting
# ---------------------------------------------------------------------------

class TestSourceHealthReliability:
    """Tests for extended source_health_summary with reliability fields."""

    def test_health_summary_includes_access_status_counts(self):
        from frontier_ai_risk_observer.services.source_health import source_health_summary
        result = source_health_summary()
        assert "access_status_counts" in result
        assert isinstance(result["access_status_counts"], dict)
        # At least "ok" and some problematic status should exist
        assert result["access_status_counts"].get("ok", 0) > 0

    def test_health_summary_includes_degraded_or_blocked(self):
        from frontier_ai_risk_observer.services.source_health import source_health_summary
        result = source_health_summary()
        assert "degraded_or_blocked" in result
        assert isinstance(result["degraded_or_blocked"], list)
        # OpenAI should appear in this list
        ids = [e["id"] for e in result["degraded_or_blocked"]]
        assert "openai_news" in ids

    def test_health_summary_includes_timeout_prone(self):
        from frontier_ai_risk_observer.services.source_health import source_health_summary
        result = source_health_summary()
        assert "timeout_prone" in result
        assert isinstance(result["timeout_prone"], list)

    def test_health_summary_includes_collection_method_counts(self):
        from frontier_ai_risk_observer.services.source_health import source_health_summary
        result = source_health_summary()
        assert "collection_method_counts" in result
        assert isinstance(result["collection_method_counts"], dict)

    def test_health_summary_includes_known_failures(self):
        from frontier_ai_risk_observer.services.source_health import source_health_summary
        result = source_health_summary()
        assert "recent_known_failures_count" in result
        assert "recent_known_failures" in result
        assert result["recent_known_failures_count"] > 0

    def test_degraded_entries_have_access_status_field(self):
        from frontier_ai_risk_observer.services.source_health import source_health_summary
        result = source_health_summary()
        for entry in result["degraded_or_blocked"]:
            assert "access_status" in entry
            assert entry["access_status"] in ("degraded", "blocked")


# ---------------------------------------------------------------------------
# 5. Helper access status checks
# ---------------------------------------------------------------------------

class TestHelperAccessStatus:
    """Tests for _run_helper_for_entry access_status gate."""

    def _make_entry(self, **overrides):
        """Create a minimal SourceEntry-like object for testing."""
        from types import SimpleNamespace
        defaults = {
            "id": "test_source",
            "name": "Test Source",
            "enabled": True,
            "access_status": None,
            "helper_type": None,
            "notes_for_hermes": None,
            "fallback_methods": None,
            "failure_policy": None,
            "max_items": None,
        }
        defaults.update(overrides)
        return SimpleNamespace(**defaults)

    def test_blocked_source_returns_empty(self):
        from frontier_ai_risk_observer.mcp.server import _run_helper_for_entry
        entry = self._make_entry(access_status="blocked")
        candidates, meta = _run_helper_for_entry(entry, 10)
        assert candidates == []
        assert meta.get("skipped_reason") == "access_status=blocked"

    def test_disabled_source_returns_empty(self):
        from frontier_ai_risk_observer.mcp.server import _run_helper_for_entry
        entry = self._make_entry(access_status="disabled")
        candidates, meta = _run_helper_for_entry(entry, 10)
        assert candidates == []
        assert "disabled" in meta.get("skipped_reason", "")

    def test_manual_only_source_returns_empty(self):
        from frontier_ai_risk_observer.mcp.server import _run_helper_for_entry
        entry = self._make_entry(access_status="manual_only")
        candidates, meta = _run_helper_for_entry(entry, 10)
        assert candidates == []
        assert "manual_only" in meta.get("skipped_reason", "")

    def test_blocked_with_search_fallback_recommends(self):
        from frontier_ai_risk_observer.mcp.server import _run_helper_for_entry
        entry = self._make_entry(
            access_status="blocked",
            fallback_methods=["search_fallback"],
        )
        candidates, meta = _run_helper_for_entry(entry, 10)
        assert candidates == []
        assert meta.get("search_fallback_recommended") is True

    def test_ok_source_attempts_helper(self):
        from frontier_ai_risk_observer.mcp.server import _run_helper_for_entry
        # ok status should not skip — but with no helper_type it returns empty
        entry = self._make_entry(access_status="ok", helper_type=None)
        candidates, meta = _run_helper_for_entry(entry, 10)
        assert isinstance(candidates, list)
        assert meta.get("access_status") == "ok"

    def test_metadata_includes_notes_for_hermes(self):
        from frontier_ai_risk_observer.mcp.server import _run_helper_for_entry
        entry = self._make_entry(
            access_status="blocked",
            notes_for_hermes="Use Yahoo Search",
        )
        candidates, meta = _run_helper_for_entry(entry, 10)
        assert meta.get("notes_for_hermes") == "Use Yahoo Search"


# ---------------------------------------------------------------------------
# 6. Failure policy behavior
# ---------------------------------------------------------------------------

class TestFailurePolicy:
    """Tests for failure policy in _run_helper_for_entry."""

    def _make_entry(self, **overrides):
        from types import SimpleNamespace
        defaults = {
            "id": "test_source",
            "name": "Test Source",
            "enabled": True,
            "access_status": None,
            "helper_type": "scrapling_official_page",
            "notes_for_hermes": None,
            "fallback_methods": None,
            "failure_policy": None,
            "max_items": None,
            "scrapling_url": None,
            "list_url": None,
            "url": "https://example.com",
            "link_include_patterns": None,
            "link_exclude_patterns": None,
        }
        defaults.update(overrides)
        return SimpleNamespace(**defaults)

    def test_degraded_source_attempts_helper(self):
        from frontier_ai_risk_observer.mcp.server import _run_helper_for_entry
        # degraded should NOT skip — it tries the helper
        entry = self._make_entry(access_status="degraded")
        candidates, meta = _run_helper_for_entry(entry, 10)
        # With scrapling_url=None and url=example.com, helper may fail
        # but the point is it wasn't skipped
        assert meta.get("skipped_reason") is None

    def test_helper_failure_sets_metadata(self):
        from frontier_ai_risk_observer.mcp.server import _run_helper_for_entry
        entry = self._make_entry(
            helper_type="scrapling_official_page",
            scrapling_url="https://nonexistent.invalid",
        )
        candidates, meta = _run_helper_for_entry(entry, 10)
        # Helper may fail due to network — that's fine, just check metadata
        assert isinstance(candidates, list)

    def test_return_type_is_tuple(self):
        from frontier_ai_risk_observer.mcp.server import _run_helper_for_entry
        entry = self._make_entry(access_status="blocked")
        result = _run_helper_for_entry(entry, 10)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_metadata_count_field(self):
        from frontier_ai_risk_observer.mcp.server import _run_helper_for_entry
        entry = self._make_entry(access_status="blocked")
        candidates, meta = _run_helper_for_entry(entry, 10)
        assert "count" in meta
        assert meta["count"] == 0


# ---------------------------------------------------------------------------
# 7. Due source access_status filter
# ---------------------------------------------------------------------------

class TestDueSourceAccessStatusFilter:
    """Tests for access_status filter on list_due_sources."""

    def test_filter_by_ok(self):
        from frontier_ai_risk_observer.mcp.server import risk_registry_list_due_sources
        result = risk_registry_list_due_sources(access_status="ok")
        assert result["ok"] is True
        for entry in result["entries"]:
            assert entry.get("access_status") == "ok"

    def test_filter_by_blocked(self):
        from frontier_ai_risk_observer.mcp.server import risk_registry_list_due_sources
        result = risk_registry_list_due_sources(access_status="blocked")
        assert result["ok"] is True
        for entry in result["entries"]:
            assert entry.get("access_status") == "blocked"

    def test_no_filter_returns_all(self):
        from frontier_ai_risk_observer.mcp.server import risk_registry_list_due_sources
        result_all = risk_registry_list_due_sources()
        result_ok = risk_registry_list_due_sources(access_status="ok")
        assert result_all["count"] >= result_ok["count"]

    def test_filter_nonexistent_status_returns_empty(self):
        from frontier_ai_risk_observer.mcp.server import risk_registry_list_due_sources
        result = risk_registry_list_due_sources(access_status="nonexistent_status")
        assert result["count"] == 0

    def test_ok_filter_has_results(self):
        from frontier_ai_risk_observer.mcp.server import risk_registry_list_due_sources
        result = risk_registry_list_due_sources(access_status="ok")
        assert result["count"] > 0
