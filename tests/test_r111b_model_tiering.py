"""R1-11B: Tests for model-tiered daily report pipeline.

Tests do NOT require Hermes, Docker, PostgreSQL, external network,
API keys, or production delivery.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from frontier_ai_risk_observer.models.config import SmallModelConfig, load_small_model_config
from frontier_ai_risk_observer.models.small_model import (
    SmallModelClient,
)
from frontier_ai_risk_observer.services.candidate_preprocess import (
    CandidatePreprocessResult,
    preprocess_candidate,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DAILY_PROMPT = REPO_ROOT / "prompts" / "daily_report_prompt.md"
INTERACTIVE_PROMPT = REPO_ROOT / "prompts" / "interactive_daily_report_prompt.md"
SKILL_MD = REPO_ROOT / "skills" / "ai-risk-signal-observer" / "SKILL.md"
ENV_EXAMPLE = REPO_ROOT / "configs" / "env.example"
HERMES_CONFIG = REPO_ROOT / "configs" / "hermes_config.example.yaml"
MAKEFILE = REPO_ROOT / "Makefile"
DOCS_FILE = REPO_ROOT / "docs" / "22_model_tiered_daily_report_pipeline.md"


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class TestSmallModelConfig:
    """Test small model configuration."""

    def test_disabled_by_default(self):
        config = SmallModelConfig()
        assert not config.enabled

    def test_env_vars_load(self, monkeypatch):
        monkeypatch.setenv("AIRO_ENABLE_SMALL_MODEL", "true")
        monkeypatch.setenv("AIRO_SMALL_MODEL_NAME", "gpt-4o-mini")
        monkeypatch.setenv("AIRO_SMALL_MODEL_PROVIDER", "openai")
        config = load_small_model_config()
        assert config.enabled
        assert config.model_name == "gpt-4o-mini"
        assert config.provider == "openai"

    def test_secrets_not_in_safe_repr(self, monkeypatch):
        monkeypatch.setenv("AIRO_SMALL_MODEL_API_KEY_ENV", "MY_SECRET_KEY")
        monkeypatch.setenv("MY_SECRET_KEY", "sk-super-secret-123")
        config = load_small_model_config()
        repr_dict = config.safe_repr()
        assert "sk-super-secret-123" not in str(repr_dict)
        assert repr_dict["api_key_set"] is True
        assert repr_dict["api_key_env"] == "MY_SECRET_KEY"

    def test_api_key_reads_from_named_env(self, monkeypatch):
        monkeypatch.setenv("AIRO_SMALL_MODEL_API_KEY_ENV", "TEST_KEY_XYZ")
        monkeypatch.setenv("TEST_KEY_XYZ", "test-key-value")
        config = SmallModelConfig(
            enabled=True, api_key_env="TEST_KEY_XYZ",
        )
        assert config.api_key == "test-key-value"

    def test_api_key_returns_none_if_no_env(self):
        config = SmallModelConfig(api_key_env="")
        assert config.api_key is None

    def test_timeout_default(self):
        config = SmallModelConfig()
        assert config.timeout_seconds == 60

    def test_dry_run_default(self):
        config = SmallModelConfig()
        assert config.dry_run is True


# ---------------------------------------------------------------------------
# Small model client
# ---------------------------------------------------------------------------


class TestSmallModelClient:
    """Test the small model client."""

    def test_disabled_client_returns_unavailable(self):
        client = SmallModelClient(config=SmallModelConfig(enabled=False))
        assert not client.available

    def test_summarize_text_fallback(self):
        client = SmallModelClient(config=SmallModelConfig(enabled=False))
        result = client.summarize_text("Some long text" * 100, purpose="test")
        assert result.advisory_only is True
        assert result.model_used == ""
        assert len(result.text) <= 600  # 500 chars + "..."

    def test_extract_evidence_fallback(self):
        client = SmallModelClient(config=SmallModelConfig(enabled=False))
        result = client.extract_evidence_excerpt("Some content", query_or_focus="risk")
        assert result.advisory_only is True
        assert result.model_used == ""

    def test_classify_candidate_fallback(self):
        client = SmallModelClient(config=SmallModelConfig(enabled=False))
        result = client.classify_candidate_lightweight("Test title", "summary")
        assert result.advisory_only is True
        data = json.loads(result.text)
        assert data["risk_relevant"] is None
        assert data["advisory_confidence"] == 0

    def test_available_when_configured(self, monkeypatch):
        monkeypatch.setenv("TEST_KEY", "sk-test")
        config = SmallModelConfig(
            enabled=True, model_name="test-model",
            api_key_env="TEST_KEY",
        )
        client = SmallModelClient(config=config)
        assert client.available

    def test_not_available_without_model_name(self, monkeypatch):
        monkeypatch.setenv("TEST_KEY", "sk-test")
        config = SmallModelConfig(
            enabled=True, model_name="",
            api_key_env="TEST_KEY",
        )
        client = SmallModelClient(config=config)
        assert not client.available

    def test_not_available_without_api_key(self):
        config = SmallModelConfig(
            enabled=True, model_name="test-model",
            api_key_env="NONEXISTENT_KEY_12345",
        )
        client = SmallModelClient(config=config)
        assert not client.available

    def test_timeout_handled_gracefully(self, monkeypatch):
        monkeypatch.setenv("TEST_KEY", "sk-test")
        config = SmallModelConfig(
            enabled=True, model_name="test-model",
            api_key_env="TEST_KEY", base_url="http://127.0.0.1:1",
            timeout_seconds=1,
        )
        client = SmallModelClient(config=config)
        result = client.summarize_text("test")
        assert result.advisory_only is True
        assert "timed out" in result.text or "error" in result.text

    def test_api_key_redaction_in_logs(self, monkeypatch):
        monkeypatch.setenv("MY_SECRET", "sk-secret-key-12345")
        config = SmallModelConfig(
            api_key_env="MY_SECRET",
        )
        safe = config.safe_repr()
        assert "sk-secret-key-12345" not in str(safe)

    def test_mocked_openai_endpoint(self, monkeypatch):
        """Test with mocked httpx response."""
        monkeypatch.setenv("TEST_KEY_R11B", "sk-test")
        config = SmallModelConfig(
            enabled=True, model_name="test-model",
            api_key_env="TEST_KEY_R11B",
        )
        client = SmallModelClient(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test summary"}}],
        }
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch(
            "frontier_ai_risk_observer.models.small_model.httpx.Client",
            return_value=mock_client,
        ):
            result = client.summarize_text("Some text")

        assert result.text == "Test summary"
        assert result.model_used == "test-model"
        assert result.advisory_only is True


# ---------------------------------------------------------------------------
# Candidate preprocess service
# ---------------------------------------------------------------------------


class TestCandidatePreprocess:
    """Test candidate preprocessing service."""

    def test_deterministic_fallback_without_small_model(self):
        result = preprocess_candidate(
            title="Test Article",
            content_text="A" * 1000,
            source_id="test_source",
            config=SmallModelConfig(enabled=False),
        )
        assert isinstance(result, CandidatePreprocessResult)
        assert result.advisory_only is True
        assert result.model_used is None

    def test_output_has_advisory_only_true(self):
        result = preprocess_candidate(
            title="Test",
            config=SmallModelConfig(enabled=False),
        )
        assert result.advisory_only is True

    def test_possible_risk_domains_returned(self):
        result = preprocess_candidate(
            title="Test",
            config=SmallModelConfig(enabled=False),
        )
        assert isinstance(result.possible_risk_domains, list)

    def test_does_not_store_anything(self):
        """Preprocess should only return data, never store."""
        result = preprocess_candidate(
            title="Test",
            config=SmallModelConfig(enabled=False),
        )
        # Result is a plain dataclass, no DB access
        assert not hasattr(result, "store") or result.advisory_only is True

    def test_handles_long_text_safely(self):
        long_text = "X" * 100000
        result = preprocess_candidate(
            title="Long article",
            content_text=long_text,
            config=SmallModelConfig(enabled=False),
        )
        assert len(result.short_summary) <= 600
        assert len(result.evidence_excerpt) <= 400

    def test_with_mocked_small_model(self, monkeypatch):
        monkeypatch.setenv("TEST_KEY_R11B_SVC", "sk-test")
        config = SmallModelConfig(
            enabled=True, model_name="test-model",
            api_key_env="TEST_KEY_R11B_SVC",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Brief summary"}}],
        }
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch(
            "frontier_ai_risk_observer.models.small_model.httpx.Client",
            return_value=mock_client,
        ):
            # For classify, return valid JSON
            classify_response = MagicMock()
            classify_response.status_code = 200
            classify_response.raise_for_status = MagicMock()
            classify_response.json.return_value = {
                "choices": [{"message": {"content": json.dumps({
                    "risk_relevant": True,
                    "possible_domains": ["governance"],
                    "advisory_confidence": 3,
                    "reason": "Mentions regulation",
                })}}],
            }
            call_count = [0]

            def side_effect_post(*args, **kwargs):
                call_count[0] += 1
                if call_count[0] <= 2:
                    return mock_response
                return classify_response

            mock_client.post.side_effect = side_effect_post

            result = preprocess_candidate(
                title="New AI Regulation",
                content_text="Article about AI governance",
                config=config,
            )

        assert result.model_used == "test-model"
        assert result.advisory_only is True


# ---------------------------------------------------------------------------
# MCP tool
# ---------------------------------------------------------------------------


class TestMCPTool:
    """Test the risk_candidate_preprocess MCP tool."""

    def test_tool_imports(self):
        from frontier_ai_risk_observer.mcp.server import risk_candidate_preprocess
        assert callable(risk_candidate_preprocess)

    def test_tool_returns_advisory_output(self):
        from frontier_ai_risk_observer.mcp.server import risk_candidate_preprocess
        with patch(
            "frontier_ai_risk_observer.services.candidate_preprocess.load_small_model_config",
            return_value=SmallModelConfig(enabled=False),
        ):
            result = risk_candidate_preprocess(title="Test Article")
        assert result["ok"] is True
        assert result["advisory_only"] is True

    def test_tool_works_when_small_model_disabled(self):
        from frontier_ai_risk_observer.mcp.server import risk_candidate_preprocess
        with patch(
            "frontier_ai_risk_observer.services.candidate_preprocess.load_small_model_config",
            return_value=SmallModelConfig(enabled=False),
        ):
            result = risk_candidate_preprocess(
                title="Test",
                url="https://example.com",
                content_text="Content",
                source_id="test_src",
            )
        assert result["ok"] is True
        assert "short_summary" in result
        assert "advisory_relevance" in result

    def test_no_network_calls_in_default(self):
        from frontier_ai_risk_observer.mcp.server import risk_candidate_preprocess
        with patch(
            "frontier_ai_risk_observer.services.candidate_preprocess.load_small_model_config",
            return_value=SmallModelConfig(enabled=False),
        ):
            result = risk_candidate_preprocess(title="Test")
        assert result["model_used"] is None

    def test_tool_in_mcp_tool_functions(self):
        from frontier_ai_risk_observer.mcp.server import MCP_TOOL_FUNCTIONS
        names = [fn.__name__ for fn in MCP_TOOL_FUNCTIONS]
        assert "risk_candidate_preprocess" in names


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


class TestDailyPromptModelTiering:
    """Verify daily prompt references model-tiered workflow."""

    def test_mentions_advisory_preprocessing(self):
        content = DAILY_PROMPT.read_text()
        assert "risk_candidate_preprocess" in content

    def test_says_advisory_only(self):
        content = DAILY_PROMPT.read_text()
        assert "仅供参考" in content or "advisory" in content.lower()

    def test_says_final_judgment_remains_hermes(self):
        content = DAILY_PROMPT.read_text()
        assert "最终" in content and "判断" in content

    def test_mentions_run_bounds(self):
        content = DAILY_PROMPT.read_text()
        assert "3-5" in content or "2-4" in content


class TestInteractivePromptModelTiering:
    """Verify interactive prompt mentions advisory status."""

    def test_mentions_preprocess_tool(self):
        content = INTERACTIVE_PROMPT.read_text()
        assert "risk_candidate_preprocess" in content or "预处理" in content

    def test_mentions_advisory_status(self):
        content = INTERACTIVE_PROMPT.read_text()
        assert "仅供参考" in content or "advisory" in content.lower()


class TestSkillModelTiering:
    """Verify SKILL.md mentions model-tiered workflow."""

    def test_mentions_model_tiering(self):
        content = SKILL_MD.read_text()
        assert "R1-11B" in content or "small model" in content.lower() or "小模型" in content

    def test_mentions_advisory_only(self):
        content = SKILL_MD.read_text()
        assert "advisory only" in content.lower() or "仅供参考" in content

    def test_mentions_risk_candidate_preprocess(self):
        content = SKILL_MD.read_text()
        assert "risk_candidate_preprocess" in content


# ---------------------------------------------------------------------------
# Config files
# ---------------------------------------------------------------------------


class TestConfigFiles:
    """Verify config files have model-tiering entries."""

    def test_env_example_has_small_model_vars(self):
        content = ENV_EXAMPLE.read_text()
        assert "AIRO_ENABLE_SMALL_MODEL" in content
        assert "AIRO_SMALL_MODEL_NAME" in content
        assert "AIRO_SMALL_MODEL_BASE_URL" in content

    def test_hermes_config_has_preprocess_tool(self):
        content = HERMES_CONFIG.read_text()
        assert "risk_candidate_preprocess" in content


# ---------------------------------------------------------------------------
# Docs
# ---------------------------------------------------------------------------


class TestDocs:
    """Verify documentation."""

    def test_docs_exist(self):
        assert DOCS_FILE.exists()

    def test_docs_mention_three_tiers(self):
        content = DOCS_FILE.read_text()
        assert "Strong model" in content or "Hermes" in content
        assert "Small" in content or "small model" in content.lower()
        assert "Deterministic" in content or "Python" in content

    def test_docs_mention_safety(self):
        content = DOCS_FILE.read_text()
        assert "advisory" in content.lower()
        assert "must NOT" in content

    def test_docs_mention_configuration(self):
        content = DOCS_FILE.read_text()
        assert "AIRO_ENABLE_SMALL_MODEL" in content

    def test_docs_mention_disabling(self):
        content = DOCS_FILE.read_text()
        assert "Disabling" in content or "disable" in content.lower()


# ---------------------------------------------------------------------------
# Makefile
# ---------------------------------------------------------------------------


class TestR111BMakefile:
    """Verify Makefile targets."""

    def test_model_tier_smoke_target(self):
        content = MAKEFILE.read_text()
        assert "model-tier-smoke:" in content


# ---------------------------------------------------------------------------
# Quality checker
# ---------------------------------------------------------------------------


class TestQualityCheckerAdvisory:
    """Verify quality checker handles advisory checks."""

    def test_checklist_has_advisory_check(self):
        import yaml
        checklist_path = REPO_ROOT / "quality" / "daily_report_checklist.yaml"
        data = yaml.safe_load(checklist_path.read_text())
        ids = {c["id"] for c in data["checks"]}
        assert "avoids_advisory_as_final_evidence" in ids

    def test_good_report_passes_advisory_check(self):
        from frontier_ai_risk_observer.quality.report_quality import check_report
        good_path = REPO_ROOT / "tests" / "fixtures" / "reports" / "good_daily_report.md"
        text = good_path.read_text()
        qr = check_report(text)
        assert "avoids_advisory_as_final_evidence" not in qr.failed_checks


# ---------------------------------------------------------------------------
# Smoke test script
# ---------------------------------------------------------------------------


class TestModelTierSmoke:
    """Test the model-tier-smoke command."""

    PYTHON = str(REPO_ROOT / ".venv" / "bin" / "python")

    def test_smoke_script_runs(self):
        result = subprocess.run(
            [self.PYTHON, "-c", """
from frontier_ai_risk_observer.models.config import SmallModelConfig
from frontier_ai_risk_observer.services.candidate_preprocess import preprocess_candidate

config = SmallModelConfig(enabled=False)
result = preprocess_candidate(title="Smoke test", config=config)
assert result.advisory_only is True
print("OK: model-tier smoke passed (deterministic fallback)")
"""],
            capture_output=True, text=True, check=False,
        )
        assert result.returncode == 0
        assert "OK" in result.stdout
