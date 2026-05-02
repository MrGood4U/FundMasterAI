# Provider Setup

## 推荐测试方式

团队联调默认先跑 mock mode，不需要 API key，也不依赖外网模型：

```bash
python3 -m unittest discover -s tests
python3 scripts/run_mock_demo.py examples/mock_input.json
```

真实模型测试通过环境变量切换 provider：

- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL`
- `LLM_TIMEOUT_SECONDS`
- `LLM_THINKING_MODE`
- `LLM_REASONING_EFFORT`

不要提交 `.env`，只提交 `.env.example`。

## Gemini 示例

Gemini API 适合能稳定访问 Google AI Studio / Gemini API 的环境：

```env
LLM_API_KEY=your_gemini_key
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
LLM_MODEL=gemini-3-flash-preview
LLM_TIMEOUT_SECONDS=60
LLM_THINKING_MODE=
LLM_REASONING_EFFORT=
```

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

如果后续要测试复杂推理，可以改成：

```env
LLM_THINKING_MODE=enabled
LLM_REASONING_EFFORT=high
```

旧模型名 `deepseek-chat` 和 `deepseek-reasoner` 当前仍兼容，但官方已说明会在
2026-07-24 停用。新接入建议直接使用 `deepseek-v4-flash` 或 `deepseek-v4-pro`。

## 本地验证

```bash
python3 scripts/run_real_demo.py examples/mock_input.json --max-parallel-agents 1
```

如果只想确认 provider 连通性，可以临时运行一个最小请求。不要把 key 写进命令历史或
提交到仓库；测试后建议在 provider 平台轮换已经暴露过的 key。
