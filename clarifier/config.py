from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str | None
    model: str
    timeout: float = 120.0

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        model = os.getenv("OPENAI_MODEL", "").strip()
        base_url = os.getenv("OPENAI_BASE_URL", "").strip() or None

        if not api_key:
            raise ConfigError(
                "缺少 OPENAI_API_KEY。复制 .env.example 为 .env，并填入你的 API Key。"
            )
        if api_key == "your-key-here":
            raise ConfigError(
                "OPENAI_API_KEY 仍是 .env.example 中的占位值。"
                "请在 .env 中填入真实密钥；不要再次执行 cp .env.example .env，"
                "否则会覆盖你填好的配置。"
            )
        if not model:
            raise ConfigError(
                "缺少 OPENAI_MODEL。请在 .env 中指定模型，例如 deepseek-chat 或 gpt-4o-mini。"
            )
        return cls(api_key=api_key, base_url=base_url, model=model)
