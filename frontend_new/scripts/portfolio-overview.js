(function (window, document) {
  "use strict";

  const api = window.FundMasterAPI;

  // 冻结版约定：持仓只保存在浏览器 localStorage，不写 Portfolio 数据库；
  // AI 分析由用户点击 Analyze Portfolio 手动触发，避免每次增删都调用真实大模型。
  const STORAGE_KEY = "fundmaster:overview-holdings:v1";
  const FUND_DIRECTORY_CACHE_KEY = "fundmaster:fund-directory:v1";
  const FUND_DIRECTORY_CACHE_TTL_MS = 24 * 60 * 60 * 1000;

  const state = {
    holdings: [],
    fundUniverse: null,
    fundUniversePromise: null,
    selectedFund: null,
    aiRunToken: 0,
    aiRunning: false,
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function formatMoney(value) {
    const number = Number(value || 0);
    const sign = number > 0 ? "+" : number < 0 ? "-" : "";
    return `${sign}¥${Math.abs(number).toLocaleString("zh-CN", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  }

  function formatPercent(value) {
    const number = Number(value || 0);
    const sign = number > 0 ? "+" : "";
    return `${sign}${number.toFixed(2)}%`;
  }

  function toneClass(value) {
    return value > 0 ? "pos" : value < 0 ? "neg" : "";
  }

  // ------------------------------------------------------------------
  // 本地持久化（仅当前浏览器，刷新不丢失）
  // ------------------------------------------------------------------

  function loadHoldings() {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) return [];
      return parsed
        .map((item) => ({
          code: typeof item.code === "string" ? item.code : "",
          name: typeof item.name === "string" ? item.name : "",
          amount: Number(item.amount),
          profit: Number(item.profit) || 0,
        }))
        .filter((item) => item.name && Number.isFinite(item.amount) && item.amount > 0);
    } catch (error) {
      console.error("Stored holdings unreadable, starting empty:", error);
      return [];
    }
  }

  function saveHoldings() {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state.holdings));
    } catch (error) {
      console.error("Failed to persist holdings locally:", error);
    }
  }

  // ------------------------------------------------------------------
  // 持仓表 + 顶部汇总
  // ------------------------------------------------------------------

  function codedHoldings() {
    return state.holdings.filter((item) => /^\d{6}$/.test(item.code || ""));
  }

  function updateAnalyzeButton() {
    const button = byId("btn-run-ai");
    if (!button) return;
    button.disabled = state.aiRunning || !codedHoldings().length;
    button.textContent = state.aiRunning ? "Analyzing…" : "Analyze Portfolio";
  }

  function renderHoldings() {
    const tbody = byId("holdings-body");
    if (!tbody) return;

    if (!state.holdings.length) {
      tbody.innerHTML = '<tr class="po-empty-row"><td colspan="6">No holdings yet. Click "Add New Holding" to search for a fund and add your position.</td></tr>';
    } else {
      tbody.innerHTML = state.holdings
        .map((item, index) => {
          const returnRate = item.amount ? (item.profit / item.amount) * 100 : 0;
          const tone = toneClass(item.profit);
          return `
            <tr>
              <td>${escapeHtml(item.name)}</td>
              <td>¥${Number(item.amount).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
              <td class="${tone}">${formatMoney(item.profit)}</td>
              <td class="${tone}">${formatPercent(returnRate)}</td>
              <td>${item.code ? `<code>${escapeHtml(item.code)}</code>` : '<span class="muted">—</span>'}</td>
              <td><button type="button" class="po-row-remove" data-holding-remove="${index}" aria-label="Remove holding">Remove</button></td>
            </tr>`;
        })
        .join("");
    }

    const totalValue = state.holdings.reduce((sum, item) => sum + item.amount, 0);
    const totalProfit = state.holdings.reduce((sum, item) => sum + item.profit, 0);
    const valueNode = byId("po-total-value");
    const profitNode = byId("po-total-profit");
    if (valueNode) {
      valueNode.textContent = `¥${totalValue.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }
    if (profitNode) {
      profitNode.textContent = state.holdings.length ? formatMoney(totalProfit) : "—";
      profitNode.className = `po-big ${toneClass(totalProfit)}`.trim();
    }
    updateAnalyzeButton();
  }

  // ------------------------------------------------------------------
  // 弹窗内的基金检索（复用后端基金名录接口）
  // ------------------------------------------------------------------

  function pick(record, keys) {
    for (const key of keys) {
      if (record && record[key] !== undefined && record[key] !== null && record[key] !== "") {
        return String(record[key]);
      }
    }
    return "";
  }

  function normalizeFund(record) {
    return {
      code: pick(record, ["基金代码", "fund_code", "code", "symbol"]),
      name: pick(record, ["基金简称", "基金名称", "name", "fund_name", "short_name"]),
      type: pick(record, ["类型", "fund_type", "type"]) || "Fund",
      pinyinAbbr: pick(record, ["拼音缩写", "pinyin_abbr"]),
      pinyinFull: pick(record, ["拼音全称", "pinyin_full"]),
    };
  }

  function readFundDirectoryCache() {
    try {
      const raw = window.localStorage.getItem(FUND_DIRECTORY_CACHE_KEY);
      if (!raw) return null;
      const cached = JSON.parse(raw);
      if (!cached || !Array.isArray(cached.rows)) return null;
      const funds = cached.rows
        .map((row) => ({
          code: String(row?.[0] || ""),
          name: String(row?.[1] || ""),
          type: String(row?.[2] || "Fund"),
          pinyinAbbr: String(row?.[3] || ""),
          pinyinFull: "",
        }))
        .filter((item) => item.code && item.name);
      if (!funds.length) return null;
      const savedAt = Number(cached.savedAt);
      const age = Date.now() - savedAt;
      return {
        funds,
        fresh: Number.isFinite(savedAt) && age >= 0 && age < FUND_DIRECTORY_CACHE_TTL_MS,
      };
    } catch (error) {
      try {
        window.localStorage.removeItem(FUND_DIRECTORY_CACHE_KEY);
      } catch (removeError) {
        // Ignore unavailable browser storage and continue with the network.
      }
      return null;
    }
  }

  function writeFundDirectoryCache(funds) {
    try {
      const rows = funds.map((item) => [
        item.code,
        item.name,
        item.type,
        item.pinyinAbbr,
      ]);
      window.localStorage.setItem(FUND_DIRECTORY_CACHE_KEY, JSON.stringify({
        savedAt: Date.now(),
        rows,
      }));
    } catch (error) {
      // Private mode or a full quota should not make fund search unusable.
    }
  }

  function refreshFundUniverse() {
    if (state.fundUniversePromise) return state.fundUniversePromise;
    if (!api?.market?.getFundNameList) {
      return Promise.reject(new Error("Fund search API is unavailable"));
    }

    state.fundUniversePromise = api.market.getFundNameList()
      .then((rows) => {
        if (!Array.isArray(rows) || !rows.length) {
          throw new Error("Fund directory returned no records");
        }
        const funds = rows.map(normalizeFund).filter((item) => item.code && item.name);
        if (!funds.length) {
          throw new Error("Fund directory contained no usable records");
        }
        state.fundUniverse = funds;
        writeFundDirectoryCache(funds);
        return funds;
      })
      .finally(() => {
        state.fundUniversePromise = null;
      });
    return state.fundUniversePromise;
  }

  async function getFundUniverse() {
    if (Array.isArray(state.fundUniverse)) return state.fundUniverse;
    const cached = readFundDirectoryCache();
    if (cached) {
      state.fundUniverse = cached.funds;
      if (!cached.fresh) {
        refreshFundUniverse().catch((error) => {
          console.error("Fund directory background refresh failed; using cached data:", error);
        });
      }
      return state.fundUniverse;
    }
    return refreshFundUniverse();
  }

  function fundSearchRank(item, query) {
    const code = String(item.code || "").toLowerCase();
    const name = String(item.name || "").toLowerCase();
    const pinyinAbbr = String(item.pinyinAbbr || "").toLowerCase();
    const pinyinFull = String(item.pinyinFull || "").toLowerCase();
    if (code.startsWith(query)) return 0;
    if (name.startsWith(query)) return 1;
    if (pinyinAbbr.startsWith(query) || pinyinFull.startsWith(query)) return 2;
    if ([code, name, pinyinAbbr, pinyinFull].some((value) => value.includes(query))) return 3;
    return Number.POSITIVE_INFINITY;
  }

  function findFundMatches(universe, query) {
    return universe
      .map((item, index) => ({ item, index, rank: fundSearchRank(item, query) }))
      .filter((entry) => Number.isFinite(entry.rank))
      .sort((left, right) => left.rank - right.rank || left.index - right.index)
      .map((entry) => entry.item);
  }

  function renderFundMessage(message) {
    const container = byId("holding-fund-results");
    if (!container) return;
    container.hidden = false;
    container.innerHTML = `<div class="po-fund-results__empty">${escapeHtml(message)}</div>`;
  }

  function renderFundResults(matches, query) {
    const container = byId("holding-fund-results");
    if (!container) return;
    if (!query) {
      container.hidden = true;
      container.innerHTML = "";
      return;
    }
    container.hidden = false;
    if (!matches.length) {
      container.innerHTML = `<div class="po-fund-results__empty">No fund matched "${escapeHtml(query)}". Check the code or try another keyword.</div>`;
      return;
    }
    container.innerHTML = matches
      .slice(0, 8)
      .map((item) => `
        <button type="button" class="po-fund-result" data-fund-code="${escapeHtml(item.code)}" data-fund-name="${escapeHtml(item.name)}">
          <code>${escapeHtml(item.code)}</code>
          <span>${escapeHtml(item.name)}</span>
          <small>${escapeHtml(item.type)}</small>
        </button>`)
      .join("");
  }

  function setSelectedFund(fund) {
    state.selectedFund = fund;
    const hint = byId("holding-fund-selected");
    if (!hint) return;
    if (fund) {
      hint.hidden = false;
      hint.innerHTML = `Selected: <code>${escapeHtml(fund.code)}</code> ${escapeHtml(fund.name)} · AI analysis will use this fund code.`;
    } else {
      hint.hidden = true;
      hint.textContent = "";
    }
  }

  function bindFundSearch() {
    const input = byId("holding-fund-name");
    const container = byId("holding-fund-results");
    if (!input || !container) return;

    let activeQuery = "";
    let searchTimer = null;
    input.addEventListener("input", () => {
      const query = input.value.trim();
      activeQuery = query;
      window.clearTimeout(searchTimer);
      // 用户手动改动文本后，之前选中的基金不再可信
      if (state.selectedFund && query !== `${state.selectedFund.code} ${state.selectedFund.name}`) {
        setSelectedFund(null);
      }
      if (!query) {
        renderFundResults([], "");
        return;
      }
      if (!Array.isArray(state.fundUniverse)) {
        renderFundMessage("Loading fund directory…");
      }
      searchTimer = window.setTimeout(async () => {
        try {
          const universe = await getFundUniverse();
          if (activeQuery !== query) return;
          const q = query.toLowerCase();
          const matches = findFundMatches(universe, q);
          renderFundResults(matches, query);
        } catch (error) {
          if (activeQuery !== query) return;
          console.error("Fund name list unavailable for holding search:", error);
          renderFundMessage("Fund directory is temporarily unavailable. Edit the query to retry.");
        }
      }, 250);
    });

    container.addEventListener("click", (event) => {
      const button = event.target.closest("[data-fund-code]");
      if (!button) return;
      const fund = { code: button.dataset.fundCode, name: button.dataset.fundName };
      setSelectedFund(fund);
      input.value = `${fund.code} ${fund.name}`;
      renderFundResults([], "");
    });

    document.addEventListener("click", (event) => {
      if (!container.contains(event.target) && event.target !== input) {
        container.hidden = true;
      }
    });
  }

  // ------------------------------------------------------------------
  // AI 组合分析（手动触发，端点 /api/ai/portfolio/analyze）
  // ------------------------------------------------------------------

  function setAiStatus(message) {
    const status = byId("ai-status");
    if (status) status.textContent = message;
  }

  function clearAiOutput(message) {
    const analysis = byId("ai-analysis");
    if (analysis) {
      analysis.textContent = message;
      analysis.className = "muted";
    }
  }

  function narrativeOnly(result) {
    const rawSummary = String(result?.summary || "").trim();
    const mentionsRating = /\b(?:overall\s+)?(?:score|rating)\b|\b(?:buy|hold|watch|avoid)\b/i.test(rawSummary);
    if (rawSummary && !mentionsRating) {
      return rawSummary.replace(/\*\*/g, "");
    }

    const evidence = [
      ...(Array.isArray(result?.key_thesis) ? result.key_thesis : []),
      ...(Array.isArray(result?.main_risks) ? result.main_risks : []),
    ].filter(Boolean);
    return evidence.length
      ? evidence.slice(0, 6).join(" ")
      : "The AI service returned no portfolio analysis text.";
  }

  function resetAiPanel() {
    clearAiOutput("The AI assistant will analyze your portfolio after you add holdings and click Analyze Portfolio.");
    setAiStatus("Add holdings, then click Analyze Portfolio to run the AI analysis.");
  }

  // 持仓变化后：作废在途的旧分析结果，提示用户手动重新分析（不自动调模型）
  function noteHoldingsChanged() {
    state.aiRunToken += 1;
    if (!state.holdings.length) {
      resetAiPanel();
      return;
    }
    const coded = codedHoldings().length;
    if (!coded) {
      clearAiOutput("Add a holding selected from the fund search before running the portfolio analysis.");
      setAiStatus("AI analysis needs holdings selected from the fund search (with a 6-digit fund code). Manually typed names cannot be analyzed.");
    } else {
      clearAiOutput("Holdings changed. Run Analyze Portfolio again to refresh the analysis.");
      setAiStatus("Holdings updated — click Analyze Portfolio to refresh the AI analysis.");
    }
  }

  function aiPositions() {
    // 只有真实的 6 位基金代码才能被 AI 服务取到净值；重复代码合并权重
    const totals = new Map();
    codedHoldings().forEach((item) => {
      totals.set(item.code, (totals.get(item.code) || 0) + item.amount);
    });
    const totalAmount = [...totals.values()].reduce((sum, value) => sum + value, 0);
    if (!totalAmount) return [];
    return [...totals.entries()].map(([code, amount]) => ({
      code,
      weight: amount / totalAmount,
    }));
  }

  async function runAiAnalysis() {
    const analysis = byId("ai-analysis");
    if (!analysis) return;
    if (state.aiRunning) return;

    const positions = aiPositions();
    if (!positions.length) {
      setAiStatus("AI analysis needs holdings selected from the fund search (with a 6-digit fund code).");
      return;
    }
    if (!api?.ai?.analyzePortfolio) {
      setAiStatus("AI service client is not available (api.js not loaded).");
      return;
    }

    const skipped = state.holdings.length - codedHoldings().length;
    const token = ++state.aiRunToken;
    state.aiRunning = true;
    updateAnalyzeButton();

    setAiStatus(`AI assistant is analyzing ${positions.length} fund${positions.length > 1 ? "s" : ""}… this can take a while for real model runs.`);
    analysis.textContent = "Calculating portfolio metrics and generating the AI commentary…";
    analysis.className = "";

    try {
      const result = await api.ai.analyzePortfolio(positions);
      if (token !== state.aiRunToken) return; // 持仓已变化，丢弃过期结果

      analysis.textContent = narrativeOnly(result);

      setAiStatus(
        skipped > 0
          ? `AI analysis covers ${positions.length} coded fund(s); ${skipped} holding(s) without a fund code were excluded.`
          : `AI analysis completed for ${positions.length} fund(s).`,
      );
    } catch (error) {
      if (token === state.aiRunToken) {
        console.error("AI portfolio analysis failed:", error);
        analysis.textContent = `AI analysis failed: ${error.message}. Make sure the AI Agent service is running, then click Analyze Portfolio to retry.`;
        analysis.className = "muted";
        setAiStatus("The AI service could not complete this analysis.");
      }
    } finally {
      state.aiRunning = false;
      updateAnalyzeButton();
    }
  }

  // ------------------------------------------------------------------
  // 添加持仓弹窗（冻结版：不写 Portfolio 数据库）
  // ------------------------------------------------------------------

  function bindModal() {
    const modal = byId("add-holding-modal");
    const openButton = byId("btn-add-holding");
    const form = byId("add-holding-form");
    const status = byId("add-holding-status");
    const input = byId("holding-fund-name");
    if (!modal || !openButton || !form || !input) return;

    const showStatus = (message, isError = false) => {
      if (!status) return;
      status.hidden = !message;
      status.textContent = message;
      status.classList.toggle("po-modal__status--error", isError);
    };

    const openModal = () => {
      modal.hidden = false;
      document.body.classList.add("po-modal-open");
      form.reset();
      setSelectedFund(null);
      renderFundResults([], "");
      showStatus("");
      input.focus();
      getFundUniverse().catch((error) => {
        console.error("Fund directory preload failed:", error);
      });
    };

    const closeModal = () => {
      modal.hidden = true;
      document.body.classList.remove("po-modal-open");
    };

    openButton.addEventListener("click", openModal);
    document.querySelectorAll("[data-holding-cancel]").forEach((button) => {
      button.addEventListener("click", closeModal);
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !modal.hidden) closeModal();
    });

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const data = new FormData(form);
      const typedName = String(data.get("fundName") || "").trim();
      const amount = Number(data.get("amount") || 0);
      const profit = Number(data.get("profit") || 0);
      if (!typedName || !(amount > 0)) {
        showStatus("Please pick a fund and enter a holding amount above zero.", true);
        return;
      }

      const selected = state.selectedFund;
      if (!selected) {
        showStatus("Select a fund from the search results before confirming.", true);
        return;
      }
      state.holdings.push({
        code: selected.code,
        name: selected.name,
        amount,
        profit,
      });
      saveHoldings();
      renderHoldings();
      noteHoldingsChanged();
      closeModal();
    });
  }

  function bindRemoveButtons() {
    const tbody = byId("holdings-body");
    if (!tbody) return;
    tbody.addEventListener("click", (event) => {
      const button = event.target.closest("[data-holding-remove]");
      if (!button) return;
      state.holdings.splice(Number(button.dataset.holdingRemove), 1);
      saveHoldings();
      renderHoldings();
      noteHoldingsChanged();
    });
  }

  function bindAnalyzeButton() {
    const button = byId("btn-run-ai");
    if (button) button.addEventListener("click", runAiAnalysis);
  }

  function init() {
    state.holdings = loadHoldings();
    renderHoldings();
    resetAiPanel();
    if (state.holdings.length) {
      setAiStatus(`Restored ${state.holdings.length} holding(s) saved in this browser. Click Analyze Portfolio to run the AI analysis.`);
    }
    bindModal();
    bindFundSearch();
    bindRemoveButtons();
    bindAnalyzeButton();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window, document);
