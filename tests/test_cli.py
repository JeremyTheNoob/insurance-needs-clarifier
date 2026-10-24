from __future__ import annotations

from pathlib import Path

import clarifier.cli as cli
from clarifier.cli import run_repl
from clarifier.documents import DraftParseError
from clarifier.session import SessionError
from tests.fakes import FakeSession


def run_cli(inputs, *, session=None, output_dir: Path):
    session = session or FakeSession()
    output: list[str] = []
    lines = iter(inputs)

    def input_fn(_):
        return next(lines)

    run_repl(
        session,
        input_fn=input_fn,
        output_fn=output.append,
        output_dir=output_dir,
    )
    return session, "\n".join(output)


def md_files(path: Path) -> list[Path]:
    return sorted(path.glob("*.md"))


def test_normal_message_calls_reply(tmp_path):
    session, out = run_cli(
        ["你好", "/quit", "n"], output_dir=tmp_path
    )

    assert session.reply_calls == ["你好"]
    assert "收到。" in out
    assert "要生成一份未校准的文档再退出吗" in out


def test_draft_prints_documents_and_calibration_questions(tmp_path):
    session, out = run_cli(
        ["你好", "/draft", "/quit", "n"], output_dir=tmp_path
    )

    assert session.draft_calls == 1
    assert "个人保险需求声明" in out
    assert "投保自查问题卡" in out
    assert "哪一句最不像你" in out


def test_revise_applies_feedback_and_confirms(tmp_path):
    session, out = run_cli(
        ["你好", "/draft", "第一条不像我", "/revise", "/confirm"],
        output_dir=tmp_path,
    )

    assert session.revise_calls == ["第一条不像我"]
    assert session.confirm_calls == 1
    assert "修订后的声明" in out
    assert len(md_files(tmp_path)) == 2
    assert all(
        "已校准" in path.read_text(encoding="utf-8")
        for path in md_files(tmp_path)
    )


def test_confirm_without_feedback_asks_concrete_question(tmp_path):
    session, out = run_cli(
        ["你好", "/draft", "/confirm", "y"], output_dir=tmp_path
    )

    assert session.confirm_calls == 1
    assert "是否准确" in out
    assert len(md_files(tmp_path)) == 2


def test_back_returns_to_interview_and_keeps_feedback(tmp_path):
    session, out = run_cli(
        ["你好", "/draft", "预算改成 5000", "/back", "/quit", "n"],
        output_dir=tmp_path,
    )

    assert any(
        "预算改成 5000" in call for call in session.reply_calls
    )
    assert "回到访谈" in out


def test_vague_feedback_reprompts_without_revising(tmp_path):
    session, out = run_cli(
        ["你好", "/draft", "都行", "/quit", "n"], output_dir=tmp_path
    )

    assert session.revise_calls == []
    assert "太笼统" in out


def test_confirm_blocks_pending_feedback(tmp_path):
    session, out = run_cli(
        [
            "你好",
            "/draft",
            "第一条不像我",
            "/confirm",
            "/quit",
            "n",
        ],
        output_dir=tmp_path,
    )

    assert session.confirm_calls == 0
    assert "未应用的反馈" in out


def test_revise_without_feedback_warns(tmp_path):
    session, out = run_cli(
        ["你好", "/draft", "/revise", "/quit", "n"],
        output_dir=tmp_path,
    )

    assert session.revise_calls == []
    assert "先写下" in out


def test_quit_from_interview_exports_uncalibrated(tmp_path):
    session, out = run_cli(
        ["你好", "/quit", "y"], output_dir=tmp_path
    )

    assert session.draft_calls == 1
    assert len(md_files(tmp_path)) == 2
    assert all(
        "未校准" in path.read_text(encoding="utf-8")
        for path in md_files(tmp_path)
    )


def test_quit_from_review_exports_current_docs(tmp_path):
    session, out = run_cli(
        ["你好", "/draft", "/quit", "y"], output_dir=tmp_path
    )

    assert session.draft_calls == 1
    assert len(md_files(tmp_path)) == 2


def test_unknown_command_shows_help_hint(tmp_path):
    session, out = run_cli(
        ["/foo", "/quit", "n"], output_dir=tmp_path
    )

    assert "未知命令" in out


def test_help_lists_commands(tmp_path):
    session, out = run_cli(
        ["/help", "/quit", "n"], output_dir=tmp_path
    )

    assert "/draft" in out
    assert "/confirm" in out


def test_welcome_discloses_privacy(tmp_path):
    session, out = run_cli(["/quit", "n"], output_dir=tmp_path)

    assert "模型服务商" in out
    assert "不保存" in out
    assert "健康信息" in out


def test_stop_iteration_exits_cleanly(tmp_path):
    def input_fn(_):
        raise StopIteration

    output: list[str] = []
    run_repl(
        FakeSession(),
        input_fn=input_fn,
        output_fn=output.append,
        output_dir=tmp_path,
    )

    assert "已退出" in "\n".join(output)


def test_conversation_end_exports_uncalibrated(tmp_path):
    for exc in (EOFError, KeyboardInterrupt):
        lines = iter(["你好"])

        def input_fn(_):
            try:
                return next(lines)
            except StopIteration:
                raise exc

        output: list[str] = []
        run_repl(
            FakeSession(),
            input_fn=input_fn,
            output_fn=output.append,
            output_dir=tmp_path,
        )

        files = list(tmp_path.glob("*.md"))
        assert len(files) == 2
        assert all(
            "未校准" in path.read_text(encoding="utf-8")
            for path in files
        )
        for path in files:
            path.unlink()


def test_eof_at_quit_prompt_exits_cleanly(tmp_path):
    lines = iter(["/quit"])

    def input_fn(_):
        try:
            return next(lines)
        except StopIteration:
            raise EOFError

    output: list[str] = []
    run_repl(
        FakeSession(),
        input_fn=input_fn,
        output_fn=output.append,
        output_dir=tmp_path,
    )

    text = "\n".join(output)
    assert "要生成一份未校准的文档再退出吗" in text
    assert list(tmp_path.glob("*.md")) == []


class InterruptingSession(FakeSession):
    def reply(self, text: str) -> str:
        self.reply_calls.append(text)
        raise KeyboardInterrupt


def test_keyboard_interrupt_during_reply_keeps_repl_alive(tmp_path):
    session, out = run_cli(
        ["你好", "/quit", "n"],
        session=InterruptingSession(),
        output_dir=tmp_path,
    )

    assert "已中断" in out


class InterruptingDraftSession(FakeSession):
    def draft(self):
        self.draft_calls += 1
        raise KeyboardInterrupt


def test_keyboard_interrupt_during_draft_keeps_repl_alive(tmp_path):
    session, out = run_cli(
        ["你好", "/draft", "/quit", "n"],
        session=InterruptingDraftSession(),
        output_dir=tmp_path,
    )

    assert "已中断" in out


def test_vague_feedback_variants_reprompt(tmp_path):
    for vague in ("都行。", "都行吧", "随便啦", "好吧"):
        session, out = run_cli(
            ["你好", "/draft", vague, "/quit", "n"],
            output_dir=tmp_path,
        )
        assert session.revise_calls == []
        assert "太笼统" in out


class FailingReviseSession(FakeSession):
    def revise(self, feedback: str):
        self.revise_calls.append(feedback)
        raise SessionError("修订失败")


def test_failed_revise_keeps_feedback_pending(tmp_path):
    session, out = run_cli(
        [
            "你好",
            "/draft",
            "第一条不像我",
            "/revise",
            "/confirm",
            "/quit",
            "n",
        ],
        session=FailingReviseSession(),
        output_dir=tmp_path,
    )

    assert "修订失败" in out
    assert "未应用的反馈" in out
    assert session.confirm_calls == 0


def test_confirm_export_failure_does_not_finalize(tmp_path, monkeypatch):
    def fail_export(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(cli, "export_documents", fail_export)
    session, out = run_cli(
        ["你好", "/draft", "/confirm", "y"], output_dir=tmp_path
    )

    assert "导出失败" in out
    assert "已定稿" not in out
    assert session.calibrated is False


class FailingReplySession(FakeSession):
    def reply(self, text: str) -> str:
        self.reply_calls.append(text)
        raise RuntimeError("network down")


def test_model_error_keeps_repl_alive(tmp_path):
    session, out = run_cli(
        ["你好", "/quit", "n"],
        session=FailingReplySession(),
        output_dir=tmp_path,
    )

    assert "调用模型失败" in out


class FailingDraftSession(FakeSession):
    def draft(self):
        self.draft_calls += 1
        raise SessionError("生成失败")


def test_draft_failure_keeps_repl_alive(tmp_path):
    session, out = run_cli(
        ["你好", "/draft", "/quit", "n"],
        session=FailingDraftSession(),
        output_dir=tmp_path,
    )

    assert "生成初稿失败" in out


class DraftParseFailingSession(FakeSession):
    def draft(self):
        self.draft_calls += 1
        raise DraftParseError("格式错误")


def test_draft_parse_error_keeps_repl_alive(tmp_path):
    session, out = run_cli(
        ["你好", "/draft", "/quit", "n"],
        session=DraftParseFailingSession(),
        output_dir=tmp_path,
    )

    assert "生成初稿失败" in out
