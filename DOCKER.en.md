# FundMasterAI Docker Guide

Docker Compose is the supported way to run, demonstrate, and verify the complete
project on `master`. It starts:

- `frontend`: Nginx static frontend and same-origin API gateway;
- `market`: market and fund data backend;
- `news`: news backend;
- `portfolio`: portfolio backend;
- `agent`: AI Agent service;
- `mysql`: database used by the Portfolio backend;
- `redis`: recoverable Market data cache.

Only the frontend port is published to the host. All other services stay inside
the Compose network.

## 1. Start

Install Docker Desktop with Docker Compose v2, then run from the repository root:

```bash
docker compose config --quiet
docker compose up --build --wait
```

Open:

```text
http://localhost:8080/ai-insights.html
```

If port `8080` is already in use, keep the same `APP_PORT` value for every
subsequent Compose command:

```bash
APP_PORT=8088 docker compose up --build --wait
APP_PORT=8088 docker compose run --rm smoke
```

You may instead place `APP_PORT=8088` in a Git-ignored root `.env` file.

The first build downloads images and Python packages and may take much longer
than later builds. Market and News still use public upstream data; only the LLM
narrative defaults to deterministic mock mode, so the demo machine needs
internet access.

A clean clone does not require a local Python environment, a pre-created `.env`,
or manual MySQL initialization. Compose uses safe classroom defaults and creates
the database tables automatically.

## 2. End-to-end verification

After all long-running services are healthy, run:

```bash
docker compose run --rm smoke
```

The smoke test checks:

1. the ten primary frontend pages;
2. Market, News, Portfolio, and Agent registries;
3. the Agent model catalog;
4. real backend data plus mock-LLM analysis for fund `000001`.

A successful run ends with:

```text
FundMasterAI Docker smoke test passed.
```

Use another fund when needed:

```bash
SMOKE_FUND_CODE=000171 docker compose run --rm smoke
```

Smoke is the minimum automated check, not visual acceptance. Before a release,
open `ai-insights.html` in a real browser, wait for data to load, run one fund
analysis, and navigate to at least one other page.

## 3. Common commands

```bash
# Service state
docker compose ps

# All logs
docker compose logs -f

# One service
docker compose logs -f agent

# Rebuild and restart selected services
docker compose build agent
docker compose up -d --wait agent frontend

# Stop containers while preserving MySQL and Redis volumes
docker compose down
```

Only delete volumes when both the local demo database and recoverable Market
cache may be permanently removed:

```bash
docker compose down -v
```

## 4. Configuration and real LLM mode

The checked-in defaults are intended for local classroom use and bind the
frontend to `127.0.0.1`. To customize the host port, demo database credentials,
or optional FMP key, copy:

```bash
cp .env.docker.example .env
```

Keep the resulting root `.env` local and Git-ignored. For OpenBB/FMP-backed
global index data, set `FMP_API_KEY` there. Never write credentials to
`compose.yaml` or `docker/market-config.container`.

MySQL users and databases are created only when the `mysql_data` volume is first
initialized. Changing `FM_MYSQL_*` later does not migrate the existing account.
Either update MySQL manually or, only when its data may be deleted, recreate the
volume with `docker compose down -v`.

For a real OpenAI-compatible LLM, use the Agent-specific environment file:

```bash
cp ai_agent/fund_llm_engine/.env.example ai_agent/fund_llm_engine/.env
```

Set at least:

```text
LLM_MOCK_MODE=false
LLM_API_KEY=your-key
LLM_BASE_URL=your-openai-compatible-base-url
LLM_MODEL=your-model-id
```

Then rebuild the Agent and frontend:

```bash
docker compose up -d --build --wait agent frontend
```

Configuration precedence is:

```text
.env.docker.example < optional root .env < ai_agent/fund_llm_engine/.env
```

All local `.env` files, virtual environments, logs, PID files, and local backend
configuration files are excluded from Docker build context.

## 5. Ports and routing

| Service | Container port | Default host port |
|---|---:|---:|
| Frontend / API gateway | 80 | 8080 |
| Market | 5001 | not published |
| News | 5000 | not published |
| Portfolio | 5002 | not published |
| Agent | 5003 | not published |
| MySQL | 3306 | not published |
| Redis | 6379 | not published |

The browser uses same-origin `/api/market/*`, `/api/news/*`,
`/api/portfolio/*`, and `/api/ai/*` paths. Portfolio Overview is connected to
the Agent through `/api/ai/portfolio/analyze` in this Docker path.

## 6. Troubleshooting

### The first build is slow

Downloading images, installing pinned dependencies, and building OpenBB assets
can take time. If the logs are still downloading or installing packages, the
build is still progressing. Later builds reuse Docker layer cache.

### Services are healthy but a page has no data

Health checks prove reachability, not public-upstream availability. Inspect:

```bash
docker compose logs --tail=200 market news agent
```

Retry after a transient upstream timeout. Do not replace missing live data with
plausible-looking values.

### Port conflict

Change only the published frontend port:

```bash
APP_PORT=8088 docker compose up -d --wait
```

### What counts as a successful start

All three conditions should hold:

1. every long-running service in `docker compose ps` is healthy;
2. `docker compose run --rm smoke` passes;
3. a real browser shows the page after data loading completes.
