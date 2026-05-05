from fastapi.testclient import TestClient

from frontier_ai_risk_observer.api.main import app
from frontier_ai_risk_observer.core.config import get_settings


def test_health() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_returns_controlled_unavailable_for_invalid_db_url(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("DATABASE_URL", "not a valid sqlalchemy url")
    get_settings.cache_clear()
    client = TestClient(app)

    response = client.get("/ready")

    get_settings.cache_clear()
    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"
    assert response.json()["reason"] == "database_config"
