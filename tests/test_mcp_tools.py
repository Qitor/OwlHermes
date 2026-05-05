from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from frontier_ai_risk_observer.db.models import Base, Digest, RawItem, Signal, Source, SourceRun
from frontier_ai_risk_observer.mcp import server


@pytest.fixture
def mcp_db() -> Iterator[None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            Source.__table__,
            RawItem.__table__,
            SourceRun.__table__,
            Signal.__table__,
            Digest.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def factory() -> Session:
        return session_factory()

    server.set_session_factory_for_tests(factory)
    try:
        yield
    finally:
        server.set_session_factory_for_tests(None)


def test_mcp_tool_functions_import_successfully() -> None:
    names = {tool.__name__ for tool in server.MCP_TOOL_FUNCTIONS}

    assert "risk_registry_summary" in names
    assert "risk_raw_item_store" in names
    assert "risk_digest_search" in names


def test_registry_tools_return_expected_data() -> None:
    summary = server.risk_registry_summary()
    due = server.risk_registry_list_due_sources(limit=2)
    source = server.risk_registry_get_source("openai_news")

    assert summary["ok"] is True
    assert summary["registry"]["sources"] >= 1
    assert due["ok"] is True
    assert due["count"] == 2
    assert source["ok"] is True
    assert source["source"]["id"] == "openai_news"


def test_raw_item_memory_tools_dedup_through_mcp_layer(mcp_db: None) -> None:
    unknown = server.risk_raw_item_seen_check(url="https://example.com/mcp")
    first = server.risk_raw_item_store(
        {
            "source_id": "openai_news",
            "kind": "web_article",
            "url": "https://example.com/mcp?utm_source=test",
            "title": "MCP memory item",
            "content_text": "Evidence text",
        }
    )
    second = server.risk_raw_item_store(
        {
            "source_id": "openai_news",
            "kind": "web_article",
            "url": "https://example.com/mcp?utm_campaign=launch",
            "title": "MCP memory item",
        }
    )
    seen = server.risk_raw_item_seen_check(url="https://example.com/mcp")
    candidates = server.risk_raw_item_duplicate_candidates(url="https://example.com/mcp")
    search = server.risk_raw_item_search(source_id="openai_news")

    assert unknown["ok"] is True
    assert unknown["seen"] is False
    assert first["ok"] is True
    assert first["is_duplicate"] is False
    assert second["ok"] is True
    assert second["is_duplicate"] is True
    assert second["match_type"] == "canonical_url"
    assert seen["seen"] is True
    assert candidates["count"] == 1
    assert search["count"] == 1


def test_source_run_record_tool(mcp_db: None) -> None:
    response = server.risk_source_run_record(
        {
            "source_id": "openai_news",
            "kind": "source",
            "status": "success",
            "items_found": 2,
            "items_new": 1,
            "items_duplicate": 1,
        }
    )

    assert response["ok"] is True
    assert response["source_run"]["items_duplicate"] == 1


def test_signal_store_and_search_tools(mcp_db: None) -> None:
    stored = server.risk_signal_store(
        {
            "source_id": "openai_news",
            "title": "重要风险信号",
            "summary": "Hermes 已判断该事项值得保存。",
            "risk_domain": "frontier_model",
            "signal_type": "lab_update",
            "severity": 3,
            "confidence": 4,
            "evidence_url": "https://example.com/signal",
        }
    )
    found = server.risk_signal_search(source_id="openai_news", risk_domain="frontier_model")

    assert stored["ok"] is True
    assert stored["signal"]["title"] == "重要风险信号"
    assert found["ok"] is True
    assert len(found["signals"]) == 1


def test_digest_store_and_search_tools(mcp_db: None) -> None:
    stored = server.risk_digest_store(
        {
            "digest_date": "2026-05-04",
            "title": "每日风险简报",
            "body": "Hermes generated body.",
            "status": "draft",
        }
    )
    found = server.risk_digest_search(digest_date="2026-05-04")

    assert stored["ok"] is True
    assert stored["digest"]["title"] == "每日风险简报"
    assert found["ok"] is True
    assert len(found["digests"]) == 1
