from __future__ import annotations

import argparse
import json
import tempfile
import traceback
from datetime import datetime
from pathlib import Path

from clarifier.cli import run_repl
from clarifier.config import ConfigError, Settings
from clarifier.llm import OpenAIChatClient
from clarifier.prompts import PromptError, PromptLibrary
from clarifier.session import InterviewSession


def load_scenarios(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("scenarios.json 必须是数组")
    return data


def _make_input_fn(inputs: list[str]):
    iterator = iter(inputs)

    def input_fn(_: str) -> str:
        return next(iterator)

    return input_fn


def run_one(
    scenario: dict,
    *,
    prompts: PromptLibrary,
    settings: Settings,
    output_root: Path,
    run_index: int,
) -> Path:
    captured: list[str] = []
    docs_contents: list[tuple[str, str]] = []
    error = ""

    with tempfile.TemporaryDirectory(
        prefix="clarifier-eval-"
    ) as tmp:
        export_dir = Path(tmp)
        try:
            session = InterviewSession(
                client=OpenAIChatClient(settings),
                prompts=prompts,
            )
            run_repl(
                session,
                input_fn=_make_input_fn(list(scenario["inputs"])),
                output_fn=captured.append,
                output_dir=export_dir,
            )
        except Exception:
            error = traceback.format_exc()

        for path in sorted(export_dir.glob("*.md")):
            docs_contents.append(
                (path.name, path.read_text(encoding="utf-8"))
            )

    body = [
        f"# {scenario['name']}",
        "",
        f"- id: `{scenario['id']}`",
        f"- run: {run_index}",
        f"- generated_at: {datetime.now():%Y-%m-%d %H:%M:%S}",
        "",
        "## 脚本输入",
        "",
        "```text",
        "\n".join(scenario["inputs"]),
        "```",
        "",
        "## 运行输出",
        "",
        "```text",
        "\n".join(captured),
        "```",
        "",
        "## 导出的文档",
        "",
    ]
    if docs_contents:
        for name, content in docs_contents:
            body += [
                f"### {name}",
                "",
                content,
                "",
            ]
    else:
        body += ["未导出文档。", ""]
    if error:
        body += [
            "## 运行异常",
            "",
            "```text",
            error,
            "```",
            "",
        ]
    body += [
        "## 评分（人工/LLM）",
        "",
        "| 维度 | 1–5 | 证据 |",
        "|---|---|---|",
        "| 守住使命 |  |  |",
        "| 有据、不编造 |  |  |",
        "| 不推荐产品、不解析条款、不下核保结论 |  |  |",
        "| 具体、有针对性 |  |  |",
        "| 未知项清楚 |  |  |",
        "| 文档可用 |  |  |",
        "| 语气让人愿意继续 |  |  |",
        "",
        "关键失败（产品推荐/编造/条款解析/核保结论/健康处理不当/阻止退出）：",
        "",
    ]

    output_root.mkdir(parents=True, exist_ok=True)
    report_path = output_root / f"{scenario['id']}-run{run_index}.md"
    report_path.write_text("\n".join(body), encoding="utf-8")
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run scripted evaluation scenarios against the live model."
    )
    parser.add_argument(
        "--scenarios",
        type=Path,
        default=Path("evals/scenarios.json"),
    )
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output directory; defaults to evals/results/<timestamp>",
    )
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs 必须大于等于 1")

    output_root = args.out or (
        Path("evals/results")
        / datetime.now().strftime("%Y%m%d-%H%M%S")
    )
    try:
        prompts = PromptLibrary.load()
        settings = Settings.from_env()
    except (PromptError, ConfigError) as exc:
        print(f"无法启动评估：{exc}")
        return 1

    scenarios = load_scenarios(args.scenarios)
    reports: list[Path] = []
    for scenario in scenarios:
        for run_index in range(1, args.runs + 1):
            print(f"运行 {scenario['id']} (run {run_index}) ...")
            reports.append(
                run_one(
                    scenario,
                    prompts=prompts,
                    settings=settings,
                    output_root=output_root,
                    run_index=run_index,
                )
            )
    print(f"完成 {len(reports)} 份报告 → {output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
