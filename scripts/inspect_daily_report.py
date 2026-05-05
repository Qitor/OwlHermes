"""Inspect daily report DB state and latest run artifacts.

Works with the configured DATABASE_URL (SQLite or PostgreSQL).
Does not require Hermes, Docker, or external network access.
"""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

REPO_ROOT = Path(__file__).resolve().parent.parent
DAILY_RUNS_DIR = REPO_ROOT / "runs" / "daily"


def _redact_url(url: str) -> str:
    try:
        parsed = make_url(url)
        if parsed.drivername.startswith("sqlite"):
            return url
        return (
            f"{parsed.drivername}://***@"
            f"{parsed.host}:{parsed.port or 5432}/{parsed.database}"
        )
    except Exception:
        return "<invalid-url>"


def _latest_daily_run() -> Path | None:
    """Find the latest daily run directory."""
    if not DAILY_RUNS_DIR.exists():
        return None
    dirs = sorted(
        [d for d in DAILY_RUNS_DIR.iterdir() if d.is_dir()],
        key=lambda d: d.name,
        reverse=True,
    )
    return dirs[0] if dirs else None


def main() -> None:
    database_url = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{Path('.local/risk_observer_dryrun.db').resolve()}",
    )

    print(f"Database URL: {_redact_url(database_url)}")
    print()

    # Latest daily run
    latest_run = _latest_daily_run()
    if latest_run:
        print(f"Latest daily run: {latest_run}")
        if (latest_run / "daily_report.md").exists():
            print(f"  Daily report: {latest_run / 'daily_report.md'}")
    else:
        print("No daily report runs found.")
    print()

    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            # Table counts
            tables = [
                "raw_items", "source_runs", "signals",
                "digests", "sources", "source_health",
            ]
            print("=== Table Counts ===")
            for table in tables:
                try:
                    result = conn.execute(
                        text(f"SELECT COUNT(*) FROM {table}"),
                    )
                    print(f"  {table}: {result.scalar()}")
                except Exception:
                    print(f"  {table}: (not found)")

            # Dedup/seen stats
            print("\n=== Dedup/Seen Stats ===")
            try:
                result = conn.execute(text(
                    "SELECT COUNT(*) FROM raw_items WHERE seen_count > 1"
                ))
                print(f"  Items seen more than once: {result.scalar()}")
            except Exception:
                print("  (could not query)")

            # Recent raw items
            print("\n=== Recent Raw Items (last 5) ===")
            try:
                rows = conn.execute(text(
                    "SELECT source_id, title, canonical_url, seen_count "
                    "FROM raw_items ORDER BY created_at DESC LIMIT 5"
                ))
                for row in rows:
                    print(f"  [{row.source_id}] {row.title}")
                    print(f"    URL: {row.canonical_url or 'N/A'}, Seen: {row.seen_count}")
            except Exception as exc:
                print(f"  (error: {exc})")

            # Recent source runs
            print("\n=== Recent Source Runs (last 5) ===")
            try:
                rows = conn.execute(text(
                    "SELECT source_id, status, items_found, items_new, "
                    "items_duplicate, metadata "
                    "FROM source_runs ORDER BY created_at DESC LIMIT 5"
                ))
                for row in rows:
                    helper = ""
                    if row.metadata and "helper_used" in str(row.metadata):
                        helper = " [helper]"
                    print(
                        f"  [{row.source_id}] status={row.status}, "
                        f"found={row.items_found}, new={row.items_new}, "
                        f"dup={row.items_duplicate}{helper}"
                    )
            except Exception as exc:
                print(f"  (error: {exc})")

            # Recent signals
            print("\n=== Recent Signals (last 5) ===")
            try:
                rows = conn.execute(text(
                    "SELECT title_zh, signal_type, severity, confidence "
                    "FROM signals ORDER BY created_at DESC LIMIT 5"
                ))
                for row in rows:
                    print(
                        f"  {row.title_zh} "
                        f"(type={row.signal_type}, "
                        f"sev={row.severity}, conf={row.confidence})"
                    )
            except Exception as exc:
                print(f"  (error: {exc})")

            # Most recent digest
            print("\n=== Most Recent Digest ===")
            try:
                rows = conn.execute(text(
                    "SELECT title, status, digest_date, timezone "
                    "FROM digests ORDER BY created_at DESC LIMIT 1"
                ))
                has_digest = False
                for row in rows:
                    has_digest = True
                    print(f"  {row.title}")
                    print(f"    Status: {row.status}, Date: {row.digest_date}, TZ: {row.timezone}")
                if not has_digest:
                    print("  (no digests)")
            except Exception as exc:
                print(f"  (error: {exc})")

        engine.dispose()
    except Exception as exc:
        print(f"Failed to inspect database: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
