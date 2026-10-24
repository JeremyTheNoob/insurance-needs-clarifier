# 保险需求澄清器（Insurance Needs Clarifier）

一个开源、BYOK、AI-native 的保险需求访谈工具。它不推荐产品、不解析条款，只帮你在接触产品之前，把模糊的担心整理成一份可核实的《个人保险需求声明》，以及一张由这次对话生成的《投保自查问题卡》。

> 本工具仅用于澄清保险需求，不构成保险销售、产品推荐、条款解释、核保结论、法律或财务意见。产品信息以保险公司正式合同和核保结论为准。

## 它做什么

- 用一场对话帮你弄清楚：为什么现在考虑保险、最承受不起什么、预算上限、先保障谁、已有保障、主动放弃什么。
- 根据完整对话生成两份 Markdown：需求声明和自查问题卡。
- 让你校准初稿：哪一句不像你、哪一项其实已有答案、如果只能改一处改哪里。
- 导出后可自己留存，也可以带去见销售或对照网购页面。

## 它不做什么

- 不推荐或对比具体产品/公司；
- 不判断性价比，不解析具体条款；
- 不输出核保结论，不承诺承保或理赔；
- 不做账户、数据库或历史记录。

## 设计文档

- [产品设计](docs/design.md)：定位、非目标、AI-native 运行模型、评估与合规边界。

## 快速开始

需要 Python 3.10+。

```bash
git clone https://github.com/JeremyTheNoob/insurance-needs-clarifier.git
cd insurance-needs-clarifier
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
test -f .env || cp .env.example .env
# 编辑 .env，填入你的 API Key 和模型；填好后不要再执行上面的复制
python app.py
```

Windows 用户请使用 `.venv\Scripts\activate` 激活虚拟环境；如果 `.env` 不存在，手动复制 `.env.example` 为 `.env`，已有 `.env` 不要覆盖。

如果 `.env` 已经存在，不要再次复制 `.env.example`，否则会覆盖你填好的密钥。应用启动时如果检测到占位值 `your-key-here` 会直接报错。

任何 OpenAI 兼容端点都可以（需支持 Chat Completions）。`.env.example` 默认给出 DeepSeek 的示例配置，也可以换成其他服务商。

```bash
OPENAI_API_KEY=your-key-here
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat
```

## 命令

| 命令 | 作用 |
|---|---|
| `/draft` | 根据当前对话生成初稿 |
| `/revise` | 应用你的修改意见，生成修订版 |
| `/confirm` | 定稿并导出两份 Markdown |
| `/back` | 回到访谈，继续补充信息 |
| `/help` | 查看命令 |
| `/quit` | 退出；可带走一份未校准文档 |

初稿会打印三个校准问题。你可以直接输入修改意见，再输入 `/revise`。如果没有任何具体修改，`/confirm` 会先问你一个具体的确认问题；"都行"不算确认。

## 输出

定稿写入 `outputs/`，每次生成两个文件：

- `YYYYMMDD-HHMMSS-microseconds-needs-statement.md`
- `YYYYMMDD-HHMMSS-microseconds-question-card.md`

文件末尾会追加生成日期、校准状态、免责声明和复查建议。

想看一份虚构示例：[`examples/sample-output.md`](examples/sample-output.md)。

## 隐私与边界

- BYOK：本项目自身没有服务器，不收集或留存对话；对话只发往你配置的模型服务商。正常使用会消耗你自己的 API 额度。
- 无账户、无数据库；导出的文件由你自己保管。
- 健康信息属于敏感个人信息。提示词要求模型在涉及健康信息前先征得同意，你可以跳过；只记录你主动描述的内容，不下核保结论。导出的本地文件可能包含这些信息，请自行妥善保管。
- 默认面向中国内地语境；其他市场的术语和合规要求需要另行适配。

## 质量评估

仓库带有 12 个脚本化评估场景：

```bash
python -m evals.run_evals --runs 1
```

报告写入 `evals/results/<timestamp>/`。评分标准见 `evals/rubric.md`，可选的模型评审提示词见 `evals/judge.md`。评估会调用真实模型并产生费用；请只使用虚构场景。

## 当前限制

- MVP 是终端 REPL，Web 界面不在本版本；
- 输出质量依赖所用模型；
- 没有历史记录；重新运行就是新会话；
- 不接入 FinClaw 或其他外部 Agent Skill；核保问卷自查留到后续版本。

> 本工具仅用于澄清保险需求，不构成保险销售、产品推荐、条款解释、核保结论、法律或财务意见。产品信息以保险公司正式合同和核保结论为准。

## License

MIT，详见 [LICENSE](LICENSE)。
