from __future__ import annotations

from dataclasses import dataclass, field

from .documents import DocumentPair, DraftParseError, parse_documents
from .llm import ChatClient
from .prompts import PromptLibrary

DRAFT_RETRY_MESSAGE = (
    "你上一次的输出缺少必要的分隔符。请严格使用以下格式重新输出，"
    "不要添加分隔符之外的任何文字：\n"
    "<<<NEEDS_STATEMENT>>>\n...\n"
    "<<<QUESTION_CARD>>>\n...\n"
    "<<<END>>>"
)


class SessionError(RuntimeError):
    """Raised for invalid session operations."""


@dataclass
class InterviewSession:
    client: ChatClient
    prompts: PromptLibrary
    messages: list[dict[str, str]] = field(default_factory=list)
    last_documents: DocumentPair | None = None
    calibrated: bool = False

    def __post_init__(self) -> None:
        if not self.messages:
            self.messages = [
                {"role": "system", "content": self.prompts.system}
            ]

    @property
    def has_user_messages(self) -> bool:
        return any(m["role"] == "user" for m in self.messages[1:])

    def reply(self, user_text: str) -> str:
        text = user_text.strip()
        if not text:
            raise SessionError("输入不能为空。")
        self.messages.append({"role": "user", "content": text})
        try:
            response = self.client.complete(
                self.messages, temperature=0.7
            ).strip()
        except (Exception, KeyboardInterrupt):
            self.messages.pop()
            raise
        if not response:
            self.messages.pop()
            raise SessionError("模型没有返回内容，请重试。")
        self.messages.append({"role": "assistant", "content": response})
        return response

    def _transcript(self) -> str:
        lines = []
        for message in self.messages[1:]:
            role = "用户" if message["role"] == "user" else "教练"
            lines.append(f"{role}：{message['content']}")
        return "\n\n".join(lines)

    def _draft_messages(self) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": self.prompts.draft},
            {
                "role": "user",
                "content": f"以下是完整访谈记录：\n\n{self._transcript()}",
            },
        ]

    def _generate(self, messages: list[dict[str, str]]) -> DocumentPair:
        raw = self.client.complete(messages, temperature=0.4)
        try:
            return parse_documents(raw)
        except DraftParseError:
            retry_messages = messages + [
                {"role": "assistant", "content": raw},
                {"role": "user", "content": DRAFT_RETRY_MESSAGE},
            ]
            raw_retry = self.client.complete(
                retry_messages, temperature=0.4
            )
            return parse_documents(raw_retry)

    def draft(self) -> DocumentPair:
        if not self.has_user_messages:
            raise SessionError("还没有访谈内容，先聊几句再生成初稿。")
        docs = self._generate(self._draft_messages())
        self.last_documents = docs
        self.calibrated = False
        return docs

    def revise(self, feedback: str) -> DocumentPair:
        if self.last_documents is None:
            raise SessionError("还没有初稿，先输入 /draft。")
        feedback = feedback.strip()
        if not feedback:
            raise SessionError("请先写下需要修改的地方。")
        messages = [
            {"role": "system", "content": self.prompts.revise},
            {
                "role": "user",
                "content": (
                    "以下是完整访谈记录：\n\n"
                    f"{self._transcript()}\n\n"
                    "以下是当前初稿：\n\n"
                    f"{self.last_documents.needs_statement}\n\n"
                    "---\n\n"
                    f"{self.last_documents.question_card}\n\n"
                    "以下是用户的校准反馈：\n\n"
                    f"{feedback}"
                ),
            },
        ]
        docs = self._generate(messages)
        self.last_documents = docs
        self.calibrated = False
        self.messages.append(
            {
                "role": "user",
                "content": f"对初稿的校准反馈：{feedback}",
            }
        )
        return docs

    def confirm(self) -> DocumentPair:
        if self.last_documents is None:
            raise SessionError("还没有初稿，先输入 /draft。")
        self.calibrated = True
        return self.last_documents
