"""Inspect the R1-09B dry-run database state.

Works with the configured DATABASE_URL (SQLite or PostgreSQL).
Does not require Hermes, Docker, or external network access.
Extends the R1-08 inspector with helper-related metadata.
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
        return (
            f"{parsed.drivername}://***@"
            f"{parsed.host}:{parsed.port or 5432}/{parsed.database}"
        )
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
            counts: dict[str, int] = {}
            for table in tables:
                try:
                    result = conn.execute(
                        text(f"SELECT COUNT(*) FROM {table}"),
                    )
                    count = result.scalar()
                    counts[table] = count
                    print(f"  {table}: {count}")
                except Exception:
                    print(f"  {table}: (not found or error)")

            # Seen/duplicate counts
            print("\n=== Dedup/Seen Stats ===")
            try:
                result = conn.execute(text(
                    "SELECT COUNT(*) FROM raw_items WHERE seen_count > 1"
                ))
                seen_multi = result.scalar()
                print(f"  Items seen more than once: {seen_multi}")
            except Exception:
                print("  (could not query seen_count)")

            # Recent raw items
            print("\n=== Recent Raw Items (last 10) ===")
            try:
                rows = conn.execute(text(
                    "SELECT id, source_id, title, canonical_url, "
                    "ingestion_status, first_seen_at, last_seen_at, "
                    "seen_count, dedup_key "
                    "FROM raw_items ORDER BY created_at DESC LIMIT 10"
                ))
                for row in rows:
                    print(f"  [{row.source_id}] {row.title}")
                    print(
                        f"    URL: {row.canonical_url or 'N/A'}",
                    )
                    print(
                        f"    Status: {row.ingestion_status}, "
                        f"First: {row.first_seen_at}, "
                        f"Last: {row.last_seen_at}, "
                        f"Seen: {row.seen_count}",
                    )
            except Exception as exc:
                print(f"  (error: {exc})")

            # Recent source runs with helper metadata
            print("\n=== Recent Source Runs (last 10) ===")
            try:
                rows = conn.execute(text(
                    "SELECT source_id, status, items_found, items_new, "
                    "items_duplicate, items_error, metadata "
                    "FROM source_runs ORDER BY created_at DESC LIMIT 10"
                ))
                for row in rows:
                    meta = row.metadata or ""
                    helper_note = ""
                    if "helper_used" in str(meta):
                        helper_note = " [helper-assisted]"
                    print(
                        f"  [{row.source_id}] status={row.status}, "
                        f"found={row.items_found}, new={row.items_new}, "
                        f"dup={row.items_duplicate}, "
                        f"err={row.items_error}{helper_note}",
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
                        f"severity={row.severity}, "
                        f"confidence={row.confidence})"
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
                    print(
                        f"    Status: {row.status}, "
                        f"Date: {row.digest_date}, "
                        f"TZ: {row.timezone}",
                    )
                if not has_digest:
                    print("  (no digests)")
            except Exception as exc:
                print(f"  (error: {exc})")

            # R1-09B-specific: helper-assisted source run summary
            print("\n=== Helper-Assisted Source Runs ===")
            try:
                rows = conn.execute(text(
                    "SELECT source_id, COUNT(*) as run_count "
                    "FROM source_runs "
                    "WHERE metadata LIKE '%helper_used%' "
                    "GROUP BY source_id"
                ))
                has_helper_runs = False
                for row in rows:
                    has_helper_runs = True
                    print(
                        f"  {row.source_id}: {row.run_count} helper-assisted run(s)"
                    )
                if not has_helper_runs:
                    print("  (no helper-assisted source runs yet)")
            except Exception as exc:
                print(f"  (could not query: {exc})")

        engine.dispose()
    except Exception as exc:
        print(f"Failed to inspect database: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
