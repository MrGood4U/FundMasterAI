(function (window, document) {
  "use strict";

  const api = window.FundMasterAPI;
  if (!api) return;

  const DEFAULT_STOCK_SYMBOL = "300059";
  const DEFAULT_FUND_CODE = "510300";

  function text(value, fallback = "--") {
    if (value === null || value === undefined || value === "") return fallback;
    return String(value);
  }

  function escapeHtml(value) {
    return text(value, "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function safeUrl(value) {
    const url = text(value, "#");
    if (url === "#" || /^https?:\/\//i.test(url)) return url;
    return "#";
  }

  function pick(record, keys, fallback = undefined) {
    if (!record) return fallback;
    for (const key of keys) {
      if (record[key] !== null && record[key] !== undefined && record[key] !== "") {
        return record[key];
      }
    }
    return fallback;
  }

  function numberValue(value) {
    if (typeof value === "number") return value;
    const parsed = Number(String(value || "").replace(/[%+,]/g, ""));
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function formatPercent(value) {
    const n = numberValue(value);
    const sign = n > 0 ? "+" : "";
    return `${sign}${n.toFixed(2)}%`;
  }

  function setStatus(target, message, isError = false) {
    const node = typeof target === "string" ? document.querySelector(target) : target;
    if (!node) return;
    node.textContent = message;
    node.classList.toggle("api-status--error", isError);
  }

  function renderMarketHeatmap(rows) {
    const heat = document.querySelector("[data-market-heat]");
    if (!heat || !rows.length) return;

    const topRows = rows
      .filter((item) => pick(item, ["stock_code", "stock_name", "代码", "名称"]))
      .slice(0, 12);

    heat.innerHTML = topRows
      .map((item) => {
        const code = pick(item, ["stock_code", "代码", "symbol"], "");
        const name = pick(item, ["stock_name", "名称", "name"], "");
        const change = pick(item, ["change_pct", "涨跌幅", "涨幅", "change"], 0);
        const positive = numberValue(change) >= 0;
        const price = pick(item, ["latest_price", "最新价", "现价", "price"], "");
        return `<div class="mh-cell ${positive ? "pos" : "neg"}"><span>${escapeHtml(code)}</span><em>${formatPercent(change)}</em><small>${escapeHtml(name)} ${price ? "· " + escapeHtml(price) : ""}</small></div>`;
      })
      .join("");
  }

  function renderMarketMovers(rows) {
    const movers = document.querySelector("[data-market-movers]");
    if (!movers || !rows.length) return;

    const sorted = rows
      .filter((item) => pick(item, ["stock_name", "stock_code", "名称", "代码"]) !== undefined)
      .slice()
      .sort((a, b) => numberValue(pick(b, ["change_pct", "涨跌幅"], 0)) - numberValue(pick(a, ["change_pct", "涨跌幅"], 0)));

    const gainers = sorted.slice(0, 5);
    const decliners = sorted.slice(-5).reverse();

    function renderList(items, cls) {
      return `<ul>${items
        .map((item) => {
          const name = pick(item, ["stock_name", "stock_code", "名称", "代码"], "Unknown");
          const change = pick(item, ["change_pct", "涨跌幅"], 0);
          return `<li class="${cls}">${escapeHtml(name)} ${formatPercent(change)}</li>`;
        })
        .join("")}</ul>`;
    }

    movers.innerHTML = `${renderList(gainers, "pos")}${renderList(decliners, "neg")}`;
  }

  async function loadMarketHub() {
    const root = document.querySelector(".content--market-hub");
    if (!root) return;

    setStatus("[data-api-status='market']", "Connecting to market backend...");
    try {
      const rows = await api.global.getIndexQuotesFromList(["^GSPC", "^IXIC", "^FTSE", "^N225"], 4);
      const quotes = Array.isArray(rows) ? rows : [];
      document.querySelectorAll(".mh-indices .mh-index").forEach((card, index) => {
        const quote = quotes[index];
        if (!quote) return;
        const change = pick(quote, ["change_pct", "changePercent", "percent_change"], 0);
        const value = numberValue(pick(quote, ["price", "last_price", "regularMarketPrice"], 0));
        const title = card.querySelector("h4");
        const price = card.querySelector(".mh-index__v");
        const percent = card.querySelector(".mh-index__p");
        if (title) title.textContent = pick(quote, ["name", "short_name", "ticker"], "Global Index");
        if (price) price.textContent = value ? value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : "--";
        if (percent) {
          percent.textContent = formatPercent(change);
          percent.classList.toggle("pos", numberValue(change) >= 0);
          percent.classList.toggle("neg", numberValue(change) < 0);
        }
      });
      renderMarketHeatmap(quotes.map((quote) => ({
        stock_code: pick(quote, ["ticker"], ""),
        stock_name: pick(quote, ["name", "region"], ""),
        latest_price: pick(quote, ["price", "last_price"], ""),
        change_pct: pick(quote, ["change_pct", "changePercent"], 0),
      })));
      renderMarketMovers(quotes.map((quote) => ({
        stock_name: pick(quote, ["name", "ticker"], "Global Index"),
        change_pct: pick(quote, ["change_pct", "changePercent"], 0),
      })));
      setStatus(
        "[data-api-status='market']",
        quotes.length ? `Global index API live · ${quotes.length} quotes` : "Global index API returned no quotes; showing preview values",
        quotes.length === 0
      );
    } catch (error) {
      setStatus("[data-api-status='market']", `Market backend unavailable: ${error.message}`, true);
    }
  }

  function newsCard(item, index) {
    const title = pick(item, ["news_title", "新闻标题", "标题", "title"], "Untitled market update");
    const body = pick(item, ["news_content", "新闻内容", "内容", "摘要", "summary"], "");
    const source = pick(item, ["文章来源", "来源", "source"], "MARKET NEWS");
    const time = pick(item, ["publish_time", "发布时间", "时间", "date"], "");
    const url = pick(item, ["新闻链接", "链接", "url"], "#");
    const hot = index === 0;

    return `<article class="news-card ${hot ? "news-card--flash" : ""}">
      <div class="news-card__meta">
        <div class="news-card__tags">
          <span class="tag ${hot ? "tag--breaking" : "tag--tech"}">${hot ? "LATEST" : "NEWS"}</span>
          <span class="news-card__source">${escapeHtml(text(time, "RECENT"))} · ${escapeHtml(source)}</span>
        </div>
        <a class="news-card__ext" href="${safeUrl(url)}" target="_blank" rel="noreferrer" aria-label="打开新闻">↗</a>
      </div>
      <h4 class="news-card__headline">${escapeHtml(title)}</h4>
      <p class="news-card__body">${escapeHtml(body || title)}</p>
      <div class="news-card__footer">
        <span class="sentiment-pill sentiment-pill--neutral"><span class="sentiment-pill__dot"></span>LIVE FEED</span>
        <span class="news-card__related">Symbol: ${DEFAULT_STOCK_SYMBOL}</span>
      </div>
    </article>`;
  }

  async function loadNewsFeed() {
    const feed = document.querySelector("[data-news-feed]");
    if (!feed) return;

    setStatus("[data-api-status='news']", "Connecting to news backend...");
    try {
      const rows = await api.news.getStockRecentNews({ symbol: DEFAULT_STOCK_SYMBOL });
      const list = Array.isArray(rows) ? rows.slice(0, 6) : [];
      if (list.length) {
        feed.innerHTML = list.map(newsCard).join("");
      }
      setStatus("[data-api-status='news']", `Live terminal · ${list.length} news`);
    } catch (error) {
      setStatus("[data-api-status='news']", `News backend unavailable: ${error.message}`, true);
    }
  }

  function renderFundHeader(record) {
    const title = document.querySelector("[data-fund-title]");
    const ticker = document.querySelector("[data-fund-ticker]");
    const nav = document.querySelector("[data-fund-nav]");
    const change = document.querySelector("[data-fund-change]");

    const name = pick(record, ["fund_name", "基金名称", "名称"], "ETF Fund");
    const code = pick(record, ["fund_code", "基金代码", "代码"], DEFAULT_FUND_CODE);
    const price = pick(
      record,
      ["latest_price", "current_unit_net_value", "latest_unit_net_value", "unit_net_value", "最新价", "现价", "单位净值"],
      "--"
    );
    const changeValue = pick(
      record,
      ["change_pct", "growth_rate", "daily_growth_rate", "涨跌幅", "涨幅", "日增长率"],
      0
    );

    if (title) title.textContent = name;
    if (ticker) ticker.textContent = code;
    if (nav) nav.textContent = text(price);
    if (change) {
      change.textContent = formatPercent(changeValue);
      change.classList.toggle("pos", numberValue(changeValue) >= 0);
      change.classList.toggle("neg", numberValue(changeValue) < 0);
    }
  }

  function renderFundHist(rows) {
    const stats = document.querySelector("[data-fund-stats]");
    if (!stats || !rows.length) return;

    const orderedRows = rows.slice().sort((a, b) => {
      const aDate = Date.parse(pick(a, ["date", "日期"], ""));
      const bDate = Date.parse(pick(b, ["date", "日期"], ""));
      return (Number.isNaN(aDate) ? 0 : aDate) - (Number.isNaN(bDate) ? 0 : bDate);
    });
    const first = orderedRows[0];
    const last = orderedRows[orderedRows.length - 1];
    const firstClose = numberValue(pick(first, ["close", "unit_net_value", "收盘", "单位净值"], 0));
    const lastClose = numberValue(pick(last, ["close", "unit_net_value", "收盘", "单位净值"], 0));
    const change = firstClose ? ((lastClose - firstClose) / firstClose) * 100 : 0;
    const latestDate = pick(last, ["日期", "date"], "Latest");

    stats.innerHTML = `
      <div><span class="fd-stats__k">${escapeHtml(latestDate)}</span><span class="fd-stats__v">${escapeHtml(lastClose || "--")}</span></div>
      <div><span class="fd-stats__k">Period Return</span><span class="fd-stats__v ${change >= 0 ? "pos" : "neg"}">${formatPercent(change)}</span></div>
      <div><span class="fd-stats__k">Rows</span><span class="fd-stats__v">${rows.length}</span></div>
      <div><span class="fd-stats__k">Source</span><span class="fd-stats__v">Eastmoney</span></div>`;

    const chart = document.querySelector(".fd-chart");
    const chartRows = orderedRows.filter((_, index) => index % Math.max(1, Math.ceil(orderedRows.length / 80)) === 0);
    const values = chartRows.map((item) => numberValue(pick(item, ["close", "unit_net_value", "收盘", "单位净值"], 0)));
    if (chart && values.length > 1) {
      const width = 900;
      const height = 240;
      const pad = 24;
      const min = Math.min(...values);
      const max = Math.max(...values);
      const range = max - min || 1;
      const points = values.map((value, index) => {
        const x = pad + index * ((width - pad * 2) / Math.max(values.length - 1, 1));
        const y = height - pad - ((value - min) / range) * (height - pad * 2);
        return `${x},${y}`;
      }).join(" ");
      chart.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="历史净值曲线" preserveAspectRatio="none">
        <defs><linearGradient id="nav-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#81ecff" stop-opacity=".3"/><stop offset="1" stop-color="#81ecff" stop-opacity="0"/></linearGradient></defs>
        <polygon points="${pad},${height - pad} ${points} ${width - pad},${height - pad}" fill="url(#nav-fill)"/>
        <polyline points="${points}" fill="none" stroke="#81ecff" stroke-width="3" vector-effect="non-scaling-stroke"/>
      </svg>`;
    }
  }

  async function loadFundDetail() {
    const page = document.querySelector("[data-fund-page]");
    if (!page) return;

    setStatus("[data-api-status='fund']", "Connecting to fund backend...");
    const title = document.querySelector("[data-fund-title]");
    const ticker = document.querySelector("[data-fund-ticker]");
    const nav = document.querySelector("[data-fund-nav]");
    const change = document.querySelector("[data-fund-change]");
    if (title) title.textContent = "沪深300ETF华泰柏瑞";
    if (ticker) ticker.textContent = DEFAULT_FUND_CODE;
    if (nav) nav.textContent = "--";
    if (change) change.textContent = "--";

    let spotLoaded = false;
    let histLoaded = false;
    const spotTask = api.publicFund
      .getOneRealTime({ platform: "eastmoney", symbol: "ETF", code: DEFAULT_FUND_CODE })
      .then((spotRows) => {
        if (Array.isArray(spotRows) && spotRows[0]) {
          renderFundHeader(spotRows[0]);
          spotLoaded = true;
        }
      });
    const histTask = api.publicFund
      .getHist({
          platform: "eastmoney",
          symbol: "ETF",
          code: DEFAULT_FUND_CODE,
          start_date: "20240101",
          end_date: "20261231",
          period: "daily",
          adjust: "",
        })
      .then((histRows) => {
        if (Array.isArray(histRows) && histRows.length) {
          renderFundHist(histRows);
          histLoaded = true;
        }
      });

    const results = await Promise.allSettled([spotTask, histTask]);
    const errors = results.filter((item) => item.status === "rejected").map((item) => item.reason?.message).filter(Boolean);
    const loaded = Number(spotLoaded) + Number(histLoaded);
    setStatus(
      "[data-api-status='fund']",
      loaded ? `ETF data · ${loaded}/2 sources loaded` : `Fund data unavailable${errors.length ? `: ${errors[0]}` : ""}`,
      loaded === 0
    );
  }

  document.addEventListener("DOMContentLoaded", () => {
    loadMarketHub();
    loadNewsFeed();
    loadFundDetail();
  });
})(window, document);
