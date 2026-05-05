"""Apply the first-version PostgreSQL schema from ``schemas/schema.sql``."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

from frontier_ai_risk_observer.db.session import (
    DatabaseConfigurationError,
    DatabaseUnavailableError,
    create_db_engine,
)

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "schema.sql"


def load_schema_sql(schema_path: Path = SCHEMA_PATH) -> str:
    """Load the SQL schema used as the R1-02 source of truth."""
    return schema_path.read_text(encoding="utf-8")


def init_database(database_url: str | None = None, schema_path: Path = SCHEMA_PATH) -> None:
    """Apply ``schemas/schema.sql`` to the configured PostgreSQL database."""
    engine = create_db_engine(database_url)
    schema_sql = load_schema_sql(schema_path)

    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(schema_sql)
    except SQLAlchemyError as exc:
        msg = f"Failed to initialize database with {schema_path}: {exc}"
        raise DatabaseUnavailableError(msg) from exc


def main() -> int:
    """CLI entrypoint for ``python -m frontier_ai_risk_observer.db.init``."""
    try:
        init_database()
    except (DatabaseConfigurationError, DatabaseUnavailableError) as exc:
        print(exc)
        return 1

    print(f"Applied schema: {SCHEMA_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
