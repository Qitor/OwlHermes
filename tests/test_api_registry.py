from fastapi.testclient import TestClient

from frontier_ai_risk_observer.api.main import app


def test_registry_summary_returns_counts() -> None:
    client = TestClient(app)

    response = client.get("/registry")

    assert response.status_code == 200
    assert response.json()["sources"] > 0
    assert response.json()["podcasts"] > 0
    assert response.json()["events"] > 0
    assert response.json()["benchmarks"] > 0


def test_registry_sources_returns_validated_entries() -> None:
    client = TestClient(app)

    response = client.get("/registry/sources")

    assert response.status_code == 200
    sources = response.json()
    assert any(source["id"] == "openai_news" for source in sources)


def test_registry_source_by_id() -> None:
    client = TestClient(app)

    response = client.get("/registry/sources/openai_news")

    assert response.status_code == 200
    assert response.json()["id"] == "openai_news"


def test_registry_source_filtering() -> None:
    client = TestClient(app)

    response = client.get("/registry/sources", params={"category": "frontier_ai_lab"})

    assert response.status_code == 200
    assert response.json()
    assert all(source["category"] == "frontier_ai_lab" for source in response.json())


def test_registry_unknown_source_returns_404() -> None:
    client = TestClient(app)

    response = client.get("/registry/sources/not_a_source")

    assert response.status_code == 404


def test_registry_due_sources_are_enabled_and_sorted() -> None:
    client = TestClient(app)

    response = client.get("/registry/due-sources", params={"limit": 10})

    assert response.status_code == 200
    entries = response.json()
    assert entries
    assert all(entry["enabled"] for entry in entries)
    sort_keys = [_sort_key(entry) for entry in entries]
    assert sort_keys == sorted(sort_keys)


def test_registry_due_sources_kind_filter() -> None:
    client = TestClient(app)

    response = client.get("/registry/due-sources", params={"kind": "podcast"})

    assert response.status_code == 200
    assert response.json()
    assert all(entry["kind"] == "podcast" for entry in response.json())


def _sort_key(entry: dict[str, object]) -> tuple[int, str]:
    priority_order = {"high": 0, "medium": 1, "low": 2}
    return (priority_order.get(str(entry.get("priority")), 99), str(entry["id"]))
