from __future__ import annotations

import sys

from clarifier.cli import run_repl
from clarifier.config import ConfigError, Settings
from clarifier.llm import OpenAIChatClient
from clarifier.prompts import PromptError, PromptLibrary
from clarifier.session import InterviewSession


def main() -> int:
    try:
        settings = Settings.from_env()
        prompts = PromptLibrary.load()
    except (ConfigError, PromptError) as exc:
        print(f"启动失败：{exc}", file=sys.stderr)
        return 1

    client = OpenAIChatClient(settings)
    session = InterviewSession(client=client, prompts=prompts)
    run_repl(session)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
