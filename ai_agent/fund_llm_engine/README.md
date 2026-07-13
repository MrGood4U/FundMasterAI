# fund-llm-engine

面向基金分析场景的 LLM / 多智能体分析模块。

这个目录只保留“大模型 / 多智能体 / 解释生成”相关的核心模块。仓库根目录的
`backend/` 和 `frontend_new/` 只用于端到端 demo 联调。

本模块本身不负责：

- 前端页面
- 数据库
- 监控和通知
- PDF 导出
- 股票策略模块

当前目录可以作为大仓库里的 AI Agent 子模块继续演进，也可以独立安装和测试。

## 当前包含的内容

- `contracts`：输入输出契约
- `feature_builder`：非 LLM 的结构化特征构建
- `llm_client`：统一模型调用和 mock client
- `agents`：按视角拆分的分析师模块
- `engine`：多 agent 编排和 chief 汇总
- `tests`：独立可跑的基础测试
- `adapters/backend_function_client.py`：读取队友后端 function registry 并执行 HTTP tool call
- `app.py`：独立 Agent HTTP 服务，默认 `5003`
- `docs/migration_notes.md`：迁移范围说明

## 目录

```text
fund-llm-engine/
├── docs/
├── app.py
├── src/fund_llm/
│   ├── adapters/
│   ├── agents/
│   └── orchestration/
└── tests/
```

## 快速开始

```bash
cd ai_agent/fund_llm_engine
python3 -m unittest discover -s tests
```

## 本地环境

这个模块是一个独立的 Python 项目，依赖声明在 [pyproject.toml](pyproject.toml)，当前要求：

- Python `>=3.11`
- 运行依赖：
  - `openai>=1.12.0`
  - `python-dotenv>=1.0.0`
- 后端联调依赖：
  - `akshare`
  - `flask`
  - `flask-openapi3`
  - `pandas`

推荐给这个项目单独建一个本地虚拟环境 `.venv`：

```bash
cd ai_agent/fund_llm_engine
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[backend]"
```

如果你要跑真实 LLM demo，再补一份本地 `.env`：

```bash
cp .env.example .env
```

然后填写：

- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL`

如果使用 DeepSeek，可以直接配置：

- `LLM_API_KEY=你的 DeepSeek API Key`
- `LLM_BASE_URL=https://api.deepseek.com`
- `LLM_MODEL=deepseek-v4-pro`

[.env.example](.env.example) 默认使用当前演示支持的 OpenCode Go / DeepSeek 配置。

建好环境后，建议先做一轮最小验证：

```bash
source .venv/bin/activate
python3 -m unittest discover -s tests
python3 scripts/run_mock_demo.py
```

## 对接队友最新 dev 后端

队友最新后端提供三个服务：

```text
market_backend     http://127.0.0.1:5001
news_backend       http://127.0.0.1:5000
portfolio_backend  http://127.0.0.1:5002
```

每个服务都暴露 function calling 风格的接口定义。本模块通过
`BackendFunctionClient` 读取这些定义，再按 `path` / `method` / `parameters`
发 HTTP 请求。基金分析当前会使用这些后端工具：

```text
get_fund_hist
get_fund_individual_basic_info
get_fund_portfolio_holds
get_fund_individual_analysis
get_fund_profit_probability
get_public_fund_announcement
```

启动顺序：

```bash
# 1. 启动基金分析需要的队友后端
cd ../../backend/market_backend
bash start.sh
cd ../news_backend
bash start.sh

# portfolio_backend 只有做用户持仓/交易分析时才需要，并且依赖 MySQL。

# 2. 启动 Agent backend
cd ../../ai_agent/fund_llm_engine
pip install -e ".[agent]"
bash start.sh
```

`start.sh` 会优先使用本目录 `.venv/bin/python`，自动等待 `/health`，
并在未显式设置 `NEWS_BACKEND_URL` 时探测本机 `5000` / `5010` 新闻后端。
运行日志写入 `app.log`，进程号写入 `app.pid`；停止服务用 `bash stop.sh`。

默认 Agent 接口：

```text
GET  http://127.0.0.1:5003/health
GET  http://127.0.0.1:5003/api/ai/functions
POST http://127.0.0.1:5003/api/ai/fund/analyze
```

本地无 LLM key 时可用 mock 模式验证后端工具链：

```bash
curl -s -X POST http://127.0.0.1:5003/api/ai/fund/analyze \
  -H 'Content-Type: application/json' \
  -d '{"code":"000001","mock":true}'
```

真实模型模式不要传 `mock:true`，并确保 `.env` 里设置了 `LLM_API_KEY`。

## 当前开发方式

当前阶段先采用 `mock-first` 开发方式，把流程、契约和编排做稳，再接真实模型。

- 跑全部测试：`python3 -m unittest discover -s tests`
- 跑一遍 mock 全流程 demo：`python3 scripts/run_mock_demo.py`
- 用 JSON 样例驱动 mock 流程：`python3 scripts/run_mock_demo.py examples/mock_input.json`
- 把 mock 结果直接存成文件：`python3 scripts/run_mock_demo.py examples/mock_input.json --output outputs/mock_result.json`
- 检查当前特征构建结果：`python3 scripts/inspect_mock_features.py`
- 检查升级后的 agent / chief 输出：`python3 scripts/inspect_agent_outputs.py`
- 跑一遍真实模型 demo：`python3 scripts/run_real_demo.py`
- 把真实模型结果直接存成文件：`python3 scripts/run_real_demo.py examples/mock_input.json --output outputs/real_result.json`
- 跑一遍输出质量评估：`python3 scripts/evaluate_analysis_output.py --input examples/mock_input.json --mode mock`
- 跑整套 golden cases：`python3 scripts/run_golden_suite.py --mode mock`
- 生成 AI 联调评分快照：`python3 scripts/score_guardrails.py snapshot --output outputs/score_snapshot_before.json`
- 对比改动前后分数：`python3 scripts/score_guardrails.py compare --before outputs/score_snapshot_before.json --after outputs/score_snapshot_after.json --fail-on-unexpected`
- 检查是否误改队友后端：`python3 scripts/score_guardrails.py scope-check`

其中 `mock demo` 不需要联网，也不需要 API Key，会直接输出一份完整的分析结果 JSON。

评分与协作护栏的详细说明见 [docs/score_guardrails_zh.md](docs/score_guardrails_zh.md)。建议每次改 AI Agent 前先保存一份 before 快照，改完保存 after 快照，再运行 compare 和 scope-check。

当前 `FeatureBuilder` 已支持：

- 基础总收益和 since inception 收益
- 1 月、3 月、6 月、1 年窗口收益
- 基准收益和窗口化超额收益
- 窗口化波动率与最大回撤
- 数据可用性计数和支持标记

窗口指标只会在净值历史长度足够时出现；默认短样例主要用于 smoke test，不代表完整历史场景。

## 真实模型接入

当前仓库已经支持单模型真实接入，按 OpenAI-compatible 方式配置：

- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL`
- `LLM_TIMEOUT_SECONDS`

DeepSeek 示例：

- `LLM_BASE_URL=https://api.deepseek.com`
- `LLM_MODEL=deepseek-v4-pro`

OpenCode Go / DeepSeek 示例保留在 `.env.example` 中。

也兼容旧字段：

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `DEFAULT_MODEL_NAME`

真实 demo 也支持直接读取 JSON 输入：

```bash
python3 scripts/run_real_demo.py examples/mock_input.json
```

如果你想直接落文件而不是只在终端看结果：

```bash
python3 scripts/run_real_demo.py examples/mock_input.json --output outputs/real_result.json
```

## 实施路线

建议先把当前版本作为第 0 版基线提交，然后按模块逐步增强。

- AI Agent 文档索引：`docs/README.md`
- 模块开发顺序与输入要求：`docs/implementation_plan.md`
- 当前已实现/部分完成/待做状态台账：`docs/ai_agent_development_log.md`
- 当前架构边界：`docs/architecture.md`
- 智能体模块架构设计：`docs/agent_architecture_design.md`
- 迁移范围说明：`docs/migration_notes.md`
- 输入输出契约说明：`docs/contracts.md`
- LLM 输出评估规则：`docs/llm_evaluation.md`
- golden cases 设计与判断标准：`docs/golden_cases.md`
- 本地环境与安装：`docs/environment_setup.md`
- OpenCode Go / DeepSeek 等 OpenAI-compatible provider 配置：`docs/provider_setup.md`
- 版本里程碑与切换方式：`docs/version_history.md`

后续判断某个 AI Agent 能力是否已经完成时，先看
`docs/ai_agent_development_log.md`，再对照代码、测试和运行验证。
`docs/README.md` 只作为文档导航，`docs/implementation_plan.md` 只作为后续规划来源，
`docs/version_history.md` 只作为里程碑/tag 历史来源。

## 当前设计原则

1. 先算结构化特征，再调用 LLM
2. LLM 负责解释，不替代底层数值计算
3. 每个 agent 单独测试，坏一块不影响其他块
4. 最终通过 chief agent 做综合结论
5. 当前 MVP 先共用一个 mock client，把全流程打通后再切真实模型
