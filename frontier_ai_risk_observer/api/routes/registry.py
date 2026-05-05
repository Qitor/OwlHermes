"""Registry API routes for Hermes-led source selection."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from frontier_ai_risk_observer.services import registry_service

router = APIRouter(prefix="/registry", tags=["registry"])


@router.get("")
def registry_summary() -> dict[str, int]:
    """Return registry group counts."""
    return registry_service.registry_summary()


@router.get("/sources")
def registry_sources(
    enabled: bool | None = None,
    category: str | None = None,
    priority: str | None = None,
    risk_domain: str | None = None,
) -> list[dict[str, object]]:
    """Return validated source entries."""
    return registry_service.list_sources(
        enabled=enabled,
        category=category,
        priority=priority,
        risk_domain=risk_domain,
    )


@router.get("/sources/{source_id}")
def registry_source(source_id: str) -> dict[str, object]:
    """Return one validated source entry."""
    source = registry_service.get_source(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail=f"Unknown source id: {source_id}")
    return source


@router.get("/podcasts")
def registry_podcasts(
    enabled: bool | None = None,
    priority: str | None = None,
    risk_domain: str | None = None,
) -> list[dict[str, object]]:
    """Return validated podcast entries."""
    return registry_service.list_podcasts(
        enabled=enabled,
        priority=priority,
        risk_domain=risk_domain,
    )


@router.get("/events")
def registry_events(
    enabled: bool | None = None,
    category: str | None = None,
    event_type: str | None = None,
    risk_domain: str | None = None,
) -> list[dict[str, object]]:
    """Return validated event entries."""
    return registry_service.list_events(
        enabled=enabled,
        category=category,
        event_type=event_type,
        risk_domain=risk_domain,
    )


@router.get("/benchmarks")
def registry_benchmarks(
    enabled: bool | None = None,
    risk_domain: str | None = None,
    priority: str | None = None,
) -> list[dict[str, object]]:
    """Return validated benchmark/framework watch entries."""
    return registry_service.list_benchmarks(
        enabled=enabled,
        risk_domain=risk_domain,
        priority=priority,
    )


@router.get("/due-sources")
def registry_due_sources(
    limit: int | None = Query(default=None, ge=1, le=500),
    kind: Literal["source", "podcast", "event", "benchmark"] | None = None,
    risk_domain: str | None = None,
) -> list[dict[str, object]]:
    """Return enabled registry entries Hermes should consider."""
    return registry_service.list_due_sources(limit=limit, kind=kind, risk_domain=risk_domain)
