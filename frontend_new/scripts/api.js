(function (window) {
  "use strict";

  const config = {
    marketBaseUrl: "",
    portfolioBaseUrl: "",
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

    const response = await fetch(joinUrl(baseUrl, path), init);
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

  window.FundMasterAPI = {
    config,
    market: {
      getFundNameList: () => request(config.marketBaseUrl, "/api/market/fund_public/fund_name_list"),
      getFundRank: (fundType = "all") =>
        request(config.marketBaseUrl, "/api/market/fund_public/rank", {
          method: "POST",
          body: { fund_type: fundType },
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
    },
    portfolio: {
      createTransaction: (body) =>
        request(config.portfolioBaseUrl, "/api/portfolio/transaction/create", {
          method: "POST",
          body,
        }),
      listHoldings: () => request(config.portfolioBaseUrl, "/api/portfolio/holding/list?page=1&page_size=50"),
    },
  };
})(window);
