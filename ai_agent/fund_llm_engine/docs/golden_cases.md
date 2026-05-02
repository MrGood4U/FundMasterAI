# Golden Cases

## 为什么要单独做这套

`golden cases` 不是“再多几个输入文件”这么简单。

它们的真正用途是：

- 后面改 prompt 时，知道自己有没有把旧能力改坏
- 后面加 agent 时，知道输出是不是更稳还是更飘
- 后面换模型时，知道质量是进步了还是退步了

## 怎么判断一个 case 是真 gold 还是 shit

最重要的一点：

**不是所有样例都应该被叫做 gold。**

当前仓库把样例分成两层：

1. `golden_real`
   - 真实基金样例
   - 有公开来源或团队提供的真实输入
   - 有单独 notes 解释数据来源和近似整理部分
   - 适合拿来判断“真实业务输出是否还靠谱”

2. `regression_case`
   - 人工构造或半人工构造的边界样例
   - 主要用来测：
     - 缺字段
     - 缺 benchmark
     - 缺 news
     - 缺 sector exposure
     - 短历史
   - 适合拿来判断“系统降级和结构稳定性是否还正常”

**所以：**

- `golden_real` 才是更接近“真 gold”的东西
- `regression_case` 不是垃圾，但也不该被吹成真实质量金标准

## 当前的质量门槛

一个 case 要想被我们认成“够格的 gold”，至少要满足：

1. 输入不是临时瞎编的
2. 数据来源能说明白
3. 预期现象在运行前就写出来
4. 评估规则跑完后，结果至少达到约定门槛
5. 人工复核时，没有明显幻觉或自相矛盾

如果缺这些条件，它最多只是：

- `useful regression case`
- 或 `demo sample`

而不是高质量 golden case

## 当前 manifest 怎么用

当前 manifest 在：

- [examples/golden_cases_manifest.json](/Users/shiling/Downloads/aiagents-stock/fund-llm-engine/examples/golden_cases_manifest.json:1)

每个 case 里会写：

- `case_id`
- `tier`
- `description`
- `input_path`
- `notes_path`
- `expectations`

其中 `expectations` 不是在追求“固定文案逐字一致”，而是追求更稳的东西：

- 必须有哪些 agent
- metadata 应该是什么
- 哪些缺字段应该被识别出来
- 最低评估状态要达到什么

## 当前为什么这样设计

因为 LLM 输出不适合用“逐字对比”来判断好坏。

如果你把 golden case 设计成：

- summary 必须一模一样
- narrative 必须逐句一样

那它会非常脆弱，模型轻微波动就全红。

所以当前我们更看重：

- 结构有没有坏
- 关键证据有没有反映出来
- 缺失数据有没有降级说明
- 风险画像有没有被考虑
- 主要 agent 有没有缺席

也就是说：

**我们在追求“稳定的质量信号”，不是“僵硬的固定措辞”。**

## 当前推荐的判断方法

以后你可以这样判断一轮改动到底是 gold 还是 shit：

1. 跑 golden suite
2. 看有没有 case 从 `pass/review` 掉到 `fail`
3. 看 real case 有没有出现明显反常的 rating / metadata / missing-field 行为
4. 再人工抽看 2 到 3 个 narrative

如果出现这些情况，就要高度警惕：

- core agent 少了
- metadata 标错
- benchmark 缺失却还在乱讲超额收益
- no-news case 却写得像读过很多新闻
- sector 缺失却硬讲行业逻辑
- 风险画像是 `balanced`，结果建议却像给激进型客户

## 当前 starter cases

当前这套 starter cases 是：

- `mock_baseline_full_context`
- `real_005827_active_concentrated`
- `real_008163_dividend_lowvol`
- `real_161725_baijiu_single_sector`
- `real_003358_fixed_income_duration`
- `regression_missing_exposure`
- `regression_sparse_payload`
- `regression_conflicting_signals`

其中真正更接近 “gold” 的，是：

- `real_005827_active_concentrated`
- `real_008163_dividend_lowvol`
- `real_161725_baijiu_single_sector`
- `real_003358_fixed_income_duration`

其余是必要的回归保护网，但不应该冒充真实质量金标准。

## 怎么新增一个 case

新增 case 时先决定它是哪一类：

- 有真实来源、能解释数据出处、能写清楚人工整理口径：放进 `golden_real`
- 人工构造出来测边界条件或降级行为：放进 `regression_case`

每个 case 至少要写：

- 一个输入 JSON，放在 `examples/`
- 一个 manifest 条目，写清 `tier`、`input_path`、`expectations`
- 如果是 `golden_real`，还要写 notes 文档说明来源和近似口径

当前 manifest 还支持 `expected_text_fragments`。它适合检查确定性输出里必须出现的关键判断，例如：

- 负面新闻 case 应该出现 `Recent news flow leans negative.`
- 缺 benchmark case 不应该被当成 benchmark-aware case
- 保守型客户遇到高集中度时，建议里应该反映 `conservative risk profile`

不要用它锁死 LLM 逐字 narrative；它更适合锁住 agent 规则产出的关键事实和风险提示。

## 推荐命令

跑整套 golden suite：

```bash
python3 scripts/run_golden_suite.py --mode mock
```

如果你想把报告落文件：

```bash
python3 scripts/run_golden_suite.py --mode mock --output outputs/golden_suite_report.json
```

如果你想用真实模型跑：

```bash
python3 scripts/run_golden_suite.py --mode real
```

如果你想同时保存每个 case 的完整输出，包括 `summary`、`agent_outputs` 和各 agent 的 `narrative`：

```bash
python3 scripts/run_golden_suite.py --mode real --include-results
```

默认会写到 `outputs/golden_case_results/`。也可以指定目录：

```bash
python3 scripts/run_golden_suite.py --mode real --results-dir outputs/golden_case_results_real
```
