(function (window, document) {
  "use strict";

  const PAGE_SIZE = 5;
  const MATRIX_SIZE = 36;
  const api = window.FundMasterAPI;
  const state = {
    funds: [],
    matrixPeriod: "DAY",
  };

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function pick(record, keys, fallback = null) {
    for (const key of keys) {
      if (record && record[key] !== undefined && record[key] !== null && record[key] !== "") {
        return record[key];
      }
    }
    return fallback;
  }

  function numberValue(value) {
    if (value === null || value === undefined || value === "") return null;
    const parsed = Number(String(value).replace(/[%+,$,]/g, "").trim());
    return Number.isFinite(parsed) ? parsed : null;
  }

  function formatPercent(value, digits = 2) {
    const number = numberValue(value);
    if (number === null) return "—";
    const sign = number > 0 ? "+" : "";
    return `${sign}${number.toFixed(digits)}%`;
  }

  function formatNumber(value, digits = 2) {
    const number = numberValue(value);
    if (number === null) return "—";
    return new Intl.NumberFormat("en-US", {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    }).format(number);
  }

  function formatDate(value) {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return new Intl.DateTimeFormat("en-CA", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(date);
  }

  function setIndexCard(valueId, changeId, quote) {
    const valueNode = document.getElementById(valueId);
    const changeNode = document.getElementById(changeId);
    if (!valueNode || !changeNode) return;

    const price = numberValue(quote && pick(quote, ["price", "latest_price", "last_price"]));
    const change = numberValue(quote && pick(quote, ["change_pct", "change_percent", "daily_return"]));
    valueNode.textContent = price === null ? "—" : formatNumber(price, price >= 100 ? 2 : 4);
    changeNode.textContent = change === null ? "Live feed unavailable" : formatPercent(change);
    changeNode.className = change !== null && change < 0
      ? "kpi-card__hint kpi-card__hint--neg"
      : "kpi-card__hint";
  }

  async function loadQuoteCards() {
    const quotePromise = api?.market?.getGlobalIndices
      ? api.market.getGlobalIndices()
      : Promise.resolve([]);
    const fxPromise = api?.global?.getExchangeRate
      ? api.global.getExchangeRate("USD", "CNY")
      : Promise.resolve(null);

    const [quotesResult, fxResult] = await Promise.allSettled([quotePromise, fxPromise]);
    const quotes = quotesResult.status === "fulfilled" && Array.isArray(quotesResult.value)
      ? quotesResult.value
      : [];
    const byTicker = new Map(
      quotes.map((quote) => [String(pick(quote, ["ticker", "symbol"], "")).toUpperCase(), quote])
    );

    setIndexCard("idx-nasdaq-val", "idx-nasdaq-change", byTicker.get("^IXIC"));
    setIndexCard("idx-dax-val", "idx-dax-change", byTicker.get("^GDAXI"));
    setIndexCard("idx-hk-val", "idx-hk-change", byTicker.get("^HSI"));

    const fxValue = document.getElementById("idx-usdcny-val");
    const fxHint = document.getElementById("idx-usdcny-change");
    const rate = fxResult.status === "fulfilled"
      ? numberValue(pick(fxResult.value, ["rate"]))
      : null;
    if (fxValue) fxValue.textContent = rate === null ? "—" : formatNumber(rate, 4);
    if (fxHint) {
      fxHint.textContent = rate === null ? "Live feed unavailable" : "Live reference rate";
      fxHint.className = "kpi-card__hint";
    }
  }

  function normalizeFund(record, index) {
    return {
      code: String(pick(record, ["fund_code", "code", "基金代码"], `QDII-${index + 1}`)),
      name: String(pick(record, ["fund_short_name", "fund_name", "基金简称", "基金名称", "name"], "Unnamed fund")),
      nav: numberValue(pick(record, ["unit_net_value", "nav", "单位净值"])),
      daily: numberValue(pick(record, ["daily_growth_rate", "daily_return", "日增长率"])),
      month: numberValue(pick(record, ["change_1m", "近1月", "近一月"])),
      oneYear: numberValue(pick(record, ["change_1y", "近1年", "近一年", "return1y"])),
      ytd: numberValue(pick(record, ["change_ytd", "今年来", "returnYtd"])),
      sinceInception: numberValue(pick(record, ["change_since_inception", "成立来"])),
      date: pick(record, ["date", "日期"], null),
    };
  }

  async function loadFunds() {
    if (!api?.market?.getFundRank) {
      throw new Error("Fund ranking API is unavailable.");
    }

    const rows = await api.market.getFundRank("qdii", "change_1y");
    if (!Array.isArray(rows) || rows.length === 0) {
      throw new Error("The QDII ranking feed returned no data.");
    }
    if (rows.length > 5000) {
      throw new Error("The backend returned the full fund universe instead of QDII funds.");
    }

    return rows
      .map(normalizeFund)
      .filter((item) => item.code && item.name)
      .sort((a, b) => (b.oneYear ?? Number.NEGATIVE_INFINITY) - (a.oneYear ?? Number.NEGATIVE_INFINITY));
  }

  function renderMatrix(period = state.matrixPeriod) {
    const container = document.getElementById("matrix-container");
    const source = document.getElementById("global-matrix-source");
    if (!container) return;

    state.matrixPeriod = period;
    const metric = period === "MONTH" ? "month" : "daily";
    const label = period === "MONTH" ? "one-month return" : "daily return";
    const valid = state.funds
      .filter((item) => numberValue(item[metric]) !== null)
      .sort((a, b) => b[metric] - a[metric]);

    if (!valid.length) {
      container.innerHTML = '<div class="gi-data-state">No verified QDII return data is currently available.</div>';
      if (source) source.textContent = `Public QDII ${label} · unavailable`;
      return;
    }

    const half = Math.ceil(MATRIX_SIZE / 2);
    const selected = [...valid.slice(0, half), ...valid.slice(-half)]
      .filter((item, index, rows) => rows.findIndex((candidate) => candidate.code === item.code) === index)
      .slice(0, MATRIX_SIZE);
    const maxAbs = Math.max(...selected.map((item) => Math.abs(item[metric])), 0.01);

    container.innerHTML = selected
      .map((item) => {
        const value = item[metric];
        const tone = value > 0 ? "positive" : value < 0 ? "negative" : "neutral";
        const strength = (0.22 + Math.min(Math.abs(value) / maxAbs, 1) * 0.68).toFixed(2);
        return `
          <div class="gi-matrix-cell gi-matrix-cell--${tone}" style="--cell-strength:${strength}" title="${escapeHtml(item.name)} · ${formatPercent(value)}">
            <span>${escapeHtml(item.code)}</span>
            <strong>${formatPercent(value)}</strong>
          </div>`;
      })
      .join("");
    container.setAttribute("aria-label", `${selected.length} QDII funds by ${label}`);
    if (source) source.textContent = `${selected.length} of ${valid.length} public QDII funds · ${label}`;
  }

  function renderRanking(section) {
    const list = section.querySelector("[data-global-ranking-list]");
    const detail = section.querySelector("[data-global-ranking-detail]");
    if (!list || !detail) return;

    let page = 0;
    let activeIndex = 0;
    const oldPager = section.querySelector(".ranking-pager");
    if (oldPager) oldPager.remove();
    const pager = document.createElement("div");
    pager.className = "ranking-pager";
    section.appendChild(pager);

    function renderDetail(item) {
      if (!item) return;
      detail.innerHTML = `
        <div class="ranking-detail__head">
          <div>
            <p class="ranking-detail__eyebrow">${escapeHtml(item.code)}</p>
            <h3>${escapeHtml(item.name)}</h3>
          </div>
          <span class="ranking-detail__return${item.oneYear !== null && item.oneYear < 0 ? " neg" : ""}">${formatPercent(item.oneYear)}</span>
        </div>
        <div class="ranking-detail__grid">
          <div><span>1M Return</span><strong>${formatPercent(item.month)}</strong></div>
          <div><span>YTD Return</span><strong>${formatPercent(item.ytd)}</strong></div>
          <div><span>Unit NAV</span><strong>${item.nav === null ? "—" : formatNumber(item.nav, 4)}</strong></div>
          <div><span>Data Date</span><strong>${formatDate(item.date)}</strong></div>
        </div>
        <div class="ranking-detail__copy">
          <p><strong>Coverage:</strong> Public QDII ranking feed. Unavailable source fields are shown as —.</p>
        </div>`;
    }

    function select(index) {
      const item = state.funds[index];
      if (!item) return;
      activeIndex = index;
      list.querySelectorAll(".ranking-row").forEach((row) => {
        row.classList.toggle("ranking-row--active", Number(row.dataset.globalRankingIndex) === activeIndex);
      });
      renderDetail(item);
    }

    function renderPage() {
      const totalPages = Math.max(1, Math.ceil(state.funds.length / PAGE_SIZE));
      const start = page * PAGE_SIZE;
      const visibleRows = state.funds.slice(start, start + PAGE_SIZE);
      list.innerHTML = visibleRows
        .map((item, offset) => {
          const index = start + offset;
          const negativeClass = item.oneYear !== null && item.oneYear < 0 ? " neg" : "";
          return `
            <button type="button" class="ranking-row${index === activeIndex ? " ranking-row--active" : ""}" data-global-ranking-index="${index}">
              <span class="ranking-row__rank">${index + 1}</span>
              <span class="ranking-row__fund">
                <strong>${escapeHtml(item.name)}</strong>
                <small>${escapeHtml(item.code)} · QDII</small>
              </span>
              <span class="ranking-row__return${negativeClass}">${formatPercent(item.oneYear)}</span>
            </button>`;
        })
        .join("");

      pager.innerHTML = `
        <button type="button" class="ranking-pager__btn" data-global-page-prev ${page === 0 ? "disabled" : ""}>Prev</button>
        <span class="ranking-pager__meta">Page ${page + 1} / ${totalPages} · ${state.funds.length} QDII funds</span>
        <button type="button" class="ranking-pager__btn" data-global-page-next ${page >= totalPages - 1 ? "disabled" : ""}>Next</button>`;
    }

    list.addEventListener("click", (event) => {
      const button = event.target.closest("[data-global-ranking-index]");
      if (button) select(Number(button.dataset.globalRankingIndex));
    });

    pager.addEventListener("click", (event) => {
      const totalPages = Math.ceil(state.funds.length / PAGE_SIZE);
      if (event.target.closest("[data-global-page-prev]") && page > 0) page -= 1;
      else if (event.target.closest("[data-global-page-next]") && page < totalPages - 1) page += 1;
      else return;
      activeIndex = page * PAGE_SIZE;
      renderPage();
      select(activeIndex);
    });

    renderPage();
    select(0);
  }

  function renderDataError(message) {
    const matrix = document.getElementById("matrix-container");
    const source = document.getElementById("global-matrix-source");
    const section = document.querySelector("[data-global-index-ranking]");
    const list = section && section.querySelector("[data-global-ranking-list]");
    const detail = section && section.querySelector("[data-global-ranking-detail]");
    const safeMessage = escapeHtml(message || "Global fund data is unavailable.");
    if (matrix) matrix.innerHTML = `<div class="gi-data-state">${safeMessage}</div>`;
    if (source) source.textContent = "Public QDII return feed unavailable";
    if (list) list.innerHTML = `<div class="gi-data-state">${safeMessage}</div>`;
    if (detail) detail.innerHTML = '<div class="gi-data-state">No placeholder ranking has been substituted.</div>';
  }

  function bindMatrixControls() {
    const day = document.getElementById("pill-matrix-day");
    const month = document.getElementById("pill-matrix-month");
    if (!day || !month) return;
    day.addEventListener("click", () => {
      day.classList.add("pill--active");
      month.classList.remove("pill--active");
      renderMatrix("DAY");
    });
    month.addEventListener("click", () => {
      month.classList.add("pill--active");
      day.classList.remove("pill--active");
      renderMatrix("MONTH");
    });
  }

  async function init() {
    bindMatrixControls();

    try {
      state.funds = await loadFunds();
      renderMatrix("DAY");
      const section = document.querySelector("[data-global-index-ranking]");
      if (section) renderRanking(section);
    } catch (error) {
      console.error("Global investment data failed to load:", error);
      renderDataError(error.message);
    }

    // The market service may process upstream calls serially. Load the primary
    // QDII visualization first so a slow global-index quote cannot block the
    // matrix and ranking for 10–20 seconds.
    void loadQuoteCards();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    void init();
  }
})(window, document);
