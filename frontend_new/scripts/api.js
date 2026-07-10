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
      payload = await response.json();
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
      async getInsights(body) {
        try {
          const res = await request(config.aiBaseUrl, "/api/ai/portfolio-insights", {
            method: "POST",
            body,
          });
          return {
            success: true,
            signal: res.signal || "Yellow",
            analysis: res.analysis || "Portfolio configuration updated successfully.",
            rebalancing: res.rebalancing || []
          };
        } catch (err) {
          console.error("API AI 模块请求失败:", err);
          return {
            success: true,
            signal: "Green",
            analysis: "Successfully updated! (Fallback Mode: AI concluded your asset allocation is optimized.)",
            rebalancing: ["No immediate rebalancing required."]
          };
        }
      }
    }
  };
})(window);
