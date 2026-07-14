(function (window, document) {
  "use strict";

  const api = window.FundMasterAPI;
  if (!api) return;

  const NEWS_SYMBOL_STORAGE_KEY = "fundmaster.news.symbol";
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

  function normalizeStockSymbol(value) {
    const symbol = text(value, "").trim();
    return /^\d{6}$/.test(symbol) ? symbol : "";
  }

  function savedNewsSymbol() {
    const querySymbol = normalizeStockSymbol(new URLSearchParams(window.location.search).get("symbol"));
    if (querySymbol) return querySymbol;
    try {
      return normalizeStockSymbol(window.localStorage.getItem(NEWS_SYMBOL_STORAGE_KEY));
    } catch (error) {
      return "";
    }
  }

  function saveNewsSymbol(symbol) {
    try {
      window.localStorage.setItem(NEWS_SYMBOL_STORAGE_KEY, symbol);
    } catch (error) {
      // URL state still keeps the selected symbol usable when storage is blocked.
    }
    const url = new URL(window.location.href);
    url.searchParams.set("symbol", symbol);
    window.history.replaceState({}, "", url);
  }

  function newsCard(item, index, signal = {}, relatedSymbol = "") {
    const title = pick(item, ["news_title", "新闻标题", "标题", "title"], "Untitled market update");
    const body = pick(item, ["news_content", "新闻内容", "内容", "摘要", "summary"], "");
    const source = pick(item, ["文章来源", "来源", "source"], "MARKET NEWS");
    const time = pick(item, ["publish_time", "发布时间", "时间", "date"], "");
    const url = pick(item, ["新闻链接", "链接", "url"], "#");
    const hot = index === 0;
    const sentiment = text(signal.sentiment, "neutral").toLowerCase();
    const sentimentClass = sentiment === "positive" ? "bull" : sentiment === "negative" ? "bear" : "neutral";
    const sentimentLabel = sentiment === "positive" ? "BULLISH" : sentiment === "negative" ? "BEARISH" : "NEUTRAL";
    const related = normalizeStockSymbol(relatedSymbol);

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
        <span class="sentiment-pill sentiment-pill--${sentimentClass}"><span class="sentiment-pill__dot"></span>${sentimentLabel}${signal.risk_event ? " · RISK EVENT" : ""}</span>
        <span class="news-card__related">Related: ${escapeHtml(related)}</span>
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

  function newsMatchesFilter(item, signal, filter) {
    if (filter === "all") return true;
    const content = `${newsTitle(item)} ${newsBody(item)}`.toLowerCase();
    if (filter === "breaking") {
      return Boolean(signal?.risk_event)
        || /breaking|latest|alert|risk|regulat|policy|fed|cpi|突发|最新|风险|监管|政策|加息|降息/.test(content);
    }
    if (filter === "earnings") {
      return /earnings|revenue|profit|eps|guidance|财报|业绩|利润|营收|盈利|指引/.test(content);
    }
    return true;
  }

  function renderNewsList(feed, items, analysis, relatedSymbol, filter = "all") {
    const signals = Array.isArray(analysis?.item_signals) ? analysis.item_signals : [];
    const signalByTitle = new Map(signals.map((item) => [text(item.title, ""), item]));
    const rows = items
      .map((item, index) => ({
        item,
        index,
        signal: signalByTitle.get(newsTitle(item)) || signals[index] || {},
      }))
      .filter((entry) => newsMatchesFilter(entry.item, entry.signal, filter));

    if (!rows.length) {
      feed.innerHTML = `<p class="muted">No ${escapeHtml(filter)} news matched the current live feed.</p>`;
      return 0;
    }

    feed.innerHTML = rows
      .map((entry, visibleIndex) => newsCard(entry.item, visibleIndex, entry.signal, relatedSymbol))
      .join("");
    return rows.length;
  }

  function setupNewsFilters(feed, items, analysis, relatedSymbol) {
    const buttons = Array.from(document.querySelectorAll("#news .pill-group .pill"));
    if (!buttons.length) return;

    const applyFilter = (button) => {
      const filter = text(button.dataset.newsFilter || button.textContent, "all").trim().toLowerCase();
      buttons.forEach((item) => item.classList.add("pill--ghost"));
      button.classList.remove("pill--ghost");
      const count = renderNewsList(feed, items, analysis, relatedSymbol, filter);
      setStatus("[data-api-status='news']", `Live terminal · ${count} ${filter} news · AI ${analysis ? "ready" : "unavailable"}`, !analysis);
    };

    buttons.forEach((button) => {
      button.dataset.newsFilter = text(button.dataset.newsFilter || button.textContent, "all").trim().toLowerCase();
      button.onclick = () => applyFilter(button);
    });

    const active = buttons.find((button) => !button.classList.contains("pill--ghost")) || buttons[0];
    if (active) applyFilter(active);
  }

  function sectorFromNews(item) {
    const content = `${newsTitle(item)} ${newsBody(item)}`.toLowerCase();
    if (/nvda|chip|semiconductor|ai|cloud|software|data center|technology|tech|芯片|半导体|人工智能|科技/.test(content)) return "TECHNOLOGY";
    if (/oil|crude|energy|gas|opec|eia|能源|原油|石油|天然气/.test(content)) return "ENERGY";
    if (/fed|rate|bank|yield|treasury|credit|loan|inflation|cpi|financial|金融|银行|利率|通胀|债券/.test(content)) return "FINANCIALS";
    if (/health|pharma|biotech|drug|medical|healthcare|医药|医疗|生物/.test(content)) return "HEALTHCARE";
    return "MARKET NEWS";
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

  function signalScore(signal, item) {
    const label = text(signal?.sentiment || signal?.sentiment_label || "", "").toLowerCase();
    if (label === "positive" || label === "bullish") return 1;
    if (label === "negative" || label === "bearish") return -1;
    if (label === "neutral" || label === "mixed") return 0;
    return fallbackNewsScore(item);
  }

  function renderNewsSectorSentiment(items, analysis) {
    const signals = Array.isArray(analysis?.item_signals) ? analysis.item_signals : [];
    const signalByTitle = new Map(signals.map((item) => [text(item.title, ""), item]));
    const buckets = new Map();

    items.forEach((item, index) => {
      const sector = sectorFromNews(item);
      const signal = signalByTitle.get(newsTitle(item)) || signals[index] || {};
      const score = signalScore(signal, item);
      const normalizedScore = Number.isFinite(score) ? score : 0;
      const current = buckets.get(sector) || { name: sector, total: 0, count: 0 };
      current.total += normalizedScore;
      current.count += 1;
      buckets.set(sector, current);
    });

    const rows = Array.from(buckets.values())
      .map((bucket) => ({ name: bucket.name, score: bucket.count ? bucket.total / bucket.count : null }))
      .sort((a, b) => Math.abs(b.score || 0) - Math.abs(a.score || 0));

    renderSectorSentiment(rows);
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

  async function loadNewsFeed(symbol) {
    const feed = document.querySelector("[data-news-feed]");
    if (!feed) return;

    const selectedSymbol = normalizeStockSymbol(symbol);
    if (!selectedSymbol) {
      feed.innerHTML = '<div class="data-loading-state">Enter a valid six-digit A-share code above.</div>';
      renderSectorSentiment([]);
      renderAiSummary([], null);
      setStatus("[data-api-status='news']", "Choose an A-share code to load verified news.");
      return;
    }

    setStatus("[data-api-status='news']", `Loading verified news for ${selectedSymbol}...`);
    try {
      const rows = await api.news.getStockRecentNews({ symbol: selectedSymbol });
      const orderedRows = Array.isArray(rows)
        ? rows.slice().sort((left, right) => newsTimestamp(right) - newsTimestamp(left))
        : [];
      const list = orderedRows.slice(0, 6);
      let analysis = null;
      if (list.length && api.ai?.summarizeNews) {
        try {
          analysis = await api.ai.summarizeNews({
            symbol: selectedSymbol,
            items: orderedRows,
            max_items: 10,
          });
        } catch (error) {
          console.warn("News AI summary unavailable:", error.message);
        }
      }
      if (list.length) {
        renderNewsList(feed, list, analysis, selectedSymbol, "all");
        setupNewsFilters(feed, list, analysis, selectedSymbol);
        renderNewsSectorSentiment(list, analysis);
      } else {
        feed.innerHTML = '<p class="muted">No live news returned from backend.</p>';
        renderSectorSentiment([]);
      }
      renderAiSummary(list, analysis);
      setStatus("[data-api-status='news']", `${selectedSymbol} · ${list.length} recent news · AI ${analysis ? "ready" : "unavailable"}`, !analysis);
    } catch (error) {
      feed.innerHTML = '<p class="muted">News backend unavailable.</p>';
      renderSectorSentiment([]);
      renderAiSummary([], null);
      setStatus("[data-api-status='news']", `${selectedSymbol} news unavailable: ${error.message}`, true);
    }
  }

  function initNewsFeed() {
    const form = document.querySelector("[data-news-symbol-form]");
    const input = document.querySelector("[data-news-symbol-input]");
    if (!form || !input) return;

    const initialSymbol = savedNewsSymbol();
    if (initialSymbol) {
      input.value = initialSymbol;
      loadNewsFeed(initialSymbol);
    } else {
      loadNewsFeed("");
    }

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const symbol = normalizeStockSymbol(input.value);
      if (!symbol) {
        input.setAttribute("aria-invalid", "true");
        setStatus("[data-api-status='news']", "Enter a valid six-digit A-share stock code.", true);
        return;
      }
      input.removeAttribute("aria-invalid");
      saveNewsSymbol(symbol);
      loadNewsFeed(symbol);
    });
  }

  function sentimentLabel(score) {
    if (score >= 0.55) return "EXTREME GREED";
    if (score >= 0.18) return "BULLISH";
    if (score <= -0.35) return "FEAR";
    if (score <= -0.12) return "CAUTIOUS";
    return "NEUTRAL";
  }

  function sentimentClass(score) {
    if (score >= 0.18) return "sector-tile--greed";
    if (score <= -0.12) return "sector-tile--fear";
    return "sector-tile--neutral";
  }

  function formatScore(score) {
    if (!Number.isFinite(score)) return "--";
    const value = score;
    return `${value > 0 ? "+" : ""}${value.toFixed(2)}`;
  }

  function averageChange(rows, field = "change_1y") {
    const valid = rows
      .map((item) => pick(item, [field], undefined))
      .filter((value) => value !== undefined && value !== null && value !== "")
      .map(numberValue)
      .filter(Number.isFinite);
    if (!valid.length) return null;
    return valid.reduce((sum, value) => sum + value, 0) / valid.length;
  }

  function renderSectorSentiment(items) {
    const grid = document.querySelector(".sector-grid");
    if (!grid) return;
    const validItems = items.filter((item) => Number.isFinite(item.score));
    if (!validItems.length) {
      grid.innerHTML = '<p class="muted">No backend sentiment inputs returned.</p>';
      const valueNode = document.querySelector(".gauge__value");
      const marker = document.querySelector(".gauge__marker");
      const track = document.querySelector(".gauge__track");
      if (valueNode) valueNode.textContent = "-- / No data";
      if (marker) marker.style.left = "50%";
      if (track) track.setAttribute("aria-label", "No backend sentiment data returned");
      return;
    }
    grid.innerHTML = validItems.slice(0, 4).map((item) => {
      const score = Math.max(-1, Math.min(1, item.score));
      return `<div class="sector-tile ${sentimentClass(score)}">
        <p class="sector-tile__name">${escapeHtml(item.name)}</p>
        <p class="sector-tile__score ${score < 0 ? "sector-tile__score--neg" : score < 0.18 ? "sector-tile__score--amber" : ""}">${formatScore(score)}</p>
        <p class="sector-tile__mood">${sentimentLabel(score)}</p>
      </div>`;
    }).join("");
    const aggregate = validItems.reduce((sum, item) => sum + item.score, 0) / validItems.length;
    const gaugeValue = Math.max(0, Math.min(100, Math.round(50 + aggregate * 50)));
    const gaugeLabel = gaugeValue >= 60 ? "Greed" : gaugeValue <= 40 ? "Fear" : "Neutral";
    const valueNode = document.querySelector(".gauge__value");
    const marker = document.querySelector(".gauge__marker");
    const track = document.querySelector(".gauge__track");
    if (valueNode) valueNode.textContent = `${gaugeValue} / ${gaugeLabel}`;
    if (marker) marker.style.left = `${gaugeValue}%`;
    if (track) track.setAttribute("aria-label", `Aggregate sentiment ${gaugeValue}, ${gaugeLabel}`);
  }

  function latestMacroRow(rows) {
    if (!Array.isArray(rows) || !rows.length) return null;
    return rows.slice().sort((a, b) => {
      const ad = Date.parse(pick(a, ["date", "month", "月份", "统计时间"], ""));
      const bd = Date.parse(pick(b, ["date", "month", "月份", "统计时间"], ""));
      return (Number.isNaN(bd) ? 0 : bd) - (Number.isNaN(ad) ? 0 : ad);
    })[0];
  }

  function renderMacroCalendar(rows) {
    const header = document.querySelector(".cal-header__date");
    const list = document.querySelector(".cal-list");
    if (!list) return;
    if (header) header.textContent = "Latest macro data";
    const visible = rows.filter((item) => item && item.row).slice(0, 3);
    if (!visible.length) {
      list.innerHTML = '<li class="cal-row"><div class="cal-row__main"><div class="cal-row__info"><span class="cal-row__title">No macro data returned</span></div></div></li>';
      return;
    }
    list.innerHTML = visible.map((item, index) => {
      const date = pick(item.row, ["date", "month", "月份", "统计时间"], "Latest");
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
    const needsSentiment = document.querySelector(".sector-grid");
    const needsMacro = document.querySelector(".cal-list");
    if (!needsSentiment && !needsMacro) return;
    const newsPageOwnsSentiment = Boolean(document.querySelector("[data-news-feed]"));

    const [equityRank, debtRank, globalQuotes, cpiData, pmiData, oilData] = await Promise.allSettled([
      api.publicFund.getRank({ fund_type: "stock" }),
      api.publicFund.getRank({ fund_type: "bond" }),
      api.global.getIndexQuotesFromList(["^IXIC", "^GSPC", "^HSI"]),
      api.macro.getData({ country: "usa", indicator: "core_cpi_monthly" }),
      api.macro.getData({ country: "china", indicator: "pmi" }),
      api.macro.getData({ country: "usa", indicator: "eia_crude_rate" }),
    ]);

    const equityRows = equityRank.status === "fulfilled" && Array.isArray(equityRank.value) ? equityRank.value : [];
    const debtRows = debtRank.status === "fulfilled" && Array.isArray(debtRank.value) ? debtRank.value : [];
    const quoteRows = globalQuotes.status === "fulfilled" && Array.isArray(globalQuotes.value) ? globalQuotes.value : [];
    const equityChange = averageChange(equityRows, "change_1m");
    const debtChange = averageChange(debtRows, "change_1m");
    const indexChange = averageChange(quoteRows, "change_pct");
    const breadthValues = equityRows
      .map((item) => pick(item, ["daily_growth_rate"], undefined))
      .filter((value) => value !== undefined && value !== null && value !== "")
      .map(numberValue);
    if (!newsPageOwnsSentiment) {
      renderSectorSentiment([
        { name: "EQUITY FUNDS", score: equityChange === null ? null : equityChange / 10 },
        { name: "BOND FUNDS", score: debtChange === null ? null : debtChange / 5 },
        { name: "GLOBAL INDEX", score: indexChange === null ? null : indexChange / 3 },
        { name: "FUND BREADTH", score: breadthValues.length ? breadthValues.filter((value) => value > 0).length / breadthValues.length * 2 - 1 : null },
      ]);
    }

    const cpi = cpiData.status === "fulfilled" ? latestMacroRow(cpiData.value) : null;
    const pmi = pmiData.status === "fulfilled" ? latestMacroRow(pmiData.value) : null;
    const oil = oilData.status === "fulfilled" ? latestMacroRow(oilData.value) : null;
    renderMacroCalendar([
      { title: "US Core CPI (MoM)", row: cpi, actual: pick(cpi, ["value", "core_cpi_monthly", "核心CPI月率", "actual"], "--"), importance: 3 },
      { title: "China Manufacturing PMI", row: pmi, actual: pick(pmi, ["manufacturing_index", "制造业-指数", "value"], "--"), importance: 2 },
      { title: "US EIA Crude Inventory", row: oil, actual: pick(oil, ["value", "eia_crude_rate", "库存", "actual"], "--"), importance: 2 },
    ]);
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
    initNewsFeed();
    loadFundDetail();
    loadHomeSidebars();
  });
})(window, document);
