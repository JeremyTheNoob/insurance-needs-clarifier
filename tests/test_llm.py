from __future__ import annotations

from types import SimpleNamespace

import pytest

from clarifier.config import Settings
from clarifier.llm import OpenAIChatClient


class FakeOpenAI:
    init_kwargs: dict = {}
    create_kwargs: dict = {}
    next_content: str = "ok"

    def __init__(self, **kwargs):
        type(self).init_kwargs = kwargs
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create)
        )

    def _create(self, **kwargs):
        type(self).create_kwargs = kwargs
        message = SimpleNamespace(content=type(self).next_content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _settings(base_url: str | None = "https://api.deepseek.com") -> Settings:
    return Settings(api_key="sk-test", base_url=base_url, model="deepseek-chat")


def test_complete_passes_model_messages_and_temperature(monkeypatch):
    FakeOpenAI.create_kwargs = {}
    FakeOpenAI.next_content = "ok"
    monkeypatch.setattr("clarifier.llm.OpenAI", FakeOpenAI)
    client = OpenAIChatClient(_settings())
    messages = [{"role": "user", "content": "你好"}]

    result = client.complete(messages, temperature=0.4)

    assert result == "ok"
    assert FakeOpenAI.create_kwargs["model"] == "deepseek-chat"
    assert FakeOpenAI.create_kwargs["messages"] == messages
    assert FakeOpenAI.create_kwargs["temperature"] == 0.4


def test_base_url_is_passed_when_configured(monkeypatch):
    FakeOpenAI.init_kwargs = {}
    monkeypatch.setattr("clarifier.llm.OpenAI", FakeOpenAI)

    OpenAIChatClient(_settings())

    assert FakeOpenAI.init_kwargs["base_url"] == "https://api.deepseek.com"
    assert FakeOpenAI.init_kwargs["api_key"] == "sk-test"
    assert FakeOpenAI.init_kwargs["timeout"] == 120.0
    assert FakeOpenAI.init_kwargs["max_retries"] == 2


def test_base_url_is_omitted_when_not_configured(monkeypatch):
    FakeOpenAI.init_kwargs = {}
    monkeypatch.setattr("clarifier.llm.OpenAI", FakeOpenAI)

    OpenAIChatClient(_settings(base_url=None))

    assert "base_url" not in FakeOpenAI.init_kwargs


def test_empty_content_raises(monkeypatch):
    FakeOpenAI.next_content = "   "
    monkeypatch.setattr("clarifier.llm.OpenAI", FakeOpenAI)
    client = OpenAIChatClient(_settings())

    with pytest.raises(RuntimeError, match="空内容"):
        client.complete([{"role": "user", "content": "你好"}])
