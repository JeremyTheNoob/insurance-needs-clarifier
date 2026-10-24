from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class PromptError(RuntimeError):
    """Raised when a prompt file is missing or empty."""


@dataclass(frozen=True)
class PromptLibrary:
    system: str
    draft: str
    revise: str

    @classmethod
    def load(cls, base_dir: Path | None = None) -> "PromptLibrary":
        root = base_dir or Path(__file__).resolve().parent.parent
        prompt_dir = root / "prompts"
        try:
            system = (prompt_dir / "system.md").read_text(encoding="utf-8").strip()
            draft = (prompt_dir / "draft.md").read_text(encoding="utf-8").strip()
            revise = (prompt_dir / "revise.md").read_text(encoding="utf-8").strip()
        except FileNotFoundError as exc:
            raise PromptError(f"缺少提示词文件：{exc.filename}") from exc

        for name, text in (("system", system), ("draft", draft), ("revise", revise)):
            if not text:
                raise PromptError(f"提示词文件为空：{name}.md")
        return cls(system=system, draft=draft, revise=revise)
