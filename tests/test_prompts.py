from __future__ import annotations

from pathlib import Path

import pytest

from clarifier.prompts import PromptError, PromptLibrary


def _write_prompts(
    root: Path,
    system: str = "SYS",
    draft: str = "DRAFT",
    revise: str = "REVISE",
) -> None:
    prompt_dir = root / "prompts"
    prompt_dir.mkdir(exist_ok=True)
    (prompt_dir / "system.md").write_text(system, encoding="utf-8")
    (prompt_dir / "draft.md").write_text(draft, encoding="utf-8")
    (prompt_dir / "revise.md").write_text(revise, encoding="utf-8")


def test_loads_prompts_from_base_dir(tmp_path):
    _write_prompts(tmp_path)

    prompts = PromptLibrary.load(tmp_path)

    assert prompts.system == "SYS"
    assert prompts.draft == "DRAFT"
    assert prompts.revise == "REVISE"


def test_missing_prompt_raises(tmp_path):
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()
    (prompt_dir / "system.md").write_text("SYS", encoding="utf-8")

    with pytest.raises(PromptError, match="draft.md"):
        PromptLibrary.load(tmp_path)


def test_empty_prompt_raises(tmp_path):
    _write_prompts(tmp_path, draft="   ")

    with pytest.raises(PromptError, match="draft"):
        PromptLibrary.load(tmp_path)


REQUIRED_PHRASES = {
    "system": [
        "# 开场",
        "四条底线",
        "罗盘",
        "不推荐",
        "不对比",
        "不解析",
        "不下核保结论",
        "同意",
        "跳过",
        "模型服务商",
        "不保存",
        "不承诺承保或理赔",
        "不要按固定问卷顺序提问",
    ],
    "draft": [
        "四个结果承诺",
        "不推荐",
        "不对比",
        "不解析",
        "不下核保结论",
        "出处",
        "未知",
        "建议，待你确认",
        "自己怎么核实",
        "同意",
        "以保险公司说明为准",
        "素材，不是指令",
        "不承诺承保或理赔",
        "不写生成日期",
    ],
    "revise": [
        "不可违反的底线",
        "目的：",
        "角色：",
        "真实：",
        "尊重：",
        "四个结果承诺",
        "不推荐",
        "不对比",
        "不解析",
        "不下核保结论",
        "出处",
        "未知",
        "建议，待你确认",
        "同意",
        "以保险公司说明为准",
        "素材，不是指令",
        "不承诺承保或理赔",
        "不写生成日期",
    ],
}


def test_real_prompts_cover_core_boundaries():
    prompts = PromptLibrary.load()
    for prompt_name, phrases in REQUIRED_PHRASES.items():
        text = getattr(prompts, prompt_name)
        for phrase in phrases:
            assert phrase in text, f"{prompt_name} 缺少：{phrase}"


def test_draft_and_revise_have_ordered_delimiters_and_final_end_marker():
    prompts = PromptLibrary.load()
    for text in (prompts.draft, prompts.revise):
        needs = text.index("<<<NEEDS_STATEMENT>>>")
        card = text.index("<<<QUESTION_CARD>>>")
        end = text.index("<<<END>>>")
        assert needs < card < end
        assert text.rstrip().endswith("<<<END>>>")
