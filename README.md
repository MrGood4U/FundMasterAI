# FundMasterAI

FundMasterAI is an integrated classroom demo for fund data, portfolio tools,
market/news dashboards, and an explainable multi-agent analysis service.

Chinese guide: [README.zh-CN.md](README.zh-CN.md)

## Quick Start

The recommended submission and demonstration path is Docker Compose. It starts
the frontend, Market/News/Portfolio backends, AI Agent, MySQL, and Redis with
one command.

Requirements:

- Docker Desktop with Docker Compose v2;
- an internet connection for the public market and fund data sources;
- no LLM API key for the default mock-narrative mode.

From the repository root:

```bash
docker compose up --build --wait
docker compose run --rm smoke
```

Then open:

```text
http://localhost:8080/ai-insights.html
```

The first build downloads images and Python packages, so it is normally much
slower than later starts. A successful smoke run ends with:

```text
FundMasterAI Docker smoke test passed.
```

If port `8080` is already in use:

```bash
APP_PORT=8088 docker compose up --build --wait
APP_PORT=8088 docker compose run --rm smoke
```

Open `http://localhost:8088/ai-insights.html`. See [DOCKER.md](DOCKER.md) for
configuration, logs, real-LLM setup, and troubleshooting.

## What Runs

```text
frontend_new (Nginx + same-origin API gateway)
  -> market backend (market, fund, macro, global and flow data; Redis cache)
  -> news backend (stock news and fund announcements)
  -> portfolio backend (portfolio CRUD backed by MySQL)
  -> AI Agent service
       -> backend function registries
       -> deterministic features and fund-type routing
       -> specialist agents
       -> Chief aggregation and explainability trace
```

Default Docker mode uses real public backend data and deterministic mock LLM
narratives. This makes the demo reproducible without an API key while still
testing the real service and data path. Configure an OpenAI-compatible provider
only when a real-model demonstration is required.

## Main Directories

| Path | Purpose |
|---|---|
| [`frontend_new/`](frontend_new/README.en.md) | Static dashboard and browser-side integrations |
| [`backend/`](backend/README.en.md) | Market, News, and Portfolio Flask services |
| [`ai_agent/fund_llm_engine/`](ai_agent/fund_llm_engine/README.en.md) | Multi-agent fund analysis service |
| [`docker/`](docker/) | Container builds, Nginx routing, and end-to-end smoke test |

## Documentation Map

Use the documents below according to the task instead of treating every
historical note as a current runbook.

| Need | Authoritative document |
|---|---|
| Run the complete project | [DOCKER.en.md](DOCKER.en.md) |
| Understand or preview the frontend | [frontend_new/README.en.md](frontend_new/README.en.md) |
| Run backends without Docker | [backend/README.en.md](backend/README.en.md) |
| Develop or test the AI Agent | [ai_agent/fund_llm_engine/README.en.md](ai_agent/fund_llm_engine/README.en.md) |
| Find AI Agent design/status docs | [AI Agent docs index](ai_agent/fund_llm_engine/docs/README.md) |
| Check stable AI API fields | [AI Agent contracts](ai_agent/fund_llm_engine/docs/contracts.en.md) |
| Contribute changes | [CONTRIBUTING.md](CONTRIBUTING.md) |

Obsolete weekend-integration and shared-systemd-server runbooks are not part of
the current startup path. Optional native Windows Agent debugging plus historical
design, migration, handoff, and benchmark notes remain available as references.

## Verification

Full-stack verification:

```bash
docker compose config --quiet
docker compose up --build --wait
docker compose run --rm smoke
```

AI Agent unit and golden-case verification (optional for module development):

```bash
cd ai_agent/fund_llm_engine
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[agent]"
python -m unittest discover -s tests
python scripts/run_golden_suite.py --mode mock
```

Do not rely on a permanently hard-coded test count. The expected result is an
`OK` unit-test run and a golden report with `overall_status: pass`. The current
documentation refresh was checked on 2026-07-16 with 262 unit tests and 8/8
mock golden cases passing.

## Real LLM Mode

The clean-clone default is mock LLM mode. To use a real OpenAI-compatible
provider:

```bash
cp ai_agent/fund_llm_engine/.env.example ai_agent/fund_llm_engine/.env
```

Fill in `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL`, then rebuild the Agent
and frontend services:

```bash
docker compose up -d --build --wait agent frontend
```

The local `.env` is Git-ignored and must never be committed. See
[DOCKER.en.md](DOCKER.en.md) and `ai_agent/fund_llm_engine/.env.example` for the
supported configuration fields.

## Known Limits

- Public upstream data can be slow or temporarily unavailable; the smoke test
  therefore needs internet access and may take longer on a cold start.
- The AI rating layer is an explainable heuristic analysis demo, not a
  calibrated return-prediction or trading system.
- Bond depth is limited by the upstream duration, maturity, issuer, and credit
  rating fields that are actually available.
- Some security and account controls are explicitly browser-local demo
  interactions rather than production identity-management features.

## Stop

```bash
docker compose down
```

This keeps both the MySQL database and Redis cache volumes. Use
`docker compose down -v` only when both the local demo database and recoverable
Market cache may be permanently deleted.
