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
    obsidian_vault_path: Path = Path(".local/obsidian_vault")
    obsidian_live_logging_enabled: bool = False
    obsidian_live_runs_dir: str = "08_Live_Runs"
    obsidian_live_append_to_daily: bool = True
    obsidian_live_open_after_start: bool = False
    obsidian_live_event_max_chars: int = 4000
    obsidian_live_flush_mode: str = "immediate"


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
        obsidian_vault_path=_expand_path(
            os.environ.get("OBSIDIAN_VAULT_PATH", str(Settings.obsidian_vault_path))
        ),
        obsidian_live_logging_enabled=os.environ.get(
            "OBSIDIAN_LIVE_LOGGING_ENABLED", "false"
        ).lower() in ("true", "1", "yes"),
        obsidian_live_runs_dir=os.environ.get(
            "OBSIDIAN_LIVE_RUNS_DIR", Settings.obsidian_live_runs_dir
        ),
        obsidian_live_append_to_daily=os.environ.get(
            "OBSIDIAN_LIVE_APPEND_TO_DAILY", "true"
        ).lower() in ("true", "1", "yes"),
        obsidian_live_open_after_start=os.environ.get(
            "OBSIDIAN_LIVE_OPEN_AFTER_START", "false"
        ).lower() in ("true", "1", "yes"),
        obsidian_live_event_max_chars=int(
            os.environ.get("OBSIDIAN_LIVE_EVENT_MAX_CHARS", "4000")
        ),
        obsidian_live_flush_mode=os.environ.get(
            "OBSIDIAN_LIVE_FLUSH_MODE", Settings.obsidian_live_flush_mode
        ),
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings for application code."""
    return load_settings()
