from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

from .documents import DocumentPair, DraftParseError, export_documents
from .session import InterviewSession, SessionError

CALIBRATION_QUESTIONS = """
请具体看看这份初稿，回答三个问题：
1. 哪一句最不像你？
2. 哪一项你其实已经有答案，只是我没问出来？
3. 如果只能改一处，你想改哪里？
"""

VAGUE_REPLIES = {
    "都行",
    "都可以",
    "随便",
    "没有",
    "没啥",
    "都差不多",
    "你看着办",
    "没有修改",
    "没问题",
    "可以",
    "好",
    "行",
}

HELP_TEXT = """可用命令：
/draft     生成初稿（需求声明 + 自查问题卡）
/revise    应用你的修改意见，生成修订版
/confirm   定稿并导出两份 Markdown
/back      回到访谈，继续补充信息
/help      查看命令
/quit      退出
"""

WELCOME = """保险需求澄清器（MVP）

这里不推荐具体产品、不对比产品、不解析条款。对话内容会发送给你配置的模型服务商，本项目不保存；你可以随时输入 /quit 退出。涉及健康信息时会先征得你的同意。

先聊聊你为什么开始考虑保险。输入 /help 查看命令。
"""

InputFn = Callable[[str], str]
OutputFn = Callable[[str], None]


def _read(
    input_fn: InputFn,
    output_fn: OutputFn,
    prompt: str,
) -> str:
    output_fn(prompt)
    return input_fn("")


def _ask_yes_no(
    input_fn: InputFn,
    output_fn: OutputFn,
    prompt: str,
) -> bool:
    try:
        answer = _read(input_fn, output_fn, prompt).strip().lower()
    except (KeyboardInterrupt, StopIteration, EOFError):
        return False
    answer = answer.strip("。！？!?，,")
    return answer in {
        "y",
        "yes",
        "是",
        "对",
        "好的",
        "好",
        "嗯",
        "确定",
    }


def _is_vague(text: str) -> bool:
    normalized = re.sub(r"[\s。！？!?，,、.…~～]+", "", text)
    normalized = re.sub(r"(吧|啦|呀|哦|啊|嘛|呢)$", "", normalized)
    return normalized in VAGUE_REPLIES


def _print_documents(
    docs: DocumentPair,
    output_fn: OutputFn,
) -> None:
    output_fn("\n===== 个人保险需求声明 =====\n")
    output_fn(docs.needs_statement)
    output_fn("\n===== 投保自查问题卡 =====\n")
    output_fn(docs.question_card)
    output_fn(CALIBRATION_QUESTIONS)


def _export(
    session: InterviewSession,
    output_dir: Path,
    output_fn: OutputFn,
) -> bool:
    if session.last_documents is None:
        output_fn("还没有初稿，先输入 /draft。")
        return False
    try:
        needs_path, card_path = export_documents(
            session.last_documents,
            output_dir=output_dir,
            calibrated=session.calibrated,
        )
    except KeyboardInterrupt:
        output_fn("\n导出已中断。")
        return False
    except OSError as exc:
        output_fn(f"导出失败：{exc}")
        return False
    output_fn(f"已导出：\n- {needs_path}\n- {card_path}")
    return True


def _confirm(
    session: InterviewSession,
    mode: str,
    feedback: list[str],
    feedback_given: bool,
    input_fn: InputFn,
    output_fn: OutputFn,
    output_dir: Path,
) -> tuple[bool, bool]:
    if mode != "review":
        output_fn("先输入 /draft 生成初稿，再定稿。")
        return False, feedback_given
    if feedback:
        output_fn(
            "你还有未应用的反馈。先输入 /revise 应用反馈，或 /back 回到访谈。"
        )
        return False, feedback_given
    if not feedback_given:
        confirmed = _ask_yes_no(
            input_fn,
            output_fn,
            "你还没有指出具体修改。请确认：初稿里关于你最担心什么、"
            "预算和保障对象的描述，是否准确？(y/N) ",
        )
        if not confirmed:
            output_fn(
                "继续审阅。可以写出具体修改，或输入 /back 回到访谈。"
            )
            return False, feedback_given
    session.confirm()
    if _export(session, output_dir, output_fn):
        output_fn("已定稿。需要重新开始请再运行一次程序。")
        return True, True
    session.calibrated = False
    return False, feedback_given


def _handle_quit(
    session: InterviewSession,
    mode: str,
    feedback: list[str],
    input_fn: InputFn,
    output_fn: OutputFn,
    output_dir: Path,
) -> None:
    if mode == "review" and session.last_documents is not None:
        if feedback:
            output_fn(
                "注意：你还有未应用的反馈，当前导出不会包含它。"
            )
        if _ask_yes_no(
            input_fn, output_fn, "要导出当前版本再退出吗？(y/N) "
        ):
            _export(session, output_dir, output_fn)
        return
    if mode == "interview" and session.has_user_messages:
        if _ask_yes_no(
            input_fn,
            output_fn,
            "要生成一份未校准的文档再退出吗？(y/N) ",
        ):
            try:
                session.draft()
            except KeyboardInterrupt:
                output_fn("\n已中断，退出。")
                return
            except Exception as exc:
                output_fn(f"生成文档失败：{exc}")
                return
            _export(session, output_dir, output_fn)


def _handle_conversation_end(
    session: InterviewSession,
    mode: str,
    output_fn: OutputFn,
    output_dir: Path,
) -> None:
    output_fn("\n已退出。")
    if mode == "review" and session.last_documents is not None:
        _export(session, output_dir, output_fn)
        return
    if mode == "interview" and session.has_user_messages:
        output_fn("检测到已有对话，正在生成一份未校准文档以便保存...")
        try:
            session.draft()
        except KeyboardInterrupt:
            output_fn("\n保存已中断。")
            return
        except Exception as exc:
            output_fn(f"生成文档失败：{exc}")
            return
        _export(session, output_dir, output_fn)


def run_repl(
    session: InterviewSession,
    *,
    input_fn: InputFn | None = None,
    output_fn: OutputFn = print,
    output_dir: Path = Path("outputs"),
) -> None:
    input_fn = input_fn or (lambda _: input())
    output_fn(WELCOME)
    mode = "interview"
    feedback: list[str] = []
    feedback_given = False
    vague_count = 0

    while True:
        prompt = "你: " if mode == "interview" else "反馈: "
        try:
            raw = _read(input_fn, output_fn, prompt)
        except (KeyboardInterrupt, StopIteration, EOFError):
            _handle_conversation_end(
                session, mode, output_fn, output_dir
            )
            return
        text = raw.strip()
        if not text:
            continue

        if text == "/quit":
            _handle_quit(
                session,
                mode,
                feedback,
                input_fn,
                output_fn,
                output_dir,
            )
            return
        if text == "/help":
            output_fn(HELP_TEXT)
            continue

        if text == "/draft":
            if mode == "review":
                output_fn(
                    "正在审阅初稿。用 /revise 应用反馈，"
                    "或 /back 回到访谈再生成新的初稿。"
                )
                continue
            try:
                docs = session.draft()
            except KeyboardInterrupt:
                output_fn("\n已中断，回到对话。")
                continue
            except (SessionError, DraftParseError) as exc:
                output_fn(f"生成初稿失败：{exc}")
                continue
            except Exception as exc:
                output_fn(
                    f"调用模型失败：{exc}。"
                    "请检查网络、Key 和模型配置后重试。"
                )
                continue
            _print_documents(docs, output_fn)
            mode = "review"
            feedback.clear()
            feedback_given = False
            vague_count = 0
            continue

        if text == "/revise":
            if mode != "review":
                output_fn("先输入 /draft 生成初稿，再修改。")
                continue
            if not feedback:
                output_fn("先写下需要修改的地方，再输入 /revise。")
                continue
            try:
                docs = session.revise("\n".join(feedback))
            except KeyboardInterrupt:
                output_fn("\n已中断，回到对话。")
                continue
            except (SessionError, DraftParseError) as exc:
                output_fn(f"修订失败：{exc}")
                continue
            except Exception as exc:
                output_fn(
                    f"调用模型失败：{exc}。"
                    "请检查网络、Key 和模型配置后重试。"
                )
                continue
            _print_documents(docs, output_fn)
            feedback.clear()
            feedback_given = True
            vague_count = 0
            continue

        if text == "/confirm":
            should_exit, feedback_given = _confirm(
                session,
                mode,
                feedback,
                feedback_given,
                input_fn,
                output_fn,
                output_dir,
            )
            if should_exit:
                return
            continue

        if text == "/back":
            if mode != "review":
                output_fn("现在就在访谈模式。")
                continue
            if feedback:
                combined = (
                    "关于刚才初稿的反馈：" + "\n".join(feedback)
                )
                try:
                    response = session.reply(combined)
                except KeyboardInterrupt:
                    output_fn("\n已中断，回到对话。")
                    continue
                except Exception as exc:
                    output_fn(f"回到访谈时调用模型失败：{exc}")
                    continue
                output_fn(response)
                feedback.clear()
            mode = "interview"
            output_fn("回到访谈。补充的信息会进入下一次 /draft。")
            continue

        if text.startswith("/"):
            output_fn("未知命令。输入 /help 查看可用命令。")
            continue

        if mode == "review":
            if _is_vague(text):
                vague_count += 1
                if vague_count == 1:
                    output_fn(
                        "这个回答太笼统，我没法据此修改。具体一点："
                        "声明里关于你最担心什么的那一句，准确吗？"
                        "哪一句最不像你？"
                    )
                else:
                    output_fn(
                        "如果暂时没有具体修改，可以输入 /confirm 定稿，"
                        "或 /back 回到访谈补充信息。"
                    )
                continue
            feedback.append(text)
            vague_count = 0
            output_fn(
                "记下了。还有别的修改吗？输入 /revise 应用反馈，"
                "/confirm 定稿，/back 回到访谈。"
            )
            continue

        try:
            response = session.reply(text)
        except KeyboardInterrupt:
            output_fn("\n已中断，回到对话。")
            continue
        except SessionError as exc:
            output_fn(str(exc))
            continue
        except Exception as exc:
            output_fn(
                f"调用模型失败：{exc}。"
                "请检查网络、Key 和模型配置后重试。"
            )
            continue
        output_fn(response)
