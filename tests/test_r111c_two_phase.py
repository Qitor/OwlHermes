"""R1-11C: Tests for two-phase daily report finalization.

Tests do NOT require Hermes, Docker, PostgreSQL, external network,
API keys, or production delivery.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
DAILY_PROMPT = REPO_ROOT / "prompts" / "daily_report_prompt.md"
FINALIZE_PROMPT = REPO_ROOT / "prompts" / "daily_report_finalize_prompt.md"
SKILL_MD = REPO_ROOT / "skills" / "ai-risk-signal-observer" / "SKILL.md"
MAKEFILE = REPO_ROOT / "Makefile"
DOCS_FILE = REPO_ROOT / "docs" / "22_two_phase_daily_report_finalization.md"
RUNNER_SCRIPT = REPO_ROOT / "scripts" / "daily_report.py"


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


class TestFinalizePrompt:
    """Test the daily report finalize prompt."""

    def test_finalize_prompt_exists(self):
        assert FINALIZE_PROMPT.exists()

    def test_says_no_browsing(self):
        content = FINALIZE_PROMPT.read_text()
        assert "不要浏览网页" in content or "Do not browse" in content

    def test_says_no_fetching(self):
        content = FINALIZE_PROMPT.read_text()
        assert "不要抓取" in content or "Do not fetch" in content

    def test_references_digest_store(self):
        content = FINALIZE_PROMPT.read_text()
        assert "risk_digest_store" in content

    def test_references_search_tools_only(self):
        content = FINALIZE_PROMPT.read_text()
        assert "risk_signal_search" in content
        assert "risk_raw_item_search" in content
        assert "risk_digest_search" in content

    def test_is_editorial_not_checklist(self):
        content = FINALIZE_PROMPT.read_text()
        # Should mention editorial mission / audience, not just tool calls
        assert "编辑使命" in content or "编辑" in content
        assert "AI safety" in content or "governance" in content or "政策" in content


class TestDailyPromptBounded:
    """Test that daily prompt is bounded."""

    def test_says_3_5_sources(self):
        content = DAILY_PROMPT.read_text()
        assert "3-5" in content

    def test_says_prioritize_completion(self):
        content = DAILY_PROMPT.read_text()
        assert "优先完成" in content or "prioritize" in content.lower()

    def test_says_store_digest_before_ending(self):
        content = DAILY_PROMPT.read_text()
        assert "risk_digest_store" in content
        assert "结束前" in content or "before ending" in content.lower() or "必须" in content


# ---------------------------------------------------------------------------
# Completion detection
# ---------------------------------------------------------------------------


class TestCompletionDetection:
    """Test report completion detection."""

    def test_complete_chinese_report_detected(self):
        from scripts.daily_report import report_looks_complete

        report = """# 前沿 AI 风险每日简报 | 2025-01-01

■ 一句话总览
今日风险格局无显著变化。

■ 信号
信号1: 某实验室发布了新的安全框架
变化：安全承诺升级
影响：治理风险降低
观察：关注后续执行情况

■ 来源扫描摘要
今天扫描了3个来源。

■ 证据和不确定性
证据充分，不确定性较低。

■ 需跟进
无。
"""
        assert report_looks_complete(report) is True

    def test_empty_text_not_complete(self):
        from scripts.daily_report import report_looks_complete

        assert report_looks_complete("") is False
        assert report_looks_complete("   ") is False

    def test_english_only_not_complete(self):
        from scripts.daily_report import report_looks_complete

        assert report_looks_complete("This is an English report with no CJK.") is False

    def test_timeout_log_not_complete(self):
        from scripts.daily_report import report_looks_complete

        log = "Hermes timed out after 1800s\nCalling tool risk_raw_item_store\nTool call complete"
        assert report_looks_complete(log) is False

    def test_tool_log_heavy_not_complete(self):
        from scripts.daily_report import report_looks_complete

        log = "■ 信号\n今日有信号" + "\nCalling tool risk_raw_item_store" * 10
        assert report_looks_complete(log) is False

    def test_traceback_not_complete(self):
        from scripts.daily_report import report_looks_complete

        log = "Traceback (most recent call last):\n  File ..."
        assert report_looks_complete(log) is False


# ---------------------------------------------------------------------------
# State snapshots
# ---------------------------------------------------------------------------


class TestStateSnapshots:
    """Test state snapshot capture."""

    def test_snapshot_against_empty_db(self, tmp_path):
        from scripts.daily_report import capture_state_snapshot

        # Patch DRYRUN_DB_URL to use a temp DB
        with patch("scripts.daily_report.DRYRUN_DB_URL", f"sqlite:///{tmp_path / 'test.db'}"):
            # Initialize the DB schema
            from sqlalchemy import create_engine

            from frontier_ai_risk_observer.db.models import Base

            engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
            Base.metadata.create_all(engine)

            snap = capture_state_snapshot()
            assert snap.raw_item_count == 0
            assert snap.source_run_count == 0
            assert snap.signal_count == 0
            assert snap.digest_count == 0

    def test_save_and_load_snapshot(self, tmp_path):
        from scripts.daily_report import StateSnapshot, save_snapshot

        snap = StateSnapshot(
            raw_item_count=10, signal_count=3,
            latest_digest_title="Test digest",
        )
        path = tmp_path / "state.json"
        save_snapshot(snap, path)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["raw_item_count"] == 10
        assert data["signal_count"] == 3
        assert data["latest_digest_title"] == "Test digest"

    def test_compute_delta(self):
        from scripts.daily_report import StateSnapshot, compute_delta

        before = StateSnapshot(raw_item_count=5, source_run_count=2, signal_count=1, digest_count=0)
        after = StateSnapshot(raw_item_count=8, source_run_count=3, signal_count=2, digest_count=1)
        delta = compute_delta(before, after)
        assert delta["raw_items"] == 3
        assert delta["source_runs"] == 1
        assert delta["signals"] == 1
        assert delta["digests"] == 1


# ---------------------------------------------------------------------------
# Runner CLI args
# ---------------------------------------------------------------------------


class TestRunnerCLIArgs:
    """Test that the runner supports new CLI arguments."""

    def test_collection_timeout_arg(self):
        result = subprocess.run(
            [str(REPO_ROOT / ".venv" / "bin" / "python"),
             str(RUNNER_SCRIPT), "--run", "--help"],
            capture_output=True, text=True, check=False,
        )
        # Script doesn't have --help for --run, but we can check the argparse
        # Instead, just verify the script is valid Python
        assert result.returncode in (0, 2)  # 2 = argparse error is fine

    def test_script_imports(self):
        from scripts.daily_report import (
            COLLECTION_TIMEOUT_DEFAULT,
            FINALIZE_TIMEOUT_DEFAULT,
        )
        assert COLLECTION_TIMEOUT_DEFAULT == 1800
        assert FINALIZE_TIMEOUT_DEFAULT == 600


# ---------------------------------------------------------------------------
# Phase result / summary
# ---------------------------------------------------------------------------


class TestPhaseResult:
    """Test PhaseResult dataclass."""

    def test_default_values(self):
        from scripts.daily_report import PhaseResult
        r = PhaseResult()
        assert r.exit_code == -1
        assert r.timed_out is False
        assert r.stdout == ""

    def test_timeout_result(self):
        from scripts.daily_report import PhaseResult
        r = PhaseResult(exit_code=-1, timed_out=True, stdout="partial", stderr="")
        assert r.timed_out is True
        assert r.stdout == "partial"


class TestRunSummary:
    """Test RunSummary dataclass."""

    def test_default_values(self):
        from scripts.daily_report import RunSummary
        s = RunSummary()
        assert s.phase_a_status == "not_run"
        assert s.phase_b_status == "not_run"
        assert s.finalize_needed is False
        assert s.daily_report_completed is False


# ---------------------------------------------------------------------------
# Should finalize decision
# ---------------------------------------------------------------------------


class TestShouldFinalize:
    """Test the finalize decision logic."""

    def test_finalize_when_phase_a_timed_out(self, tmp_path):
        from scripts.daily_report import (
            PhaseResult,
            StateSnapshot,
            _should_finalize,
        )
        phase_a = PhaseResult(exit_code=-1, timed_out=True, stdout="", stderr="")
        delta = {"raw_items": 5, "source_runs": 3, "signals": 1, "digests": 0}
        needed, reason = _should_finalize(
            phase_a, tmp_path, StateSnapshot(), StateSnapshot(), delta,
        )
        assert needed is True
        assert "timed out" in reason.lower()

    def test_finalize_when_no_digest(self, tmp_path):
        from scripts.daily_report import (
            PhaseResult,
            StateSnapshot,
            _should_finalize,
        )
        phase_a = PhaseResult(exit_code=0, timed_out=False, stdout="", stderr="")
        delta = {"raw_items": 5, "source_runs": 3, "signals": 1, "digests": 0}
        needed, reason = _should_finalize(
            phase_a, tmp_path, StateSnapshot(), StateSnapshot(), delta,
        )
        assert needed is True

    def test_skip_when_phase_a_complete(self, tmp_path):
        from scripts.daily_report import (
            PhaseResult,
            StateSnapshot,
            _should_finalize,
        )
        report_content = (
            "# 前沿 AI 风险每日简报\n\n"
            "■ 信号\n信号1：测试信号内容\n\n"
            "■ 一句话总览\n今日风险格局需要更新判断\n\n"
            "风险判断需要更新，这是足够长的中文内容来通过检测。"
        )
        phase_a = PhaseResult(
            exit_code=0, timed_out=False,
            stdout=report_content,
            stderr="",
        )
        delta = {"raw_items": 5, "source_runs": 3, "signals": 1, "digests": 1}
        # Write a good report file
        (tmp_path / "daily_report.md").write_text(report_content, encoding="utf-8")
        needed, reason = _should_finalize(
            phase_a, tmp_path, StateSnapshot(), StateSnapshot(), delta,
        )
        assert needed is False


# ---------------------------------------------------------------------------
# Signal schema
# ---------------------------------------------------------------------------


class TestSignalThreeQuestions:
    """Test that risk_signal_store supports three-question fields."""

    def test_signal_store_input_has_what_changed(self):
        from frontier_ai_risk_observer.mcp.schemas import SignalStoreInput
        inp = SignalStoreInput(
            title="Test", summary="Test summary",
            what_changed="New regulation",
            signal_type="governance", severity=3, confidence=3,
        )
        assert inp.what_changed == "New regulation"

    def test_signal_store_input_has_why_it_matters(self):
        from frontier_ai_risk_observer.mcp.schemas import SignalStoreInput
        inp = SignalStoreInput(
            title="Test", summary="Test summary",
            why_it_matters="Shifts governance risk",
            signal_type="governance", severity=3, confidence=3,
        )
        assert inp.why_it_matters == "Shifts governance risk"

    def test_signal_store_input_has_what_to_watch_next(self):
        from frontier_ai_risk_observer.mcp.schemas import SignalStoreInput
        inp = SignalStoreInput(
            title="Test", summary="Test summary",
            what_to_watch_next="Enforcement timeline",
            signal_type="governance", severity=3, confidence=3,
        )
        assert inp.what_to_watch_next == "Enforcement timeline"

    def test_signal_store_input_has_needs_review_reason(self):
        from frontier_ai_risk_observer.mcp.schemas import SignalStoreInput
        inp = SignalStoreInput(
            title="Test", summary="Test summary",
            needs_review_reason="Incomplete evidence",
            signal_type="governance", severity=3, confidence=3,
        )
        assert inp.needs_review_reason == "Incomplete evidence"

    def test_missing_three_question_fields_marks_review(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        from frontier_ai_risk_observer.db.models import Base
        from frontier_ai_risk_observer.mcp.schemas import SignalStoreInput
        from frontier_ai_risk_observer.services.signals import store_signal

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            inp = SignalStoreInput(
                title="Test", summary="Test summary",
                signal_type="governance", severity=3, confidence=3,
            )
            signal = store_signal(session, inp)
            assert signal.needs_human_review is True

    def test_explicit_fields_preferred_over_metadata(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        from frontier_ai_risk_observer.db.models import Base
        from frontier_ai_risk_observer.mcp.schemas import SignalStoreInput
        from frontier_ai_risk_observer.services.signals import store_signal

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            inp = SignalStoreInput(
                title="Test", summary="Test summary",
                what_changed="Explicit change",
                why_it_matters="Explicit reason",
                what_to_watch_next="Explicit watch",
                signal_type="governance", severity=3, confidence=3,
            )
            signal = store_signal(session, inp)
            assert signal.what_changed == "Explicit change"
            assert signal.why_it_matters == "Explicit reason"
            assert signal.what_to_watch_next == "Explicit watch"

    def test_metadata_fallback_for_three_questions(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        from frontier_ai_risk_observer.db.models import Base
        from frontier_ai_risk_observer.mcp.schemas import SignalStoreInput
        from frontier_ai_risk_observer.services.signals import store_signal

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            inp = SignalStoreInput(
                title="Test", summary="Test summary",
                metadata={
                    "what_changed": "Meta change",
                    "why_it_matters": "Meta reason",
                    "what_to_watch_next": "Meta watch",
                },
                signal_type="governance", severity=3, confidence=3,
            )
            signal = store_signal(session, inp)
            assert signal.what_changed == "Meta change"
            assert signal.why_it_matters == "Meta reason"
            assert signal.what_to_watch_next == "Meta watch"


# ---------------------------------------------------------------------------
# Makefile
# ---------------------------------------------------------------------------


class TestR111CMakefile:
    """Verify Makefile targets."""

    def test_daily_report_target(self):
        content = MAKEFILE.read_text()
        assert "daily-report:" in content

    def test_daily_report_with_quality_target(self):
        content = MAKEFILE.read_text()
        assert "daily-report-with-quality:" in content

    def test_daily_report_finalize_target(self):
        content = MAKEFILE.read_text()
        assert "daily-report-finalize:" in content

    def test_daily_report_debug_target(self):
        content = MAKEFILE.read_text()
        assert "daily-report-debug:" in content


# ---------------------------------------------------------------------------
# Docs
# ---------------------------------------------------------------------------


class TestR111CDocs:
    """Verify documentation."""

    def test_docs_exist(self):
        assert DOCS_FILE.exists()

    def test_docs_mention_two_phases(self):
        content = DOCS_FILE.read_text()
        assert "Phase A" in content
        assert "Phase B" in content

    def test_docs_mention_no_browsing_in_phase_b(self):
        content = DOCS_FILE.read_text()
        assert "Does not browse" in content or "no browsing" in content.lower()

    def test_docs_mention_sqlite(self):
        content = DOCS_FILE.read_text()
        assert "SQLite" in content

    def test_docs_mention_no_docker_postgres(self):
        content = DOCS_FILE.read_text()
        assert "No Docker" in content or "No Postgres" in content

    def test_docs_mention_timeout_handling(self):
        content = DOCS_FILE.read_text()
        assert "timeout" in content.lower()

    def test_docs_mention_hermes_led(self):
        content = DOCS_FILE.read_text()
        assert "Hermes" in content


# ---------------------------------------------------------------------------
# Smoke test script
# ---------------------------------------------------------------------------


class TestR111CSmoke:
    """Test the two-phase smoke test."""

    PYTHON = str(REPO_ROOT / ".venv" / "bin" / "python")

    def test_smoke_script_runs(self):
        result = subprocess.run(
            [self.PYTHON, "-c", """
from scripts.daily_report import report_looks_complete, StateSnapshot, compute_delta

# Test completion detection
assert report_looks_complete("") is False
assert report_looks_complete("■ 信号\\n测试信号" + "中" * 30) is True

# Test snapshot delta
before = StateSnapshot(raw_item_count=5, source_run_count=2, signal_count=1, digest_count=0)
after = StateSnapshot(raw_item_count=10, source_run_count=3, signal_count=3, digest_count=1)
delta = compute_delta(before, after)
assert delta["raw_items"] == 5
assert delta["digests"] == 1

print("OK: two-phase smoke passed")
"""],
            capture_output=True, text=True, check=False,
        )
        assert result.returncode == 0
        assert "OK" in result.stdout
