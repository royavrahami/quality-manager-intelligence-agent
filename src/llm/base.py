"""LLM provider interface and normalised error types.

Decouples the agent from any single vendor SDK: callers depend on the small
``LLMProvider`` protocol and the normalised exceptions below, not on
``openai``/``anthropic`` directly. Swapping or adding a provider is a matter of
implementing this protocol (see openai_provider.py / anthropic_provider.py).
"""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable


class ProviderError(Exception):
    """Base class for all LLM provider errors."""


class ProviderRateLimitError(ProviderError):
    """The provider reported a rate-limit / quota error."""


class ProviderConnectionError(ProviderError):
    """The provider could not be reached."""


@runtime_checkable
class LLMProvider(Protocol):
    """Minimal interface for a chat-completion LLM provider."""

    name: str

    def chat_json(
        self,
        system: str,
        user: str,
        *,
        model: str,
        max_tokens: int,
        temperature: float = 0.3,
        timeout: Optional[int] = None,
    ) -> str:
        """Run a single chat completion and return the raw response content.

        Implementations should request a JSON-object response when the provider
        supports it, and must translate vendor errors into the normalised
        exceptions in this module:

          - quota / rate-limit -> ProviderRateLimitError
          - connectivity        -> ProviderConnectionError
          - anything else        -> ProviderError
        """
        ...
