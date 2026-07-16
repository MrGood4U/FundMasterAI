# FundMaster Frontend

`frontend_new/` is the current FundMasterAI static frontend. It uses plain
HTML, CSS, and JavaScript. In the complete stack, Nginx serves the files and
proxies same-origin `/api/market`, `/api/news`, `/api/portfolio`, and `/api/ai`
requests to their services.

## Recommended preview

Run the complete project from the repository root:

```bash
docker compose up --build --wait
docker compose run --rm smoke
```

Open `http://localhost:8080/ai-insights.html` and use the sidebar to inspect the
other pages. This exercises the same routing used by the final demo.

For layout-only work, you may run:

```bash
python3 -m http.server 8080 --directory frontend_new
```

Then open `http://127.0.0.1:8080/`. This mode has no Nginx API gateway and is
not a substitute for integration acceptance.

## Primary pages

| File | Page |
|---|---|
| `portfolio-overview.html` | Portfolio Overview |
| `equity-funds.html` | Equity Funds |
| `debt-funds.html` | Debt Funds |
| `global-investment.html` | Global Investment |
| `fund-deep-dive.html` | Fund Deep Dive |
| `market-hub.html` | Market Hub |
| `market-flow.html` | ETF Capital Flow |
| `index.html` | Market Intelligence / News |
| `ai-insights.html` | AI Insights |
| `settings.html` | Settings |

The pages originated from several frames in Figma file
`B1cuHJoXlJTr7e1ADVhH2P`. Current source code, API contracts, and browser-visible
behavior are authoritative when they differ from old placeholders.

## Shared assets

| Path | Purpose |
|---|---|
| `css/shell.css` | Sidebar, header, theme variables, and responsive baseline |
| `css/dashboard-widgets.css` | Shared KPI, table, and chart components |
| `css/page-*.css` | Page-specific layout and styling |
| `scripts/`, `js/` | Data loading, caching, interactions, and AI Insights |
| `assets/icons/` | Navigation and header icons |

## Fund search and cache

Header search and Portfolio Overview use the real Market fund directory at
`GET /api/market/fund_public/fund_name_list`. A successful compact directory is
cached in `localStorage` under `fundmaster:fund-directory:v1` for 24 hours.
Expired cache may be shown while a background refresh runs. Network failure is
reported explicitly; arbitrary input is not presented as a verified fund.

Portfolio Overview only saves a holding after the user selects a real search
result. Its AI action calls `/api/ai/portfolio/analyze` with the selected fund
codes and weights.

## Generated navigation pages

Shared navigation for generated pages is maintained by
`scripts/generate-pages.py`:

```bash
python3 frontend_new/scripts/generate-pages.py
```

`index.html` is maintained separately. Always inspect the Git diff after
generation so manual page integrations are not overwritten.

## Acceptance

```bash
docker compose run --rm smoke
```

Smoke verifies reachability and the main API path. A release still requires a
real-browser check after live data loads, including navigation, empty states,
and any cache-dependent behavior.

Use a current Chrome, Edge, Safari, or Firefox release. Older browsers may
degrade `backdrop-filter` and `:has()` styling without affecting core data.
