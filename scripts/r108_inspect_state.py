"""Inspect the R1-08 dry-run database state.

Works with the configured DATABASE_URL (SQLite or PostgreSQL).
Does not require Hermes, Docker, or external network access.
"""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


def _redact_url(url: str) -> str:
    """Show DB type and path, redact credentials."""
    try:
        parsed = make_url(url)
        if parsed.drivername.startswith("sqlite"):
            return url
        return f"{parsed.drivername}://***@{parsed.host}:{parsed.port or 5432}/{parsed.database}"
    except Exception:
        return "<invalid-url>"


def main() -> None:
    database_url = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{Path('.local/risk_observer_dryrun.db').resolve()}",
    )

    print(f"Database URL: {_redact_url(database_url)}")
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
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    print(f"  {table}: {count}")
                except Exception:
                    print(f"  {table}: (not found or error)")

            # Recent raw items
            print("\n=== Recent Raw Items (last 10) ===")
            try:
                rows = conn.execute(text(
                    "SELECT id, source_id, title, canonical_url, "
                    "ingestion_status, first_seen_at, last_seen_at "
                    "FROM raw_items ORDER BY created_at DESC LIMIT 10"
                ))
                for row in rows:
                    print(f"  [{row.source_id}] {row.title}")
                    print(f"    URL: {row.canonical_url or 'N/A'}")
                    print(f"    Status: {row.ingestion_status}, "
                          f"First: {row.first_seen_at}, Last: {row.last_seen_at}")
            except Exception as exc:
                print(f"  (error: {exc})")

            # Recent source runs
            print("\n=== Recent Source Runs (last 5) ===")
            try:
                rows = conn.execute(text(
                    "SELECT source_id, status, items_found, items_new, "
                    "items_duplicate, items_error "
                    "FROM source_runs ORDER BY created_at DESC LIMIT 5"
                ))
                for row in rows:
                    print(f"  [{row.source_id}] status={row.status}, "
                          f"found={row.items_found}, new={row.items_new}, "
                          f"dup={row.items_duplicate}, err={row.items_error}")
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
                    print(f"  {row.title_zh} "
                          f"(type={row.signal_type}, "
                          f"severity={row.severity}, confidence={row.confidence})")
            except Exception as exc:
                print(f"  (error: {exc})")

            # Most recent digest
            print("\n=== Most Recent Digest ===")
            try:
                rows = conn.execute(text(
                    "SELECT title, status, digest_date, timezone "
                    "FROM digests ORDER BY created_at DESC LIMIT 1"
                ))
                for row in rows:
                    print(f"  {row.title}")
                    print(f"    Status: {row.status}, Date: {row.digest_date}, "
                          f"TZ: {row.timezone}")
                else:
                    if rows.rowcount == 0:
                        print("  (no digests)")
            except Exception as exc:
                print(f"  (error: {exc})")

        engine.dispose()
    except Exception as exc:
        print(f"Failed to inspect database: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
