"""Deterministic daily report quality checker.

No LLMs. No network. No Postgres. No Hermes.
Reads a report Markdown file and a checklist YAML, runs deterministic
section-detection and anti-pattern checks, and produces a scored result.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml


@dataclass
class CheckResult:
    """Result of a single quality check."""

    check_id: str
    name: str
    passed: bool
    description: str = ""
    weight: int = 0
    notes: str = ""


@dataclass
class QualityReport:
    """Aggregated quality report for a daily report."""

    report_path: str
    checks: list[CheckResult] = field(default_factory=list)
    score: float = 0.0
    max_score: float = 0.0
    timestamp: str = ""
    failed_checks: list[str] = field(default_factory=list)
    anti_patterns: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    @property
    def score_percent(self) -> int:
        if self.max_score == 0:
            return 0
        return round(self.score / self.max_score * 100)


def load_checklist(path: Path | str | None = None) -> list[dict[str, Any]]:
    """Load checklist YAML. Returns list of check dicts."""
    if path is None:
        repo_root = Path(__file__).resolve().parent.parent.parent
        path = repo_root / "quality" / "daily_report_checklist.yaml"
    path = Path(path)
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("checks", [])  # type: ignore[no-any-return]


def check_report(text: str, checklist: list[dict[str, Any]] | None = None) -> QualityReport:
    """Run all quality checks on report text. Returns QualityReport."""
    if checklist is None:
        checklist = load_checklist()

    results: list[CheckResult] = []
    for check in checklist:
        cid = check["id"]
        name = check["name"]
        desc = check.get("description", "")
        weight = check.get("weight", 1)
        passed, notes = _run_check(cid, text)
        results.append(CheckResult(
            check_id=cid, name=name, passed=passed,
            description=desc, weight=weight, notes=notes,
        ))

    total_weight = sum(r.weight for r in results)
    earned_weight = sum(r.weight for r in results if r.passed)
    failed = [r.check_id for r in results if not r.passed]
    anti_patterns = _detect_anti_patterns(text)
    suggestions = _generate_suggestions(failed, anti_patterns)

    return QualityReport(
        report_path="",
        checks=results,
        score=earned_weight,
        max_score=total_weight,
        timestamp=datetime.now(UTC).isoformat(),
        failed_checks=failed,
        anti_patterns=anti_patterns,
        suggestions=suggestions,
    )


# ---------------------------------------------------------------------------
# Check registry — explicit registration avoids mypy untyped-decorator issues
# ---------------------------------------------------------------------------

_CHECK_FNS: dict[str, Callable[[str], tuple[bool, str]]] = {}


def _register(check_id: str, fn: Callable[[str], tuple[bool, str]]) -> None:
    _CHECK_FNS[check_id] = fn


def _run_check(check_id: str, text: str) -> tuple[bool, str]:
    fn = _CHECK_FNS.get(check_id)
    if fn is None:
        return False, f"No implementation for check: {check_id}"
    return fn(text)


# ---------------------------------------------------------------------------
# Individual check implementations
# ---------------------------------------------------------------------------

def _has_non_production_label(text: str) -> tuple[bool, str]:
    keywords = [
        "非生产", "non-production", "本地运行", "local_daily_report",
        "dry_run", "dry run", "仅供",
    ]
    found = [k for k in keywords if k in text.lower()]
    if found:
        return True, f"Found: {found}"
    return False, "No non-production label found"


def _has_one_sentence_overview(text: str) -> tuple[bool, str]:
    patterns = [
        r"一句话总览", r"今日总览", r"今日概览",
        r"one.?sentence.?overview", r"daily.?overview",
    ]
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True, "Overview section found"
    return False, "No one-sentence overview section found"


def _has_top_signals_section(text: str) -> tuple[bool, str]:
    patterns = [
        r"top.?signal", r"■\s*信号", r"##\s*信号", r"#\s*信号",
        r"■\s*Top.?Signal", r"##\s*Top.?Signal",
    ]
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True, "Top Signals section found"
    # Also check if there are signal-like entries
    if re.search(r"信号\s*\d|信号\s*[1-9]", text):
        return True, "Signal entries found"
    return False, "No Top Signals section found"


def _has_candidate_items_section(text: str) -> tuple[bool, str]:
    patterns = [
        r"候选.*未升级", r"未升级为信号", r"候选但未",
        r"candidate.*not.*promoted", r"not.*signal",
        r"未入选", r"排除", r"过滤",
    ]
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True, "Candidate items section found"
    return False, "No candidate items section found"


def _has_evidence_links(text: str) -> tuple[bool, str]:
    urls = re.findall(r"https?://\S+", text)
    if urls:
        return True, f"Found {len(urls)} URL(s)"
    return False, "No evidence URLs found"


def _has_uncertainty_section(text: str) -> tuple[bool, str]:
    patterns = [
        r"不确定性", r"证据.*不足", r"置信度.*低", r"未确认",
        r"需人工审核", r"uncertainty", r"evidence.*gap",
        r"低置信度", r"待验证", r"无法确认",
    ]
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True, "Uncertainty discussion found"
    return False, "No uncertainty discussion found"


def _has_follow_up_section(text: str) -> tuple[bool, str]:
    patterns = [
        r"需跟进", r"需.*跟进", r"后续.*关注", r"跟进",
        r"follow.?up", r"next.?step", r"深挖",
    ]
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True, "Follow-up section found"
    return False, "No follow-up section found"


def _distinguishes_signal_vs_news(text: str) -> tuple[bool, str]:
    risk_terms = [
        r"风险判断", r"影响.*风险", r"风险.*格局", r"风险曲线",
        r"能力风险", r"对齐风险", r"治理风险", r"扩散风险",
        r"risk.?judgment", r"risk.?landscape",
    ]
    found = [t for t in risk_terms if re.search(t, text, re.IGNORECASE)]
    if found:
        return True, f"Risk judgment language found: {len(found)} instances"
    return False, "No risk judgment language found — report may read as news summary"


def _each_signal_has_what_changed(text: str) -> tuple[bool, str]:
    patterns = [r"什么改变", r"变化[：:]", r"what.?changed", r"改变了"]
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True, "What-changed element found in signals"
    # Also check for signal blocks that describe change
    signal_blocks = re.findall(
        r"(?:信号|Signal)\s*\d.*?(?=(?:信号|Signal)\s*\d|$)",
        text, re.DOTALL | re.IGNORECASE,
    )
    if not signal_blocks:
        if re.search(r"未发现.*信号|no.*signal|0.*信号", text, re.IGNORECASE):
            return True, "No signals found — check N/A"
        return False, "No what-changed element in signals"
    return False, "No what-changed element in signals"


def _each_signal_has_why_it_matters(text: str) -> tuple[bool, str]:
    patterns = [r"为什么.*影响", r"影响[：:]", r"why.*matter", r"影响风险", r"风险影响"]
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True, "Why-it-matters element found in signals"
    if re.search(r"未发现.*信号|no.*signal|0.*信号", text, re.IGNORECASE):
        return True, "No signals found — check N/A"
    return False, "No why-it-matters element in signals"


def _each_signal_has_what_to_watch_next(text: str) -> tuple[bool, str]:
    patterns = [r"接下来.*关注", r"观察[：:]", r"watch.*next", r"关注.*下一步"]
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True, "What-to-watch-next element found in signals"
    if re.search(r"未发现.*信号|no.*signal|0.*信号", text, re.IGNORECASE):
        return True, "No signals found — check N/A"
    return False, "No what-to-watch-next element in signals"


def _avoids_tool_log_style(text: str) -> tuple[bool, str]:
    tool_patterns = [
        r"Calling tool", r"Tool call", r"risk_raw_item_store\(",
        r"risk_source_run_record\(", r"risk_signal_store\(",
        r"risk_raw_item_seen_check\(", r"risk_digest_store\(",
        r"risk_discovery_helper_preview\(", r"risk_source_health_summary\(",
        r"MCP tool", r"calling MCP", r"调用工具",
    ]
    tool_count = sum(len(re.findall(p, text, re.IGNORECASE)) for p in tool_patterns)
    if tool_count > 5:
        return False, f"Too many tool-call references ({tool_count})"
    return True, f"Tool-call references acceptable ({tool_count})"


def _avoids_news_dump_style(text: str) -> tuple[bool, str]:
    risk_lang = [
        r"风险判断", r"影响.*风险", r"风险.*变化", r"风险格局",
        r"severity", r"confidence", r"置信度", r"严重度",
        r"不确定性", r"证据",
    ]
    found = sum(1 for p in risk_lang if re.search(p, text, re.IGNORECASE))
    if found >= 2:
        return True, f"Risk judgment language present ({found} terms)"
    return False, f"Insufficient risk judgment language ({found} terms) — may be news dump"


def _mentions_no_signal_if_none_found(text: str) -> tuple[bool, str]:
    if re.search(r"信号\s*\d|Signal\s*\d|■\s*信号|##\s*信号|Top.?Signal", text, re.IGNORECASE):
        return True, "Signals present — check N/A"
    if re.search(r"未发现.*信号|no.*signal|0.*信号|无.*信号", text, re.IGNORECASE):
        return True, "No-signal acknowledgment found"
    return False, "No signals found and no acknowledgment of zero signals"


def _includes_source_coverage(text: str) -> tuple[bool, str]:
    patterns = [
        r"来源.*扫描", r"来源覆盖", r"扫描了.*来源", r"检查了.*来源",
        r"source.?coverage", r"sources.*checked",
        r"来源.*摘要",
    ]
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True, "Source coverage section found"
    return False, "No source coverage section found"


def _includes_helper_notes_if_helpers_used(text: str) -> tuple[bool, str]:
    helper_used = re.search(r"helper|Helper|Scrapling|scrapling|preview", text, re.IGNORECASE)
    if not helper_used:
        return True, "No helpers mentioned — check N/A"
    if re.search(r"helper.*使用|Helper.*usage|helper.*有效|helper.*候选", text, re.IGNORECASE):
        return True, "Helper usage notes found"
    return False, "Helpers mentioned but no usage notes"


def _avoids_product_announcements_as_signals(text: str) -> tuple[bool, str]:
    product_lang = [
        r"发布了?新.*产品", r"新.*功能上线", r"launched.*new.*product",
        r"announced.*new.*feature", r"新.*模型发布",
    ]
    signal_section = _extract_signal_section(text)
    if not signal_section:
        return True, "No signal section to check"
    product_hits = sum(1 for p in product_lang if re.search(p, signal_section, re.IGNORECASE))
    if product_hits > 0:
        risk_justification = re.search(
            r"影响.*风险|风险.*判断|风险.*格局|risk.*impact",
            signal_section, re.IGNORECASE,
        )
        if risk_justification:
            return True, "Product mentions include risk justification"
        return False, f"Product announcements without risk justification ({product_hits})"
    return True, "No product announcements in signal section"


def _has_chinese_content(text: str) -> tuple[bool, str]:
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    if cjk > 20:
        return True, f"Chinese content found ({cjk} CJK chars)"
    return False, f"Insufficient Chinese content ({cjk} CJK chars)"


# Register all check functions
_register("has_non_production_label", _has_non_production_label)
_register("has_one_sentence_overview", _has_one_sentence_overview)
_register("has_top_signals_section", _has_top_signals_section)
_register("has_candidate_items_section", _has_candidate_items_section)
_register("has_evidence_links", _has_evidence_links)
_register("has_uncertainty_section", _has_uncertainty_section)
_register("has_follow_up_section", _has_follow_up_section)
_register("distinguishes_signal_vs_news", _distinguishes_signal_vs_news)
_register("each_signal_has_what_changed", _each_signal_has_what_changed)
_register("each_signal_has_why_it_matters", _each_signal_has_why_it_matters)
_register("each_signal_has_what_to_watch_next", _each_signal_has_what_to_watch_next)
_register("avoids_tool_log_style", _avoids_tool_log_style)
_register("avoids_news_dump_style", _avoids_news_dump_style)
_register("mentions_no_signal_if_none_found", _mentions_no_signal_if_none_found)
_register("includes_source_coverage", _includes_source_coverage)
_register("includes_helper_notes_if_helpers_used", _includes_helper_notes_if_helpers_used)
_register("avoids_product_announcements_as_signals", _avoids_product_announcements_as_signals)
_register("has_chinese_content", _has_chinese_content)


def _avoids_advisory_as_final_evidence(text: str) -> tuple[bool, str]:
    # Check if report treats advisory/preprocessing output as final judgment
    advisory_patterns = [
        r"advisory_confidence.*信号", r"advisory_relevance.*信号",
        r"预处理.*判断.*最终", r"小模型.*判断",
    ]
    for p in advisory_patterns:
        if re.search(p, text, re.IGNORECASE):
            return False, "Report appears to treat advisory preprocessing as final judgment"
    return True, "No advisory-as-final-evidence pattern detected"


_register("avoids_advisory_as_final_evidence", _avoids_advisory_as_final_evidence)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_signal_section(text: str) -> str:
    """Extract the Top Signals section from the report."""
    match = re.search(
        r"(?:信号|Top.?Signal|Signal)\s*\n(.*?)(?=\n(?:#{1,3}\s|■\s)|$)",
        text, re.DOTALL | re.IGNORECASE,
    )
    if match:
        return match.group(1)
    return ""


def _detect_anti_patterns(text: str) -> list[str]:
    """Detect common quality anti-patterns."""
    patterns: list[tuple[str, str]] = [
        ("tool_log", r"(?:Calling tool|Tool call|MCP tool|calling MCP|调用工具).{0,50}"),
        ("raw_item_dump", r"(?:raw.?item|候选条目).{0,30}(?:\n.*){10,}"),
        ("no_evidence_links", r"^((?!https?://).)*$"),
        ("hype_language", r"(?:革命性|revolutionary|突破性|groundbreaking"
                          r"|前所未有|unprecedented|颠覆性)"),
        ("agi_sensationalism", r"AGI.{0,20}(?:即将|imminent|arriving|到来)"),
        ("news_headline_only", r"^\s*[-*]\s+\[.*?\]\(https?://.*?\)\s*$"),
    ]
    found = []
    for name, pattern in patterns:
        if re.search(pattern, text, re.MULTILINE | re.IGNORECASE):
            found.append(name)
    return found


def _generate_suggestions(failed_checks: list[str], anti_patterns: list[str]) -> list[str]:
    """Generate improvement suggestions from failed checks and anti-patterns."""
    suggestions: list[str] = []

    if "has_one_sentence_overview" in failed_checks:
        suggestions.append(
            "Add a one-sentence overview (今日一句话总览) at the top of the report"
        )
    if "has_top_signals_section" in failed_checks:
        suggestions.append("Add a Top Signals section with structured signal entries")
    if "has_evidence_links" in failed_checks:
        suggestions.append("Include primary source URLs as evidence for each signal")
    if "has_uncertainty_section" in failed_checks:
        suggestions.append("Add an uncertainty or evidence-gap section")
    if "has_follow_up_section" in failed_checks:
        suggestions.append("Add a follow-up section (需跟进)")
    if "distinguishes_signal_vs_news" in failed_checks:
        suggestions.append(
            "Distinguish signals from news — explain risk judgment, not just what happened"
        )
    if "each_signal_has_what_changed" in failed_checks:
        suggestions.append("Each signal must explain what changed (什么改变了)")
    if "each_signal_has_why_it_matters" in failed_checks:
        suggestions.append(
            "Each signal must explain why it affects risk judgment (为什么影响风险判断)"
        )
    if "each_signal_has_what_to_watch_next" in failed_checks:
        suggestions.append(
            "Each signal must identify what to watch next (接下来关注什么)"
        )
    if "avoids_tool_log_style" in failed_checks:
        suggestions.append(
            "Remove tool-call logs from the report — focus on editorial judgment"
        )
    if "avoids_news_dump_style" in failed_checks:
        suggestions.append(
            "Add risk judgment language — this reads as a news dump, not intelligence"
        )
    if "avoids_product_announcements_as_signals" in failed_checks:
        suggestions.append(
            "Do not treat product announcements as signals without risk justification"
        )
    if "has_candidate_items_section" in failed_checks:
        suggestions.append(
            "Add a section for candidate items that were considered but not promoted"
        )
    if "has_chinese_content" in failed_checks:
        suggestions.append("Report should contain meaningful Chinese-language content")

    if "tool_log" in anti_patterns:
        suggestions.append(
            "Tool-call process logs detected — remove or move to appendix"
        )
    if "hype_language" in anti_patterns:
        suggestions.append(
            "Hype/sensationalist language detected — use neutral, evidence-backed tone"
        )
    if "agi_sensationalism" in anti_patterns:
        suggestions.append(
            "AGI sensationalism detected — avoid timeline speculation without evidence"
        )

    return suggestions
