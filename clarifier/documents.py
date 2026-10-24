from __future__ import annotations

import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

NEEDS_MARKER = "<<<NEEDS_STATEMENT>>>"
CARD_MARKER = "<<<QUESTION_CARD>>>"
END_MARKER = "<<<END>>>"


class DraftParseError(ValueError):
    """Raised when the model output does not match the document envelope."""


@dataclass(frozen=True)
class DocumentPair:
    needs_statement: str
    question_card: str


def parse_documents(raw: str) -> DocumentPair:
    text = raw.strip()
    try:
        start = text.index(NEEDS_MARKER) + len(NEEDS_MARKER)
        card_start = text.index(CARD_MARKER, start)
        end = text.index(END_MARKER, card_start)
    except ValueError as exc:
        raise DraftParseError("模型输出缺少文档分隔符，无法解析。") from exc

    needs = text[start:card_start].strip()
    card = text[card_start + len(CARD_MARKER):end].strip()
    if not needs or not card:
        raise DraftParseError("模型输出中的文档为空。")
    return DocumentPair(needs_statement=needs, question_card=card)


def build_footer(*, calibrated: bool, generated_at: datetime | None = None) -> str:
    now = generated_at or datetime.now()
    status = "已校准" if calibrated else "未校准"
    return (
        "\n\n---\n\n"
        f"> 生成日期：{now:%Y-%m-%d}  \n"
        f"> 校准状态：{status}  \n"
        "> 仅用于澄清保险需求，不构成保险销售、产品推荐、条款解释、核保结论、法律或财务意见。"
        "产品信息以保险公司正式合同和核保结论为准。  \n"
        "> 建议在收入、家庭责任或已有保障发生变化时复查；否则 6–12 个月后复查。\n"
    )


def _write_temp(output_dir: Path, content: str) -> Path:
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=output_dir,
        prefix=".export-",
        suffix=".tmp",
        delete=False,
    )
    try:
        with handle:
            handle.write(content)
        return Path(handle.name)
    except Exception:
        Path(handle.name).unlink(missing_ok=True)
        raise


def export_documents(
    docs: DocumentPair,
    *,
    output_dir: Path,
    calibrated: bool,
    generated_at: datetime | None = None,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    now = generated_at or datetime.now()
    stamp = now.strftime("%Y%m%d-%H%M%S-%f")
    needs_path = output_dir / f"{stamp}-needs-statement.md"
    card_path = output_dir / f"{stamp}-question-card.md"
    footer = build_footer(calibrated=calibrated, generated_at=now)

    tmp_needs: Path | None = None
    tmp_card: Path | None = None
    published: list[Path] = []
    try:
        tmp_needs = _write_temp(
            output_dir, docs.needs_statement + footer
        )
        tmp_card = _write_temp(
            output_dir, docs.question_card + footer
        )
        tmp_needs.replace(needs_path)
        tmp_needs = None
        published.append(needs_path)
        tmp_card.replace(card_path)
        tmp_card = None
        published.append(card_path)
    except Exception:
        for path in (tmp_needs, tmp_card):
            if path is not None:
                path.unlink(missing_ok=True)
        for path in published:
            path.unlink(missing_ok=True)
        raise
    return needs_path, card_path
