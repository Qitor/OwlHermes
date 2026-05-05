"""R1-09B: Tests for helper-assisted Hermes dry run infrastructure.

Tests do NOT require Hermes, Docker, real PostgreSQL, external network,
or production delivery.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPT_FILE = (
    REPO_ROOT / "prompts" / "r109_hermes_helper_assisted_dry_run_prompt.md"
)
DOCS_FILE = (
    REPO_ROOT / "docs" / "19_r109b_helper_assisted_hermes_dry_run.md"
)


# ---------------------------------------------------------------------------
# Prompt file tests
# ---------------------------------------------------------------------------


class TestR109BPrompt:
    """Verify the R1-09B prompt file exists and contains required content."""

    def test_prompt_file_exists(self):
        assert PROMPT_FILE.exists(), f"Prompt file not found: {PROMPT_FILE}"

    def test_prompt_references_source_health_summary(self):
        content = PROMPT_FILE.read_text()
        assert "risk_source_health_summary" in content

    def test_prompt_references_discovery_helper_preview(self):
        content = PROMPT_FILE.read_text()
        assert "risk_discovery_helper_preview" in content

    def test_prompt_references_list_due_sources(self):
        content = PROMPT_FILE.read_text()
        assert "risk_registry_list_due_sources" in content

    def test_prompt_references_seen_check(self):
        content = PROMPT_FILE.read_text()
        assert "risk_raw_item_seen_check" in content

    def test_prompt_references_raw_item_store(self):
        content = PROMPT_FILE.read_text()
        assert "risk_raw_item_store" in content

    def test_prompt_references_source_run_record(self):
        content = PROMPT_FILE.read_text()
        assert "risk_source_run_record" in content

    def test_prompt_references_digest_store(self):
        content = PROMPT_FILE.read_text()
        assert "risk_digest_store" in content

    def test_prompt_says_non_production(self):
        content = PROMPT_FILE.read_text()
        assert "NON-PRODUCTION" in content or "non-production" in content

    def test_prompt_says_no_post_externally(self):
        content = PROMPT_FILE.read_text()
        assert "NOT post externally" in content or "Do NOT post" in content

    def test_prompt_says_candidates_not_judgments(self):
        content = PROMPT_FILE.read_text()
        assert "NOT final risk judgments" in content

    def test_prompt_says_seen_check_before_store(self):
        content = PROMPT_FILE.read_text()
        # Must mention seen-check before storing
        assert "risk_raw_item_seen_check" in content
        assert "risk_raw_item_store" in content
        # seen-check should appear before store in the prompt
        seen_pos = content.index("risk_raw_item_seen_check")
        store_pos = content.rindex("risk_raw_item_store")
        assert seen_pos < store_pos, (
            "risk_raw_item_seen_check should appear before risk_raw_item_store"
        )

    def test_prompt_mentions_selected_sources(self):
        content = PROMPT_FILE.read_text()
        assert "anthropic_news" in content
        assert "apollo_blog" in content
        assert "arxiv_ai_safety" in content
        assert "techcrunch_ai" in content

    def test_prompt_mentions_fetch_true_allowlisted(self):
        content = PROMPT_FILE.read_text()
        assert "fetch=True" in content or "fetch=true" in content
        assert "allowlisted" in content.lower()

    def test_prompt_mentions_dry_run_status(self):
        content = PROMPT_FILE.read_text()
        assert "dry_run" in content

    def test_prompt_mentions_chinese_digest(self):
        content = PROMPT_FILE.read_text()
        assert "Chinese" in content or "中文" in content

    def test_prompt_mentions_helper_usage_section(self):
        content = PROMPT_FILE.read_text()
        assert "Helper 使用情况" in content or "helper" in content.lower()


# ---------------------------------------------------------------------------
# Runner script tests
# ---------------------------------------------------------------------------


class TestR109BRunner:
    """Tests for the R1-09B runner script (without Hermes)."""

    def test_runner_script_exists(self):
        runner = REPO_ROOT / "scripts" / "r109b_run_hermes.py"
        assert runner.exists()

    def test_runner_supports_preflight(self):
        runner = REPO_ROOT / "scripts" / "r109b_run_hermes.py"
        content = runner.read_text()
        assert "--preflight" in content

    def test_runner_can_locate_prompt(self):
        # Import the module and check prompt file path
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        try:
            import importlib

            spec = importlib.util.spec_from_file_location(
                "r109b_run_hermes",
                REPO_ROOT / "scripts" / "r109b_run_hermes.py",
            )
            mod = importlib.util.module_from_spec(spec)  # noqa: F841
            # Don't execute main, just check constants
            source = (REPO_ROOT / "scripts" / "r109b_run_hermes.py").read_text()
            assert "r109_hermes_helper_assisted_dry_run_prompt.md" in source
        finally:
            sys.path.pop(0)

    def test_runner_uses_r109b_run_dir(self):
        source = (REPO_ROOT / "scripts" / "r109b_run_hermes.py").read_text()
        assert "r1_09b" in source

    def test_runner_does_not_reset_db_by_default(self):
        source = (REPO_ROOT / "scripts" / "r109b_run_hermes.py").read_text()
        # Should NOT have db-reset-dryrun in the run flow
        assert "db-reset" not in source
        # Should keep existing data for seen-check/dedup testing
        assert "R1-08 data" in source or "keeping" in source.lower()

    def test_runner_timeout_configured(self):
        source = (REPO_ROOT / "scripts" / "r109b_run_hermes.py").read_text()
        assert "TIMEOUT" in source

    def test_runner_saves_artifacts(self):
        source = (REPO_ROOT / "scripts" / "r109b_run_hermes.py").read_text()
        assert "hermes_stdout.log" in source
        assert "hermes_stderr.log" in source
        assert "hermes_output.md" in source
        assert "summary.md" in source
        assert "prompt.md" in source

    def test_runner_uses_hermes_yolo_mode(self):
        source = (REPO_ROOT / "scripts" / "r109b_run_hermes.py").read_text()
        assert "--yolo" in source
        assert "hermes" in source


# ---------------------------------------------------------------------------
# Inspector script tests
# ---------------------------------------------------------------------------


class TestR109BInspector:
    """Tests for the R1-09B inspector script."""

    def test_inspector_script_exists(self):
        inspector = REPO_ROOT / "scripts" / "r109b_inspect_state.py"
        assert inspector.exists()

    def test_inspector_uses_sqlite(self):
        source = (
            REPO_ROOT / "scripts" / "r109b_inspect_state.py"
        ).read_text()
        assert "sqlite" in source.lower()

    def test_inspector_shows_table_counts(self):
        source = (
            REPO_ROOT / "scripts" / "r109b_inspect_state.py"
        ).read_text()
        assert "raw_items" in source
        assert "source_runs" in source
        assert "signals" in source
        assert "digests" in source

    def test_inspector_shows_helper_assisted_runs(self):
        source = (
            REPO_ROOT / "scripts" / "r109b_inspect_state.py"
        ).read_text()
        assert "helper_used" in source or "helper-assisted" in source

    def test_inspector_shows_seen_count(self):
        source = (
            REPO_ROOT / "scripts" / "r109b_inspect_state.py"
        ).read_text()
        assert "seen_count" in source

    def test_inspector_redacts_credentials(self):
        source = (
            REPO_ROOT / "scripts" / "r109b_inspect_state.py"
        ).read_text()
        assert "_redact_url" in source

    def test_inspector_works_with_empty_db(self, tmp_path):
        """Inspector should not crash on an empty SQLite DB."""
        db_path = tmp_path / "empty_test.db"
        db_url = f"sqlite:///{db_path}"

        # Create empty DB with schema
        from sqlalchemy import create_engine

        from frontier_ai_risk_observer.db.models import Base

        engine = create_engine(db_url)
        Base.metadata.create_all(engine)
        engine.dispose()

        # Run inspector with this DB
        env = {**os.environ, "DATABASE_URL": db_url}
        import subprocess

        result = subprocess.run(
            [str(REPO_ROOT / ".venv" / "bin" / "python"),
             str(REPO_ROOT / "scripts" / "r109b_inspect_state.py")],
            capture_output=True, text=True, env=env, check=False,
        )
        assert result.returncode == 0
        assert "raw_items: 0" in result.stdout


# ---------------------------------------------------------------------------
# Documentation tests
# ---------------------------------------------------------------------------


class TestR109BDocs:
    """Verify R1-09B documentation."""

    def test_docs_file_exists(self):
        assert DOCS_FILE.exists(), f"Docs file not found: {DOCS_FILE}"

    def test_docs_mention_no_docker(self):
        content = DOCS_FILE.read_text()
        assert "Docker" in content

    def test_docs_mention_no_production_delivery(self):
        content = DOCS_FILE.read_text()
        assert "non-production" in content or "Non-Production" in content

    def test_docs_mention_makefile_commands(self):
        content = DOCS_FILE.read_text()
        assert "r109b-dry-run-preflight" in content
        assert "r109b-run-hermes" in content
        assert "r109b-inspect-state" in content

    def test_docs_mention_artifact_location(self):
        content = DOCS_FILE.read_text()
        assert "runs/r1_09b" in content

    def test_docs_mention_helper_fetch_empty(self):
        content = DOCS_FILE.read_text()
        assert "0 candidates" in content or "empty" in content.lower()


# ---------------------------------------------------------------------------
# Makefile tests
# ---------------------------------------------------------------------------


class TestR109BMakefile:
    """Verify Makefile targets exist."""

    def test_makefile_has_r109b_preflight(self):
        source = (REPO_ROOT / "Makefile").read_text()
        assert "r109b-dry-run-preflight" in source

    def test_makefile_has_r109b_run_hermes(self):
        source = (REPO_ROOT / "Makefile").read_text()
        assert "r109b-run-hermes" in source

    def test_makefile_has_r109b_inspect_state(self):
        source = (REPO_ROOT / "Makefile").read_text()
        assert "r109b-inspect-state" in source


# ---------------------------------------------------------------------------
# Gitignore tests
# ---------------------------------------------------------------------------


class TestR109BGitignore:
    """Verify run artifacts are gitignored."""

    def test_gitignore_has_r109b(self):
        source = (REPO_ROOT / ".gitignore").read_text()
        assert "runs/r1_09b/" in source
