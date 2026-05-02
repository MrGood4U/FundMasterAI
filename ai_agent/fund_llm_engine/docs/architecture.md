# Architecture

## 仓库职责

这个仓库只负责基金分析系统里的 LLM 智能分析层：

- 接收结构化输入
- 构建标准化特征
- 调用多个 agent 做分视角分析
- 由 chief agent 汇总输出统一结论

## 分层

```text
FundAnalysisInput
  -> FeatureBuilder
  -> FundFeaturePack
  -> Agents
  -> ChiefAgent
  -> FinalAnalysisResult
```

## 模块边界

- `contracts.py`
  定义请求、特征包、agent 输出、最终结果
- `feature_builder.py`
  负责收益、回撤、波动率、集中度等确定性指标
- `llm_client.py`
  负责真实模型调用和 mock client
- `agents/`
  负责分视角解释
- `orchestration/engine.py`
  负责注册、执行、失败隔离和最终汇总

更详细的智能体模块设计见 [agent_architecture_design.md](/Users/shiling/Downloads/aiagents-stock/fund-llm-engine/docs/agent_architecture_design.md:1)。

## 当前 MVP Agents

- `PerformanceAgent`
- `ExposureAgent`
- `RiskAgent`
- `SentimentAgent`
- `SectorAgent`
- `ChiefAgent`

## Proposal 对齐后建议补充的 Agents

如果只看 LLM 模块，当前还建议补下面这些角色，以更贴近 proposal：

- `MarketAgent`
- `CapitalFlowAgent`

是否全部实现，取决于上游最终能提供哪些结构化或半结构化数据。

## 后续输入层级

当前仓库的主入口仍然是单基金分析。

如果要继续对齐 proposal，后续建议扩展为三类输入：

- `FundAnalysisInput`
- `SectorAnalysisInput`
- `PortfolioAnalysisInput`

这样可以避免把 fund / sector / portfolio 三种分析场景都硬塞进一个 payload。
