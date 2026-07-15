(function (window) {
  "use strict";

  const config = {
    marketBaseUrl: "",
    portfolioBaseUrl: "",
    aiBaseUrl: "",
    ...(window.FUNDMASTER_API_CONFIG || {}),
  };

  function joinUrl(baseUrl, path) {
    const base = String(baseUrl || "").replace(/\/$/, "");
    return `${base}${path}`;
  }

  function replaceNonFiniteJsonNumbers(text) {
    const source = String(text || "");
    const tokens = ["-Infinity", "Infinity", "NaN"];
    const isBoundary = (character) => character === undefined || /[\s,:\[\]{}]/.test(character);
    let result = "";
    let inString = false;
    let escaped = false;

    for (let index = 0; index < source.length; index += 1) {
      const character = source[index];
      if (inString) {
        result += character;
        if (escaped) {
          escaped = false;
        } else if (character === "\\") {
          escaped = true;
        } else if (character === '"') {
          inString = false;
        }
        continue;
      }

      if (character === '"') {
        inString = true;
        result += character;
        continue;
      }

      const token = tokens.find((candidate) => source.startsWith(candidate, index));
      if (
        token
        && isBoundary(source[index - 1])
        && isBoundary(source[index + token.length])
      ) {
        result += "null";
        index += token.length - 1;
      } else {
        result += character;
      }
    }

    return result;
  }

  async function request(baseUrl, path, options = {}) {
    const headers = new Headers(options.headers || {});
    const init = {
      method: options.method || "GET",
      headers,
    };

    if (options.body !== undefined) {
      headers.set("Content-Type", "application/json");
      init.body = JSON.stringify(options.body);
    }

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), options.timeout || 30000);
    init.signal = controller.signal;
    let response;
    try {
      response = await fetch(joinUrl(baseUrl, path), init);
    } catch (error) {
      throw new Error(error.name === "AbortError" ? `Request timed out: ${path}` : error.message);
    } finally {
      clearTimeout(timeout);
    }
    let payload = null;

    try {
      if (options.allowNonFiniteJsonNumbers) {
        const responseText = await response.text();
        payload = JSON.parse(replaceNonFiniteJsonNumbers(responseText));
      } else {
        payload = await response.json();
      }
    } catch (error) {
      payload = { message: response.statusText || "Invalid JSON response" };
    }

    if (!response.ok || (payload && payload.code && payload.code !== 200)) {
      throw new Error((payload && payload.message) || `HTTP ${response.status}`);
    }

    return payload && Object.prototype.hasOwnProperty.call(payload, "data") ? payload.data : payload;
  }

  const postMarket = (path, body = {}) => request(config.marketBaseUrl, path, { method: "POST", body });
  const publicFund = {
    getOneRealTime: (body = {}) => postMarket("/api/market/fund_public/real_time_get_one", body),
    getAllRealTime: (body = {}) => request(config.marketBaseUrl, "/api/market/fund_public/real_time_get_all", {
      method: "POST",
      body,
      timeout: 180000,
      allowNonFiniteJsonNumbers: true,
    }),
    getRank: (body = {}) => postMarket("/api/market/fund_public/rank", { order_by: "change_1y", ...body }),
    getHist: (body = {}) => postMarket("/api/market/fund_public/hist", body),
    getBasicInfo: (code) => postMarket("/api/market/fund_public/individual_basic_info", { code }),
    getDetailHold: (code, date) => postMarket("/api/market/fund_public/individual_detail_hold", { code, ...(date ? { date } : {}) }),
    getIndustryAllocation: (code, year) => postMarket("/api/market/fund_public/portfolio_industry_allocation", { code, ...(year ? { year } : {}) }),
    getStockHolds: (code, year) => postMarket("/api/market/fund_public/portfolio_hold_stock", { code, ...(year ? { year } : {}) }),
    getBondHolds: (code, year) => postMarket("/api/market/fund_public/portfolio_hold_bond", { code, ...(year ? { year } : {}) }),
  };

  window.FundMasterAPI = {
    config,
    market: {
      getFundNameList: () => request(config.marketBaseUrl, "/api/market/fund_public/fund_name_list"),
      getFundRank: (fundType = "all", orderBy = "change_1y") =>
        request(config.marketBaseUrl, "/api/market/fund_public/rank", {
          method: "POST",
          body: { fund_type: fundType, order_by: orderBy },
          allowNonFiniteJsonNumbers: true,
        }),
      getFundHist: (code, options = {}) =>
        request(config.marketBaseUrl, "/api/market/fund_public/hist", {
          method: "POST",
          body: {
            platform: options.platform || "eastmoney",
            symbol: options.symbol || "ETF",
            code,
            start_date: options.start_date || "20240101",
            end_date: options.end_date || "20261231",
            period: options.period || "daily",
            adjust: options.adjust || "",
          },
        }),

      getGlobalIndices: () => postMarket("/api/market/global/index/quotes", { tickers: ["^IXIC", "^GDAXI", "^HSI"] }),

      getGlobalMatrixData: () => postMarket("/api/market/global/index/rank", {}),
    },
    publicFund,
    global: {
      getIndexQuotesFromList: (tickers) => request(config.marketBaseUrl, "/api/market/global/index/quotes", { method: "POST", body: { tickers }, timeout: 90000 }),
      getIndexInfo: (ticker) => request(config.marketBaseUrl, "/api/market/global/index/info", { method: "POST", body: { ticker }, timeout: 60000 }),
      getIndexHist: (ticker, options = {}) => request(config.marketBaseUrl, "/api/market/global/index/hist", { method: "POST", body: { ticker, ...options }, timeout: 90000 }),
      getIndexRank: () => request(config.marketBaseUrl, "/api/market/global/index/rank", { method: "POST", body: {}, timeout: 90000 }),
      getIndexList: () => postMarket("/api/market/global/index/list", {}),
      getExchangeRate: (fromCurrency, toCurrency) => postMarket("/api/market/global/exchange_rate/rate", { from_currency: fromCurrency, to_currency: toCurrency }),
      getExchangeRateHistory: (fromCurrency, toCurrency, queryDate) => postMarket("/api/market/global/exchange_rate/history", { from_currency: fromCurrency, to_currency: toCurrency, query_date: queryDate }),
    },
    macro: {
      getCountries: () => postMarket("/api/market/macro/countries", {}),
      getIndicators: (country) => postMarket("/api/market/macro/indicators", country ? { country } : {}),
      getSchema: (country, indicator) => postMarket("/api/market/macro/schema", { country, indicator }),
      getData: (body) => postMarket("/api/market/macro/data", body),
    },
    news: {
      getStockRecentNews: (body) => request(config.marketBaseUrl, "/api/news/stock/get_recent_news", { method: "POST", body }),
    },
    
    portfolio: {
      createTransaction: (body) =>
        request(config.portfolioBaseUrl, "/api/portfolio/transaction/create", {
          method: "POST",
          body,
        }),
      listHoldings: () => request(config.portfolioBaseUrl, "/api/portfolio/holding/list?page=1&page_size=50"),
    },
    
    ai: {
      summarizeNews: (body) => request(config.aiBaseUrl, "/api/ai/news/summary", {
        method: "POST",
        body,
        timeout: 60000,
      }),
      // 组合层 AI 分析：positions 形如 [{ code: "000834", weight: 0.4 }, ...]
      // 真实路由是 /api/ai/portfolio/analyze（旧的 /api/ai/portfolio-insights 不存在，会 404）
      analyzePortfolio: (positions, options = {}) =>
        request(config.aiBaseUrl, "/api/ai/portfolio/analyze", {
          method: "POST",
          body: { positions, ...options },
          timeout: 180000,
        }),
    }
  };
})(window);
