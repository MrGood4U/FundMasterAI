(function (window, document) {
  "use strict";

  const api = window.FundMasterAPI;
  const state = {
    history: [],
    range: "1Y",
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function numberValue(value) {
    if (value === null || value === undefined || value === "") return null;
    const parsed = Number(String(value).replace(/[%+,¥$]/g, "").trim());
    return Number.isFinite(parsed) ? parsed : null;
  }

  function formatPercent(value, digits = 2) {
    const number = numberValue(value);
    if (number === null) return "—";
    return `${number > 0 ? "+" : ""}${number.toFixed(digits)}%`;
  }

  function formatNav(value) {
    const number = numberValue(value);
    return number === null ? "—" : `¥ ${number.toFixed(4)}`;
  }

  function toDate(value) {
    const date = value instanceof Date ? value : new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
  }

  function formatDate(value) {
    const date = toDate(value);
    if (!date) return "—";
    return new Intl.DateTimeFormat("en-CA", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(date);
  }

  function compactDate(date) {
    return `${date.getFullYear()}${String(date.getMonth() + 1).padStart(2, "0")}${String(date.getDate()).padStart(2, "0")}`;
  }

  function setSignedClass(node, value, baseClass) {
    if (!node) return;
    const number = numberValue(value);
    node.className = baseClass;
    if (number !== null && number > 0) node.classList.add("pos");
    if (number !== null && number < 0) node.classList.add("neg");
  }

  function normalizeHistory(rows) {
    if (!Array.isArray(rows)) return [];
    return rows
      .map((row) => ({
        date: toDate(row.date || row.datetime || row.time),
        nav: numberValue(row.unit_net_value ?? row.close ?? row.nav),
        change: numberValue(row.change_pct ?? row.daily_growth_rate ?? row.daily_return),
      }))
      .filter((row) => row.date && row.nav !== null && row.nav > 0)
      .sort((a, b) => a.date - b.date);
  }

  function returnBetween(rows) {
    if (!rows || rows.length < 2) return null;
    const first = rows[0].nav;
    const last = rows[rows.length - 1].nav;
    if (!first) return null;
    return (last / first - 1) * 100;
  }

  function rowsForDays(rows, days) {
    if (!rows.length) return [];
    const latest = rows[rows.length - 1].date;
    const cutoff = new Date(latest);
    cutoff.setDate(cutoff.getDate() - days);
    return rows.filter((row) => row.date >= cutoff);
  }

  function rowsForRange(range) {
    const daysByRange = { "1M": 31, "3M": 93, "1Y": 366 };
    return daysByRange[range] ? rowsForDays(state.history, daysByRange[range]) : state.history;
  }

  function renderChart(range = state.range) {
    state.range = range;
    const chart = byId("fd-chart");
    const caption = byId("fd-chart-caption");
    if (!chart) return;

    document.querySelectorAll("[data-history-range]").forEach((button) => {
      button.classList.toggle("pill--active", button.dataset.historyRange === range);
    });

    const rows = rowsForRange(range);
    if (rows.length < 2) {
      chart.innerHTML = '<div class="fd-empty-state">Published NAV history is unavailable for this period.</div>';
      if (caption) caption.textContent = "No template chart has been substituted.";
      return;
    }

    const width = 960;
    const height = 250;
    const padding = 18;
    const values = rows.map((row) => row.nav);
    let min = Math.min(...values);
    let max = Math.max(...values);
    if (min === max) {
      min *= 0.99;
      max *= 1.01;
    }
    const span = max - min;
    const usableWidth = width - padding * 2;
    const usableHeight = height - padding * 2;
    const points = rows.map((row, index) => ({
      x: padding + (index / (rows.length - 1)) * usableWidth,
      y: padding + (1 - (row.nav - min) / span) * usableHeight,
    }));
    const line = points.map((point, index) => `${index === 0 ? "M" : "L"}${point.x.toFixed(2)},${point.y.toFixed(2)}`).join(" ");
    const area = `${line} L${points[points.length - 1].x.toFixed(2)},${height - padding} L${points[0].x.toFixed(2)},${height - padding} Z`;
    const positive = rows[rows.length - 1].nav >= rows[0].nav;
    const stroke = positive ? "#00ffa3" : "#ff6b6b";
    const grid = [0.25, 0.5, 0.75].map((ratio) => {
      const y = (padding + ratio * usableHeight).toFixed(2);
      return `<line x1="${padding}" y1="${y}" x2="${width - padding}" y2="${y}" class="fd-chart__grid" />`;
    }).join("");

    chart.innerHTML = `
      <svg class="fd-chart__svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" aria-hidden="true">
        <defs>
          <linearGradient id="fd-nav-area" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="${stroke}" stop-opacity="0.34" />
            <stop offset="100%" stop-color="${stroke}" stop-opacity="0.02" />
          </linearGradient>
        </defs>
        ${grid}
        <path d="${area}" fill="url(#fd-nav-area)" />
        <path d="${line}" fill="none" stroke="${stroke}" stroke-width="3" vector-effect="non-scaling-stroke" />
      </svg>
      <div class="fd-chart__range">
        <span>${formatDate(rows[0].date)} · ${formatNav(rows[0].nav)}</span>
        <strong>${formatPercent(returnBetween(rows))}</strong>
        <span>${formatDate(rows[rows.length - 1].date)} · ${formatNav(rows[rows.length - 1].nav)}</span>
      </div>`;
    chart.setAttribute("aria-label", `Published NAV from ${formatDate(rows[0].date)} to ${formatDate(rows[rows.length - 1].date)}`);
    if (caption) caption.textContent = `${rows.length} published NAV observations · ${range === "ALL" ? "available five-year window" : range}`;
  }

  function renderPerformance() {
    if (!state.history.length) {
      renderChart(state.range);
      return;
    }

    const latest = state.history[state.history.length - 1];
    const previous = state.history[state.history.length - 2];
    const latestChange = latest.change !== null
      ? latest.change
      : previous ? (latest.nav / previous.nav - 1) * 100 : null;
    const navNode = byId("fd-kpi-nav");
    const changeNode = byId("fd-kpi-change");
    const asOf = byId("fd-as-of");
    if (navNode) navNode.textContent = formatNav(latest.nav);
    if (changeNode) {
      changeNode.textContent = formatPercent(latestChange);
      setSignedClass(changeNode, latestChange, "kpi-card__value");
    }
    if (asOf) asOf.textContent = `Published NAV date · ${formatDate(latest.date)}`;

    const latestYear = latest.date.getFullYear();
    const ytdRows = state.history.filter((row) => row.date.getFullYear() === latestYear);
    const oneYearRows = rowsForDays(state.history, 366);
    const threeYearRows = rowsForDays(state.history, 1096);
    const threeYearSpan = threeYearRows.length > 1
      ? (threeYearRows[threeYearRows.length - 1].date - threeYearRows[0].date) / 86400000
      : 0;
    const threeYearTotal = returnBetween(threeYearRows);
    const threeYearAnnualized = threeYearTotal !== null && threeYearSpan >= 900
      ? (Math.pow(1 + threeYearTotal / 100, 365.25 / threeYearSpan) - 1) * 100
      : null;

    const metrics = [
      ["fd-stat-date", formatDate(latest.date), null],
      ["fd-stat-ytd", formatPercent(returnBetween(ytdRows)), returnBetween(ytdRows)],
      ["fd-stat-1y", formatPercent(returnBetween(oneYearRows)), returnBetween(oneYearRows)],
      ["fd-stat-3y", formatPercent(threeYearAnnualized), threeYearAnnualized],
      ["fd-stat-window", formatPercent(returnBetween(state.history)), returnBetween(state.history)],
    ];
    metrics.forEach(([id, text, value]) => {
      const node = byId(id);
      if (!node) return;
      node.textContent = text;
      setSignedClass(node, value, "fd-stats__v");
    });
    renderChart(state.range);
  }

  function renderRisk() {
    const root = byId("fd-risk");
    if (!root) return;
    const rows = rowsForDays(state.history, 366);
    if (rows.length < 10) {
      root.innerHTML = '<li><div><strong>Risk statistics unavailable</strong><span class="muted">At least 10 published NAV observations are required.</span></div><em>—</em></li>';
      return;
    }

    const returns = [];
    let peak = rows[0].nav;
    let maxDrawdown = 0;
    for (let index = 1; index < rows.length; index += 1) {
      returns.push(rows[index].nav / rows[index - 1].nav - 1);
      peak = Math.max(peak, rows[index].nav);
      maxDrawdown = Math.min(maxDrawdown, rows[index].nav / peak - 1);
    }
    const mean = returns.reduce((sum, value) => sum + value, 0) / returns.length;
    const variance = returns.reduce((sum, value) => sum + Math.pow(value - mean, 2), 0) / Math.max(returns.length - 1, 1);
    const volatility = Math.sqrt(variance) * Math.sqrt(252) * 100;
    const best = Math.max(...returns) * 100;
    const worst = Math.min(...returns) * 100;

    root.innerHTML = `
      <li><div><strong>Annualized Volatility</strong><span class="muted">Calculated from the latest 1Y NAV window</span></div><em>${formatPercent(volatility)}</em></li>
      <li><div><strong>Maximum Drawdown</strong><span class="muted">Peak-to-trough decline in the latest 1Y window</span></div><em class="neg">${formatPercent(maxDrawdown * 100)}</em></li>
      <li><div><strong>Best Daily Move</strong><span class="muted">Largest published NAV increase in the latest 1Y window</span></div><em class="pos">${formatPercent(best)}</em></li>
      <li><div><strong>Worst Daily Move</strong><span class="muted">Largest published NAV decline in the latest 1Y window</span></div><em class="neg">${formatPercent(worst)}</em></li>`;
  }

  function renderAllocation(rows) {
    const root = byId("fd-allocation");
    const caption = byId("fd-allocation-caption");
    if (!root) return false;
    const normalized = Array.isArray(rows)
      ? rows.map((row) => ({
        type: row.asset_type || row.type || "Other",
        pct: numberValue(row.pct ?? row.weight ?? row.ratio),
      })).filter((row) => row.pct !== null)
      : [];
    if (!normalized.length) {
      root.innerHTML = '<li class="fd-empty-state">No public asset-allocation data is available for this fund.</li>';
      if (caption) caption.textContent = "Unavailable from the public source";
      return false;
    }
    root.innerHTML = normalized.map((row) => {
      const width = Math.max(0, Math.min(row.pct, 100));
      return `
        <li>
          <span>${escapeHtml(row.type)}</span><span>${formatPercent(row.pct)}</span>
          <div class="bar-track"><div class="bar-fill" style="width:${width.toFixed(2)}%"></div></div>
        </li>`;
    }).join("");
    if (caption) caption.textContent = `${normalized.length} public asset categories`;
    return true;
  }

  function renderHoldings(rows) {
    const tbody = byId("fd-holdings-tbody");
    if (!tbody) return false;
    const normalized = Array.isArray(rows)
      ? rows.map((row) => ({
        code: row.stock_code || row.ticker || row.code || "—",
        name: row.stock_name || row.name || "—",
        pct: numberValue(row.pct ?? row.weight ?? row.ratio),
      })).filter((row) => row.code !== "—" || row.name !== "—")
      : [];
    if (!normalized.length) {
      tbody.innerHTML = '<tr><td colspan="3" class="muted fd-table-state">No public stock-holdings data is available for this fund.</td></tr>';
      return false;
    }
    tbody.innerHTML = normalized.slice(0, 10).map((row) => `
      <tr>
        <td><code>${escapeHtml(row.code)}</code></td>
        <td>${escapeHtml(row.name)}</td>
        <td class="fd-holding-weight">${formatPercent(row.pct)}</td>
      </tr>`).join("");
    return true;
  }

  function renderProfile(basic, requestedCode, requestedName) {
    const passedName = requestedName && requestedName !== requestedCode ? requestedName : null;
    const name = basic?.fund_name || passedName || `Fund ${requestedCode}`;
    const type = basic?.fund_type || "Public Fund";
    const company = basic?.fund_company || null;
    const title = byId("fd-fund-name");
    const subtitle = byId("fd-fund-subtitle");
    if (title) title.textContent = name;
    if (subtitle) subtitle.textContent = company ? `${type} · ${company}` : `${type} · Public fund profile`;
    if (byId("fd-breadcrumb-type")) byId("fd-breadcrumb-type").textContent = type;
    if (byId("fd-breadcrumb-current")) byId("fd-breadcrumb-current").textContent = name;
    if (byId("fd-kpi-code")) byId("fd-kpi-code").textContent = basic?.fund_code || requestedCode;

    const manager = byId("fd-manager-name");
    const managerMeta = byId("fd-manager-meta");
    if (manager) manager.textContent = basic?.fund_manager || "Not provided by source";
    if (managerMeta) {
      const meta = [
        basic?.fund_company && `Company · ${basic.fund_company}`,
        basic?.inception_date && `Inception · ${basic.inception_date}`,
        basic?.latest_aum && `Latest AUM · ${basic.latest_aum}`,
      ].filter(Boolean);
      managerMeta.innerHTML = meta.length
        ? meta.map((item) => `<span>${escapeHtml(item)}</span>`).join("")
        : "<span>Management metadata unavailable</span>";
    }

    const objective = byId("fd-objective");
    const strategy = byId("fd-strategy");
    if (objective) objective.textContent = basic?.investment_objective || "Investment objective not provided by the public source.";
    if (strategy) strategy.textContent = basic?.investment_strategy || "Investment strategy not provided by the public source.";
    return Boolean(basic);
  }

  function matchingFundProfile(basic, requestedCode) {
    if (!basic || !requestedCode) return null;
    const profileCode = String(basic.fund_code || basic.code || "").trim();
    if (!profileCode) return null;
    const normalize = (value) => /^\d+$/.test(value) ? value.padStart(6, "0") : value.toUpperCase();
    return normalize(profileCode) === normalize(String(requestedCode).trim()) ? basic : null;
  }

  function setNotice(profileLoaded, historyLoaded, allocationLoaded, holdingsLoaded) {
    const notice = byId("fd-data-notice");
    const chip = byId("fd-data-chip");
    const sources = [
      profileLoaded && "fund profile",
      historyLoaded && "NAV history",
      allocationLoaded && "asset allocation",
      holdingsLoaded && "top holdings",
    ].filter(Boolean);
    const complete = profileLoaded && historyLoaded;

    if (notice) {
      notice.dataset.state = sources.length ? (complete ? "success" : "partial") : "error";
      notice.textContent = sources.length
        ? `Verified public data loaded: ${sources.join(", ")}. Missing fields are shown as unavailable; no template values are substituted.`
        : "No verified fund data was returned. The page is showing unavailable states instead of template values.";
    }
    if (chip) {
      chip.textContent = complete ? "PUBLIC DATA" : sources.length ? "PARTIAL DATA" : "NO DATA";
      chip.className = complete ? "chip chip--live" : "chip fd-data-chip--partial";
    }
  }

  function rejected(message) {
    return Promise.reject(new Error(message));
  }

  async function init() {
    const params = new URLSearchParams(window.location.search);
    const fundCode = String(params.get("code") || "").trim();
    const requestedName = String(params.get("name") || "").trim();

    if (!fundCode) {
      renderProfile(null, "—", requestedName);
      setNotice(false, false, false, false);
      return;
    }

    renderProfile(null, fundCode, requestedName);
    const end = new Date();
    const start = new Date(end);
    start.setFullYear(start.getFullYear() - 5);

    const calls = [
      api?.publicFund?.getBasicInfo ? api.publicFund.getBasicInfo(fundCode) : rejected("Basic-info API unavailable"),
      api?.market?.getFundHist ? api.market.getFundHist(fundCode, {
        start_date: compactDate(start),
        end_date: compactDate(end),
        period: "daily",
      }) : rejected("History API unavailable"),
      api?.publicFund?.getDetailHold ? api.publicFund.getDetailHold(fundCode) : rejected("Allocation API unavailable"),
      api?.publicFund?.getStockHolds ? api.publicFund.getStockHolds(fundCode, String(end.getFullYear())) : rejected("Holdings API unavailable"),
    ];

    const [basicResult, historyResult, allocationResult, holdingsResult] = await Promise.allSettled(calls);
    const basicRows = basicResult.status === "fulfilled" && Array.isArray(basicResult.value) ? basicResult.value : [];
    const basic = matchingFundProfile(basicRows[0] || null, fundCode);
    state.history = normalizeHistory(historyResult.status === "fulfilled" ? historyResult.value : []);

    const profileLoaded = renderProfile(basic, fundCode, requestedName);
    renderPerformance();
    renderRisk();
    // Some legacy endpoints can return a default sample when the requested code
    // is unknown. Only attach descriptive data after the profile confirms that
    // it belongs to the code in the URL.
    const allocationLoaded = renderAllocation(
      basic && allocationResult.status === "fulfilled" ? allocationResult.value : [],
    );
    const holdingsLoaded = renderHoldings(
      basic && holdingsResult.status === "fulfilled" ? holdingsResult.value : [],
    );
    setNotice(profileLoaded, state.history.length > 1, allocationLoaded, holdingsLoaded);

    [basicResult, historyResult, allocationResult, holdingsResult].forEach((result) => {
      if (result.status === "rejected") console.error("Deep Dive public-data request failed:", result.reason);
    });
  }

  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-history-range]");
    if (button) renderChart(button.dataset.historyRange);
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    void init();
  }
})(window, document);
