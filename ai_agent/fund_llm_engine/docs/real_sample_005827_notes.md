# Real Sample Notes: 005827

这个样例文件对应：

- [real_input_005827.json](../examples/real_input_005827.json)

## 这份样例里哪些字段是公开数据

以下字段直接来自公开页面整理：

- 基金代码、基金名称、基金类型、基金经理
- 基金成立日期
- 2025-12-31 的净资产规模
- 2026-03-31 到 2026-04-15 的单位净值序列
- 2025-12-31 的前十大重仓股合计占比
- 2025-12-31 的前十大重仓股名单
- 官方业绩比较基准文字说明
- 2025-12-31 的股票仓位占比

## 哪些字段是为适配当前引擎做的整理或近似

以下字段不是官方页面直接一模一样提供的原始结构，而是为了喂给当前 LLM 引擎做的整理：

- `industry_exposure`
  - 这是根据 2025-12-31 前十大重仓股按行业手工归类后的近似值
  - 它反映的是“前十大重仓股层面的行业暴露近似”，不是全组合官方行业配置
- `fund_tags`
  - 这是为了适配当前 agent 逻辑手工补的轻量标签
- `manager_tenure_years`
  - 这是根据 2018-09-05 到 2026-04-15 计算出的近似值
- `extra_context`
  - 这是为当前仓库保留的补充上下文

## 为什么没有 `benchmark_nav_series`

这只基金公开页面给出的官方业绩比较基准是：

- `沪深300指数收益率×45% + 中证港股通综合指数收益率×35% + 中债总指数收益率×20%`

当前仓库的 contract 还只支持单一基准净值序列，所以这里先把官方 benchmark 说明保存在：

- `extra_context.official_benchmark`

而没有硬塞一条不够准确的单基准序列进去。

## 当前最适合怎么用

先跑 mock：

```bash
source .venv/bin/activate
python3 scripts/run_mock_demo.py examples/real_input_005827.json
```

再跑真实模型：

```bash
source .venv/bin/activate
python3 scripts/run_real_demo.py examples/real_input_005827.json
```

## 公开来源

- 基金净值与阶段表现：
  - [天天基金：易方达蓝筹精选混合(005827)](https://fund.eastmoney.com/005827.html?fund=005827)
- 基本概况、规模、成立日期、经理、业绩比较基准：
  - [天天基金 F10：基本概况](https://fundf10.eastmoney.com/005827.html)
- 资产配置：
  - [天天基金 F10：资产配置](https://fundf10.eastmoney.com/zcpz_005827.html)
- 前十大重仓股：
  - [搜狐基金：十大重仓股](https://q.fund.sohu.com/q/hs10.php?code=005827)
