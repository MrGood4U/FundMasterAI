(function (window, document) {
  "use strict";

  const api = window.FundMasterAPI;
  if (!api) return;

  const page = window.location.pathname.split("/").pop() || "";

  function numberValue(value) {
    if (typeof value === "number") return Number.isFinite(value) ? value : 0;
    const parsed = Number(String(value ?? "").replace(/[%+,¥$]/g, ""));
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function hasNumber(value) {
    return value !== null && value !== undefined && value !== "" && value !== "--" && Number.isFinite(numberValue(value));
  }

  function formatNumber(value, digits = 2) {
    return numberValue(value).toLocaleString("zh-CN", { maximumFractionDigits: digits });
  }

  function formatMoney(value) {
    return `¥${formatNumber(value, 2)}`;
  }

  function formatPercent(value) {
    if (!hasNumber(value)) return "--";
    const numeric = numberValue(value);
    return `${numeric > 0 ? "+" : ""}${numeric.toFixed(2)}%`;
  }

  function percentClass(value) {
    const numeric = numberValue(value);
    return numeric > 0 ? "pos" : numeric < 0 ? "neg" : "";
  }

  function fundName(item) {
    return item?.fund_name || item?.["基金简称"] || item?.["基金名称"] || item?.fund_code || "--";
  }

  function extractRows(payload) {
    let value = payload;
    for (let depth = 0; depth < 4; depth += 1) {
      if (Array.isArray(value)) return value;
      if (typeof value === "string") {
        try {
          value = JSON.parse(value);
          continue;
        } catch (error) {
          return [];
        }
      }
      if (value && typeof value === "object") {
        if (Array.isArray(value.items)) return value.items;
        if (Object.prototype.hasOwnProperty.call(value, "data")) {
          value = value.data;
          continue;
        }
      }
      break;
    }
    return [];
  }

  function statusNode() {
    let node = document.querySelector("[data-dashboard-status]");
    if (node) return node;
    node = document.createElement("p");
    node.className = "api-status";
    node.dataset.dashboardStatus = "";
    const pageHeadCopy = document.querySelector(".page-head > div:first-child");
    const pageHead = document.querySelector(".page-head");
    (pageHeadCopy || pageHead || document.querySelector("main"))?.append(node);
    return node;
  }

  function setStatus(message, isError = false) {
    const node = statusNode();
    if (!node) return;
    node.textContent = message;
    node.classList.toggle("api-status--error", isError);
  }

  function setCard(card, label, value, hint = "") {
    if (!card) return;
    const labelNode = card.querySelector(".kpi-card__label");
    const valueNode = card.querySelector(".kpi-card__value");
    const hintNode = card.querySelector(".kpi-card__hint, .muted.sm");
    if (labelNode) labelNode.textContent = label;
    if (valueNode) valueNode.textContent = value;
    if (hintNode) hintNode.textContent = hint;
  }

  function replaceTable(table, headers, rows) {
    if (!table) return;
    const headerCells = table.querySelectorAll("thead th");
    headers.forEach((header, index) => {
      if (headerCells[index]) headerCells[index].textContent = header;
    });
    const tbody = table.querySelector("tbody");
    if (!tbody) return;
    tbody.replaceChildren();
    if (!rows.length) {
      const row = document.createElement("tr");
      const cell = document.createElement("td");
      cell.colSpan = headers.length;
      cell.textContent = "No live data returned.";
      row.append(cell);
      tbody.append(row);
      return;
    }
    rows.forEach((values) => {
      const row = document.createElement("tr");
      values.forEach((item) => {
        const cell = document.createElement("td");
        const descriptor = item && typeof item === "object" ? item : { value: item };
        cell.textContent = descriptor.value ?? "--";
        if (descriptor.className) cell.className = descriptor.className;
        row.append(cell);
      });
      tbody.append(row);
    });
  }

  function replaceBars(list, rows) {
    if (!list) return;
    list.replaceChildren();
    rows.forEach(({ label, value, width }) => {
      const item = document.createElement("li");
      const name = document.createElement("span");
      const amount = document.createElement("span");
      const track = document.createElement("div");
      const fill = document.createElement("div");
      name.textContent = label;
      amount.textContent = value;
      track.className = "bar-track";
      fill.className = "bar-fill";
      fill.style.width = `${Math.max(2, Math.min(100, numberValue(width)))}%`;
      track.append(fill);
      item.append(name, amount, track);
      list.append(item);
    });
  }

  function renderLineChart(container, values, labels, color = "#00f2a4") {
    if (!container) return;
    const points = values.map(numberValue).filter(Number.isFinite);
    if (points.length < 2) return;
    const width = 760;
    const height = 220;
    const pad = 28;
    const min = Math.min(...points, 0);
    const max = Math.max(...points, 0);
    const range = max - min || 1;
    const coords = points.map((value, index) => ({
      x: pad + index * ((width - pad * 2) / Math.max(points.length - 1, 1)),
      y: height - pad - ((value - min) / range) * (height - pad * 2),
      value,
    }));
    const path = coords.map((point) => `${point.x},${point.y}`).join(" ");
    const area = `${pad},${height - pad} ${path} ${width - pad},${height - pad}`;
    container.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="收益趋势图" preserveAspectRatio="none">
      <defs><linearGradient id="chart-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${color}" stop-opacity=".28"/><stop offset="1" stop-color="${color}" stop-opacity="0"/></linearGradient></defs>
      <line x1="${pad}" y1="${height - pad}" x2="${width - pad}" y2="${height - pad}" stroke="rgba(255,255,255,.15)"/>
      <polygon points="${area}" fill="url(#chart-fill)"/>
      <polyline points="${path}" fill="none" stroke="${color}" stroke-width="3" vector-effect="non-scaling-stroke"/>
      ${coords.map((point, index) => `<circle cx="${point.x}" cy="${point.y}" r="4" fill="${color}"><title>${labels[index] || index}: ${formatPercent(point.value)}</title></circle>`).join("")}
      ${coords.map((point, index) => `<text x="${point.x}" y="${height - 8}" text-anchor="middle" fill="#8f98a7" font-size="12">${labels[index] || ""}</text>`).join("")}
    </svg>`;
  }

  function resetPage() {
    document.querySelectorAll(".kpi-card__value").forEach((node) => {
      node.innerHTML = '<span class="data-skeleton data-skeleton--value" aria-hidden="true"></span><span class="visually-hidden">Loading</span>';
    });
    document.querySelectorAll(".data-table tbody").forEach((tbody) => {
      const columnCount = tbody.closest("table")?.querySelectorAll("thead th").length || 1;
      tbody.innerHTML = `<tr><td colspan="${columnCount}"><div class="data-loading-state data-loading-state--compact">Loading verified backend data…</div></td></tr>`;
    });
    setStatus("Connecting to backend...");
  }

  async function loadEquityFunds() {
    resetPage();
    try {
      const data = await api.publicFund.getRank({ fund_type: "stock" });
      const rows = extractRows(data);
      const ranked = rows.slice().sort((a, b) => numberValue(b.change_1y) - numberValue(a.change_1y));
      const validYear = rows.filter((item) => hasNumber(item.change_1y));
      const averageYear = validYear.length
        ? validYear.reduce((sum, item) => sum + numberValue(item.change_1y), 0) / validYear.length
        : 0;
      const cards = document.querySelectorAll(".eq-kpis .kpi-card");
      setCard(cards[0], "Tracked Equity Funds", formatNumber(rows.length, 0), "Live stock-fund ranking");
      setCard(cards[1], "Average 1Y Return", formatPercent(averageYear), `${validYear.length} funds with data`);
      setCard(cards[2], "Best 1Y Fund", ranked[0]?.fund_code || "--", ranked[0] ? fundName(ranked[0]) : "No result");
      setCard(cards[3], "Best 1Y Return", formatPercent(ranked[0]?.change_1y), "Backend ranking leader");

      const mini = document.querySelectorAll(".eq-mini > div");
      const latest = ranked[0] || {};
      const miniValues = [
        [latest.date || "Latest NAV", latest.unit_net_value ?? "--"],
        ["Daily", formatPercent(latest.daily_growth_rate)],
        ["1 Month", formatPercent(latest.change_1m)],
        ["6 Months", formatPercent(latest.change_6m)],
        ["Year to Date", formatPercent(latest.change_ytd)],
      ];
      miniValues.forEach(([label, value], index) => {
        if (!mini[index]) return;
        mini[index].querySelector(".fd-stats__k").textContent = label;
        mini[index].querySelector(".fd-stats__v").textContent = value;
      });
      renderLineChart(
        document.querySelector(".eq-chart"),
        [0, latest.change_1m, latest.change_3m, latest.change_6m, latest.change_ytd, latest.change_1y],
        ["Start", "1M", "3M", "6M", "YTD", "1Y"]
      );

      const allocationHeading = document.querySelector(".two-col .glass-panel h3");
      if (allocationHeading) allocationHeading.textContent = "Top 1Y Equity Funds";
      replaceBars(
        document.querySelector(".fd-alloc"),
        ranked.slice(0, 5).map((item) => ({
          label: fundName(item),
          value: formatPercent(item.change_1y),
          width: Math.abs(numberValue(item.change_1y)),
        }))
      );
      const alert = document.querySelector(".two-col .glass-panel:nth-child(2) .muted");
      if (alert) alert.textContent = ranked[0]
        ? `${fundName(ranked[0])} currently leads the backend stock-fund ranking with ${formatPercent(ranked[0].change_1y)} over one year.`
        : "No equity ranking data returned.";
      replaceTable(
        document.querySelector(".data-table"),
        ["Code", "Fund", "NAV", "1Y"],
        ranked.slice(0, 10).map((item) => [
          item.fund_code,
          fundName(item),
          item.unit_net_value ?? "--",
          { value: formatPercent(item.change_1y), className: percentClass(item.change_1y) },
        ])
      );
      setStatus(`Equity API live · ${rows.length} funds`);
    } catch (error) {
      setStatus(`Equity backend unavailable: ${error.message}`, true);
    }
  }

  async function loadDebtFunds() {
    resetPage();
    try {
      const data = await api.publicFund.getRank({ fund_type: "bond" });
      const allRows = Array.isArray(data) ? data.filter((item) => item.fund_code) : [];
      const debtPattern = /债|利率|信用|转债|固收/;
      const rows = allRows.filter((item) => debtPattern.test(fundName(item)));
      const ranked = rows.slice().sort((a, b) => numberValue(b.change_1y) - numberValue(a.change_1y));
      const validYear = rows.filter((item) => hasNumber(item.change_1y));
      const averageYear = validYear.length
        ? validYear.reduce((sum, item) => sum + numberValue(item.change_1y), 0) / validYear.length
        : 0;
      const positive = validYear.filter((item) => numberValue(item.change_1y) > 0).length;
      const cards = document.querySelectorAll(".kpi-row .kpi-card");
      setCard(cards[0], "Tracked Debt Funds", formatNumber(rows.length, 0), "Live bond-fund ranking");
      setCard(cards[1], "Average 1Y Return", formatPercent(averageYear), "Backend average");
      setCard(cards[2], "Positive 1Y Funds", formatNumber(positive, 0), `${validYear.length} comparable`);
      setCard(cards[3], "Latest NAV Date", ranked[0]?.date || "--", ranked[0]?.fund_code || "No result");
      const leaders = ranked.slice(0, 6);
      renderLineChart(
        document.querySelector(".debt-chart"),
        leaders.map((item) => item.change_1y),
        leaders.map((item) => item.fund_code),
        "#ffc563"
      );

      const riskHeading = document.querySelector(".two-col .glass-panel:nth-child(2) h3");
      if (riskHeading) riskHeading.textContent = "Top Bond Fund Returns";
      replaceBars(
        document.querySelector(".fd-alloc"),
        ranked.slice(0, 5).map((item) => ({
          label: fundName(item),
          value: formatPercent(item.change_1y),
          width: Math.abs(numberValue(item.change_1y)),
        }))
      );
      replaceTable(
        document.querySelector(".data-table"),
        ["Fund", "NAV", "Daily", "1Y", "Date"],
        ranked.slice(0, 10).map((item) => [
          `${fundName(item)} · ${item.fund_code}`,
          item.unit_net_value ?? "--",
          { value: formatPercent(item.daily_growth_rate), className: percentClass(item.daily_growth_rate) },
          { value: formatPercent(item.change_1y), className: percentClass(item.change_1y) },
          item.date || "--",
        ])
      );
      setStatus(`Debt API live · ${rows.length} funds`);
    } catch (error) {
      setStatus(`Debt backend unavailable: ${error.message}`, true);
    }
  }

  async function loadMarketFlow() {
    resetPage();
    try {
      const data = await api.publicFund.getRank({ fund_type: "stock" });
      // rank 已按 fund_type 在后端筛选；这里保留所有返回行，避免字段过滤误判为 0 条。
      const rows = extractRows(data);
      const advancing = rows.filter((item) => numberValue(item.daily_growth_rate) > 0);
      const declining = rows.filter((item) => numberValue(item.daily_growth_rate) < 0);
      const averageDaily = rows.reduce((sum, item) => sum + numberValue(item.daily_growth_rate), 0) / Math.max(rows.length, 1);
      const positiveMomentum = advancing.reduce((sum, item) => sum + numberValue(item.daily_growth_rate), 0);
      const negativeMomentum = declining.reduce((sum, item) => sum + Math.abs(numberValue(item.daily_growth_rate)), 0);
      const cards = document.querySelectorAll(".mf-kpis .kpi-card");
      setCard(cards[0], "Advancing Funds", `${(advancing.length / Math.max(rows.length, 1) * 100).toFixed(1)}%`, `${advancing.length} funds`);
      setCard(cards[1], "Declining Funds", `${(declining.length / Math.max(rows.length, 1) * 100).toFixed(1)}%`, `${declining.length} funds`);
      setCard(cards[2], "Net Momentum", formatPercent(positiveMomentum - negativeMomentum), "Aggregate daily proxy");
      setCard(cards[3], "Average Daily Move", formatPercent(averageDaily), "Equity-fund universe");
      setCard(cards[4], "Large Movers", formatNumber(rows.filter((item) => Math.abs(numberValue(item.daily_growth_rate)) >= 2).length, 0), "Absolute move ≥ 2%");
      setCard(cards[5], "Tracked Funds", formatNumber(rows.length, 0), "Live backend rows");

      const headings = document.querySelectorAll(".section-head__title");
      if (headings[0]) headings[0].textContent = "Equity Fund Momentum";
      if (headings[1]) headings[1].textContent = "Active Fund Heatmap";
      if (headings[2]) headings[2].textContent = "Largest Daily Moves";
      if (headings[3]) headings[3].textContent = "Equity Fund Momentum Table";
      const liquid = rows.slice().sort((a, b) => Math.abs(numberValue(b.daily_growth_rate)) - Math.abs(numberValue(a.daily_growth_rate)));
      replaceBars(
        document.querySelector(".mf-heat"),
        liquid.slice(0, 4).map((item, index) => ({
          label: fundName(item),
          value: formatPercent(item.daily_growth_rate),
          width: index === 0 ? 100 : Math.abs(numberValue(item.daily_growth_rate)) / Math.max(Math.abs(numberValue(liquid[0]?.daily_growth_rate)), 0.01) * 100,
        }))
      );
      const movers = liquid.slice(0, 5);
      const moverList = document.querySelector(".mf-list");
      if (moverList) {
        moverList.replaceChildren();
        movers.forEach((item) => {
          const li = document.createElement("li");
          li.className = percentClass(item.daily_growth_rate);
          const name = document.createElement("span");
          const change = document.createElement("span");
          name.textContent = fundName(item);
          change.textContent = formatPercent(item.daily_growth_rate);
          li.append(name, change);
          moverList.append(li);
        });
      }
      replaceTable(
        document.querySelector(".data-table"),
        ["Fund", "Direction", "NAV", "Daily", "1Y"],
        liquid.slice(0, 10).map((item) => [
          `${fundName(item)} · ${item.fund_code}`,
          numberValue(item.daily_growth_rate) >= 0 ? "POSITIVE" : "NEGATIVE",
          item.unit_net_value ?? "--",
          { value: formatPercent(item.daily_growth_rate), className: percentClass(item.daily_growth_rate) },
          { value: formatPercent(item.change_1y), className: percentClass(item.change_1y) },
        ])
      );
      setStatus(`Market flow API live · ${rows.length} equity funds`);
    } catch (error) {
      document.querySelectorAll(".mf-kpis .kpi-card").forEach((card) => {
        setCard(card, card.querySelector(".kpi-card__label")?.textContent || "Fund metric", "—", "Verified backend data unavailable");
      });
      const heat = document.querySelector(".mf-heat");
      if (heat) heat.innerHTML = '<li class="data-unavailable">Verified equity fund moves are unavailable.</li>';
      const movers = document.querySelector(".mf-list");
      if (movers) movers.innerHTML = '<li class="data-unavailable">Verified movers are unavailable.</li>';
      replaceTable(document.querySelector(".data-table"), ["Fund", "Direction", "NAV", "Daily", "1Y"], []);
      setStatus(`Market flow backend unavailable: ${error.message}`, true);
    }
  }

  async function loadGlobalInvestment() {
    resetPage();
    try {
      const results = await Promise.allSettled([
        api.global.getIndexQuotesFromList(["^IXIC", "^GDAXI", "^HSI"], 3),
        api.global.getExchangeRate("USD", "CNY"),
        api.macro.getData({ country: "china", indicator: "pmi" }),
      ]);
      const rows = results[0].status === "fulfilled" && Array.isArray(results[0].value) ? results[0].value : [];
      const rate = results[1].status === "fulfilled" ? results[1].value : null;
      const macroRows = results[2].status === "fulfilled" && Array.isArray(results[2].value) ? results[2].value : [];
      const tickerCards = document.querySelectorAll(".gi-ticker .kpi-card");
      tickerCards.forEach((card, index) => {
        if (index < 3) {
          setCard(card, card.querySelector(".kpi-card__label")?.textContent || "Global Index", "--", "No live quote");
          card.querySelector(".kpi-card__hint")?.classList.remove("kpi-card__hint--neg", "pos", "neg");
        }
      });
      rows.slice(0, 3).forEach((item, index) => {
        setCard(tickerCards[index], item.name || item.ticker || "Global Index", formatNumber(item.price, 2), formatPercent(item.change_pct));
      });
      if (tickerCards[3]) setCard(tickerCards[3], "USD/CNY", formatNumber(rate?.rate, 4), "Live exchange rate");
      const aiItems = document.querySelectorAll(".gi-ai li");
      const ranked = rows.slice().sort((a, b) => numberValue(b.change_pct) - numberValue(a.change_pct));
      if (aiItems[0] && ranked[0]) {
        aiItems[0].querySelector("strong").textContent = `LEADER: ${ranked[0].name || ranked[0].ticker}`;
        aiItems[0].querySelector("p").textContent = `Latest move ${formatPercent(ranked[0].change_pct)} from the global index API.`;
      }
      const weakest = ranked[ranked.length - 1];
      if (aiItems[1] && weakest) {
        aiItems[1].querySelector("strong").textContent = `WATCH: ${weakest.name || weakest.ticker}`;
        aiItems[1].querySelector("p").textContent = `Latest move ${formatPercent(weakest.change_pct)}; review cross-border exposure.`;
      }
      const averageDaily = rows.reduce((sum, item) => sum + numberValue(item.change_pct), 0) / Math.max(rows.length, 1);
      const sentiment = document.querySelector(".mh-greed__n");
      if (sentiment) sentiment.textContent = String(Math.max(0, Math.min(100, Math.round(50 + averageDaily * 10))));
      const matrix = document.querySelector(".gi-matrix");
      if (matrix && macroRows.length) {
        matrix.replaceChildren();
        macroRows.slice(0, 24).forEach((item) => {
          const cell = document.createElement("span");
          const value = item.manufacturing_index ?? item["制造业-指数"] ?? item.value ?? item.national_yoy ?? 0;
          cell.className = numberValue(value) >= 50 ? "pos" : "neg";
          cell.style.opacity = String(Math.max(0.35, Math.min(1, 0.35 + Math.abs(numberValue(value) - 50) / 8)));
          cell.title = `${item.month || item["月份"] || item.date || "Macro"}: 制造业 PMI ${value}`;
          matrix.append(cell);
        });
      }
      replaceTable(
        document.querySelector(".data-table"),
        ["Index", "Region", "Price", "Daily", "Strategy"],
        ranked.map((item) => [
          `${item.name || "Global Index"} · ${item.ticker || "--"}`,
          item.region || "Global",
          formatNumber(item.price, 2),
          { value: formatPercent(item.change_pct), className: percentClass(item.change_pct) },
          numberValue(item.change_pct) > 0 ? "HOLD / REVIEW" : "WATCH",
        ])
      );
      const liveCount = (rows.length ? 1 : 0) + (rate?.rate ? 1 : 0) + (macroRows.length ? 1 : 0);
      setStatus(`Global APIs live · ${liveCount}/3 sources · ${rows.length} indices · ${macroRows.length} macro rows`, liveCount < 2);
    } catch (error) {
      setStatus(`Global backend unavailable: ${error.message}`, true);
    }
  }

  async function loadPortfolioOverview() {
    resetPage();
    try {
      const data = await api.portfolio.holdings.list({ page: 1, page_size: 50 });
      const rows = Array.isArray(data?.items) ? data.items : [];
      const totalMarketValue = rows.reduce((sum, item) => sum + numberValue(item.market_value), 0);
      const totalPnl = rows.reduce((sum, item) => sum + numberValue(item.unrealized_pnl), 0);
      const big = document.querySelector(".po-big");
      const summaryLabel = document.querySelector(".po-summary .muted");
      if (summaryLabel) summaryLabel.textContent = `Market value ${formatMoney(totalMarketValue)} · ${rows.length} holdings`;
      if (big) {
        big.textContent = formatMoney(totalPnl);
        big.className = `po-big ${percentClass(totalPnl)}`;
      }
      replaceTable(
        document.querySelector(".data-table"),
        ["Asset", "Value", "Daily", "Return", "Type"],
        rows.map((item) => [
          `${item.asset_name || "--"} · ${item.asset_code}`,
          formatMoney(item.market_value),
          { value: formatPercent(item.change_pct), className: percentClass(item.change_pct) },
          { value: formatPercent(item.unrealized_pnl_pct), className: percentClass(item.unrealized_pnl_pct) },
          item.asset_type || "--",
        ])
      );
      const signal = document.querySelector(".po-ai .chip");
      const detail = document.querySelector(".po-ai > div:nth-child(2) p");
      const actions = document.querySelector(".po-ai > div:nth-child(3) ul");
      const largest = rows.slice().sort((a, b) => numberValue(b.market_value) - numberValue(a.market_value))[0];
      const concentration = totalMarketValue && largest ? numberValue(largest.market_value) / totalMarketValue * 100 : 0;
      if (signal) signal.textContent = concentration > 40 ? "Concentrated" : rows.length ? "Balanced" : "Empty";
      if (detail) detail.textContent = rows.length
        ? `${largest.asset_name || largest.asset_code} is the largest holding at ${concentration.toFixed(1)}% of live market value.`
        : "No holdings are stored in the portfolio backend.";
      if (actions) {
        actions.replaceChildren();
        const messages = rows.length
          ? [
              `Review ${largest.asset_name || largest.asset_code} concentration.`,
              `${rows.filter((item) => numberValue(item.unrealized_pnl) < 0).length} holdings currently have unrealized losses.`,
            ]
          : ["Create a transaction in the portfolio backend to generate holdings."];
        messages.forEach((message) => {
          const item = document.createElement("li");
          item.textContent = message;
          actions.append(item);
        });
      }
      const refresh = document.querySelector(".data-table-wrap + .btn-outline");
      if (refresh) {
        refresh.textContent = "Refresh Holdings";
        refresh.addEventListener("click", loadPortfolioOverview, { once: true });
      }
      setStatus(`Portfolio API live · ${rows.length} holdings`);
    } catch (error) {
      setStatus(`Portfolio backend unavailable: ${error.message}`, true);
    }
  }

  function smtpFormData(form) {
    return {
      email: form.elements.email.value.trim(),
      sender_name: form.elements.sender_name.value.trim(),
      smtp_host: form.elements.smtp_host.value.trim(),
      smtp_port: Number(form.elements.smtp_port.value),
      password: form.elements.password.value,
      encryption: form.elements.encryption.value,
    };
  }

  async function loadSettings() {
    const form = document.querySelector("[data-smtp-form]");
    const profileForm = document.querySelector("[data-profile-form]");
    if (profileForm) {
      try {
        const profile = await api.portfolio.userProfile.get();
        profileForm.elements.phone.value = profile?.phone || "";
        profileForm.elements.profile_email.value = profile?.email || "";
      } catch (error) {
        setStatus(`User profile unavailable: ${error.message}`, true);
      }
      profileForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const phone = profileForm.elements.phone.value.trim();
        const email = profileForm.elements.profile_email.value.trim();
        if (!phone && !email) {
          setStatus("Enter a phone number or contact email", true);
          return;
        }
        setStatus("Saving user profile...");
        try {
          await api.portfolio.userProfile.update({ phone: phone || undefined, email: email || undefined });
          setStatus("User profile saved");
        } catch (error) {
          setStatus(`Unable to save user profile: ${error.message}`, true);
        }
      });
    }
    if (!form) return;
    setStatus("Connecting to portfolio settings...");
    try {
      const config = await api.portfolio.smtp.getConfig();
      ["email", "sender_name", "smtp_host", "smtp_port", "encryption"].forEach((name) => {
        if (form.elements[name] && config?.[name] !== undefined) form.elements[name].value = config[name];
      });
      setStatus("Portfolio settings API live");
    } catch (error) {
      setStatus(`Settings backend unavailable: ${error.message}`, true);
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      setStatus("Saving SMTP configuration...");
      try {
        await api.portfolio.smtp.updateConfig(smtpFormData(form));
        setStatus("SMTP configuration saved");
      } catch (error) {
        setStatus(`Unable to save SMTP configuration: ${error.message}`, true);
      }
    });

    const testButton = document.querySelector("[data-test-email]");
    testButton?.addEventListener("click", async () => {
      const toEmail = form.elements.test_email.value.trim();
      if (!toEmail) {
        setStatus("Enter a test recipient first", true);
        return;
      }
      setStatus("Sending test email...");
      try {
        await api.portfolio.smtp.testEmail({ to_email: toEmail });
        setStatus("Test email sent");
      } catch (error) {
        setStatus(`Test email failed: ${error.message}`, true);
      }
    });
  }

  const loaders = {
    "equity-funds.html": loadEquityFunds,
    "debt-funds.html": loadDebtFunds,
    "market-flow.html": loadMarketFlow,
    "global-investment.html": loadGlobalInvestment,
    "portfolio-overview.html": loadPortfolioOverview,
    "settings.html": loadSettings,
  };

  document.addEventListener("DOMContentLoaded", () => {
    loaders[page]?.();
  });
})(window, document);
