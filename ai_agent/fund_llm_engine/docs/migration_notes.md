# Migration Notes

## 直接迁移进来的文件思路

以下内容被直接迁移或轻度改造后迁移：

- `fundmaster/contracts.py` -> `src/fund_llm/contracts.py`
- `fundmaster/feature_builder.py` -> `src/fund_llm/feature_builder.py`
- `fundmaster/llm_client.py` -> `src/fund_llm/llm_client.py`
- `fundmaster/agent_base.py` -> `src/fund_llm/agents/base.py`
- `fundmaster/engine.py` -> `src/fund_llm/orchestration/engine.py`
- `fundmaster/test_feature_builder.py` -> `tests/test_feature_builder.py`

## 参考后重写的部分

以下内容没有原样迁移，而是参考后拆分重写：

- `fundmaster/agents.py`
  原因：原文件是单文件 prompt-first 结构，不适合专仓长期维护
- `fundmaster/test_modular.py`
  原因：测试目标改成了新仓库的模块结构和输出契约
- `deepseek_client.py`
  原因：股票语义过重，且与专仓职责不匹配
- `ai_agents.py`
  原因：与 UI、股票场景和主工程耦合过深

## 没有迁移的部分

以下内容明确不属于本仓库职责：

- `app.py` 和所有 `*_ui.py`
- `portfolio_*`
- `monitor_*`
- `notification_service.py`
- `pdf_generator*.py`
- `stock_data.py`
- `data_source_manager.py`
- 所有股票策略模块
- 所有数据库文件和部署文件

## 迁移原则

这个仓库只保留：

1. 可独立测试的 LLM 底座
2. 与 UI/数据库无关的 agent 编排能力
3. 未来可以直接接入组项目的输入输出接口

