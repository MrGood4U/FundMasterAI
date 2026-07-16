# Manual Acceptance Checklist

这份清单用于人工验收 AI Insights 页面和 AI Agent 链路。重点是：
用户从页面怎么点、看到什么才算符合预期，而不是只看单元测试是否通过。

## 0. 验收前置条件

- 在仓库根目录按当前 Docker 主线启动并完成 smoke：

```bash
docker compose up --build --wait
docker compose run --rm smoke
```

- 浏览器入口：`http://localhost:8080/ai-insights.html`。
- Docker 主线通过 Nginx 同源代理访问 Agent，浏览器不需要直接访问宿主机 `5003`。

验收前打开浏览器开发者工具的 Network 面板。点击 `Analyze` 后应看到
`POST /api/ai/fund/analyze` 返回 HTTP `200`；错误场景除外。

## 1. 页面初始状态

操作：

1. 打开 `AI Insights` 页面。
2. 不点击任何按钮，先看页面默认状态。

通过标准：

- 页面标题显示 `AI Fund Analysis`。
- 右上状态 chip 显示 `Ready`。
- 表单里能看到 `Fund code`、`Start date`、`Risk profile`、`Use real LLM`、`Analyze`。
- `Current Fund` 显示等待状态。
- `Agent Outputs` 表格显示 `No agent output yet.`。
- `Analysis Evidence` 显示等待采集证据。

## 2. 常规基金 mock 验收

操作：

1. `Fund code` 输入 `000001`。
2. `Start date` 选择或保留 `2025-01-01`。
3. `Risk profile` 选择 `Balanced`。
4. 不勾选 `Use real LLM`。
5. 点击 `Analyze`。

通过标准：

- 点击后状态先变成 `Running`，完成后变成 `Complete`。
- `Rating`、`Score`、`NAV points` 不再是 `--`。
- `LLM mode` 显示 `mock`。
- `Current Fund` 显示真实基金名称，不再是 `Waiting`。
- `Backend Data Coverage` 中 `Successful tools` 不为空。
- `Chief Summary`、`Why This Rating`、`Key Thesis`、`Main Risks`、`Action Plan` 都有内容。
- `Analysis Evidence` 至少包含这些步骤：
  - `Discovered backend tools`
  - `Loaded real fund history`
  - `Identified fund profile`
  - `Checked backend data coverage`
  - `Calculated fund metrics`
  - `Combined specialist views`
- `Agent Outputs` 至少能看到这些 agent：
  - `Performance`
  - `Portfolio Exposure`
  - `Bond Exposure`
  - `Risk Control`
  - `News Signal`
  - `Sector Context`
  - `Peer & Market Context`

常规基金的重点预期：

- `Bond Exposure` 应该是 `skipped + not_applicable`，因为混合或权益类基金不应做债券暴露分析。
- `Portfolio Exposure` 和 `Sector Context` 如果后端提供股票持仓和行业数据，应为 `success`；如果后端缺行业数据，可以是 `skipped + insufficient_data`，但不能是系统 error。

## 3. 债券基金路由验收

操作：

1. `Fund code` 输入 `003358`。
2. `Start date` 保持 `2025-01-01`。
3. `Risk profile` 选择 `Balanced` 或 `Conservative`。
4. 不勾选 `Use real LLM`。
5. 点击 `Analyze`。

通过标准：

- 页面完成后状态为 `Complete`。
- `Current Fund` 应显示类似 `易方达中债7-10年期国开行债券指数A`。
- `Backend Data Coverage` 的基金类型或 evidence 中能看出这是债券型 / `bond_index_fund`。
- `Portfolio Exposure` 应为 `skipped + not_applicable`。
- `Sector Context` 应为 `skipped + not_applicable`。
- 不能把债券基金硬讲成股票行业配置或权益行业暴露。

如果当前 market backend 已提供债券持仓和资产配置工具：

- `Bond Exposure` 应为 `success`。
- 它的 evidence 或表格详情应能支持债券暴露判断，例如债券持仓、前几大债券集中度、债券/现金/其他资产配置。
- `Missing fields` 不应包含 `bond_holdings` 和 `asset_allocation`。

如果当前 backend 还没有提供这些工具或 Agent 连到了旧 market backend：

- `Bond Exposure` 可以是 `skipped + insufficient_data`。
- `Missing fields` 可以包含 `bond_holdings`、`asset_allocation`。
- `Analysis Evidence` 的 `Checked backend data coverage` 应明确显示 `bond_holdings` 或 `asset_allocation` 是 `missing_backend_capability`。
- 这种情况算“降级逻辑通过”，但不算“完整债券持仓数据验收通过”。

## 4. 错误提示验收

操作：

1. 清空 `Fund code`。
2. 点击 `Analyze`。

通过标准：

- 页面状态变成 `Error`。
- `Current Fund` 或 summary 区域显示 `code is required` 或类似错误信息。
- 页面不能卡在 `Running`。

再测一个无数据基金：

1. `Fund code` 输入 `000002`。
2. 不勾选 `Use real LLM`。
3. 点击 `Analyze`。

通过标准：

- 如果后端没有 NAV，页面应显示 `Error`，错误信息指向无 NAV 或数据不足。
- 这不是 AI agent 失败，而是输入数据不足的预期错误路径。
- 如果后端返回少于 30 个可用 NAV 点，页面应显示 `INSUFFICIENT DATA` / `NOT RATED`，
  不能继续发布 BUY/HOLD/WATCH/AVOID 和数值分数。

## 5. 真实 LLM 验收（可选）

操作：

1. 确认 `ai_agent/fund_llm_engine/.env` 中已有真实
   `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`，并重建 Agent/Frontend 容器。
2. 页面输入 `003358` 或 `000001`。
3. 勾选 `Use real LLM`。
4. 点击 `Analyze`。

通过标准：

- `LLM mode` 显示 `real`。
- `Chief Summary` 和 agent narrative 不应是 `Mock LLM narrative...`。
- 如果 API key 缺失或模型服务不可用，页面应显示 `Error` 和清晰错误信息；这算环境配置未通过，不算页面交互失败。

## 6. 不通过判定

出现以下任意情况，应判定为不通过或需要返修：

- 点击 `Analyze` 后长期停留在 `Running`，没有成功或错误反馈。
- Network 中 `/api/ai/fund/analyze` 没有发出，或被 CORS 阻止。
- 债券基金 `003358` 被当成普通权益基金处理，`Portfolio Exposure` 或
  `Sector Context` 生成股票行业结论。
- 缺少后端数据时，页面仍让 LLM 编造债券持仓、久期、评级或行业配置。
- `Analysis Evidence` 为空，无法解释后端取数、指标计算、agent 检查和汇总过程。
- `Agent Outputs` 缺少当前核心 agent，尤其是 `Bond Exposure` 或
  `Peer & Market Context`。

## 7. 当前可接受的小瑕疵

- 如果某个非核心后端工具失败，但页面仍返回 `Complete`、主要分析可用，并且 `Errored tools` 或 evidence 里记录了失败工具，属于可接受的部分降级。
