from __future__ import annotations

import pytest

from clarifier.config import ConfigError, Settings


def test_reads_required_and_optional_values(monkeypatch):
    monkeypatch.setattr("clarifier.config.load_dotenv", lambda: None)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_MODEL", "deepseek-chat")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.deepseek.com")

    settings = Settings.from_env()

    assert settings.api_key == "sk-test"
    assert settings.model == "deepseek-chat"
    assert settings.base_url == "https://api.deepseek.com"


def test_base_url_is_optional(monkeypatch):
    monkeypatch.setattr("clarifier.config.load_dotenv", lambda: None)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_MODEL", "deepseek-chat")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    settings = Settings.from_env()

    assert settings.base_url is None


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.setattr("clarifier.config.load_dotenv", lambda: None)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_MODEL", "deepseek-chat")

    with pytest.raises(ConfigError, match="OPENAI_API_KEY"):
        Settings.from_env()


def test_missing_model_raises(monkeypatch):
    monkeypatch.setattr("clarifier.config.load_dotenv", lambda: None)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    with pytest.raises(ConfigError, match="OPENAI_MODEL"):
        Settings.from_env()


def test_placeholder_api_key_raises(monkeypatch):
    monkeypatch.setattr("clarifier.config.load_dotenv", lambda: None)
    monkeypatch.setenv("OPENAI_API_KEY", "your-key-here")
    monkeypatch.setenv("OPENAI_MODEL", "deepseek-chat")

    with pytest.raises(ConfigError, match="占位"):
        Settings.from_env()
