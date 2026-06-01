"""OpenAI implementation of the LLMProvider protocol."""

from __future__ import annotations

from typing import Optional

import openai
from openai import OpenAI

from src.config.settings import settings
from src.llm.base import ProviderConnectionError, ProviderError, ProviderRateLimitError


class OpenAIProvider:
    """LLMProvider backed by the OpenAI Chat Completions API."""

    name = "openai"

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._client = OpenAI(api_key=api_key or settings.openai_api_key)

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
            response = self._client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                response_format={"type": "json_object"},
                **kwargs,
            )
            return response.choices[0].message.content
        except openai.RateLimitError as exc:
            raise ProviderRateLimitError(str(exc)) from exc
        except openai.APIConnectionError as exc:
            raise ProviderConnectionError(str(exc)) from exc
        except Exception as exc:  # noqa: BLE001 - normalise any other vendor error
            raise ProviderError(str(exc)) from exc
