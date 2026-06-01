"""Tests for the Arxiv collector (network mocked — no real HTTP)."""

from __future__ import annotations

from types import SimpleNamespace

from src.collectors.arxiv_collector import ArxivCollector
from src.storage.repository import ArticleRepository, SourceRepository

_ATOM_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>A Study of LLM-based Test Generation</title>
    <id>http://arxiv.org/abs/2601.00001v1</id>
    <link href="http://arxiv.org/abs/2601.00001v1" rel="alternate" type="text/html"/>
    <summary>We study autonomous test generation with large language models.</summary>
    <author><name>Alice Researcher</name></author>
    <author><name>Bob Scientist</name></author>
    <published>2026-05-01T00:00:00Z</published>
  </entry>
</feed>
"""


class _FakeResponse:
    content = _ATOM_FEED

    def raise_for_status(self):
        return None


def _collector(db_session) -> ArxivCollector:
    return ArxivCollector(
        source_repo=SourceRepository(db_session),
        article_repo=ArticleRepository(db_session),
    )


def test_collect_all_persists_parsed_papers(db_session, monkeypatch):
    monkeypatch.setattr("src.collectors.arxiv_collector.requests.get", lambda *a, **k: _FakeResponse())
    monkeypatch.setattr("src.collectors.arxiv_collector.time.sleep", lambda *_a, **_k: None)

    collector = _collector(db_session)
    new_count = collector.collect_all()

    assert new_count >= 1
    # The parsed paper was stored as an Article.
    repo = ArticleRepository(db_session)
    assert repo.exists("http://arxiv.org/abs/2601.00001v1")


def test_collect_all_is_idempotent_on_duplicate_urls(db_session, monkeypatch):
    monkeypatch.setattr("src.collectors.arxiv_collector.requests.get", lambda *a, **k: _FakeResponse())
    monkeypatch.setattr("src.collectors.arxiv_collector.time.sleep", lambda *_a, **_k: None)

    collector = _collector(db_session)
    collector.collect_all()
    second = collector.collect_all()  # same URLs -> nothing new

    assert second == 0


# ── static parse helpers ─────────────────────────────────────────────────────

def test_extract_authors_truncates_after_five():
    entry = SimpleNamespace(authors=[{"name": f"A{i}"} for i in range(7)])
    result = ArxivCollector._extract_authors(entry)
    assert result.endswith("...")
    assert result.count(",") == 4  # 5 names shown


def test_extract_authors_empty():
    assert ArxivCollector._extract_authors(SimpleNamespace(authors=[])) == ""


def test_get_abs_url_prefers_html_link():
    entry = SimpleNamespace(
        links=[
            {"type": "application/pdf", "href": "http://x/pdf"},
            {"type": "text/html", "href": "http://x/abs"},
        ],
        link="http://fallback",
    )
    assert ArxivCollector._get_abs_url(entry) == "http://x/abs"


def test_get_abs_url_falls_back_to_link():
    entry = SimpleNamespace(links=[], link="http://fallback")
    assert ArxivCollector._get_abs_url(entry) == "http://fallback"


def test_parse_date_handles_missing():
    assert ArxivCollector._parse_date(SimpleNamespace(published_parsed=None)) is None


def test_parse_date_parses_struct_time():
    entry = SimpleNamespace(published_parsed=(2026, 5, 1, 12, 0, 0, 0, 0, 0))
    parsed = ArxivCollector._parse_date(entry)
    assert parsed is not None
    assert parsed.year == 2026 and parsed.month == 5
