# FundMasterAI Backends

FundMasterAI contains three Flask services:

| Service | Port | Responsibility | MySQL | Redis |
|---|---:|---|---|---|
| `market_backend` | 5001 | Market, fund, macro, global, crypto, and flow data | no | optional |
| `news_backend` | 5000 | Stock news and public-fund announcements | no | no |
| `portfolio_backend` | 5002 | Portfolio CRUD, allocation, alerts, and profiles | yes | no |

The supported complete-project path is Docker Compose. Use this document only
when a backend must be developed or debugged natively.

## Complete stack

From the repository root:

```bash
docker compose up --build --wait
docker compose run --rm smoke
```

Docker starts MySQL and Redis, uses the pinned dependency files in
`docker/requirements/`, and keeps backend ports inside the Compose network.

## Native Python environment

From `backend/`:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r ../docker/requirements/market.txt
python -m pip install -r ../docker/requirements/news.txt
python -m pip install -r ../docker/requirements/portfolio.txt
openbb-build
```

The pinned Docker requirement files are authoritative. Do not maintain a second
hand-written package list in this overview.

## Native configuration

- Market uses `market_backend/apis/config.ini` for cache, Redis, and local API
  credentials. `MARKET_HTTP_PORT` and `FMP_API_KEY` support environment
  overrides.
- News uses its built-in defaults and listens on port `5000` when started with
  its native script.
- Portfolio reads environment variables before `portfolio_backend/config.ini`
  and requires a MySQL database.

Docker intentionally excludes local config files and credentials. It uses
`docker/market-config.container` plus Git-ignored environment files instead.

## Native MySQL initialization

Only Portfolio requires MySQL. Before native startup:

```bash
cd portfolio_backend
mysql -u root -p fundmaster_db < init.sql
```

Docker performs this initialization automatically.

## Native start and stop

From `backend/`:

```bash
bash start_all.sh
bash stop_all.sh
```

`start_all.sh` starts Market, News, then Portfolio. It does not start MySQL.
Each service writes `app.log` and `app.pid` in its own directory.

For focused work, run the corresponding `start.sh` and `stop.sh` inside one
service directory.

## Function registries

```text
GET http://localhost:5001/api/market/functions
GET http://localhost:5000/api/news/functions
GET http://localhost:5002/api/portfolio/functions
```

The registries are the runtime authority for available functions and tags; the
set grows as endpoints are added.

## Logs

```bash
tail -f market_backend/app.log
tail -f news_backend/app.log
tail -f portfolio_backend/app.log
```

For the Compose stack, use `docker compose logs` instead.
