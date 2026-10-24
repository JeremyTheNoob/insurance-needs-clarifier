from __future__ import annotations

import app
from clarifier.config import ConfigError, Settings


def test_main_returns_1_when_config_invalid(monkeypatch, capsys):
    def fail():
        raise ConfigError("缺少 OPENAI_API_KEY")

    monkeypatch.setattr(
        app.Settings, "from_env", classmethod(lambda cls: fail())
    )

    assert app.main() == 1
    captured = capsys.readouterr()
    assert "启动失败" in captured.err
    assert "OPENAI_API_KEY" in captured.err


def test_main_starts_repl(monkeypatch):
    settings = Settings(api_key="sk", base_url=None, model="m")
    called = {}

    monkeypatch.setattr(
        app.Settings, "from_env", classmethod(lambda cls: settings)
    )
    monkeypatch.setattr(
        app.PromptLibrary, "load", classmethod(lambda cls: object())
    )
    monkeypatch.setattr(app, "OpenAIChatClient", lambda s: object())
    monkeypatch.setattr(
        app, "InterviewSession", lambda **kwargs: object()
    )

    def fake_run_repl(session):
        called["session"] = session

    monkeypatch.setattr(app, "run_repl", fake_run_repl)

    assert app.main() == 0
    assert "session" in called
