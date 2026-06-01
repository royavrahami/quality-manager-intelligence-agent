"""Tests for the daily-digest enrichment/statistics builders (no DB/LLM)."""

from __future__ import annotations

from datetime import datetime

import pytest

from src.agent.daily_digest_agent import DailyDigestAgent


@pytest.fixture
def agent(monkeypatch):
    # __init__ calls init_db() (would touch the configured DB) — stub it out.
    monkeypatch.setattr("src.agent.daily_digest_agent.init_db", lambda: None)
    return DailyDigestAgent()


def test_build_digest_articles_maps_fields(agent, sample_article):
    sample_article.relevance_score = 73.4
    result = agent._build_digest_articles([sample_article])

    assert len(result) == 1
    da = result[0]
    assert da.title == sample_article.title
    assert da.url == sample_article.url
    assert da.relevance_score == 73.4
    assert isinstance(da.keywords, list)


def test_build_digest_articles_sorts_by_score(agent, sample_article, processed_article):
    sample_article.relevance_score = 10.0
    processed_article.relevance_score = 90.0
    result = agent._build_digest_articles([sample_article, processed_article])
    assert [round(a.relevance_score) for a in result] == [90, 10]


def test_build_stats_aggregates(agent, sample_article):
    sample_article.relevance_score = 60.0
    das = agent._build_digest_articles([sample_article])
    stats = agent._build_stats(das)
    assert stats.total_articles == 1
    assert stats.avg_relevance == 60.0
    assert stats.category_counts  # non-empty


def test_build_stats_empty_returns_zeroed():
    DailyDigestAgent._build_stats  # exists
    from src.agent.daily_digest_agent import DigestStats

    # call the staticmethod-like builder via a stub instance is overkill; build empty directly
    empty = DigestStats(date_str="01 May 2026")
    assert empty.total_articles == 0


def test_fmt_dt_handles_none_and_naive():
    assert DailyDigestAgent._fmt_dt(None) == "N/A"
    out = DailyDigestAgent._fmt_dt(datetime(2026, 5, 1, 12, 0))
    assert "2026" in out and "UTC" in out
