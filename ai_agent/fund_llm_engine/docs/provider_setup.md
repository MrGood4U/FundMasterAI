# Provider Setup

## 推荐测试方式

团队联调默认先跑 mock mode，不需要 API key，也不依赖外网模型：

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/python scripts/run_mock_demo.py examples/mock_input.json
```

本模块要求 Python `>=3.11`。如果本机 `python3` 仍指向 Python 3.9，请优先使用
`.venv/bin/python` 或显式 `python3.11`。

真实模型测试通过环境变量切换 provider：

- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL`
- `LLM_TIMEOUT_SECONDS`
- `LLM_THINKING_MODE`
- `LLM_REASONING_EFFORT`

不要提交 `.env`，只提交 `.env.example`。

## 模型切换逻辑

推荐团队只申请 **一个 OpenAI-compatible 网关 Key**（例如 OpenCode Go），然后通过模型名切换，不需要逐厂商单独申请 key。

默认模型来自 `.env` 中的 `LLM_MODEL`。如果同一个 OpenAI-compatible 网关和 API key
支持多个模型，只需要改模型名，不需要换 `LLM_BASE_URL` 或 key。

OpenCode Go 推荐配置：

```env
LLM_API_KEY=your_opencode_key
LLM_BASE_URL=https://opencode.ai/zen/go/v1
LLM_MODEL=deepseek-v4-flash
# 可选：限制 demo / AI Insights 下拉可见模型
# LLM_ALLOWED_MODELS=deepseek-v4-flash,deepseek-v4-pro,glm-5.1
```

三种切换方式：

| 方式 | 操作 |
|------|------|
| 改默认 | 编辑 `.env` 的 `LLM_MODEL`，重启 agent 服务 |
| CLI 单次 | `run_real_demo.py ... --model deepseek-v4-pro` |
| 页面临时 | AI Insights 勾选 Real LLM → 下拉选模型 → Analyze |

模型列表来源：

- Agent 提供 `GET /api/ai/llm/models`
- 优先 live 拉取 `{LLM_BASE_URL}/models`
- 只返回当前 `LLMClient` 支持的 chat/completions 模型；MiniMax / Qwen 等 `/v1/messages` 模型不会出现在列表里

默认全局切换：

```env
LLM_BASE_URL=https://opencode.ai/zen/go/v1
LLM_MODEL=deepseek-v4-pro
```

单次命令行覆盖：

```bash
.venv/bin/python scripts/run_real_demo.py examples/mock_input.json \
  --model deepseek-v4-pro \
  --max-parallel-agents 1
```

单次 HTTP 请求覆盖：

```json
{
  "code": "000001",
  "mock": false,
  "llm_model": "deepseek-v4-pro",
  "max_parallel_agents": 1
}
```

如果请求里没有 `llm_model`，Agent 会继续使用 `.env` 里的默认 `LLM_MODEL`。

AI Insights 页面会在勾选 `Use real LLM` 后启用模型下拉框，并通过
`GET /api/ai/llm/models` 加载可选模型；分析请求会把选中的 `llm_model` 传给
`POST /api/ai/fund/analyze`。

## DeepSeek V4 示例

DeepSeek API 使用 OpenAI-compatible Chat Completions 格式。DeepSeek V4 的 `base_url`
保持不变，模型名推荐使用 `deepseek-v4-flash` 或 `deepseek-v4-pro`。

团队在中国大陆网络环境下测试时，建议先用 `deepseek-v4-flash`：

```env
LLM_API_KEY=your_deepseek_key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
LLM_TIMEOUT_SECONDS=60
LLM_THINKING_MODE=disabled
LLM_REASONING_EFFORT=
```

DeepSeek V4 默认开启 thinking mode。当前项目的 agent 输出只需要最终分析文本，
所以默认建议设置 `LLM_THINKING_MODE=disabled`，这样响应更快，也避免短输出额度被
reasoning 内容占用。

如果真实 provider 返回 `finish_reason=length` 且 `content` 为空，`LLMClient` 会
自动做一次保守 retry：扩大输出 token budget，并在已配置 thinking controls 时禁用
thinking。重试后仍为空会进入明确的 LLM error path，不再把
`API returned empty response` 当成正常 agent narrative。HTTP provider 错误也会
省略 raw response body，避免把 provider body 或敏感信息带到前端/日志说明里。

如果后续要测试复杂推理，可以改成：

```env
LLM_THINKING_MODE=enabled
LLM_REASONING_EFFORT=high
```

旧模型名 `deepseek-chat` 和 `deepseek-reasoner` 当前仍兼容，但官方已说明会在
2026-07-24 停用。新接入建议直接使用 `deepseek-v4-flash` 或 `deepseek-v4-pro`。

## 本地验证

```bash
.venv/bin/python scripts/run_real_demo.py examples/mock_input.json --max-parallel-agents 1
```

如果只想确认 provider 连通性，可以临时运行一个最小请求。不要把 key 写进命令历史或
提交到仓库；测试后建议在 provider 平台轮换已经暴露过的 key。
