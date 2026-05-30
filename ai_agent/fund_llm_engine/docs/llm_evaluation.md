# LLM Output Evaluation

## 目标

这套评估规则不是为了证明 LLM “绝对正确”，而是为了回答 3 个更实际的问题：

1. 当前输出结构是不是完整
2. 输出和输入、分数、风险画像是不是自洽
3. 每次改 prompt 或加 agent 以后，我们怎么快速判断有没有明显退化

当前仓库提供两层评估：

- `自动评估`
  - 用规则检查结构、覆盖度、评分一致性、缺失数据降级、风险画像对齐、narrative 健康度
- `人工复核`
  - 用少量固定问题检查是否出现明显幻觉、过度推断或风格跑偏

## 自动评估维度

当前自动评估总分 `100`，分成 7 个检查项：

1. `structure_completeness` `20`
   - 顶层字段是否齐全
   - 核心 agent 是否都有输出
   - success agent 是否有 `score / key_points / narrative`

2. `score_consistency` `15`
   - `overall_score` 和 `overall_rating` 是否匹配
   - agent 的 `score` 和 `stance` 是否匹配
   - `metadata.success_agent_count / error_agent_count` 是否和真实输出一致

3. `core_agent_coverage` `15`
   - 当前核心 agent 是否都在结果中
   - 当前版本默认是：
     - `PerformanceAgent`
     - `ExposureAgent`
     - `RiskAgent`
     - `SentimentAgent`
     - `SectorAgent`

4. `evidence_coverage` `20`
   - 关键指标是否真的体现在输出里
   - 例如：
     - performance 是否提到 `total return`
     - performance 是否提到 `max drawdown`
     - 有 benchmark 时是否提到 benchmark / excess return
     - 有 news 时 metadata 是否标记 `has_news_signal`
     - 有 industry exposure 时 metadata 是否标记 `has_sector_context`

5. `missing_data_handling` `10`
   - benchmark / news / sector 数据缺失时，是否明确降级说明

6. `risk_profile_alignment` `10`
   - 如果输入里给了 `client_risk_profile`，最终建议是否有体现

7. `narrative_sanity` `10`
   - summary 和各 agent narrative 是否为空
   - 是否出现 `API returned empty response`
   - 是否把失败信息混进 success narrative

## 自动评估结果解释

- `pass`
  - 总分 `>= 85`
  - 且没有高优先级失败项
- `review`
  - 总分 `60 - 84`
  - 说明能用，但值得人工复核
- `fail`
  - 总分 `< 60`
  - 或关键结构 / 覆盖度明显缺失

## 推荐命令

直接对默认 mock case 做自动评估：

```bash
python3 scripts/evaluate_analysis_output.py --input examples/mock_input.json --mode mock
```

如果你已经先跑好了分析结果文件，再单独评估：

```bash
python3 scripts/evaluate_analysis_output.py \
  --input examples/mock_input.json \
  --result outputs/real_result.json
```

如果想把评估报告落文件：

```bash
python3 scripts/evaluate_analysis_output.py \
  --input examples/mock_input.json \
  --mode real \
  --output outputs/evaluation_report.json
```

## 人工复核问题

自动评估通过后，建议再人工看这 5 个问题：

1. narrative 有没有引用输入里根本不存在的数据
2. benchmark 不存在时，是否还在强行讲超额收益
3. 风险提示和行动建议是否互相矛盾
4. 新闻 / 行业解释是否和这只基金的真实风格一致
5. 最终 summary 是否比各 agent 结论更夸张

## 当前建议的 starter golden cases

当前仓库至少可以先拿这 3 份做回归：

- [examples/mock_input.json](../examples/mock_input.json)
- [examples/real_input_005827.json](../examples/real_input_005827.json)
- [examples/real_input_008163.json](../examples/real_input_008163.json)

后续建议再补至少 2 份：

- 一只高波动科技/成长风格基金
- 一只 benchmark 和 news 都明显缺失的低信息样例

这样你就能更稳定地判断：

- prompt 变更后输出有没有退化
- 新 agent 接入后 chief 汇总有没有跑偏
- mock / real 两条链的结构是否仍然一致
