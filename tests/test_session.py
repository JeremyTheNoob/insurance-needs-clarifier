from __future__ import annotations

import pytest

from clarifier.documents import DraftParseError
from clarifier.prompts import PromptLibrary
from clarifier.session import InterviewSession, SessionError
from tests.fakes import FakeChatClient

PROMPTS = PromptLibrary(system="SYS", draft="DRAFT", revise="REVISE")
VALID = (
    "<<<NEEDS_STATEMENT>>>\n"
    "声明正文\n"
    "<<<QUESTION_CARD>>>\n"
    "问题卡正文\n"
    "<<<END>>>"
)


def make_session(responses: list[str]) -> tuple[InterviewSession, FakeChatClient]:
    client = FakeChatClient(responses)
    return InterviewSession(client=client, prompts=PROMPTS), client


def test_reply_appends_user_and_assistant_messages():
    session, client = make_session(["你好呀"])

    result = session.reply("你好")

    assert result == "你好呀"
    assert [m["role"] for m in session.messages] == [
        "system",
        "user",
        "assistant",
    ]
    assert session.has_user_messages is True
    assert client.calls[0]["temperature"] == 0.7


def test_reply_rejects_empty_input():
    session, _ = make_session([])

    with pytest.raises(SessionError, match="不能为空"):
        session.reply("   ")


def test_draft_requires_user_message():
    session, _ = make_session([])

    with pytest.raises(SessionError, match="还没有访谈内容"):
        session.draft()


def test_draft_uses_full_transcript_and_parses():
    session, client = make_session(["好的", VALID])
    session.reply("预算 5000")

    docs = session.draft()

    assert docs.needs_statement == "声明正文"
    assert docs.question_card == "问题卡正文"
    assert session.last_documents == docs
    assert session.calibrated is False
    draft_call = client.calls[1]
    assert draft_call["messages"][0] == {"role": "system", "content": "DRAFT"}
    assert "预算 5000" in draft_call["messages"][1]["content"]
    assert "好的" in draft_call["messages"][1]["content"]
    assert draft_call["temperature"] == 0.4


def test_draft_retries_once_on_parse_error():
    session, client = make_session(["好的", "格式不对", VALID])
    session.reply("预算 5000")

    docs = session.draft()

    assert docs.needs_statement == "声明正文"
    assert len(client.calls) == 3
    retry_messages = client.calls[2]["messages"]
    assert retry_messages[-1]["role"] == "user"
    assert "分隔符" in retry_messages[-1]["content"]


def test_draft_retry_failure_raises():
    session, _ = make_session(["好的", "坏输出", "还是坏输出"])
    session.reply("预算 5000")

    with pytest.raises(DraftParseError, match="分隔符"):
        session.draft()


def test_revise_requires_draft():
    session, _ = make_session([])

    with pytest.raises(SessionError, match="还没有初稿"):
        session.revise("改一下")


def test_revise_includes_feedback_and_parses():
    session, client = make_session(["好的", VALID, VALID])
    session.reply("预算 5000")
    session.draft()

    docs = session.revise("第一条不像我")

    assert docs.needs_statement == "声明正文"
    assert session.calibrated is False
    revise_call = client.calls[2]
    assert revise_call["messages"][0] == {"role": "system", "content": "REVISE"}
    assert "第一条不像我" in revise_call["messages"][1]["content"]
    assert "声明正文" in revise_call["messages"][1]["content"]
    assert "问题卡正文" in revise_call["messages"][1]["content"]
    assert "对初稿的校准反馈：第一条不像我" in session.messages[-1]["content"]


def test_revise_rejects_empty_feedback():
    session, _ = make_session(["好的", VALID])
    session.reply("预算 5000")
    session.draft()

    with pytest.raises(SessionError, match="需要修改"):
        session.revise("   ")


def test_confirm_marks_calibrated():
    session, _ = make_session(["好的", VALID])
    session.reply("预算 5000")
    docs = session.draft()

    confirmed = session.confirm()

    assert confirmed == docs
    assert session.calibrated is True


def test_confirm_requires_draft():
    session, _ = make_session([])

    with pytest.raises(SessionError, match="还没有初稿"):
        session.confirm()


def test_has_user_messages_starts_false():
    session, _ = make_session([])

    assert session.has_user_messages is False


class RaisingClient:
    def complete(self, messages, temperature=0.7):
        raise RuntimeError("network down")


def test_reply_rolls_back_user_message_on_client_error():
    session = InterviewSession(client=RaisingClient(), prompts=PROMPTS)

    with pytest.raises(RuntimeError, match="network down"):
        session.reply("你好")

    assert session.messages == [{"role": "system", "content": "SYS"}]
    assert session.has_user_messages is False


def test_reply_rolls_back_user_message_on_empty_response():
    session, _ = make_session([""])

    with pytest.raises(SessionError, match="没有返回内容"):
        session.reply("你好")

    assert session.messages == [{"role": "system", "content": "SYS"}]
    assert session.has_user_messages is False


def test_failed_draft_preserves_last_documents_and_calibrated():
    session, _ = make_session(["好的", VALID, "坏输出", "还是坏输出"])
    session.reply("预算 5000")
    docs = session.draft()
    session.confirm()

    with pytest.raises(DraftParseError):
        session.draft()

    assert session.last_documents == docs
    assert session.calibrated is True


def test_failed_revise_preserves_messages():
    session, _ = make_session(["好的", VALID, "坏输出", "还是坏输出"])
    session.reply("预算 5000")
    session.draft()
    before = list(session.messages)

    with pytest.raises(DraftParseError):
        session.revise("第一条不像我")

    assert session.messages == before
    assert session.last_documents is not None


class RaisingKeyboardInterruptClient:
    def complete(self, messages, temperature=0.7):
        raise KeyboardInterrupt


def test_reply_rolls_back_user_message_on_keyboard_interrupt():
    session = InterviewSession(
        client=RaisingKeyboardInterruptClient(), prompts=PROMPTS
    )

    with pytest.raises(KeyboardInterrupt):
        session.reply("你好")

    assert session.messages == [{"role": "system", "content": "SYS"}]
    assert session.has_user_messages is False
