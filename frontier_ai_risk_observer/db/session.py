"""Database engine, session, and readiness helpers."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from frontier_ai_risk_observer.core.config import get_settings


class DatabaseConfigurationError(RuntimeError):
    """Raised when DATABASE_URL cannot be used to create an engine."""


class DatabaseUnavailableError(RuntimeError):
    """Raised when a configured database cannot be reached."""


def create_db_engine(database_url: str | None = None) -> Engine:
    """Create an SQLAlchemy engine from DATABASE_URL.

    This validates URL syntax early, but it does not hide connection failures;
    actual network/auth/database problems are raised when a connection is used.
    """
    resolved_url = database_url or get_settings().database_url
    if not resolved_url:
        msg = "DATABASE_URL is required for database operations."
        raise DatabaseConfigurationError(msg)

    try:
        make_url(resolved_url)
        return create_engine(resolved_url, pool_pre_ping=True)
    except ArgumentError as exc:
        msg = f"DATABASE_URL is invalid: {exc}"
        raise DatabaseConfigurationError(msg) from exc


def create_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    """Create a SQLAlchemy session factory."""
    return sessionmaker(bind=engine or create_db_engine(), autoflush=False, expire_on_commit=False)


SessionLocal = create_session_factory


def get_db_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    session_factory = create_session_factory()
    with session_factory() as session:
        yield session


def check_database_connection(database_url: str | None = None) -> None:
    """Run a minimal readiness query against the configured database."""
    try:
        engine = create_db_engine(database_url)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except DatabaseConfigurationError:
        raise
    except SQLAlchemyError as exc:
        msg = f"Database is unavailable: {exc}"
        raise DatabaseUnavailableError(msg) from exc
