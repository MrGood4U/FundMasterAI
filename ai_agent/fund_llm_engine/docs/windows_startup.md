# AI Agent 服务 Windows 启动说明

> 可选的 Windows 原生调试说明：完整项目启动、课堂演示和提交验收优先使用仓库根
> 目录的 Docker Compose 文档。本文只说明在 Market、News 等依赖已经原生运行时，
> 如何单独启动 Agent（5003），不等同于完整项目启动步骤。

`fund_llm_engine/start.sh` 是 bash 脚本，Windows CMD 不能直接用，按下面步骤手动启动。

## 一、首次运行安装依赖

```bat
cd /d C:\Users\admin\Desktop\项目\code\new\FundMasterAI\ai_agent\fund_llm_engine
python -m pip install -e ".[backend,agent]"
```

只需要执行一次。要求 Python 3.11 及以上（`python --version` 确认）。

## 二、CMD 4：启动 AI Agent 服务（5003）

新闻后端如果按默认端口跑在 `5000`，直接：

```bat
cd /d C:\Users\admin\Desktop\项目\code\new\FundMasterAI\ai_agent\fund_llm_engine
set AGENT_DEBUG=false
set AGENT_RELOAD=false
python app.py
```

看到下面内容表示服务已启动：

```text
Running on http://127.0.0.1:5003
```

如果新闻后端跑在其他端口（例如 `5010`），启动前多设置一个环境变量：

```bat
set NEWS_BACKEND_URL=http://127.0.0.1:5010
```

## 三、验证

浏览器打开（GET 请求可以直接打开）：

```text
http://127.0.0.1:5003/health
```

返回 JSON 且 `message` 是 `agent backend ok` 即成功。分析接口是 POST，
用另一个 CMD 验证 mock 模式（不消耗 LLM 额度）：

```bat
curl -s -X POST http://127.0.0.1:5003/api/ai/fund/analyze -H "Content-Type: application/json" -d "{\"code\":\"000001\",\"start_date\":\"2025/01/01\",\"mock\":true}"
```

三个分析接口（契约详见 [`contracts.md`](./contracts.md)）：

```text
POST /api/ai/fund/analyze        单基金多智能体分析
POST /api/ai/portfolio/analyze   组合层分析（净值合成 + 持仓穿透）
POST /api/ai/sector/analyze      多基金行业横向比较
```

## 四、真实 LLM 模式（可选）

mock 模式已经使用真实后端数据，只有总评文本是固定的。要跑真实 LLM：

1. 在 `ai_agent\fund_llm_engine` 下复制 `.env.example` 为 `.env`；
2. 填入 `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`（`.env` 不要提交仓库）；
3. 重启 AI Agent 服务，请求里把 `"mock"` 改成 `false`。

## 五、常见问题

- **接口返回 500 且日志出现 `Connection refused`**：market_backend（5001）没启动，
  先按 `backend/README.md` 启动所需后端。
- **`422`**：不是系统错误，是该基金数据不足（例如 `000002` 无 NAV），属于预期行为。
- **停止服务**：在本 CMD 窗口按 `Ctrl+C`。
