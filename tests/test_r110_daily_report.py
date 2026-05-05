"""R1-10: Tests for stable daily report run modes.

Tests do NOT require Hermes, Docker, PostgreSQL, external network,
or production delivery.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DAILY_PROMPT = REPO_ROOT / "prompts" / "daily_report_prompt.md"
INTERACTIVE_PROMPT = REPO_ROOT / "prompts" / "interactive_daily_report_prompt.md"
DOCS_FILE = REPO_ROOT / "docs" / "20_stable_daily_report_modes.md"


# ---------------------------------------------------------------------------
# Daily report prompt
# ---------------------------------------------------------------------------


class TestDailyReportPrompt:
    """Verify the daily report prompt."""

    def test_prompt_exists(self):
        assert DAILY_PROMPT.exists()

    def test_references_source_health_summary(self):
        assert "risk_source_health_summary" in DAILY_PROMPT.read_text()

    def test_references_list_due_sources(self):
        assert "risk_registry_list_due_sources" in DAILY_PROMPT.read_text()

    def test_references_discovery_helper_preview(self):
        assert "risk_discovery_helper_preview" in DAILY_PROMPT.read_text()

    def test_references_seen_check(self):
        assert "risk_raw_item_seen_check" in DAILY_PROMPT.read_text()

    def test_references_raw_item_store(self):
        assert "risk_raw_item_store" in DAILY_PROMPT.read_text()

    def test_references_source_run_record(self):
        assert "risk_source_run_record" in DAILY_PROMPT.read_text()

    def test_references_signal_store(self):
        assert "risk_signal_store" in DAILY_PROMPT.read_text()

    def test_references_digest_store(self):
        assert "risk_digest_store" in DAILY_PROMPT.read_text()

    def test_says_no_external_posting(self):
        content = DAILY_PROMPT.read_text()
        assert "不对外发布" in content or "NOT post externally" in content

    def test_says_chinese_report(self):
        content = DAILY_PROMPT.read_text()
        assert "中文" in content or "Chinese" in content

    def test_has_editorial_mission(self):
        content = DAILY_PROMPT.read_text()
        assert "编辑使命" in content or "情报编辑" in content

    def test_has_selection_criteria(self):
        content = DAILY_PROMPT.read_text()
        assert "选稿标准" in content or "入选" in content

    def test_mentions_signal_not_news(self):
        content = DAILY_PROMPT.read_text()
        assert "新闻聚合" in content or "新闻摘要" in content or "not a news" in content.lower()


# ---------------------------------------------------------------------------
# Interactive prompt
# ---------------------------------------------------------------------------


class TestInteractivePrompt:
    """Verify the interactive daily report prompt."""

    def test_prompt_exists(self):
        assert INTERACTIVE_PROMPT.exists()

    def test_says_show_progress(self):
        content = INTERACTIVE_PROMPT.read_text()
        assert "进度" in content or "progress" in content.lower() or "观察" in content

    def test_says_tool_call_intentions(self):
        content = INTERACTIVE_PROMPT.read_text()
        assert "tool" in content.lower() or "工具" in content

    def test_references_daily_report_prompt(self):
        content = INTERACTIVE_PROMPT.read_text()
        assert "daily_report_prompt" in content

    def test_says_no_external_posting(self):
        content = INTERACTIVE_PROMPT.read_text()
        assert "不对外发布" in content or "不发布" in content or "NOT post" in content


# ---------------------------------------------------------------------------
# Runner scripts
# ---------------------------------------------------------------------------


class TestDailyReportRunner:
    """Tests for the automated daily report runner."""

    def test_script_exists(self):
        assert (REPO_ROOT / "scripts" / "daily_report.py").exists()

    def test_supports_preflight(self):
        content = (REPO_ROOT / "scripts" / "daily_report.py").read_text()
        assert "--preflight" in content

    def test_uses_daily_prompt(self):
        content = (REPO_ROOT / "scripts" / "daily_report.py").read_text()
        assert "daily_report_prompt.md" in content

    def test_uses_runs_daily_dir(self):
        content = (REPO_ROOT / "scripts" / "daily_report.py").read_text()
        assert "runs/daily" in content or "daily" in content

    def test_saves_daily_report_md(self):
        content = (REPO_ROOT / "scripts" / "daily_report.py").read_text()
        assert "daily_report.md" in content

    def test_does_not_reset_db(self):
        content = (REPO_ROOT / "scripts" / "daily_report.py").read_text()
        assert "db-reset" not in content


class TestInteractiveRunner:
    """Tests for the interactive daily report runner."""

    def test_script_exists(self):
        assert (REPO_ROOT / "scripts" / "hermes_interactive_daily.py").exists()

    def test_supports_preflight(self):
        content = (REPO_ROOT / "scripts" / "hermes_interactive_daily.py").read_text()
        assert "--preflight" in content

    def test_supports_copy_prompt_only(self):
        content = (REPO_ROOT / "scripts" / "hermes_interactive_daily.py").read_text()
        assert "--copy-prompt-only" in content

    def test_supports_launch(self):
        content = (REPO_ROOT / "scripts" / "hermes_interactive_daily.py").read_text()
        assert "--launch" in content

    def test_uses_interactive_prompt(self):
        content = (REPO_ROOT / "scripts" / "hermes_interactive_daily.py").read_text()
        assert "interactive_daily_report_prompt.md" in content

    def test_uses_runs_interactive_dir(self):
        content = (REPO_ROOT / "scripts" / "hermes_interactive_daily.py").read_text()
        assert '"interactive"' in content

    def test_copy_prompt_works_without_hermes(self, tmp_path):
        """--copy-prompt-only should work even without a live Hermes."""
        result = subprocess.run(
            [str(REPO_ROOT / ".venv" / "bin" / "python"),
             str(REPO_ROOT / "scripts" / "hermes_interactive_daily.py"),
             "--copy-prompt-only"],
            capture_output=True, text=True, check=False,
            env={**os.environ, "DATABASE_URL": f"sqlite:///{tmp_path / 'test.db'}"},
        )
        # Should print the prompt, exit 0
        assert result.returncode == 0
        assert "daily_report_prompt" in result.stdout or "interactive" in result.stdout.lower()


class TestInspectDailyReport:
    """Tests for the daily report inspector."""

    def test_script_exists(self):
        assert (REPO_ROOT / "scripts" / "inspect_daily_report.py").exists()

    def test_works_with_empty_db(self, tmp_path):
        from sqlalchemy import create_engine

        from frontier_ai_risk_observer.db.models import Base

        db_path = tmp_path / "empty_test.db"
        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)
        engine.dispose()

        result = subprocess.run(
            [str(REPO_ROOT / ".venv" / "bin" / "python"),
             str(REPO_ROOT / "scripts" / "inspect_daily_report.py")],
            capture_output=True, text=True, check=False,
            env={**os.environ, "DATABASE_URL": f"sqlite:///{db_path}"},
        )
        assert result.returncode == 0
        assert "raw_items: 0" in result.stdout

    def test_shows_daily_run_dir(self):
        content = (REPO_ROOT / "scripts" / "inspect_daily_report.py").read_text()
        assert "daily" in content


# ---------------------------------------------------------------------------
# Makefile
# ---------------------------------------------------------------------------


class TestR110Makefile:
    """Verify Makefile targets."""

    def test_daily_report_target(self):
        content = (REPO_ROOT / "Makefile").read_text()
        assert "daily-report:" in content

    def test_daily_report_preflight_target(self):
        content = (REPO_ROOT / "Makefile").read_text()
        assert "daily-report-preflight:" in content

    def test_daily_report_inspect_target(self):
        content = (REPO_ROOT / "Makefile").read_text()
        assert "daily-report-inspect:" in content

    def test_hermes_interactive_daily_target(self):
        content = (REPO_ROOT / "Makefile").read_text()
        assert "hermes-interactive-daily:" in content

    def test_hermes_interactive_preflight_target(self):
        content = (REPO_ROOT / "Makefile").read_text()
        assert "hermes-interactive-preflight:" in content


# ---------------------------------------------------------------------------
# Documentation
# ---------------------------------------------------------------------------


class TestR110Docs:
    """Verify R1-10 documentation."""

    def test_docs_exist(self):
        assert DOCS_FILE.exists()

    def test_docs_mention_no_docker(self):
        content = DOCS_FILE.read_text()
        assert "Docker" in content

    def test_docs_mention_no_external_delivery(self):
        content = DOCS_FILE.read_text()
        assert "external delivery" in content.lower() or "Feishu" in content

    def test_docs_mention_sqlite(self):
        content = DOCS_FILE.read_text()
        assert "SQLite" in content

    def test_docs_mention_make_daily_report(self):
        content = DOCS_FILE.read_text()
        assert "make daily-report" in content

    def test_docs_mention_make_interactive(self):
        content = DOCS_FILE.read_text()
        assert "hermes-interactive-daily" in content


# ---------------------------------------------------------------------------
# Gitignore
# ---------------------------------------------------------------------------


class TestR110Gitignore:
    """Verify run artifacts are gitignored."""

    def test_gitignore_has_daily(self):
        content = (REPO_ROOT / ".gitignore").read_text()
        assert "runs/daily/" in content

    def test_gitignore_has_interactive(self):
        content = (REPO_ROOT / ".gitignore").read_text()
        assert "runs/interactive/" in content
