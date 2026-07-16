# AI Agent 中文文档索引

这里集中列出当前仍保留在 `master` 的中文 AI Agent 文档。代码和测试仍是最终依据。

## 当前使用

- [`contracts.md`](./contracts.md)：AI HTTP 请求、响应、状态和错误契约。
- [`environment_setup.md`](./environment_setup.md)：不用 Docker 时的本地 Python 环境。
- [`provider_setup.md`](./provider_setup.md)：OpenAI-compatible provider 和模型配置。
- [`manual_acceptance_checklist.md`](./manual_acceptance_checklist.md)：Docker 主线下的
  AI Insights 人工验收清单。
- [`windows_startup.md`](./windows_startup.md)：可选的 Windows 原生 Agent 单服务调试，
  不是完整项目启动说明。
- [`score_guardrails_zh.md`](./score_guardrails_zh.md)：评分变化和 Agent/后端协作边界。
- [`golden_cases.md`](./golden_cases.md)：golden case 设计与判断标准。

## 真实样例说明

- [`real_sample_003358_notes.md`](./real_sample_003358_notes.md)
- [`real_sample_005827_notes.md`](./real_sample_005827_notes.md)
- [`real_sample_008163_notes.md`](./real_sample_008163_notes.md)
- [`real_sample_161725_notes.md`](./real_sample_161725_notes.md)

这些样例说明用于记录输入来源、近似口径和已知边界，不是项目启动文档。

## 历史参考

- [`agent_architecture_design.md`](./agent_architecture_design.md)：早期架构设计理由；当前
  行为以代码、`architecture.md` 和契约为准。
- [`migration_notes.md`](./migration_notes.md)：早期模块迁移范围。
- [`dev_backend_integration_handoff.md`](./dev_backend_integration_handoff.md)：2026-05-30
  dev 后端联调快照，不是当前启动说明。
- [`real_api_parallel_benchmark.md`](./real_api_parallel_benchmark.md)：旧 Gemini 配置下的
  并行 benchmark，不是当前 provider 指南。

## 维护规则

- 当前启动统一使用仓库根目录的 `DOCKER.zh-CN.md`。
- 周末联调和共享 systemd 云服务器说明已经退出当前启动链路；Windows 原生 Agent
  单服务调试说明继续保留。
- 历史设计、迁移、handoff 和 benchmark 可以保留查阅，但不能覆盖当前代码、契约、
  Docker smoke 和浏览器实测结果。
- 新增或修改公开接口时，同步更新中英文契约和入口。
- 真实 API Key 只能放在 Git 忽略的本地环境文件中。
