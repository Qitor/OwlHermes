"""Initialize a local SQLite dry-run database for R1-08+.

Uses ``Base.metadata.create_all()`` instead of the Postgres-specific
``schemas/schema.sql`` so that the dry-run DB works without Docker
or a local Postgres instance.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import event

from frontier_ai_risk_observer.db.models import Base
from frontier_ai_risk_observer.db.session import (
    DatabaseConfigurationError,
    create_db_engine,
)

DRYRUN_DB_DIR = Path(".local")
DRYRUN_DB_URL = f"sqlite:///{DRYRUN_DB_DIR}/risk_observer_dryrun.db"


def init_dryrun_db(database_url: str | None = None) -> str:
    """Create or verify a local SQLite dry-run database.

    Returns the database URL used.
    """
    url = database_url or DRYRUN_DB_URL
    db_path = _sqlite_path_from_url(url)
    if db_path is not None:
        db_path.parent.mkdir(parents=True, exist_ok=True)

    engine = create_db_engine(url)

    # Enable WAL mode and foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):  # type: ignore[name-defined]  # noqa: ARG001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    engine.dispose()
    return url


def _sqlite_path_from_url(url: str) -> Path | None:
    """Extract the file path from a sqlite:/// URL, or None."""
    if not url.startswith("sqlite:///"):
        return None
    # sqlite:///./.local/risk_observer_dryrun.db → ./.local/risk_observer_dryrun.db
    return Path(url[len("sqlite:///"):])


def main() -> int:
    """CLI entrypoint for ``python -m frontier_ai_risk_observer.db.dryrun``."""
    try:
        url = init_dryrun_db()
    except (DatabaseConfigurationError, Exception) as exc:
        print(f"Failed to initialize dry-run DB: {exc}")
        return 1
    print(f"Dry-run DB initialized: {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
