(function (window) {
  "use strict";

  const DEFAULT_CONFIG = {
    marketBaseUrl: "",
    newsBaseUrl: "",
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
    const init = { method, headers };

    if (options.body !== undefined) {
      headers.set("Content-Type", "application/json");
      init.body = JSON.stringify(options.body);
    }

    const response = await fetch(joinUrl(baseUrl, path), init);
    let payload = null;

    try {
      payload = await response.json();
    } catch (error) {
      payload = { message: response.statusText || "Invalid JSON response" };
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

  function postMarket(path, body) {
    return request(config.marketBaseUrl, path, { method: "POST", body });
  }

  function postNews(path, body) {
    return request(config.newsBaseUrl, path, { method: "POST", body });
  }

  window.FundMasterAPI = {
    config,
    stock: {
      getASpot: (params) => postMarket("/api/market/stock/a/one_spot", params),
      getAllASpot: (params = { platform: "eastmoney" }) => postMarket("/api/market/stock/a/all_spot", params),
      getAHist: (params) => postMarket("/api/market/stock/a/hist", params),
      getABidAsk: (params) => postMarket("/api/market/stock/a/bid_ask", params),
    },
    publicFund: {
      getOneRealTime: (params) => postMarket("/api/market/fund_public/real_time_get_one", params),
      getAllRealTime: (params) => postMarket("/api/market/fund_public/real_time_get_all", params),
      getHist: (params) => postMarket("/api/market/fund_public/hist", params),
      getHistMin: (params) => postMarket("/api/market/fund_public/hist_min", params),
      getNameList: () => get("/api/market/fund_public/fund_name_list"),
    },
    news: {
      getStockRecentNews: (params) => postNews("/api/news/stock/get_recent_news", params),
      getPublicFundAnnouncement: (params) => postNews("/api/news/public_fund/get_announcement", params),
    },
  };
})(window);
