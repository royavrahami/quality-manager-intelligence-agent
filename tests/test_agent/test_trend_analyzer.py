"""
Unit tests for the pure trend-analysis helpers.

Covers the deduplication logic (text normalisation, Jaccard similarity, and
semantic dedup) and momentum scoring — the deterministic core of the trend
analyzer that does not require an LLM call.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.agent.trend_analyzer import TrendAnalyzer, _SIMILARITY_THRESHOLD
from src.storage.models import Trend


def _analyzer() -> TrendAnalyzer:
    # Repos are unused by the pure helpers; OpenAI client is created but never called.
    return TrendAnalyzer(article_repo=None, trend_repo=None, api_key="test-key")


# ── _jaccard_similarity ──────────────────────────────────────────────────────

def test_jaccard_identical_sets_is_one():
    s = {"agile", "scrum", "kanban"}
    assert TrendAnalyzer._jaccard_similarity(s, set(s)) == 1.0


def test_jaccard_disjoint_sets_is_zero():
    assert TrendAnalyzer._jaccard_similarity({"a", "b"}, {"c", "d"}) == 0.0


def test_jaccard_empty_set_is_zero():
    assert TrendAnalyzer._jaccard_similarity(set(), {"a"}) == 0.0
    assert TrendAnalyzer._jaccard_similarity({"a"}, set()) == 0.0


def test_jaccard_partial_overlap():
    # {a,b} & {b,c} = {b} (1), union = {a,b,c} (3) -> 1/3
    assert TrendAnalyzer._jaccard_similarity({"a", "b"}, {"b", "c"}) == 1 / 3


# ── _normalize_text ──────────────────────────────────────────────────────────

def test_normalize_lowercases_and_drops_stopwords():
    words = TrendAnalyzer._normalize_text("The NEW Rise of Agile Testing")
    # stop words ("the", "new", "rise", "of") are removed; meaningful words kept.
    assert "agile" in words
    assert "testing" in words
    assert "the" not in words
    assert "new" not in words


def test_normalize_drops_short_tokens_and_symbols():
    words = TrendAnalyzer._normalize_text("AI/ML in QA — go!")
    # only \b[a-z]{3,}\b tokens survive; 2-letter "ai"/"ml"/"qa"/"go" dropped.
    assert words == set()


# ── _calculate_momentum ──────────────────────────────────────────────────────

def test_momentum_without_first_seen_returns_article_count():
    t = Trend(name="X", category="agile", article_count=5)
    assert TrendAnalyzer._calculate_momentum(t) == 5.0


def test_momentum_is_capped_at_100():
    t = Trend(
        name="Y",
        category="agile",
        article_count=10_000,
        first_seen_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    assert TrendAnalyzer._calculate_momentum(t) == 100.0


def test_momentum_reasonable_value():
    # ~7 articles over ~7 days -> (7/7)*10 = 10.0
    t = Trend(
        name="Z",
        category="agile",
        article_count=7,
        first_seen_at=datetime.now(timezone.utc) - timedelta(days=7),
    )
    score = TrendAnalyzer._calculate_momentum(t)
    assert 8.0 <= score <= 12.0


# ── _deduplicate_trends ──────────────────────────────────────────────────────

def test_dedup_removes_semantically_similar_trends():
    analyzer = _analyzer()
    data = [
        {"name": "Agile Testing Practices"},
        {"name": "Agile Testing Practices Evolving"},  # highly similar -> dropped
        {"name": "Kubernetes Security Hardening"},      # distinct -> kept
    ]
    result = analyzer._deduplicate_trends(data)
    names = [t["name"] for t in result]
    assert "Agile Testing Practices" in names
    assert "Kubernetes Security Hardening" in names
    assert len(result) == 2


def test_dedup_keeps_distinct_trends():
    analyzer = _analyzer()
    data = [
        {"name": "Observability in Microservices"},
        {"name": "Contract Testing Adoption"},
        {"name": "Chaos Engineering Maturity"},
    ]
    result = analyzer._deduplicate_trends(data)
    assert len(result) == 3


def test_dedup_skips_blank_names_and_empty_list():
    analyzer = _analyzer()
    assert analyzer._deduplicate_trends([]) == []
    assert analyzer._deduplicate_trends([{"name": "   "}, {"foo": "bar"}]) == []


def test_similarity_threshold_is_sane():
    assert 0.0 < _SIMILARITY_THRESHOLD < 1.0
