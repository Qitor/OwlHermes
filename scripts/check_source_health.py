"""CLI script for source health reporting."""

from __future__ import annotations

import json

from frontier_ai_risk_observer.services.source_health import source_health_summary


def main() -> None:
    summary = source_health_summary()
    print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))
    if summary["requires_human_review_count"] > 0 or summary["invalid_urls_count"] > 0:
        print("\nAction required: some entries need human review or have invalid URLs.")


if __name__ == "__main__":
    main()
