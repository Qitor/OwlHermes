"""Candidate pre-processing service.

Optionally uses a small model for advisory summaries and lightweight
classification. Falls back to deterministic truncation if disabled.

This service must NOT:
- store signals
- decide final risk
- generate final daily report
- replace Hermes judgment
"""

from __future__ import annotations

from dataclasses import dataclass, field

from frontier_ai_risk_observer.models.config import SmallModelConfig, load_small_model_config
from frontier_ai_risk_observer.models.small_model import SmallModelClient, SmallModelResult


@dataclass(frozen=True)
class CandidatePreprocessResult:
    """Result of candidate pre-processing."""

    short_summary: str
    evidence_excerpt: str
    possible_risk_domains: list[str] = field(default_factory=list)
    advisory_relevance: str = "unknown"
    advisory_confidence: int = 0
    notes: str = ""
    model_used: str | None = None
    advisory_only: bool = True


def preprocess_candidate(
    title: str,
    url: str = "",
    content_text: str = "",
    source_id: str = "",
    focus: str = "",
    risk_domain: str = "",
    config: SmallModelConfig | None = None,
) -> CandidatePreprocessResult:
    """Pre-process a candidate item.

    If small model is enabled, uses it for advisory summary/classification.
    Otherwise falls back to deterministic truncation.

    Returns CandidatePreprocessResult with advisory_only=True always.
    """
    if config is None:
        config = load_small_model_config()

    client = SmallModelClient(config=config)

    # Summary
    summary_result = client.summarize_text(
        content_text or title,
        purpose=f"Source: {source_id}, Focus: {focus or risk_domain}",
        max_chars=500,
    )

    # Evidence excerpt
    excerpt_result = client.extract_evidence_excerpt(
        content_text or title,
        query_or_focus=focus or risk_domain or title,
        max_chars=300,
    )

    # Lightweight classification
    classify_result = client.classify_candidate_lightweight(
        title=title,
        summary=content_text[:500] if content_text else "",
    )

    # Parse classification
    domains, relevance, confidence, notes = _parse_classify(classify_result)

    return CandidatePreprocessResult(
        short_summary=summary_result.text,
        evidence_excerpt=excerpt_result.text,
        possible_risk_domains=domains,
        advisory_relevance=relevance,
        advisory_confidence=confidence,
        notes=notes,
        model_used=summary_result.model_used or None,
        advisory_only=True,
    )


def _parse_classify(
    result: SmallModelResult,
) -> tuple[list[str], str, int, str]:
    """Parse classification result from small model or fallback."""
    import json

    try:
        data = json.loads(result.text)
        domains = data.get("possible_domains", [])
        if isinstance(domains, list):
            domains = [str(d) for d in domains]
        else:
            domains = []

        relevant = data.get("risk_relevant")
        if relevant is True:
            relevance = "possibly_relevant"
        elif relevant is False:
            relevance = "likely_not_relevant"
        else:
            relevance = "unknown"

        confidence = data.get("advisory_confidence", 0)
        if not isinstance(confidence, int):
            confidence = 0

        reason = data.get("reason", "")
        notes = reason if reason else "Advisory classification"
        if result.model_used:
            notes += f" (model: {result.model_used})"

        return domains, relevance, confidence, notes
    except (json.JSONDecodeError, AttributeError, TypeError):
        return [], "unknown", 0, "Classification unavailable — advisory only"
