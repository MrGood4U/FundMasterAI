# Real API Parallel Execution Benchmark

> Historical record only: this benchmark used a former Gemini configuration.
> Gemini is not part of the current demo model catalog or supported setup; use
> `provider_setup.md` for the active OpenCode Go / DeepSeek configuration.

测试日期：2026-04-27

历史说明：这份 benchmark 记录的是当时的 5-agent pipeline。当前状态请以
`ai_agent_development_log.md` 为准；新增 `BondExposureAgent` 后，当前 pipeline
已有 6 个 specialist agents。

## 目的

这份记录用于说明：在真实 LLM API 路径下，把 specialist agents 从串行执行改成并行执行后，端到端运行时间是否明显缩短，以及并行是否影响 golden suite 的自动质量检查结果。

## 测试对象

- Golden suite：`examples/golden_cases_manifest.json`
- Case 数量：8
- 模型：`gemini-3-flash-preview`
- API base URL：`https://generativelanguage.googleapis.com/v1beta/openai/`
- 执行结构：
  - 串行基准：每个 case 内 5 个 specialist agents 逐个执行，然后 `ChiefAgent` 汇总
  - 并行版本：每个 case 内 5 个 specialist agents 并行执行，然后 `ChiefAgent` 汇总
  - Case 之间仍然串行执行，避免 suite 级别并发过高触发 API rate limit

## 实测命令

串行基准：

```bash
TIMEFORMAT='elapsed_seconds=%R'
time ./.venv/bin/python scripts/run_golden_suite.py \
  --mode real \
  --max-parallel-agents 1 \
  --output outputs/golden_suite_real_v1.4_serial_baseline.json
```

并行版本，同时保存完整 case outputs / narratives：

```bash
TIMEFORMAT='elapsed_seconds=%R'
time ./.venv/bin/python scripts/run_golden_suite.py \
  --mode real \
  --include-results \
  --results-dir outputs/golden_case_results_real_v1.4_parallel \
  --output outputs/golden_suite_real_v1.4_parallel_with_results.json
```

## 结果摘要

| Mode | Worker setting | Total time | Suite status | Passed cases | Failed cases |
|---|---:|---:|---|---:|---:|
| Serial baseline | `--max-parallel-agents 1` | `6:06.09` | `pass` | 8 | 0 |
| Parallel agents | default, 5 workers | `2:18.31` | `pass` | 8 | 0 |

## 性能结论

- 并行版本耗时：`138.31` 秒
- 串行基准耗时：`366.09` 秒
- 加速比：约 `2.65x`
- 时间减少：约 `62.2%`

这说明 agent 并行执行能显著改善真实 API 路径的端到端体验。它没有减少总 LLM 请求数，但把同一个 case 内相互独立的 specialist agent 等待时间重叠起来，因此显著缩短总耗时。

## 质量对比

串行报告与并行报告在以下层面没有差异：

- `overall_status`
- `evaluation_status`
- `evaluation_score`
- 每个 case 的检查项通过/失败状态

8 个 case 的对比结果均为：

- `pass -> pass`
- `evaluation_score 100 -> 100`
- check changes：无

因此，在当前 suite 的自动评估维度上，并行执行没有降低输出质量。

## Rate Limit 观察

本次测试中没有观察到：

- HTTP `429`
- timeout
- rate-limit error
- agent failure caused by API throttling

当时并发策略是“case 内 5 个 specialist agents 并行，case 之间串行”，在本次真实 API 测试中可运行。后续如果继续增加 agent，建议保留 `--max-parallel-agents` 作为并发阀门，例如在演示或额度紧张时使用：

```bash
./.venv/bin/python scripts/run_golden_suite.py --mode real --max-parallel-agents 3
```

## 完整 Narrative 留档

并行版本已保存每个 case 的完整 `FinalAnalysisResult`，包括：

- `summary`
- `key_thesis`
- `main_risks`
- `action_plan`
- `agent_outputs`
- 每个 agent 的 `narrative`

当时的本地保存目录是
`outputs/golden_case_results_real_v1.4_parallel/`，示例文件名是
`real_003358_fixed_income_duration_real_result.json`。这些运行产物没有提交到当前
仓库，因此这里只保留历史路径文字，不提供会失效的仓库链接。

该样例的 metadata 中记录：

```json
{
  "llm_mode": "real",
  "llm_model": "gemini-3-flash-preview",
  "agent_execution_mode": "parallel",
  "agent_worker_count": "5"
}
```

## 报告文件

- 串行基准报告（历史本地文件）：
  `outputs/golden_suite_real_v1.4_serial_baseline.json`
- 并行报告（历史本地文件）：
  `outputs/golden_suite_real_v1.4_parallel_with_results.json`
