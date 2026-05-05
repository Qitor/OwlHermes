"""Configuration for model-tiered pipeline.

Reads environment variables. No secrets are stored or printed.
If small model is disabled or misconfigured, the system continues working.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class SmallModelConfig:
    """Configuration for the optional small/fast model tier."""

    enabled: bool = False
    provider: str = ""
    model_name: str = ""
    base_url: str = ""
    api_key_env: str = ""
    timeout_seconds: int = 60
    max_concurrency: int = 2
    dry_run: bool = True
    strong_model_name: str = ""

    @property
    def api_key(self) -> str | None:
        """Read API key from the named env var. Never logs or prints."""
        if not self.api_key_env:
            return None
        return os.environ.get(self.api_key_env)

    def safe_repr(self) -> dict[str, str | int | bool]:
        """Return a representation safe for logging (no API keys)."""
        return {
            "enabled": self.enabled,
            "provider": self.provider,
            "model_name": self.model_name,
            "base_url": self.base_url if self.base_url else "(default)",
            "api_key_env": self.api_key_env,
            "api_key_set": bool(self.api_key),
            "timeout_seconds": self.timeout_seconds,
            "max_concurrency": self.max_concurrency,
            "dry_run": self.dry_run,
            "strong_model_name": self.strong_model_name,
        }


def load_small_model_config() -> SmallModelConfig:
    """Load small model config from environment variables."""
    return SmallModelConfig(
        enabled=_bool_env("AIRO_ENABLE_SMALL_MODEL", False),
        provider=os.environ.get("AIRO_SMALL_MODEL_PROVIDER", ""),
        model_name=os.environ.get("AIRO_SMALL_MODEL_NAME", ""),
        base_url=os.environ.get("AIRO_SMALL_MODEL_BASE_URL", ""),
        api_key_env=os.environ.get("AIRO_SMALL_MODEL_API_KEY_ENV", ""),
        timeout_seconds=int(os.environ.get("AIRO_SMALL_MODEL_TIMEOUT_SECONDS", "60")),
        max_concurrency=int(os.environ.get("AIRO_SMALL_MODEL_MAX_CONCURRENCY", "2")),
        dry_run=_bool_env("AIRO_SMALL_MODEL_DRY_RUN", True),
        strong_model_name=os.environ.get("AIRO_STRONG_MODEL_NAME", ""),
    )


def _bool_env(key: str, default: bool) -> bool:
    val = os.environ.get(key, "").lower()
    if val in ("true", "1", "yes"):
        return True
    if val in ("false", "0", "no"):
        return False
    return default
