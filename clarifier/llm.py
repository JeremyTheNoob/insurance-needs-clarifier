from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from openai import OpenAI

from .config import Settings


class ChatClient(Protocol):
    def complete(
        self,
        messages: Sequence[dict[str, str]],
        temperature: float = 0.7,
    ) -> str: ...


class OpenAIChatClient:
    def __init__(self, settings: Settings):
        self._model = settings.model
        kwargs = {
            "api_key": settings.api_key,
            "timeout": settings.timeout,
            "max_retries": 2,
        }
        if settings.base_url:
            kwargs["base_url"] = settings.base_url
        self._client = OpenAI(**kwargs)

    def complete(
        self,
        messages: Sequence[dict[str, str]],
        temperature: float = 0.7,
    ) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=list(messages),
            temperature=temperature,
        )
        content = response.choices[0].message.content
        if not content or not content.strip():
            raise RuntimeError("模型返回了空内容，请重试。")
        return content.strip()
