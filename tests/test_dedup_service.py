from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from frontier_ai_risk_observer.api.schemas import RawItemCreate
from frontier_ai_risk_observer.db.models import Base, RawItem, Source, SourceRun
from frontier_ai_risk_observer.services.dedup import (
    canonicalize_url,
    compute_content_hash,
    normalize_title,
)
from frontier_ai_risk_observer.services.ingestion import (
    create_raw_item,
    list_duplicate_candidates,
    seen_raw_item,
)


@pytest.fixture
def session() -> Iterator[Session]:
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
    with session_factory() as db_session:
        yield db_session


def test_canonicalize_url_removes_tracking_params_and_fragment() -> None:
    url = "HTTPS://Example.COM/path/?utm_source=x&keep=1&fbclid=y#section"

    assert canonicalize_url(url) == "https://example.com/path?keep=1"


def test_canonicalize_url_preserves_meaningful_query_params() -> None:
    url = "https://example.com/search?q=evals&sort=new&utm_medium=email"

    assert canonicalize_url(url) == "https://example.com/search?q=evals&sort=new"


def test_content_hash_and_title_normalization_are_deterministic() -> None:
    assert compute_content_hash("Some\n evidence   text") == compute_content_hash(
        "Some evidence text"
    )
    assert normalize_title("  Frontier   MODEL Update ") == "frontier model update"


def test_same_url_with_tracking_params_dedups(session: Session) -> None:
    first = create_raw_item(
        session,
        RawItemCreate(
            source_id="openai_news",
            kind="web_article",
            url="https://example.com/item?utm_source=test",
            title="A useful raw item",
        ),
    )
    first_last_seen = first.item.last_seen_at

    second = create_raw_item(
        session,
        RawItemCreate(
            source_id="openai_news",
            kind="web_article",
            url="https://example.com/item?utm_campaign=launch",
            title="A useful raw item",
        ),
    )

    assert first.is_duplicate is False
    assert second.is_duplicate is True
    assert second.match_type == "canonical_url"
    assert second.item.id == first.item.id
    assert second.item.seen_count == 2
    assert second.item.last_seen_at >= first_last_seen


def test_same_content_hash_dedups(session: Session) -> None:
    first = create_raw_item(
        session,
        RawItemCreate(
            source_id="openai_news",
            kind="web_article",
            url="https://example.com/one",
            title="First title",
            content_hash="same-hash",
        ),
    )
    second = create_raw_item(
        session,
        RawItemCreate(
            source_id="openai_news",
            kind="web_article",
            url="https://example.com/two",
            title="Different title",
            content_hash="same-hash",
        ),
    )

    assert first.is_duplicate is False
    assert second.is_duplicate is True
    assert second.match_type == "content_hash"


def test_same_source_and_normalized_title_dedups(session: Session) -> None:
    create_raw_item(
        session,
        RawItemCreate(source_id="openai_news", kind="web_article", title=" Frontier  Update "),
    )

    second = create_raw_item(
        session,
        RawItemCreate(source_id="openai_news", kind="web_article", title="frontier update"),
    )

    assert second.is_duplicate is True
    assert second.match_type == "source_title"


def test_seen_check_and_duplicate_candidates_include_match_metadata(
    session: Session,
) -> None:
    stored = create_raw_item(
        session,
        RawItemCreate(
            source_id="openai_news",
            kind="web_article",
            url="https://example.com/memory",
            title="Memory item",
        ),
    )

    match = seen_raw_item(session, url="https://example.com/memory?gclid=abc")
    candidates = list_duplicate_candidates(
        session,
        url="https://example.com/memory?utm_content=abc",
        limit=10,
    )

    assert match is not None
    assert match.match_type == "canonical_url"
    assert match.item.id == stored.item.id
    assert match.dedup_key == "url:https://example.com/memory"
    assert len(candidates) == 1
    assert candidates[0].item.id == stored.item.id
