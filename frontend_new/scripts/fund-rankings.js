(function (window, document) {
  "use strict";

  const PAGE_SIZE = 5;
  const api = window.FundMasterAPI;

  const DATA = {
    equity: [
      {
        code: "512480",
        name: "Semiconductor Innovation ETF",
        return1y: "+42.8%",
        returnYtd: "+26.4%",
        mtd: "+8.9% MTD",
        totalValue: "$1,840,000.00",
        annualizedYield: "31.6%",
        volatility: "High",
        risk: "High",
        score: "96/100",
        scoreHint: "AI hardware leader",
        aum: "$1.84B",
        latestDate: "Jul 05, 2026",
        latestValue: "$1,840,000 (+8.9%)",
        stdDev: "18.40%",
        sharpe: "3.12",
        beta: "1.36",
        alpha: "+8.20%",
        sectors: [
          ["Semiconductors", "58.0%"],
          ["AI Infrastructure", "18.0%"],
          ["Cloud Hardware", "12.0%"],
          ["Software", "7.0%"],
          ["Cash", "5.0%"],
        ],
        focus: "AI semiconductors, advanced packaging, and memory cycle recovery.",
        signal: "Momentum strong; rebalance gradually after sharp rallies.",
      },
      {
        code: "588000",
        name: "STAR 50 Growth ETF",
        return1y: "+35.6%",
        returnYtd: "+21.9%",
        mtd: "+6.8% MTD",
        totalValue: "$2,160,000.00",
        annualizedYield: "27.4%",
        volatility: "Mod-High",
        risk: "Mod-High",
        score: "93/100",
        scoreHint: "Strong growth basket",
        aum: "$2.16B",
        latestDate: "Jul 05, 2026",
        latestValue: "$2,160,000 (+6.8%)",
        stdDev: "16.10%",
        sharpe: "2.76",
        beta: "1.22",
        alpha: "+6.35%",
        sectors: [
          ["Technology", "44.0%"],
          ["Advanced Manufacturing", "20.0%"],
          ["Healthcare Tech", "13.0%"],
          ["Consumer Tech", "12.0%"],
          ["Cash", "11.0%"],
        ],
        focus: "China technology leaders with high R&D intensity.",
        signal: "Suitable as satellite exposure for high-growth allocation.",
      },
      {
        code: "159915",
        name: "ChiNext Select ETF",
        return1y: "+29.4%",
        returnYtd: "+18.2%",
        mtd: "+5.7% MTD",
        totalValue: "$1,320,000.00",
        annualizedYield: "23.1%",
        volatility: "High",
        risk: "High",
        score: "89/100",
        scoreHint: "Growth with drawdown risk",
        aum: "$1.32B",
        latestDate: "Jul 05, 2026",
        latestValue: "$1,320,000 (+5.7%)",
        stdDev: "19.80%",
        sharpe: "2.18",
        beta: "1.48",
        alpha: "+5.75%",
        sectors: [
          ["Healthcare", "29.0%"],
          ["Technology", "27.0%"],
          ["Consumer Disc.", "19.0%"],
          ["Industrials", "14.0%"],
          ["Cash", "11.0%"],
        ],
        focus: "New economy, healthcare, and growth-oriented small caps.",
        signal: "Watch drawdown risk; position sizing should remain disciplined.",
      },
      {
        code: "510300",
        name: "CSI 300 ETF",
        return1y: "+18.7%",
        returnYtd: "+11.5%",
        mtd: "+3.4% MTD",
        totalValue: "$4,800,000.00",
        annualizedYield: "15.8%",
        volatility: "Medium",
        risk: "Medium",
        score: "82/100",
        scoreHint: "Core allocation fit",
        aum: "$4.80B",
        latestDate: "Jul 05, 2026",
        latestValue: "$4,800,000 (+3.4%)",
        stdDev: "12.20%",
        sharpe: "1.92",
        beta: "1.00",
        alpha: "+2.10%",
        sectors: [
          ["Financials", "24.0%"],
          ["Industrials", "20.0%"],
          ["Consumer", "18.0%"],
          ["Technology", "16.0%"],
          ["Healthcare", "12.0%"],
        ],
        focus: "Large-cap broad market beta with high liquidity.",
        signal: "Core sleeve candidate for balanced equity exposure.",
      },
      {
        code: "516160",
        name: "New Energy Vehicle ETF",
        return1y: "+16.2%",
        returnYtd: "+9.4%",
        mtd: "+2.8% MTD",
        totalValue: "$980,000.00",
        annualizedYield: "13.2%",
        volatility: "Mod-High",
        risk: "Mod-High",
        score: "78/100",
        scoreHint: "Cyclical recovery watch",
        aum: "$0.98B",
        latestDate: "Jul 05, 2026",
        latestValue: "$980,000 (+2.8%)",
        stdDev: "17.20%",
        sharpe: "1.64",
        beta: "1.28",
        alpha: "+1.85%",
        sectors: [
          ["EV Batteries", "36.0%"],
          ["Auto OEM", "24.0%"],
          ["Materials", "18.0%"],
          ["Electronics", "12.0%"],
          ["Cash", "10.0%"],
        ],
        focus: "EV battery chain and smart mobility exposure.",
        signal: "Wait for volume confirmation before increasing allocation.",
      },
      {
        code: "512690",
        name: "Wine & Consumer Leaders ETF",
        return1y: "+13.5%",
        returnYtd: "+7.1%",
        mtd: "+1.6% MTD",
        totalValue: "$760,000.00",
        annualizedYield: "10.4%",
        volatility: "Medium",
        risk: "Medium",
        score: "74/100",
        scoreHint: "Defensive growth",
        aum: "$0.76B",
        latestDate: "Jul 05, 2026",
        latestValue: "$760,000 (+1.6%)",
        stdDev: "10.90%",
        sharpe: "1.48",
        beta: "0.82",
        alpha: "+0.95%",
        sectors: [
          ["Consumer Staples", "52.0%"],
          ["Premium Brands", "22.0%"],
          ["Retail", "12.0%"],
          ["Food & Beverage", "10.0%"],
          ["Cash", "4.0%"],
        ],
        focus: "Consumer leaders with lower beta and dividend visibility.",
        signal: "Useful stabilizer when growth volatility rises.",
      },
    ],
    debt: [
      {
        code: "BND",
        name: "Vanguard Total Bond Fund",
        return1y: "+7.6%",
        returnYtd: "+4.1%",
        duration: "6.1 yrs",
        rating: "AAA / AA",
        totalValue: "$5,200,000",
        averageYield: "4.12%",
        weightedMaturity: "6.1 yrs",
        risk: "AA",
        aum: "$5.20B",
        riskMix: [
          ["AAA / Government", "48%"],
          ["AA / Corporate HG", "24%"],
          ["A / IG Credit", "18%"],
          ["BBB", "8%"],
          ["Cash", "2%"],
        ],
        stableYield: "4.1%",
        highYield: "2.0%",
        focus: "Diversified investment-grade bond exposure.",
        signal: "Stable carry; useful as defensive portfolio anchor.",
      },
      {
        code: "AGG",
        name: "Core Aggregate Bond Fund",
        return1y: "+6.9%",
        returnYtd: "+3.8%",
        duration: "5.8 yrs",
        rating: "AA",
        totalValue: "$3,740,000",
        averageYield: "3.95%",
        weightedMaturity: "5.8 yrs",
        risk: "AA-",
        aum: "$3.74B",
        riskMix: [
          ["AAA / Treasury", "42%"],
          ["Agency MBS", "25%"],
          ["AA / Corporate", "18%"],
          ["BBB / IG", "11%"],
          ["Cash", "4%"],
        ],
        stableYield: "3.9%",
        highYield: "1.8%",
        focus: "Treasuries, agencies, and high-grade corporate bonds.",
        signal: "Balanced duration exposure with moderate rate sensitivity.",
      },
      {
        code: "SHY",
        name: "Short Treasury Income Fund",
        return1y: "+5.2%",
        returnYtd: "+2.7%",
        duration: "1.9 yrs",
        rating: "AAA",
        totalValue: "$2,420,000",
        averageYield: "3.62%",
        weightedMaturity: "1.9 yrs",
        risk: "AAA",
        aum: "$2.42B",
        riskMix: [
          ["US Treasury", "78%"],
          ["Agency", "14%"],
          ["Cash", "8%"],
        ],
        stableYield: "3.6%",
        highYield: "0.5%",
        focus: "Short-duration treasury allocation.",
        signal: "Lower volatility; suitable for cash management sleeve.",
      },
      {
        code: "HYG",
        name: "High Yield Credit Fund",
        return1y: "+9.8%",
        returnYtd: "+5.5%",
        duration: "3.7 yrs",
        rating: "BB",
        totalValue: "$1,180,000",
        averageYield: "6.45%",
        weightedMaturity: "3.7 yrs",
        risk: "BB",
        aum: "$1.18B",
        riskMix: [
          ["BB / High Yield", "46%"],
          ["B / High Yield", "32%"],
          ["CCC", "8%"],
          ["Cash", "14%"],
        ],
        stableYield: "2.2%",
        highYield: "6.4%",
        focus: "Selective high-yield credit and income enhancement.",
        signal: "Higher carry but more credit beta; keep risk budget capped.",
      },
      {
        code: "LQD",
        name: "Investment Grade Corporate Bond Fund",
        return1y: "+6.4%",
        returnYtd: "+3.5%",
        duration: "7.8 yrs",
        rating: "A",
        totalValue: "$2,060,000",
        averageYield: "4.38%",
        weightedMaturity: "7.8 yrs",
        risk: "A",
        aum: "$2.06B",
        riskMix: [
          ["A / Corporate", "44%"],
          ["BBB / IG", "31%"],
          ["AA", "15%"],
          ["Cash", "10%"],
        ],
        stableYield: "4.3%",
        highYield: "2.8%",
        focus: "Longer-duration investment-grade corporate credit.",
        signal: "Attractive if rates stabilize; monitor duration risk.",
      },
      {
        code: "MUB",
        name: "Municipal Income Bond Fund",
        return1y: "+4.8%",
        returnYtd: "+2.4%",
        duration: "4.9 yrs",
        rating: "AA",
        totalValue: "$1,540,000",
        averageYield: "3.28%",
        weightedMaturity: "4.9 yrs",
        risk: "AA",
        aum: "$1.54B",
        riskMix: [
          ["AA / Municipal", "52%"],
          ["A / Municipal", "26%"],
          ["AAA", "16%"],
          ["Cash", "6%"],
        ],
        stableYield: "3.2%",
        highYield: "1.2%",
        focus: "Tax-aware municipal income with lower default risk.",
        signal: "Defensive income option for conservative allocation.",
      },
    ],
  };

  function numberValue(value) {
    const parsed = Number(String(value ?? "").replace(/[%+,$]/g, ""));
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function formatPercent(value) {
    if (value === null || value === undefined || value === "" || value === "--") return "--";
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

  function fallbackCurve(seed = 1) {
    const base = 100 + seed * 2;
    return Array.from({ length: 16 }, (_, index) => {
      const wave = Math.sin((index + seed) / 2) * 2.8;
      const trend = index * (0.8 + seed * 0.08);
      return Math.round((base + trend + wave) * 100) / 100;
    });
  }

  function normalizeRankRecord(record, type, index) {
    const code = String(pick(record, ["基金代码", "fund_code", "code", "symbol"], `FUND-${index + 1}`));
    const name = String(pick(record, ["基金简称", "基金名称", "name", "fund_name", "short_name"], code));
    const return1y = formatPercent(pick(record, ["change_1y", "近1年", "近一年", "1年", "return1y", "year_return", "收益率"], "--"));
    const returnYtd = formatPercent(pick(record, ["change_ytd", "今年来", "近今年", "returnYtd", "ytd_return"], "--"));
    const curve = Array.isArray(record.curve) ? record.curve : [];

    if (type === "debt") {
      return {
        code,
        name,
        return1y,
        returnYtd,
        duration: String(pick(record, ["duration", "久期"], "--")),
        rating: String(pick(record, ["rating", "评级"], "--")),
        totalValue: String(pick(record, ["totalValue", "规模", "aum"], "--")),
        averageYield: return1y,
        weightedMaturity: String(pick(record, ["weightedMaturity", "duration", "久期"], "--")),
        risk: String(pick(record, ["risk", "rating", "评级"], "--")),
        aum: String(pick(record, ["aum", "规模"], "--")),
        riskMix: [],
        stableYield: "--",
        highYield: "--",
        focus: "Backend ranking data",
        signal: "No AI recommendation returned by the backend.",
        curve,
      };
    }

    return {
      code,
      name,
      return1y,
      returnYtd,
      mtd: `${formatPercent(pick(record, ["change_1m", "近1月", "近一月", "mtd"], "--"))} MTD`,
      totalValue: String(pick(record, ["totalValue", "规模", "aum"], "--")),
      annualizedYield: return1y,
      volatility: String(pick(record, ["volatility", "波动"], "--")),
      risk: String(pick(record, ["risk", "风险等级"], "--")),
      score: String(pick(record, ["score"], "--")),
      scoreHint: "Not supplied by backend",
      aum: String(pick(record, ["aum", "规模"], "--")),
      latestDate: String(pick(record, ["date", "latestDate", "净值日期"], "--")),
      latestValue: String(pick(record, ["unit_net_value", "latestValue", "单位净值"], "--")),
      stdDev: "--",
      sharpe: "--",
      beta: "--",
      alpha: "--",
      sectors: [],
      focus: "Backend ranking data",
      signal: "No AI recommendation returned by the backend.",
      curve,
    };
  }

  async function loadRankRows(type) {
    if (!api?.market?.getFundRank) throw new Error("Fund ranking API is not configured");
    try {
      const fundType = type === "debt" ? "bond" : "stock";
      const rows = await api.market.getFundRank(fundType, "change_1y");
      if (Array.isArray(rows) && rows.length) return rows.map((record, index) => normalizeRankRecord(record, type, index));
      throw new Error("Fund ranking API returned no data");
    } catch (error) {
      throw new Error(`Fund ranking unavailable: ${error.message}`);
    }
  }

  async function loadCurve(item) {
    if (!api?.market?.getFundHist || !item.code) return [];
    try {
      const rows = await api.market.getFundHist(item.code);
      if (!Array.isArray(rows) || rows.length < 2) return [];
      return rows
        .map((record) => numberValue(pick(record, ["unit_net_value", "accumulated_net_value", "单位净值", "累计净值", "收盘", "close", "净值"])))
        .filter((value) => Number.isFinite(value) && value > 0)
        .slice(-32);
    } catch (error) {
      console.warn(`Return curve unavailable for ${item.code}:`, error.message);
      return [];
    }
  }

  function renderCard(root, item, type) {
    const extraLabel = type === "debt" ? "Duration / Rating" : "Volatility";
    const extraValue = type === "debt" ? `${item.duration} · ${item.rating}` : item.volatility;

    root.innerHTML = `
      <div class="ranking-detail__head">
        <div>
          <p class="ranking-detail__eyebrow">${item.code}</p>
          <h3>${item.name}</h3>
        </div>
        <span class="ranking-detail__return">${item.return1y}</span>
      </div>
      <div class="ranking-detail__grid">
        <div><span>1Y Return</span><strong>${item.return1y}</strong></div>
        <div><span>YTD Return</span><strong>${item.returnYtd}</strong></div>
        <div><span>${extraLabel}</span><strong>${extraValue}</strong></div>
        <div><span>AUM</span><strong>${item.aum}</strong></div>
      </div>
      <div class="ranking-detail__copy">
        <p><strong>Focus:</strong> ${item.focus}</p>
        <p><strong>AI note:</strong> ${item.signal}</p>
      </div>
    `;
  }

  function updateText(node, value) {
    if (node) node.textContent = value;
  }

  function setBarList(list, rows) {
    if (!list || !rows) return;
    list.innerHTML = rows
      .map(([label, value]) => {
        const width = Number.parseFloat(value) || 0;
        return `<li><span>${label}</span><span>${value}</span><div class="bar-track"><div class="bar-fill" style="width:${width}%"></div></div></li>`;
      })
      .join("");
  }

  function renderCurve(container, values, label) {
    if (!container) return;
    if (!Array.isArray(values) || values.length < 2) {
      container.innerHTML = '<p class="muted">Return curve unavailable from backend.</p>';
      return;
    }
    const width = 760;
    const height = 180;
    const padding = 18;
    const min = Math.min(...values);
    const max = Math.max(...values);
    const span = max - min || 1;
    const points = values
      .map((value, index) => {
        const x = padding + (index / (values.length - 1)) * (width - padding * 2);
        const y = height - padding - ((value - min) / span) * (height - padding * 2);
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");

    container.innerHTML = `
      <svg class="return-chart__svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="${label}">
        <defs>
          <linearGradient id="returnLineGradient" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stop-color="var(--accent-cyan)" />
            <stop offset="100%" stop-color="var(--accent-green)" />
          </linearGradient>
        </defs>
        <path class="return-chart__grid" d="M${padding} ${height - padding}H${width - padding}M${padding} ${height / 2}H${width - padding}M${padding} ${padding}H${width - padding}" />
        <polyline class="return-chart__line" points="${points}" />
      </svg>
      <div class="return-chart__caption">${label}</div>
    `;
  }

  function updateKpis(page, item, type) {
    const cards = page.querySelectorAll(".kpi-row .kpi-card");
    if (type === "equity") {
      updateText(cards[0]?.querySelector(".kpi-card__value"), item.totalValue);
      updateText(cards[0]?.querySelector(".kpi-card__hint"), item.mtd);
      updateText(cards[1]?.querySelector(".kpi-card__value"), item.annualizedYield);
      updateText(cards[1]?.querySelector(".kpi-card__hint"), `${item.return1y} 1Y return`);
      updateText(cards[2]?.querySelector(".kpi-card__value"), item.risk);
      updateText(cards[3]?.querySelector(".kpi-card__value"), item.score);
      updateText(cards[3]?.querySelector(".kpi-card__hint"), item.scoreHint);
      return;
    }

    updateText(cards[0]?.querySelector(".kpi-card__value"), item.totalValue);
    updateText(cards[0]?.querySelector(".kpi-card__hint"), `${item.return1y} YoY`);
    updateText(cards[1]?.querySelector(".kpi-card__value"), item.averageYield);
    updateText(cards[1]?.querySelector(".muted, .kpi-card__hint"), `YTD ${item.returnYtd}`);
    updateText(cards[2]?.querySelector(".kpi-card__value"), item.weightedMaturity);
    updateText(cards[2]?.querySelector(".muted, .kpi-card__hint"), "Fund duration");
    updateText(cards[3]?.querySelector(".kpi-card__value"), item.risk);
    updateText(cards[3]?.querySelector(".muted, .kpi-card__hint"), item.rating);
  }

  async function updateEquityPage(page, item) {
    updateKpis(page, item, "equity");

    const stats = page.querySelectorAll(".fd-stats.eq-mini > div");
    updateText(stats[0]?.querySelector(".fd-stats__k"), item.latestDate);
    updateText(stats[0]?.querySelector(".fd-stats__v"), item.latestValue);
    updateText(stats[1]?.querySelector(".fd-stats__v"), item.stdDev);
    updateText(stats[2]?.querySelector(".fd-stats__v"), item.sharpe);
    updateText(stats[3]?.querySelector(".fd-stats__v"), item.beta);
    updateText(stats[4]?.querySelector(".fd-stats__v"), item.alpha);

    const allocation = Array.from(page.querySelectorAll(".glass-panel")).find((panel) =>
      /Sector Allocation/.test(panel.textContent || "")
    );
    let sectors = [];
    try {
      const rows = await api.publicFund.getIndustryAllocation(item.code);
      if (Array.isArray(rows) && rows.length) {
        sectors = rows.slice(0, 6).map((row) => [
          pick(row, ["industry_category", "industry", "行业类别"], "Other"),
          numberValue(pick(row, ["pct", "percentage", "占净值比例"], 0)),
        ]);
      }
    } catch (error) {
      console.warn(`Industry allocation unavailable for ${item.code}:`, error.message);
    }
    setBarList(allocation?.querySelector(".fd-alloc"), sectors);

    const alert = Array.from(page.querySelectorAll(".glass-panel")).find((panel) =>
      /AI Rebalancing Alert/.test(panel.textContent || "")
    );
    updateText(alert?.querySelector("p"), item.signal);

    const curve = await loadCurve(item);
    renderCurve(page.querySelector("[data-return-chart]"), curve, `${item.name} return curve`);
  }

  async function updateDebtPage(page, item) {
    updateKpis(page, item, "debt");

    const comparison = Array.from(page.querySelectorAll(".glass-panel")).find((panel) =>
      /Return Curve/.test(panel.textContent || "")
    );
    const legend = comparison?.querySelector(".debt-legend");
    if (legend) {
      legend.innerHTML = `<span>Stable Income ${item.stableYield}</span><span>High-Yield ${item.highYield}</span>`;
    }
    const chart = comparison?.querySelector(".debt-chart");
    const curve = await loadCurve(item);
    renderCurve(chart, curve, `${item.name} return curve · Avg yield ${item.averageYield}`);

    const risk = Array.from(page.querySelectorAll(".glass-panel")).find((panel) =>
      /Risk Composition/.test(panel.textContent || "")
    );
    let riskMix = [];
    try {
      const rows = await api.publicFund.getDetailHold(item.code);
      if (Array.isArray(rows) && rows.length) {
        riskMix = rows.slice(0, 6).map((row) => [
          pick(row, ["asset_type", "asset", "资产类型"], "Other"),
          numberValue(pick(row, ["pct", "percentage", "占净值比例"], 0)),
        ]);
      }
    } catch (error) {
      console.warn(`Asset allocation unavailable for ${item.code}:`, error.message);
    }
    setBarList(risk?.querySelector(".fd-alloc"), riskMix);
    updateText(risk?.querySelector("p"), item.signal);
  }

  function updatePage(section, item, type) {
    const page = section.closest("main");
    if (!page) return;
    if (type === "equity") updateEquityPage(page, item);
    if (type === "debt") updateDebtPage(page, item);
  }

  async function initRanking(section) {
    const type = section.dataset.rankingType;
    const list = section.querySelector("[data-ranking-list]");
    const detail = section.querySelector("[data-ranking-detail]");
    if (!list || !detail) return;
    let rows;
    try {
      rows = await loadRankRows(type);
    } catch (error) {
      list.innerHTML = `<p class="muted">${error.message}</p>`;
      detail.innerHTML = "";
      return;
    }

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
        row.classList.toggle("ranking-row--active", Number(row.dataset.rankingIndex) === activeIndex);
      });
      renderCard(detail, item, type);
      updatePage(section, item, type);
    }

    function renderPage() {
      const totalPages = Math.ceil(rows.length / PAGE_SIZE);
      const start = page * PAGE_SIZE;
      const visibleRows = rows.slice(start, start + PAGE_SIZE);

      list.innerHTML = visibleRows
        .map((item, offset) => {
          const index = start + offset;
          return `
          <button type="button" class="ranking-row${index === activeIndex ? " ranking-row--active" : ""}" data-ranking-index="${index}">
            <span class="ranking-row__rank">${index + 1}</span>
            <span class="ranking-row__fund">
              <strong>${item.name}</strong>
              <small>${item.code}</small>
            </span>
            <span class="ranking-row__return">${item.return1y}</span>
          </button>`;
        })
        .join("");

      pager.innerHTML = `
        <button type="button" class="ranking-pager__btn" data-page-prev ${page === 0 ? "disabled" : ""}>Prev</button>
        <span class="ranking-pager__meta">Page ${page + 1} / ${totalPages} · ${rows.length} funds</span>
        <button type="button" class="ranking-pager__btn" data-page-next ${page >= totalPages - 1 ? "disabled" : ""}>Next</button>
      `;
    }

    list.addEventListener("click", (event) => {
      const button = event.target.closest("[data-ranking-index]");
      if (!button) return;
      const index = Number(button.dataset.rankingIndex);
      select(index);
    });

    pager.addEventListener("click", (event) => {
      const totalPages = Math.ceil(rows.length / PAGE_SIZE);
      if (event.target.closest("[data-page-prev]") && page > 0) {
        page -= 1;
        activeIndex = page * PAGE_SIZE;
        renderPage();
        select(activeIndex);
      }
      if (event.target.closest("[data-page-next]") && page < totalPages - 1) {
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
    document.querySelectorAll("[data-ranking-type]").forEach(initRanking);
  });
})(window, document);
