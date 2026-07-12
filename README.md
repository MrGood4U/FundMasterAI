# FundMasterAI

Integrated demo branch for the FundMasterAI frontend, backend, and AI Agent.

Language:

- English: this file
- Chinese: [README.zh-CN.md](README.zh-CN.md)

## Docker quick start

Run the complete frontend, three backends, AI Agent, and MySQL stack:

```bash
docker compose up --build --wait
docker compose run --rm smoke
```

Open `http://localhost:8080/ai-insights.html`. See [DOCKER.md](DOCKER.md) for
port overrides, configuration, logs, and real-LLM setup.

This branch connects:

```text
frontend_new
  -> ai_agent/fund_llm_engine Agent HTTP service
      -> backend function registries
      -> market/news backend real data
      -> LLM multi-agent analysis
```

The current Agent path is no longer mock-only: it can call the team's real backend APIs through `function_registry.py`, then run either mock LLM mode or real LLM mode.

## Branch Purpose

Current branch:

```text
aiagent-use-dev-backend
```

This branch is for:

- testing the AI Agent against the latest team `dev` backend;
- validating real backend function registry calls;
- exposing an AI analysis endpoint for the frontend;
- improving Agent-side routing, data coverage checks, and hallucination prevention.

## Main Directories

```text
backend/                    Team backend services
frontend_new/               Current demo frontend
ai_agent/fund_llm_engine/   LLM / multi-agent fund analysis engine
```

Important AI Agent docs:

```text
ai_agent/README.md
ai_agent/fund_llm_engine/README.md
ai_agent/fund_llm_engine/docs/README.md
ai_agent/fund_llm_engine/docs/ai_agent_development_log.md
ai_agent/fund_llm_engine/docs/dev_backend_integration_handoff.md
```

Use `ai_agent/fund_llm_engine/docs/ai_agent_development_log.md` as the first
source of truth for implemented, partial, and planned AI Agent work. Treat
`docs/README.md` as the AI docs index, `implementation_plan.md` as future
planning, and `version_history.md` as milestone/tag history.

## Prerequisites

- Python `>=3.11`
- `pip`
- Optional: MySQL, only if running `portfolio_backend`
- Real LLM mode requires an `.env` file under `ai_agent/fund_llm_engine/`

Install backend dependencies in your active Python environment:

```bash
pip install flask flask-openapi3 akshare pandas numpy efinance okx
pip install -U "flask-openapi3[swagger,redoc]"
```

Install AI Agent dependencies:

```bash
cd ai_agent/fund_llm_engine
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[backend,agent]"
```

## Run Unit Tests

AI Agent tests:

```bash
cd ai_agent/fund_llm_engine
source .venv/bin/activate
python3 -m unittest discover -s tests
```

Current expected result:

```text
78 tests OK
```

Frontend syntax check:

```bash
node --check frontend_new/js/ai-insights.js
```

## Start Backend Services

For the AI demo, only `market_backend` and `news_backend` are required.

```bash
cd backend/market_backend
bash start.sh

cd ../news_backend
bash start.sh
```

Default backend URLs:

```text
market_backend: http://127.0.0.1:5001
news_backend:   http://127.0.0.1:5000
```

If port `5000` is occupied on macOS, run `news_backend` on another port manually and set `NEWS_BACKEND_URL` before starting the Agent service. For example:

```bash
cd backend/news_backend
python3.11 -c "from app import create_app; create_app().run(port=5010, debug=True)"

export NEWS_BACKEND_URL=http://127.0.0.1:5010
```

Check function registries:

```bash
curl -s http://127.0.0.1:5001/api/market/functions?tag=fund
curl -s http://127.0.0.1:5000/api/news/functions?tag=fund
```

Use `5010` in the second URL if you changed the news backend port.

## Start AI Agent Service

```bash
cd ai_agent/fund_llm_engine
bash start.sh
```

`start.sh` uses the local `.venv/bin/python` when available, waits for
`/health`, and probes local `5000` / `5010` news backends when
`NEWS_BACKEND_URL` is not set. Logs go to `app.log`, the process id goes to
`app.pid`, and `bash stop.sh` stops the Agent service.

Agent service:

```text
GET  http://127.0.0.1:5003/health
GET  http://127.0.0.1:5003/api/ai/functions
POST http://127.0.0.1:5003/api/ai/fund/analyze
```

Health check:

```bash
curl -s http://127.0.0.1:5003/health
```

## Run AI Analysis

Mock LLM mode, still using real backend data:

```bash
curl -s -X POST http://127.0.0.1:5003/api/ai/fund/analyze \
  -H 'Content-Type: application/json' \
  -d '{"code":"000001","start_date":"2025/01/01","mock":true}'
```

Real LLM mode:

```bash
cd ai_agent/fund_llm_engine
cp .env.example .env
```

For DeepSeek, fill in:

```text
LLM_API_KEY=your DeepSeek API key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-pro
```

You can also use the legacy-compatible model name:

```text
LLM_MODEL=deepseek-chat
```

DeepSeek docs say `deepseek-chat` will be deprecated, so `deepseek-v4-pro` is preferred for higher-quality real LLM demos. `.env` is local secret config and should not be committed.

Then call:

```bash
curl -s -X POST http://127.0.0.1:5003/api/ai/fund/analyze \
  -H 'Content-Type: application/json' \
  -d '{"code":"003358","start_date":"2025/01/01","mock":false,"llm_timeout_seconds":90}'
```

Useful real-data test codes:

```text
000001  mixed_fund, normal real-data demo
003358  bond_index_fund, validates bond routing and not_applicable behavior
161725  stock_index_fund, validates equity/index route and holdings parsing
000002  expected 422 because current backend returns no NAV data
```

Expected routing examples:

```text
000001 -> mixed_fund
003358 -> bond_index_fund
161725 -> stock_index_fund
```

For bond funds like `003358`, equity-style `ExposureAgent` and `SectorAgent` should return:

```text
status=skipped
stance=not_applicable
```

Missing bond-specific data should be reported as:

```text
coverage_bond_holdings=missing_backend_capability
coverage_asset_allocation=missing_backend_capability
```

## Start Frontend Demo

```bash
cd frontend_new
python3 -m http.server 8003
```

Open:

```text
http://127.0.0.1:8003/ai-insights.html
```

The frontend calls:

```text
http://127.0.0.1:5003/api/ai/fund/analyze
```

## Stop Services

```bash
cd backend/market_backend && bash stop.sh
cd ../news_backend && bash stop.sh

cd ../../ai_agent/fund_llm_engine
bash stop.sh
```

If you started the frontend with `python3 -m http.server`, stop it with `Ctrl+C` in that terminal.

## Current Known Backend Gaps

The Agent can already read fund type from:

```text
get_fund_individual_basic_info
```

The backend still needs additional APIs for deeper asset-aware analysis:

```text
get_fund_bond_holdings
get_fund_asset_allocation
get_fund_industry_allocation
```

Until those exist, the Agent reports missing backend capability instead of letting the LLM guess.
