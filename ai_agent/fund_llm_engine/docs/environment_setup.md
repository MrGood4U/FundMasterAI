# Environment Setup

## 当前状态

这个仓库是一个独立的 Python 项目：

- 项目入口和依赖声明在 [pyproject.toml](../pyproject.toml)
- 当前要求 Python `>=3.11`
- 推荐给仓库单独创建 `.venv`

仓库不会提交虚拟环境目录，`.venv/` 已在 [.gitignore](../.gitignore) 中忽略。

## 创建环境

```bash
cd .
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 当前依赖

当前运行依赖：

- `openai>=1.12.0`
- `python-dotenv>=1.0.0`

这些依赖定义在 [pyproject.toml](../pyproject.toml:11)。

## 配置真实模型

如果你要跑真实 Gemini 模式，先复制环境变量模板：

```bash
cp .env.example .env
```

然后填写：

- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL`
- `LLM_TIMEOUT_SECONDS`

默认建议值在 [.env.example](../.env.example)：

- `LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/`
- `LLM_MODEL=gemini-3-flash-preview`

代码会在 [src/fund_llm/config.py](../src/fund_llm/config.py) 里自动读取这些变量。

如果团队需要在 Gemini 和 DeepSeek 之间切换，参考
[docs/provider_setup.md](./provider_setup.md)。

## 验证顺序

建好环境后，推荐按这个顺序验证：

```bash
source .venv/bin/activate
python3 -m unittest discover -s tests
python3 scripts/run_mock_demo.py
python3 scripts/inspect_agent_outputs.py
python3 scripts/run_real_demo.py examples/mock_input.json
python3 scripts/evaluate_analysis_output.py --input examples/mock_input.json --mode mock
python3 scripts/run_golden_suite.py --mode mock
```

如果最后一步报 `LLM API key is missing`，说明 `.env` 或环境变量还没配好。

如果你想直接把 demo 结果存成 JSON 文件，可以这样：

```bash
python3 scripts/run_mock_demo.py examples/mock_input.json --output outputs/mock_result.json
python3 scripts/run_real_demo.py examples/mock_input.json --output outputs/real_result.json
```
