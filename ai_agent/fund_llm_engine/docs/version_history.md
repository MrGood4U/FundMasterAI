# Version History

## 当前建议用法

不要记 commit 哈希，优先记可读 tag。

先看所有里程碑版本：

```bash
git tag -l
```

查看某个版本内容：

```bash
git show v0.4-windowed-features
```

临时切到某个版本查看：

```bash
git switch --detach v0.4-windowed-features
```

如果想从某个版本继续开发，建议新开分支：

```bash
git switch -c codex/from-v0.4 v0.4-windowed-features
```

看完后切回当前开发分支：

```bash
git switch codex/mock-first-stabilization
```

## 当前里程碑

### `v0.1-baseline`

- 对应阶段：项目初始骨架
- 当前含义：
  - 仓库初始化
  - 基础多 agent 编排骨架
  - 最小可运行测试

### `v0.2-mock-first`

- 对应阶段：mock 全流程跑通
- 当前含义：
  - 统一 mock pipeline
  - 一键运行 mock demo
  - mock-first 开发方式固定下来

### `v0.3-contracts`

- 对应阶段：输入输出契约增强
- 当前含义：
  - JSON 输入输出契约成型
  - 增加 benchmark、analysis window、fund tags 等字段
  - 增加样例输入输出 JSON

### `v0.4-windowed-features`

- 对应阶段：多窗口特征工程增强
- 当前含义：
  - 增加 1m / 3m / 6m / 1y 收益指标
  - 增加窗口化 benchmark / excess return
  - 增加窗口化波动率与最大回撤
  - 增加数据质量计数与支持标记

### `v0.5-agent-upgrade`

- 对应阶段：核心 agent 使用增强后的特征
- 当前含义：
  - `PerformanceAgent` 开始使用窗口收益和超额收益
  - `RiskAgent` 开始使用窗口波动率和窗口回撤
  - 输出里增加对历史长度是否足够的提示
  - 新增 agent 人工验收脚本

### `v0.6-exposure-chief`

- 对应阶段：剩余 agent 与 chief 汇总升级
- 当前含义：
  - `ExposureAgent` 开始使用 fund tags、运营指标和客户风险偏好
  - `ChiefAgent` 开始汇总 agent 置信度、错误状态和数据质量信息
  - 最终结果 metadata 增加 agent 健康度和覆盖度提示
  - 人工验收脚本扩展为查看 exposure 与 chief 输出

### `v0.7-single-model-api`

- 对应阶段：单模型真实 API 接入
- 当前含义：
  - `LLMClient` 切成直接解析 OpenAI-compatible 原始 JSON，兼容 Gemini
  - 新增 `real_pipeline` 和 `run_real_demo.py`
  - 配置统一收口到 `LLM_API_KEY / LLM_BASE_URL / LLM_MODEL`
  - `.env.example` 默认对齐 Gemini 3 Flash
  - 已提供 2 份真实样例输入：
    - `examples/real_input_005827.json`
    - `examples/real_input_008163.json`

### `v0.8-sentiment-agent`

- 对应阶段：新闻 / 情绪分析模块接入
- 当前含义：
  - 新增 `SentimentAgent`
  - `FundAnalysisInput` 支持结构化 `news_items`
  - `FeatureBuilder` 增加新闻覆盖度相关 flag / metric
  - mock / real pipeline 默认进入 4-agent 编排
  - `ChiefAgent` 开始汇总 news / sentiment 覆盖信息

### `v0.9-sector-agent`

- 对应阶段：行业 / sector 视角模块接入
- 当前含义：
  - 新增 `SectorAgent`
  - `FundFeaturePack` 携带行业暴露明细供 sector 分析使用
  - mock / real pipeline 默认进入 5-agent 编排
  - `ChiefAgent` 开始汇总 sector context 覆盖信息

### `v1.0-llm-evaluation`

- 对应阶段：LLM 输出评估基线建立
- 当前含义：
  - 新增自动化评估模块与脚本
  - 建立结构完整性、评分一致性、coverage、降级行为、风险画像对齐等规则检查
  - 新增 LLM 评估文档与 starter golden cases 说明

### `v1.1-golden-cases`

- 对应阶段：golden cases 基线建立
- 当前含义：
  - 新增 golden cases manifest
  - 区分 `golden_real` 与 `regression_case`
  - 新增 golden suite 批量运行脚本
  - 新增“怎么判断 gold 不是 shit”的说明文档

### `v1.2-real-golden-expansion`

- 对应阶段：真实 golden cases 扩展
- 当前含义：
  - 新增 `real_161725_baijiu_single_sector` 真实白酒指数基金样例
  - 新增真实样例来源说明与字段近似口径说明
  - 新增 `regression_conflicting_signals` 冲突信号回归样例
  - golden suite 支持 `expected_text_fragments`，用于锁住关键事实和风险提示
  - mock golden suite 扩展到 7 个 case

### `v1.3-fixed-income-golden`

- 对应阶段：固收真实 golden case 补齐
- 当前含义：
  - 新增 `real_003358_fixed_income_duration` 真实固收指数基金样例
  - 新增固收样例来源说明与字段近似口径说明
  - 明确保留 `industry_exposure` 和 `benchmark_nav_series` 缺失，用来测试系统在债券基金上是否诚实降级
  - mock golden suite 扩展到 8 个 case

### `v1.4-parallel-agent-execution`

- 对应阶段：真实模型演示性能优化
- 当前含义：
  - `AnalysisEngine` 改为并行执行 specialist agents，`ChiefAgent` 仍串行汇总
  - 新增 `--max-parallel-agents`，用于真实 API 演示时控制并发
  - golden suite 支持 `--include-results` / `--results-dir` 保存完整 case outputs 和 agent narratives
  - 新增真实 API 并行 benchmark 报告，记录串行 `6:06.09`、并行 `2:18.31`、约 `2.65x` 加速
  - 保存真实模型并行版 8 个 case 的完整输出，方便人工复核和报告引用

## 推荐记忆方式

以后你只需要记“阶段名”，不用记哈希：

- `v0.1-baseline`
- `v0.2-mock-first`
- `v0.3-contracts`
- `v0.4-windowed-features`
- `v0.5-agent-upgrade`
- `v0.6-exposure-chief`
- `v0.7-single-model-api`
- `v0.8-sentiment-agent`
- `v0.9-sector-agent`
- `v1.0-llm-evaluation`
- `v1.1-golden-cases`
- `v1.2-real-golden-expansion`
- `v1.3-fixed-income-golden`
- `v1.4-parallel-agent-execution`

如果后面继续迭代，我们就按这个模式继续加：

- `v1.5-real-llm-robustness`
- `v1.6-evidence-evaluation-hardening`
- `v1.7-market-agent`
- `v1.8-capital-flow-agent`

这样版本线会一直保持可读。
