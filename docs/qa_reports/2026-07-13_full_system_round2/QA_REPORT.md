# FundMasterAI 全系统第二轮浏览器实测报告

- 测试日期：2026-07-13
- 测试方式：真实浏览器逐页操作、点击、提交、刷新与截图；同时核对 API/服务日志
- 测试环境：本地 Docker Compose 服务，前端 `http://127.0.0.1:8080`
- 自动测试结果：`270 passed`
- 报告范围：全局搜索、基金深研、Portfolio、Equity、Debt、Global Investment、Markets、News、Settings、AI Insights 多基金类型

## 1. 执行摘要

本轮没有只检查 HTTP 200 或接口返回值，而是实际查看浏览器最终显示内容，并针对刷新持久化、按钮行为、动态数据和 AI Agent 路由进行了验证。

总体结论：系统并非“全部做好”。市场行情、基金榜单和 AI Insights 的部分数据链路能够动态工作，但 Portfolio、Global Investment、搜索按钮、深研页声明栏和 Settings 名称持久化仍存在可复现问题。

特别需要澄清：

1. AI Insights 的指标、评分和 Agent 路由会随基金变化，并非整页静态稿。
2. 当前页面明确运行在 `mock LLM (real data)` 模式：指标与路由来自后端真实数据，但 Chief narrative 仍是通用 Mock 文案。
3. Portfolio 页面中的 AI Portfolio Analysis / Rebalancing 当前仍是固定演示内容，不是真正生成的 AI Proposal。

## 2. 测试结果总表

| 模块 | 结果 | 浏览器实测结论 |
|---|---|---|
| 全局搜索：回车 | 部分通过 | 未匹配基金可以跳转到深研页，但深研页声明栏未出现 |
| 全局搜索：放大镜 | 失败 | 点击实际放大镜图标后没有跳转 |
| Fund Deep Dive | 失败 | URL 和基金标题发生变化，但演示模式声明栏未显示 |
| Portfolio 持仓写入 | 部分通过 | 后端成功保存，但页面刷新后新增持仓消失 |
| Portfolio AI Proposal | 失败 | 页面显示固定 Yellow、固定分析和固定调仓文案；AI 接口请求 404 |
| Equity Fund | 通过（有缺口） | 排名、详情、收益和图表可随基金动态切换；无 AI recommendation |
| Debt Fund | 通过（有缺口） | 排名、详情、收益和图表可随基金动态切换；无 AI recommendation |
| Market Hub | 通过 | 成功显示 4 条动态指数报价，但初次加载较慢 |
| Market Flow | 通过 | 成功显示动态基金流向和热力图数据 |
| News | 通过（Mock AI） | 新闻与筛选动态工作；AI Summary 是 deterministic mock |
| Settings：2FA | 通过 | 刷新后状态能够保留 |
| Settings：Display name | 失败 | 修改后刷新恢复为 `Alex Chen` |
| Global Investment | 失败 | Matrix 为空；榜单出现 `undefined`、`¥NaN`、`NaN%` |
| AI Insights 多基金 | 部分通过 | 多类型路由和数字分析动态工作，但存在 ETF 联接误判、行业标签和 metadata 不一致 |

## 3. AI Insights 多基金类型验证

### 3.1 案例矩阵

| 基金代码 | 类型/用途 | 评级与分数 | Agent 路由 | 结论 |
|---|---|---:|---|---|
| 000001 | 混合基金基准案例 | WATCH 58.4 | 6 completed + 1 not applicable | 路由及主要数字正常 |
| 005827 | 主动权益、集中持仓案例 | AVOID 34.0 | 6 completed + 1 not applicable | 成功识别深回撤和高集中度 |
| 008163 | ETF 联接/指数基金案例 | WATCH 54.9 | 6 completed + 1 not applicable | 出现重要投资语义错误 |
| 161725 | 白酒主题指数案例 | AVOID 28.6 | 6 completed + 1 not applicable | 集中度方向正确，主题标签过于泛化 |
| 003358 | 债券指数基金案例 | HOLD 68.8 | 5 completed + 2 not applicable | 债券 Agent 与 N/A 路由正确 |

### 3.2 000001：混合基金

- 总回报：`+90.16%`
- 最大回撤：`-15.89%`
- 行业集中度：`61.14%`
- 同类分位：`83%`
- Bond Exposure Agent：`not applicable`

![000001 混合基金完整结果](assets/20-ai-000001-mixed.png)

### 3.3 005827：主动权益/集中持仓基金

- 评级：AVOID 34.0
- 总回报：`-11.33%`
- 最大回撤：`-28.30%`
- 前十大持仓集中度：`84.96%`
- 同类分位：`4%`

![005827 主动权益基金摘要](assets/21b-ai-005827-summary.png)

### 3.4 008163：ETF 联接基金语义错误

页面将直接股票行业占比 `0.22%`、前十大持仓 `0.27%` 解读为“Exposure profile looks acceptable for diversified allocation”。

但本地案例文档说明该基金属于 ETF 联接基金，不能因为直接持有的股票很少，就推断其底层风险足够分散。分析应继续下钻到所联接 ETF 的底层行业和成分风险。

这是本轮 AI Insights 最重要的实质性问题：数字本身可能来自真实接口，但 Agent 对基金结构的解释是错误的。

![008163 ETF 联接基金摘要](assets/22c-ai-008163-summary-clear.png)

### 3.5 161725：白酒主题行业标签过度泛化

系统识别出约 `94.61%` 行业集中度和 `85.76%` 前十大集中度，因此风险方向基本正确。但主要行业仅显示为“制造业”，没有像 golden case 那样明确指出“白酒”。

这会降低主题基金风险提示的可操作性。

![161725 白酒基金摘要](assets/23c-ai-161725-summary-clear.png)

![161725 Agent 路由](assets/23b-ai-161725-routing.png)

### 3.6 003358：债券指数基金路由正确

- 评级：HOLD 68.8
- 最大回撤：`-2.77%`
- 年化波动率：`2.34%`
- Bond Exposure Agent 正常执行
- Portfolio Exposure 和 Sector Context 正确显示为 `not applicable`

![003358 债券基金摘要](assets/24-ai-003358-summary.png)

![003358 债券 Agent 路由](assets/24b-ai-003358-routing.png)

### 3.7 AI Insights 跨案例一致性问题

1. 股票和混合基金的 Bond Agent 明明显示 `not applicable`，Developer metadata 却写 `has_bond_exposure=true`。
2. 所有实测案例均为 `has_benchmark=false`，但 Developer View 的 `Missing fields` 显示 `none`。缺 benchmark 状态只埋在运行 metadata 中。
3. 不同基金的数字、评级和列表会变化，但 Chief summary 统一显示 `Mock LLM narrative generated for backend function-registry integration.`，所以不能将当前叙述层描述为真实 LLM 分析。

## 4. Portfolio 页面验证

### 4.1 初始页面是固定内容

页面初始显示固定的 Yellow 信号、`Balanced exposure with concentration in AI-linked names.` 和两条固定调仓建议。

![Portfolio 初始静态内容](assets/03-portfolio-initial-static.png)

### 4.2 添加持仓时后端写入成功

测试添加基金 `999997 Round2 Persistence Fund`，金额 2222，收益 111。POST 请求成功，页面暂时显示该行。

![Portfolio 添加持仓后](assets/04-portfolio-after-add.png)

### 4.3 刷新后页面丢失新增持仓

刷新页面后测试持仓从界面消失，固定 AI 文案重新出现；但后端 API 当时仍能查询到该持仓。因此故障位于前端读取/渲染链路，而不是持仓写入。

![Portfolio 刷新后](assets/05-portfolio-after-refresh.png)

### 4.4 AI Proposal 请求错误

浏览器触发的 `/api/ai/portfolio-insights` 返回 404，而实际后端路由为 `/api/ai/portfolio/analyze`。因此当前 AI Portfolio Analysis 区域不是有效 AI 结果。

测试持仓已在测试结束后删除。

## 5. 搜索与 Fund Deep Dive

### 5.1 回车跳转部分通过

输入未匹配基金并按 Enter 后，URL 成功携带 code 和 name 跳转至 `fund-deep-dive.html`，页面标题也更新。但队友描述的演示模式声明栏没有出现。

![搜索回车进入深研页](assets/01-search-enter-deep-dive.png)

### 5.2 放大镜点击失败

输入另一只未匹配基金并点击页面实际的放大镜图标后，页面仍停留在 AI Insights，只显示无匹配结果，没有跳转。

![搜索放大镜未跳转](assets/02-search-magnifier.png)

所以“回车或点击放大镜都会强制跳转”和“顶部已注入声明栏”两项，目前只有回车跳转部分成立。

## 6. Global Investment

Global Strategy Matrix 没有渲染内容，排行榜出现 `undefined`、`¥NaN` 和 `NaN%`。

![Global Investment 错误](assets/13-global-investment-broken.png)

服务日志显示页面发起的排名请求返回了约 10 MB 数据。结合界面表现，前端字段映射和基金类型参数仍存在问题，并非简单的加载等待。

## 7. Settings

### 7.1 修改后的状态

测试将 Display name 改为 `Round2 Persisted Name`，并启用 2FA。

![Settings 修改后](assets/11-settings-before-refresh.png)

### 7.2 刷新验证

刷新后 2FA 仍显示为已启用，说明其 localStorage 状态有效；Display name 则恢复为 `Alex Chen`，名称持久化未生效。

![Settings 刷新后](assets/12-settings-after-refresh.png)

测试完成后已恢复 2FA 测试状态。

## 8. 动态数据页面

### 8.1 Equity Fund

成功从第一只基金切换到第二只 `006503 财通集成电路产业股票C`，收益、规模、曲线和行业数据同时变化。

![Equity Fund 动态切换](assets/06-equity-second-fund.png)

缺口：页面显示 `No AI recommendation returned by backend`。

### 8.2 Debt Fund

成功切换到 `012887 华夏可转债增强债券C`，收益、规模和曲线发生变化。

![Debt Fund 动态切换](assets/07-debt-second-fund.png)

缺口：同样没有后端 AI recommendation。

### 8.3 Market Hub

成功加载 4 条动态指数报价，但初次等待约 30 秒。

![Market Hub 动态报价](assets/08-market-hub-live.png)

### 8.4 Market Flow

状态显示 `Market flow API live · 1074 equity funds`，列表及热力图动态渲染。

![Market Flow 动态数据](assets/09-market-flow-live.png)

### 8.5 News

页面成功加载新闻，筛选交互工作，AI Summary 接口返回成功。但摘要正文明确写着 `Mock news digest generated from deterministic sentiment classification`，所以当前属于 Mock AI 摘要。

![News 与 AI Summary](assets/10-news-live-ai.png)

![News Earnings 筛选](assets/10b-news-earnings-filter.png)

## 9. 建议修复优先级

### P0：演示和业务链路直接可见

1. Portfolio 从后端重新读取持仓，并修正 AI endpoint。
2. 移除或明确标识 Portfolio 固定 AI Proposal，避免将演示文本误认为真实分析。
3. 修复 Global Investment 的空 Matrix、`undefined` 和 `NaN`。
4. 为 ETF 联接基金增加底层 ETF 识别，禁止把低直接持仓误判为充分分散。

### P1：功能承诺和状态一致性

1. 修复搜索放大镜点击跳转。
2. 修复 Fund Deep Dive 演示模式声明栏。
3. 修复 Settings Display name 持久化。
4. 统一 `has_bond_exposure`、Agent N/A 和 benchmark missing metadata。

### P2：结果表达质量

1. 白酒主题基金应显示更具体的主题/行业标签，而不是仅显示制造业。
2. Equity 和 Debt 页面应接入真实 AI recommendation，或明确说明当前仅有数据展示。
3. Mock LLM 模式下避免将通用 Chief narrative 表述为真实 AI 生成内容。

## 10. 测试资产与复现说明

- 本报告的所有图片均位于同目录下的 `assets/`，Markdown 使用相对路径，复制或提交整个 `2026-07-13_full_system_round2` 目录即可正常显示。
- 共保存 25 张浏览器截图，包括完整页面、摘要区域和 Agent 路由区域。
- 本轮没有修改业务代码，也没有创建提交。
- 测试写入的临时持仓已删除。

### 额外完整页面截图

![005827 完整页面](assets/21-ai-005827-active-equity.png)

![008163 完整页面](assets/22-ai-008163-etf-feeder.png)

![008163 初始摘要截图](assets/22b-ai-008163-summary.png)

![161725 初始摘要截图](assets/23-ai-161725-summary.png)
