from pathlib import Path

from frontier_ai_risk_observer.core.config import load_settings


def test_load_settings_from_environment(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("DATABASE_URL", "postgresql://example")
    monkeypatch.setenv("HERMES_CONFIG_PATH", "~/hermes.yaml")
    monkeypatch.setenv("SOURCE_REGISTRY_DIR", "custom_registry")
    monkeypatch.setenv("LOG_LEVEL", "debug")

    settings = load_settings()

    assert settings.database_url == "postgresql://example"
    assert settings.hermes_config_path == Path("~/hermes.yaml").expanduser()
    assert settings.source_registry_dir == Path("custom_registry")
    assert settings.log_level == "DEBUG"


def test_default_database_url_targets_local_postgres(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("DATABASE_URL", raising=False)

    settings = load_settings()

    assert settings.database_url.startswith("postgresql+psycopg://")
    assert "localhost" in settings.database_url
