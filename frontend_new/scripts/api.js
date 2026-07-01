(function (window) {
  "use strict";

  const DEFAULT_CONFIG = {
    marketBaseUrl: "",
    newsBaseUrl: "",
    portfolioBaseUrl: "",
  };

  const config = {
    ...DEFAULT_CONFIG,
    ...(window.FUNDMASTER_API_CONFIG || {}),
  };

  function joinUrl(baseUrl, path) {
    return `${String(baseUrl).replace(/\/$/, "")}${path}`;
  }

  async function request(baseUrl, path, options = {}) {
    const method = options.method || "GET";
    const headers = new Headers(options.headers || {});
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), options.timeoutMs || 45000);
    const init = { method, headers, signal: controller.signal };

    if (options.body !== undefined) {
      headers.set("Content-Type", "application/json");
      init.body = JSON.stringify(options.body);
    }

    let response;
    try {
      response = await fetch(joinUrl(baseUrl, path), init);
    } catch (error) {
      if (error.name === "AbortError") throw new Error("Request timed out");
      throw error;
    } finally {
      window.clearTimeout(timeoutId);
    }
    let payload = null;
    const responseText = await response.text();

    try {
      payload = responseText ? JSON.parse(responseText) : null;
    } catch (error) {
      // Python's default JSON encoder may emit bare NaN/Infinity values.
      // Browsers reject those as invalid JSON, so normalize numeric values to null.
      const normalized = responseText
        .replace(/(:|\[|,)\s*NaN\s*(?=,|\]|})/g, "$1 null")
        .replace(/(:|\[|,)\s*-?Infinity\s*(?=,|\]|})/g, "$1 null");
      try {
        payload = normalized ? JSON.parse(normalized) : null;
      } catch (normalizedError) {
        payload = { message: response.statusText || "Invalid JSON response" };
      }
    }

    if (!response.ok || (payload && payload.code && payload.code !== 200)) {
      const message = payload && payload.message ? payload.message : `HTTP ${response.status}`;
      throw new Error(message);
    }

    return payload && Object.prototype.hasOwnProperty.call(payload, "data") ? payload.data : payload;
  }

  function get(path) {
    return request(config.marketBaseUrl, path);
  }

  function withQuery(path, params = {}) {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        query.set(key, String(value));
      }
    });
    const suffix = query.toString();
    return suffix ? `${path}?${suffix}` : path;
  }

  function postMarket(path, body) {
    return request(config.marketBaseUrl, path, { method: "POST", body });
  }

  function postNews(path, body) {
    return request(config.newsBaseUrl, path, { method: "POST", body });
  }

  function getPortfolio(path, params) {
    return request(config.portfolioBaseUrl, withQuery(path, params));
  }

  function postPortfolio(path, body = {}) {
    return request(config.portfolioBaseUrl, path, { method: "POST", body });
  }

  window.FundMasterAPI = {
    config,
    stock: {
      getASpot: (params) => postMarket("/api/market/stock/a/one_spot", params),
      getAllASpot: (params = { platform: "sina" }) => postMarket("/api/market/stock/a/all_spot", params),
      getAHist: (params) => postMarket("/api/market/stock/a/hist", params),
      getAHistKline: (params) => postMarket("/api/market/stock/a/hist_kline", params),
      getABidAsk: (params) => postMarket("/api/market/stock/a/bid_ask", params),
      getBatchASpot: (params) => postMarket("/api/market/stock/a/batch_spot", params),
    },
    publicFund: {
      getOneRealTime: (params) => postMarket("/api/market/fund_public/real_time_get_one", params),
      getAllRealTime: (params) => postMarket("/api/market/fund_public/real_time_get_all", params),
      getBatchSpot: (params) => postMarket("/api/market/fund_public/batch_spot", params),
      getHist: (params) => postMarket("/api/market/fund_public/hist", params),
      getHistKline: (params) => postMarket("/api/market/fund_public/hist_kline", params),
      getHistMin: (params) => postMarket("/api/market/fund_public/hist_min", params),
      getHistMinKline: (params) => postMarket("/api/market/fund_public/hist_min_kline", params),
      getNameList: () => get("/api/market/fund_public/fund_name_list"),
      getPortfolioHolds: (params) => postMarket("/api/market/fund_public/portfolio_holds", params),
      getIndividualAnalysis: (params) => postMarket("/api/market/fund_public/individual_analysis", params),
      getProfitProbability: (params) => postMarket("/api/market/fund_public/profit_probability", params),
      getValueEstimation: (params) => postMarket("/api/market/fund_public/value_estimation", params),
      getValueEstimationList: (params = {}) => postMarket("/api/market/fund_public/value_estimation_list", params),
      getRank: (params = {}) => postMarket("/api/market/fund_public/rank", params),
      getInfoIndex: (params = {}) => postMarket("/api/market/fund_public/info_index", params),
      getIndividualBasicInfo: (params) => postMarket("/api/market/fund_public/individual_basic_info", params),
      getIndividualDetailHold: (params) => postMarket("/api/market/fund_public/individual_detail_hold", params),
      getPortfolioIndustryAllocation: (params) => postMarket("/api/market/fund_public/portfolio_industry_allocation", params),
      getPortfolioHoldStock: (params) => postMarket("/api/market/fund_public/portfolio_hold_stock", params),
      getPortfolioHoldBond: (params) => postMarket("/api/market/fund_public/portfolio_hold_bond", params),
    },
    bond: {
      getSpotQuote: (params = {}) => postMarket("/api/market/bond/spot_quote", params),
      getSpotDeal: (params = {}) => postMarket("/api/market/bond/spot_deal", params),
      searchSpotQuote: (params) => postMarket("/api/market/bond/spot_quote_search", params),
      searchSpotDeal: (params) => postMarket("/api/market/bond/spot_deal_search", params),
      searchInfo: (params = {}) => postMarket("/api/market/bond/info_search", params),
      getChinaYield: (params) => postMarket("/api/market/bond/china_yield", params),
      searchChinaYield: (params) => postMarket("/api/market/bond/china_yield_search", params),
      getNameByCode: (params) => postMarket("/api/market/bond/get_name_by_code", params),
    },
    crypto: {
      getBooks: (params) => postMarket("/api/market/crypto/books", params),
      getTicker: (params) => postMarket("/api/market/crypto/ticker", params),
      getKlines: (params) => postMarket("/api/market/crypto/klines", params),
      getMovingAverages: (params) => postMarket("/api/market/crypto/ma", params),
    },
    global: {
      exchangeRate: (params) => postMarket("/api/market/global/exchange_rate/rate", params),
      convertCurrency: (params) => postMarket("/api/market/global/exchange_rate/convert", params),
      getAllRates: (params) => postMarket("/api/market/global/exchange_rate/all_rates", params),
      getRateHistory: (params) => postMarket("/api/market/global/exchange_rate/history", params),
      getIndexList: () => postMarket("/api/market/global/index/list", {}),
      getIndexQuote: (params) => postMarket("/api/market/global/index/quote", params),
      getIndexQuotes: (params) => postMarket("/api/market/global/index/quotes", params),
      getIndexQuotesFromList: async (preferredTickers = [], limit = 4) => {
        const supported = await postMarket("/api/market/global/index/list", {});
        const available = Array.isArray(supported)
          ? supported.map((item) => item && item.ticker).filter(Boolean)
          : [];
        const preferred = preferredTickers.filter((ticker) => available.includes(ticker));
        const tickers = [...new Set([...preferred, ...available])].slice(0, limit);
        const fallback = preferredTickers.slice(0, limit);
        return postMarket("/api/market/global/index/quotes", {
          tickers: tickers.length ? tickers : fallback,
        });
      },
      getIndexInfo: (params) => postMarket("/api/market/global/index/info", params),
      getIndexHistory: (params) => postMarket("/api/market/global/index/hist", params),
    },
    macro: {
      getCountries: () => postMarket("/api/market/macro/countries", {}),
      getIndicators: (params = {}) => postMarket("/api/market/macro/indicators", params),
      getSchema: (params) => postMarket("/api/market/macro/schema", params),
      getData: (params) => postMarket("/api/market/macro/data", params),
    },
    news: {
      getStockRecentNews: (params) => postNews("/api/news/stock/get_recent_news", params),
      getPublicFundAnnouncement: (params) => postNews("/api/news/public_fund/get_announcement", params),
    },
    portfolio: {
      getFunctions: (tag) => getPortfolio("/api/portfolio/functions", tag ? { tag } : {}),
      transactions: {
        create: (params) => postPortfolio("/api/portfolio/transaction/create", params),
        get: (transId) => getPortfolio(`/api/portfolio/transaction/${encodeURIComponent(transId)}`),
        update: (params) => postPortfolio("/api/portfolio/transaction/update", params),
        remove: (params) => postPortfolio("/api/portfolio/transaction/delete", params),
        list: (params = {}) => getPortfolio("/api/portfolio/transaction/list", params),
      },
      holdings: {
        list: (params = {}) => getPortfolio("/api/portfolio/holding/list", params),
        getDetail: (params) => getPortfolio("/api/portfolio/holding/detail", params),
      },
      alerts: {
        create: (params) => postPortfolio("/api/portfolio/alert/create", params),
        get: (alertId) => getPortfolio(`/api/portfolio/alert/${encodeURIComponent(alertId)}`),
        update: (params) => postPortfolio("/api/portfolio/alert/update", params),
        remove: (params) => postPortfolio("/api/portfolio/alert/delete", params),
        list: (params = {}) => getPortfolio("/api/portfolio/alert/list", params),
      },
      watchlist: {
        create: (params) => postPortfolio("/api/portfolio/watchlist/create", params),
        remove: (params) => postPortfolio("/api/portfolio/watchlist/delete", params),
        list: (params = {}) => getPortfolio("/api/portfolio/watchlist/list", params),
      },
      allocation: {
        getCurrent: () => getPortfolio("/api/portfolio/allocation/current"),
        setTarget: (params) => postPortfolio("/api/portfolio/allocation/target", params),
        getTarget: () => getPortfolio("/api/portfolio/allocation/target"),
        getDrift: () => getPortfolio("/api/portfolio/allocation/drift"),
      },
      sector: {
        getExposure: () => getPortfolio("/api/portfolio/sector/exposure"),
        getConcentration: () => getPortfolio("/api/portfolio/sector/concentration"),
      },
      fund: {
        getDetailHold: (params) => postPortfolio("/api/portfolio/fund/detail_hold", params),
        getIndustryAllocation: (params) => postPortfolio("/api/portfolio/fund/industry_allocation", params),
        getStockHolds: (params) => postPortfolio("/api/portfolio/fund/stock_holds", params),
        getBondHolds: (params) => postPortfolio("/api/portfolio/fund/bond_holds", params),
      },
      smtp: {
        getConfig: () => getPortfolio("/api/portfolio/smtp_config/get_config"),
        updateConfig: (params) => postPortfolio("/api/portfolio/smtp_config/update_config", params),
        testEmail: (params) => postPortfolio("/api/portfolio/smtp_config/test_email", params),
      },
      userProfile: {
        get: () => getPortfolio("/api/portfolio/user_profile/get_profile"),
        updatePhone: (phone) => postPortfolio("/api/portfolio/user_profile/update_phone", { phone }),
        updateEmail: (email) => postPortfolio("/api/portfolio/user_profile/update_email", { email }),
        update: (params) => postPortfolio("/api/portfolio/user_profile/update", params),
      },
    },
  };
})(window);
