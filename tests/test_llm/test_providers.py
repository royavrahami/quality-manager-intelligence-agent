"""Tests for the LLM provider abstraction (factory + OpenAI error translation)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.llm import ProviderError, ProviderRateLimitError, get_provider


def _patch_openai(monkeypatch, *, response=None, error=None):
    mock_client = MagicMock()
    if error is not None:
        mock_client.chat.completions.create.side_effect = error
    else:
        mock_client.chat.completions.create.return_value = response
    monkeypatch.setattr("src.llm.openai_provider.OpenAI", lambda **_kw: mock_client)
    return mock_client


# ── Factory ──────────────────────────────────────────────────────────────────

def test_factory_returns_openai_provider():
    from src.llm.openai_provider import OpenAIProvider

    assert isinstance(get_provider("openai"), OpenAIProvider)


def test_factory_unknown_provider_raises():
    with pytest.raises(ValueError):
        get_provider("does-not-exist")


def test_factory_anthropic_without_package_raises():
    try:
        import anthropic  # noqa: F401
    except ImportError:
        with pytest.raises(ProviderError):
            get_provider("anthropic")
    else:
        pytest.skip("anthropic is installed; the missing-package path is not exercised")


# ── OpenAI provider error translation ────────────────────────────────────────

def test_openai_provider_returns_content(monkeypatch):
    resp = MagicMock()
    resp.choices[0].message.content = '{"ok": true}'
    _patch_openai(monkeypatch, response=resp)

    from src.llm.openai_provider import OpenAIProvider

    out = OpenAIProvider(api_key="x").chat_json("sys", "user", model="gpt-4o", max_tokens=10)
    assert out == '{"ok": true}'


def test_openai_provider_translates_rate_limit(monkeypatch):
    import openai

    err = openai.RateLimitError(message="rl", response=MagicMock(status_code=429), body={})
    _patch_openai(monkeypatch, error=err)

    from src.llm.openai_provider import OpenAIProvider

    with pytest.raises(ProviderRateLimitError):
        OpenAIProvider(api_key="x").chat_json("s", "u", model="gpt-4o", max_tokens=10)


def test_openai_provider_translates_generic_error(monkeypatch):
    _patch_openai(monkeypatch, error=ValueError("boom"))

    from src.llm.openai_provider import OpenAIProvider

    with pytest.raises(ProviderError):
        OpenAIProvider(api_key="x").chat_json("s", "u", model="m", max_tokens=10)


def test_openai_provider_passes_timeout(monkeypatch):
    resp = MagicMock()
    resp.choices[0].message.content = "{}"
    client = _patch_openai(monkeypatch, response=resp)

    from src.llm.openai_provider import OpenAIProvider

    OpenAIProvider(api_key="x").chat_json("s", "u", model="m", max_tokens=10, timeout=60)
    assert client.chat.completions.create.call_args.kwargs["timeout"] == 60
