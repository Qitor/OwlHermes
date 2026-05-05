"""Logging setup helpers."""

from __future__ import annotations

import logging

from frontier_ai_risk_observer.core.config import get_settings


def configure_logging() -> None:
    """Configure process logging from settings."""
    logging.basicConfig(level=get_settings().log_level)
