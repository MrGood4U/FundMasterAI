# FundMasterAI

FundMasterAI is a fund-analysis prototype built by the project team. This
branch is the AI Agent integration branch: it keeps the LLM / multi-agent
engine in `ai_agent/fund_llm_engine/` and wires it to the teammate market
backend and static frontend for a runnable local demo.

## What This Branch Demonstrates

- AI Agent / LLM engine for fund analysis, maintained under
  `ai_agent/fund_llm_engine/`.
- Real open-fund NAV data retrieval through the market backend.
- Backend adapter endpoint:
  `POST /api/ai/fund/analyze`.
- Static frontend page:
  `/app/ai-insights.html`.
- End-to-end flow:
  fund code -> real NAV data -> structured metrics -> multi-agent analysis ->
  frontend display.

## Contribution Boundary

My main responsibility is the AI Agent / LLM engine and its integration
adapter:

- multi-agent analysis workflow;
- fund-analysis input / output contracts;
- feature and metric construction before LLM calls;
- mock and real OpenAI-compatible model clients;
- missing-data handling to avoid unsupported conclusions;
- backend adapter endpoint and demo integration with team modules.

The market backend and frontend are integrated from teammate branches so that
the AI Agent module can be verified in an end-to-end setting.

## Repository Layout

```text
FundMasterAI/
├── ai_agent/
│   └── fund_llm_engine/        # AI Agent / LLM analysis engine
├── backend/
│   ├── market_backend/         # market and public-fund data backend
│   └── news_backend/
├── frontend_new/               # static demo frontend
└── scripts/
    └── run_integrated_smoke.py # repository-level smoke test
```

## Quick Start

Use Python 3.11+.

```bash
cd FundMasterAI/ai_agent/fund_llm_engine
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[backend]"
python3 -m unittest discover -s tests
```

Run the repository-level smoke test from the project root:

```bash
cd FundMasterAI
ai_agent/fund_llm_engine/.venv/bin/python scripts/run_integrated_smoke.py
```

Start the integrated demo:

```bash
cd FundMasterAI/backend/market_backend
../../ai_agent/fund_llm_engine/.venv/bin/python app.py
```

Then open:

```text
http://127.0.0.1:5001/app/ai-insights.html
```

The page calls `/api/ai/fund/analyze`, which pulls real open-fund NAV data,
transforms it into the AI Agent contract, runs the multi-agent engine, and
renders the result back to the page.

## Model Modes

The demo supports two modes:

- `mock`: deterministic local LLM mock for testing and demo stability;
- `real`: OpenAI-compatible model call, configured with environment variables.

For real model calls, create:

```bash
cd ai_agent/fund_llm_engine
cp .env.example .env
```

Then fill:

- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL`

## Data Reliability Note

This branch intentionally distinguishes unavailable data from neutral signals.
For example, when industry exposure, holdings, news, or sentiment data are not
available, the corresponding agent returns `skipped / insufficient_data`
instead of inventing a neutral assessment. The chief agent aggregates only
supported signals and reports partial agent health when applicable.
