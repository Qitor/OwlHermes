from pathlib import Path

import pytest

from frontier_ai_risk_observer.db import models
from frontier_ai_risk_observer.db.init import load_schema_sql
from frontier_ai_risk_observer.db.session import (
    DatabaseConfigurationError,
    create_db_engine,
    create_session_factory,
)


def test_db_session_module_imports_and_factory_builds_with_sqlite() -> None:
    engine = create_db_engine("sqlite:///:memory:")
    session_factory = create_session_factory(engine)

    assert session_factory.kw["bind"] is engine


def test_invalid_database_url_has_clean_error() -> None:
    with pytest.raises(DatabaseConfigurationError, match="DATABASE_URL is invalid"):
        create_db_engine("not a valid sqlalchemy url")


def test_core_models_are_registered() -> None:
    table_names = set(models.Base.metadata.tables)

    assert {
        "sources",
        "raw_items",
        "signals",
        "digests",
        "delivery_events",
        "audit_logs",
    }.issubset(table_names)


def test_schema_sql_loads_from_source_of_truth() -> None:
    schema_sql = load_schema_sql(Path("schemas/schema.sql"))

    assert "CREATE TABLE IF NOT EXISTS sources" in schema_sql
    assert "CREATE TABLE IF NOT EXISTS raw_items" in schema_sql
