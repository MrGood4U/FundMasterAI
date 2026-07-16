# Real Sample Notes: 003358

这个样例文件对应：

- [real_input_003358.json](../examples/real_input_003358.json)

## 为什么选这只基金

这只基金补上了当前真实 golden cases 缺少的一类样本：

- `005827` 是主动混合基金，持仓集中
- `008163` 是红利低波 ETF 联接，权益风格更均衡
- `161725` 是白酒主题指数基金，单行业暴露很高
- `003358` 是固收指数基金，适合测试系统面对非权益行业暴露时是否会诚实降级

## 这份样例里哪些字段是公开数据

以下字段来自公开页面或公开接口整理：

- 基金代码、基金名称、基金类型、基金经理
- 成立日期
- 2026-03-31 的基金规模
- 2026-03-13 到 2026-04-24 的单位净值序列
- 跟踪标的名称
- 官方业绩比较基准
- 投资范围与风险收益特征
- 2025-12-31 的前五大债券持仓明细
- 当前基金经理任职信息

## 哪些字段是近似整理

以下字段是为了适配当前引擎而做的近似整理：

- `bond_holdings`
  - 这是 2025-12-31 前五大债券持仓占基金净值比例
  - 计算值为 `21.28% + 19.96% + 15.04% + 13.81% + 13.55% = 83.64%`
  - 当前样例只保留 sequence / pct / quarter，避免补入未经同一文件核验的个券名称
- `top_holdings_weight`
  - 保留为旧兼容字段，值同样为前五大债券持仓合计 `83.64%`
  - 新的债券分析应优先读取 `bond_holdings`，不要把它当成股票持仓集中度
- `asset_allocation`
  - 当前样例没有硬填无法从同一整理口径确认的精确资产配置比例
  - 因此保持为空，让 `coverage.data_coverage.asset_allocation` 和 `BondExposureAgent` 明确提示缺失
- `industry_exposure`
  - 这只基金是固收指数基金，不是权益行业基金
  - 公开 F10 基本概况说明其不直接在二级市场买入股票、权证，也不参与新股申购/增发和可转债投资
  - 因此这里保留为空，让 golden suite 检查系统是否识别 `industry_exposure` 缺失，而不是硬讲股票行业配置
- `manager_tenure_years`
  - 当前经理页面展示杨真管理本基金从 `2020-11-28` 至今
  - 这里按 `2020-11-28` 到 `2026-04-24` 近似为 `5.41` 年
- `fund_tags`
  - 这是为了适配当前 agent 逻辑手工补的轻量标签

## 为什么没有 `benchmark_nav_series`

这只基金公开页面给出的业绩比较基准是：

- `中债-7-10年期国开行债券指数收益率`

跟踪标的是：

- `中债7-10年国开行债券全价(总值)指数`

当前样例先保留 `benchmark` 和 `extra_context.official_benchmark`，但没有硬填一条无法从同一来源确认的 benchmark 净值序列。因此 golden suite 里会期望识别出：

- `benchmark_nav_series`

这能防止系统在缺少基准序列时乱讲精确超额收益。

## 这只基金样例要注意的地方

这个 case 是一个真实 `golden_real`，但它故意暴露了当前 schema 的边界：

- 有真实净值序列
- 有结构化债券持仓集中度
- 没有权益行业暴露
- 没有精确资产配置字段
- 没有新闻样例
- 没有同源 benchmark 净值序列

它更适合测试：

- Performance / Risk agent 能不能基于真实净值序列给出低波动分析
- BondExposureAgent 能不能提示债券持仓集中，同时说明资产配置、久期和评级字段缺失
- Sector agent 能不能停止在行业层面做过度结论
- Chief agent 能不能把缺 benchmark、缺 news、缺 sector context 说清楚

## 当前最适合怎么用

先跑 mock：

```bash
source .venv/bin/activate
python3 scripts/run_mock_demo.py examples/real_input_003358.json
```

再跑真实模型：

```bash
source .venv/bin/activate
python3 scripts/run_real_demo.py examples/real_input_003358.json
```

## 公开来源

- 基金基本概况、规模、成立日期、经理、投资范围、跟踪标的、业绩比较基准：
  - [天天基金 F10：易方达中债7-10年期国开行债券指数A 基本概况](https://fundf10.eastmoney.com/003358.html)
- 历史净值页面：
  - [天天基金 F10：历史净值](https://fundf10.eastmoney.com/jjjz_003358.html)
- 历史净值接口：
  - [天天基金 F10DataApi：历史净值](https://fundf10.eastmoney.com/F10DataApi.aspx?code=003358&type=lsjz&page=1&per=30)
- 基金经理页面：
  - [天天基金 F10：基金经理](https://fundf10.eastmoney.com/jjjl_003358.html)
- 债券持仓页面：
  - [天天基金 F10：债券持仓](https://fundf10.eastmoney.com/ccmx1_003358.html)
- 债券持仓接口：
  - [天天基金 FundArchivesDatas：2025Q4 债券持仓](https://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=zqcc&code=003358&year=2025&month=12)
