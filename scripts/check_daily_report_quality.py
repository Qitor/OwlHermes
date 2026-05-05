"""Daily report quality checker.

Modes:
  --report PATH       Check a specific report file.
  --latest            Check the latest runs/daily/*/daily_report.md.
  --json              Output results as JSON.
  --fail-under SCORE  Exit non-zero if score < SCORE (0-100).
  --write-review PATH Write a Markdown review file.

No LLMs. No Hermes. No network. No Postgres.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from frontier_ai_risk_observer.quality.report_quality import (
    QualityReport,
    check_report,
    load_checklist,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = REPO_ROOT / "runs" / "daily"
CHECKLIST_PATH = REPO_ROOT / "quality" / "daily_report_checklist.yaml"


def find_latest_report() -> Path | None:
    """Find the latest daily_report.md in runs/daily/."""
    if not RUNS_DIR.exists():
        return None
    dirs = sorted(RUNS_DIR.iterdir(), reverse=True)
    for d in dirs:
        if d.is_dir():
            report = d / "daily_report.md"
            if report.exists():
                return report
    return None


def format_report(qr: QualityReport) -> str:
    """Format quality report as human-readable text."""
    lines = [
        "=== Daily Report Quality Check ===\n",
        f"Report: {qr.report_path}",
        f"Score: {qr.score}/{qr.max_score} ({qr.score_percent}%)\n",
    ]

    lines.append("Checks:")
    for c in qr.checks:
        status = "PASS" if c.passed else "FAIL"
        lines.append(f"  [{status}] {c.name} (weight {c.weight})")
        if not c.passed and c.notes:
            lines.append(f"         {c.notes}")

    if qr.anti_patterns:
        lines.append(f"\nAnti-patterns detected: {', '.join(qr.anti_patterns)}")

    if qr.failed_checks:
        lines.append(f"\nFailed checks ({len(qr.failed_checks)}): {', '.join(qr.failed_checks)}")

    if qr.suggestions:
        lines.append("\nSuggestions:")
        for s in qr.suggestions:
            lines.append(f"  - {s}")

    return "\n".join(lines)


def format_review_md(qr: QualityReport) -> str:
    """Format quality report as Markdown review."""
    lines = [
        "# Daily Report Quality Review\n",
        f"- **Report**: {qr.report_path}",
        f"- **Score**: {qr.score}/{qr.max_score} ({qr.score_percent}%)",
        f"- **Timestamp**: {qr.timestamp}\n",
    ]

    if qr.failed_checks:
        lines.append("## Failed Checks\n")
        for c in qr.checks:
            if not c.passed:
                lines.append(f"- **{c.name}** ({c.check_id}): {c.notes}")
        lines.append("")

    if qr.anti_patterns:
        lines.append("## Anti-Patterns\n")
        for ap in qr.anti_patterns:
            lines.append(f"- {ap}")
        lines.append("")

    if qr.suggestions:
        lines.append("## Suggested Improvements\n")
        for s in qr.suggestions:
            lines.append(f"- {s}")
        lines.append("")

    lines.append("## All Checks\n")
    lines.append("| Check | Status | Weight | Notes |")
    lines.append("|-------|--------|--------|-------|")
    for c in qr.checks:
        status = "PASS" if c.passed else "FAIL"
        lines.append(f"| {c.name} | {status} | {c.weight} | {c.notes} |")

    return "\n".join(lines)


def to_json(qr: QualityReport) -> str:
    """Format quality report as JSON."""
    data = {
        "report_path": qr.report_path,
        "score": qr.score,
        "max_score": qr.max_score,
        "score_percent": qr.score_percent,
        "timestamp": qr.timestamp,
        "failed_checks": qr.failed_checks,
        "anti_patterns": qr.anti_patterns,
        "suggestions": qr.suggestions,
        "checks": [
            {
                "id": c.check_id,
                "name": c.name,
                "passed": c.passed,
                "weight": c.weight,
                "notes": c.notes,
            }
            for c in qr.checks
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Daily report quality checker",
    )
    parser.add_argument("--report", type=str, help="Path to daily_report.md")
    parser.add_argument(
        "--latest", action="store_true",
        help="Check the latest runs/daily/*/daily_report.md",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--fail-under", type=int, default=0,
        help="Exit non-zero if score percent < this value (0-100)",
    )
    parser.add_argument(
        "--write-review", type=str, default=None,
        help="Write Markdown review to this path",
    )
    args = parser.parse_args()

    if not args.report and not args.latest:
        parser.error("Specify --report PATH or --latest")

    report_path: Path | None = None
    if args.report:
        report_path = Path(args.report)
        if not report_path.exists():
            print(f"ERROR: Report not found: {report_path}")
            sys.exit(1)
    elif args.latest:
        report_path = find_latest_report()
        if report_path is None:
            print("ERROR: No daily report found in runs/daily/")
            print("  Run 'make daily-report' first, or use --report with a fixture.")
            sys.exit(1)

    text = report_path.read_text(encoding="utf-8")
    checklist = load_checklist(CHECKLIST_PATH)
    qr = check_report(text, checklist)
    qr.report_path = str(report_path)

    if args.json:
        print(to_json(qr))
    else:
        print(format_report(qr))

    if args.write_review:
        review_path = Path(args.write_review)
        review_path.parent.mkdir(parents=True, exist_ok=True)
        review_path.write_text(format_review_md(qr), encoding="utf-8")
        print(f"\nReview written to: {review_path}")

    if args.fail_under and qr.score_percent < args.fail_under:
        print(
            f"\nFAIL: Score {qr.score_percent}% is below threshold "
            f"{args.fail_under}%"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
