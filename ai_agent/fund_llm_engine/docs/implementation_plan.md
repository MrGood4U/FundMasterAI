# Implementation Plan

## 当前定位

当前仓库只负责 `FundMaster AI` 里的 LLM 智能分析模块，不负责：

- 前端页面
- 后端 API 服务
- 数据库
- 外部数据采集

截至当前版本，这个仓库已经具备可作为 LLM 子系统 MVP 基线的骨架：

- 输入输出契约已定义
- `FeatureBuilder` 已能生成基础结构化特征
- `PerformanceAgent` / `ExposureAgent` / `RiskAgent` / `ChiefAgent` 已串通
- `AnalysisEngine` 已能完成一次完整编排
- mock / real API 两条链路已跑通
- 基础测试已可运行

这意味着接下来的重点不是“从零初始化代码”，而是把当前 fund-level analysis engine 固化为基线，然后继续补齐 proposal 里仍然缺失的 LLM 范围。

## 与 Proposal 的对齐情况

如果只看你负责的“大模型部分”，当前方向是对的，但目前更准确的定位是：

- 已完成：`fund-level multi-agent analysis engine`
- 未完全覆盖：proposal 里承诺的更完整 financial analysis agent 集合

当前已经对齐的部分：

- 先算确定性指标，再交给 LLM 做解释
- 多 agent 分视角分析
- chief 聚合最终结论
- sentiment/news 视角已有独立 agent 骨架
- sector 视角已有独立 agent 骨架
- 已有自动化输出评估脚本和文档 rubric
- mock 到 real API 的联调路径
- 可测试、可回退的工程骨架

当前仍需补齐的部分：

1. `SentimentAgent` 的输入质量、新闻结构和真实样例继续补强
2. `Market / Capital Flow` 中至少 1 到 2 个专门 agent
3. `portfolio-level` 与 `sector-level` 的输入契约和分析入口
4. golden cases 数量继续扩展，并把 prompt version 纳入评估记录

## 当前建议主线

建议把 LLM 模块后续工作拆成两条线并行推进：

- 工程线：契约、特征、调用、编排、错误处理、可观测性
- 分析线：agent 角色扩展、prompt 规范、解释质量、评估体系

两条线都需要推进，但优先级应以“先补齐 proposal 的 LLM 覆盖面”为主。

## 推荐实施顺序

建议按下面顺序推进，每一阶段都保持“可测试、可提交、可回退”。

### Phase 0: 基线固化

- 保持当前目录结构
- 补齐基线测试
- 提供一键可跑的 mock smoke flow
- 建立首个 git commit
- 明确模块边界和后续输入要求

### Phase 1: 输入契约增强

目标：

- 明确上游传入字段的必填/选填规则
- 为 `FundAnalysisInput` 增加更真实的业务字段
- 统一缺失字段、空值、异常值处理策略

建议优先补充的字段：

- 分析时间区间
- 基准指数信息
- 基金类型标签
- 规模、成立时长、经理任期
- 更多可选新闻/事件摘要

完成标志：

- 契约类稳定
- 有至少 2 到 5 份真实样例 payload
- 缺失字段行为被测试覆盖

### Phase 2: 特征工程增强

目标：

- 扩展 `FeatureBuilder`
- 继续坚持“先算特征，再交给 LLM 解释”

建议优先实现的指标：

- 区间收益率：近 1 月、3 月、6 月、1 年
- 波动率与回撤：分窗口计算
- 相对基准超额收益
- 行业/风格集中度
- 持仓集中度分层指标

完成标志：

- 新指标全部可在无 LLM 情况下独立测试
- 输入异常时有稳定降级行为

### Phase 3: LLM 接口与 Prompt 规范

目标：

- 稳定 `LLMClient`
- 约束各 Agent 的输入 prompt 和输出风格

建议内容：

- 统一模型配置入口
- 支持 mock / test / production 三种模式
- 明确温度、token、超时、重试策略
- 统一 agent narrative 的长度和风格

完成标志：

- 不接真实 API 时可全部通过 mock 测试
- 接入真实模型时只需要补环境变量

## 当前阶段默认策略

在第一阶段，所有 agent 先共用同一个 `MockLLMClient`。

这样做的目的不是模拟真实效果，而是稳定以下内容：

- 输入结构
- 特征构建
- agent 调用链路
- chief 汇总逻辑
- 端到端 smoke test

等这些稳定后，再切到单一真实模型做联调。

### Phase 4: 单 Agent 逐个增强

建议顺序：

1. `PerformanceAgent`
2. `RiskAgent`
3. `ExposureAgent`
4. `ChiefAgent`

原因：

- 绩效与风险最容易基于结构化指标形成稳定解释
- 暴露与集中度依赖字段完整性更高
- Chief 需要在前面几个 agent 相对稳定后再做汇总优化

每个 Agent 的完成标志：

- 有明确输入字段依赖
- 有 mock LLM 测试
- 有错误隔离测试
- 输出 `AgentOutput` 结构稳定

### Phase 5: 编排与集成接口

目标：

- 强化 `AnalysisEngine`
- 为未来接业务系统预留清晰接入点

建议实现：

- agent 注册机制
- 单 agent 失败隔离
- 可选的运行日志 / trace id
- 统一入口函数，例如 `run_analysis(payload)`

完成标志：

- 上游系统只需要传一个标准 payload
- 下游系统只需要消费一个标准 result

### Phase 6: News 与 Sentiment Agent

目标：

- 补上 proposal 中“financial news / sentiment analysis”这一块
- 让非结构化新闻输入不再只是 `news_summary` 附带字段，而是变成可解释的独立分析模块

建议实现：

- 为新闻输入定义更清晰的数据结构
- 增加 `SentimentAgent` 或 `NewsSentimentAgent`
- 提取情绪倾向、事件主题、风险事件、利好利空摘要
- 让 chief 显式消费 sentiment 结果

建议输入字段：

- 新闻标题
- 新闻摘要
- 发布时间
- 来源
- 情绪标签（如果上游已有）
- 主题标签（可选）

完成标志：

- 有独立 sentiment agent 输出
- 有新闻缺失时的稳定降级
- chief 能在最终结论里引用 news / sentiment 视角

### Phase 7: Sector / Market / Capital Flow Agent 扩展

目标：

- 对齐 proposal 中“sector performance / market trends / capital flow”这类分析角色
- 从当前 fund-level 解释器，扩展到更完整的 financial agent 集合

建议优先级：

1. `SectorAgent`
2. `MarketAgent`
3. `CapitalFlowAgent`

原因：

- `SectorAgent` 最容易和当前基金暴露、行业集中度逻辑衔接
- `MarketAgent` 适合承接 broader market context
- `CapitalFlowAgent` 对上游数据依赖最强，可以稍后实现

完成标志：

- 至少新增 1 到 2 个 proposal 对齐 agent
- chief 可以汇总 fund + sector/market 维度结论
- 每个新 agent 都有 mock / real 两套可验证路径

### Phase 8: Portfolio-Level 与 Sector-Level 输入契约

目标：

- 当前仓库不再只接受单基金 payload
- 为 proposal 中提到的 portfolio / sector analysis 预留标准化入口

建议实现：

- 保留现有 `FundAnalysisInput`
- 新增 `SectorAnalysisInput`
- 新增 `PortfolioAnalysisInput`
- 明确不同层级输入共用哪些字段、各自依赖哪些字段

建议原则：

- 不要把所有层级强塞进一个超大 payload
- 每种分析对象都用自己的契约类
- 能复用 `FeatureBuilder` 逻辑的尽量复用，不能复用的拆开

完成标志：

- fund / sector / portfolio 三类输入边界清晰
- chief 或 orchestrator 可以根据输入类型选择对应 agent 组合

### Phase 9: Prompt 质量与输出评估

目标：

- 把“能生成”升级成“能解释得合理、稳定、可验收”
- 为课程项目的中期/最终汇报准备可展示的质量标准

建议实现：

- 建一套人工验收 rubric
- 固定 narrative 输出结构，例如：
  - summary
  - evidence
  - risks
  - action
- 补充 prompt version 标记
- 记录少量 golden cases 做回归

建议评估维度：

- 事实贴合度
- 是否引用了关键指标
- 风险与建议是否一致
- 是否符合投资者风险画像
- 是否出现明显幻觉或过度推断

完成标志：

- 至少有 5 份 golden examples
- 每次 prompt 调整后有可复看的对比结果
- 能在汇报中说明“我们如何判断 LLM 输出是好的”

### Phase 10: 生产级稳健性补强

目标：

- 把当前可跑通版本补到更适合联调和演示的状态

建议实现：

- request / trace id 贯穿
- retry / timeout / provider error 分类
- 统一 metadata 输出
- 记录模型名、运行模式、agent 健康度
- 明确 mock / real / future multi-model 的切换边界

完成标志：

- 出错时有可读错误信息
- real API 联调时问题定位路径清晰
- 输出中能追踪到模型和运行模式

## 你现在需要提供什么

当前阶段不一定需要真实 API，但下面这些材料会显著提高推进速度。

### 必需

1. 至少 2 到 5 份真实或接近真实的基金分析样例输入
2. 上游准备怎么调用这个仓库
3. 下游希望拿到什么样的输出字段

如果暂时没有正式接口文档，给 JSON 样例也完全可以。

### 强烈建议尽快提供

1. 评分标准
2. 投资结论分档规则
3. 你希望 narrative 的语言风格
4. 哪些字段将来一定拿得到，哪些字段经常缺失
5. 2 到 5 份真实新闻样例或新闻摘要样例
6. portfolio / sector 两类输入将来大概长什么样

### 在接真实模型前再提供也可以

1. LLM 服务商和模型名
2. 测试环境 API Key
3. 是否有自定义 base URL
4. 调用频率、预算和超时限制

## 是否现在就需要测试 API

不需要。

当前阶段我们完全可以先用 `MockLLMClient` 和本地单元测试把以下内容做稳：

- 输入输出契约
- 特征工程
- agent 输出结构
- chief 汇总逻辑
- 编排流程

真正需要测试 API 的节点是：

- 开始验证真实模型效果
- 开始调 prompt
- 开始联调上游/下游接口
- 开始做 golden case 质量对比

换句话说，API Key 不是第 0 步，而是第 3 到第 5 步之间再接入更合适。

## 我建议你下一步优先补给我的材料

如果你想让我按 proposal 继续补齐 LLM 模块，优先给这四样就够了：

1. 一份你期望的输入 JSON 样例
2. 一份你期望的最终输出 JSON 样例
3. 一份新闻输入样例
4. 你最想先补的 agent（我建议优先 `SentimentAgent`）

如果你暂时没有现成 JSON，我也可以先根据当前 `contracts.py` 帮你反推一版接口草案，然后我们再一起改。
