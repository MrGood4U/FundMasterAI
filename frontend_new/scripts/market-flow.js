(function (window, document) {
  "use strict";

  const api = window.FundMasterAPI;
  const root = document.querySelector("[data-market-flow-page]");
  if (!api || !root) return;

  const CACHE_KEY = "fundmaster:market-flow:etf:v1";
  const CACHE_VERSION = 1;
  const CACHE_TTL_MS = 5 * 60 * 1000;

  function numberValue(value) {
    if (value === null || value === undefined || value === "") return null;
    const parsed = Number(String(value).replace(/[,%+¥]/g, "").trim());
    return Number.isFinite(parsed) ? parsed : null;
  }

  function normalizeEtf(record) {
    return {
      code: String(record?.fund_code || record?.code || ""),
      name: String(record?.fund_name || record?.name || record?.fund_code || "Unnamed ETF"),
      mainFlow: numberValue(record?.main_net_inflow_amount),
      mainFlowRatio: numberValue(record?.main_net_inflow_pct),
      superLargeFlow: numberValue(record?.super_large_net_inflow_amount),
      largeFlow: numberValue(record?.large_net_inflow_amount),
      mediumFlow: numberValue(record?.medium_net_inflow_amount),
      smallFlow: numberValue(record?.small_net_inflow_amount),
      turnover: numberValue(record?.turnover),
      changePct: numberValue(record?.change_pct),
      updateTime: record?.update_time || record?.data_date || null,
    };
  }

  function readCache() {
    try {
      const raw = window.sessionStorage.getItem(CACHE_KEY);
      if (!raw) return null;
      const cached = JSON.parse(raw);
      if (
        cached?.version !== CACHE_VERSION
        || !Array.isArray(cached?.items)
        || !cached.items.length
        || !Number.isFinite(Number(cached?.updatedAt))
      ) {
        return null;
      }
      return cached;
    } catch (error) {
      console.warn("Market Flow cache is unavailable:", error.message);
      return null;
    }
  }

  function writeCache(items) {
    try {
      window.sessionStorage.setItem(CACHE_KEY, JSON.stringify({
        version: CACHE_VERSION,
        items,
        updatedAt: Date.now(),
      }));
    } catch (error) {
      console.warn("Market Flow cache could not be updated:", error.message);
    }
  }

  function cacheIsFresh(cached) {
    const age = Date.now() - Number(cached?.updatedAt);
    return Number.isFinite(age) && age >= 0 && age < CACHE_TTL_MS;
  }

  function formatCount(value) {
    return Number(value || 0).toLocaleString("en-US", { maximumFractionDigits: 0 });
  }

  function formatPercent(value) {
    const numeric = numberValue(value);
    if (numeric === null) return "—";
    return `${numeric > 0 ? "+" : ""}${numeric.toFixed(2)}%`;
  }

  function formatMoney(value) {
    const numeric = numberValue(value);
    if (numeric === null) return "—";
    const absolute = Math.abs(numeric);
    const sign = numeric > 0 ? "+" : numeric < 0 ? "−" : "";
    let scaled = absolute;
    let suffix = "";
    if (absolute >= 1e9) {
      scaled = absolute / 1e9;
      suffix = "B";
    } else if (absolute >= 1e6) {
      scaled = absolute / 1e6;
      suffix = "M";
    } else if (absolute >= 1e3) {
      scaled = absolute / 1e3;
      suffix = "K";
    }
    return `${sign}¥${scaled.toFixed(suffix ? 2 : 0)}${suffix}`;
  }

  function flowClass(value) {
    const numeric = numberValue(value);
    return numeric > 0 ? "pos" : numeric < 0 ? "neg" : "";
  }

  function setStatus(message, isError = false) {
    const status = document.querySelector("[data-market-flow-status]");
    if (!status) return;
    status.textContent = message;
    status.classList.toggle("api-status--error", isError);
  }

  function setCard(key, value, hint, tone = "") {
    const card = document.querySelector(`[data-flow-card="${key}"]`);
    if (!card) return;
    const valueNode = card.querySelector(".kpi-card__value");
    const hintNode = card.querySelector(".kpi-card__hint");
    if (valueNode) {
      valueNode.textContent = value;
      valueNode.classList.remove("pos", "neg");
      if (tone) valueNode.classList.add(tone);
    }
    if (hintNode) hintNode.textContent = hint;
  }

  function sum(items, key) {
    return items.reduce((total, item) => total + (numberValue(item[key]) || 0), 0);
  }

  function renderSummary(items) {
    const mainFlow = sum(items, "mainFlow");
    const superLargeFlow = sum(items, "superLargeFlow");
    const largeFlow = sum(items, "largeFlow");
    const turnover = sum(items, "turnover");
    const inflowCount = items.filter((item) => (item.mainFlow || 0) > 0).length;

    setCard("main", formatMoney(mainFlow), "ETF universe", flowClass(mainFlow));
    setCard("super", formatMoney(superLargeFlow), "Super-large orders", flowClass(superLargeFlow));
    setCard("large", formatMoney(largeFlow), "Large orders", flowClass(largeFlow));
    setCard("turnover", formatMoney(turnover), "Reported turnover");
    setCard("inflow", formatCount(inflowCount), `${(inflowCount / items.length * 100).toFixed(1)}% of tracked ETFs`);
    setCard("tracked", formatCount(items.length), "Live ETF rows");
  }

  function renderOrderBreakdown(items) {
    const rows = [
      { label: "Super Large", value: sum(items, "superLargeFlow") },
      { label: "Large", value: sum(items, "largeFlow") },
      { label: "Medium", value: sum(items, "mediumFlow") },
      { label: "Small", value: sum(items, "smallFlow") },
    ];
    const maxAbsolute = Math.max(...rows.map((row) => Math.abs(row.value)), 1);
    const list = document.querySelector("[data-order-flow-breakdown]");
    if (!list) return;
    list.replaceChildren();

    rows.forEach((row) => {
      const item = document.createElement("li");
      const label = document.createElement("span");
      const value = document.createElement("strong");
      const track = document.createElement("div");
      const fill = document.createElement("div");
      label.textContent = row.label;
      value.textContent = formatMoney(row.value);
      value.className = flowClass(row.value);
      track.className = "bar-track";
      fill.className = `bar-fill ${flowClass(row.value)}`.trim();
      fill.style.width = `${Math.max(2, Math.abs(row.value) / maxAbsolute * 100)}%`;
      track.append(fill);
      item.append(label, value, track);
      list.append(item);
    });
  }

  function renderLeaderGroup(container, title, items) {
    if (!container) return;
    const heading = document.createElement("h4");
    heading.textContent = title;
    const list = document.createElement("ul");
    list.className = "mf-list";
    items.forEach((item) => {
      const row = document.createElement("li");
      const identity = document.createElement("span");
      const value = document.createElement("strong");
      identity.textContent = `${item.name} · ${item.code}`;
      value.textContent = formatMoney(item.mainFlow);
      value.className = flowClass(item.mainFlow);
      row.append(identity, value);
      list.append(row);
    });
    container.replaceChildren(heading, list);
  }

  function renderLeaders(items) {
    const inflows = items
      .filter((item) => (item.mainFlow || 0) > 0)
      .sort((a, b) => b.mainFlow - a.mainFlow)
      .slice(0, 3);
    const outflows = items
      .filter((item) => (item.mainFlow || 0) < 0)
      .sort((a, b) => a.mainFlow - b.mainFlow)
      .slice(0, 3);
    renderLeaderGroup(document.querySelector("[data-flow-inflows]"), "Top Inflows", inflows);
    renderLeaderGroup(document.querySelector("[data-flow-outflows]"), "Top Outflows", outflows);
  }

  function renderTable(items) {
    const tbody = document.querySelector("[data-flow-table-body]");
    if (!tbody) return;
    tbody.replaceChildren();
    const rows = items
      .slice()
      .sort((a, b) => Math.abs(b.mainFlow || 0) - Math.abs(a.mainFlow || 0))
      .slice(0, 12);

    rows.forEach((item) => {
      const row = document.createElement("tr");
      const values = [
        `${item.name} · ${item.code}`,
        formatMoney(item.mainFlow),
        formatPercent(item.mainFlowRatio),
        formatMoney(item.turnover),
        formatPercent(item.changePct),
      ];
      values.forEach((value, index) => {
        const cell = document.createElement("td");
        cell.textContent = value;
        if (index === 1) cell.className = flowClass(item.mainFlow);
        if (index === 2) cell.className = flowClass(item.mainFlowRatio);
        if (index === 4) cell.className = flowClass(item.changePct);
        row.append(cell);
      });
      tbody.append(row);
    });
  }

  function latestSourceTime(items) {
    const timestamps = items
      .map((item) => item.updateTime ? new Date(item.updateTime).getTime() : Number.NaN)
      .filter(Number.isFinite);
    if (!timestamps.length) return "source time unavailable";
    return `source ${new Intl.DateTimeFormat("en-GB", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(new Date(Math.max(...timestamps)))}`;
  }

  function render(items, sourceLabel) {
    renderSummary(items);
    renderOrderBreakdown(items);
    renderLeaders(items);
    renderTable(items);
    setStatus(`${sourceLabel} · ${formatCount(items.length)} ETFs · ${latestSourceTime(items)}`);
  }

  function renderUnavailable(message) {
    document.querySelectorAll(".mf-kpis .kpi-card").forEach((card) => {
      const value = card.querySelector(".kpi-card__value");
      const hint = card.querySelector(".kpi-card__hint");
      if (value) value.textContent = "—";
      if (hint) hint.textContent = "Verified ETF flow unavailable";
    });
    const breakdown = document.querySelector("[data-order-flow-breakdown]");
    const leaders = document.querySelector("[data-flow-leaders]");
    const tbody = document.querySelector("[data-flow-table-body]");
    if (breakdown) breakdown.innerHTML = '<li class="data-unavailable">No verified order-size flow data available.</li>';
    if (leaders) leaders.innerHTML = '<div class="data-unavailable">No verified ETF flow leaders available.</div>';
    if (tbody) tbody.innerHTML = '<tr><td colspan="5">No verified ETF capital-flow data available.</td></tr>';
    setStatus(message, true);
  }

  async function refresh({ cachedItems = [], manual = false } = {}) {
    const button = document.querySelector("[data-market-flow-refresh]");
    if (button) {
      button.disabled = true;
      button.textContent = "Refreshing…";
    }
    if (!cachedItems.length) setStatus("Loading verified ETF capital-flow data…");

    try {
      const rows = await api.publicFund.getAllRealTime({ platform: "eastmoney", symbol: "ETF" });
      const items = Array.isArray(rows)
        ? rows.map(normalizeEtf).filter((item) => item.code && item.mainFlow !== null)
        : [];
      if (!items.length) throw new Error("ETF real-time feed returned no capital-flow rows");
      render(items, manual ? "Manually refreshed" : "Live ETF flow");
      writeCache(items);
    } catch (error) {
      if (cachedItems.length) {
        render(cachedItems, "Cached fallback");
        setStatus(`Cached fallback · refresh failed: ${error.message}`, true);
      } else {
        renderUnavailable(`ETF capital-flow data unavailable: ${error.message}`);
      }
    } finally {
      if (button) {
        button.disabled = false;
        button.textContent = "Refresh";
      }
    }
  }

  function init() {
    const cached = readCache();
    const cachedItems = cached?.items || [];
    if (cachedItems.length) render(cachedItems, cacheIsFresh(cached) ? "Cached" : "Stale cache");

    const refreshButton = document.querySelector("[data-market-flow-refresh]");
    if (refreshButton) {
      refreshButton.addEventListener("click", () => {
        void refresh({ cachedItems: readCache()?.items || cachedItems, manual: true });
      });
    }

    if (!cacheIsFresh(cached)) {
      void refresh({ cachedItems });
    }
  }

  init();
})(window, document);
