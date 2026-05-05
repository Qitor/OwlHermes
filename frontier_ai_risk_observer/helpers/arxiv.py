"""arXiv API query helper.

Builds deterministic query URLs and parses Atom XML responses.
Does NOT fetch from the network by default, score papers,
store items automatically, or call LLMs.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import urlencode

from frontier_ai_risk_observer.helpers.models import CandidateItem

ARXIV_API_BASE = "https://export.arxiv.org/api/query"


def build_query_url(query: str, max_results: int = 20, sort_by: str = "submittedDate") -> str:
    """Build a deterministic arXiv API query URL."""
    params = {
        "search_query": query,
        "start": 0,
        "max_results": max_results,
        "sortBy": sort_by,
        "sortOrder": "descending",
    }
    return f"{ARXIV_API_BASE}?{urlencode(params)}"


def parse_arxiv_atom(
    atom_content: str,
    source_id: str = "arxiv_ai_safety",
    limit: int = 20,
) -> list[CandidateItem]:
    """Parse arXiv Atom XML response into candidate items.

    This is the offline-testable function. It does NOT fetch from the network.
    """
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }

    root = ET.fromstring(atom_content)
    candidates: list[CandidateItem] = []

    for entry in root.findall("atom:entry", ns):
        title_el = entry.find("atom:title", ns)
        title = (title_el.text or "").strip().replace("\n", " ") if title_el is not None else ""

        url = None
        for link_el in entry.findall("atom:link", ns):
            if link_el.get("type") == "text/html":
                url = link_el.get("href")
                break
        if not url:
            id_el = entry.find("atom:id", ns)
            url = id_el.text.strip() if id_el is not None else None
        if not url:
            continue

        published_at = None
        published_el = entry.find("atom:published", ns)
        if published_el is not None and published_el.text:
            try:
                published_at = datetime.fromisoformat(published_el.text.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        summary_el = entry.find("atom:summary", ns)
        summary = (summary_el.text or "").strip() if summary_el is not None else None

        candidates.append(CandidateItem(
            source_id=source_id,
            kind="arxiv_paper",
            title=title,
            url=url,
            published_at=published_at,
            summary=summary,
            source_url=ARXIV_API_BASE,
            discovery_method="arxiv_query",
        ))

        if len(candidates) >= limit:
            break

    return candidates


def fetch_and_parse(
    query: str,
    source_id: str = "arxiv_ai_safety",
    max_results: int = 20,
    timeout: float = 30.0,
) -> list[CandidateItem]:
    """Query arXiv API and parse results.

    This function DOES fetch from the network. Do not call in default tests.
    Requires explicit ALLOW_NETWORK=1 or --fetch flag.
    """
    import httpx

    url = build_query_url(query, max_results)
    response = httpx.get(url, timeout=timeout)
    response.raise_for_status()
    return parse_arxiv_atom(
        atom_content=response.text,
        source_id=source_id,
        limit=max_results,
    )
