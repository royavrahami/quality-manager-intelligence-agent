"""Tests for the GitHub collector (HTTP mocked — no real network)."""

from __future__ import annotations

from src.collectors.github_collector import GitHubCollector
from src.storage.models import Source
from src.storage.repository import ArticleRepository, SourceRepository

_TRENDING_HTML = """
<html><body>
  <article class="Box-row">
    <h2><a href="/owner/cool-tester">owner / cool-tester</a></h2>
    <p>An AI-powered test generation tool</p>
    <a href="/owner/cool-tester/stargazers">1,234</a>
    <span itemprop="programmingLanguage">Python</span>
  </article>
  <article class="Box-row">
    <h2><a href="/acme/agentkit">acme / agentkit</a></h2>
    <p>Agent framework</p>
  </article>
</body></html>
"""

_API_JSON = {
    "items": [
        {
            "html_url": "https://github.com/foo/llm-qa",
            "full_name": "foo/llm-qa",
            "topics": ["testing", "llm"],
            "stargazers_count": 4200,
            "language": "Python",
            "description": "LLM-assisted QA",
        }
    ]
}


class _HtmlResponse:
    text = _TRENDING_HTML

    def raise_for_status(self):
        return None


class _JsonResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return _API_JSON


def _collector(db_session) -> GitHubCollector:
    return GitHubCollector(
        source_repo=SourceRepository(db_session),
        article_repo=ArticleRepository(db_session),
        github_token=None,
    )


def _persist_source(db_session, source_type: str) -> Source:
    src = Source(
        name="GH",
        url="https://github.com/trending",
        source_type=source_type,
        category="tools",
    )
    db_session.add(src)
    db_session.flush()
    return src


def test_scrape_trending_parses_and_saves_repos(db_session, monkeypatch):
    monkeypatch.setattr(
        "src.collectors.github_collector.requests.get", lambda *a, **k: _HtmlResponse()
    )
    source = _persist_source(db_session, "github_trending")
    collector = _collector(db_session)

    new_count = collector._scrape_trending(source)

    assert new_count >= 1
    assert ArticleRepository(db_session).exists("https://github.com/owner/cool-tester")


def test_search_topic_parses_api_json(db_session, monkeypatch):
    monkeypatch.setattr(
        "src.collectors.github_collector.requests.get", lambda *a, **k: _JsonResponse()
    )
    source = _persist_source(db_session, "github_api")
    collector = _collector(db_session)

    new_count = collector._search_topic(source, "testing")

    assert new_count == 1
    assert ArticleRepository(db_session).exists("https://github.com/foo/llm-qa")


def test_search_topic_skips_existing(db_session, monkeypatch):
    monkeypatch.setattr(
        "src.collectors.github_collector.requests.get", lambda *a, **k: _JsonResponse()
    )
    source = _persist_source(db_session, "github_api")
    collector = _collector(db_session)

    collector._search_topic(source, "testing")
    second = collector._search_topic(source, "testing")  # already stored

    assert second == 0


def test_collector_sets_auth_header_when_token_present(db_session):
    collector = GitHubCollector(
        SourceRepository(db_session), ArticleRepository(db_session), github_token="ghp_x"
    )
    assert collector._headers["Authorization"] == "Bearer ghp_x"
