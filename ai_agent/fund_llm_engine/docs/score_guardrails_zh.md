# AI Agent 评分与协作护栏

这份文档用于保护联调 demo 的稳定性，避免三类问题：

- 改完代码后忘记旧分数，无法判断评分变化是否合理。
- 新接入后端数据后，把正常变化和异常变化混在一起。
- AI Agent 联调时误改队友后端脚本或后端实现。

## 默认分工

AI Agent 侧默认可以修改：

- `ai_agent/fund_llm_engine/src/`
- `ai_agent/fund_llm_engine/scripts/`
- `ai_agent/fund_llm_engine/tests/`
- `ai_agent/fund_llm_engine/docs/`
- 必要的 `frontend_new/` 展示或调用配置

默认不修改：

- `backend/market_backend/`
- `backend/news_backend/`
- `backend/portfolio_backend/`
- `backend/start_all.sh`
- `backend/stop_all.sh`

如果确实必须修改后端文件，需要先说明原因，并在提交说明里写清楚为什么 AI 侧无法通过 adapter 或运行参数解决。

## 生成评分快照

先确保后端和 Agent 服务已经启动：

```bash
cd ai_agent/fund_llm_engine
python3 scripts/score_guardrails.py snapshot \
  --output outputs/score_snapshot_before.json
```

默认会测试这些基金：

```text
000001
512100
003358
```

默认使用 mock LLM，所以适合快速回归。脚本仍然会通过 Agent HTTP API 调后端 registry，因此可以验证真实后端数据链路。

如果要跑真实 LLM：

```bash
python3 scripts/score_guardrails.py snapshot \
  --real-llm \
  --output outputs/score_snapshot_real.json
```

## 对比改动前后

改代码前先保存 before，改完后保存 after：

```bash
python3 scripts/score_guardrails.py snapshot \
  --output outputs/score_snapshot_before.json

# 修改 AI Agent 代码后

python3 scripts/score_guardrails.py snapshot \
  --output outputs/score_snapshot_after.json
```

然后对比：

```bash
python3 scripts/score_guardrails.py compare \
  --before outputs/score_snapshot_before.json \
  --after outputs/score_snapshot_after.json \
  --output outputs/score_guardrail_report.json \
  --fail-on-unexpected
```

对比结果有三种状态：

- `pass`：变化可解释，或没有关键变化。
- `review`：需要人工解释，例如新增 Agent 后 overall 分母变化。
- `fail`：稳定 Agent 出现异常变化，例如没有改 NAV/风险逻辑却导致 `PerformanceAgent` 或 `RiskAgent` 大幅变分。

## 检查是否误改后端

提交前运行：

```bash
python3 scripts/score_guardrails.py scope-check
```

如果发现 `backend/` 下有改动，默认失败。只有在确实需要修改队友后端，并且已经说明原因时，才使用：

```bash
python3 scripts/score_guardrails.py scope-check --allow-backend
```

## 演示前冻结稳定版本

演示前建议在仓库根目录打一个本地 tag：

```bash
git tag demo-stable-YYYYMMDD
```

如果后续改乱，可以查看稳定点：

```bash
git show demo-stable-YYYYMMDD
```

如果需要回到稳定版本，应先确认当前改动是否要保留，再使用 git 命令恢复。不要直接 `reset --hard`，除非明确知道会丢弃哪些改动。

## 判断评分变化是否合理

合理变化示例：

- 后端新增行业配置后，`SectorAgent` 从 `skipped` 变成 `success`。
- 后端新增行业配置后，`ExposureAgent` 因为行业集中度参与计算而变化。
- 新增 Agent 参与聚合后，`overall_score` 因为分母变化而变化。

需要警惕的变化：

- 只改前端展示，却导致 `PerformanceAgent` 或 `RiskAgent` 分数变化。
- 没有改后端数据和 feature builder，却导致 NAV 点数变化。
- 没有新增数据字段，却导致缺失字段数量突然变化。

这套护栏不是要求分数永远不变，而是要求每一次变化都能被数据、特征或评分公式解释。
