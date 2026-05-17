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
- `docs/migration_notes.md`：迁移范围说明

## 目录

```text
fund-llm-engine/
├── docs/
├── src/fund_llm/
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

如果你要跑真实 Gemini demo，再补一份本地 `.env`：

```bash
cp .env.example .env
```

然后填写：

- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL`

当前默认推荐值已经写在 [.env.example](.env.example)：

- `LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/`
- `LLM_MODEL=gemini-3-flash-preview`

建好环境后，建议先做一轮最小验证：

```bash
source .venv/bin/activate
python3 -m unittest discover -s tests
python3 scripts/run_mock_demo.py
```

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

其中 `mock demo` 不需要联网，也不需要 API Key，会直接输出一份完整的分析结果 JSON。

当前 `FeatureBuilder` 已支持：

- 基础总收益和 since inception 收益
- 1 月、3 月、6 月、1 年窗口收益
- 基准收益和窗口化超额收益
- 窗口化波动率与最大回撤
- 数据可用性计数和支持标记

窗口指标只会在净值历史长度足够时出现；默认短样例主要用于 smoke test，不代表完整历史场景。

## 真实模型接入

当前仓库已经支持单模型真实接入，默认按 Gemini OpenAI-compatible 方式配置：

- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL`
- `LLM_TIMEOUT_SECONDS`

当前 `.env.example` 已经给出 Gemini 3 Flash 的默认示例：

- `LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/`
- `LLM_MODEL=gemini-3-flash-preview`

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

- 模块开发顺序与输入要求：`docs/implementation_plan.md`
- 当前架构边界：`docs/architecture.md`
- 智能体模块架构设计：`docs/agent_architecture_design.md`
- 迁移范围说明：`docs/migration_notes.md`
- 输入输出契约说明：`docs/contracts.md`
- LLM 输出评估规则：`docs/llm_evaluation.md`
- golden cases 设计与判断标准：`docs/golden_cases.md`
- 本地环境与安装：`docs/environment_setup.md`
- Gemini / DeepSeek 等模型 provider 配置：`docs/provider_setup.md`
- 版本里程碑与切换方式：`docs/version_history.md`

## 当前设计原则

1. 先算结构化特征，再调用 LLM
2. LLM 负责解释，不替代底层数值计算
3. 每个 agent 单独测试，坏一块不影响其他块
4. 最终通过 chief agent 做综合结论
5. 当前 MVP 先共用一个 mock client，把全流程打通后再切真实模型
