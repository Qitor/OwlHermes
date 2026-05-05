"""Lightweight small-model client for advisory pre-processing.

Uses httpx (already a dependency) for OpenAI-compatible chat completions.
No heavy SDK. Fully optional — if disabled, returns unavailable cleanly.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

import httpx

from frontier_ai_risk_observer.models.config import SmallModelConfig

logger = logging.getLogger(__name__)


class SmallModelUnavailable(Exception):
    """Raised when the small model is disabled or misconfigured."""


@dataclass(frozen=True)
class SmallModelResult:
    """Result from a small-model call."""

    text: str
    model_used: str
    advisory_only: bool = True
    purpose: str = ""
    truncated: bool = False


@dataclass
class SmallModelClient:
    """Client for optional small/fast model tier."""

    config: SmallModelConfig = field(default_factory=SmallModelConfig)

    @property
    def available(self) -> bool:
        """Whether the small model is enabled and configured."""
        if not self.config.enabled:
            return False
        if not self.config.model_name:
            return False
        if not self.config.api_key:
            return False
        return True

    def summarize_text(
        self, text: str, purpose: str = "", max_chars: int = 500,
    ) -> SmallModelResult:
        """Summarize text using small model. Advisory only."""
        if not self.available:
            return _fallback_summary(text, purpose, max_chars)
        prompt = (
            f"请用中文简洁总结以下内容，不超过{max_chars}字。"
            + (f" 目的：{purpose}。" if purpose else "")
            + "\n\n" + text[:8000]
        )
        return self._chat(prompt, purpose="summarize")

    def extract_evidence_excerpt(
        self, text: str, query_or_focus: str = "", max_chars: int = 300,
    ) -> SmallModelResult:
        """Extract evidence excerpt from text. Advisory only."""
        if not self.available:
            return _fallback_excerpt(text, query_or_focus, max_chars)
        prompt = (
            f"从以下内容中提取与「{query_or_focus}」相关的关键证据片段，"
            f"不超过{max_chars}字。如果没有相关证据，回复'无相关证据'。"
            "\n\n" + text[:8000]
        )
        return self._chat(prompt, purpose="extract_evidence")

    def classify_candidate_lightweight(
        self, title: str, summary: str = "",
    ) -> SmallModelResult:
        """Lightweight classification of a candidate item. Advisory only."""
        if not self.available:
            return _fallback_classify(title, summary)
        prompt = (
            "判断以下候选条目是否可能与前沿AI风险相关。"
            " 回复JSON格式：{\"risk_relevant\": true/false, "
            "\"possible_domains\": [\"...\"], \"advisory_confidence\": 1-5, "
            "\"reason\": \"...\"}\n\n"
            f"标题：{title}\n"
            + (f"摘要：{summary}" if summary else "")
        )
        return self._chat(prompt, purpose="classify")

    def _chat(self, prompt: str, purpose: str = "") -> SmallModelResult:
        """Make a chat completion call to the small model."""
        base_url = self.config.base_url or "https://api.openai.com/v1"
        url = f"{base_url.rstrip('/')}/chat/completions"
        api_key = self.config.api_key
        if not api_key:
            raise SmallModelUnavailable("No API key configured")

        payload = {
            "model": self.config.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是前沿AI风险情报的辅助分析工具。"
                        "输出简洁、有据。你的输出仅供参考，不构成最终判断。"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 1024,
            "temperature": 0.3,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        timeout = self.config.timeout_seconds
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return SmallModelResult(
                    text=content,
                    model_used=self.config.model_name,
                    advisory_only=True,
                    purpose=purpose,
                )
        except httpx.TimeoutException:
            logger.warning("Small model request timed out (%ss)", timeout)
            return SmallModelResult(
                text="(small model timed out)",
                model_used=self.config.model_name,
                advisory_only=True,
                purpose=purpose,
                truncated=True,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Small model request failed: %s", exc)
            return SmallModelResult(
                text=f"(small model error: {type(exc).__name__})",
                model_used=self.config.model_name,
                advisory_only=True,
                purpose=purpose,
                truncated=True,
            )


# ---------------------------------------------------------------------------
# Deterministic fallbacks (no model, no network)
# ---------------------------------------------------------------------------


def _fallback_summary(text: str, purpose: str, max_chars: int) -> SmallModelResult:
    """Deterministic truncation fallback."""
    if len(text) <= max_chars:
        return SmallModelResult(
            text=text, model_used="", advisory_only=True, purpose=purpose,
        )
    return SmallModelResult(
        text=text[:max_chars] + "...", model_used="", advisory_only=True,
        purpose=purpose, truncated=True,
    )


def _fallback_excerpt(text: str, query: str, max_chars: int) -> SmallModelResult:
    """Return first max_chars as excerpt fallback."""
    excerpt = text[:max_chars]
    if len(text) > max_chars:
        excerpt += "..."
    return SmallModelResult(
        text=excerpt, model_used="", advisory_only=True,
        purpose="extract_evidence", truncated=len(text) > max_chars,
    )


def _fallback_classify(title: str, summary: str) -> SmallModelResult:
    """Return unknown classification fallback."""
    result: dict[str, object] = {
        "risk_relevant": None,
        "possible_domains": [],
        "advisory_confidence": 0,
        "reason": "Small model not available — requires human judgment",
    }
    return SmallModelResult(
        text=json.dumps(result, ensure_ascii=False),
        model_used="",
        advisory_only=True,
        purpose="classify",
    )
