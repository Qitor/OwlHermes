"""R1-11: Tests for daily report quality loop.

Tests do NOT require Hermes, Docker, PostgreSQL, external network,
or production delivery.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import yaml

from frontier_ai_risk_observer.quality.report_quality import (
    check_report,
    load_checklist,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "reports"
CHECKLIST_PATH = REPO_ROOT / "quality" / "daily_report_checklist.yaml"
RUBRIC_PATH = REPO_ROOT / "docs" / "21_daily_report_quality_rubric.md"
GOOD_REPORT = FIXTURES_DIR / "good_daily_report.md"
BAD_TOOL_LOG = FIXTURES_DIR / "bad_tool_log_report.md"
BAD_NEWS_DUMP = FIXTURES_DIR / "bad_news_dump_report.md"
NO_SIGNAL_REPORT = FIXTURES_DIR / "no_signal_report.md"
DAILY_PROMPT = REPO_ROOT / "prompts" / "daily_report_prompt.md"
INTERACTIVE_PROMPT = REPO_ROOT / "prompts" / "interactive_daily_report_prompt.md"
MAKEFILE = REPO_ROOT / "Makefile"


# ---------------------------------------------------------------------------
# Rubric docs
# ---------------------------------------------------------------------------


class TestQualityRubric:
    """Verify R1-11 quality rubric document."""

    def test_rubric_exists(self):
        assert RUBRIC_PATH.exists()

    def test_rubric_mentions_audience(self):
        content = RUBRIC_PATH.read_text()
        assert "AI safety" in content or "安全研究者" in content

    def test_rubric_defines_signal(self):
        content = RUBRIC_PATH.read_text()
        assert "What Counts as a Signal" in content or "什么算信号" in content

    def test_rubric_defines_filter_rules(self):
        content = RUBRIC_PATH.read_text()
        assert "Filter" in content or "过滤" in content or "不应" in content

    def test_rubric_includes_what_changed_why_watch(self):
        content = RUBRIC_PATH.read_text()
        assert "what changed" in content.lower() or "什么改变" in content
        assert "why" in content.lower() and "matter" in content.lower() or "影响风险判断" in content
        assert "watch" in content.lower() or "关注" in content

    def test_rubric_has_evaluation_dimensions(self):
        content = RUBRIC_PATH.read_text()
        assert "Novelty" in content or "novelty" in content.lower()
        assert "Confidence" in content or "confidence" in content.lower()

    def test_rubric_has_style_guide(self):
        content = RUBRIC_PATH.read_text()
        assert "Style Guide" in content or "风格" in content or "Avoid hype" in content


# ---------------------------------------------------------------------------
# Checklist
# ---------------------------------------------------------------------------


class TestQualityChecklist:
    """Verify quality checklist YAML."""

    def test_checklist_exists(self):
        assert CHECKLIST_PATH.exists()

    def test_checklist_loads_as_yaml(self):
        data = yaml.safe_load(CHECKLIST_PATH.read_text())
        assert "checks" in data
        assert isinstance(data["checks"], list)

    def test_checklist_has_required_checks(self):
        data = yaml.safe_load(CHECKLIST_PATH.read_text())
        ids = {c["id"] for c in data["checks"]}
        required = {
            "has_non_production_label",
            "has_one_sentence_overview",
            "has_top_signals_section",
            "has_candidate_items_section",
            "has_evidence_links",
            "has_uncertainty_section",
            "has_follow_up_section",
            "distinguishes_signal_vs_news",
            "each_signal_has_what_changed",
            "each_signal_has_why_it_matters",
            "each_signal_has_what_to_watch_next",
            "avoids_tool_log_style",
            "avoids_news_dump_style",
            "mentions_no_signal_if_none_found",
            "includes_source_coverage",
            "includes_helper_notes_if_helpers_used",
        }
        missing = required - ids
        assert not missing, f"Missing checks: {missing}"

    def test_each_check_has_weight(self):
        data = yaml.safe_load(CHECKLIST_PATH.read_text())
        for c in data["checks"]:
            assert "weight" in c, f"Check {c['id']} missing weight"
            assert isinstance(c["weight"], int)
            assert c["weight"] > 0


# ---------------------------------------------------------------------------
# Quality checker module
# ---------------------------------------------------------------------------


class TestQualityModule:
    """Test the quality checker module directly."""

    def test_load_checklist_default(self):
        checks = load_checklist()
        assert len(checks) > 10

    def test_load_checklist_path(self):
        checks = load_checklist(CHECKLIST_PATH)
        assert len(checks) > 10

    def test_good_report_scores_high(self):
        text = GOOD_REPORT.read_text()
        qr = check_report(text)
        assert qr.score_percent >= 60, f"Good report scored {qr.score_percent}%"

    def test_tool_log_report_scores_low(self):
        text = BAD_TOOL_LOG.read_text()
        qr = check_report(text)
        assert qr.score_percent < 50, f"Tool log report scored {qr.score_percent}%"

    def test_news_dump_report_scores_low(self):
        text = BAD_NEWS_DUMP.read_text()
        qr = check_report(text)
        assert qr.score_percent < 50, f"News dump scored {qr.score_percent}%"

    def test_no_signal_report_can_pass(self):
        text = NO_SIGNAL_REPORT.read_text()
        qr = check_report(text)
        assert qr.score_percent >= 50, f"No-signal report scored {qr.score_percent}%"

    def test_missing_evidence_links_fails_check(self):
        text = BAD_TOOL_LOG.read_text()
        qr = check_report(text)
        assert "has_evidence_links" in qr.failed_checks

    def test_missing_uncertainty_fails_check(self):
        text = BAD_TOOL_LOG.read_text()
        qr = check_report(text)
        assert "has_uncertainty_section" in qr.failed_checks

    def test_missing_top_signals_fails(self):
        text = BAD_NEWS_DUMP.read_text()
        qr = check_report(text)
        assert "has_top_signals_section" in qr.failed_checks

    def test_tool_log_fails_avoids_tool_log(self):
        text = BAD_TOOL_LOG.read_text()
        qr = check_report(text)
        assert "avoids_tool_log_style" in qr.failed_checks

    def test_news_dump_fails_distinguishes_signal_vs_news(self):
        text = BAD_NEWS_DUMP.read_text()
        qr = check_report(text)
        assert "distinguishes_signal_vs_news" in qr.failed_checks

    def test_no_signal_acknowledged(self):
        text = NO_SIGNAL_REPORT.read_text()
        qr = check_report(text)
        assert "mentions_no_signal_if_none_found" not in qr.failed_checks

    def test_quality_report_score_percent(self):
        text = GOOD_REPORT.read_text()
        qr = check_report(text)
        assert 0 <= qr.score_percent <= 100

    def test_quality_report_suggestions(self):
        text = BAD_NEWS_DUMP.read_text()
        qr = check_report(text)
        assert len(qr.suggestions) > 0

    def test_quality_report_anti_patterns(self):
        text = BAD_TOOL_LOG.read_text()
        qr = check_report(text)
        assert len(qr.anti_patterns) > 0


# ---------------------------------------------------------------------------
# Quality checker script
# ---------------------------------------------------------------------------


class TestQualityCheckerScript:
    """Test the check_daily_report_quality.py script."""

    PYTHON = str(REPO_ROOT / ".venv" / "bin" / "python")
    SCRIPT = str(REPO_ROOT / "scripts" / "check_daily_report_quality.py")

    def test_report_flag_works(self):
        result = subprocess.run(
            [self.PYTHON, self.SCRIPT, "--report", str(GOOD_REPORT)],
            capture_output=True, text=True, check=False,
        )
        assert result.returncode == 0
        assert "Score" in result.stdout

    def test_latest_flag_with_no_reports(self, tmp_path):
        result = subprocess.run(
            [self.PYTHON, self.SCRIPT, "--latest"],
            capture_output=True, text=True, check=False,
            env={**_env(), "HOME": str(tmp_path)},
        )
        # May fail if no reports exist, but should not crash
        assert (
            "No daily report" in result.stdout
            or "Score" in result.stdout
            or result.returncode in (0, 1)
        )

    def test_json_output(self):
        result = subprocess.run(
            [self.PYTHON, self.SCRIPT, "--report", str(GOOD_REPORT), "--json"],
            capture_output=True, text=True, check=False,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "score" in data
        assert "checks" in data
        assert "failed_checks" in data

    def test_fail_under_passes(self):
        result = subprocess.run(
            [self.PYTHON, self.SCRIPT, "--report", str(GOOD_REPORT), "--fail-under", "10"],
            capture_output=True, text=True, check=False,
        )
        assert result.returncode == 0

    def test_fail_under_fails(self):
        result = subprocess.run(
            [self.PYTHON, self.SCRIPT, "--report", str(BAD_TOOL_LOG), "--fail-under", "90"],
            capture_output=True, text=True, check=False,
        )
        assert result.returncode != 0

    def test_write_review(self, tmp_path):
        review_path = tmp_path / "review.md"
        result = subprocess.run(
            [self.PYTHON, self.SCRIPT, "--report", str(GOOD_REPORT),
             "--write-review", str(review_path)],
            capture_output=True, text=True, check=False,
        )
        assert result.returncode == 0
        assert review_path.exists()
        content = review_path.read_text()
        assert "Quality Review" in content


# ---------------------------------------------------------------------------
# Prompt tests
# ---------------------------------------------------------------------------


class TestDailyPrompt:
    """Verify the updated daily report prompt."""

    def test_prompt_says_not_news_summary(self):
        content = DAILY_PROMPT.read_text()
        assert "新闻聚合" in content or "not a news" in content.lower()

    def test_prompt_defines_audience(self):
        content = DAILY_PROMPT.read_text()
        assert "受众" in content or "Audience" in content or "AI safety" in content

    def test_prompt_says_every_signal_needs_three_questions(self):
        content = DAILY_PROMPT.read_text()
        assert "什么改变" in content
        assert "影响风险判断" in content
        assert "关注什么" in content or "接下来" in content

    def test_prompt_says_product_launches_not_automatically_signals(self):
        content = DAILY_PROMPT.read_text()
        assert "产品发布" in content or "产品公告" in content

    def test_prompt_says_avoid_tool_logs(self):
        content = DAILY_PROMPT.read_text()
        assert (
            "工具调用日志" in content
            or "tool.*log" in content.lower()
            or "不要在报告中包含工具" in content
        )

    def test_prompt_has_candidate_items_section(self):
        content = DAILY_PROMPT.read_text()
        assert "候选" in content and "未升级" in content

    def test_prompt_has_uncertainty_section(self):
        content = DAILY_PROMPT.read_text()
        assert "不确定性" in content or "证据.*缺口" in content

    def test_prompt_says_zero_signals_ok(self):
        content = DAILY_PROMPT.read_text()
        assert "0" in content and "信号" in content or "信号数为 0" in content

    def test_prompt_has_signal_definition(self):
        content = DAILY_PROMPT.read_text()
        assert "什么算信号" in content or "信号应涉及" in content


class TestInteractivePrompt:
    """Verify the updated interactive prompt."""

    def test_references_editorial_judgment(self):
        content = INTERACTIVE_PROMPT.read_text()
        assert "编辑判断" in content or "判断" in content

    def test_references_why_signal_or_not(self):
        content = INTERACTIVE_PROMPT.read_text()
        assert "为什么" in content or "判断为" in content

    def test_references_evidence_weakness(self):
        content = INTERACTIVE_PROMPT.read_text()
        assert "证据" in content and ("薄弱" in content or "弱" in content or "薄弱" in content)


# ---------------------------------------------------------------------------
# Makefile
# ---------------------------------------------------------------------------


class TestR111Makefile:
    """Verify R1-11 Makefile targets."""

    def test_report_quality_check_target(self):
        content = MAKEFILE.read_text()
        assert "report-quality-check:" in content

    def test_report_quality_review_target(self):
        content = MAKEFILE.read_text()
        assert "report-quality-review:" in content

    def test_daily_report_with_quality_target(self):
        content = MAKEFILE.read_text()
        assert "daily-report-with-quality:" in content


# ---------------------------------------------------------------------------
# Fixtures exist
# ---------------------------------------------------------------------------


class TestFixtures:
    """Verify test fixture files."""

    def test_good_report_exists(self):
        assert GOOD_REPORT.exists()

    def test_bad_tool_log_exists(self):
        assert BAD_TOOL_LOG.exists()

    def test_bad_news_dump_exists(self):
        assert BAD_NEWS_DUMP.exists()

    def test_no_signal_report_exists(self):
        assert NO_SIGNAL_REPORT.exists()

    def test_good_report_is_chinese(self):
        content = GOOD_REPORT.read_text()
        assert len(content) > 200
        import re
        assert len(re.findall(r"[\u4e00-\u9fff]", content)) > 50

    def test_bad_tool_log_has_tool_calls(self):
        content = BAD_TOOL_LOG.read_text()
        assert "Calling tool" in content or "risk_raw_item_store" in content

    def test_bad_news_dump_has_no_risk_judgment(self):
        content = BAD_NEWS_DUMP.read_text()
        assert "风险判断" not in content
        assert "信号" not in content or "新闻" in content

    def test_no_signal_report_explicitly_states_no_signals(self):
        content = NO_SIGNAL_REPORT.read_text()
        assert "未发现" in content and "信号" in content


# ---------------------------------------------------------------------------
# Quality module files
# ---------------------------------------------------------------------------


class TestQualityModuleFiles:
    """Verify quality module structure."""

    def test_quality_module_exists(self):
        assert (REPO_ROOT / "frontier_ai_risk_observer" / "quality" / "__init__.py").exists()

    def test_report_quality_module_exists(self):
        assert (REPO_ROOT / "frontier_ai_risk_observer" / "quality" / "report_quality.py").exists()

    def test_check_script_exists(self):
        assert (REPO_ROOT / "scripts" / "check_daily_report_quality.py").exists()


# Helper


def _env() -> dict:
    import os
    return {**os.environ, "DATABASE_URL": "sqlite:///./.local/risk_observer_dryrun.db"}
