# FundMasterAI 中文说明

本分支是 FundMasterAI 的前端、后端和 AI Agent 真实数据联调 demo。

对应英文说明见 [README.md](README.md)。

## 当前分支定位

当前分支：

```text
aiagent-use-dev-backend
```

这个分支用于：

- 基于队友最新 `dev` 后端做真实接口联调；
- 恢复并增强 AI Agent / LLM 引擎；
- 让前端通过 AI 服务获取基金分析结果；
- 让 AI 服务通过后端 function registry 调用真实后端数据；
- 验证数据缺失、基金类型路由、Agent 跳过逻辑和防幻觉策略。

当前链路已经不是纯 mock：

```text
frontend_new
  -> ai_agent/fund_llm_engine Agent HTTP service
      -> backend function registries
      -> market/news backend real data
      -> LLM multi-agent analysis
```

## 主要目录

```text
backend/                    队友后端服务
frontend_new/               当前联调前端
ai_agent/fund_llm_engine/   LLM / 多智能体基金分析引擎
```

重要 AI Agent 文档：

```text
ai_agent/README.md
ai_agent/fund_llm_engine/README.md
ai_agent/fund_llm_engine/docs/dev_backend_integration_handoff.md
ai_agent/fund_llm_engine/docs/midterm_report_zh.md
```

## 环境要求

- Python `>=3.11`
- `pip`
- 可选：MySQL，仅运行 `portfolio_backend` 时需要
- 真实 LLM 模式需要在 `ai_agent/fund_llm_engine/` 下配置 `.env`

后端依赖：

```bash
pip install flask flask-openapi3 akshare pandas numpy efinance okx
pip install -U "flask-openapi3[swagger,redoc]"
```

AI Agent 依赖：

```bash
cd ai_agent/fund_llm_engine
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[backend,agent]"
```

## 运行测试

AI Agent 测试：

```bash
cd ai_agent/fund_llm_engine
source .venv/bin/activate
python3 -m unittest discover -s tests
```

当前预期：

```text
59 tests OK
```

前端语法检查：

```bash
node --check frontend_new/js/ai-insights.js
```

## 启动后端服务

当前 AI demo 主要需要 `market_backend` 和 `news_backend`。

```bash
cd backend/market_backend
bash start.sh

cd ../news_backend
bash start.sh
```

默认端口：

```text
market_backend: http://127.0.0.1:5001
news_backend:   http://127.0.0.1:5000
```

如果 macOS 上 `5000` 被占用，可以手动把 `news_backend` 放到其他端口，例如 `5010`：

```bash
cd backend/news_backend
python3.11 -c "from app import create_app; create_app().run(port=5010, debug=True)"

export NEWS_BACKEND_URL=http://127.0.0.1:5010
```

检查 function registry：

```bash
curl -s http://127.0.0.1:5001/api/market/functions?tag=fund
curl -s http://127.0.0.1:5000/api/news/functions?tag=fund
```

如果新闻后端改成 `5010`，第二个 URL 也要改成 `5010`。

## 启动 AI Agent 服务

```bash
cd ai_agent/fund_llm_engine
source .venv/bin/activate
export NEWS_BACKEND_URL=${NEWS_BACKEND_URL:-http://127.0.0.1:5000}
bash start.sh
```

AI Agent 服务：

```text
GET  http://127.0.0.1:5003/health
GET  http://127.0.0.1:5003/api/ai/functions
POST http://127.0.0.1:5003/api/ai/fund/analyze
```

健康检查：

```bash
curl -s http://127.0.0.1:5003/health
```

## 调用 AI 分析

mock LLM 模式，但仍然使用真实后端数据：

```bash
curl -s -X POST http://127.0.0.1:5003/api/ai/fund/analyze \
  -H 'Content-Type: application/json' \
  -d '{"code":"000001","start_date":"2025/01/01","mock":true}'
```

真实 LLM 模式：

```bash
cd ai_agent/fund_llm_engine
cp .env.example .env
```

如果使用 DeepSeek，可以直接按下面这样填写：

```text
LLM_API_KEY=你的 DeepSeek API Key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
```

也可以用兼容旧模型名：

```text
LLM_MODEL=deepseek-chat
```

但 DeepSeek 官方文档提示 `deepseek-chat` 后续会弃用，优先建议使用 `deepseek-v4-flash`。`.env` 是本地私密配置，不会上传，也不要提交到仓库。

然后调用：

```bash
curl -s -X POST http://127.0.0.1:5003/api/ai/fund/analyze \
  -H 'Content-Type: application/json' \
  -d '{"code":"003358","start_date":"2025/01/01","mock":false,"llm_timeout_seconds":90}'
```

## 队友接入说明

### 前端如何接 AI Agent

前端 AI 分析页面只需要调用一个聚合接口：

```text
POST http://127.0.0.1:5003/api/ai/fund/analyze
```

请求示例：

```json
{
  "code": "000001",
  "start_date": "2025-01-01",
  "client_risk_profile": "balanced",
  "mock": false,
  "max_nav_points": 260
}
```

字段说明：

```text
code                 基金代码，必填
start_date           分析开始日期，可用 2025-01-01 或 2025/01/01
client_risk_profile  用户风险偏好，可选 balanced / conservative / aggressive
mock                 true 表示 mock LLM，false 表示真实 LLM
max_nav_points       没有显式 start_date 时最多取多少个 NAV 点
```

当前 `frontend_new/js/ai-insights.js` 默认调用：

```text
http://127.0.0.1:5003/api/ai/fund/analyze
```

如果 AI Agent 不在 `5003`，前端可以用 URL 参数切换：

```text
http://127.0.0.1:8003/ai-insights.html?agentBase=http://127.0.0.1:5003
```

或者在页面里设置：

```js
window.FUNDMASTER_AGENT_BASE = "http://127.0.0.1:5003";
```

### mock 模式和真实 LLM 模式的区别

```text
mock: true
  使用 mock LLM，适合前端调试和接口联通测试。
  不需要 LLM_API_KEY。
  但仍然需要先启动 market_backend / news_backend，因为基金数据仍来自真实后端。

mock: false
  使用真实 LLM。
  需要在 ai_agent/fund_llm_engine/.env 里配置 LLM_API_KEY。
  .env 不会上传到仓库，也不应该上传。
```

`.env` 配置方式：

```bash
cd ai_agent/fund_llm_engine
cp .env.example .env
```

填写：

```text
LLM_API_KEY=你的 DeepSeek API Key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
```

如果换成 Gemini 或其他 OpenAI-compatible provider，只需要把 `LLM_BASE_URL` 和 `LLM_MODEL` 换成对应服务的值。

### 后端需要提供什么

AI Agent 当前会通过后端 function registry 自动发现和调用工具，不需要在 Agent 里硬编码每个后端 URL。

需要先启动：

```text
market_backend
news_backend
```

Agent 会读取：

```text
GET http://127.0.0.1:5001/api/market/functions?tag=fund
GET http://127.0.0.1:5000/api/news/functions?tag=fund
```

如果新闻后端端口改成 `5010`，启动 Agent 前设置：

```bash
export NEWS_BACKEND_URL=http://127.0.0.1:5010
```

当前 AI Agent 已接入的后端函数：

```text
get_fund_hist
get_fund_individual_basic_info
get_fund_portfolio_holds
get_fund_individual_analysis
get_fund_profit_probability
get_public_fund_announcement
```

后续如果后端补充以下函数，AI Agent 可以继续增强分析：

```text
get_fund_industry_allocation
get_fund_bond_holdings
get_fund_asset_allocation
```

### 返回结果里前端重点看什么

成功响应：

```json
{
  "code": 200,
  "message": "success",
  "coverage": {},
  "data": {}
}
```

前端展示建议：

```text
data.overall_rating       最终评级
data.overall_score        综合分数
data.summary              ChiefAgent 汇总文字
data.agent_outputs        各 Agent 结果
data.missing_fields       缺失字段
data.metadata             执行元信息
coverage.nav_points       使用的 NAV 点数
coverage.fund_type        后端原始基金类型
coverage.normalized_fund_type
                          Agent 归一化基金类型
coverage.data_coverage    数据覆盖状态
```

Agent 状态不要都当作错误：

```text
success                   正常完成
skipped + insufficient_data
                          该 Agent 理论上适用，但缺少必要数据
skipped + not_applicable  该基金类型不适合该 Agent
error                     真正执行异常
```

如果返回 HTTP `422`，通常表示请求格式没问题，但当前基金代码没有足够 NAV 数据，AI Agent 会拒绝生成报告，避免 LLM 编造结果。

## 启动前端 demo

```bash
cd frontend_new
python3 -m http.server 8003
```

打开：

```text
http://127.0.0.1:8003/ai-insights.html
```

前端当前调用：

```text
http://127.0.0.1:5003/api/ai/fund/analyze
```

## 推荐测试基金代码

```text
000001  混合型基金，适合作为常规真实数据 demo
003358  债券指数基金，用于验证基金类型路由和 not_applicable 跳过逻辑
161725  股票/指数类基金，用于验证权益类路由和持仓解析
512100  指数/ETF 场景，可验证行业暴露缺失时 SectorAgent 的 insufficient_data 逻辑
000002  当前后端无 NAV，预期返回 422
```

## 当前 AI Agent 设计逻辑

AI 引擎不会让 LLM 猜基金类型，而是走确定性流程：

```text
基金代码
  -> get_fund_individual_basic_info
  -> 读取结构化 fund_type
  -> 代码中归一化基金类型
  -> 判断哪些 Agent 适用
  -> 调用真实后端数据
  -> 缺数据则返回结构化缺失状态
  -> LLM 只负责解释已有证据
```

Agent 输出状态含义：

```text
success             Agent 正常完成分析
skipped + insufficient_data
                    该基金理论上适合该 Agent，但后端缺少必要数据
skipped + not_applicable
                    该基金类型不适合该 Agent，例如债券基金不做股票行业分析
error               Agent 或服务执行异常
```

这个设计的核心目标是：缺数据时不让 LLM 编答案。

## 当前已知后端数据缺口

当前已经能通过后端 function registry 读取：

```text
NAV 历史净值
基金基本信息
基金股票持仓
基金公告/新闻
基金风险收益分析
基金盈利概率
```

后续更完整分析仍需要补充：

```text
get_fund_bond_holdings
get_fund_asset_allocation
get_fund_industry_allocation
```

在这些数据没有提供之前，AI Agent 会返回 `missing_backend_capability` 或 `insufficient_data`，而不是让模型猜测。

## 团队分工建议

后端：

- 维护原始数据 API；
- 维护 `function_registry.py`；
- 补充债券持仓、资产配置、行业配置等数据能力。

AI Agent：

- 负责基金类型路由；
- 负责工具选择和多 Agent 编排；
- 负责数据覆盖检查和防幻觉逻辑；
- 输出前端可直接展示的结构化结果。

前端：

- AI 分析页面优先调用 `/api/ai/fund/analyze`；
- 根据 `status` 和 `stance` 区分展示 `success`、`insufficient_data`、`not_applicable`、`error`；
- 普通基金详情、持仓、组合页可以直接复用后端 API。

## 停止服务

```bash
cd backend/market_backend && bash stop.sh
cd ../news_backend && bash stop.sh

cd ../../ai_agent/fund_llm_engine
bash stop.sh
```

如果前端是用 `python3 -m http.server` 启动的，在对应终端按 `Ctrl+C` 停止。
