(function (window) {
  "use strict";

  // Keep empty when the frontend is served by a dev proxy or the same origin as backend.
  // For direct local integration, change to:
  // marketBaseUrl: "http://127.0.0.1:5001"
  // portfolioBaseUrl: "http://127.0.0.1:5002"
  window.FUNDMASTER_API_CONFIG = {
    marketBaseUrl: "",
    portfolioBaseUrl: "",
  };
})(window);
