from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from frontier_ai_risk_observer.api.main import app
from frontier_ai_risk_observer.db.models import Base, RawItem, Source, SourceRun
from frontier_ai_risk_observer.db.session import get_db_session


@pytest.fixture
def client() -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[Source.__table__, RawItem.__table__, SourceRun.__table__],
    )
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_db() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_raw_item_seen_check_false_for_unknown_item(client: TestClient) -> None:
    response = client.get("/ingestion/raw-items/seen", params={"url": "https://example.com/item"})

    assert response.status_code == 200
    assert response.json() == {
        "seen": False,
        "match_type": None,
        "raw_item_id": None,
        "canonical_url": None,
        "dedup_key": None,
    }


def test_raw_item_create_then_seen_check_true(client: TestClient) -> None:
    create_response = _create_raw_item(client)

    assert create_response.status_code == 200
    body = create_response.json()
    item = body["item"]
    assert body["is_duplicate"] is False
    assert item["source_id"] == "openai_news"
    assert item["title"] == "A useful raw item"
    assert item["canonical_url"] == "https://example.com/item"
    assert item["seen_count"] == 1

    seen_response = client.get(
        "/ingestion/raw-items/seen",
        params={"url": "https://example.com/item"},
    )

    assert seen_response.status_code == 200
    assert seen_response.json()["seen"] is True
    assert seen_response.json()["raw_item_id"] == item["id"]
    assert seen_response.json()["match_type"] == "canonical_url"
    assert seen_response.json()["dedup_key"] == "url:https://example.com/item"


def test_repeated_raw_item_returns_duplicate_and_increments_count(
    client: TestClient,
) -> None:
    first = _create_raw_item(client).json()
    second = client.post(
        "/ingestion/raw-items",
        json={
            "source_id": "openai_news",
            "source_type": "web_article",
            "url": "https://example.com/item?utm_source=test",
            "title": "A useful raw item",
            "content_text": "Evidence text",
            "metadata": {"discovered_by": "second"},
        },
    )

    assert second.status_code == 200
    body = second.json()
    assert body["is_duplicate"] is True
    assert body["match_type"] == "canonical_url"
    assert body["item"]["id"] == first["item"]["id"]
    assert body["item"]["seen_count"] == 2


def test_raw_item_list_filters_by_source_id_and_url(client: TestClient) -> None:
    item = _create_raw_item(client).json()["item"]

    by_source = client.get("/ingestion/raw-items", params={"source_id": "openai_news"})
    by_url = client.get("/ingestion/raw-items", params={"url": "https://example.com/item"})
    by_canonical = client.get(
        "/ingestion/raw-items",
        params={"canonical_url": "https://example.com/item?utm_medium=email"},
    )
    by_dedup_key = client.get(
        "/ingestion/raw-items",
        params={"dedup_key": item["dedup_key"]},
    )

    assert by_source.status_code == 200
    assert len(by_source.json()) == 1
    assert by_url.status_code == 200
    assert len(by_url.json()) == 1
    assert by_canonical.status_code == 200
    assert len(by_canonical.json()) == 1
    assert by_dedup_key.status_code == 200
    assert len(by_dedup_key.json()) == 1


def test_duplicate_candidates_returns_deterministic_matches(client: TestClient) -> None:
    item = _create_raw_item(client).json()["item"]

    response = client.get(
        "/ingestion/raw-items/duplicates",
        params={"url": "https://example.com/item?utm_campaign=launch"},
    )

    assert response.status_code == 200
    matches = response.json()
    assert len(matches) == 1
    assert matches[0]["match_type"] == "canonical_url"
    assert matches[0]["item"]["id"] == item["id"]


def test_source_run_recording_works(client: TestClient) -> None:
    response = client.post(
        "/ingestion/source-runs",
        json={
            "source_id": "axrp",
            "kind": "podcast",
            "status": "success",
            "items_found": 2,
            "items_new": 1,
            "items_duplicate": 1,
            "items_error": 0,
            "metadata": {"note": "offline test"},
        },
    )

    assert response.status_code == 200
    assert response.json()["source_id"] == "axrp"
    assert response.json()["source_type"] == "podcast"
    assert response.json()["items_found"] == 2
    assert response.json()["items_duplicate"] == 1


def test_raw_item_unknown_source_returns_400(client: TestClient) -> None:
    response = client.post(
        "/ingestion/raw-items",
        json={
            "source_id": "missing_source",
            "kind": "web_article",
            "url": "https://example.com/item",
            "title": "Unknown source",
        },
    )

    assert response.status_code == 400


def test_seen_check_requires_url_or_content_hash(client: TestClient) -> None:
    response = client.get("/ingestion/raw-items/seen")

    assert response.status_code == 422


def test_db_unavailable_error_is_controlled() -> None:
    def broken_db() -> Iterator[Session]:
        raise SQLAlchemyError("database down")
        yield  # pragma: no cover

    app.dependency_overrides[get_db_session] = broken_db
    try:
        response = TestClient(app).get("/ingestion/raw-items")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["reason"] == "database_connection"


def _create_raw_item(client: TestClient):
    return client.post(
        "/ingestion/raw-items",
        json={
            "source_id": "openai_news",
            "source_type": "web_article",
            "url": "https://example.com/item",
            "title": "A useful raw item",
            "content_text": "Evidence text",
            "content_hash": "hash-one",
            "metadata": {"discovered_by": "test"},
        },
    )
