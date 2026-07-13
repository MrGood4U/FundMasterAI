(function (window, document) {
  "use strict";

  const FALLBACK_FUNDS = [
    { code: "510300", name: "CSI 300 ETF", type: "ETF" },
    { code: "159915", name: "ChiNext ETF", type: "ETF" },
    { code: "512000", name: "Brokerage ETF", type: "ETF" },
    { code: "512480", name: "Semiconductor ETF", type: "ETF" },
    { code: "588000", name: "STAR 50 ETF", type: "ETF" },
    { code: "THTE", name: "Tianyuan Huiteng Tech ETF", type: "Fund" },
    { code: "GSI", name: "Global Semiconductor Index", type: "Index" },
    { code: "CESF", name: "Clean Energy Strategic Fund", type: "Fund" },
    { code: "MTGF.QX", name: "MasterTech Growth Fund", type: "Fund" },
  ];

  const api = window.FundMasterAPI;
  let remoteFunds = null;

  function normalize(value) {
    return String(value || "").trim().toLowerCase();
  }

  function pick(record, keys, fallback = "") {
    for (const key of keys) {
      if (record && record[key] !== undefined && record[key] !== null && record[key] !== "") {
        return String(record[key]);
      }
    }
    return fallback;
  }

  function normalizeFund(record) {
    return {
      code: pick(record, ["基金代码", "fund_code", "code", "symbol"]),
      name: pick(record, ["基金简称", "基金名称", "name", "fund_name", "short_name"]),
      type: pick(record, ["类型", "type"], "Fund"),
    };
  }

  async function getFundUniverse() {
    if (remoteFunds) return remoteFunds;
    if (api && api.market && api.market.getFundNameList) {
      try {
        const rows = await api.market.getFundNameList();
        if (Array.isArray(rows) && rows.length) {
          remoteFunds = rows.map(normalizeFund).filter((item) => item.code || item.name);
          return remoteFunds;
        }
      } catch (error) {
        // Keep fallback functional
      }
    }
    remoteFunds = FALLBACK_FUNDS;
    return remoteFunds;
  }

  function buildResultUrl(item) {
    const params = new URLSearchParams();
    if (item.code) params.set("code", item.code);
    if (item.name) params.set("name", item.name);
    if (item.type) params.set("type", item.type);
    return `fund-deep-dive.html?${params.toString()}`;
  }

  // 💡 新增：兜底的直接强行跳转函数
  function forceRedirect(query) {
    if (!query) return;
    window.location.href = `fund-deep-dive.html?code=${encodeURIComponent(query)}&name=${encodeURIComponent(query)}`;
  }

  function renderResults(container, items, query) {
    if (!query) {
      container.hidden = true;
      container.innerHTML = "";
      return;
    }
    if (!items.length) {
      container.hidden = false;
      container.innerHTML = `<div class="search-results__empty">No fund matched "${escapeHtml(query)}"</div>`;
      return;
    }
    container.hidden = false;
    container.innerHTML = items
      .slice(0, 8)
      .map(
        (item) => `
          <a class="search-result" href="${buildResultUrl(item)}">
            <span class="search-result__code">${escapeHtml(item.code || "FUND")}</span>
            <span class="search-result__main">
              <strong>${escapeHtml(item.name || item.code)}</strong>
              <small>${escapeHtml(item.type || "Fund")} · Open in Analytics</small>
            </span>
          </a>
        `
      )
      .join("");
  }

  function escapeHtml(value) {
    return String(value).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function attachSearch(input) {
    const field = input.closest(".search-field") || input.parentElement;
    if (!field || field.dataset.searchReady === "true") return;
    field.dataset.searchReady = "true";
    field.classList.add("search-field--active");

    // 创建下拉框
    const results = document.createElement("div");
    results.className = "search-results";
    results.hidden = true;
    field.appendChild(results);

    let activeQuery = "";

    input.addEventListener("input", async () => {
      const query = input.value.trim();
      activeQuery = query;
      if (!query) {
        renderResults(results, [], "");
        return;
      }

      const universe = await getFundUniverse();
      if (activeQuery !== query) return;

      const q = normalize(query);
      const matches = universe.filter((item) => {
        return normalize(item.code).includes(q) || normalize(item.name).includes(q);
      });
      renderResults(results, matches, query);
    });

    function openSearchResult() {
      const firstResult = results.querySelector(".search-result");
      if (firstResult && !results.hidden) {
        window.location.href = firstResult.getAttribute("href");
      } else {
        forceRedirect(input.value.trim());
      }
    }

    // 💡 升级：监听键盘回车
    input.addEventListener("keydown", (event) => {
      if (event.key !== "Enter") return;
      event.preventDefault();
      openSearchResult();
    });

    // 💡 升级：监听旁边的放大镜图标/按钮点击
    const searchIcon = field.querySelector(".search-field__icon-img, .search-icon, svg, i");
    if (searchIcon) {
      searchIcon.style.cursor = "pointer";
      searchIcon.setAttribute("role", "button");
      searchIcon.setAttribute("tabindex", "0");
      searchIcon.setAttribute("aria-label", "Search funds");
      searchIcon.addEventListener("click", openSearchResult);
      searchIcon.addEventListener("keydown", (event) => {
        if (event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault();
        openSearchResult();
      });
    }

    document.addEventListener("click", (event) => {
      if (!field.contains(event.target)) {
        results.hidden = true;
      }
    });

    input.addEventListener("focus", () => {
      if (input.value.trim() && results.innerHTML) {
        results.hidden = false;
      }
    });
  }

  function hydrateAnalyticsPage() {
    if (!document.body || !/fund-deep-dive\.html$/.test(window.location.pathname)) return;
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const name = params.get("name");
    if (!code && !name) return;

    const title = document.querySelector(".page-head__title");
    const ticker = document.querySelector(".kpi-row .kpi-card:first-child .kpi-card__value") || document.querySelector(".ticker-value");
    const breadcrumbCurrent = document.querySelector(".breadcrumb span:last-child");

    if (title && name) title.textContent = name;
    if (ticker && code) ticker.textContent = code;
    if (breadcrumbCurrent && name) breadcrumbCurrent.textContent = name;
  }

  // 💡 全局初始化（多重选择器支持）
  function init() {
    // 兼容可能存在的不同 class
    const inputs = document.querySelectorAll(".search-field__input, .search-box input, header input[type='text']");
    inputs.forEach(attachSearch);
    hydrateAnalyticsPage();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window, document);
