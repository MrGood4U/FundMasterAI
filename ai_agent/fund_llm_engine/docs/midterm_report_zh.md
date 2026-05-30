# FundMasterAI 大模型模块中期报告

日期：2026-05-30

模块：AI Agent / LLM-based Fund Analysis Engine

当前分支：`aiagent-use-dev-backend`

## 1. 模块定位

本模块负责 FundMasterAI 项目中的大模型与多智能体基金分析部分。它不直接负责前端页面、数据库或底层原始数据采集，而是作为一个独立的 AI 分析服务接收基金代码、用户风险偏好和分析时间窗口，调用后端真实基金数据，再通过多 Agent 流程生成结构化分析结果。

当前端到端链路如下：

```text
frontend_new
  -> AI Agent HTTP service
      -> backend function registry
      -> market/news backend real data
      -> feature builder
      -> multi-agent analysis
      -> chief summary
      -> frontend display
```

当前阶段的核心目标不是追求所有金融数据维度一次性完整，而是先完成一条真实可跑、可解释、可扩展、不会乱编数据的 AI 分析链路。

## 2. 已完成工作

### 2.1 独立 AI Agent 服务

已将大模型模块封装成独立 HTTP 服务，默认端口为 `5003`。

主要接口：

```text
GET  /health
GET  /api/ai/functions
POST /api/ai/fund/analyze
```

前端当前通过：

```text
POST http://127.0.0.1:5003/api/ai/fund/analyze
```

获取 AI 分析结果。

### 2.2 真实后端 function registry 对接

已实现 `BackendFunctionClient`，可以从队友后端的 function registry 读取工具定义，再按工具定义发 HTTP 请求。

当前已接入的后端工具包括：

```text
get_fund_hist
get_fund_individual_basic_info
get_fund_portfolio_holds
get_fund_individual_analysis
get_fund_profit_probability
get_public_fund_announcement
```

因此当前 demo 路径已经不是纯 mock，而是可以读取真实后端数据后再进入 AI 分析流程。

### 2.3 多 Agent 分析流程

当前已实现并接入的 Agent：

```text
PerformanceAgent   收益表现分析
ExposureAgent      持仓与暴露分析
RiskAgent          风险与回撤分析
SentimentAgent     公告/新闻情绪分析
SectorAgent        行业配置分析
ChiefAgent         综合汇总和最终建议
```

各 Agent 先基于结构化特征判断，再由 LLM 负责自然语言解释。底层收益率、波动率、最大回撤、持仓比例等核心数值不依赖 LLM 生成。

### 2.4 确定性基金类型路由

已新增基金类型路由逻辑。系统不会让 LLM 猜基金类型，而是从后端结构化接口 `get_fund_individual_basic_info` 读取 `fund_type`，再在代码中归一化。

示例：

```text
混合型-偏股       -> mixed_fund
债券型-债券指数   -> bond_index_fund
股票/指数相关类型 -> stock_index_fund 或 equity_fund
```

该路由用于判断哪些 Agent 应该运行、哪些 Agent 对当前基金类型不适用。

### 2.5 数据覆盖与防幻觉机制

已加入数据覆盖检查。Agent 输出中会区分：

```text
success
skipped + insufficient_data
skipped + not_applicable
error
```

含义如下：

```text
success
  Agent 正常完成分析。

insufficient_data
  该基金理论上适合这个 Agent，但当前后端缺少必要数据。

not_applicable
  该基金类型本来就不适合这个 Agent，例如债券基金不做股票行业分析。

error
  服务或 Agent 执行异常。
```

这部分是当前大模型模块的关键设计：缺数据时不让 LLM 编造结论，而是把缺失状态结构化返回给前端。

### 2.6 前端真实联调

当前前端页面已经可以调用 AI Agent 服务，并展示：

- 基金最终分析结论；
- 各 Agent 输出；
- Agent 分数、置信度和状态；
- 已使用数据；
- 缺失或跳过的数据；
- 后端工具调用痕迹。

当前前端展示仍比较原始，后续需要进一步优化 `insufficient_data`、`not_applicable` 和 `error` 的视觉区分。

### 2.7 测试与版本管理

当前 AI Agent 测试已通过：

```text
59 tests OK
```

已在当前分支中持续提交和推送，便于团队查看和回滚。

当前分支：

```text
aiagent-use-dev-backend
```

## 3. 当前可演示能力

当前 demo 可以展示以下能力：

### 3.1 真实数据基金分析

用户输入基金代码后，AI 服务会从后端获取真实基金数据并生成多 Agent 分析结果。

推荐 demo 代码：

```text
000001  混合型基金，适合展示完整真实数据链路
161725  股票/指数类基金，适合展示权益类持仓解析
512100  指数/ETF 场景，适合展示行业数据缺失时的谨慎处理
003358  债券指数基金，适合展示 not_applicable 路由逻辑
000002  当前后端无 NAV，预期返回 422，适合展示拒绝无效数据
```

### 3.2 基金类型驱动的 Agent 路由

例如债券基金不会强行运行股票行业分析，而是返回：

```text
status = skipped
stance = not_applicable
```

股票或指数基金如果缺少行业配置数据，则返回：

```text
status = skipped
stance = insufficient_data
```

这说明系统能够区分“这个分析不适用”和“这个分析需要数据但数据缺失”。

### 3.3 时间窗口分析

前端传入的 `start_date` 已接入 Agent 数据窗口。修复后，用户修改开始日期会影响 NAV 点数、收益窗口和最终评分，而不是始终使用同一段默认历史数据。

### 3.4 无数据拒绝分析

如果后端无法返回 NAV 历史数据，AI 服务返回 HTTP `422`，表示请求格式没问题，但当前数据不足以完成基金分析。

这比让 LLM 编造结果更安全。

## 4. 当前限制

### 4.1 行业配置数据缺失

`SectorAgent` 需要行业/板块暴露数据，例如：

```text
行业名称
行业占比
```

当前后端还没有稳定暴露该能力，因此对于部分股票/指数基金会出现：

```text
SectorAgent: skipped, insufficient_data
```

这是预期行为，不是 Agent 错误。

### 4.2 债券持仓和资产配置数据缺失

对于债券基金，当前更需要：

```text
债券持仓
债券/现金/股票/其他资产配置
久期或期限结构
信用债/利率债分类
```

当前后端尚未完整提供这些字段，所以债券基金的深度分析仍有限。

### 4.3 前端状态展示仍需优化

当前前端会把 skipped Agent 直接显示在表格中，非专业用户可能误以为系统失败。后续建议前端区分展示：

```text
success             正常展示
insufficient_data   灰色提示：缺少某类数据
not_applicable      弱化或折叠：该基金类型不适用
error               真正错误提示
```

### 4.4 工具调用仍可继续智能化

当前已经通过 function registry 调用后端工具，但工具选择仍以代码逻辑为主。后续可以进一步升级为更完整的 function calling / tool-use agent，让 Agent 能根据后端工具定义更灵活地规划调用。

## 5. 技术路线与原计划对应关系

当前实现与原大模型技术路线基本一致：

```text
结构化数据输入
  -> 非 LLM 特征计算
  -> 多 Agent 分工分析
  -> Chief Agent 汇总
  -> 前端结构化展示
```

其中已经完成：

- 多 Agent 架构；
- mock 与真实 LLM 两种模式；
- 后端真实数据接入；
- function registry 风格工具发现；
- 基金类型确定性路由；
- 数据覆盖检查；
- 缺数据防幻觉机制；
- 前端联调 demo。

尚未完全完成：

- 更完整的动态 tool-use agent；
- 债券/资产配置/行业配置等后端数据补齐；
- 更细粒度的 Agent 评估指标；
- 更产品化的前端展示和用户解释。

## 6. 下一步计划

### 6.1 AI Agent 侧

继续完善：

- 将 `insufficient_data`、`not_applicable`、`missing_backend_capability` 的输出格式进一步规范；
- 增加更多真实基金代码回归测试；
- 在后端补充行业/债券/资产配置接口后，接入新字段；
- 增加债券基金专用的 `BondExposureAgent` 或在 `ExposureAgent` 内部拆分债券逻辑；
- 进一步探索 function calling / tool-use agent。

### 6.2 后端协作需求

建议后端补充：

```text
get_fund_industry_allocation
get_fund_bond_holdings
get_fund_asset_allocation
```

这些接口不是前端 AI 页面必须直接调用的，但 AI Agent 需要它们来生成更完整、更可信的分析。

### 6.3 前端协作需求

建议前端优化 Agent 状态展示：

```text
success             主结果展示
insufficient_data   数据缺失提示
not_applicable      不适用检查，弱化或折叠
error               真正错误
```

这样可以避免用户把“谨慎跳过”误解成“系统坏了”。

## 7. 中期结论

当前大模型模块已经达到中期可交付状态。

它已经不只是 prompt demo，而是完成了一个可真实运行的 AI Agent 分析链路：

- 能接真实后端 API；
- 能进行多 Agent 分析；
- 能根据基金类型决定 Agent 是否适用；
- 能识别数据缺失；
- 能在数据不足时拒绝或跳过，而不是让 LLM 幻觉；
- 能把结构化结果返回给前端展示；
- 有测试和版本管理支撑。

因此当前阶段可以作为中期成果提交。后续重点应放在数据源覆盖、前端展示优化和更高级 tool-use 能力上。
