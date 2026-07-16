(function (window, document) {
  "use strict";

  const api = window.FundMasterAPI;
  const FUND_DIRECTORY_CACHE_KEY = "fundmaster:fund-directory:v1";
  const FUND_DIRECTORY_CACHE_TTL_MS = 24 * 60 * 60 * 1000;
  let remoteFunds = null;
  let remoteFundsPromise = null;

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
      type: pick(record, ["类型", "fund_type", "type"], "Fund"),
      pinyinAbbr: pick(record, ["拼音缩写", "pinyin_abbr"]),
      pinyinFull: pick(record, ["拼音全称", "pinyin_full"]),
    };
  }

  function readFundDirectoryCache() {
    try {
      const raw = window.localStorage.getItem(FUND_DIRECTORY_CACHE_KEY);
      if (!raw) return null;
      const cached = JSON.parse(raw);
      if (!cached || !Array.isArray(cached.rows)) return null;
      const funds = cached.rows
        .map((row) => ({
          code: String(row?.[0] || ""),
          name: String(row?.[1] || ""),
          type: String(row?.[2] || "Fund"),
          pinyinAbbr: String(row?.[3] || ""),
          pinyinFull: "",
        }))
        .filter((item) => item.code && item.name);
      if (!funds.length) return null;
      const savedAt = Number(cached.savedAt);
      const age = Date.now() - savedAt;
      return {
        funds,
        fresh: Number.isFinite(savedAt) && age >= 0 && age < FUND_DIRECTORY_CACHE_TTL_MS,
      };
    } catch (error) {
      try {
        window.localStorage.removeItem(FUND_DIRECTORY_CACHE_KEY);
      } catch (removeError) {
        // Ignore unavailable browser storage and continue with the network.
      }
      return null;
    }
  }

  function writeFundDirectoryCache(funds) {
    try {
      const rows = funds.map((item) => [
        item.code,
        item.name,
        item.type,
        item.pinyinAbbr,
      ]);
      window.localStorage.setItem(FUND_DIRECTORY_CACHE_KEY, JSON.stringify({
        savedAt: Date.now(),
        rows,
      }));
    } catch (error) {
      // Private mode or a full quota should not make fund search unusable.
    }
  }

  function refreshFundUniverse() {
    if (remoteFundsPromise) return remoteFundsPromise;
    if (!api?.market?.getFundNameList) {
      return Promise.reject(new Error("Fund search API is unavailable"));
    }
    remoteFundsPromise = api.market.getFundNameList()
      .then((rows) => {
        if (!Array.isArray(rows) || !rows.length) {
          throw new Error("Fund directory returned no records");
        }
        const funds = rows.map(normalizeFund).filter((item) => item.code && item.name);
        if (!funds.length) {
          throw new Error("Fund directory contained no usable records");
        }
        remoteFunds = funds;
        writeFundDirectoryCache(funds);
        return funds;
      })
      .finally(() => {
        remoteFundsPromise = null;
      });
    return remoteFundsPromise;
  }

  async function getFundUniverse() {
    if (Array.isArray(remoteFunds)) return remoteFunds;
    const cached = readFundDirectoryCache();
    if (cached) {
      remoteFunds = cached.funds;
      if (!cached.fresh) {
        refreshFundUniverse().catch((error) => {
          console.error("Fund directory background refresh failed; using cached data:", error);
        });
      }
      return remoteFunds;
    }
    return refreshFundUniverse();
  }

  function fundSearchRank(item, query) {
    const code = normalize(item.code);
    const name = normalize(item.name);
    const pinyinAbbr = normalize(item.pinyinAbbr);
    const pinyinFull = normalize(item.pinyinFull);
    if (code.startsWith(query)) return 0;
    if (name.startsWith(query)) return 1;
    if (pinyinAbbr.startsWith(query) || pinyinFull.startsWith(query)) return 2;
    if ([code, name, pinyinAbbr, pinyinFull].some((value) => value.includes(query))) return 3;
    return Number.POSITIVE_INFINITY;
  }

  function findFundMatches(universe, query) {
    return universe
      .map((item, index) => ({ item, index, rank: fundSearchRank(item, query) }))
      .filter((entry) => Number.isFinite(entry.rank))
      .sort((left, right) => left.rank - right.rank || left.index - right.index)
      .map((entry) => entry.item);
  }

  function buildResultUrl(item) {
    const params = new URLSearchParams();
    if (item.code) params.set("code", item.code);
    if (item.name) params.set("name", item.name);
    if (item.type) params.set("type", item.type);
    return `fund-deep-dive.html?${params.toString()}`;
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

  function renderMessage(container, message) {
    container.hidden = false;
    container.innerHTML = `<div class="search-results__empty">${escapeHtml(message)}</div>`;
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
    let searchTimer = null;

    input.addEventListener("input", () => {
      const query = input.value.trim();
      activeQuery = query;
      window.clearTimeout(searchTimer);
      if (!query) {
        renderResults(results, [], "");
        return;
      }
      if (!Array.isArray(remoteFunds)) {
        renderMessage(results, "Loading fund directory…");
      }
      searchTimer = window.setTimeout(async () => {
        try {
          const universe = await getFundUniverse();
          if (activeQuery !== query) return;
          const matches = findFundMatches(universe, normalize(query));
          renderResults(results, matches, query);
        } catch (error) {
          if (activeQuery !== query) return;
          console.error("Fund search unavailable:", error);
          renderMessage(results, "Fund search is temporarily unavailable. Please try again later.");
        }
      }, 250);
    });

    function openSearchResult() {
      const firstResult = results.querySelector(".search-result");
      if (firstResult && !results.hidden) {
        window.location.href = firstResult.getAttribute("href");
      } else if (input.value.trim()) {
        renderMessage(results, "Select a real fund from the search results.");
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
