# fund-llm-engine

`fund-llm-engine` is FundMasterAI's standalone multi-agent analysis package and
HTTP service. The complete project uses it through Docker Compose; this document
covers Agent-focused development and native debugging.

## Responsibilities

The module owns:

- deterministic feature calculation and data-coverage checks;
- fund-type routing;
- specialist Agent execution;
- Chief aggregation and rating eligibility;
- mock and OpenAI-compatible narrative generation;
- stable HTTP response fields and `analysis_trace`.

It does not own frontend layout, Portfolio database CRUD, public-market data
quality, deployment infrastructure, or account security.

## Complete-project path

From the repository root:

```bash
docker compose up --build --wait
docker compose run --rm smoke
```

The frontend reaches the Agent through same-origin `/api/ai/*` routes. The Agent
itself stays inside the Compose network on port `5003`.

## Local Agent environment

```bash
cd ai_agent/fund_llm_engine
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[agent]"
```

Use `.[backend,agent]` only when this environment also needs the teammate
backend integration dependencies.

## Verification

```bash
python -m unittest discover -s tests
python scripts/run_mock_demo.py examples/mock_input.json
python scripts/evaluate_analysis_output.py --input examples/mock_input.json --mode mock
python scripts/run_golden_suite.py --mode mock
```

Mock mode requires neither an API key nor an external model. It exercises the
same deterministic features, routing, scoring, output contracts, and Chief
aggregation used by real-model mode.

## Native HTTP service

When Market and News are already running locally:

```bash
bash start.sh
curl -fsS http://127.0.0.1:5003/health
curl -fsS -X POST http://127.0.0.1:5003/api/ai/fund/analyze \
  -H 'Content-Type: application/json' \
  -d '{"code":"000001","mock":true}'
```

`start.sh` prefers `.venv/bin/python`, waits for `/health`, and writes `app.log`
and `app.pid`. Stop it with:

```bash
bash stop.sh
```

The native defaults are Market `5001`, News `5000`, Portfolio `5002`, and Agent
`5003`. Override backend locations with `MARKET_BACKEND_URL`,
`NEWS_BACKEND_URL`, and `PORTFOLIO_BACKEND_URL`.

## HTTP endpoints

```text
GET  /health
GET  /api/ai/functions
GET  /api/ai/llm/models
POST /api/ai/fund/analyze
POST /api/ai/portfolio/analyze
POST /api/ai/sector/analyze
POST /api/ai/news/summary
```

See `docs/contracts.en.md` for English request, response, status, and error
semantics.

## Real LLM mode

```bash
cp .env.example .env
```

Set `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL`, then use a request with
`"mock": false`. `.env` is Git-ignored and must not be committed.

The service accepts OpenAI-compatible providers. A request may override the
configured model with `llm_model` while keeping the same gateway and key.

## Current specialist set

- `PerformanceAgent`
- `ExposureAgent`
- `BondExposureAgent`
- `RiskAgent`
- `SentimentAgent`
- `SectorAgent`
- `MarketAgent`
- `ChiefAgent` / `PortfolioChiefAgent`

Deterministic scoring runs before narrative generation. Missing data remains
visible as `insufficient_data`, `not_applicable`, or a technical error; the LLM
must not invent unavailable market or fund fields.

## English documentation

- `docs/README.md`: English documentation index;
- `docs/contracts.en.md`: API contract;
- `docs/architecture.md`: current architecture and ownership boundaries;
- `docs/ai_agent_development_log.md`: verified implementation ledger;
- `docs/implementation_plan.md`: forward work only;
- `docs/llm_evaluation.md`: output evaluation rules;
- `docs/version_history.md`: real Git tags and milestone guidance.
