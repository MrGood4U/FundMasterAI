# Implementation Plan

This document is the forward-looking plan for the AI Agent / LLM module. For
the current implemented state, read
[`ai_agent_development_log.md`](./ai_agent_development_log.md) first.

## 当前定位

当前仓库中的 AI Agent 部分负责 `FundMasterAI` 的 LLM 智能分析层：

- 接收标准化基金分析输入；
- 通过后端 function registry 获取真实基金数据；
- 构建非 LLM 的确定性指标和数据覆盖状态；
- 调用 specialist agents 做分视角分析；
- 由 `ChiefAgent` 汇总最终结论；
- 返回前端可解释的 `status`、`stance`、`coverage` 和 `analysis_trace`。

它不负责前端页面、后端原始数据 API、数据库或外部数据采集。需要跨模块协作时，优先通过 adapter、运行参数、接口契约和文档明确边界。

## 当前已完成能力

当前分支已经具备 fund-level multi-agent analysis engine 的可演示基线：

- 输入输出契约、feature builder、mock / real LLM 路径已建立；
- `PerformanceAgent`、`ExposureAgent`、`BondExposureAgent`、`RiskAgent`、`SentimentAgent`、`SectorAgent`、`ChiefAgent` 已接入编排；
- `AnalysisEngine` 支持 specialist agents 并行执行，`ChiefAgent` 串行汇总；
- `FundTypeRouter` 和 data coverage 逻辑用于判断 agent 是否适用、数据是否缺失；
- `BackendFunctionClient` 通过后端 function registry 调用真实 market/news backend 工具；
- golden cases、自动评估脚本、score guardrails 和 explainability trace 已作为回归与演示支撑。

这些能力不再作为未来待办重复规划。后续计划应围绕“已完成但可增强”和“尚未覆盖”的部分展开。

## Proposal 对齐状态

已经对齐：

- 先算确定性指标，再让 LLM 解释证据；
- 多 agent 分视角分析和 chief 聚合；
- mock / real LLM 两条验证路径；
- 新闻 / sentiment 视角已有独立 agent；
- 行业 / sector 视角已有独立 agent；
- 债券基金已有 bond-specific exposure baseline；
- 数据缺失时返回结构化状态，避免让 LLM 猜测；
- 输出质量评估、golden cases 和版本里程碑文档已建立。

仍需增强。下面不是“未实现”清单，而是已实现能力的下一步增强方向：

- `SentimentAgent` 已实现；后续重点是提升新闻输入质量、真实样例覆盖和事件结构化；
- `SectorAgent` 已实现；后续重点是在后端提供稳定行业配置后进一步提升解释质量；
- `BondExposureAgent` 已实现 baseline；后续重点是久期、期限结构、发行主体和信用评级等更细债券字段；
- proposal 中更宽的 `MarketAgent` / `CapitalFlowAgent` 视角；
- portfolio-level 与 sector-level 输入契约和分析入口；
- prompt version、更多真实 golden cases、人工验收记录和回归对比。

## 已完成阶段归档

### Phase 1: Bond-Aware Exposure Baseline (Completed)

目标：

- 补齐当前债券基金分析的主要 AI 侧缺口；（baseline 已完成）
- 不把债券基金强行塞进 equity-style `ExposureAgent` / `SectorAgent`；
- 在后端缺少债券持仓或资产配置时继续返回结构化缺失状态。

已实现：

- 新增 `BondExposureAgent`；
- 新增 `bond_holdings` 和 `asset_allocation` 输入字段；
- 接入 backend function registry 返回的 `get_fund_portfolio_hold_bond` 和 `get_fund_individual_detail_hold`；
- 补充债券基金 regression / golden case，覆盖数据可用、数据缺失、not applicable 三类结果。

后续增强：

- 明确债券持仓、债券/现金/其他资产配置、久期或期限结构、信用债/利率债信息的输入字段；
- 与后端协作确认 `get_fund_bond_holdings`、`get_fund_asset_allocation` 等工具的 registry 形态；
- 在后端补齐久期、期限结构、发行主体和信用评级字段后，继续增强 `BondExposureAgent` 的风险解释。

完成标志：

- 债券基金不再只表现为 equity exposure 缺失；
- `coverage.data_coverage` 能解释哪些债券数据可用、缺失或不适用；
- mock 测试、engine 测试和 golden suite 都覆盖债券路径。

当前状态：

- Phase 1 baseline 已完成，不再作为未来实施阶段占用规划位；
- 后续固定收益深度分析不属于 Phase 1 收尾，而是依赖后端补齐久期、期限结构、发行主体和信用评级等更细字段后的增强工作；
- 真实模型可靠性、工程加固和回归证据进入 Phase 1.5。

## 推荐实施顺序

### Phase 1.5: AI Agent Engineering Hardening

范围说明：

- Agent hardening 主体只改 `ai_agent/fund_llm_engine`，不动 backend 代码；
  如需支持联调页面展示或模型选择，可以同步更新 `frontend_new` 的 AI
  Insights 集成页。
- 公开 API 返回结构保持向后兼容。可以增加可选字段，但不能破坏前端现有读取方式。
- LLM 调用合并不在本期。多个 agent 是否合并成更少 LLM call，留给 Phase 2 或后续性能 / 成本评估。
- agent score / overall score 标定不在本期。Phase 1.5 只处理工程可靠性，不重新定义评分体系。
- 输出语言保持英文不变。香港大学毕设交付物要求英文，prompt 里的
  `Write in clear user-facing English` 是正确设计。
- `_summary_looks_incomplete` 现在服务于英文输出，Phase 1.5 不改。

当前已完成：

- `LLMClient` 已处理真实 provider 的空 `content`、`finish_reason=length`
  retry、provider-specific `reasoning_content` presence、诊断 metadata 和 HTTP
  provider body 脱敏；
- real-model run 已支持同一个 OpenAI-compatible API key / base URL 下通过
  `LLM_MODEL`、CLI `--model` 或 HTTP `llm_model` 切换不同模型；
- 已跑通过 `deepseek-v4-flash` 和 `deepseek-v4-pro` 的真实 smoke test。

剩余建议实现：

1. 整理后端取数逻辑，但现在不做并发。

   当前 `build_fund_input_from_backend_functions` 已经能跑，但里面同时做了取数、
   年份回退、字段整理和 trace 记录。Phase 1.5 先把这些逻辑整理清楚，方便后面加
   MarketAgent / CapitalFlowAgent 时继续扩展。

   本期要做：

   - 保持 `get_fund_hist` 作为必需数据；
   - 保持 `get_fund_individual_basic_info` 用来判断 fund type 和后续需要哪些数据；
   - 把股票持仓、行业配置、债券持仓、资产配置、公告、
     `get_fund_individual_analysis`、`get_fund_profit_probability` 标清楚哪些是可选数据；
   - 每个可选数据要写清楚：失败后是否降级、结果写到哪里、coverage 如何体现；
   - 先保持串行执行，暂时不引入 `ThreadPoolExecutor`。

2. 把现在塞在 `extra_context` 里的重要数据改成正式字段。

   现在 `top_holdings`、`profit_probability`、`individual_analysis` 主要靠
   `_json_preview` 字符串放在 `extra_context` 里，这更像展示日志，不适合下游稳定读取。

   本期要做：

   - 在 `contracts.py` 的 `FundAnalysisInput` 增加正式字段：
     `top_holdings`、`profit_probability`、`individual_analysis`；
   - 同步更新 `from_dict` / `to_dict`；
   - 更新 `feature_builder.py` 的 coverage 标志；
   - 更新 `app.py` 的 `_coverage`；
   - `extra_context` 中对应的 `_json_preview` 只保留给 trace 展示，不作为下游逻辑来源。

3. 动态置信度。

   现在部分 agent 的 confidence 是写死的，例如 `PerformanceAgent=0.78`、
   `RiskAgent=0.80`。这不好解释。

   本期要做：

   - 在 `agents/base.py` 增加统一 confidence helper；
   - 输入包括 NAV 点数、可用回报窗口数、是否有 benchmark、该 agent 所需字段是否齐全；
   - 输出控制在 `0.4-0.9`；
   - 替换 `PerformanceAgent`、`RiskAgent` 的固定值；
   - exposure / sentiment / sector / bond 这些已有动态 confidence 的 agent，也统一到同一口径。

4. 健壮性小修。

   本期要做：

   - 在已有 empty-content / `finish_reason=length` retry 基础上，给 `llm_client.py`
     补 timeout / `429` / `5xx` 的一次短退避 retry；
   - 不 retry `400` / `401` / `403`，这些通常是配置或权限问题；
   - 给 `MockLLMClient` 和 `LLMClient` 增加显式 `is_mock` 属性；
   - 替换 `chief_agent.py` 里按 class name 判断 mock 的写法；
   - `app.py` 继续记录完整异常日志，但对外 `500` 只返回通用错误信息，不直接回传
     `str(exc)`。

5. 测试与文档。

   本期要做：

   - 新增或更新单测：取数整理、结构化字段、动态 confidence、`is_mock` 判定、
     LLM timeout / `429` / `5xx` retry、HTTP `500` 对外脱敏；
   - 回归命令：

     ```bash
     cd ai_agent/fund_llm_engine
     .venv/bin/python -m unittest discover tests
     .venv/bin/python scripts/run_golden_suite.py --mode mock
     ```

   - 动态置信度会改变部分 golden 期望值，需同步更新；
   - 按文档规则同步 `docs/ai_agent_development_log.md` 和必要的 provider /
     evaluation docs。

完成标志：

- mock 测试和 golden suite 继续全绿；
- 后端取数逻辑更清楚：哪些数据必需、哪些可选、失败后怎么降级、结果写到哪里；
- `top_holdings`、`profit_probability`、`individual_analysis` 有正式结构化字段和测试覆盖；
- confidence 口径统一，可解释，相关 metadata / golden 期望已更新；
- mock 判定不再依赖 class name；
- Agent HTTP `500` 对外不泄露 raw exception；
- Phase 2 可以专注 evidence / evaluation、prompt/run metadata、真实样例留档和人工评估。

风险提示：

- 动态置信度会改变 `average_confidence` 和相关 metadata 的具体数值，golden cases
  和断言需同步调整，这是预期内改动；
- 不要把 LLM 输出语言改成中文；
- 不要在本期合并多 agent LLM 调用；
- 不要在本期急着做后端取数并发。

后续性能优化：

- backend optional tool 并发化先不作为 Phase 1.5 必做项；
- 等 MarketAgent / CapitalFlowAgent 等后续 agent 的输入字段和取数需求更稳定后再做；
- 到时候再并发，只并发互相独立的可选取数；
- 并发后也要保证输出日志顺序稳定，并且不能改变“今年没有持仓就取去年”的
  `portfolio_year` 回退逻辑。

### Phase 2: Evidence And Evaluation Hardening

目标：

- 让 demo 和报告更容易说明“模型为什么这么说”；
- 把 prompt 调整、真实模型输出和 agent 行为变化纳入可复查记录。

建议实现：

- 为 agent narrative 增加 prompt version 或 run metadata；
- 扩展 golden cases，覆盖混合、权益指数、债券、缺数据、冲突信号等代表场景；
- 保存关键真实模型输出，配合 `llm_evaluation.md` 做人工复核；
- 继续维护 `score_guardrails.py`，避免 AI 侧改动误碰 backend/frontend。

完成标志：

- 每次关键 prompt 或 agent 改动都能跑 mock golden suite；
- 真实模型结果有可复查样例和评估报告；
- 文档能说明质量标准、失败类型和降级策略。

### Phase 3: Sentiment And Sector Enhancements

目标：

- 在已有 `SentimentAgent` / `SectorAgent` 基础上增强输入质量，而不是重新规划为未实现模块。

建议实现：

- 为新闻输入稳定字段，例如 title、summary、published_at、source、topic、sentiment_label；
- 让 `SentimentAgent` 区分缺新闻、弱新闻、重大事件和结构化情绪标签；
- 在后端提供行业配置后，让 `SectorAgent` 区分行业集中、单赛道暴露、主题风险和行业数据缺失；
- 保持 `success`、`insufficient_data`、`not_applicable`、`error` 语义稳定，方便前端展示。

完成标志：

- 新闻和行业数据不足时不生成过度结论；
- 有真实样例证明 sentiment / sector 输出引用了具体证据；
- `ChiefAgent` 能清晰吸收这两个视角，而不是机械拼接 agent 文案。

### Phase 4: Market And Capital Flow Agents

目标：

- 对齐 proposal 中 broader market context 和 capital flow 分析要求；
- 只在上游数据稳定后接入，避免先造一个只能写泛泛结论的 LLM agent。

建议实现：

- 新增 `MarketAgent` 时，先定义市场指数、利率、宏观或基金同类排名等可证据化输入；
- 新增 `CapitalFlowAgent` 时，先确认资金流向数据来源、时间窗口、字段单位和可解释限制；
- 让 `ChiefAgent` 将 market / flow 作为辅助上下文，不替代 fund-level 风险收益结论。

完成标志：

- 每个新 agent 都有明确字段依赖、缺失降级、mock 测试和 golden case；
- 没有可用市场或资金流数据时，agent 明确 skipped，而不是让 LLM 编宏观判断。

### Phase 5: Portfolio And Sector-Level Inputs

目标：

- 把当前单基金分析扩展到更高层级，但不把所有分析对象塞进同一个 payload。

建议实现：

- 保留 `FundAnalysisInput`；
- 设计独立的 `PortfolioAnalysisInput` 和 `SectorAnalysisInput`；
- 明确 fund / portfolio / sector 各自复用哪些 feature builder 逻辑，哪些需要拆分；
- 让 orchestrator 根据输入类型选择 agent 组合。

完成标志：

- 输入契约边界清晰；
- 不同分析层级的必填字段、可选字段、缺失策略和输出结构可被测试覆盖。

## 文档维护规则

- 当前实现状态只以 `ai_agent_development_log.md`、代码和测试为准；
- 本文件只记录未来计划、优先级和完成标志；
- `version_history.md` 只记录里程碑和 tag，不作为当前状态台账；
- `dev_backend_integration_handoff.md` 是历史联调快照，保留用于追溯，不应替代当前状态判断；
- 每次新增或完成 AI Agent 能力时，同步更新 development log、相关 docs 和测试证据。
