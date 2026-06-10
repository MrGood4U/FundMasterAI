# AI Agent Module

This directory contains the LLM-based analysis module for FundMaster AI.

## Current Module

- `fund_llm_engine/`: multi-agent fund analysis engine.
- `fund_llm_engine/app.py`: optional Agent HTTP service, default port `5003`.

The engine is intentionally kept as a standalone Python package under this
directory. The repository root integrates it with teammate backend and frontend
modules only for demo verification.

## Backend Function Registry Integration

The latest team backend exposes machine-readable function definitions:

```text
GET http://127.0.0.1:5001/api/market/functions?tag=fund
GET http://127.0.0.1:5000/api/news/functions?tag=fund
GET http://127.0.0.1:5002/api/portfolio/functions
```

If `news_backend` is moved to another local port, set `NEWS_BACKEND_URL`
before starting `fund_llm_engine/app.py`. For example:

```bash
export NEWS_BACKEND_URL=http://127.0.0.1:5010
```

The LLM engine now uses `fund_llm.adapters.BackendFunctionClient` to discover
those functions and call them over HTTP. The current fund analysis path uses:

- `get_fund_hist`
- `get_fund_individual_basic_info`
- `get_fund_portfolio_holds`
- `get_fund_individual_analysis`
- `get_fund_profit_probability`
- `get_public_fund_announcement`

This keeps the Agent side from hard-coding every backend route.

## Quick Verification

```bash
cd ai_agent/fund_llm_engine
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[backend]"
python3 -m unittest discover -s tests
python3 scripts/run_mock_demo.py examples/mock_input.json
```

Run the Agent backend after `market_backend` and `news_backend` are running:

```bash
cd backend/market_backend && bash start.sh
cd ../news_backend && bash start.sh
cd ../..

cd ai_agent/fund_llm_engine
pip install -e ".[agent]"
bash start.sh
curl -s http://127.0.0.1:5003/health
curl -s -X POST http://127.0.0.1:5003/api/ai/fund/analyze \
  -H 'Content-Type: application/json' \
  -d '{"code":"000001","mock":true}'
```

`fund_llm_engine/start.sh` prefers the local `.venv/bin/python`, waits for the
Agent `/health` endpoint, writes `app.pid` and `app.log`, and probes local
`5000` / `5010` news backends when `NEWS_BACKEND_URL` is not already set.
Use `bash stop.sh` from `fund_llm_engine/` to stop it.

For real LLM mode, create `fund_llm_engine/.env` from `.env.example`, fill in
`LLM_API_KEY`, and call the endpoint with `"mock": false`.

See `fund_llm_engine/README.md` and `fund_llm_engine/docs/README.md` for the
module scope, contracts, provider setup, integration notes, and current status
entry points.
