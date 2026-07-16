# AI Agent API Contract

This document defines the stable HTTP interface exposed by the FundMasterAI AI
service. Source code and tests remain authoritative; compatible additions may
introduce new optional fields, Agent outputs, trace events, or registry entries.

## Base paths

In Docker, the browser uses same-origin `/api/ai/*` paths through Nginx. Native
Agent development uses `http://127.0.0.1:5003` by default.

Public endpoints:

```text
GET  /health
GET  /api/ai/functions
GET  /api/ai/llm/models
POST /api/ai/fund/analyze
POST /api/ai/portfolio/analyze
POST /api/ai/sector/analyze
POST /api/ai/news/summary
```

## Common response envelope

Successful analysis endpoints return HTTP `200` with:

```json
{
  "code": 200,
  "data": {},
  "coverage": {},
  "message": "success"
}
```

`data` contains the analysis result. `coverage` explains source-data
availability. `message` may distinguish a complete result, partial coverage,
narrative fallback, insufficient data, or incomplete technical execution.

Runtime secrets never belong in requests, responses, logs returned to clients,
or repository files.

## Fund analysis

```text
POST /api/ai/fund/analyze
Content-Type: application/json
```

Minimal request:

```json
{
  "code": "000001",
  "mock": true
}
```

Supported request fields include:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `code` | string | yes | Six-digit public-fund code |
| `start_date` | string | no | Analysis start date, accepted by backend loading logic |
| `end_date` | string | no | Analysis end date |
| `risk_profile` | string | no | User risk profile used by output framing |
| `mock` | boolean/string | no | Use deterministic mock narrative mode |
| `llm_model` | string | no | Per-request model override in real mode; `model` is an alias |
| `max_parallel_agents` | integer | no | Specialist concurrency limit |
| `max_nav_points` | integer | no | NAV sample cap |
| `max_news_items` | integer | no | News/announcement cap |
| `portfolio_year` | integer/string | no | Preferred holdings disclosure year |
| `top_holdings_n` | integer | no | Maximum disclosed top holdings requested |

The response `data` includes final rating fields, deterministic metrics,
specialist outputs, Chief narrative fields, metadata, and `analysis_trace`.

Publication rules:

- fewer than 30 usable NAV points produces `analysis_status=insufficient_data`,
  `overall_rating=insufficient_data`, and `overall_score=null`;
- technical core failure or insufficient specialist quorum produces
  `analysis_status=technical_error`, `overall_rating=unavailable`, and a null
  score;
- non-core missing data may produce a partial result when the fixed routing
  quorum is still satisfied;
- an LLM narrative failure does not erase valid deterministic scores. The
  service keeps the structured result and marks the narrative source as a
  deterministic fallback.

## Portfolio analysis

```text
POST /api/ai/portfolio/analyze
```

Minimal request:

```json
{
  "positions": [
    {"code": "000001", "weight": 0.6},
    {"code": "003358", "weight": 0.4}
  ],
  "mock": true
}
```

Important request fields:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `positions` | array | yes | Fund code and positive portfolio weight |
| `start_date` / `end_date` | string | no | Shared NAV window |
| `include_lookthrough` | boolean/string | no | Load holdings/industry/asset look-through; default `true` |
| `top_holdings_n` | integer | no | Per-fund holding cap |
| `max_nav_points` | integer | no | Per-fund NAV cap |
| `mock` / `llm_model` | mixed | no | Narrative mode and optional model override |

The service normalizes positive weights, rejects duplicate or empty fund codes,
loads each constituent's NAV, intersects trading dates, and builds a
fixed-weight daily-rebalanced series. The result can include:

- portfolio-level return, volatility, drawdown, and risk metrics;
- constituent metrics and the common analysis window;
- `holdings_lookthrough`, including overlapping disclosed top holdings;
- `industry_lookthrough` and `asset_allocation_lookthrough`;
- `PortfolioChiefAgent` summary, rating eligibility, metadata, and trace.

Look-through is explicitly partial because public fund disclosures generally
expose top holdings rather than complete real-time books.

## Sector comparison

```text
POST /api/ai/sector/analyze
```

Example:

```json
{
  "funds": ["000001", "161725"],
  "mock": true
}
```

The deterministic view returns per-fund classification and sector status,
top-sector exposures, a cross-fund sector matrix, common sectors, concentration
flags, metadata, and a mock/real summary with deterministic fallback.

Sector status is one of:

- `available`: structured sector data exists;
- `insufficient_data`: the view applies but upstream evidence is missing;
- `not_applicable`: the fund type should not be described as equity-sector
  exposure.

Duplicate or empty fund codes are rejected.

## News summary

```text
POST /api/ai/news/summary
```

Example:

```json
{
  "symbol": "300059",
  "items": [
    {
      "news_title": "Example title",
      "news_content": "Example content",
      "publish_time": "2026-07-16"
    }
  ],
  "mock": true
}
```

`news` is accepted as an alias for `items`. `max_items` defaults to 10 and is
capped at 20. Sentiment labels, counts, risk-event count, and confidence are
calculated deterministically; the LLM only writes the digest.

`related_symbols` echoes the requested `symbol` only. The model is not allowed
to infer tickers from article text. A request with no usable title or content
returns `422`.

## Agent output

Every specialist output follows one compatible shape:

```json
{
  "agent_name": "RiskAgent",
  "status": "success",
  "stance": "neutral",
  "score": 62.0,
  "confidence": 0.8,
  "summary": "...",
  "evidence": [],
  "risks": [],
  "metadata": {}
}
```

Stable semantics:

| Status / stance | Meaning |
|---|---|
| `success` | Deterministic calculation completed; narrative may still be a fallback |
| `skipped` + `insufficient_data` | Applicable view lacks required evidence |
| `skipped` + `not_applicable` | View does not apply to this routed fund type |
| `error` | Deterministic or technical execution failed |

Clients must not render skipped or unavailable outputs as investment ratings.
New specialist Agents may be appended to `agent_outputs` without changing the
existing item shape.

## Coverage and trace

Coverage reports what the backend actually supplied, such as NAV, fund type,
stock holdings, industry exposure, bond holdings, asset allocation, news, peer
analysis, and holding-period profit evidence.

Missing-data reasons distinguish at least:

- backend capability unavailable;
- data unavailable for this fund;
- not applicable to this fund type;
- backend or provider error.

`analysis_trace` is an ordered explanation of execution. Compatible releases
may append events or fields. Clients should use event labels and evidence for
display rather than assuming a permanently fixed trace length.

## Model catalog

```text
GET /api/ai/llm/models
```

The endpoint returns models allowed by the configured OpenAI-compatible gateway
and project compatibility rules. It never returns API keys. The live gateway
catalog may be narrowed by `LLM_ALLOWED_MODELS`.

## Errors

| HTTP status | Meaning |
|---:|---|
| `400` | Malformed JSON or required request shape missing |
| `422` | Request is structurally valid but cannot be analyzed, such as invalid weights, duplicate codes, missing NAV, too little overlap, or unusable news |
| `500` | Sanitized internal technical failure |

HTTP `500` responses do not expose raw exception or provider response bodies.
Detailed stack traces belong in server logs only.

## Compatibility rules

- preserve existing request names and response meanings;
- add fields and Agent outputs rather than renaming stable ones;
- keep percentage-point inputs and internal fractions unambiguous;
- keep unavailable data visible instead of fabricating replacements;
- update tests and both language entry points when public semantics change.
