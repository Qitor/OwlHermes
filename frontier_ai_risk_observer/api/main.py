"""Minimal FastAPI app for local backend smoke tests."""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from frontier_ai_risk_observer import __version__
from frontier_ai_risk_observer.api.routes.ingestion import router as ingestion_router
from frontier_ai_risk_observer.api.routes.registry import router as registry_router
from frontier_ai_risk_observer.core.config import get_settings
from frontier_ai_risk_observer.db.session import (
    DatabaseConfigurationError,
    DatabaseUnavailableError,
    check_database_connection,
)

app = FastAPI(
    title="Frontier AI Risk Signal Observer",
    version=__version__,
    description="Deterministic backend for the Hermes-Agent risk signal workflow.",
)

app.include_router(registry_router)
app.include_router(ingestion_router)


@app.exception_handler(DatabaseConfigurationError)
def database_configuration_exception_handler(
    _request: object, exc: DatabaseConfigurationError
) -> JSONResponse:
    """Return controlled errors when DB configuration is invalid."""
    return JSONResponse(
        status_code=503,
        content={"status": "unavailable", "reason": "database_config", "detail": str(exc)},
    )


@app.exception_handler(DatabaseUnavailableError)
def database_unavailable_exception_handler(
    _request: object, exc: DatabaseUnavailableError
) -> JSONResponse:
    """Return controlled errors when DB operations fail."""
    return JSONResponse(
        status_code=503,
        content={"status": "unavailable", "reason": "database_connection", "detail": str(exc)},
    )


@app.exception_handler(SQLAlchemyError)
def sqlalchemy_exception_handler(_request: object, exc: SQLAlchemyError) -> JSONResponse:
    """Return controlled errors for SQLAlchemy failures raised by dependencies."""
    return JSONResponse(
        status_code=503,
        content={"status": "unavailable", "reason": "database_connection", "detail": str(exc)},
    )


@app.get("/health")
def health() -> dict[str, str]:
    """Return process health without requiring database access."""
    return {"status": "ok"}


@app.get("/ready", response_model=None)
def ready() -> dict[str, str] | JSONResponse:
    """Return database readiness without making /health depend on storage."""
    try:
        check_database_connection()
    except DatabaseConfigurationError as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "reason": "database_config", "detail": str(exc)},
        )
    except DatabaseUnavailableError as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "reason": "database_connection", "detail": str(exc)},
        )

    return {"status": "ok", "database": "ok"}


@app.get("/version")
def version() -> dict[str, str]:
    """Return package and environment metadata useful for smoke tests."""
    settings = get_settings()
    return {
        "version": __version__,
        "service": "frontier-ai-risk-observer",
        "source_registry_dir": str(settings.source_registry_dir),
    }


def run() -> None:
    """Run the development API server."""
    uvicorn.run("frontier_ai_risk_observer.api.main:app", host="127.0.0.1", port=8787)
