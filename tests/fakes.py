from __future__ import annotations

from clarifier.documents import DocumentPair


class FakeChatClient:
    def __init__(self, responses: list[str]):
        self.responses = list(responses)
        self.calls: list[dict] = []

    def complete(self, messages, temperature=0.7) -> str:
        self.calls.append(
            {"messages": list(messages), "temperature": temperature}
        )
        if not self.responses:
            raise AssertionError("FakeChatClient 没有更多预设回复")
        return self.responses.pop(0)


class FakeSession:
    def __init__(self, docs: DocumentPair | None = None):
        self.last_documents = docs
        self.calibrated = False
        self.reply_calls: list[str] = []
        self.draft_calls = 0
        self.revise_calls: list[str] = []
        self.confirm_calls = 0
        self._reply_response = "收到。"

    @property
    def has_user_messages(self) -> bool:
        return True

    def reply(self, text: str) -> str:
        self.reply_calls.append(text)
        return self._reply_response

    def draft(self) -> DocumentPair:
        self.draft_calls += 1
        if self.last_documents is None:
            self.last_documents = DocumentPair("声明初稿", "问题卡初稿")
        return self.last_documents

    def revise(self, feedback: str) -> DocumentPair:
        self.revise_calls.append(feedback)
        self.last_documents = DocumentPair("修订后的声明", "修订后的问题卡")
        return self.last_documents

    def confirm(self) -> DocumentPair:
        self.confirm_calls += 1
        self.calibrated = True
        return self.last_documents
