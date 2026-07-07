(function (window, document) {
  "use strict";

  const PAGE_SIZE = 5;
  const api = window.FundMasterAPI;

  const FALLBACK_FUNDS = [
    {
      code: "VT",
      name: "Vanguard Total World Stock ETF",
      region: "Global",
      return1y: "+21.8%",
      returnYtd: "+12.6%",
      aum: "$42.3B",
      benchmark: "FTSE Global All Cap",
      strategy: "Global broad equity beta with diversified country exposure.",
    },
    {
      code: "ACWI",
      name: "iShares MSCI ACWI ETF",
      region: "Global",
      return1y: "+20.9%",
      returnYtd: "+12.1%",
      aum: "$19.7B",
      benchmark: "MSCI ACWI",
      strategy: "Core global allocation across developed and emerging markets.",
    },
    {
      code: "VEA",
      name: "Vanguard FTSE Developed Markets ETF",
      region: "Developed Markets",
      return1y: "+18.4%",
      returnYtd: "+10.8%",
      aum: "$132.6B",
      benchmark: "FTSE Developed ex US",
      strategy: "Developed-market exposure with low-cost index tracking.",
    },
    {
      code: "IEFA",
      name: "iShares Core MSCI EAFE ETF",
      region: "EAFE",
      return1y: "+17.6%",
      returnYtd: "+10.1%",
      aum: "$121.4B",
      benchmark: "MSCI EAFE IMI",
      strategy: "Europe, Australasia and Far East index exposure.",
    },
    {
      code: "VWO",
      name: "Vanguard FTSE Emerging Markets ETF",
      region: "Emerging Markets",
      return1y: "+16.2%",
      returnYtd: "+9.5%",
      aum: "$74.8B",
      benchmark: "FTSE Emerging Markets",
      strategy: "Emerging-market equity allocation with broad country coverage.",
    },
    {
      code: "EEM",
      name: "iShares MSCI Emerging Markets ETF",
      region: "Emerging Markets",
      return1y: "+15.7%",
      returnYtd: "+9.0%",
      aum: "$18.1B",
      benchmark: "MSCI Emerging Markets",
      strategy: "Liquid emerging-market proxy for tactical global rotation.",
    },
    {
      code: "EWJ",
      name: "iShares MSCI Japan ETF",
      region: "Japan",
      return1y: "+14.3%",
      returnYtd: "+8.4%",
      aum: "$14.9B",
      benchmark: "MSCI Japan",
      strategy: "Japan equity exposure with export and governance reform themes.",
    },
    {
      code: "EZU",
      name: "iShares MSCI Eurozone ETF",
      region: "Eurozone",
      return1y: "+12.9%",
      returnYtd: "+7.3%",
      aum: "$7.9B",
      benchmark: "MSCI EMU",
      strategy: "Eurozone equity allocation focused on large and mid caps.",
    },
  ];

  function numberValue(value) {
    const parsed = Number(String(value ?? "").replace(/[%+,$]/g, ""));
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function formatPercent(value) {
    const n = numberValue(value);
    const sign = n > 0 ? "+" : "";
    return `${sign}${n.toFixed(1)}%`;
  }

  function pick(record, keys, fallback = "") {
    for (const key of keys) {
      if (record && record[key] !== undefined && record[key] !== null && record[key] !== "") {
        return record[key];
      }
    }
    return fallback;
  }

  function normalizeBackendRecord(record, index) {
    const code = String(pick(record, ["基金代码", "fund_code", "code", "symbol"], `GLOBAL-${index + 1}`));
    const name = String(pick(record, ["基金简称", "基金名称", "name", "fund_name", "short_name"], code));
    return {
      code,
      name,
      region: String(pick(record, ["region", "区域", "投资区域"], "Global")),
      return1y: formatPercent(pick(record, ["近1年", "近一年", "1年", "return1y", "year_return", "收益率"], 0)),
      returnYtd: formatPercent(pick(record, ["今年来", "近今年", "returnYtd", "ytd_return"], 0)),
      aum: String(pick(record, ["aum", "规模", "基金规模"], "Backend data")),
      benchmark: String(pick(record, ["benchmark", "跟踪指数", "标的指数"], "Global index")),
      strategy: String(pick(record, ["strategy", "投资类型", "focus"], "Backend-provided global index fund profile.")),
    };
  }

  async function loadFunds() {
    if (!api?.market?.getFundRank) return FALLBACK_FUNDS;
    try {
      const rows = await api.market.getFundRank("QDII");
      if (Array.isArray(rows) && rows.length > PAGE_SIZE) {
        return rows.map(normalizeBackendRecord);
      }
    } catch (error) {
      // Keep the page usable while backend integration is in progress.
    }
    return FALLBACK_FUNDS;
  }

  function sortByReturn(rows) {
    return [...rows].sort((a, b) => numberValue(b.return1y) - numberValue(a.return1y));
  }

  function renderDetail(root, item) {
    root.innerHTML = `
      <div class="ranking-detail__head">
        <div>
          <p class="ranking-detail__eyebrow">${item.code}</p>
          <h3>${item.name}</h3>
        </div>
        <span class="ranking-detail__return">${item.return1y}</span>
      </div>
      <div class="ranking-detail__grid">
        <div><span>Region</span><strong>${item.region}</strong></div>
        <div><span>YTD Return</span><strong>${item.returnYtd}</strong></div>
        <div><span>AUM</span><strong>${item.aum}</strong></div>
        <div><span>Benchmark</span><strong>${item.benchmark}</strong></div>
      </div>
      <div class="ranking-detail__copy">
        <p><strong>Strategy:</strong> ${item.strategy}</p>
        <p><strong>Backend hook:</strong> Replace fallback rows with /api/market/fund_public/rank global index fund data.</p>
      </div>
    `;
  }

  async function initRanking(section) {
    const list = section.querySelector("[data-global-ranking-list]");
    const detail = section.querySelector("[data-global-ranking-detail]");
    if (!list || !detail) return;

    const rows = sortByReturn(await loadFunds());
    if (!rows.length) return;

    let page = 0;
    let activeIndex = 0;
    const pager = document.createElement("div");
    pager.className = "ranking-pager";
    section.appendChild(pager);

    function select(index) {
      const item = rows[index];
      if (!item) return;
      activeIndex = index;
      list.querySelectorAll(".ranking-row").forEach((row) => {
        row.classList.toggle("ranking-row--active", Number(row.dataset.globalRankingIndex) === activeIndex);
      });
      renderDetail(detail, item);
    }

    function renderPage() {
      const totalPages = Math.ceil(rows.length / PAGE_SIZE);
      const start = page * PAGE_SIZE;
      const visibleRows = rows.slice(start, start + PAGE_SIZE);

      list.innerHTML = visibleRows
        .map((item, offset) => {
          const index = start + offset;
          return `
            <button type="button" class="ranking-row${index === activeIndex ? " ranking-row--active" : ""}" data-global-ranking-index="${index}">
              <span class="ranking-row__rank">${index + 1}</span>
              <span class="ranking-row__fund">
                <strong>${item.name}</strong>
                <small>${item.code} · ${item.region}</small>
              </span>
              <span class="ranking-row__return">${item.return1y}</span>
            </button>`;
        })
        .join("");

      pager.innerHTML = `
        <button type="button" class="ranking-pager__btn" data-global-page-prev ${page === 0 ? "disabled" : ""}>Prev</button>
        <span class="ranking-pager__meta">Page ${page + 1} / ${totalPages} · ${rows.length} funds</span>
        <button type="button" class="ranking-pager__btn" data-global-page-next ${page >= totalPages - 1 ? "disabled" : ""}>Next</button>
      `;
    }

    list.addEventListener("click", (event) => {
      const button = event.target.closest("[data-global-ranking-index]");
      if (!button) return;
      select(Number(button.dataset.globalRankingIndex));
    });

    pager.addEventListener("click", (event) => {
      const totalPages = Math.ceil(rows.length / PAGE_SIZE);
      if (event.target.closest("[data-global-page-prev]") && page > 0) {
        page -= 1;
        activeIndex = page * PAGE_SIZE;
        renderPage();
        select(activeIndex);
      }
      if (event.target.closest("[data-global-page-next]") && page < totalPages - 1) {
        page += 1;
        activeIndex = page * PAGE_SIZE;
        renderPage();
        select(activeIndex);
      }
    });

    renderPage();
    select(0);
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-global-index-ranking]").forEach(initRanking);
  });
})(window, document);
