# AI Agent Development Log

This document is the task-level status ledger for the AI Agent module on the
`aiagent-use-dev-backend` branch. Use it as the first source of truth before
reading proposal, planning, or report documents.

It records verified implementation state only. Future plans stay in
`implementation_plan.md`, and milestone/tag history stays in
`version_history.md`.

## Current Snapshot

Date: 2026-06-10

Branch:

```text
aiagent-use-dev-backend
```

Current architecture status:

- The current demo path is runnable as:
  `frontend_new -> AI service -> backend function registry -> metrics -> specialist agents -> Chief aggregation`.
- The AI service uses deterministic fund-type routing and structured data coverage before asking the LLM to explain results.
- Specialist agents run before `ChiefAgent`; `ChiefAgent` aggregates scores, confidence, skipped modules, missing data, and final action text.
- This is not a free-form planner/executor agent. Tool calls are registry-backed and orchestrated by code, with LLM used for explanation.
- The Agent HTTP service has its own `start.sh` / `stop.sh`; backend services
  still start separately through `backend/*/start.sh` or `backend/start_all.sh`.

Implemented agents:

```text
PerformanceAgent
ExposureAgent
BondExposureAgent
RiskAgent
SentimentAgent
SectorAgent
ChiefAgent
```

Frontend-facing AI output status:

- The AI service returns `status`, `stance`, `coverage`, and `analysis_trace` so the frontend can explain what happened.
- `analysis_trace` can show backend tool discovery, real fund history loading, fund profile identification, data coverage checks, metric calculation, specialist checks, and final aggregation.
- User-facing page copy, layout, interaction, and demo-friendly visual presentation are frontend responsibilities.
- The AI module should keep output semantics clear enough for the frontend to distinguish `success`, `insufficient_data`, `not_applicable`, and `error`.

Known gaps:

- `BondExposureAgent` now has a baseline path for bond holdings and asset allocation. Remaining fixed-income depth depends on richer duration, maturity, issuer, and credit-rating data.
- `MarketAgent` and `CapitalFlowAgent` are proposal-alignment enhancement agents, not the immediate reason bond funds skip equity-style analysis.
- `get_fund_profit_probability` is currently a backend tool result, stored in analysis context. There is no standalone `ProfitabilityAgent`.
- Frontend should own non-developer wording so skipped or not-applicable agents do not look broken in demos; the AI module owns the structured status and evidence fields that make this possible.

## Completed

- Real-data AI demo branch is connected through frontend, AI service, backend function registries, and the LLM agent pipeline.
  - Evidence: `README.zh-CN.md`, `ai_agent/fund_llm_engine/app.py`, `ai_agent/fund_llm_engine/src/fund_llm/adapters/backend_function_client.py`.
- Deterministic fund-type routing exists.
  - Evidence: `ai_agent/fund_llm_engine/src/fund_llm/fund_routing.py`.
- Coverage-aware feature building exists.
  - Evidence: `ai_agent/fund_llm_engine/src/fund_llm/feature_builder.py`.
- Bond-like funds can mark equity exposure and sector analysis as not applicable instead of letting the LLM invent data.
  - Evidence: `ai_agent/fund_llm_engine/src/fund_llm/agents/exposure_agent.py`, `ai_agent/fund_llm_engine/src/fund_llm/agents/sector_agent.py`.
- Bond-like funds can run a dedicated fixed-income exposure check when bond holdings or asset-allocation data is available.
  - Evidence: `ai_agent/fund_llm_engine/src/fund_llm/agents/bond_exposure_agent.py`, `ai_agent/fund_llm_engine/src/fund_llm/feature_builder.py`, `ai_agent/fund_llm_engine/examples/real_input_003358.json`.
- `Analysis Evidence` trace data is available for frontend explanation.
  - Evidence: `ai_agent/fund_llm_engine/app.py`, `ai_agent/fund_llm_engine/src/fund_llm/orchestration/engine.py`, `frontend_new/ai-insights.html`, `frontend_new/js/ai-insights.js`.

## Partial

- Backend tool use is registry-backed, but not a fully autonomous LLM tool planner.
  - Done: AI service discovers backend function definitions and calls registered tools through code.
  - Still partial: future function-calling or tool-use agent exploration remains a plan item.
- Frontend presentation is outside the AI module ownership boundary.
  - AI-owned: structured statuses, coverage metadata, and analysis trace events.
  - Frontend-owned: labels such as `Performance Check`, layout, visual hierarchy, and demo-friendly copy.

## Todo

- Add deeper bond analytics after backend data includes duration, maturity structure, issuer classification, and credit-rating fields.
- Consider a future `ProfitabilityAgent` only if the team decides to make `get_fund_profit_probability` a first-class specialist view.
- Add or expand regression cases after new bond, asset allocation, market, or capital-flow data becomes available.

## Blocked Or Backend-Dependent

- Complete bond fund exposure analysis depends on reliable duration, maturity, issuer, credit-rating, and asset-allocation data.
- `MarketAgent` and `CapitalFlowAgent` depend on upstream market context and capital-flow data.
- Richer sentiment analysis depends on higher-quality news/event inputs.

## Task Entries

### 2026-06-09 - Create AI Agent status ledger

Goal:

- Add a single source of truth for future AI or teammate handoff so current implementation state is not confused with proposal plans.

Actual changes:

- Added this task-level development log.
- Planned README entry points so future readers know to check this document before architecture or planning docs.

Impact:

- Documentation only.
- No runtime code, API contract, prompt, backend, frontend behavior, or test fixture changes.

Verification:

- To verify after editing, run:

```bash
test -f ai_agent/fund_llm_engine/docs/ai_agent_development_log.md
rg -n "ai_agent_development_log" README.zh-CN.md ai_agent/fund_llm_engine/README.md
```

Known unfinished work:

- This ledger records the current known state, but future code changes still need task entries added manually.

Next suggested work:

- Keep AI output semantics stable enough for frontend display.
- Then implement bond-specific exposure analysis once the backend data contract is stable.

### 2026-06-09 - Remove submitted midterm report and clarify ownership

Goal:

- Remove the already submitted midterm report from the active repository docs and prevent future AI sessions from treating it as current implementation truth.
- Clarify that frontend demo-friendly wording and visual presentation are frontend responsibilities, while the AI module owns structured evidence and status outputs.

Actual changes:

- Deleted `ai_agent/fund_llm_engine/docs/midterm_report_zh.md`.
- Removed README references to the deleted report.
- Clarified the AI/frontend boundary in the root Chinese README.
- Updated this ledger so AI-owned work is not confused with frontend presentation work.

Impact:

- Documentation only.
- No runtime code, API contract, prompt, backend, frontend behavior, or test fixture changes.

Verification:

- To verify after editing, run:

```bash
rg -n "midterm_report_zh|中期报告" README.md README.zh-CN.md ai_agent/fund_llm_engine/docs --glob '!ai_agent_development_log.md'
rg -n "analysis_trace|演示友好化|前端" README.zh-CN.md ai_agent/fund_llm_engine/docs/ai_agent_development_log.md
```

Known unfinished work:

- Resolved in the later "Organize AI Agent docs and repository hygiene" task:
  `implementation_plan.md` was cleaned and `dev_backend_integration_handoff.md`
  was marked historical.

Next suggested work:

- Keep the next AI-module feature focus on bond-specific exposure analysis and evidence-backed evaluation.

### 2026-06-09 - Organize AI Agent docs and repository hygiene

Goal:

- Make the AI Agent docs easier to navigate and prevent future readers from confusing current implementation state with old plans or handoff snapshots.
- Keep the project structure stable while cleaning repository noise.

Actual changes:

- Added `docs/README.md` as the AI Agent documentation index.
- Rewrote `docs/implementation_plan.md` as a forward-looking plan that treats `SentimentAgent` and `SectorAgent` as implemented but still enhanceable.
- Marked `docs/dev_backend_integration_handoff.md` as a historical 2026-05-30 integration snapshot.
- Updated README entry points to include the docs index.
- Added `.DS_Store` and `.specstory/` ignore rules.
- Stopped tracking `frontend_new/.DS_Store`.

Impact:

- Documentation and repository hygiene only.
- No runtime code, API contract, prompt, backend, frontend behavior, or test fixture changes.

Verification:

- To verify after editing, run:

```bash
rg -n "midterm_report_zh|中期报告" README.md README.zh-CN.md ai_agent/fund_llm_engine/docs
rg -n "SentimentAgent|SectorAgent|BondExposureAgent" ai_agent/fund_llm_engine/docs
python3.11 -m unittest discover -s tests
node --check frontend_new/js/ai-insights.js
git status --short --branch
```

Next suggested work:

- Implement bond-specific exposure analysis once the backend bond and asset-allocation data contract is stable.
- Add evaluation evidence for any future prompt or agent behavior changes.

### 2026-06-10 - Harden Agent service start and stop scripts

Goal:

- Make the AI Agent service runnable with the same simple `bash start.sh` /
  `bash stop.sh` workflow as the backend services while keeping backend startup
  separate.

Actual changes:

- Updated `ai_agent/fund_llm_engine/start.sh` to prefer local `.venv/bin/python`,
  set `PYTHONPATH`, wait for `/health`, write `app.pid` and `app.log`, and auto
  detect local `5000` / `5010` news backend URLs when `NEWS_BACKEND_URL` is not
  explicitly set.
- Updated `ai_agent/fund_llm_engine/stop.sh` to clean stale pid files and stop
  Agent listeners on the configured port.
- Updated `app.py` so script-managed background runs can disable Flask debug
  reload with `AGENT_DEBUG=false` and `AGENT_RELOAD=false`.
- Updated README startup docs to describe the new Agent script behavior.

Impact:

- Runtime startup behavior changed for the local Agent HTTP service only.
- No backend startup scripts were changed.
- No public AI API response contract changed.

Verification:

```bash
bash -n ai_agent/fund_llm_engine/start.sh
bash -n ai_agent/fund_llm_engine/stop.sh
cd ai_agent/fund_llm_engine && python3.11 -m py_compile app.py
cd ai_agent/fund_llm_engine && python3.11 -m unittest discover -s tests -p 'test_api_contract.py'
curl -s http://127.0.0.1:5003/health
```

Next suggested work:

- Keep backend service startup documented as a separate prerequisite for
  full real-data Agent analysis.

### 2026-06-10 - Add bond-aware exposure agent baseline

Goal:

- Implement the planned Phase 1 bond-aware exposure path so fixed-income funds are not reduced to skipped equity exposure checks.

Actual changes:

- Added structured `bond_holdings` and `asset_allocation` fields to `FundAnalysisInput`.
- Added bond exposure metrics to `FeatureBuilder`, including top bond weight, top-three bond weight, disclosed bond weight, and asset-class buckets.
- Added `BondExposureAgent` and wired it into mock and real pipelines, trace copy, chief aggregation metadata, evaluation, score guardrails, API coverage, and golden cases.
- Updated fund-type routing so `index_fixed_income` is classified as a bond-like fund.
- Updated `real_input_003358.json` so its disclosed bond positions are represented as `bond_holdings`.

Impact:

- Public API response shape remains backward compatible, but `agent_outputs` now includes an additional `BondExposureAgent` item.
- `coverage` can now expose `has_bond_holdings` and `has_asset_allocation`.
- Equity-like funds receive `BondExposureAgent` as `skipped + not_applicable`; bond-like funds receive success when bond holdings or asset allocation are available, and `skipped + insufficient_data` when both are missing.

Verification:

```bash
cd ai_agent/fund_llm_engine && PYTHONPATH=src python3.11 -m unittest discover -s tests
cd ai_agent/fund_llm_engine && PYTHONPATH=src python3.11 scripts/run_golden_suite.py --mode mock
```

Known unfinished work:

- The baseline does not infer duration, maturity ladder, issuer sector, yield curve positioning, or credit-rating exposure when those fields are absent.

Next suggested work:

- Move to Phase 2 evidence and evaluation hardening, especially prompt/run metadata and saved real-model review samples.

## Handoff Notes For Future AI

- Do not infer implemented status from proposal, plan, or report wording alone.
- Check this document, then inspect code paths and tests before claiming a feature is complete.
- Treat `implementation_plan.md` as future planning unless this ledger or code proves the item is done.
- Treat `version_history.md` as milestone/tag history, not a complete current-state ledger.
- Runtime secrets, including LLM API keys, must stay runtime-only and must not be written into repository files.
- The default maintenance branch for this ledger is `aiagent-use-dev-backend`; do not update other branches unless the user explicitly asks.
