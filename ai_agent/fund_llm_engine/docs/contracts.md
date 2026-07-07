# AI Agent API 契约

本文档定义 AI Agent / LLM 层对前端和队友后端暴露的稳定接口契约。
队友接前端页面、做联调、或以后新增 Agent 时，优先看这份文档。

字段名、接口路径、状态值保持英文，因为它们是代码和 JSON 里的真实字段；
解释说明以中文为主，方便团队沟通。

当前实现状态请看 [`ai_agent_development_log.md`](./ai_agent_development_log.md)。
后续规划请看 [`implementation_plan.md`](./implementation_plan.md)。

## 兼容规则

- 当前公开 AI 分析接口是 `POST /api/ai/fund/analyze`（单基金）、
  `POST /api/ai/portfolio/analyze`（组合层，见「组合层分析接口」一节）、
  `POST /api/ai/sector/analyze`（行业层，见「行业层比较接口」一节）和
  `POST /api/ai/news/summary`（新闻摘要，见「新闻摘要接口」一节）。
- 成功响应的顶层结构固定为 `code`、`data`、`coverage`、`message`。
- 前端可以长期依赖本文档列出的稳定字段。
- 后续可以新增字段、新增 `metadata` key、新增 `analysis_trace` 事件，或在
  `agent_outputs` 里追加新的 Agent 结果。
- 未经迁移说明，不要改名、删除、或改变已有稳定字段的类型。
- 新增 Agent 必须是增量式的：只往 `data.agent_outputs` 追加同结构对象。
- LLM API key 等运行时密钥不属于接口契约，不能写进请求、响应或仓库文件。

## 接口

```text
POST /api/ai/fund/analyze
Content-Type: application/json
```

这个接口接收前端传来的轻量请求，然后由 AI 服务通过后端 function registry
获取真实基金数据，组装 `FundAnalysisInput`，最后运行 mock LLM 或真实 LLM
分析流程。

### 请求字段

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|---|---:|---:|---|---|
| `code` | string | 是 | - | 基金代码。也兼容 `fund_code` 作为别名。 |
| `start_date` | string | 否 | 后端或默认窗口 | 分析开始日期，会传给后端数据加载逻辑。 |
| `end_date` | string | 否 | 后端或默认窗口 | 分析结束日期，会传给后端数据加载逻辑。 |
| `fund_name` | string | 否 | 空字符串 | 后端基础信息缺失时的基金名称兜底。 |
| `client_risk_profile` | string | 否 | `balanced` | 用户风险偏好，会进入分析上下文。 |
| `mock` | boolean/string | 否 | `LLM_MOCK_MODE` 或 `false` | 为真时跑 mock LLM 模式。 |
| `max_nav_points` | integer | 否 | `260` | 最多请求多少个净值点。 |
| `portfolio_year` | string/integer | 否 | 当前年/上一年兜底 | 用于请求持仓数据。 |
| `top_holdings_n` | integer | 否 | `10` | 最多请求多少条前十大持仓。 |
| `max_news_items` | integer | 否 | `8` | 最多使用多少条新闻或公告。 |
| `max_parallel_agents` | integer | 否 | `6` | specialist agents 并发数量。 |
| `llm_timeout_seconds` | integer | 否 | `LLM_TIMEOUT_SECONDS` 或 `60` | 真实 LLM 模式的超时时间。 |
| `llm_model` | string | 否 | `.env` 中的 `LLM_MODEL` | 真实 LLM 模式下，单次分析覆盖默认模型。也兼容 `model` 别名。 |
| `model` | string | 否 | 同 `llm_model` | `llm_model` 的兼容别名。 |

最小请求示例：

```json
{
  "code": "000001",
  "start_date": "2025/01/01",
  "mock": true
}
```

真实模型单次切换示例：

```json
{
  "code": "000001",
  "mock": false,
  "llm_model": "deepseek-v4-pro",
  "max_parallel_agents": 3
}
```

## 组合层分析接口

```text
POST /api/ai/portfolio/analyze
Content-Type: application/json
```

组合层分析：AI 服务为每只成分基金拉取 NAV 和基本信息，
按「日期交集对齐 + 固定权重每日再平衡」合成组合净值（组合每日收益 =
各成分当日收益的加权平均，逐日复利），在合成净值上计算组合层量化指标，
再做持仓穿透（Level 2：合并各基金披露的前十大持仓 / 行业配置 / 资产配置，
发现重叠暴露和组合级集中度），最后由组合版 Chief 生成总评。
设计给前端 portfolio / overview 页消费，不要求堆进 AI Insights 单基金页。

### 请求字段

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|---|---:|---:|---|---|
| `positions` | array | 是 | - | 成分基金列表，每项 `{code, weight}`。`weight` 必须为正数，权重和不为 1 时会按比例归一化（`60/40` 与 `0.6/0.4` 等价）。也兼容 `funds` 作为别名。 |
| `start_date` | string | 否 | 后端或默认窗口 | 分析开始日期，会传给每只基金的 NAV 加载。 |
| `end_date` | string | 否 | 后端或默认窗口 | 分析结束日期。 |
| `client_risk_profile` | string | 否 | `balanced` | 用户风险偏好。 |
| `mock` | boolean/string | 否 | `LLM_MOCK_MODE` 或 `false` | 为真时跑 mock LLM 模式。 |
| `max_nav_points` | integer | 否 | `520` | 每只基金最多使用多少个净值点（无显式 `start_date` 时截尾）。 |
| `include_lookthrough` | boolean/string | 否 | `true` | 是否拉取并计算持仓穿透（Level 2）。设为 `false` 时只做净值层分析，减少后端调用。 |
| `top_holdings_n` | integer | 否 | `10` | 穿透时每只基金纳入的持仓条数上限。 |
| `llm_timeout_seconds` | integer | 否 | `LLM_TIMEOUT_SECONDS` 或 `60` | 真实 LLM 模式的超时时间。 |
| `llm_model` | string | 否 | `.env` 中的 `LLM_MODEL` | 真实 LLM 模式下单次覆盖默认模型。也兼容 `model` 别名。 |

最小请求示例（另见 `examples/portfolio_input_demo.json`）：

```json
{
  "positions": [
    {"code": "000001", "weight": 60},
    {"code": "003358", "weight": 40}
  ],
  "start_date": "2025/01/01",
  "mock": true
}
```

### 成功响应

顶层结构与单基金接口一致：`code`、`data`、`coverage`、`message`。

`data` 的稳定字段（与 `FinalAnalysisResult` 同名字段语义一致，前端可复用渲染逻辑）：

| 字段 | 类型 | 说明 |
|---|---:|---|
| `request_id` | string | 本次组合分析请求 id。 |
| `overall_rating` | string | `buy` / `hold` / `watch` / `avoid`。 |
| `overall_score` | number | 0-100 组合层确定性评分。 |
| `summary` | string | 组合总评（真实模式为 LLM 解释，失败时回退确定性摘要）。 |
| `score_explanation` | string | 评分如何由合成净值指标算出的确定性解释。 |
| `key_thesis` / `main_risks` / `action_plan` | string[] | 组合层要点、风险、建议。 |
| `quant_metrics` | object | 组合层量化指标，见下。 |
| `constituents` | array | 每只成分基金在共同窗口上的对比指标，见下。 |
| `holdings_lookthrough` | object | 持仓穿透（Level 2），见「持仓穿透字段」。 |
| `industry_lookthrough` | object | 行业穿透（组合加权行业暴露），见「持仓穿透字段」。 |
| `asset_allocation_lookthrough` | object | 股/债/现金资产配置合并，见「持仓穿透字段」。 |
| `missing_fields` | string[] | 组合路径当前恒为空数组（NAV 缺失会直接 `422`；穿透数据缺失以各 lookthrough 的 `status` 表达，不静默降级）。 |
| `metadata` | object | 执行元数据，含 `analysis_level=portfolio`、`fund_count`、`shared_nav_points`、`weights_rescaled`、`llm_mode`、`quant_metrics_reliability` 等。 |
| `analysis_trace` | `AnalysisTraceEvent[]` | 证据链：取数、日期对齐、净值合成、组合汇总。 |

`data.quant_metrics` 在单基金 A 类指标（`total_return`、`annualized_return`、
`annualized_volatility`、`max_drawdown`、`sharpe_ratio`、`sortino_ratio`、
`calmar_ratio`、`positive_period_ratio`、`sample_size`，另含可用窗口的
`return_1m/3m/6m/1y` 等滚动指标）之外，新增两个组合特有字段：

| 字段 | 类型 | 说明 |
|---|---:|---|
| `weighted_average_volatility` | number | 成分基金年化波动率按权重的线性平均。 |
| `diversification_benefit` | number | 线性平均波动率减组合实际波动率。固定权重每日再平衡下恒 ≥ 0：成分相关性越低数值越大，完全同涨同跌时为 0，即分散化收益。 |

`constituents` 每项字段：`code`、`name`、`fund_type`、`normalized_fund_type`、
`weight`（归一化后）、`nav_points`、`total_return`、`annualized_return`、
`annualized_volatility`、`max_drawdown`、`sharpe_ratio`。所有成分指标都在
同一个共同日期窗口上计算，可直接横向比较。

### 持仓穿透字段（Level 2）

三个 lookthrough 对象都有统一的状态语义：

| `status` | 含义 |
|---|---|
| `available` | 所有成分基金都提供了该类数据。 |
| `partial` | 部分基金有数据；`funds_without_data` 列出缺数据的基金（债券基金没有股票持仓属于正常情况）。 |
| `missing` | 没有任何基金提供该类数据；数值字段为空或 0，不伪造。 |

`holdings_lookthrough`（每条持仓对组合的贡献 = 基金权重 × 持仓占基金净值比例）：

| 字段 | 说明 |
|---|---|
| `disclosure_basis` | 固定为 `quarterly_top10_holdings`：公募季报只披露前十大持仓，这是部分穿透。 |
| `top_holdings` | 合并后的组合真实重仓，按组合权重排序；每项含 `stock_code`、`stock_name`、`portfolio_weight`、`held_by`（哪些基金持有及占各自净值比例）。 |
| `overlapping_holdings` | 被 2 只及以上成分基金同时持有的股票，用于发现隐性重叠集中。 |
| `combined_top_weight` | 穿透后前十大合计占组合比例。 |
| `disclosed_weight_total` | 全部已披露持仓合计占组合比例，其余仓位不可见。 |

`industry_lookthrough`：`aggregate_exposure`（组合加权行业暴露）、
`top_sectors`、`top_sector_weight`、`per_fund_exposure`（per-fund 明细，
供前端做横向比较）。

`asset_allocation_lookthrough`：`aggregate_allocation`（原始资产类别合并）与
`buckets`（`stock` / `bond` / `cash` / `other` 四桶归类）。

对应的 `metadata` 新增 `holdings_lookthrough_status`、
`industry_lookthrough_status`、`asset_allocation_lookthrough_status`；
`analysis_trace` 新增 `Merged constituent holdings look-through` 事件。
组合请求可传 `include_lookthrough: false` 跳过穿透取数（默认 `true`），
`top_holdings_n`（默认 `10`）控制每只基金纳入的持仓条数。

组合接口的 `coverage` 字段：

| 字段 | 类型 | 说明 |
|---|---:|---|
| `fund_count` | integer | 成分基金数量。 |
| `funds` | array | 每只基金的 `code`、`fund_name`、`fund_type`、`normalized_fund_type`、`weight`、`nav_points`。 |
| `weights_rescaled` | string | `"true"` 表示输入权重和不为 1，已按比例归一化。 |
| `data_source` / `available_backend_tools` / `successful_backend_tools` / `errored_backend_tools` | string | 与单基金接口同语义。 |

### 组合接口错误语义

| HTTP | 触发条件 |
|---|---|
| `400` | 缺少 `positions` 或列表为空。 |
| `422` | 权重非正数、基金代码重复、任一成分基金拉不到 NAV（报错信息会列出失败代码）、共同交易日不足 30 个。 |
| `500` | 未预期异常。 |

防幻觉原则与单基金一致：任何成分基金数据缺失都会显式失败并说明原因，
不会静默丢弃基金或让 LLM 编造缺失部分。

## 行业层比较接口

```text
POST /api/ai/sector/analyze
Content-Type: application/json
```

行业层视图（Phase B1）：把多只基金的行业暴露聚合成横向比较矩阵，回答
"这几只基金在行业上怎么分布、哪里撞车"。不需要 NAV，每只基金只取
基本信息（判断基金类型）和行业配置。设计给前端行业 / sector 页消费。

行业状态语义与单基金 `SectorAgent` 一致：债券/货币基金为
`not_applicable`，权益基金缺行业数据为 `insufficient_data`，
都不会被编造行业结论。

### 请求字段

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|---|---:|---:|---|---|
| `codes` | array | 是 | - | 基金代码列表，例如 `["161725", "000001"]`。也兼容 `funds`（可以是代码或 `{code}` 对象数组）。代码不能重复。 |
| `mock` | boolean/string | 否 | `LLM_MOCK_MODE` 或 `false` | 为真时跑 mock LLM 模式。 |
| `llm_timeout_seconds` | integer | 否 | `LLM_TIMEOUT_SECONDS` 或 `60` | 真实 LLM 模式超时。 |
| `llm_model` | string | 否 | `.env` 中的 `LLM_MODEL` | 真实模式单次覆盖模型。也兼容 `model` 别名。 |

### 成功响应

顶层结构同样是 `code`、`data`、`coverage`、`message`。`data` 稳定字段：

| 字段 | 类型 | 说明 |
|---|---:|---|
| `request_id` | string | `sector-view-<codes>`。 |
| `status` | string | `available` / `partial` / `missing`，语义同组合穿透。 |
| `funds` | array | 每只基金一行：`code`、`name`、`fund_type`、`normalized_fund_type`、`sector_status`（`available` / `insufficient_data` / `not_applicable`）、`sector_count`、`top_sector`、`top_sector_weight`、`top_sectors`（前 3）。 |
| `sector_matrix` | array | 行业比较矩阵，按平均暴露降序；每行含 `sector`、`exposures`（fund_code → 占比）、`funds_holding`、`average_weight`（对有数据的基金等权平均）、`max_weight`、`max_fund`。 |
| `sector_total_count` | integer | 全部行业数（矩阵默认只返回前 15 行）。 |
| `common_sectors` | string[] | 被 2 只及以上基金共同持有的行业。 |
| `funds_with_data` / `funds_without_data` | string[] | 有 / 无可用行业数据的基金代码。 |
| `summary` | string | 行业比较总评（真实模式 LLM 解释，失败回退确定性摘要）。 |
| `metadata` | object | 含 `analysis_level=sector`、`sector_view_status`、`summary_source`、`llm_mode` 等。 |
| `analysis_trace` | array | 矩阵构建与总评两个事件。 |

注意：`sector_matrix.average_weight` 是对提供了行业数据的基金做**等权**平均
（横向比较口径）；如果要按用户组合权重加权的行业暴露，用组合接口的
`industry_lookthrough`。

### 错误语义

| HTTP | 触发条件 |
|---|---|
| `400` | 缺少 `codes` 或列表为空。 |
| `422` | 基金代码重复或为空字符串。 |
| `500` | 未预期异常。 |

## 新闻摘要接口

```text
POST /api/ai/news/summary
Content-Type: application/json
```

给 News 页 AI Summary 组件用：前端把从 news backend 拿到的新闻行**原样转发**
即可（`news_title` / `news_content` / `publish_time` / `文章来源` 等中英文字段
都能识别），AI 服务不重复取数。

防幻觉分工与其他接口一致：逐条情绪标签由确定性关键词规则打出（复用
`SentimentAgent` 分类器），整体 label / 计数 / 置信度全部代码计算；LLM 只把
已分类的新闻写成摘要，失败时回退确定性摘要；**`related_symbols` 只回传请求里
给的 `symbol`，不会让模型从文本里编造股票代码**。

### 请求字段

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|---|---:|---:|---|---|
| `items` | array | 是 | - | 新闻行列表，每行至少要有标题或正文。兼容 `news` 别名。 |
| `symbol` | string | 否 | 空 | 查询这些新闻用的标的代码，会原样回传到 `related_symbols`。兼容 `code` 别名。 |
| `max_items` | integer | 否 | `10` | 最多纳入多少条（硬上限 20，超出截断）。 |
| `mock` | boolean/string | 否 | `LLM_MOCK_MODE` 或 `false` | 为真时跑 mock LLM 模式。 |
| `llm_timeout_seconds` / `llm_model` | - | 否 | 同其他接口 | 真实模式超时与单次模型覆盖。 |

请求示例（`items` 就是 `get_recent_news` 的原始返回行）：

```json
{
  "symbol": "300059",
  "items": [
    {"news_title": "...", "news_content": "...", "publish_time": "...", "文章来源": "..."}
  ],
  "mock": true
}
```

### 成功响应

顶层结构同样是 `code`、`data`、`coverage`、`message`。`data` 稳定字段：

| 字段 | 类型 | 说明 |
|---|---:|---|
| `request_id` | string | `news-summary-<symbol>-<n>`。 |
| `status` | string | 当前恒为 `success`（无可用新闻会直接 `422`）。 |
| `summary` | string | 新闻摘要（真实模式 LLM 生成，失败回退确定性摘要，英文）。 |
| `sentiment` | object | `label`（`positive`/`negative`/`neutral`/`mixed`）+ `positive_count` / `negative_count` / `neutral_count` / `risk_event_count`，全部确定性计算。 |
| `confidence` | number | 0.4-0.9，按条数、正文长度、时间与来源齐全度计算。 |
| `related_symbols` | string[] | 只包含请求传入的 `symbol`，未传则为空数组。 |
| `items_analyzed` | integer | 实际纳入的条数。 |
| `item_signals` | array | 逐条 `{title, sentiment, risk_event}`，前端可直接做每条新闻的情绪角标。 |
| `metadata` | object | `analysis_level=news`、`llm_mode`、`summary_source`、`prompt_version` 等。 |
| `analysis_trace` | array | 两个事件：确定性分类、摘要生成。 |

`coverage`：`items_received` / `items_used` / `has_symbol` / `data_source`。

### 错误语义

| HTTP | 触发条件 |
|---|---|
| `400` | 缺少 `items` 或不是非空数组。 |
| `422` | `items` 里没有任何一行有标题或正文。 |
| `500` | 未预期异常（对外通用文案，详情看服务日志）。 |

## 模型目录接口

```text
GET /api/ai/llm/models
```

用于前端或联调工具获取当前 gateway 下可选模型列表。不会返回 API key。

成功响应示例：

```json
{
  "code": 200,
  "data": {
    "default_model": "deepseek-v4-flash",
    "provider": "opencode-go",
    "base_url": "https://opencode.ai/zen/go/v1",
    "models": [
      {"id": "deepseek-v4-flash", "label": "DeepSeek V4 Flash"},
      {"id": "deepseek-v4-pro", "label": "DeepSeek V4 Pro"}
    ],
    "source": "live"
  },
  "message": "success"
}
```

`source` 取值：

- `live`：从 `{LLM_BASE_URL}/models` 拉取并与 chat/completions 兼容 allowlist 求交集
- `static`：网关不可达时回退到内置静态列表

## 成功响应

分析成功时返回 HTTP `200`：

```json
{
  "code": 200,
  "data": {},
  "coverage": {},
  "message": "success"
}
```

### 顶层稳定字段

| 字段 | 类型 | 说明 |
|---|---:|---|
| `code` | integer | 应用层状态码。成功时为 `200`。 |
| `data` | object | `FinalAnalysisResult`，前端主分析内容从这里渲染。 |
| `coverage` | object | 本次分析的数据覆盖情况和后端数据来源摘要。 |
| `message` | string | 人类可读的状态说明。 |

## `data`: FinalAnalysisResult

`data` 是前端最主要消费的 AI 分析结果。

| 字段 | 类型 | 稳定 | 说明 |
|---|---:|---:|---|
| `request_id` | string | 是 | 本次分析的内部请求 id。 |
| `overall_rating` | string | 是 | 最终评级，例如 `buy`、`hold`、`watch`、`avoid`。 |
| `overall_score` | number | 是 | 最终 0-100 分。 |
| `summary` | string | 是 | 最终综合分析摘要。 |
| `score_explanation` | string | 是 | 用确定性文本解释最终评分和评级怎么来的。 |
| `key_thesis` | string[] | 是 | 主要支持理由或核心判断。 |
| `main_risks` | string[] | 是 | 主要风险和限制。 |
| `action_plan` | string[] | 是 | 建议关注或采取的后续动作。 |
| `agent_outputs` | `AgentOutput[]` | 是 | 各 specialist Agent 的分析结果。这个数组以后只追加，不破坏旧结构。 |
| `analysis_trace` | `AnalysisTraceEvent[]` | 是 | 证据链，解释后端取数、指标计算、Agent 检查、Chief 汇总过程。 |
| `missing_fields` | string[] | 是 | 本次分析缺失或覆盖不足的字段。 |
| `metadata` | object | 是 | 执行元数据。以后可以新增 key。 |
| `quant_metrics` | object | 是 | 只依赖净值的量化指标（收益、波动率、Sharpe 等），前端可直接做指标卡。 |

前端应当忽略自己不认识的额外字段，不要因为新增字段而报错。

## `data.quant_metrics`

`quant_metrics` 是只依赖基金净值序列的量化指标（A 类指标），对任何基金类型都成立，
不需要个股交易记录。前端可以直接用它渲染指标卡（dials），不必再从 `key_points` 文本里解析数字。

| 字段 | 类型 | 说明 |
|---|---:|---|
| `total_return` | number | 区间总收益率，小数表示，例如 `0.08` 表示 8%。 |
| `annualized_return` | number | 年化收益率。净值点很少时会被放大，仅在足够长的历史下有意义。 |
| `annualized_volatility` | number | 年化波动率。 |
| `max_drawdown` | number | 最大回撤，负数。 |
| `sharpe_ratio` | number | 夏普比率，使用约 2% 的年化无风险利率假设。 |
| `sortino_ratio` | number | 索提诺比率，只惩罚下行波动。 |
| `calmar_ratio` | number | 年化收益除以最大回撤绝对值。 |
| `positive_period_ratio` | number | 上涨交易日占比，取值 0-1，作为“胜率”的净值版近似。 |
| `excess_return` | number | 仅在提供基准净值序列时出现，等于基金区间收益减基准区间收益。 |
| `sample_size` | number | 计算这些指标所用的净值点数量，用于判断年化指标是否基于足够样本。 |

`excess_return` 属于需要基准数据的 B 类指标，只有传入 `benchmark_nav_series` 时才会出现，
没有基准时不会伪造该字段。其余字段只要有净值就会返回。依赖个股交易记录的指标（如成交胜率、
盈亏比）和个股估值指标（如 PE/PB）不属于这里，因为基金作为被分析标的没有这些原料。

### 样本量与可靠性

年化类指标（`annualized_return`、`sharpe_ratio`、`sortino_ratio`、`calmar_ratio`）需要足够长的
净值历史才可靠。净值点不足一年（约 252 个交易日）时，这些指标会被显著放大。因此结果同时提供：

- `data.quant_metrics.sample_size`：本次使用的净值点数量。
- `data.metadata.quant_metrics_sample_size`：同一数量的字符串形式。
- `data.metadata.quant_metrics_reliability`：可靠性标签，取值 `high`（≥252 点）、
  `medium`（≥120 点）、`low`（更少）。

前端建议在 `reliability` 为 `medium` 或 `low` 时，对年化指标加“样本不足”提示或弱化展示，
而不是直接把可能失真的数值当成可信结论。指标值本身不会被改写，只附带可靠性说明。

## `agent_outputs`: AgentOutput

现在和未来的 specialist Agent 都必须返回同一套结构。这样前端可以做通用
`AgentCard` 或 `AgentTableRow`，未来新增 Agent 时自然多展示一项。

| 字段 | 类型 | 可为空 | 说明 |
|---|---:|---:|---|
| `agent_name` | string | 否 | 稳定机器名，例如 `PerformanceAgent`。 |
| `status` | string | 否 | 执行状态，见下方状态语义。 |
| `stance` | string | 否 | Agent 立场、判断方向，或 skipped 原因。 |
| `score` | number | 是 | `status=success` 时为 0-100 分；skipped/error 时通常为 `null`。 |
| `confidence` | number | 否 | 0-1 置信度。 |
| `key_points` | string[] | 否 | 主要证据点。 |
| `risks` | string[] | 否 | 该 Agent 发现的风险或限制。 |
| `recommendations` | string[] | 否 | 该 Agent 给出的建议。 |
| `narrative` | string | 否 | LLM 或确定性逻辑生成的 Agent 说明文本。 |

### 当前 Agent 名称

| `agent_name` | 建议展示名 |
|---|---|
| `PerformanceAgent` | Performance Check / 收益表现检查 |
| `ExposureAgent` | Exposure Check / 持仓暴露检查 |
| `BondExposureAgent` | Bond Exposure Check / 债券暴露检查 |
| `RiskAgent` | Risk Check / 风险检查 |
| `SentimentAgent` | News / Sentiment Check / 新闻情绪检查 |
| `SectorAgent` | Sector Check / 行业配置检查 |
| `MarketAgent` | Peer / Market Context / 同类与市场对比 |

`MarketAgent` 的证据是后端的同类比较（`get_fund_individual_analysis`，
percentile 表示优于百分之多少的同类基金）和持有期盈利概率
（`get_fund_profit_probability`）。两类数据都缺失时输出
`skipped + insufficient_data`。资金流视角（CapitalFlowAgent）因上游暂无
数据源未接入，属于依赖上游数据的未来扩展。

`ChiefAgent` 当前负责把各 Agent 结果汇总到 `data` 的最终字段里，不要求作为
普通 `agent_outputs` 项出现。

未来如果新增 `MarketAgent`、`CapitalFlowAgent` 或其他 specialist agent，
也必须使用同样的 `AgentOutput` 结构。前端遇到不认识的 `agent_name` 时，
可以直接显示原始名称，或在本地 label map 里补一个展示名。

## 状态语义

`status` 表示 Agent 执行结果：

| `status` | 含义 | 前端建议展示 |
|---|---|---|
| `success` | Agent 正常完成，`score` 有意义。 | 正常完成状态。 |
| `skipped` | Agent 主动跳过，不参与打分。 | 不是系统失败，需要看 `stance`。 |
| `error` | Agent 异常失败。 | 真正错误状态。 |

重要 `stance` 组合：

| `status` + `stance` | 含义 |
|---|---|
| `success` + `positive` | Agent 看到偏正面的信号。 |
| `success` + `neutral` | Agent 看到中性或平衡信号。 |
| `success` + `negative` | Agent 看到偏弱或偏风险的信号。 |
| `skipped` + `insufficient_data` | 这个 Agent 理论上适用，但当前数据不足。 |
| `skipped` + `not_applicable` | 这个 Agent 对当前基金类型不适用。例如债券指数基金不做权益行业分析。 |
| `error` + 任意 stance | Agent 执行异常。当前兜底 `stance` 可能是 `mixed`。 |

前端不要把 `skipped + insufficient_data` 或 `skipped + not_applicable`
当成 `error`。它们是“谨慎跳过”，不是“系统坏了”。

## `analysis_trace`: AnalysisTraceEvent

`analysis_trace` 是证据链，用来解释这次结果是怎么来的。它适合给前端做
“Analysis Evidence”“诊断详情”“调试面板”等展示。

| 字段 | 类型 | 稳定 | 说明 |
|---|---:|---:|---|
| `category` | string | 是 | 步骤类别，例如 `backend`、`feature`、`agent`、`aggregation`。 |
| `title` | string | 是 | 人类可读的步骤标题。 |
| `detail` | string | 是 | 人类可读的步骤说明。 |
| `status` | string | 是 | trace 状态，通常是 `success`、`warning`、`error`。 |
| `evidence` | object | 是 | 前端可展示的证据摘要。不同事件 key 可以不同。 |
| `technical` | object | 是 | 给开发者看的调试信息。不同事件 key 可以不同。 |

兼容规则：以后可以新增 trace 事件，也可以在 `evidence` / `technical` 里新增
key，但现有稳定字段类型不要变。

## `coverage`

`coverage` 位于顶层，不在 `data` 里面。它总结本次分析从后端拿到了哪些数据、
哪些数据缺失、哪些数据对当前基金类型不适用。

| 字段 | 类型 | 说明 |
|---|---:|---|
| `nav_points` | integer | 本次使用的净值点数量。 |
| `has_top_holdings_weight` | boolean | 是否拿到前十大持仓集中度。 |
| `has_industry_exposure` | boolean | 是否拿到行业暴露数据。 |
| `has_bond_holdings` | boolean | 是否拿到债券持仓明细。 |
| `has_asset_allocation` | boolean | 是否拿到资产配置结构。 |
| `has_news_items` | boolean | 是否拿到结构化新闻或公告。 |
| `fund_name` | string | 后端返回或兜底的基金名称。 |
| `fund_type` | string | 后端返回的原始基金类型。 |
| `normalized_fund_type` | string | AI 路由归一化后的基金类型。 |
| `fund_family` | string | 用于适用性判断的大类基金族。 |
| `data_coverage` | object | 各数据类别的覆盖情况。 |
| `data_source` | string | 数据来源标记，通常是 backend function registry。 |
| `available_backend_tools` | string | 发现到的后端工具名，逗号分隔。 |
| `successful_backend_tools` | string | 成功调用的后端工具名，逗号分隔。 |
| `errored_backend_tools` | string | 调用失败的后端工具名，逗号分隔。 |

常见 `coverage.data_coverage` 值：

| 值 | 含义 |
|---|---|
| `available` | 数据存在且可用。 |
| `missing` | 必要输入缺失。 |
| `missing_backend_capability` | 当前后端还没有稳定提供这类数据。 |
| `not_applicable` | 这类数据对当前基金类型不适用。 |

常见数据类别包括 `nav`、`fund_type`、`stock_holdings`、
`industry_exposure`、`bond_holdings`、`asset_allocation`、`news`、
`benchmark`。

## 错误响应

已知失败也保持类似的顶层 JSON 风格。

### 缺少基金代码

HTTP `400`：

```json
{
  "code": 400,
  "data": null,
  "message": "code is required"
}
```

### 数据不足或校验失败

HTTP `422`：

```json
{
  "code": 422,
  "data": null,
  "message": "No NAV data returned for fund 000002"
}
```

`422` 表示请求格式大体没问题，但当前无法完成分析。常见原因包括：

- 后端没有返回足够 NAV 数据；
- 当前基金代码在后端不可用；
- 真实 LLM 模式缺少必要运行时配置，例如 `LLM_API_KEY`。

### 未预期异常

HTTP `500`：

```json
{
  "code": 500,
  "data": null,
  "message": "Internal error while running fund analysis. Check the Agent service log for details."
}
```

`500` 对外只返回通用错误说明，不回传 raw exception 文本；完整堆栈只写入
Agent 服务日志（`app.log`），排查时看日志而不是接口响应。

## 内部输入对象

HTTP 接口会先构造 `FundAnalysisInput`，再交给 engine。脚本和测试也可以直接
使用这个对象。

### 必填字段

- `request_id`
- `fund_info.code`
- `fund_info.name`
- `fund_info.asset_type`
- `nav_series`

### 可选字段

- `industry_exposure`
- `top_holdings_weight`
- `bond_holdings`
- `asset_allocation`
- `news_summary`
- `news_items`
- `analysis_window`
- `benchmark`
- `benchmark_nav_series`
- `fund_tags`
- `operational_metrics`
- `extra_context`

如果有结构化新闻，`news_items` 建议包含 `title`、`summary`、`published_at`、
`source`、`topic`、`sentiment_label`。

如果有债券持仓，`bond_holdings` 建议包含 `bond_code`、`bond_name`、`pct`、
`hold_market_value`、`quarter` 等后端可稳定提供的字段。`asset_allocation`
建议使用资产类型到占比的对象，例如 `{"债券": 0.86, "现金": 0.07}`；百分比
字符串也会被归一化为 0-1 的比例。

## 前端交接样例

下面这些 case 用于测试页面状态。它们依赖实时后端数据，后端能力变化后需要重新验证。

| Case | 用途 |
|---|---|
| `000001` | 正常混合基金 demo，适合测试真实后端数据和新闻公告流。 |
| `003358` | 债券指数基金，适合测试 `BondExposureAgent` success、权益类检查 `skipped + not_applicable`、以及资产配置缺失降级。 |
| `000002` | 预期无 NAV 或数据不足，通常用于测试 HTTP `422`。 |
| `161725` | 行业高度集中的权益/指数基金，适合测试 `SectorAgent` success。 |
| Sparse/no-news sample | 无新闻或低信息样例，适合测试 `SentimentAgent` 的 `skipped + insufficient_data`。 |

## 本地验证

在 `ai_agent/fund_llm_engine` 下运行：

```bash
python3 -m unittest discover -s tests
python3 scripts/run_mock_demo.py examples/mock_input.json
```

在仓库根目录检查前端 AI 脚本语法：

```bash
node --check frontend_new/js/ai-insights.js
```
