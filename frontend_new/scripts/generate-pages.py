#!/usr/bin/env python3
"""一次性生成多页 HTML 侧栏（与 Figma 导航一致）。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSET_VERSION = "20260630-1"

NAV = [
    ("global-investment.html", "Overview", "overview"),
    ("portfolio-overview.html", "Portfolio", "portfolio"),
    ("fund-deep-dive.html", "Analytics", "analytics"),
    ("market-hub.html", "Markets", "markets"),
    ("index.html", "News", "news"),
    ("ai-insights.html", "AI Insights", "ai"),
    ("settings.html", "Settings", "settings"),
]

# 与 assets/icons/ 下 PNG 对应（由 Figma 导出后放入）
ICON_SRC = {
    "overview": "assets/icons/nav-overview.png",
    "portfolio": "assets/icons/nav-portfolio.png",
    "analytics": "assets/icons/nav-analytics.png",
    "markets": "assets/icons/nav-markets.png",
    "news": "assets/icons/nav-news.png",
    "ai": "assets/icons/nav-ai-insights.png",
    "settings": "assets/icons/nav-settings.png",
}


def sidebar(active_href: str) -> str:
    lines = [
        '      <aside class="sidebar" aria-label="主导航">',
        '        <div class="sidebar__brand">',
        '          <img class="sidebar__logo" src="assets/icons/logo.png" width="32" height="32" alt="" />',
        '          <div class="sidebar__titles">',
        '            <h1 class="sidebar__name">FundMaster</h1>',
        '            <p class="sidebar__tagline">STRATEGIC CAPITAL</p>',
        "          </div>",
        "        </div>",
        '        <nav class="sidebar__nav" aria-label="功能菜单">',
    ]
    for href, label, key in NAV:
        src = ICON_SRC[key]
        active = href == active_href
        cls = "nav-link nav-link--active" if active else "nav-link"
        cur = ' aria-current="page"' if active else ""
        lines.append(f'          <a class="{cls}" href="{href}"{cur}>')
        lines.append(f'            <img class="nav-link__icon" src="{src}" width="20" height="20" alt="" />')
        lines.append(f"            {label}")
        lines.append("          </a>")
    lines += [
        "        </nav>",
        '        <div class="sidebar__footer">',
        '          <button type="button" class="btn-upgrade">',
        '            <span class="btn-upgrade__icon" aria-hidden="true">◇</span>',
        "            Upgrade to Pro",
        "          </button>",
        "        </div>",
        "      </aside>",
    ]
    return "\n".join(lines)


def topbar(placeholder: str, input_id: str = "q") -> str:
    return f"""      <header class="top-bar">
        <div class="search-field" role="search">
          <img class="search-field__icon-img" src="assets/icons/header-search.png" width="16" height="16" alt="" />
          <label class="visually-hidden" for="{input_id}">搜索</label>
          <input id="{input_id}" class="search-field__input" type="search" placeholder="{placeholder}" autocomplete="off" />
        </div>
        <div class="top-bar__actions">
          <button type="button" class="icon-btn" aria-label="通知"><img class="icon-btn__img" src="assets/icons/header-bell.png" width="18" height="18" alt="" /></button>
          <button type="button" class="icon-btn" aria-label="帮助"><img class="icon-btn__img" src="assets/icons/header-help.png" width="18" height="18" alt="" /></button>
          <button type="button" class="avatar-btn" aria-label="用户资料"><img class="avatar-btn__img" src="assets/icons/header-avatar.png" width="32" height="32" alt="" /></button>
        </div>
      </header>"""


def doc_shell(title: str, extra_css: list[str], active_href: str, placeholder: str, body: str, fab: bool = True, input_id: str = "q", extra_scripts: list[str] | None = None) -> str:
    links = "\n    ".join(f'<link rel="stylesheet" href="{c}" />' for c in ["css/shell.css", *extra_css])
    scripts = "\n    ".join(f'<script src="{s}?v={ASSET_VERSION}"></script>' for s in (extra_scripts or []))
    script_block = f"\n    {scripts}" if scripts else ""
    fab_html = (
        '\n        <button type="button" class="fab" aria-label="快捷操作"><span class="fab__plus" aria-hidden="true">+</span></button>'
        if fab
        else ""
    )
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{title}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@400&family=Space+Grotesk:wght@500;700;900&display=swap" rel="stylesheet" />
    {links}
  </head>
  <body>
    <div class="app">
{sidebar(active_href)}
      <div class="main-shell">
{topbar(placeholder, input_id)}
{body}
{fab_html}
      </div>
    </div>{script_block}
  </body>
</html>
"""


# —— 各页主内容 ——


def page_fund_deep_dive():
    body = """        <main class="content" data-fund-page>
          <nav class="breadcrumb" aria-label="面包屑">
            <a href="fund-deep-dive.html">Funds</a><span class="breadcrumb__sep">›</span>
            <a href="#">Global Tech Equities</a><span class="breadcrumb__sep">›</span>
            <span>MasterTech Growth Fund</span>
          </nav>
          <header class="page-head">
            <div>
              <h2 class="page-head__title" data-fund-title>MasterTech Growth Fund</h2>
              <p class="page-head__sub">High-conviction global technology allocation with active risk overlays.</p>
            </div>
            <span class="chip chip--live">Active</span>
          </header>
          <div class="kpi-row">
            <div class="kpi-card"><p class="kpi-card__label">Ticker</p><p class="kpi-card__value" data-fund-ticker>MTGF.QX</p></div>
            <div class="kpi-card"><p class="kpi-card__label">NAV</p><p class="kpi-card__value" data-fund-nav>$248.12</p></div>
            <div class="kpi-card"><p class="kpi-card__label">24H Change</p><p class="kpi-card__value pos" data-fund-change>+2.41%</p><p class="kpi-card__hint api-status" data-api-status="fund">Static preview</p></div>
          </div>
          <div class="toolbar"><button type="button" class="btn-outline">Prospectus</button></div>
          <section class="glass-panel fd-matrix">
            <div class="section-head">
              <h3 class="section-head__title"><span class="section-head__bolt" aria-hidden="true"></span>Performance Matrix</h3>
              <div class="pill-group" role="group">
                <button type="button" class="pill pill--ghost">1M</button>
                <button type="button" class="pill pill--ghost">3M</button>
                <button type="button" class="pill pill--ghost">1Y</button>
                <button type="button" class="pill pill--ghost">ALL</button>
              </div>
            </div>
            <p class="fd-caption">Historical NAV growth over selected period</p>
            <div class="fd-chart" role="img" aria-label="NAV 曲线示意图"></div>
            <div class="fd-stats" data-fund-stats>
              <div><span class="fd-stats__k">Oct 24, 2023</span><span class="fd-stats__v">$214.85</span></div>
              <div><span class="fd-stats__k">YTD Return</span><span class="fd-stats__v pos">+18.4%</span></div>
              <div><span class="fd-stats__k">1Y Return</span><span class="fd-stats__v pos">+32.1%</span></div>
              <div><span class="fd-stats__k">3Y Annualized</span><span class="fd-stats__v pos">+14.2%</span></div>
              <div><span class="fd-stats__k">Since Inception</span><span class="fd-stats__v pos">+144.5%</span></div>
            </div>
          </section>
          <div class="two-col">
            <section class="glass-panel">
              <h3 class="section-head__title section-head__title--compact">Risk Assessment</h3>
              <ul class="fd-risk">
                <li><div><strong>Sharpe Ratio</strong><span class="muted">Risk-adjusted return quality</span></div><em>2.14</em></li>
                <li><div><strong>Standard Deviation</strong><span class="muted">Volatility over 1 year</span></div><em>12.8%</em></li>
                <li><div><strong>Alpha</strong><span class="muted">Excess return vs benchmark</span></div><em>4.2</em></li>
                <li><div><strong>Beta</strong><span class="muted">Market correlation factor</span></div><em>1.08</em></li>
              </ul>
            </section>
            <section class="glass-panel">
              <h3 class="section-head__title section-head__title--compact">Asset Allocation</h3>
              <p class="fd-caption">14 holdings · sector weights</p>
              <ul class="fd-alloc">
                <li><span>Software &amp; SaaS</span><span>65.2%</span><div class="bar-track"><div class="bar-fill" style="width:65.2%"></div></div></li>
                <li><span>Semiconductors</span><span>18.4%</span><div class="bar-track"><div class="bar-fill" style="width:18.4%"></div></div></li>
                <li><span>Cloud Infrastructure</span><span>12.1%</span><div class="bar-track"><div class="bar-fill" style="width:12.1%"></div></div></li>
                <li><span>Cash / Liquid</span><span>4.3%</span><div class="bar-track"><div class="bar-fill" style="width:4.3%"></div></div></li>
              </ul>
            </section>
          </div>
          <section class="glass-panel fd-mgmt">
            <h3 class="section-head__title section-head__title--compact">Management Team</h3>
            <div class="fd-mgmt__card">
              <div class="fd-avatar" aria-hidden="true"></div>
              <div>
                <p class="fd-mgmt__name">Dr. Elena Thorne</p>
                <p class="fd-mgmt__role">Chief Portfolio Manager</p>
                <div class="fd-mgmt__meta"><span>Experience · 18+ Years</span><span>AUM Lead · $4.2B</span></div>
              </div>
            </div>
          </section>
          <section class="glass-panel">
            <h3 class="section-head__title section-head__title--compact">Top Holdings</h3>
            <div class="data-table-wrap">
              <table class="data-table">
                <thead><tr><th>Ticker</th><th>Name</th><th>Weight</th></tr></thead>
                <tbody>
                  <tr><td>NVDA</td><td>NVIDIA Corp.</td><td>9.2%</td></tr>
                  <tr><td>MSFT</td><td>Microsoft</td><td>8.4%</td></tr>
                  <tr><td>AAPL</td><td>Apple Inc.</td><td>7.9%</td></tr>
                  <tr><td>TSM</td><td>TSMC Ltd.</td><td>6.1%</td></tr>
                  <tr><td>GOOGL</td><td>Alphabet</td><td>5.8%</td></tr>
                </tbody>
              </table>
            </div>
          </section>
          <section class="glass-panel">
            <h3 class="section-head__title section-head__title--compact">Investment Strategy &amp; Philosophy</h3>
            <p class="fd-strat">The fund maintains a concentrated book in secular growth technology while using macro overlays to dampen drawdowns during liquidity shocks.</p>
          </section>
        </main>"""
    html = doc_shell(
        "FundMaster — Fund Deep Dive",
        ["css/dashboard-widgets.css", "css/page-fund-deep-dive.css"],
        "fund-deep-dive.html",
        "Search funds...",
        body,
        extra_scripts=["scripts/api.js", "scripts/live-data.js"],
    )
    (ROOT / "fund-deep-dive.html").write_text(html, encoding="utf-8")


def page_market_hub():
    body = """        <main class="content content--market-hub">
          <header class="page-head">
            <div>
              <h2 class="page-head__title">Market Hub</h2>
              <p class="page-head__sub">Live indices, sentiment, heatmap and capital flow — Figma 11:626.</p>
              <p class="muted sm" style="margin:8px 0 0"><a href="market-flow.html" style="color:var(--accent-cyan)">Market liquidity &amp; flow 视图（Figma 11:1391）→</a></p>
            </div>
            <div class="mh-clock"><span class="mh-clock__label">MARKET API</span><span class="mh-clock__time api-status" data-api-status="market">Static preview</span></div>
          </header>
          <section class="mh-indices">
            <article class="mh-index"><h4>S&amp;P 500</h4><p class="mh-index__v">5,147.22</p><p class="mh-index__p pos">+0.82%</p></article>
            <article class="mh-index"><h4>NASDAQ 100</h4><p class="mh-index__v">18,103.44</p><p class="mh-index__p pos">+1.45%</p></article>
            <article class="mh-index"><h4>FTSE 100</h4><p class="mh-index__v">7,820.30</p><p class="mh-index__p neg">-0.12%</p></article>
            <article class="mh-index"><h4>NIKKEI 225</h4><p class="mh-index__v">38,707.95</p><p class="mh-index__p pos">+0.54%</p></article>
          </section>
          <div class="two-col">
            <section class="glass-panel">
              <div class="section-head"><h3 class="section-head__title">Market Sentiment</h3><span class="muted">Greed Index Analysis</span></div>
              <div class="mh-greed"><span class="mh-greed__n">74</span><div><p class="mh-greed__lbl">GREED</p><div class="bar-track"><div class="bar-fill" style="width:74%"></div></div><div class="mh-greed__ticks"><span>Extreme Fear</span><span>Neutral</span><span>Extreme Greed</span></div></div></div>
            </section>
            <section class="glass-panel">
              <h3 class="section-head__title section-head__title--compact">Global Market Heatmap</h3>
              <div class="mh-legend"><span>U.S. Tech</span><span>A-Shares</span><span>EU Broad</span><span class="mh-legend__vol">Volatility: Low</span></div>
              <div class="mh-heat" data-market-heat>
                <div class="mh-cell pos"><span>AAPL</span><em>+2.84%</em><small>Apple Inc.</small></div>
                <div class="mh-cell pos"><span>MSFT</span><em>+1.15%</em><small>MICROSOFT</small></div>
                <div class="mh-cell pos"><span>GOOGL</span><em>+0.42%</em></div>
                <div class="mh-cell neg"><span>AMZN</span><em>-0.88%</em></div>
                <div class="mh-cell pos"><span>NVDA</span><em>+4.12%</em><small>NEW ATH</small></div>
                <div class="mh-cell neg"><span>TSLA</span><em>-3.21%</em></div>
                <div class="mh-cell pos"><span>META</span><em>+0.22%</em></div>
              </div>
              <p class="mh-sectors-title">Sectors (avg)</p>
              <div class="mh-sectors"><span>Health +0.14%</span><span>Energy -1.05%</span></div>
            </section>
          </div>
          <section class="glass-panel">
            <h3 class="section-head__title section-head__title--compact">Capital Flow Analysis</h3>
            <div class="mh-flow">
              <div><p class="muted">Northbound Inflow (CNY)</p><p class="mh-flow__big pos">+12.4B</p><div class="mh-dow">Mon Tue Wed Thu Fri Sat Sun</div></div>
              <div><p class="muted">Institutional Liquidity</p><p class="mh-flow__big">Stable</p><div class="mh-split"><span>Retail 42%</span><span>Institutional 58%</span></div></div>
            </div>
          </section>
          <section class="glass-panel">
            <div class="section-head"><h3 class="section-head__title">Top Gaining / Declining</h3><button type="button" class="btn-outline">View all 18 sectors</button></div>
            <div class="mh-movers" data-market-movers>
              <ul><li class="pos">Semiconductors +5.82%</li><li class="pos">Cloud Computing +3.44%</li><li class="pos">Clean Energy +1.20%</li></ul>
              <ul><li class="neg">Real Estate -2.15%</li><li class="neg">Consumer Staples -4.88%</li></ul>
            </div>
          </section>
        </main>"""
    html = doc_shell(
        "FundMaster — Market Hub",
        ["css/dashboard-widgets.css", "css/page-market-hub.css"],
        "market-hub.html",
        "Search funds...",
        body,
        extra_scripts=["scripts/api.js", "scripts/live-data.js"],
    )
    (ROOT / "market-hub.html").write_text(html, encoding="utf-8")


def page_ai():
    body = """        <main class="content">
          <header class="page-head">
            <div>
              <h2 class="page-head__title">AI Strategy Analysis</h2>
              <p class="page-head__sub">Neural-Mean Reversion v4.2 · live execution telemetry</p>
            </div>
            <span class="chip chip--live">Active Algorithm</span>
          </header>
          <section class="glass-panel ai-hero">
            <div class="ai-hero__grid">
              <div>
                <p class="muted">Predictive Alpha Curve</p>
                <p class="ai-alpha">+14.82%</p>
                <p class="muted sm">Alpha vs benchmark</p>
              </div>
              <div class="ai-dials">
                <div><span>Win rate</span><strong>68.4%</strong></div>
                <div><span>Sharpe</span><strong>2.84</strong></div>
                <div><span>Max drawdown</span><strong class="neg">-4.1%</strong></div>
                <div><span>Volatility</span><strong>12.2%</strong></div>
              </div>
            </div>
            <div class="ai-confbox"><p>Current Confidence</p><p class="ai-confbox__n">85%</p><span>High conviction</span></div>
          </section>
          <div class="two-col">
            <section class="glass-panel">
              <h3 class="section-head__title section-head__title--compact">AI Execution Logic</h3>
              <ul class="ai-steps">
                <li><strong>Pattern Synthesis</strong><span class="chip chip--live">Completed</span><p class="muted sm">Multi-timeframe feature fusion.</p></li>
                <li><strong>Correlated Hedging</strong><span class="chip chip--live">Optimized</span><p class="muted sm">Dynamic beta neutralization.</p></li>
                <li><strong>Risk Parity Adjustment</strong><span class="chip chip--warn">Watch</span><p class="muted sm">Liquidity-aware sizing.</p></li>
              </ul>
            </section>
            <section class="glass-panel">
              <h3 class="section-head__title section-head__title--compact">Liquidity Warning</h3>
              <p class="muted">Tape velocity elevated on small-cap sleeve — reduce participation rate by 15% until spread normalizes.</p>
            </section>
          </div>
          <section class="glass-panel">
            <h3 class="section-head__title section-head__title--compact">Backtest Matrix</h3>
            <div class="data-table-wrap">
              <table class="data-table">
                <thead><tr><th>Period</th><th>Scenario</th><th>Model</th><th>Net</th></tr></thead>
                <tbody>
                  <tr><td>DEC 23</td><td>Bearish Macro Spike</td><td>Omega</td><td class="pos">+4.2%</td></tr>
                  <tr><td>NOV 15</td><td>Sustained Bull Run</td><td>Alpha</td><td class="pos">+11.8%</td></tr>
                  <tr><td>OCT 02</td><td>Liquidity Flash Crash</td><td>Zeta</td><td class="neg">-1.2%</td></tr>
                  <tr><td>SEP 18</td><td>Interest Rate Shock</td><td>Omega</td><td class="pos">+2.1%</td></tr>
                </tbody>
              </table>
            </div>
          </section>
          <section class="glass-panel">
            <div class="section-head"><h3 class="section-head__title">Recent Algorithmic Trade Log</h3><div><span class="chip chip--live">Live Engine</span><span class="muted sm">14ms latency</span></div></div>
            <div class="data-table-wrap">
              <table class="data-table">
                <thead><tr><th>Pair</th><th>Action</th><th>Price</th><th>AI Conf.</th><th>Status</th></tr></thead>
                <tbody>
                  <tr><td>BTC/USDT</td><td>LONG_MARKET</td><td>$64,281.42</td><td>92.4%</td><td>EXECUTED</td></tr>
                  <tr><td>ETH/USDT</td><td>LONG_LIMIT</td><td>$3,482.11</td><td>88.1%</td><td>EXECUTED</td></tr>
                </tbody>
              </table>
            </div>
          </section>
        </main>"""
    html = doc_shell(
        "FundMaster — AI Insights",
        ["css/dashboard-widgets.css", "css/page-ai-insights.css"],
        "ai-insights.html",
        "Search funds...",
        body,
    )
    (ROOT / "ai-insights.html").write_text(html, encoding="utf-8")


def page_market_flow():
    body = """        <main class="content">
          <header class="page-head">
            <div>
              <h2 class="page-head__title">Market Liquidity &amp; Flow</h2>
              <p class="page-head__sub">Buying vs selling pressure, heatmap and block trades — Figma 11:1391.</p>
            </div>
            <div class="pill-group"><button type="button" class="pill pill--ghost">Daily</button><button type="button" class="pill pill--ghost">Intraday</button><button type="button" class="pill pill--ghost">Custom</button></div>
          </header>
          <section class="glass-panel">
            <div class="section-head"><h3 class="section-head__title">Aggregate Liquidity Flow</h3><span class="muted">Last 24h</span></div>
            <div class="mf-kpis">
              <div class="kpi-card"><p class="kpi-card__label">Buy vol</p><p class="kpi-card__value">62%</p></div>
              <div class="kpi-card"><p class="kpi-card__label">Sell vol</p><p class="kpi-card__value">38%</p></div>
              <div class="kpi-card"><p class="kpi-card__label">Net inflow</p><p class="kpi-card__value pos">+$12.4B</p></div>
              <div class="kpi-card"><p class="kpi-card__label">Volatility index</p><p class="kpi-card__value">14.2</p><p class="kpi-card__hint">H</p></div>
              <div class="kpi-card"><p class="kpi-card__label">Whale moves</p><p class="kpi-card__value">248</p><p class="kpi-card__hint">Significant</p></div>
              <div class="kpi-card"><p class="kpi-card__label">Slippage avg</p><p class="kpi-card__value">0.02%</p><p class="kpi-card__hint">Optimal</p></div>
            </div>
          </section>
          <div class="two-col">
            <section class="glass-panel">
              <h3 class="section-head__title section-head__title--compact">Liquidity Heatmap</h3>
              <ul class="mf-heat">
                <li><span>Equities (US)</span><div class="bar-track"><div class="bar-fill" style="width:82%"></div></div><span>82%</span></li>
                <li><span>Fixed Income</span><div class="bar-track"><div class="bar-fill" style="width:24%"></div></div><span>24%</span></li>
                <li><span>Forex (G10)</span><div class="bar-track"><div class="bar-fill" style="width:71%"></div></div><span>71%</span></li>
                <li><span>Digital Assets</span><div class="bar-track"><div class="bar-fill" style="width:38%"></div></div><span>38%</span></li>
              </ul>
              <button type="button" class="btn-outline mf-btn">Investigate flow</button>
            </section>
            <section class="glass-panel">
              <h3 class="section-head__title section-head__title--compact">Sector Inflow Distribution</h3>
              <ul class="mf-list">
                <li class="pos"><span>Technology</span><span>+$4.2B</span></li>
                <li class="neg"><span>Energy &amp; Utilities</span><span>-$1.8B</span></li>
                <li class="pos"><span>Healthcare</span><span>+$0.9B</span></li>
              </ul>
            </section>
          </div>
          <section class="glass-panel">
            <div class="section-head"><h3 class="section-head__title">Institutional Large-Scale Orders</h3><span class="muted">Refreshed 4s ago</span></div>
            <div class="data-table-wrap">
              <table class="data-table">
                <thead><tr><th>Asset</th><th>Flow</th><th>Size</th><th>Move</th><th>Time</th></tr></thead>
                <tbody>
                  <tr><td>NVDA.O</td><td>LARGE BUY</td><td>$142,500,000</td><td class="pos">+0.42%</td><td>14:22:01</td></tr>
                  <tr><td>AAPL.O</td><td>BLOCK SELL</td><td>$89,200,000</td><td class="neg">-0.15%</td><td>14:21:44</td></tr>
                  <tr><td>TSLA.O</td><td>INSTITUTIONAL BUY</td><td>$210,000,000</td><td class="pos">+1.12%</td><td>14:21:10</td></tr>
                  <tr><td>EUR/USD</td><td>ARBITRAGE</td><td>$450,000,000</td><td>0.00%</td><td>14:20:55</td></tr>
                </tbody>
              </table>
            </div>
          </section>
        </main>"""
    html = doc_shell(
        "FundMaster — Market Flow",
        ["css/dashboard-widgets.css", "css/page-market-flow.css"],
        "market-hub.html",
        "Search funds...",
        body,
        fab=False,
        extra_scripts=["scripts/api.js", "scripts/dashboard-data.js"],
    )
    (ROOT / "market-flow.html").write_text(html, encoding="utf-8")


def page_equity():
    body = """        <main class="content">
          <nav class="breadcrumb" aria-label="面包屑">
            <a href="portfolio-overview.html">Portfolio</a><span class="breadcrumb__sep">›</span>
            <span>Equity Funds</span>
          </nav>
          <header class="page-head">
            <div>
              <h2 class="page-head__title">Equity Funds</h2>
              <p class="page-head__sub">Core vs satellite equity sleeves with AI rebalancing signals.</p>
            </div>
            <div class="toolbar">
              <button type="button" class="btn-outline">Export Report</button>
              <button type="button" class="btn-outline">Rebalance</button>
            </div>
          </header>
          <div class="kpi-row eq-kpis">
            <div class="kpi-card"><p class="kpi-card__label">Total Equity Value</p><p class="kpi-card__value">$1,420,582.40</p><p class="kpi-card__hint">+12.4% MTD</p></div>
            <div class="kpi-card"><p class="kpi-card__label">Annualized Yield</p><p class="kpi-card__value">18.2%</p><p class="kpi-card__hint">Top 5% performance</p></div>
            <div class="kpi-card"><p class="kpi-card__label">Risk Rating</p><p class="kpi-card__value">Mod-High</p></div>
            <div class="kpi-card"><p class="kpi-card__label">AI Strategy Score</p><p class="kpi-card__value">94/100</p><p class="kpi-card__hint">Highly optimized</p></div>
          </div>
          <section class="glass-panel">
            <h3 class="section-head__title section-head__title--compact">High-Growth Trajectory</h3>
            <div class="pill-group" style="margin-bottom:12px"><button class="pill pill--ghost">1M</button><button class="pill pill--ghost">3M</button><button class="pill pill--ghost">YTD</button><button class="pill pill--ghost">MAX</button></div>
            <div class="eq-chart" role="presentation"></div>
            <div class="fd-stats eq-mini">
              <div><span class="fd-stats__k">Oct 24, 2023</span><span class="fd-stats__v">$1,142,000 (+8.2%)</span></div>
              <div><span class="fd-stats__k">Std Dev</span><span class="fd-stats__v">14.22%</span></div>
              <div><span class="fd-stats__k">Sharpe</span><span class="fd-stats__v">2.84</span></div>
              <div><span class="fd-stats__k">Beta vs S&amp;P 500</span><span class="fd-stats__v">1.12</span></div>
              <div><span class="fd-stats__k">Alpha</span><span class="fd-stats__v pos">+4.15%</span></div>
            </div>
          </section>
          <div class="two-col">
            <section class="glass-panel">
              <h3 class="section-head__title section-head__title--compact">Sector Allocation</h3>
              <ul class="fd-alloc">
                <li><span>Technology</span><span>42.5%</span><div class="bar-track"><div class="bar-fill" style="width:42.5%"></div></div></li>
                <li><span>Energy &amp; Renewables</span><span>18.2%</span><div class="bar-track"><div class="bar-fill" style="width:18.2%"></div></div></li>
                <li><span>Financials</span><span>12.8%</span><div class="bar-track"><div class="bar-fill" style="width:12.8%"></div></div></li>
                <li><span>Healthcare</span><span>10.5%</span><div class="bar-track"><div class="bar-fill" style="width:10.5%"></div></div></li>
                <li><span>Consumer Disc.</span><span>16.0%</span><div class="bar-track"><div class="bar-fill" style="width:16%"></div></div></li>
              </ul>
            </section>
            <section class="glass-panel">
              <h3 class="section-head__title section-head__title--compact">AI Rebalancing Alert</h3>
              <p class="muted">Tilt toward quality growth and reduce cyclical beta before CPI print.</p>
            </section>
          </div>
          <section class="glass-panel">
            <h3 class="section-head__title section-head__title--compact">Holdings Analysis</h3>
            <p class="muted" style="margin-top:0">Core 70% · Satellite 30%</p>
            <div class="data-table-wrap">
              <table class="data-table">
                <thead><tr><th>Symbol</th><th>Name</th><th>Value</th><th>1Y</th></tr></thead>
                <tbody>
                  <tr><td>VTS</td><td>Vanguard Total Stock · 25% weight</td><td>$355,145.00</td><td class="pos">+8.4%</td></tr>
                  <tr><td>SPY</td><td>SPDR S&amp;P 500 · 20% weight</td><td>$284,116.00</td><td class="pos">+7.1%</td></tr>
                </tbody>
              </table>
            </div>
          </section>
        </main>"""
    html = doc_shell(
        "FundMaster — Equity Funds",
        ["css/dashboard-widgets.css", "css/page-fund-deep-dive.css", "css/page-portfolio-family.css"],
        "portfolio-overview.html",
        "Search markets or funds...",
        body,
        fab=False,
        input_id="eq-q",
        extra_scripts=["scripts/api.js", "scripts/dashboard-data.js"],
    )
    (ROOT / "equity-funds.html").write_text(html, encoding="utf-8")


def page_global():
    body = """        <main class="content">
          <div class="mf-kpis gi-ticker">
            <div class="kpi-card"><p class="kpi-card__label">NASDAQ Composite</p><p class="kpi-card__value">16,428.52</p><p class="kpi-card__hint">+1.24%</p></div>
            <div class="kpi-card"><p class="kpi-card__label">DAX</p><p class="kpi-card__value">18,175.10</p><p class="kpi-card__hint kpi-card__hint--neg">-0.15%</p></div>
            <div class="kpi-card"><p class="kpi-card__label">Hang Seng</p><p class="kpi-card__value">17,139.17</p><p class="kpi-card__hint">+0.88%</p></div>
            <div class="kpi-card"><p class="kpi-card__label">USD/CNY</p><p class="kpi-card__value">7.2345</p><p class="kpi-card__hint">Steady</p></div>
          </div>
          <header class="page-head">
            <div>
              <h2 class="page-head__title">Global Strategic Matrix</h2>
              <p class="page-head__sub">Cross-border dispersion and AI allocation engine — Figma 11:2106.</p>
            </div>
            <div class="pill-group"><button class="pill pill--ghost">DAY</button><button class="pill pill--ghost">MONTH</button></div>
          </header>
          <section class="glass-panel">
            <div class="gi-months" aria-hidden="true">JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC</div>
            <div class="gi-matrix" role="img" aria-label="热力矩阵占位"></div>
          </section>
          <div class="two-col">
            <section class="glass-panel">
              <h3 class="section-head__title section-head__title--compact">AI Allocation Engine</h3>
              <ul class="gi-ai">
                <li><strong class="pos">BUY SIGNAL: EMERGING MARKETS</strong><p class="muted sm">Risk-on rotation confirmed by flow + carry.</p></li>
                <li><strong class="neg">RISK ALERT: USD/CNY</strong><p class="muted sm">Hedge 10% CN exposure via liquid proxies.</p></li>
              </ul>
              <button type="button" class="btn-outline">Generate Custom Strategy</button>
            </section>
            <section class="glass-panel">
              <h3 class="section-head__title section-head__title--compact">Market Sentiment</h3>
              <div class="mh-greed gi-sent"><span class="mh-greed__n">72</span><p class="muted">Fear ↔ Greed</p></div>
            </section>
          </div>
          <section class="glass-panel">
            <h3 class="section-head__title section-head__title--compact">Active Asset Allocation</h3>
            <div class="data-table-wrap">
              <table class="data-table">
                <thead><tr><th>Asset</th><th>Region</th><th>Value</th><th>Perf</th><th>Strategy</th></tr></thead>
                <tbody>
                  <tr><td>Vanguard Total World</td><td>Global</td><td>$1,245,600</td><td class="pos">+5.2%</td><td>HODL</td></tr>
                </tbody>
              </table>
            </div>
          </section>
        </main>"""
    html = doc_shell(
        "FundMaster — Global Investment",
        ["css/dashboard-widgets.css", "css/page-market-flow.css", "css/page-global-investment.css"],
        "global-investment.html",
        "Search markets or funds...",
        body,
        fab=False,
        input_id="gi-q",
        extra_scripts=["scripts/api.js", "scripts/dashboard-data.js"],
    )
    (ROOT / "global-investment.html").write_text(html, encoding="utf-8")


def page_portfolio():
    body = """        <main class="content">
          <header class="page-head">
            <div>
              <h2 class="page-head__title">Portfolio Overview</h2>
              <p class="page-head__sub">Holdings table + AI commentary — Figma 11:2408 / 42:2.</p>
            </div>
            <div class="toolbar">
              <a class="btn-outline" href="equity-funds.html">Equity sleeve</a>
              <a class="btn-outline" href="debt-funds.html">Debt sleeve</a>
            </div>
          </header>
          <section class="glass-panel po-summary">
            <h3 class="section-head__title section-head__title--compact">Total Account Assets</h3>
            <div class="po-split">
              <div><p class="muted">Daily gain/loss</p><p class="po-big pos">+¥500.00</p></div>
              <div class="po-table-labels muted sm">Asset / Value · Daily return · Sector · Holdings</div>
            </div>
          </section>
          <div class="data-table-wrap">
            <table class="data-table">
              <thead><tr><th>Asset</th><th>Value</th><th>Daily</th><th>Return</th><th>Sector</th></tr></thead>
              <tbody>
                <tr><td>Tianyuan Huiteng Tech ETF</td><td>¥2,000.00</td><td>+¥500.00</td><td class="pos">+1.00%</td><td class="pos">+1.2%</td></tr>
                <tr><td>—</td><td>+¥5,000.00</td><td>—</td><td class="pos">+10.0%</td><td>—</td></tr>
                <tr><td>Global Semiconductor Index</td><td>¥4,500.00</td><td>-¥120.00</td><td class="neg">-0.24%</td><td class="neg">-0.8%</td></tr>
                <tr><td>Clean Energy Strategic Fund</td><td>¥3,200.00</td><td>—</td><td>—</td><td>—</td></tr>
              </tbody>
            </table>
          </div>
          <button type="button" class="btn-outline" style="margin-top:12px">Add New Holding</button>
          <section class="glass-panel" style="margin-top:24px">
            <h3 class="section-head__title section-head__title--compact">AI Portfolio Analysis</h3>
            <p class="muted">AI Assistant Selection</p>
            <div class="po-ai">
              <div><span class="muted sm">Signal</span><div><span class="chip chip--warn">Yellow</span></div></div>
              <div><span class="muted sm">Detailed analysis</span><p>Balanced exposure with concentration in AI-linked names.</p></div>
              <div><span class="muted sm">Rebalancing</span><ul>
                <li>Increase Tianyuan Huiteng Tech ETF by 2.5%.</li>
                <li>Rotate profits from infrastructure into green energy strategic sleeve.</li>
              </ul></div>
            </div>
          </section>
        </main>"""
    html = doc_shell(
        "FundMaster — Portfolio Overview",
        ["css/dashboard-widgets.css", "css/page-portfolio-overview.css"],
        "portfolio-overview.html",
        "Search markets or funds...",
        body,
        fab=True,
        input_id="po-q",
        extra_scripts=["scripts/api.js", "scripts/dashboard-data.js"],
    )
    (ROOT / "portfolio-overview.html").write_text(html, encoding="utf-8")


def page_debt():
    body = """        <main class="content">
          <nav class="breadcrumb" aria-label="面包屑">
            <a href="portfolio-overview.html">Portfolio</a><span class="breadcrumb__sep">›</span>
            <span>Debt Funds</span>
          </nav>
          <header class="page-head">
            <div>
              <h2 class="page-head__title">Debt Portfolio</h2>
              <p class="page-head__sub">Strategic yield optimization and risk exposure management.</p>
            </div>
            <div class="toolbar">
              <button type="button" class="btn-outline">Export Report</button>
              <button type="button" class="btn-outline">Rebalance Assets</button>
            </div>
          </header>
          <div class="kpi-row">
            <div class="kpi-card"><p class="kpi-card__label">Total Value</p><p class="kpi-card__value">$2,482,900</p><p class="kpi-card__hint">+4.2% YoY</p></div>
            <div class="kpi-card"><p class="kpi-card__label">Average Yield</p><p class="kpi-card__value">5.82%</p><p class="muted sm">Target 6.00%</p></div>
            <div class="kpi-card"><p class="kpi-card__label">Weighted Maturity</p><p class="kpi-card__value">4.2 yrs</p><p class="muted sm">Short-term focus</p></div>
            <div class="kpi-card"><p class="kpi-card__label">Risk Rating</p><p class="kpi-card__value">AA-</p><p class="muted sm">Investment grade</p></div>
          </div>
          <div class="two-col">
            <section class="glass-panel">
              <h3 class="section-head__title section-head__title--compact">Yield Comparison</h3>
              <p class="muted sm">Stable vs High-Yield</p>
              <div class="debt-chart" role="presentation"></div>
              <div class="debt-legend"><span>Stable Income</span><span>High-Yield</span></div>
            </section>
            <section class="glass-panel">
              <h3 class="section-head__title section-head__title--compact">Risk Composition</h3>
              <ul class="fd-alloc">
                <li><span>AAA / Government</span><span>42%</span><div class="bar-track"><div class="bar-fill" style="width:42%"></div></div></li>
                <li><span>AA / Corporate HG</span><span>28%</span><div class="bar-track"><div class="bar-fill" style="width:28%"></div></div></li>
                <li><span>BBB / IG</span><span>15%</span><div class="bar-track"><div class="bar-fill" style="width:15%"></div></div></li>
                <li><span>BB / High Yield</span><span>10%</span><div class="bar-track"><div class="bar-fill" style="width:10%"></div></div></li>
                <li><span>Unrated / Private</span><span>5%</span><div class="bar-track"><div class="bar-fill" style="width:5%"></div></div></li>
              </ul>
              <p class="muted sm" style="margin-top:12px"><strong>AI Strategy Shift</strong> — barbell US Treasuries with selective HY energy paper.</p>
            </section>
          </div>
          <section class="glass-panel">
            <div class="section-head"><h3 class="section-head__title">Active Debt Holdings</h3><div class="pill-group"><button class="pill pill--ghost">Stable (5)</button><button class="pill pill--ghost">High-Yield (3)</button></div></div>
            <div class="data-table-wrap">
              <table class="data-table">
                <thead><tr><th>Fund</th><th>Yield</th><th>Maturity</th><th>Risk</th><th>Allocation</th></tr></thead>
                <tbody>
                  <tr><td>Vanguard Total Bond · BND</td><td>4.12%</td><td>Dec 2028</td><td>AAA</td><td>$520,000</td></tr>
                  <tr><td>BlackRock Strategic Bond</td><td>5.45%</td><td>Jun 2027</td><td>AA</td><td>$310,000</td></tr>
                </tbody>
              </table>
            </div>
          </section>
        </main>"""
    html = doc_shell(
        "FundMaster — Debt Funds",
        ["css/dashboard-widgets.css", "css/page-fund-deep-dive.css", "css/page-portfolio-family.css", "css/page-debt-funds.css"],
        "portfolio-overview.html",
        "Search markets or funds...",
        body,
        fab=False,
        input_id="de-q",
        extra_scripts=["scripts/api.js", "scripts/dashboard-data.js"],
    )
    (ROOT / "debt-funds.html").write_text(html, encoding="utf-8")


def page_settings():
    body = """        <main class="content">
          <header class="page-head">
            <div>
              <h2 class="page-head__title">Settings</h2>
              <p class="page-head__sub">Portfolio email delivery configuration.</p>
            </div>
          </header>
          <form data-smtp-form>
          <div class="two-col">
            <section class="glass-panel">
              <h3 class="section-head__title section-head__title--compact">Sender</h3>
              <label class="st-label">Email<input class="st-input" name="email" type="email" autocomplete="email" required /></label>
              <label class="st-label">Sender name<input class="st-input" name="sender_name" type="text" autocomplete="organization" /></label>
              <label class="st-label">SMTP host<input class="st-input" name="smtp_host" type="text" placeholder="smtp.example.com" required /></label>
            </section>
            <section class="glass-panel">
              <h3 class="section-head__title section-head__title--compact">Connection</h3>
              <label class="st-label">SMTP port<input class="st-input" name="smtp_port" type="number" min="1" max="65535" value="587" required /></label>
              <label class="st-label">Encryption<select class="st-input" name="encryption"><option value="tls">TLS</option><option value="ssl">SSL</option><option value="none">None</option></select></label>
              <label class="st-label">App password<input class="st-input" name="password" type="password" autocomplete="new-password" placeholder="Leave unchanged when masked" /></label>
            </section>
          </div>
          <section class="glass-panel">
            <h3 class="section-head__title section-head__title--compact">Delivery Test</h3>
            <label class="st-label">Test recipient<input class="st-input" name="test_email" type="email" autocomplete="email" /></label>
            <div class="toolbar"><button type="submit" class="btn-outline">Save SMTP</button><button type="button" class="btn-outline" data-test-email>Send Test Email</button></div>
          </section>
          </form>
        </main>"""
    html = doc_shell(
        "FundMaster — Settings",
        ["css/dashboard-widgets.css", "css/page-settings.css"],
        "settings.html",
        "Search funds...",
        body,
        fab=False,
        input_id="st-q",
        extra_scripts=["scripts/api.js", "scripts/dashboard-data.js"],
    )
    (ROOT / "settings.html").write_text(html, encoding="utf-8")


def main():
    page_fund_deep_dive()
    page_market_hub()
    page_market_flow()
    page_equity()
    page_global()
    page_portfolio()
    page_debt()
    page_settings()
    print("Generated HTML pages in", ROOT)


if __name__ == "__main__":
    main()
