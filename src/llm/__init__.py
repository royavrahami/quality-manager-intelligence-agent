"""LLM provider abstraction.

Use ``get_provider()`` to obtain the configured chat-completion provider; depend
on the ``LLMProvider`` protocol and the normalised error types, not on a vendor
SDK directly.
"""

from __future__ import annotations

from typing import Optional

from src.config.settings import settings
from src.llm.base import (
    LLMProvider,
    ProviderConnectionError,
    ProviderError,
    ProviderRateLimitError,
)

__all__ = [
    "LLMProvider",
    "ProviderError",
    "ProviderRateLimitError",
    "ProviderConnectionError",
    "get_provider",
]


def get_provider(name: Optional[str] = None, api_key: Optional[str] = None) -> LLMProvider:
    """Return an LLMProvider for the configured (or requested) vendor.

    Args:
        name:    Provider name ("openai" | "anthropic"). Defaults to
                 settings.llm_provider.
        api_key: Override the provider API key.
    """
    provider_name = (name or settings.llm_provider).lower()

    if provider_name == "openai":
        from src.llm.openai_provider import OpenAIProvider

        return OpenAIProvider(api_key)

    if provider_name == "anthropic":
        from src.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider(api_key)

    raise ValueError(
        f"Unknown LLM provider '{provider_name}'. Supported: openai, anthropic."
    )
