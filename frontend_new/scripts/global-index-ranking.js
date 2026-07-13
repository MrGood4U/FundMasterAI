(function (window, document) {
  "use strict";

  const PAGE_SIZE = 5;
  const MATRIX_SIZE = 36;
  const CACHE_KEY = "fundmaster:global-investment:v1";
  const CACHE_VERSION = 1;
  const CACHE_STALE_AFTER_MS = 6 * 60 * 60 * 1000;
  const api = window.FundMasterAPI;
  const state = {
    funds: [],
    matrixPeriod: "DAY",
    fundSource: { mode: "loading", updatedAt: null, note: "" },
  };

  function readCache() {
    try {
      const raw = window.localStorage.getItem(CACHE_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      return parsed && parsed.version === CACHE_VERSION ? parsed : null;
    } catch (error) {
      console.warn("Global dashboard cache is unavailable:", error.message);
      return null;
    }
  }

  function writeCache(patch) {
    try {
      const current = readCache() || { version: CACHE_VERSION };
      window.localStorage.setItem(CACHE_KEY, JSON.stringify({ ...current, ...patch, version: CACHE_VERSION }));
    } catch (error) {
      console.warn("Global dashboard cache could not be updated:", error.message);
    }
  }

  function cacheMode(updatedAt) {
    const timestamp = Number(updatedAt);
    if (!Number.isFinite(timestamp)) return "stale";
    return Date.now() - timestamp > CACHE_STALE_AFTER_MS ? "stale" : "cached";
  }

  function formatTimestamp(updatedAt) {
    const timestamp = Number(updatedAt);
    if (!Number.isFinite(timestamp)) return "unknown time";
    return new Intl.DateTimeFormat("en-GB", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    }).format(new Date(timestamp));
  }

  function sourceLabel(meta) {
    const mode = meta?.mode || "loading";
    if (mode === "loading") return "Loading verified data";
    if (mode === "unavailable") return "Unavailable";
    const verb = mode === "stale" ? "Last updated" : "Updated";
    const label = mode === "live" ? "Live" : mode === "cached" ? "Cached" : "Stale";
    return `${label} · ${verb} ${formatTimestamp(meta.updatedAt)}`;
  }

  function setSourceStatus(node, meta, detail = "") {
    if (!node) return;
    node.dataset.state = meta?.mode || "loading";
    node.textContent = [sourceLabel(meta), detail, meta?.note].filter(Boolean).join(" · ");
  }

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

  function renderQuoteCards(market) {
    const quotes = Array.isArray(market?.indices?.items) ? market.indices.items : [];
    const byTicker = new Map(
      quotes.map((quote) => [String(pick(quote, ["ticker", "symbol"], "")).toUpperCase(), quote])
    );

    setIndexCard("idx-nasdaq-val", "idx-nasdaq-change", byTicker.get("^IXIC"));
    setIndexCard("idx-dax-val", "idx-dax-change", byTicker.get("^GDAXI"));
    setIndexCard("idx-hk-val", "idx-hk-change", byTicker.get("^HSI"));

    const fxValue = document.getElementById("idx-usdcny-val");
    const fxHint = document.getElementById("idx-usdcny-change");
    const rate = numberValue(market?.fx?.rate);
    if (fxValue) fxValue.textContent = rate === null ? "—" : formatNumber(rate, 4);
    if (fxHint) {
      fxHint.textContent = rate === null ? "Live feed unavailable" : "USD/CNY reference rate";
      fxHint.className = "kpi-card__hint";
    }
  }

  function marketCacheTimestamp(market) {
    return Math.min(
      Number(market?.indices?.updatedAt) || Number.POSITIVE_INFINITY,
      Number(market?.fx?.updatedAt) || Number.POSITIVE_INFINITY
    );
  }

  function renderCachedQuoteCards(market) {
    if (!market?.indices && !market?.fx) return false;
    renderQuoteCards(market);
    const updatedAt = marketCacheTimestamp(market);
    const safeTimestamp = Number.isFinite(updatedAt)
      ? updatedAt
      : Number(market?.indices?.updatedAt || market?.fx?.updatedAt);
    setSourceStatus(document.getElementById("global-quote-source"), {
      mode: cacheMode(safeTimestamp),
      updatedAt: safeTimestamp,
      note: "refreshing in background",
    }, "last successful market data");
    return true;
  }

  function renderQuoteUnavailable(message = "Verified market sources did not return data") {
    renderQuoteCards({});
    setSourceStatus(document.getElementById("global-quote-source"), {
      mode: "unavailable",
      updatedAt: null,
      note: message,
    });
  }

  async function refreshQuoteCards(cachedMarket = null) {
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
    const rate = fxResult.status === "fulfilled"
      ? numberValue(pick(fxResult.value, ["rate"]))
      : null;

    const now = Date.now();
    const liveSourceCount = (quotes.length ? 1 : 0) + (rate !== null ? 1 : 0);
    if (!liveSourceCount) {
      if (cachedMarket) {
        renderQuoteCards(cachedMarket);
        const fallbackTimestamp = marketCacheTimestamp(cachedMarket);
        setSourceStatus(document.getElementById("global-quote-source"), {
          mode: "stale",
          updatedAt: Number.isFinite(fallbackTimestamp) ? fallbackTimestamp : null,
          note: "background refresh failed",
        }, "last successful market data retained");
      } else {
        renderQuoteUnavailable("background refresh failed");
      }
      return;
    }

    const market = {
      indices: quotes.length ? { items: quotes, updatedAt: now } : cachedMarket?.indices || null,
      fx: rate !== null ? { rate, updatedAt: now } : cachedMarket?.fx || null,
    };
    const retainedFallback = (!quotes.length && Boolean(cachedMarket?.indices))
      || (rate === null && Boolean(cachedMarket?.fx));
    renderQuoteCards(market);
    setSourceStatus(document.getElementById("global-quote-source"), {
      mode: "live",
      updatedAt: now,
      note: liveSourceCount === 2
        ? "2/2 sources refreshed"
        : retainedFallback
          ? "1/2 sources refreshed; cached fallback retained"
          : "1/2 sources refreshed; other source unavailable",
    });
    writeCache({ market });
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
      setSourceStatus(source, state.fundSource, `Public QDII ${label} unavailable`);
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
    setSourceStatus(source, state.fundSource, `${selected.length} of ${valid.length} public QDII funds · ${label}`);
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

    list.onclick = (event) => {
      const button = event.target.closest("[data-global-ranking-index]");
      if (button) select(Number(button.dataset.globalRankingIndex));
    };

    pager.onclick = (event) => {
      const totalPages = Math.ceil(state.funds.length / PAGE_SIZE);
      if (event.target.closest("[data-global-page-prev]") && page > 0) page -= 1;
      else if (event.target.closest("[data-global-page-next]") && page < totalPages - 1) page += 1;
      else return;
      activeIndex = page * PAGE_SIZE;
      renderPage();
      select(activeIndex);
    };

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
    setSourceStatus(source, { mode: "unavailable", updatedAt: null, note: safeMessage }, "Public QDII return feed");
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

  function renderFundViews() {
    renderMatrix(state.matrixPeriod);
    const section = document.querySelector("[data-global-index-ranking]");
    if (section) renderRanking(section);
  }

  function renderCachedFunds(cache) {
    const items = cache?.funds?.items;
    if (!Array.isArray(items) || !items.length || items.length > 5000) return false;
    state.funds = items.filter((item) => item && item.code && item.name);
    if (!state.funds.length) return false;
    state.fundSource = {
      mode: cacheMode(cache.funds.updatedAt),
      updatedAt: cache.funds.updatedAt,
      note: "refreshing in background",
    };
    renderFundViews();
    return true;
  }

  async function refreshFunds(hasCachedFunds) {
    try {
      state.funds = await loadFunds();
      const updatedAt = Date.now();
      state.fundSource = { mode: "live", updatedAt, note: "QDII feed refreshed" };
      renderFundViews();
      writeCache({ funds: { items: state.funds, updatedAt } });
    } catch (error) {
      console.error("Global investment data failed to load:", error);
      if (hasCachedFunds && state.funds.length) {
        state.fundSource = {
          mode: "stale",
          updatedAt: state.fundSource.updatedAt,
          note: "background refresh failed; cached data retained",
        };
        renderMatrix(state.matrixPeriod);
      } else {
        renderDataError(error.message);
      }
    }
  }

  function init() {
    bindMatrixControls();
    const cache = readCache();
    const hasCachedFunds = renderCachedFunds(cache);
    const hasCachedMarket = renderCachedQuoteCards(cache?.market);

    if (!hasCachedFunds) {
      setSourceStatus(document.getElementById("global-matrix-source"), {
        mode: "loading",
        updatedAt: null,
        note: "waiting for the first verified QDII response",
      });
    }
    if (!hasCachedMarket) {
      setSourceStatus(document.getElementById("global-quote-source"), {
        mode: "loading",
        updatedAt: null,
        note: "waiting for the first verified market response",
      });
    }

    // Stale-while-revalidate: cached data paints immediately while both live
    // sources refresh concurrently in the background.
    void Promise.allSettled([
      refreshFunds(hasCachedFunds),
      refreshQuoteCards(hasCachedMarket ? cache.market : null),
    ]);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    void init();
  }
})(window, document);
