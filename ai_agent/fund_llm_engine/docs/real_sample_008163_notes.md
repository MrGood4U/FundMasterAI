# Real Sample Notes: 008163

这个样例文件对应：

- [real_input_008163.json](../examples/real_input_008163.json)

## 为什么选这只基金

这只基金和 [real_input_005827.json](../examples/real_input_005827.json) 风格差异很大：

- `005827` 更像高集中主动权益
- `008163` 是红利低波指数 ETF 联接

两者适合一起做 demo 对照。

## 这份样例里哪些字段是公开数据

以下字段来自公开页面整理：

- 基金代码、基金名称、基金类型、基金经理
- 成立日期
- 2025-12-31 的基金规模
- 2026-03-26 到 2026-04-17 的单位净值序列
- 跟踪标的名称
- 2025-12-31 页面展示的前十持仓占比合计约 `0.10%`

## 哪些字段是近似整理

以下字段是为了适配当前引擎而做的近似整理：

- `industry_exposure`
  - 这是根据该基金跟踪的红利低波指数风格和主要成分股行业特征做的近似暴露
  - 不是官方完整行业配置披露
- `top_holdings_weight`
  - 这里使用的是联接基金页面披露的直接股票持仓占比近似值 `0.001`
  - 因为它是 `ETF feeder`，这个数字不能像主动权益基金那样直接理解为“组合高度分散”
- `manager_tenure_years`
  - 这是根据 2020-01-21 到 2026-04-17 计算出的近似值

## 这只基金样例要注意的地方

这只基金是 `ETF 联接基金`，不是典型主动股票基金。

所以当前仓库用它做分析时会有两个特点：

1. `top_holdings_weight` 会显得非常低  
因为联接基金主要持有目标 ETF，而不是直接持有很多股票。

2. `industry_exposure` 需要人为整理  
当前 contract 还没有“ETF 联接基金穿透到底层指数成分”的专门字段。

因此，这份样例很适合做：

- 风格对照 demo
- 暴露解释差异演示
- 当前 LLM 引擎边界说明

## 当前最适合怎么用

先跑 mock：

```bash
source .venv/bin/activate
python3 scripts/run_mock_demo.py examples/real_input_008163.json
```

再跑真实模型：

```bash
source .venv/bin/activate
python3 scripts/run_real_demo.py examples/real_input_008163.json
```

## 公开来源

- 基金净值、规模、成立日期、经理、跟踪标的：
  - [天天基金：南方标普红利低波50ETF联接A(008163)](https://fund.eastmoney.com/008163.html?fund=008163)
- 基金持仓页：
  - [天天基金 F10：持仓明细](https://fundf10.eastmoney.com/ccmx_008163.html)
- 十大重仓股页面：
  - [搜狐基金：十大重仓股](https://q.fund.sohu.com/q/hs10.php?code=008163)
