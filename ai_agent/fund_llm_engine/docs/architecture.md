# AI Agent Architecture

Last reconciled with the integrated codebase: 2026-07-15.

## Responsibility

`fund_llm_engine` is the intelligent analysis layer. It does not replace the
Market/News/Portfolio services and it does not calculate numbers by asking the
LLM to guess them.

It is responsible for:

- loading registered backend tools through HTTP;
- normalizing backend data into stable contracts;
- calculating deterministic return, risk, exposure, coverage, and comparison
  features;
- routing fund types to applicable specialist Agents;
- generating mock or real-model narratives around those features;
- aggregating eligible specialist results through a Chief;
- returning coverage and an explainability trace.

## Runtime Path

```text
Frontend / API client
  -> Flask Agent service (app.py)
     -> BackendFunctionClient
        -> Market / News / Portfolio function registries
     -> FundAnalysisInput or Portfolio/Sector input
     -> deterministic feature/routing layer
     -> specialist Agents (parallel when more than one worker is allowed)
     -> ChiefAgent or PortfolioChiefAgent (serial aggregation)
     -> JSON result + coverage + analysis_trace
```

## HTTP Interfaces

| Method and path | Purpose |
|---|---|
| `GET /health` | Service and configuration health metadata |
| `GET /api/ai/llm/models` | Allowed/discovered model catalog |
| `GET /api/ai/functions` | Backend tools visible to the Agent service |
| `POST /api/ai/fund/analyze` | Single-fund multi-agent analysis |
| `POST /api/ai/portfolio/analyze` | Portfolio NAV composition and look-through analysis |
| `POST /api/ai/sector/analyze` | Cross-fund sector comparison |
| `POST /api/ai/news/summary` | Summary of the news rows supplied by the frontend |

Stable request/response fields are documented in
[`contracts.md`](./contracts.md).

## Fund Specialist Set

- `PerformanceAgent`: absolute/window returns, drawdown, and benchmark context;
- `RiskAgent`: volatility, drawdown, window support, and risk suitability;
- `ExposureAgent`: equity/industry/top-holdings concentration when applicable;
- `BondExposureAgent`: disclosed bond holdings and asset allocation for
  fixed-income routes;
- `SentimentAgent`: recent news and announcement evidence;
- `SectorAgent`: sector concentration/context when industry data is applicable;
- `MarketAgent`: peer percentile and historical holding-period profit evidence;
- `ChiefAgent`: eligible-score aggregation, failure isolation, rating gates,
  summary, and action text.

`ExposureAgent` and `BondExposureAgent` are both registered, but routing and
coverage determine whether each one succeeds, is not applicable, or has
insufficient data. A skipped Agent is not automatically a system failure.

Portfolio analysis uses a separate `PortfolioChiefAgent`. Sector comparison and
news summary use their own pipelines rather than pretending to be single-fund
specialists.

## Deterministic Versus LLM Work

Deterministic code owns:

- backend calls and unit normalization;
- feature calculation and data-quality flags;
- fund-type routing and applicability;
- specialist scores, confidence inputs, stances, and rating eligibility;
- technical-error and missing-data states.

The LLM owns narrative explanation. If a provider fails, eligible specialist
metrics can use a deterministic narrative fallback; a provider failure must not
silently change the underlying score.

## Failure Semantics

The frontend can distinguish:

- `success`: the module produced an evidence-backed result;
- `insufficient_data`: applicable, but required evidence is missing;
- `not_applicable`: the module does not fit this fund type;
- `error`: a technical failure occurred.

Chief rating publication is guarded by NAV sufficiency, core-agent health, and
coverage policies. The service returns sanitized HTTP 500 messages while full
exceptions remain in server logs.

## Module Map

| Path | Role |
|---|---|
| `app.py` | Flask endpoints and response envelopes |
| `src/fund_llm/contracts.py` | Request, feature, Agent, and result dataclasses |
| `src/fund_llm/adapters/` | Backend registry discovery and ingestion |
| `src/fund_llm/feature_builder.py` | Deterministic feature construction |
| `src/fund_llm/fund_routing.py` | Fund-family normalization and applicability |
| `src/fund_llm/agents/` | Specialist and Chief implementations |
| `src/fund_llm/orchestration/engine.py` | Parallel specialists and serial aggregation |
| `src/fund_llm/evaluation.py` | Automatic quality checks and gates |
| `tests/` | Unit/regression tests |

The longer [`agent_architecture_design.md`](./agent_architecture_design.md) is a
historical design rationale. Where it differs from this file or the contracts,
the current code, contracts, and this architecture summary take precedence.
