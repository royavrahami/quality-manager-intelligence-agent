"""Anthropic (Claude) implementation of the LLMProvider protocol.

The ``anthropic`` package is imported lazily so it is only required when this
provider is actually selected (LLM_PROVIDER=anthropic). Anthropic has no native
JSON-object response mode, so JSON is requested via the system prompt; the
caller already validates/parses the returned content.
"""

from __future__ import annotations

from typing import Optional

from src.config.settings import settings
from src.llm.base import ProviderConnectionError, ProviderError, ProviderRateLimitError

_JSON_GUARD = "\n\nRespond with a single valid JSON object and nothing else."


class AnthropicProvider:
    """LLMProvider backed by the Anthropic Messages API."""

    name = "anthropic"

    def __init__(self, api_key: Optional[str] = None) -> None:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - exercised only without the dep
            raise ProviderError(
                "The 'anthropic' package is required for the Anthropic provider. "
                "Install it with: pip install anthropic"
            ) from exc
        self._anthropic = anthropic
        self._client = anthropic.Anthropic(api_key=api_key or settings.anthropic_api_key)

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
        kwargs = {"timeout": timeout} if timeout is not None else {}
        try:
            message = self._client.messages.create(
                model=model,
                system=system + _JSON_GUARD,
                messages=[{"role": "user", "content": user}],
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs,
            )
            return message.content[0].text
        except self._anthropic.RateLimitError as exc:
            raise ProviderRateLimitError(str(exc)) from exc
        except self._anthropic.APIConnectionError as exc:
            raise ProviderConnectionError(str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(str(exc)) from exc
