# AI Agent Development Log

This document is the task-level status ledger for the AI Agent module on the
`aiagent-use-dev-backend` branch. Use it as the first source of truth before
reading proposal, planning, or report documents.

It records verified implementation state only. Future plans stay in
`implementation_plan.md`, and milestone/tag history stays in
`version_history.md`.

## Current Snapshot

Date: 2026-07-02

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
MarketAgent (peer percentile + holding-period profit probability evidence)
ChiefAgent
PortfolioChiefAgent (portfolio-level aggregation)
```

Implemented analysis levels:

- Fund level: `POST /api/ai/fund/analyze` (multi-agent pipeline above).
- Portfolio level (Phase A1 MVP + A2 look-through):
  `POST /api/ai/portfolio/analyze` composes a fixed-weight, daily-rebalanced
  portfolio NAV from constituent funds (date intersection, then compound the
  weighted average of daily returns), reuses the fund-level metric functions
  on the composed series, adds `weighted_average_volatility` /
  `diversification_benefit` evidence (guaranteed non-negative under daily
  rebalancing), merges disclosed top holdings / industry allocation / asset
  allocation into `holdings_lookthrough` / `industry_lookthrough` /
  `asset_allocation_lookthrough` (overlap detection included), and aggregates
  through `PortfolioChiefAgent`.
- Sector level (Phase B1): `POST /api/ai/sector/analyze` builds a
  deterministic cross-fund sector comparison matrix with per-fund
  `available` / `insufficient_data` / `not_applicable` statuses and an
  LLM-explained (mock/real) summary with deterministic fallback.

Frontend-facing AI output status:

- The AI service returns `status`, `stance`, `coverage`, and `analysis_trace` so the frontend can explain what happened.
- `analysis_trace` can show backend tool discovery, real fund history loading, fund profile identification, data coverage checks, metric calculation, specialist checks, and final aggregation.
- User-facing page copy, layout, interaction, and demo-friendly visual presentation are frontend responsibilities.
- The AI module should keep output semantics clear enough for the frontend to distinguish `success`, `insufficient_data`, `not_applicable`, and `error`.

Known gaps:

- `BondExposureAgent` now has a baseline path for bond holdings and asset allocation. Remaining fixed-income depth depends on richer duration, maturity, issuer, and credit-rating data.
- The Phase 1.5 P0 LLM client layer now handles `finish_reason=length`, empty
  `content`, provider-specific `reasoning_content` presence, retry diagnostics,
  and sanitized HTTP provider errors. Remaining Phase 1.5 work is broader
  Agent-only engineering hardening before Phase 2 evidence and evaluation work.
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
- Real LLM client empty-content handling is hardened.
  - Evidence: `ai_agent/fund_llm_engine/src/fund_llm/llm_client.py`, `ai_agent/fund_llm_engine/tests/test_llm_client.py`.
- Real-model runs can override the configured model per CLI run or per Agent
  HTTP analysis request while keeping the same OpenAI-compatible base URL and
  API key.
  - Evidence: `ai_agent/fund_llm_engine/app.py`, `ai_agent/fund_llm_engine/scripts/run_real_demo.py`, `ai_agent/fund_llm_engine/src/fund_llm/real_pipeline.py`.
- OpenCode-style single-gateway multi-model switching is available through
  `GET /api/ai/llm/models`, per-request `llm_model`, and the AI Insights model
  picker on the frontend integration page.
  - Evidence: `ai_agent/fund_llm_engine/src/fund_llm/llm_models.py`, `ai_agent/fund_llm_engine/app.py`, `frontend_new/ai-insights.html`, `frontend_new/js/ai-insights.js`, `ai_agent/fund_llm_engine/tests/test_llm_models.py`.

## Partial

- Backend tool use is registry-backed, but not a fully autonomous LLM tool planner.
  - Done: AI service discovers backend function definitions and calls registered tools through code.
  - Still partial: future function-calling or tool-use agent exploration remains a plan item.
- Frontend presentation is outside the AI module ownership boundary.
  - AI-owned: structured statuses, coverage metadata, and analysis trace events.
  - Frontend-owned: labels such as `Performance Check`, layout, visual hierarchy, and demo-friendly copy.

## Todo

- CapitalFlowAgent remains a data-dependent future extension: no upstream
  fund-flow data source exists yet, so it is intentionally not registered
  (documented in `contracts.md` instead of shipping a permanently-skipped
  agent).
- Optional follow-ups: extend the shared dynamic-confidence helper to the
  exposure/sentiment/sector/bond agents, and archive more real-model outputs
  against `prompt_version` for the evaluation records.
- Consider a dedicated ProfitabilityAgent only if the team wants
  `get_fund_profit_probability` as a first-class view separate from
  `MarketAgent`.
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

- Continue the narrowed Phase 1.5 engineering hardening plan in this order:
  clean up Agent-side backend data handling, add structured `top_holdings` /
  `profit_probability` / `individual_analysis` fields, unify dynamic confidence,
  add explicit `is_mock`, add timeout / `429` / `5xx` LLM retry, sanitize Agent
  HTTP `500`, tests, and docs. Leave backend optional-tool concurrency for a
  later performance pass after future agent inputs are more stable. Then move to
  Phase 2 evidence and evaluation hardening.

### 2026-06-18 - Add Phase 1.5 engineering hardening plan

Goal:

- Make the pre-Phase-2 engineering hardening scope explicit in the active plan
  so it is not confused with prompt-language tuning or broader evidence work.
- Capture the newly verified P0 real-LLM client gap: reasoning models may
  return empty `content` when token budget is exhausted, while the current
  client lacks finish-reason handling and retry.

Actual changes:

- Added `Phase 1.5: Engineering Hardening Before Evidence Work` to
  `implementation_plan.md`.
- Clarified that the P0 item is LLM client robustness for real providers,
  followed by backend tool-call concurrency, structured context fields,
  dynamic confidence, explicit mock/real mode, sanitized errors, tests, and
  docs.
- Updated this ledger's current known gaps and todo list so future readers know
  Phase 1.5 is planned but not yet implemented.

Impact:

- Documentation only.
- No runtime code, API contract, prompt behavior, backend, frontend behavior, or
  test fixture changes.

Verification:

```bash
rg -n "Phase 1.5|finish_reason=length|empty-content|Engineering Hardening" ai_agent/fund_llm_engine/docs
```

Known unfinished work:

- Implement the Phase 1.5 code changes and add the corresponding regression
  tests.

### 2026-06-18 - Move completed Phase 1 out of active roadmap

Goal:

- Prevent the completed bond-aware baseline from looking like unfinished future
  work in the forward-looking implementation plan.

Actual changes:

- Moved Phase 1 under a completed-stage archive in
  `implementation_plan.md`.
- Kept the Phase 1 goal, implemented items, and completion markers for
  traceability, but made the active recommended sequence start at Phase 1.5.
- Clarified that deeper fixed-income analytics are future enhancements after
  richer backend fields exist, not unfinished Phase 1 baseline work.

Impact:

- Documentation only.
- No runtime code, API contract, prompt behavior, backend, frontend behavior, or
  test fixture changes.

Verification:

```bash
rg -n "已完成阶段归档|Phase 1: Bond-Aware Exposure Baseline \\(Completed\\)|推荐实施顺序|Phase 1.5" ai_agent/fund_llm_engine/docs/implementation_plan.md
```

### 2026-06-24 - Harden real LLM client empty-response handling

Goal:

- Prevent real provider failures from being displayed as normal agent narrative.
- Make `finish_reason=length`, empty `content`, and provider-specific
  `reasoning_content` presence diagnosable without exposing raw reasoning text
  or provider error bodies.

Actual changes:

- Added `LLMClient.chat_with_metadata()` and `last_response_metadata` while
  keeping `LLMClient.chat()` string-compatible for existing agents.
- Added one conservative retry for empty content when the first provider
  response has `finish_reason=length`; the retry expands `max_tokens` and
  disables thinking controls when they were configured.
- Replaced `"API returned empty response"` success-like fallback with
  `LLMEmptyResponseError`, so existing `safe_analyze()` paths mark the agent as
  `status="error"` instead of producing a fake success narrative.
- Sanitized HTTP provider failures so raw provider bodies are omitted from
  exception text.
- Added regression tests for empty-content retry, retry failure, non-length
  empty responses, diagnostics, and HTTP error sanitization.

Impact:

- AI Agent / LLM layer only.
- No frontend changes.
- No backend changes.
- Existing agent calls remain compatible because `chat()` still returns a
  string on success.

Verification:

```bash
cd ai_agent/fund_llm_engine
.venv/bin/python -m unittest tests/test_llm_client.py
.venv/bin/python -m unittest discover tests
```

Known unfinished work:

- Surface selected LLM diagnostic metadata into final analysis metadata or trace
  if the team wants frontend/debug tooling to see retry status directly.
- Continue the remaining Phase 1.5 items: structured `extra_context`, dynamic
  confidence, explicit analysis mode/status metadata, and broader docs.

### 2026-06-24 - Add per-request real-model override

Goal:

- Let the Agent module use one OpenAI-compatible provider API key/base URL while
  switching between supported model IDs such as `deepseek-v4-flash`,
  `deepseek-v4-pro`, `qwen3.7-plus`, or `glm-5.2`.
- Avoid requiring `.env` edits and service restarts for one-off model smoke
  tests.

Actual changes:

- `POST /api/ai/fund/analyze` accepts optional `llm_model` or `model` in real
  mode and passes it into `run_real_analysis_for_input()`.
- `scripts/run_real_demo.py` accepts `--model` for command-line smoke tests.
- Provider setup docs and `.env.example` explain the default-vs-override model
  selection rule.

Impact:

- AI Agent / LLM layer only.
- No frontend changes.
- No backend changes.
- If no model override is provided, behavior stays unchanged and uses
  `LLM_MODEL` from `.env`.

Verification:

```bash
cd ai_agent/fund_llm_engine
.venv/bin/python -m unittest tests/test_api_contract.py tests/test_demo_scripts.py
.venv/bin/python -m unittest discover tests
.venv/bin/python scripts/run_real_demo.py examples/mock_input.json \
  --model deepseek-v4-pro \
  --max-parallel-agents 1 \
  --output /private/tmp/fundmasterai_real_smoke_deepseek_pro_20260624.json
```

Known unfinished work:

- Consider adding a dedicated diagnostic endpoint for provider model discovery
  if the team wants to list supported models from the Agent service itself.

### 2026-06-24 - Replace Phase 1.5 with narrowed Agent hardening scope

Goal:

- Make Phase 1.5 executable instead of broad by pinning it to Agent-only
  engineering hardening.
- Preserve the ownership boundary: only `ai_agent/fund_llm_engine`, no backend
  or frontend changes.
- Keep English output behavior unchanged for the HKU capstone deliverable.

Actual changes:

- Replaced the active Phase 1.5 section in `implementation_plan.md` with the
  narrowed scope:
  Agent-owned backend data handling, structured `top_holdings` /
  `profit_probability` / `individual_analysis` fields, unified dynamic
  confidence, explicit `is_mock`, timeout / `429` / `5xx` LLM retry, sanitized
  Agent HTTP `500`, tests, and docs.
- Explicitly moved LLM-call consolidation and agent/overall score calibration
  out of Phase 1.5.
- Explicitly kept `Write in clear user-facing English` and
  `_summary_looks_incomplete` unchanged.
- Updated this ledger's Todo and next suggested work to match the narrowed plan.

Impact:

- Documentation only.
- No runtime code, API contract, prompt behavior, backend, frontend behavior, or
  test fixture changes in this task entry.

Verification:

```bash
rg -n "Phase 1.5|AI Agent Engineering Hardening|LLM 调用合并|dynamic confidence|is_mock|500" ai_agent/fund_llm_engine/docs
```

Known unfinished work:

- Implement the narrowed Phase 1.5 code changes in the documented order.

### 2026-06-24 - Defer backend tool concurrency out of Phase 1.5

Goal:

- Avoid doing backend optional-tool concurrency before future agent input needs
  are stable.
- Keep Phase 1.5 focused on foundations that reduce future rework: clearer
  Agent-side data handling, structured fields, confidence, and robustness.

Actual changes:

- Updated `implementation_plan.md` so Phase 1.5 starts with clearer Agent-side
  backend data handling plus structured `top_holdings` / `profit_probability` /
  `individual_analysis` fields, not immediate `ThreadPoolExecutor` concurrency.
- Moved backend optional-tool concurrency to a later performance optimization
  after MarketAgent / CapitalFlowAgent and related input fields are clearer.
- Kept the future concurrency constraints documented in plain language: only
  parallelize independent optional calls, keep trace output stable, and preserve
  the current `portfolio_year` fallback behavior.
- Updated this ledger's Todo and next suggested work accordingly.

Impact:

- Documentation only.
- No runtime code, API contract, prompt behavior, backend, frontend behavior, or
  test fixture changes in this task entry.

Verification:

```bash
rg -n "后续性能优化|并发化先不作为 Phase 1.5|今年没有持仓就取去年" ai_agent/fund_llm_engine/docs
```

Known unfinished work:

- Implement Phase 1.5 without adding backend concurrency yet.

### 2026-06-24 - Rewrite Phase 1.5 plan in plain implementation language

Goal:

- Make the Phase 1.5 plan read like an executable task list for the team, not an
  abstract architecture note.

Actual changes:

- Rewrote the active Phase 1.5 section in `implementation_plan.md` with plainer
  wording:
  scope, already-completed items, remaining work, completion markers, risks,
  and later performance optimization.
- Kept the intended substance unchanged: Agent-only work, no backend/frontend
  changes, no LLM-call consolidation, no score recalibration, English output
  unchanged, and backend optional-tool concurrency deferred.
- Updated this ledger's Todo and next suggested work to use the same wording.

Impact:

- Documentation only.
- No runtime code, API contract, prompt behavior, backend, frontend behavior, or
  test fixture changes in this task entry.

Verification:

```bash
rg -n "只改|现在不做并发|今年没有持仓就取去年|不要在本期" ai_agent/fund_llm_engine/docs/implementation_plan.md
```

Known unfinished work:

- Implement the Phase 1.5 code changes described by the plain-language plan.

### 2026-06-24 - Add OpenCode multi-model catalog and AI Insights picker

Goal:

- Let the team use one OpenAI-compatible gateway API key while switching models
  without applying to each vendor separately.
- Expose a model catalog for the AI Insights integration page and keep per-run
  `llm_model` override behavior.

Actual changes:

- Added `fund_llm.llm_models` with static chat/completions allowlist, optional
  live `{LLM_BASE_URL}/models` discovery, cache, and `LLM_ALLOWED_MODELS`
  filtering.
- Added `GET /api/ai/llm/models` and extended `/health` with
  `default_llm_model` / `llm_base_url`.
- Updated `frontend_new/ai-insights.html` and `frontend_new/js/ai-insights.js`
  to load the catalog, enable a model dropdown in real LLM mode, and send
  `llm_model` with analysis requests.
- Updated `contracts.md`, `provider_setup.md`, `.env.example`, and tests.

Impact:

- AI Agent service plus the AI Insights integration page.
- No backend market/news/portfolio code changes.
- Backward compatible: existing analyze requests still work without `llm_model`.

Verification:

```bash
cd ai_agent/fund_llm_engine
.venv/bin/python -m unittest discover tests
.venv/bin/python scripts/run_golden_suite.py --mode mock
node --check frontend_new/js/ai-insights.js
```

Known unfinished work:

- Models that require `/v1/messages` instead of chat/completions remain excluded
  until `LLMClient` grows a second transport path.

### 2026-07-02 - Make Performance/Risk confidence data-driven (Phase C)

Goal:

- Replace the hard-coded `PerformanceAgent` (`0.78`) and `RiskAgent` (`0.80`)
  confidence values with a data-quality-driven calculation, aligned with the
  dynamic-confidence style already used by exposure/sentiment/sector/bond
  agents.

Actual changes:

- Added `data_driven_confidence()` to `agents/base.py`: signals are NAV point
  count (up to +0.20 at 252 points), available rolling return window count
  (+0.04 each, up to 4), benchmark presence (+0.06), and required-flag
  completeness (up to +0.08); output clamped to `0.4-0.9`.
- `PerformanceAgent` and `RiskAgent` now call the helper instead of returning
  fixed values. Other agents keep their existing dynamic confidence logic.
- Added `DataDrivenConfidenceTest` regression tests (rich data high, sparse
  data low, required-flag sensitivity).
- Regenerated `examples/mock_output.json`; `average_confidence` for the 5-point
  mock payload moved from `0.78` to `0.68` as expected.

Impact:

- AI Agent layer only; no backend/frontend changes.
- Public API shape unchanged; only `confidence` values and derived
  `average_confidence` metadata move with data quality.
- Golden suite expectations did not assert fixed confidence values, so all 8
  cases still pass unchanged.

Verification:

```bash
cd ai_agent/fund_llm_engine
.venv/bin/python -m unittest discover tests
.venv/bin/python scripts/run_golden_suite.py --mode mock
```

### 2026-07-02 - Add portfolio-level analysis MVP (Phase A1)

Goal:

- Deliver the proposal-promised portfolio-level analysis as a stable JSON API
  without depending on portfolio_backend or frontend changes.

Actual changes:

- Added `POST /api/ai/portfolio/analyze` to `app.py` with the same
  `code/data/coverage/message` envelope and `mock` / `llm_model` /
  `llm_timeout_seconds` request options as the fund endpoint.
- Added `src/fund_llm/portfolio_analysis.py`: weight validation and
  normalization (positive weights, no duplicate codes, auto rescale),
  NAV date intersection with a 30-point minimum overlap, fixed-weight
  daily-rebalanced composition (portfolio daily return = weighted average of
  constituent daily returns, compounded), per-constituent metrics on the
  shared window, and portfolio quant metrics including
  `weighted_average_volatility` and `diversification_benefit` (non-negative
  by construction).
- Added portfolio contracts to `contracts.py`: `PortfolioPosition`,
  `PortfolioFundData`, `PortfolioAnalysisInput`,
  `PortfolioConstituentMetrics`, `PortfolioAnalysisResult`.
- Added `build_portfolio_input_from_backend_functions()` to
  `adapters/backend_function_client.py`: light per-fund fetch
  (`get_fund_hist` + `get_fund_individual_basic_info` only); any missing NAV
  raises `ValueError` listing the failing codes (HTTP `422`), basic-info
  failure degrades to code/unknown labels. The input `analysis_window` and
  `request_id` date use the shared NAV-date intersection (same
  `intersect_nav_dates()` helper the composition uses), not the union of all
  fund date ranges, so the input window always matches the actually analyzed
  window; an empty intersection leaves the window unset with a
  `no-shared-window` request-id placeholder and lets the pipeline raise the
  structured `422`.
- Added `agents/portfolio_chief_agent.py` (deterministic score/rating plus
  LLM explanation with deterministic fallback) and
  `portfolio_pipeline.py` (mock/real orchestration with alignment,
  composition, and aggregation trace events).
- Added tests: `test_portfolio_analysis.py` (15 math/validation cases),
  `test_portfolio_pipeline.py` (8 pipeline cases),
  `test_portfolio_api.py` (6 endpoint contract cases), plus 3 adapter cases in
  `test_backend_function_client.py`.
- Added `examples/portfolio_input_demo.json` and the portfolio section in
  `docs/contracts.md`.

Impact:

- New additive endpoint; existing fund-level API is unchanged (covered by a
  regression test).
- No backend or frontend code changes; frontend can adopt the endpoint on the
  portfolio/overview page when ready.

Verification:

```bash
cd ai_agent/fund_llm_engine
.venv/bin/python -m unittest discover tests
.venv/bin/python scripts/run_golden_suite.py --mode mock
curl -s -X POST http://127.0.0.1:5003/api/ai/portfolio/analyze \
  -H 'Content-Type: application/json' \
  -d @examples/portfolio_input_demo.json
```

Known unfinished work:

- Phase A2 holdings look-through and sector-level aggregation remain planned.
- Real-LLM portfolio summary quality review should be added to the manual
  acceptance checklist when real-mode smoke tests run.

### 2026-07-02 - Promote backend tool results to structured input fields

Goal:

- Stop treating `top_holdings`, `profit_probability`, and
  `individual_analysis` as `extra_context` JSON-preview strings so downstream
  logic (starting with the A2 look-through) can read them reliably.

Actual changes:

- Added `top_holdings`, `profit_probability`, `individual_analysis` list
  fields to `FundAnalysisInput` with `from_dict` support (single dict results
  are wrapped into one-element lists via `_records_from_payload`).
- `FundFeaturePack` passes the three fields through; `data_quality_flags`
  gained `has_top_holdings` / `has_profit_probability` /
  `has_individual_analysis`, and `data_quality_metrics` gained the matching
  counts.
- `build_fund_input_from_backend_functions` now fills the structured fields;
  the `extra_context` `_json_preview` entries remain for trace display only.
- `/api/ai/fund/analyze` `coverage` gained `has_top_holdings`,
  `has_profit_probability`, `has_individual_analysis`.

Impact:

- Additive only: no existing field changed shape; golden suite unchanged.

Verification:

```bash
cd ai_agent/fund_llm_engine
.venv/bin/python -m unittest tests.test_contracts tests.test_backend_function_client tests.test_feature_builder tests.test_api_contract
```

### 2026-07-02 - Add portfolio holdings look-through (Phase A2)

Goal:

- Turn the portfolio endpoint from NAV-level composition into real exposure
  analysis: merged top holdings, overlapping positions across funds,
  portfolio-weighted industry exposure, and merged stock/bond/cash allocation.

Actual changes:

- `PortfolioFundData` gained optional `top_holdings` / `industry_exposure` /
  `asset_allocation`; `build_portfolio_input_from_backend_functions` fetches
  them per fund as degradable optional calls (`include_lookthrough` request
  flag, default true; `top_holdings_n` default 10) with the current-year /
  previous-year fallback used by the fund path.
- Added `build_holdings_lookthrough` / `build_industry_lookthrough` /
  `build_asset_allocation_lookthrough` to `portfolio_analysis.py`: per-holding
  portfolio contribution = fund weight x weight in fund; overlap detection
  for stocks held by 2+ funds; unified `available` / `partial` / `missing`
  statuses with `funds_without_data` lists (bond funds without stock holdings
  are listed, not faked).
- `PortfolioAnalysisResult` and the HTTP response gained
  `holdings_lookthrough`, `industry_lookthrough`,
  `asset_allocation_lookthrough` plus matching metadata statuses and a
  `Merged constituent holdings look-through` trace event.
- `PortfolioChiefAgent` states look-through evidence (top combined holding,
  overlap warning, top sector concentration, asset mix) only when statuses
  allow, and feeds the same evidence into the LLM prompt.
- `disclosure_basis=quarterly_top10_holdings` marks the partial-disclosure
  limitation explicitly.

Impact:

- Additive fields on the portfolio contract; NAV-level metrics unchanged.
- No backend or frontend code changes.

Verification:

```bash
cd ai_agent/fund_llm_engine
.venv/bin/python -m unittest tests.test_portfolio_analysis tests.test_portfolio_pipeline tests.test_portfolio_api tests.test_backend_function_client
```

### 2026-07-02 - Add sector-level comparison endpoint (Phase B1)

Goal:

- Deliver the proposal-promised sector-level view as a stable JSON API:
  compare multiple funds' industry exposure side by side without requiring
  NAV data or portfolio weights.

Actual changes:

- Added `sector_view.py` (deterministic matrix: per-fund sector status
  aligned with `SectorAgent` semantics, sectors ranked by equal-weight
  average across funds with data, `common_sectors` for 2+ fund overlaps) and
  `sector_pipeline.py` (mock/real LLM summary with deterministic fallback and
  trace events).
- Added `build_sector_view_funds_from_backend_functions` light fetch (basic
  info + industry allocation only, both degradable).
- Added `POST /api/ai/sector/analyze` with the standard
  `code/data/coverage/message` envelope; duplicate or empty codes return
  structured `422`/`400`.

Impact:

- New additive endpoint; existing fund and portfolio APIs unchanged.

Verification:

```bash
cd ai_agent/fund_llm_engine
.venv/bin/python -m unittest tests.test_sector_view tests.test_sector_api
.venv/bin/python -m unittest discover tests
.venv/bin/python scripts/run_golden_suite.py --mode mock
```

### 2026-07-03 - Phase D hardening: is_mock, LLM transport retry, sanitized 500

Goal:

- Close the remaining engineering-hardening items so provider hiccups and
  internal errors behave predictably in demos.

Actual changes:

- Added explicit `is_mock` class attributes to `LLMClient` (False) and
  `MockLLMClient` (True); `chief_agent`, `portfolio_chief_agent`, and
  `sector_pipeline` now use `getattr(client, "is_mock", False)` instead of
  class-name string comparison.
- `LLMClient._post_json` retries once with a 1.5s backoff for timeout /
  `429` / `500` / `502` / `503` / `504`; `400` / `401` / `403` and
  non-timeout transport errors are raised immediately. `LLMHTTPError` carries
  `status_code`, `LLMTransportError` carries `is_timeout`, and response
  metadata gains `transport_retry_count`.
- All three Agent HTTP endpoints return a generic `500` message; the full
  exception goes to the service log only.

Impact:

- No public success-path contract changes; `500` body text changed from raw
  exception text to a fixed generic message (documented in `contracts.md`).

Verification:

```bash
cd ai_agent/fund_llm_engine
.venv/bin/python -m unittest tests.test_llm_client tests.test_api_contract tests.test_portfolio_api tests.test_sector_api
```

### 2026-07-03 - Add MarketAgent peer/market context (Phase B2 lightweight)

Goal:

- Fulfil the proposal's broader market-context view using data the backend
  already serves, without letting the LLM invent macro narratives.

Actual changes:

- Added `agents/market_agent.py`: evidence is the structured
  `individual_analysis` peer percentiles (`risk_return_ratio_vs_peers`,
  `risk_robustness_vs_peers` per period) and `profit_probability`
  holding-period win rates; deterministic score starts at 55 and moves with
  peer percentile and win-rate distance from 50; confidence uses the shared
  `data_driven_confidence` helper; both datasets missing yields
  `skipped + insufficient_data`.
- Registered the agent in mock/real pipelines (7 specialist agents now),
  `AGENT_TRACE_COPY`, chief display names, `evaluation.CORE_AGENT_NAMES`,
  and `score_guardrails` `DATA_SENSITIVE_AGENTS`.
- `build_mock_input` now carries sample peer/probability rows so the mock
  baseline demonstrates MarketAgent success; golden manifest requires
  `MarketAgent` in all 8 cases (static legacy inputs exercise the skipped
  path).
- CapitalFlowAgent is intentionally not registered: no upstream fund-flow
  data source exists, documented as a future extension.
- Added `PROMPT_VERSION` (`config.py`) surfaced as `prompt_version` metadata
  in fund, portfolio, and sector results for evaluation traceability.

Impact:

- `agent_outputs` gains one additional item (additive, matches the existing
  `AgentOutput` shape); fund analyses of funds without peer data show
  `MarketAgent` as `skipped + insufficient_data` rather than failing.

Verification:

```bash
cd ai_agent/fund_llm_engine
.venv/bin/python -m unittest discover tests
.venv/bin/python scripts/run_golden_suite.py --mode mock
.venv/bin/python scripts/run_mock_demo.py --output examples/mock_output.json
```

### 2026-07-03 - Stabilize real-LLM chief summaries and degrade news-registry outages

Goal:

- Stop the chief summary from silently falling back to deterministic text in
  real-LLM demos, and stop a news-backend outage from failing whole analyses.

Actual changes:

- Root cause of frequent `summary_source=deterministic_fallback`: the model
  sometimes answered in Chinese; `_summary_looks_incomplete()` counts
  whitespace-separated words, so Chinese text scored ~2 "words" and was
  rejected. Added an explicit "Respond in English only" instruction to the
  fund chief, portfolio chief, and sector summary system prompts
  (`PROMPT_VERSION` bumped to `2026-07-03.2`); verified 3/3 real
  `deepseek-v4-pro` runs now keep `summary_source=llm`.
- Widened summary output budgets: fund chief `max_tokens` 700 -> 1100,
  portfolio chief 700 -> 1000, sector summary 600 -> 900.
- `discover_fund_tools()` now treats the news (and optional portfolio)
  registry as degradable: discovery failure logs a warning and continues, so
  a dead news backend yields `SentimentAgent skipped + insufficient_data`
  instead of an HTTP 500 (regression test added).

Impact:

- AI Agent layer only; English-output requirement is unchanged, now enforced
  harder for mixed-language inputs.

Verification:

```bash
cd ai_agent/fund_llm_engine
.venv/bin/python -m unittest discover tests
.venv/bin/python scripts/run_golden_suite.py --mode mock
```

### 2026-07-07 - Add news summary endpoint for the News page

Goal:

- Close the integration blocker "AI 服务没有新闻摘要接口" from the 2026-07-07
  frontend integration issue list: the News page AI Summary widget needs
  `POST /api/ai/news/summary`.

Actual changes:

- Added `src/fund_llm/news_summary.py`: normalizes raw news-backend rows
  (Chinese/English field names accepted as-is), classifies each item with the
  deterministic `SentimentAgent` keyword rules, computes aggregate
  label/counts/risk-event count and data-quality confidence (0.4-0.9) in
  code, and lets the LLM only write the digest (English-only prompt,
  quality-gate fallback to a deterministic summary).
- `related_symbols` echoes the request `symbol` only; the model is never
  asked to infer ticker symbols from text.
- Added `POST /api/ai/news/summary` to `app.py` with the standard
  `code/data/coverage/message` envelope, `items`/`news` aliases,
  `max_items` cap (default 10, hard cap 20), mock/real modes, structured
  `400`/`422`, and sanitized `500`.
- Tests: `tests/test_news_summary.py` (13 unit cases) and
  `tests/test_news_api.py` (6 endpoint contract cases).

Impact:

- New additive endpoint; existing fund/portfolio/sector APIs unchanged.
- No backend or frontend code changes; the frontend can forward
  `get_recent_news` rows unmodified.

Verification:

```bash
cd ai_agent/fund_llm_engine
.venv/bin/python -m unittest tests.test_news_summary tests.test_news_api
.venv/bin/python -m unittest discover tests
.venv/bin/python scripts/run_golden_suite.py --mode mock
```

### 2026-07-10 - Separate data, provider, and technical failures from investment ratings

Goal:

- Prevent tiny NAV samples or infrastructure failures from being translated into
  BUY/HOLD/WATCH/AVOID, and make the evaluator reject error-heavy outputs.

Actual changes:

- Added a 30-NAV publication floor. `PerformanceAgent` and `RiskAgent` return
  `skipped + insufficient_data` below the floor; Chief returns
  `overall_rating=insufficient_data` and `overall_score=null` and suppresses
  degenerate annualized metric tiles.
- Specialist LLM calls now use `explain_or_fallback()`. Provider/empty-response
  failures retain deterministic scores and expose
  `metadata.narrative_source=deterministic_fallback`; only deterministic
  calculation failures become Agent errors.
- Removed the `-3 per error` financial penalty. A non-core specialist error is
  excluded and the remaining scores can still produce
  `analysis_status=partial` when Performance/Risk, at least 3 scores, and 60%
  applicable-agent coverage remain. Core failure or sub-quorum coverage returns
  `overall_rating=unavailable` with a null score.
- Quorum uses the fixed fund-routing expectation rather than the returned list
  length: missing/skipped/error outputs remain in the denominator, only routed
  `not_applicable` agents are removed, and duplicate/non-finite/out-of-range
  scores cannot inflate coverage.
- Added evaluator and golden-suite execution-health gates. Technical errors can
  no longer receive automatic structure credit or an overall PASS; legal
  `insufficient_data` and `not_applicable` skips remain valid.
- Updated the AI Insights UI to show `INSUFFICIENT DATA` / `NOT RATED`, hide null
  scores, and distinguish a narrative fallback from a scoring failure.

Verification:

```bash
cd ai_agent/fund_llm_engine
.venv/bin/python -m unittest discover -s tests  # 229 passed
.venv/bin/python scripts/run_golden_suite.py --mode mock  # 8/8 passed
```

## Handoff Notes For Future AI

- Do not infer implemented status from proposal, plan, or report wording alone.
- Check this document, then inspect code paths and tests before claiming a feature is complete.
- Treat `implementation_plan.md` as future planning unless this ledger or code proves the item is done.
- Treat `version_history.md` as milestone/tag history, not a complete current-state ledger.
- Runtime secrets, including LLM API keys, must stay runtime-only and must not be written into repository files.
- The default maintenance branch for this ledger is `aiagent-use-dev-backend`; do not update other branches unless the user explicitly asks.
