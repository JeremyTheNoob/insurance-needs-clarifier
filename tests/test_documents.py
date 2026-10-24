from __future__ import annotations

from datetime import datetime

import pytest

import clarifier.documents as documents
from clarifier.documents import (
    DraftParseError,
    DocumentPair,
    build_footer,
    export_documents,
    parse_documents,
)

VALID = """\
前面可能有说明文字。
<<<NEEDS_STATEMENT>>>
# 我的需求
预算 5000 元。
<<<QUESTION_CARD>>>
1. 总保费是多少？
<<<END>>>
后面可能有说明文字。
"""


def test_parse_documents_extracts_both_sections():
    docs = parse_documents(VALID)

    assert docs.needs_statement == "# 我的需求\n预算 5000 元。"
    assert docs.question_card == "1. 总保费是多少？"


def test_parse_documents_requires_markers():
    with pytest.raises(DraftParseError, match="分隔符"):
        parse_documents("只有正文，没有标记")


def test_parse_documents_rejects_empty_section():
    raw = "<<<NEEDS_STATEMENT>>>\n\n<<<QUESTION_CARD>>>\n问题\n<<<END>>>"

    with pytest.raises(DraftParseError, match="为空"):
        parse_documents(raw)


def test_build_footer_contains_date_status_and_disclaimer():
    footer = build_footer(
        calibrated=True,
        generated_at=datetime(2026, 10, 21, 12, 0, 0),
    )

    assert "2026-10-21" in footer
    assert "已校准" in footer
    assert "不构成保险销售" in footer
    assert "条款解释" in footer
    assert "复查" in footer


def test_export_documents_writes_two_utf8_files(tmp_path):
    docs = DocumentPair(
        needs_statement="# 需求\n预算 5000 元。",
        question_card="1. 总保费是多少？",
    )
    stamp = datetime(2026, 10, 21, 12, 0, 0, 123456)

    needs_path, card_path = export_documents(
        docs,
        output_dir=tmp_path,
        calibrated=False,
        generated_at=stamp,
    )

    assert needs_path.exists()
    assert card_path.exists()
    assert needs_path.name.startswith("20261021-120000-123456")
    assert card_path.name.startswith("20261021-120000-123456")
    assert "未校准" in needs_path.read_text(encoding="utf-8")
    assert "1. 总保费是多少？" in card_path.read_text(encoding="utf-8")


def test_export_cleans_up_when_second_write_fails(tmp_path, monkeypatch):
    docs = DocumentPair(
        needs_statement="声明",
        question_card="问题卡",
    )
    original = documents._write_temp
    calls = {"count": 0}

    def flaky(output_dir, content):
        calls["count"] += 1
        if calls["count"] == 2:
            raise OSError("disk full")
        return original(output_dir, content)

    monkeypatch.setattr(documents, "_write_temp", flaky)

    with pytest.raises(OSError, match="disk full"):
        documents.export_documents(
            docs,
            output_dir=tmp_path,
            calibrated=True,
            generated_at=datetime(2026, 10, 21, 12, 0, 0),
        )

    assert list(tmp_path.iterdir()) == []
