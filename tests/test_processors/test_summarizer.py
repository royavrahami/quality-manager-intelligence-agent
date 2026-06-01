"""
Unit tests for the Summarizer – verifies response parsing, error handling and
output structure without real API calls, using an injected fake LLM provider.
"""

from __future__ import annotations

import json
from typing import Optional

import pytest

from src.llm.base import ProviderError, ProviderRateLimitError
from src.processors.summarizer import Summarizer


class FakeProvider:
    """In-memory LLMProvider stub: returns canned content or raises an error."""

    name = "fake"

    def __init__(self, content: Optional[str] = None, error: Optional[Exception] = None) -> None:
        self._content = content
        self._error = error
        self.last_user: Optional[str] = None

    def chat_json(self, system, user, *, model, max_tokens, temperature=0.3, timeout=None) -> str:
        self.last_user = user
        if self._error is not None:
            raise self._error
        return self._content


@pytest.fixture
def valid_api_response() -> dict:
    return {
        "summary": "A three-sentence summary of the article content.",
        "key_insights": [
            "LLMs can autonomously generate test cases",
            "Self-healing locators reduce maintenance by 40%",
            "Integration with CI/CD is now plug-and-play",
        ],
        "qa_relevance": "Directly useful for QA managers building AI-assisted pipelines.",
    }


def _summarizer(content=None, error=None) -> tuple[Summarizer, FakeProvider]:
    provider = FakeProvider(content=content, error=error)
    return Summarizer(provider=provider), provider


class TestSummarizerHappyPath:
    def test_returns_dict_with_required_keys(self, valid_api_response):
        summarizer, _ = _summarizer(content=json.dumps(valid_api_response))
        result = summarizer.summarise(
            title="Test Article",
            content="Some content",
            source_name="Test Feed",
            category="qa_testing",
            url="https://example.com",
        )
        assert result is not None
        assert {"summary", "key_insights", "qa_relevance"} <= set(result)

    def test_key_insights_is_list(self, valid_api_response):
        summarizer, _ = _summarizer(content=json.dumps(valid_api_response))
        result = summarizer.summarise("T", "C", "S", "genai", "https://x.com")
        assert isinstance(result["key_insights"], list)
        assert len(result["key_insights"]) == 3

    def test_content_truncated_before_sending(self, valid_api_response):
        summarizer, provider = _summarizer(content=json.dumps(valid_api_response))
        summarizer.summarise("T", "X" * 10_000, "S", "genai", "https://x.com")
        # The user prompt sent to the provider must not carry the full 10k chars.
        assert provider.last_user.count("X") <= 4000


class TestSummarizerErrorHandling:
    def test_returns_none_on_rate_limit_and_sets_quota_flag(self):
        summarizer, _ = _summarizer(error=ProviderRateLimitError("rate limit"))
        result = summarizer.summarise("T", "C", "S", "genai", "https://x.com")
        assert result is None
        assert summarizer.quota_warning is True

    def test_returns_none_on_provider_error(self):
        summarizer, _ = _summarizer(error=ProviderError("network"))
        assert summarizer.summarise("T", "C", "S", "genai", "https://x.com") is None

    def test_returns_none_on_unexpected_error(self):
        summarizer, _ = _summarizer(error=RuntimeError("boom"))
        assert summarizer.summarise("T", "C", "S", "genai", "https://x.com") is None

    def test_returns_none_on_invalid_json(self):
        summarizer, _ = _summarizer(content="this is not JSON")
        assert summarizer.summarise("T", "C", "S", "genai", "https://x.com") is None

    def test_returns_none_on_missing_required_keys(self):
        summarizer, _ = _summarizer(content=json.dumps({"only_one_key": "value"}))
        assert summarizer.summarise("T", "C", "S", "genai", "https://x.com") is None

    def test_non_list_key_insights_coerced_to_list(self):
        summarizer, _ = _summarizer(content=json.dumps({
            "summary": "Summary text.",
            "key_insights": "Just one insight as a string",
            "qa_relevance": "Relevant.",
        }))
        result = summarizer.summarise("T", "C", "S", "genai", "https://x.com")
        assert result is not None
        assert isinstance(result["key_insights"], list)
