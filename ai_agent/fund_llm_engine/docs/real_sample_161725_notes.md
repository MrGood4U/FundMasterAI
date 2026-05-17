# Real Sample Notes: 161725

这个样例文件对应：

- [real_input_161725.json](../examples/real_input_161725.json)

## 为什么选这只基金

这只基金和当前已有的两个真实样例形成互补：

- `005827` 是主动混合基金，持仓集中但不是纯指数复制
- `008163` 是红利低波 ETF 联接，直接股票持仓比例很低
- `161725` 是白酒主题指数基金，行业暴露极度集中，适合测试 sector / exposure agent 是否会正确提示单行业风险

## 这份样例里哪些字段是公开数据

以下字段来自公开页面或公开接口整理：

- 基金代码、基金名称、基金类型、基金经理
- 成立日期
- 2026-03-31 的基金规模
- 2026-03-27 到 2026-04-24 的单位净值序列
- 跟踪标的名称
- 官方业绩比较基准
- 2025-12-31 的股票持仓明细
- 当前基金经理任职信息

## 哪些字段是近似整理

以下字段是为了适配当前引擎而做的近似整理：

- `industry_exposure`
  - 这是根据 2025-12-31 股票持仓明细手工归类
  - 前 19 个主要白酒股票合计约占基金净值 `94.34%`
  - 这里用 `白酒: 0.9434` 表示主题行业暴露，不代表官方完整行业配置表逐项复制
- `top_holdings_weight`
  - 这是 2025-12-31 前十大股票持仓占基金净值比例的合计
  - 计算值约为 `84.79%`
- `manager_tenure_years`
  - 当前经理页面展示侯昊上任日期为 `2017-08-22`
  - 这里按 `2017-08-22` 到 `2026-04-24` 近似为 `8.67` 年
- `fund_tags`
  - 这是为了适配当前 agent 逻辑手工补的轻量标签

## 为什么没有 `benchmark_nav_series`

这只基金公开页面给出的跟踪标的是：

- `中证白酒指数`

官方业绩比较基准是：

- `中证白酒指数收益率*95%+金融机构人民币活期存款基准利率(税后)*5%`

当前样例先保留 `benchmark` 和 `extra_context.official_benchmark`，但没有硬填一条无法从同一来源确认的 benchmark 净值序列。因此 golden suite 里会期望识别出：

- `benchmark_nav_series`

这能防止系统在缺少基准序列时乱讲精确超额收益。

## 这只基金样例要注意的地方

这个 case 是一个真实 `golden_real`，但它不是用来证明模型一定要给出买入建议。

它更适合测试：

- sector agent 能不能识别白酒单行业集中
- exposure agent 能不能识别前十大持仓权重很高
- chief agent 能不能把缺少 benchmark 净值序列、缺少新闻样例说清楚
- 风险画像为 `aggressive` 时，系统是否仍然提醒主题基金的集中度风险

## 当前最适合怎么用

先跑 mock：

```bash
source .venv/bin/activate
python3 scripts/run_mock_demo.py examples/real_input_161725.json
```

再跑真实模型：

```bash
source .venv/bin/activate
python3 scripts/run_real_demo.py examples/real_input_161725.json
```

## 公开来源

- 基金基本概况、规模、成立日期、经理、跟踪标的、业绩比较基准：
  - [天天基金 F10：招商中证白酒指数(LOF)A 基本概况](https://fundf10.eastmoney.com/161725.html)
- 历史净值页面：
  - [天天基金 F10：历史净值](https://fundf10.eastmoney.com/jjjz_161725.html)
- 历史净值接口：
  - [天天基金 F10DataApi：历史净值](https://fundf10.eastmoney.com/F10DataApi.aspx?code=161725&type=lsjz&page=1&per=20)
- 基金经理页面：
  - [天天基金 F10：基金经理](https://fundf10.eastmoney.com/jjjl_161725.html)
- 股票持仓页面：
  - [天天基金 F10：基金持仓](https://fundf10.eastmoney.com/ccmx_161725.html)
- 股票持仓接口：
  - [天天基金 FundArchivesDatas：2025Q4 股票持仓](https://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc&code=161725&topline=10&year=2025&month=12)
