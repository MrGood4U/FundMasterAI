# AI Agent + Dev Backend Integration Handoff

Date: 2026-05-30

This document records the current state of the temporary integrated demo, what has been verified, what is still missing, and what should be done next. It is meant as a restart point for future development, so we do not have to rely on chat context.

## Current Branch And Location

Active integration worktree:

```text
/private/tmp/fundmaster-aiagent-use-dev-backend
```

Active branch:

```text
aiagent-use-dev-backend
```

Remote branch:

```text
https://github.com/MrGood4U/FundMasterAI/tree/aiagent-use-dev-backend
```

Purpose of this branch:

- Start from the team's latest `dev` backend.
- Restore and connect the AI agent engine.
- Let frontend call the AI service.
- Let AI service call real backend APIs through the backend function registry.
- Avoid hard-coded mock data for the demo path.

Previous stable snapshot tag:

```text
aiagent-demo-real-data-v1
```

## Current Demo Architecture

The current working demo has four local services:

```text
frontend_new
  -> AI service /api/ai/fund/analyze
      -> market_backend function registry
      -> news_backend function registry
      -> fund_llm_engine multi-agent pipeline
```

Local ports currently used:

```text
market_backend: http://127.0.0.1:5001
news_backend:   http://127.0.0.1:5010
ai service:     http://127.0.0.1:5003
frontend:       http://127.0.0.1:8003/ai-insights.html
```

Note: `news_backend` uses `5010` locally because macOS may occupy port `5000`.

## What Has Been Implemented

### AI Engine Routing Update

Implemented after the initial handoff:

```text
FundTypeRouter
DataCoverageChecker
not_applicable agent handling
coverage metadata in AI responses
```

Key files:

```text
ai_agent/fund_llm_engine/src/fund_llm/fund_routing.py
ai_agent/fund_llm_engine/src/fund_llm/feature_builder.py
ai_agent/fund_llm_engine/src/fund_llm/agents/exposure_agent.py
ai_agent/fund_llm_engine/src/fund_llm/agents/sector_agent.py
ai_agent/fund_llm_engine/src/fund_llm/agents/chief_agent.py
```

The AI engine now uses deterministic rules based on backend `fund_type` instead of LLM judgment.

Examples:

```text
债券型-债券指数 -> bond_index_fund
混合型-偏股     -> mixed_fund
股票型         -> equity_fund
指数型         -> stock_index_fund
```

For bond-like funds:

- `ExposureAgent` no longer treats missing stock holdings as a neutral signal.
- `SectorAgent` no longer treats missing equity industry exposure as a neutral signal.
- Both return `status=skipped` and `stance=not_applicable`.
- `ChiefAgent` does not treat `not_applicable` as an unhealthy partial failure.
- Missing bond-specific backend abilities are reported as `missing_backend_capability`.

The AI response now includes structured coverage metadata such as:

```text
coverage_nav
coverage_stock_holdings
coverage_industry_exposure
coverage_bond_holdings
coverage_asset_allocation
normalized_fund_type
fund_family
```

### AI Service

File:

```text
ai_agent/fund_llm_engine/app.py
```

Important endpoints:

```text
GET  /health
GET  /api/ai/functions
POST /api/ai/fund/analyze
```

The frontend calls:

```text
POST http://127.0.0.1:5003/api/ai/fund/analyze
```

Important behavior:

- `mock: false` or no `mock` field means real backend + real LLM mode.
- `mock: true` runs the mock pipeline for quick debugging.
- If backend returns no NAV data, AI service returns HTTP `422`.
- `422` means the request format is valid, but the submitted fund code/data cannot be processed.

### Backend Function Registry Client

File:

```text
ai_agent/fund_llm_engine/src/fund_llm/adapters/backend_function_client.py
```

What it does:

- Discovers backend tools from:
  - `GET /api/market/functions?tag=fund`
  - `GET /api/news/functions?tag=fund`
- Calls backend functions using their registered `path`, `method`, and parameter schema.
- Builds `FundAnalysisInput` for the existing AI agent pipeline.

Currently called backend functions:

```text
get_fund_hist
get_fund_individual_basic_info
get_fund_portfolio_holds
get_public_fund_announcement
get_fund_individual_analysis
get_fund_profit_probability
```

### Frontend

Files:

```text
frontend_new/ai-insights.html
frontend_new/js/ai-insights.js
frontend_new/css/page-ai-insights.css
```

Current behavior:

- Frontend sends the user-selected fund code, start date, risk profile, and LLM flag to the AI service.
- Frontend displays:
  - final recommendation
  - agent outputs
  - data used
  - missing/skipped data
  - backend tool trace
- Error state now distinguishes analysis failure from a successful analysis with partial data.

## Verified Real-Data Demo Cases

### `000001`

Fund:

```text
000001 华夏成长混合
```

Status:

```text
success
```

Observed data:

- NAV available.
- Basic info available.
- Stock holdings available.
- Announcements/news available.
- Risk/profit analysis available.

Agent behavior:

- `PerformanceAgent`: success
- `ExposureAgent`: success
- `RiskAgent`: success
- `SentimentAgent`: success
- `SectorAgent`: skipped if industry exposure is missing

Why this is a good demo code:

- It exercises the real backend path.
- It has enough data for most agents.
- It shows graceful degradation when one data field is unavailable.

### `003358`

Fund:

```text
003358 易方达中债7-10年期国开行债券指数A
```

Backend basic info:

```text
fund_type = 债券型-债券指数
```

Observed data:

- NAV available.
- Basic info available.
- Announcements available.
- Current stock-holding endpoint returns 0 rows.

Agent behavior:

- `PerformanceAgent`: success
- `RiskAgent`: success
- `SentimentAgent`: success
- `ExposureAgent`: skipped
- `SectorAgent`: skipped

Why two agents are skipped:

- `ExposureAgent` currently needs at least `industry_exposure` or `top_holdings_weight`.
- `SectorAgent` needs `industry_exposure`.
- For this bond index fund, the current backend stock-holding API returns no holdings, so `top_holdings_weight` cannot be calculated.
- `industry_exposure` is not currently provided by the dev backend integration.

Important conclusion:

This is not an LLM hallucination bug. It is a data coverage and fund-type routing problem. Bond funds need bond-specific data and bond-specific agents.

### `000002`

Observed behavior:

```text
HTTP 422
```

Reason:

- The fund code appears in a name list as a backend/suffix variant.
- Current backend NAV lookup returns no NAV series for this code.
- The AI service correctly refuses to analyze it instead of fabricating a result.

## Current Data Coverage

Currently supported through the dev backend function registry:

```text
NAV history
fund basic info
fund stock holdings
fund announcements
fund risk/return analysis
fund profit probability
index fund info
fund rank/value estimation APIs
```

Currently missing or not yet connected:

```text
bond holdings
asset allocation
industry allocation
fund type routing
bond-specific exposure analysis
structured data coverage reporting
```

## Backend API Gap Analysis

Current backend has `get_fund_portfolio_holds`, but it maps to:

```python
ak.fund_portfolio_hold_em(symbol=code, date=year)
```

This is a stock-holdings interface. It works better for stock/mixed funds, but it is not enough for bond funds.

Useful AkShare functions found locally but not yet exposed through backend `function_registry.py`:

```text
fund_portfolio_bond_hold_em
fund_portfolio_industry_allocation_em
fund_individual_detail_hold_xq
fund_report_asset_allocation_cninfo
fund_report_industry_allocation_cninfo
```

Reality check for `003358`:

- `fund_portfolio_bond_hold_em(symbol="003358", date="2025")` returned bond holdings successfully.
- `fund_individual_detail_hold_xq(symbol="003358", date="20251231")` returned asset allocation such as bond/cash/other.
- `fund_portfolio_industry_allocation_em` failed for this bond fund, which is reasonable because equity industry exposure is not the right data model for a bond index fund.

Conclusion:

The data source is not hopeless. The current backend just has not exposed the required bond/asset allocation APIs yet.

## Fund Type Should Not Be Decided By LLM

Do not ask the LLM to guess whether a fund is stock, mixed, bond, index, QDII, etc.

The deterministic route should be:

```text
fund code
  -> get_fund_individual_basic_info
  -> read structured fund_type
  -> normalize fund_type in code
  -> choose allowed tools and agents
  -> run only applicable agents
  -> send evidence to LLM for explanation only
```

Example:

```text
003358
  fund_type = 债券型-债券指数
  normalized_type = bond_index_fund
  run:
    PerformanceAgent
    RiskAgent
    SentimentAgent
    BondExposureAgent
  skip:
    SectorAgent, because equity industry exposure is not applicable
```

The LLM should summarize evidence, not decide the data pipeline.

## Recommended Next Development Plan

### Step 1: Add Fund Type Router

Add deterministic classification inside the AI engine:

```text
fund_type string -> normalized_fund_type
```

Possible normalized types:

```text
equity_fund
mixed_fund
bond_fund
bond_index_fund
stock_index_fund
qdii_fund
fof_fund
money_market_fund
unknown_fund
```

The router should use:

- `fund_type` from `get_fund_individual_basic_info`
- optional `tracking_index` from `get_fund_info_index`
- no LLM judgment

### Step 2: Add Data Coverage Object

The AI response should include a structured coverage object:

```json
{
  "fund_type": "bond_index_fund",
  "data_coverage": {
    "nav": "available",
    "basic_info": "available",
    "stock_holdings": "not_applicable",
    "bond_holdings": "available",
    "asset_allocation": "available",
    "industry_exposure": "not_applicable"
  }
}
```

Frontend can display this directly.

### Step 3: Ask Backend To Add Missing APIs

Suggested backend functions:

```text
get_fund_bond_holdings
get_fund_asset_allocation
get_fund_industry_allocation
```

Suggested registry descriptions:

- `get_fund_bond_holdings`: returns bond code/name, net value percentage, market value, quarter.
- `get_fund_asset_allocation`: returns asset type percentages such as stock, bond, cash, other.
- `get_fund_industry_allocation`: returns equity industry exposure. This should be treated as not applicable for bond-only funds.

### Step 4: Add Bond-Aware Agent Logic

Do not force all funds through equity-style `ExposureAgent` and `SectorAgent`.

Add either:

```text
BondExposureAgent
```

or split `ExposureAgent` internally by normalized fund type.

For bond funds, useful signals include:

- bond holdings concentration
- bond/cash/other allocation
- government bond vs credit bond exposure if available
- duration or maturity proxy if available
- tracking index for bond index funds

### Step 5: Improve Frontend Explanation

Frontend should distinguish:

```text
success
skipped: insufficient data
skipped: not applicable for this fund type
error
```

This is important for demos. A skipped agent should not look like a broken system.

## Team Boundary Recommendation

Backend:

- Owns raw data APIs.
- Owns `function_registry.py` definitions.
- Should expose reusable fund data capabilities.

AI engine:

- Owns fund type routing.
- Owns tool selection.
- Owns agent orchestration.
- Owns hallucination prevention and data coverage logic.
- Returns frontend-ready analysis payload.

Frontend:

- Prefer calling the AI aggregate endpoint for AI analysis pages.
- Display final analysis, agent statuses, and data coverage.
- May directly call backend APIs for non-AI pages such as fund detail, portfolio, watchlist, or holdings pages.

Recommended message to teammates:

```text
AI engine needs deterministic fund-type routing and additional backend data APIs for asset-aware analysis. The most useful new backend functions are fund bond holdings, fund asset allocation, and fund industry allocation. Frontend AI pages can initially call only /api/ai/fund/analyze, while the AI service internally calls these backend tools and returns data coverage plus agent results. Other frontend pages can reuse the backend APIs directly if they need detail views.
```

## How To Resume Locally

From the integration worktree:

```bash
cd /private/tmp/fundmaster-aiagent-use-dev-backend
git status --short --branch
```

Check ports:

```bash
lsof -iTCP:5001 -sTCP:LISTEN
lsof -iTCP:5010 -sTCP:LISTEN
lsof -iTCP:5003 -sTCP:LISTEN
lsof -iTCP:8003 -sTCP:LISTEN
```

Open frontend:

```text
http://127.0.0.1:8003/ai-insights.html
```

Useful test fund codes:

```text
000001  mixed fund, good for demo
005827  mixed/blue-chip style, useful real-data test
161725  stock/index style, useful real-data test
003358  bond index fund, useful for testing fund-type routing gaps
000002  expected 422/no NAV data in current backend behavior
```

## Verification Already Done

Tests passed earlier on this branch:

```text
python3.11 -m unittest discover -s tests
49 tests OK
```

Frontend JavaScript syntax check passed:

```text
node --check frontend_new/js/ai-insights.js
```

Real non-mock demo for `000001` succeeded through:

```text
frontend -> AI service -> backend function registry -> real backend data -> real LLM
```

## High-Level Next Task List

1. Add backend function support for bond holdings, asset allocation, and industry allocation.
2. Add a bond-specific exposure agent once backend data is available.
3. Update frontend labels to separate `insufficient_data`, `not_applicable`, and `error`.
4. Add tests for the new backend data once those APIs exist:
   - equity/mixed fund route
   - bond fund route
   - no NAV / 422 route
   - missing holdings but valid NAV route
5. Re-run a real demo with:
   - `000001`
   - `003358`
   - one index fund
   - one intentionally invalid/no-NAV code
