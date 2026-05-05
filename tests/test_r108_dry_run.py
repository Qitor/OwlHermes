"""Tests for R1-08 automated Hermes daily dry run infrastructure.

These tests do NOT require Hermes-Agent, Docker, PostgreSQL, or external
network access. They verify that the R1-08 infrastructure (prompt, scripts,
DB support, docs) is structured correctly.
"""

from __future__ import annotations

import importlib
import os
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPT_PATH = REPO_ROOT / "prompts" / "r108_hermes_daily_dry_run_prompt.md"
DOC_PATH = REPO_ROOT / "docs" / "17_r108_automated_hermes_daily_dry_run.md"
RUNNER_PATH = REPO_ROOT / "scripts" / "r108_run_hermes.py"
INSPECT_PATH = REPO_ROOT / "scripts" / "r108_inspect_state.py"
DRYRUN_MODULE = "frontier_ai_risk_observer.db.dryrun"


def _import_runner():
    spec = importlib.util.spec_from_file_location("r108_run_hermes", RUNNER_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# 1. Prompt file exists and contains dry-run mode
# ---------------------------------------------------------------------------

def test_prompt_file_exists() -> None:
    assert PROMPT_PATH.exists(), f"Prompt file not found: {PROMPT_PATH}"


def test_prompt_contains_dry_run_mode() -> None:
    content = PROMPT_PATH.read_text()
    assert "dry-run" in content.lower() or "dry_run" in content.lower()


def test_prompt_says_not_to_post_externally() -> None:
    content = PROMPT_PATH.read_text()
    assert "Feishu" in content or "WeCom" in content or "external" in content.lower()


REQUIRED_MCP_TOOLS_IN_PROMPT = [
    "risk_registry_list_due_sources",
    "risk_raw_item_seen_check",
    "risk_raw_item_store",
    "risk_raw_item_duplicate_candidates",
    "risk_source_run_record",
    "risk_digest_store",
]


def test_prompt_references_required_mcp_tools() -> None:
    content = PROMPT_PATH.read_text()
    for tool in REQUIRED_MCP_TOOLS_IN_PROMPT:
        assert tool in content, f"Prompt missing reference to: {tool}"


# ---------------------------------------------------------------------------
# 2. Runner script supports --preflight and can load prompt
# ---------------------------------------------------------------------------

def test_runner_supports_preflight() -> None:
    mod = _import_runner()
    assert hasattr(mod, "preflight")


def test_runner_can_load_prompt() -> None:
    mod = _import_runner()
    prompt_text = mod.PROMPT_FILE.read_text(encoding="utf-8")
    assert len(prompt_text) > 100
    assert "dry-run" in prompt_text.lower() or "dry_run" in prompt_text.lower()


def test_runner_can_identify_run_directory() -> None:
    mod = _import_runner()
    assert mod.RUNS_DIR.name == "r1_08"


# ---------------------------------------------------------------------------
# 3. DB init/check code supports SQLite dry-run URL
# ---------------------------------------------------------------------------

def test_dryrun_db_init_with_sqlite(tmp_path: Path) -> None:
    """Test that the dry-run DB init works with a SQLite URL."""
    db_url = f"sqlite:///{tmp_path / 'test_dryrun.db'}"
    from frontier_ai_risk_observer.db.dryrun import init_dryrun_db
    result_url = init_dryrun_db(db_url)
    assert result_url == db_url
    assert (tmp_path / "test_dryrun.db").exists()


def test_dryrun_db_url_is_sqlite() -> None:
    from frontier_ai_risk_observer.db.dryrun import DRYRUN_DB_URL
    assert DRYRUN_DB_URL.startswith("sqlite:///")


# ---------------------------------------------------------------------------
# 4. State inspection script can run against empty SQLite DB
# ---------------------------------------------------------------------------

def test_inspect_state_against_empty_db(tmp_path: Path) -> None:
    """Run the inspection script against an empty SQLite DB."""
    db_path = tmp_path / "empty_inspect.db"
    db_url = f"sqlite:///{db_path}"

    # Initialize the DB first
    from frontier_ai_risk_observer.db.dryrun import init_dryrun_db
    init_dryrun_db(db_url)

    # Run inspection
    spec = importlib.util.spec_from_file_location("r108_inspect_state", INSPECT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # Monkeypatch DATABASE_URL and capture output
    with patch.dict(os.environ, {"DATABASE_URL": db_url}):
        # Should not raise
        mod.main()


# ---------------------------------------------------------------------------
# 5. Docs mention Docker is optional/not required
# ---------------------------------------------------------------------------

def test_docs_mention_docker_not_required() -> None:
    content = DOC_PATH.read_text()
    assert "Docker" in content
    assert "NOT Required" in content or "not required" in content.lower()


def test_docs_mention_non_production() -> None:
    content = DOC_PATH.read_text()
    assert "non-production" in content.lower() or "dry run" in content.lower()


def test_docs_mention_no_external_delivery() -> None:
    content = DOC_PATH.read_text()
    assert "Feishu" in content or "WeCom" in content or "delivery" in content.lower()


# ---------------------------------------------------------------------------
# 6. .gitignore covers .local/ and runs/r1_08/
# ---------------------------------------------------------------------------

def test_gitignore_covers_local_and_runs() -> None:
    gitignore = (REPO_ROOT / ".gitignore").read_text()
    assert ".local/" in gitignore
    assert "runs/r1_08/" in gitignore
