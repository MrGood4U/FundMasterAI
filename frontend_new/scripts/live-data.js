(function (window, document) {
  "use strict";

  const api = window.FundMasterAPI;
  if (!api) return;

  const NEWS_LEADER_BASKET = [
    { symbol: "600036", sector: "FINANCIALS" },
    { symbol: "600519", sector: "CONSUMER" },
    { symbol: "300750", sector: "NEW ENERGY" },
    { symbol: "600030", sector: "BROKERAGE" },
    { symbol: "601857", sector: "ENERGY" },
    { symbol: "600276", sector: "HEALTHCARE" },
  ];
  const NEWS_CACHE_KEY = "fundmaster:news-feed:v1";
  const NEWS_CACHE_VERSION = 1;
  const NEWS_CACHE_TTL_MS = 5 * 60 * 1000;
  const NEWS_BASKET_KEY = NEWS_LEADER_BASKET.map((leader) => `${leader.symbol}:${leader.sector}`).join("|");
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

  function booleanValue(value) {
    if (typeof value === "boolean") return value;
    if (typeof value === "number") return value === 1;
    return String(value || "").trim().toLowerCase() === "true";
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
      const tickers = ["^GSPC", "^IXIC", "^FTSE", "^N225"];
      const rows = await api.global.getIndexQuotesFromList(tickers);
      const batchQuotes = Array.isArray(rows) ? rows : [];
      const batchByTicker = new Map(
        batchQuotes
          .map((item) => [String(pick(item, ["ticker", "symbol"], "")).toUpperCase(), item])
          .filter(([ticker]) => ticker)
      );

      // The batch endpoint normally contains every requested quote. Only call
      // the slower detail endpoint for genuinely missing tickers instead of
      // blocking the whole page on four redundant upstream requests.
      const missingTickers = tickers.filter((ticker) => !batchByTicker.has(ticker));
      const detailResults = await Promise.allSettled(
        missingTickers.map((ticker) => api.global.getIndexInfo(ticker))
      );
      const detailByTicker = new Map();
      missingTickers.forEach((ticker, index) => {
        const result = detailResults[index];
        if (result?.status === "fulfilled" && result.value) detailByTicker.set(ticker, result.value);
      });
      const quotes = tickers
        .map((ticker, index) => batchByTicker.get(ticker) || detailByTicker.get(ticker) || batchQuotes[index] || null)
        .filter(Boolean);
      if (!quotes.length) {
        document.querySelectorAll(".mh-indices .mh-index").forEach((card) => {
          const price = card.querySelector(".mh-index__v");
          const percent = card.querySelector(".mh-index__p");
          if (price) price.textContent = "--";
          if (percent) percent.textContent = "--";
        });
        const heat = document.querySelector("[data-market-heat]");
        const movers = document.querySelector("[data-market-movers]");
        const coverage = document.querySelector(".mh-sectors");
        const clock = document.querySelector(".mh-clock__time");
        if (heat) heat.innerHTML = '<p class="muted">No global index data returned.</p>';
        if (movers) movers.innerHTML = '<p class="muted">No mover data returned.</p>';
        if (coverage) coverage.innerHTML = '<span>No verified index coverage returned</span>';
        if (clock) clock.textContent = "Unavailable";
        setStatus("[data-api-status='market']", "Global index APIs returned no data", true);
        return;
      }
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
          percent.classList.remove("muted");
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
      const legend = document.querySelector(".mh-legend__vol");
      const coverage = document.querySelector(".mh-sectors");
      const clock = document.querySelector(".mh-clock__time");
      if (legend) legend.textContent = `${quotes.length} live quotes`;
      if (coverage) coverage.innerHTML = `<span>${quotes.length} verified indices</span><span>Not a stock-level heatmap</span>`;
      if (clock) clock.textContent = "Live";
      setStatus(
        "[data-api-status='market']",
        `Global index API live · ${quotes.length} quotes`,
        false
      );
    } catch (error) {
      document.querySelectorAll(".mh-indices .mh-index").forEach((card) => {
        const price = card.querySelector(".mh-index__v");
        const percent = card.querySelector(".mh-index__p");
        if (price) price.textContent = "--";
        if (percent) {
          percent.textContent = "Unavailable";
          percent.className = "mh-index__p muted";
        }
      });
      const heat = document.querySelector("[data-market-heat]");
      const movers = document.querySelector("[data-market-movers]");
      const clock = document.querySelector(".mh-clock__time");
      if (heat) heat.innerHTML = '<div class="data-loading-state">Global index data is unavailable.</div>';
      if (movers) movers.innerHTML = '<div class="data-loading-state data-loading-state--compact">No verified index movers available.</div>';
      if (clock) clock.textContent = "Unavailable";
      setStatus("[data-api-status='market']", `Market backend unavailable: ${error.message}`, true);
    }
  }

  function newsSymbols(item) {
    return Array.isArray(item?.source_symbols)
      ? item.source_symbols.filter((symbol) => /^\d{6}$/.test(String(symbol)))
      : [];
  }

  function readNewsCache() {
    try {
      const raw = window.sessionStorage.getItem(NEWS_CACHE_KEY);
      if (!raw) return null;
      const cached = JSON.parse(raw);
      if (
        cached?.version !== NEWS_CACHE_VERSION
        || cached?.basketKey !== NEWS_BASKET_KEY
        || !Array.isArray(cached?.items)
        || !Number.isFinite(Number(cached?.updatedAt))
      ) {
        return null;
      }
      return cached;
    } catch (error) {
      console.warn("News cache is unavailable:", error.message);
      return null;
    }
  }

  function writeNewsCache(payload) {
    try {
      window.sessionStorage.setItem(NEWS_CACHE_KEY, JSON.stringify({
        ...payload,
        version: NEWS_CACHE_VERSION,
        basketKey: NEWS_BASKET_KEY,
      }));
    } catch (error) {
      console.warn("News cache could not be updated:", error.message);
    }
  }

  function newsCacheIsFresh(cached) {
    const age = Date.now() - Number(cached?.updatedAt);
    return Number.isFinite(age) && age >= 0 && age < NEWS_CACHE_TTL_MS;
  }

  function newsKey(item) {
    return text(pick(item, ["新闻链接", "链接", "url"], ""), "")
      || `${newsTitle(item)}|${newsTimestamp(item)}`;
  }

  function mergeLeaderNews(results) {
    const merged = new Map();
    NEWS_LEADER_BASKET.forEach((leader, index) => {
      const result = results[index];
      const rows = result?.status === "fulfilled" && Array.isArray(result.value) ? result.value : [];
      rows.forEach((item) => {
        const key = newsKey(item);
        const existing = merged.get(key);
        if (existing) {
          if (!existing.source_symbols.includes(leader.symbol)) existing.source_symbols.push(leader.symbol);
          if (!existing.source_sectors.includes(leader.sector)) existing.source_sectors.push(leader.sector);
          return;
        }
        merged.set(key, {
          ...item,
          source_symbols: [leader.symbol],
          source_sectors: [leader.sector],
        });
      });
    });
    return Array.from(merged.values());
  }

  function newsCard(item, index, signal = {}) {
    const title = pick(item, ["news_title", "新闻标题", "标题", "title"], "Untitled market update");
    const body = pick(item, ["news_content", "新闻内容", "内容", "摘要", "summary"], "");
    const source = pick(item, ["文章来源", "来源", "source"], "MARKET NEWS");
    const time = pick(item, ["publish_time", "发布时间", "时间", "date"], "");
    const url = pick(item, ["新闻链接", "链接", "url"], "#");
    const hot = index === 0;
    const sentiment = text(signal.sentiment, "neutral").toLowerCase();
    const sentimentClass = sentiment === "positive" ? "bull" : sentiment === "negative" ? "bear" : "neutral";
    const sentimentLabel = sentiment === "positive" ? "BULLISH" : sentiment === "negative" ? "BEARISH" : "NEUTRAL";
    const related = newsSymbols(item).join(", ");

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
        <span class="sentiment-pill sentiment-pill--${sentimentClass}"><span class="sentiment-pill__dot"></span>${sentimentLabel}${booleanValue(signal.risk_event) ? " · RISK EVENT" : ""}</span>
        ${related ? `<span class="news-card__related">Related: ${escapeHtml(related)}</span>` : ""}
      </div>
    </article>`;
  }

  function newsTitle(item) {
    return text(pick(item, ["news_title", "新闻标题", "标题", "title"], ""), "");
  }

  function newsBody(item) {
    return text(pick(item, ["news_content", "新闻内容", "内容", "摘要", "summary"], ""), "");
  }

  function newsTimestamp(item) {
    const raw = text(pick(item, ["publish_time", "发布时间", "时间", "date"], ""), "").trim();
    if (!raw) return Number.NEGATIVE_INFINITY;
    const normalized = raw.replace(/^(\d{4}-\d{2}-\d{2})\s+/, "$1T");
    const timestamp = Date.parse(normalized);
    return Number.isFinite(timestamp) ? timestamp : Number.NEGATIVE_INFINITY;
  }

  function newsCategory(item, signal) {
    const content = `${newsTitle(item)} ${newsBody(item)}`.toLowerCase();
    const isRisk = booleanValue(signal?.risk_event)
      || /breaking|latest|alert|risk|regulat|policy|fed|cpi|突发|最新|风险|监管|政策|加息|降息/.test(content);
    if (isRisk) return "risk";
    if (/earnings|revenue|profit|eps|guidance|财报|业绩|利润|营收|盈利|指引/.test(content)) return "earnings";
    return "other";
  }

  function newsFilterLabel(filter) {
    if (filter === "risk") return "Risk & Policy";
    if (filter === "earnings") return "Earnings";
    if (filter === "other") return "Other";
    return "All";
  }

  function newsEntries(items, analysis) {
    const signals = Array.isArray(analysis?.item_signals) ? analysis.item_signals : [];
    const signalByTitle = new Map(signals.map((item) => [text(item.title, ""), item]));
    return items.map((item, index) => {
      const signal = signalByTitle.get(newsTitle(item)) || signals[index] || {};
      return { item, index, signal, category: newsCategory(item, signal) };
    });
  }

  function renderNewsList(feed, items, analysis, filter = "all") {
    const rows = newsEntries(items, analysis)
      .filter((entry) => filter === "all" || entry.category === filter);

    if (!rows.length) {
      feed.innerHTML = `<p class="muted">No ${escapeHtml(newsFilterLabel(filter).toLowerCase())} news matched the current live feed.</p>`;
      return 0;
    }

    feed.innerHTML = rows
      .map((entry, visibleIndex) => newsCard(entry.item, visibleIndex, entry.signal))
      .join("");
    return rows.length;
  }

  function setupNewsFilters(feed, items, analysis, sourceLabel = "Live terminal") {
    const buttons = Array.from(document.querySelectorAll("#news .pill-group .pill"));
    if (!buttons.length) return;
    const counts = { all: items.length, risk: 0, earnings: 0, other: 0 };
    newsEntries(items, analysis).forEach((entry) => {
      counts[entry.category] += 1;
    });

    const applyFilter = (button) => {
      const filter = text(button.dataset.newsFilter, "all").trim().toLowerCase();
      const label = text(button.dataset.newsFilterLabel, newsFilterLabel(filter));
      buttons.forEach((item) => item.classList.add("pill--ghost"));
      button.classList.remove("pill--ghost");
      const count = renderNewsList(feed, items, analysis, filter);
      setStatus("[data-api-status='news']", `${sourceLabel} · ${count} ${label.toLowerCase()} news · AI ${analysis ? "ready" : "unavailable"}`, !analysis);
    };

    buttons.forEach((button) => {
      const filter = text(button.dataset.newsFilter, "all").trim().toLowerCase();
      const label = text(button.dataset.newsFilterLabel, newsFilterLabel(filter));
      button.textContent = `${label} ${counts[filter] ?? 0}`;
      button.onclick = () => applyFilter(button);
    });

    const active = buttons.find((button) => !button.classList.contains("pill--ghost")) || buttons[0];
    if (active) applyFilter(active);
  }

  function fallbackNewsScore(item) {
    const content = `${newsTitle(item)} ${newsBody(item)}`.toLowerCase();
    const positive = /beat|beats|surge|rally|gain|growth|record|upgrade|bullish|strong|shatters|利好|增长|上涨|突破|强劲/.test(content);
    const negative = /miss|fall|drop|plunge|risk|warning|cut|bearish|restrictive|inflation|concern|压力|下跌|风险|警告|收紧/.test(content);
    if (positive && !negative) return 1;
    if (negative && !positive) return -1;
    if (positive && negative) return 0;
    return null;
  }

  function renderAiSummary(items, analysis) {
    const summary = document.querySelector(".panel--ai .ai-copy");
    if (!summary) return;

    if (analysis) {
      summary.textContent = analysis.summary || "No AI summary returned.";
      return;
    }

    if (!items.length) {
      summary.textContent = "No live news returned from the backend, so no signal summary is available.";
      return;
    }

    const positive = items.filter((item) => fallbackNewsScore(item) === 1).length;
    const negative = items.filter((item) => fallbackNewsScore(item) === -1).length;
    const neutral = Math.max(0, items.length - positive - negative);
    const topTitle = newsTitle(items[0]) || "latest headline";
    const tone = positive > negative ? "positive" : negative > positive ? "negative" : "mixed";
    summary.textContent = `Live news fallback summary: ${items.length} headline(s) loaded. Tone is ${tone} (${positive} positive / ${negative} negative / ${neutral} neutral). Latest: ${topTitle}`;
  }

  function renderNewsPayload(feed, payload, mode = "live") {
    const list = Array.isArray(payload?.items) ? payload.items.slice(0, 6) : [];
    const analysis = payload?.analysis || null;
    const successfulSources = Number(payload?.successfulSources) || 0;
    const sourceLabel = mode === "cached" ? "Cached terminal" : "Live terminal";

    if (list.length) {
      renderNewsList(feed, list, analysis, "all");
      setupNewsFilters(feed, list, analysis, sourceLabel);
    } else {
      feed.innerHTML = '<p class="muted">No live news returned from backend.</p>';
    }
    renderAiSummary(list, analysis);
    setStatus(
      "[data-api-status='news']",
      `${mode === "cached" ? "Cached sector leaders" : "Sector leaders"} · ${successfulSources}/${NEWS_LEADER_BASKET.length} sources · ${list.length} news · AI ${analysis ? "ready" : "unavailable"}`,
      successfulSources === 0
    );
  }

  async function refreshNewsFeed(feed, hasCachedFeed = false) {
    try {
      const results = await Promise.allSettled(
        NEWS_LEADER_BASKET.map((leader) => api.news.getStockRecentNews({ symbol: leader.symbol }))
      );
      const successfulSources = results.filter((result) => result.status === "fulfilled" && Array.isArray(result.value)).length;
      const orderedRows = mergeLeaderNews(results)
        .sort((left, right) => newsTimestamp(right) - newsTimestamp(left));
      const list = orderedRows.slice(0, 6);
      let analysis = null;
      if (list.length && api.ai?.summarizeNews) {
        try {
          analysis = await api.ai.summarizeNews({
            items: list,
            max_items: list.length,
          });
        } catch (error) {
          console.warn("News AI summary unavailable:", error.message);
        }
      }

      if (!list.length && hasCachedFeed) {
        setStatus("[data-api-status='news']", "Cached sector-leader news retained · live refresh returned no news", true);
        return;
      }

      const payload = {
        items: list,
        analysis,
        successfulSources,
        updatedAt: Date.now(),
      };
      renderNewsPayload(feed, payload, "live");
      if (list.length) writeNewsCache(payload);
    } catch (error) {
      if (hasCachedFeed) {
        setStatus("[data-api-status='news']", `Cached sector-leader news retained · refresh unavailable: ${error.message}`, true);
        return;
      }
      feed.innerHTML = '<p class="muted">News backend unavailable.</p>';
      renderAiSummary([], null);
      setStatus("[data-api-status='news']", `News backend unavailable: ${error.message}`, true);
    }
  }

  async function loadNewsFeed() {
    const feed = document.querySelector("[data-news-feed]");
    if (!feed) return;

    const cached = readNewsCache();
    if (cached) {
      renderNewsPayload(feed, cached, "cached");
      if (newsCacheIsFresh(cached)) return;
      setStatus("[data-api-status='news']", "Cached sector-leader news shown · refreshing stale data...");
      await refreshNewsFeed(feed, true);
      return;
    }

    setStatus("[data-api-status='news']", "Loading verified sector-leader news...");
    await refreshNewsFeed(feed, false);
  }

  function latestMacroRow(rows) {
    if (!Array.isArray(rows) || !rows.length) return null;
    return rows.slice().sort((a, b) => {
      const macroDateRank = (row) => {
        const raw = text(pick(row, ["date", "month", "quarter", "月份", "季度", "统计时间"], ""), "");
        const parsed = Date.parse(raw);
        if (!Number.isNaN(parsed)) return parsed;
        const parts = raw.match(/(\d{4})\D*(\d{1,2})?/);
        if (!parts) return 0;
        const year = Number(parts[1]);
        const period = Number(parts[2] || 1);
        return year * 100 + period;
      };
      return macroDateRank(b) - macroDateRank(a);
    })[0];
  }

  function macroActual(row, keys, suffix = "") {
    const value = pick(row, keys, null);
    if (value === null || value === undefined || value === "") return "--";
    const rendered = text(value);
    return suffix && !rendered.includes(suffix) ? `${rendered}${suffix}` : rendered;
  }

  function renderMacroCalendar(rows) {
    const header = document.querySelector(".cal-header__date");
    const list = document.querySelector(".cal-list");
    if (!list) return;
    if (header) header.textContent = "Latest released data";
    const visible = rows.filter((item) => item && item.row).slice(0, 4);
    if (!visible.length) {
      list.innerHTML = '<li class="cal-row"><div class="cal-row__main"><div class="cal-row__info"><span class="cal-row__title">No macro data returned</span></div></div></li>';
      return;
    }
    list.innerHTML = visible.map((item, index) => {
      const date = pick(item.row, ["date", "month", "quarter", "月份", "季度", "统计时间"], "Latest");
      return `<li class="cal-row ${index ? "cal-row--border" : ""}">
        <div class="cal-row__main">
          <time class="cal-time">${escapeHtml(text(date).slice(0, 10))}</time>
          <div class="cal-row__info">
            <span class="cal-row__title">${escapeHtml(item.title)}</span>
            <span class="cal-row__bars ${item.importance < 3 ? "cal-row__bars--short" : ""}" aria-hidden="true">${"▮".repeat(item.importance)}</span>
          </div>
        </div>
        <div class="cal-row__nums">
          <span>Actual: ${escapeHtml(text(item.actual))}</span>
          <span>Source: Backend</span>
        </div>
      </li>`;
    }).join("");
  }

  async function loadHomeSidebars() {
    const needsMacro = document.querySelector(".cal-list");
    if (!needsMacro) return;

    const candidates = [
      { indicator: "pmi", title: "China Manufacturing PMI", keys: ["manufacturing_index", "制造业-指数", "value"], suffix: "", importance: 3 },
      { indicator: "cpi", title: "China CPI (YoY)", keys: ["national_yoy", "全国-同比增长", "value"], suffix: "%", importance: 3 },
      { indicator: "ppi", title: "China PPI (YoY)", keys: ["ppi_yoy", "当月-同比增长", "value"], suffix: "%", importance: 2 },
      { indicator: "money_supply", title: "China M2 (YoY)", keys: ["m2_yoy", "货币和准货币(M2)-同比增长", "value"], suffix: "%", importance: 2 },
      { indicator: "lpr", title: "China 1Y LPR", keys: ["lpr_1y", "1年期", "value"], suffix: "%", importance: 2 },
      { indicator: "gdp", title: "China GDP (YoY)", keys: ["gdp_yoy", "国内生产总值-同比增长", "value"], suffix: "%", importance: 3 },
    ];
    const results = await Promise.allSettled(
      candidates.map((item) => api.macro.getData({ country: "china", indicator: item.indicator }))
    );
    const observations = candidates.map((item, index) => {
      const result = results[index];
      const row = result.status === "fulfilled" ? latestMacroRow(result.value) : null;
      return {
        title: item.title,
        row,
        actual: macroActual(row, item.keys, item.suffix),
        importance: item.importance,
      };
    });
    renderMacroCalendar(observations);
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
    loadHomeSidebars();
  });
})(window, document);
