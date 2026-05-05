"""Typed local configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Application settings with safe local-development defaults."""

    database_url: str = "postgresql+psycopg://risk:risk@localhost:5432/risk_signal"
    hermes_config_path: Path = Path("configs/hermes_config.example.yaml")
    source_registry_dir: Path = Path("source_registry")
    log_level: str = "INFO"


def _expand_path(value: str) -> Path:
    return Path(value).expanduser()


def load_settings() -> Settings:
    """Load settings from the current process environment."""
    return Settings(
        database_url=os.environ.get("DATABASE_URL", Settings.database_url),
        hermes_config_path=_expand_path(
            os.environ.get("HERMES_CONFIG_PATH", str(Settings.hermes_config_path))
        ),
        source_registry_dir=_expand_path(
            os.environ.get("SOURCE_REGISTRY_DIR", str(Settings.source_registry_dir))
        ),
        log_level=os.environ.get("LOG_LEVEL", Settings.log_level).upper(),
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings for application code."""
    return load_settings()
