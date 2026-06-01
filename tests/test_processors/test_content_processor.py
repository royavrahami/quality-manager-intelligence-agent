"""Integration tests for the ContentProcessor (scoring pipeline, no LLM)."""

from __future__ import annotations

from src.processors.content_processor import ContentProcessor
from src.processors.relevance_scorer import RelevanceScorer
from src.storage.repository import ArticleRepository, SourceRepository


def _processor(db_session, min_score: float = 0.0) -> ContentProcessor:
    scorer = RelevanceScorer(
        high_keywords=["llm", "ai agent", "playwright"],
        medium_keywords=["testing", "automation"],
        low_keywords=["software"],
    )
    return ContentProcessor(
        article_repo=ArticleRepository(db_session),
        source_repo=SourceRepository(db_session),
        scorer=scorer,
        summarizer=None,  # no OpenAI in this test
        min_score=min_score,
    )


def test_process_pending_scores_and_marks_articles(db_session, sample_article):
    processor = _processor(db_session)

    scored, summarised, quota_warning = processor.process_pending()

    assert scored >= 1
    assert summarised == 0          # no summarizer configured
    assert quota_warning is False

    # process_pending mutates the ORM objects in-session (caller owns the commit),
    # so assert on the same instance rather than refreshing it from the DB.
    assert sample_article.is_processed is True
    assert sample_article.relevance_score is not None


def test_process_pending_with_no_unprocessed_articles(db_session):
    processor = _processor(db_session)
    assert processor.process_pending() == (0, 0, False)
