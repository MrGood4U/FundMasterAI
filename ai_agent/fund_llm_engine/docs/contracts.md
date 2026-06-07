# Contracts

## 当前目标

当前仓库先把输入输出契约稳定下来，供后续三类场景复用：

- 本地 mock 开发
- 真实模型联调
- 与上游/下游系统做 JSON 对接

## 输入契约

主入口对象是 `FundAnalysisInput`。

### 当前必填字段

- `request_id`
- `fund_info.code`
- `fund_info.name`
- `fund_info.asset_type`
- `nav_series`

### 当前推荐但可选字段

- `industry_exposure`
- `top_holdings_weight`
- `news_summary`
- `news_items`
- `analysis_window`
- `benchmark`
- `benchmark_nav_series`
- `fund_tags`
- `operational_metrics`
- `extra_context`

### 字段说明

- `analysis_window`
  用于标识当前分析覆盖的时间区间与观察日期
- `benchmark`
  用于标识比较基准本身
- `benchmark_nav_series`
  如果提供，当前版本会产出基础基准收益和超额收益特征
- `news_items`
  用于承载结构化新闻条目，适合给 `SentimentAgent` 做事件和情绪判断
  建议字段包括：
  - `title`
  - `summary`
  - `published_at`
  - `source`
  - `topic`
  - `sentiment_label`
- `fund_tags`
  适合承载风格、定位、渠道等轻量业务标签
- `operational_metrics`
  适合承载基金规模、成立日期、经理任期等稳定业务信息
- `extra_context`
  预留给上游快速扩展，不影响主契约结构

## 输出契约

当前主输出对象是 `FinalAnalysisResult`。

### 当前核心字段

- `overall_rating`
- `overall_score`
- `key_thesis`
- `main_risks`
- `action_plan`
- `agent_outputs`
- `summary`
- `score_explanation`

### 当前新增字段

- `score_explanation`
  用确定性文本解释最终评分和评级的形成原因，例如哪些 specialist score 支持评级、哪些分数拉低评级；不替代 `summary`
- `missing_fields`
  用于告诉下游这次分析里有哪些输入字段缺失或未齐备
- `metadata`
  预留给后续执行信息、模型信息或版本信息

## JSON 示例

- 输入示例：`examples/mock_input.json`
- 输出示例：`examples/mock_output.json`

## 本地验证

直接跑：

```bash
python3 scripts/run_mock_demo.py
```

如果想用自定义 JSON 输入：

```bash
python3 scripts/run_mock_demo.py examples/mock_input.json
```
