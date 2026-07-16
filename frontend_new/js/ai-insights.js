/**
 * AI Insights 页面逻辑。
 *
 * 信息分三层渲染，回答"这不是一句 prompt 丢给大模型"的证明诉求：
 * 1. 结论层  —— 评级/评分/Chief 总结（普通用户看的答案）；
 * 2. 过程层  —— 四阶段流水线（真实取数 → 确定性指标 → 专家检查 → 汇总），
 *               由后端返回的 analysis_trace 按 category 聚合而成；
 * 3. 开发者层 —— 原始 coverage / 元数据 / technical JSON，默认隐藏在开关后。
 *
 * 页面只消费 /api/ai/fund/analyze 的既有字段，不依赖任何新接口。
 */

const form = document.querySelector("[data-analysis-form]");
const statusPill = document.querySelector("[data-analysis-status]");

const fields = {
  fundCode: document.querySelector("[data-fund-code]"),
  startDate: document.querySelector("[data-start-date]"),
  riskProfile: document.querySelector("[data-risk-profile]"),
  realLlm: document.querySelector("[data-real-llm]"),
  llmModel: document.querySelector("[data-llm-model]"),
  submitBtn: document.querySelector("[data-submit-btn]"),
  overallRating: document.querySelector("[data-overall-rating]"),
  overallScore: document.querySelector("[data-overall-score]"),
  scoreFill: document.querySelector("[data-score-fill]"),
  reliabilityBadge: document.querySelector("[data-reliability-badge]"),
  confidenceBadge: document.querySelector("[data-confidence-badge]"),
  fundName: document.querySelector("[data-fund-name]"),
  fundMeta: document.querySelector("[data-fund-meta]"),
  summary: document.querySelector("[data-summary]"),
  scoreExplanation: document.querySelector("[data-score-explanation]"),
  keyThesis: document.querySelector("[data-key-thesis]"),
  mainRisks: document.querySelector("[data-main-risks]"),
  actionPlan: document.querySelector("[data-action-plan]"),
  metricsNote: document.querySelector("[data-metrics-note]"),
  quantMetrics: document.querySelector("[data-quant-metrics]"),
  pipelineStages: document.querySelector("[data-pipeline-stages]"),
  stageDrawer: document.querySelector("[data-stage-drawer]"),
  agentGrid: document.querySelector("[data-agent-grid]"),
  agentDrawer: document.querySelector("[data-agent-drawer]"),
  agentCount: document.querySelector("[data-agent-count]"),
  devToggle: document.querySelector("[data-dev-toggle]"),
  devPanel: document.querySelector("[data-dev-panel]"),
  devCoverage: document.querySelector("[data-dev-coverage]"),
  devMetadata: document.querySelector("[data-dev-metadata]"),
  runId: document.querySelector("[data-run-id]"),
  technicalEvidence: document.querySelector("[data-technical-evidence]"),
};

/* ------------------------------------------------------------------ */
/* 静态文案：agent 友好名、职责说明、状态翻译                              */
/* ------------------------------------------------------------------ */

const AGENT_META = {
  PerformanceAgent: {
    label: "Performance",
    desc: "Returns across rolling windows vs drawdown",
  },
  ExposureAgent: {
    label: "Portfolio Exposure",
    desc: "Holding concentration and diversification",
  },
  BondExposureAgent: {
    label: "Bond Exposure",
    desc: "Fixed-income holdings and asset mix",
  },
  RiskAgent: {
    label: "Risk Control",
    desc: "Volatility, drawdown and rolling risk",
  },
  SentimentAgent: {
    label: "News Signal",
    desc: "Recent announcements and news tone",
  },
  SectorAgent: {
    label: "Sector Context",
    desc: "Industry concentration and sector bets",
  },
  MarketAgent: {
    label: "Peer & Market Context",
    desc: "Standing vs peer funds and holding-period win rates",
  },
};

const STANCE_META = {
  positive: { label: "Positive", tone: "green" },
  neutral: { label: "Neutral", tone: "cyan" },
  negative: { label: "Negative", tone: "red" },
  mixed: { label: "Mixed", tone: "amber" },
  insufficient_data: { label: "Skipped — required data unavailable", tone: "amber" },
  not_applicable: { label: "Not applicable to this fund type", tone: "muted" },
};

const RATING_TONE = {
  buy: "green",
  hold: "cyan",
  watch: "amber",
  avoid: "red",
  insufficient_data: "amber",
  unavailable: "red",
};

const RATING_LABEL = {
  insufficient_data: "INSUFFICIENT DATA",
  unavailable: "NOT RATED",
};

const STAGE_DEFS = [
  {
    key: "backend",
    title: "Real Data",
    sub: "market & news backends",
  },
  {
    key: "feature",
    title: "Computed Metrics",
    sub: "calculated in code, not by the LLM",
  },
  {
    key: "agent",
    title: "Specialist Checks",
    sub: "independent agents, honest skips",
  },
  {
    key: "aggregation",
    title: "Aggregation",
    sub: "score math + LLM explanation",
  },
];

/* ------------------------------------------------------------------ */
/* 基础工具                                                             */
/* ------------------------------------------------------------------ */

let lastPayload = null;

function agentBase() {
  const params = new URLSearchParams(window.location.search);
  if (params.get("agentBase")) return params.get("agentBase").replace(/\/$/, "");
  if (window.FUNDMASTER_AGENT_BASE) return window.FUNDMASTER_AGENT_BASE.replace(/\/$/, "");
  // 以 file:// 直接打开页面时连本机 agent；经 HTTP 服务器(dev-server)访问时用同源相对路径，
  // 由 dev-server 转发到同机 agent —— 本地和云端自动适配，无需写死 IP。
  if (window.location.protocol === "file:") return "http://127.0.0.1:5003";
  return "";
}

function endpoint() {
  return `${agentBase()}/api/ai/fund/analyze`;
}

function modelsEndpoint() {
  return `${agentBase()}/api/ai/llm/models`;
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}

function setStatus(text, state = "live") {
  statusPill.textContent = text;
  statusPill.classList.toggle("chip--warn", state === "warn");
  statusPill.classList.toggle("chip--live", state !== "warn");
}

function formatPercent(value, digits = 2) {
  const n = Number(value || 0) * 100;
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(digits)}%`;
}

function formatEvidenceValue(value) {
  if (Array.isArray(value)) {
    return value.length ? value.join(", ") : "none";
  }
  if (value && typeof value === "object") {
    return Object.entries(value)
      .slice(0, 4)
      .map(([key, item]) => `${key}: ${formatEvidenceValue(item)}`)
      .join("; ");
  }
  if (value === null || value === undefined || value === "") {
    return "--";
  }
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toFixed(4);
  }
  return String(value);
}

/** 真实模型偶尔输出 markdown 记号（**加粗**、# 标题）；页面按纯文本渲染，
 *  所以显示前剥掉这些记号，避免出现裸星号。 */
function plainText(value) {
  return String(value || "")
    .replace(/\*\*/g, "")
    .replace(/^#+\s*/gm, "");
}

function listItems(node, items) {
  node.innerHTML = "";
  if (!items || items.length === 0) {
    node.append(el("li", null, "No output."));
    return;
  }
  items.forEach((item) => node.append(el("li", null, plainText(item))));
}


function resetResultState() {
  lastPayload = null;

  fields.overallRating.textContent = "--";
  fields.overallRating.className = "ai-rating-badge";
  fields.overallScore.textContent = "--";
  fields.scoreFill.style.width = "0%";
  fields.scoreFill.className = "ai-scorebar__fill";

  fields.reliabilityBadge.hidden = true;
  fields.reliabilityBadge.textContent = "";
  fields.reliabilityBadge.className = "ai-badge";
  fields.confidenceBadge.hidden = true;
  fields.confidenceBadge.textContent = "";
  fields.confidenceBadge.className = "ai-badge";

  fields.fundName.textContent = "Run an analysis to load fund data";
  fields.fundMeta.textContent = "";
  fields.summary.textContent = "Run analysis to generate a grounded multi-agent summary.";
  fields.scoreExplanation.textContent =
    "Run analysis to see how specialist scores shaped the final rating.";
  listItems(fields.keyThesis, []);
  listItems(fields.mainRisks, []);
  listItems(fields.actionPlan, []);

  fields.quantMetrics.innerHTML = "";
  fields.quantMetrics.append(
    el(
      "p",
      "ai-placeholder",
      "Run an analysis to compute return and risk metrics from real NAV history."
    )
  );
  fields.metricsNote.textContent =
    "Metrics are computed deterministically from NAV data — the LLM only explains them.";

  fields.pipelineStages.querySelectorAll(".ai-stage").forEach((node) => {
    node.className = "ai-stage ai-stage--idle";
    const stat = node.querySelector(".ai-stage__stat");
    if (stat) stat.textContent = "waiting";
  });
  fields.stageDrawer.hidden = true;
  fields.stageDrawer.innerHTML = "";
  delete fields.stageDrawer.dataset.openStage;

  fields.agentGrid.innerHTML = "";
  fields.agentGrid.append(
    el(
      "p",
      "ai-placeholder",
      "Each specialist agent audits one perspective and can refuse when its data is missing."
    )
  );
  fields.agentDrawer.hidden = true;
  fields.agentDrawer.innerHTML = "";
  delete fields.agentDrawer.dataset.openAgent;
  fields.agentCount.textContent = "idle";

  fields.runId.textContent = "no run yet";
  fields.devCoverage.innerHTML = "";
  fields.devCoverage.append(coverageCell("Status", "Run an analysis first."));
  fields.devMetadata.innerHTML = "";
  fields.devMetadata.append(el("li", null, "Run an analysis first."));
  fields.technicalEvidence.innerHTML = "";
  fields.technicalEvidence.append(
    el("li", null, "No backend or agent trace has been recorded yet.")
  );
  const technicalDetails = fields.technicalEvidence.closest("details");
  if (technicalDetails) technicalDetails.open = false;
}

/* ------------------------------------------------------------------ */
/* 模型目录（Run settings）                                             */
/* ------------------------------------------------------------------ */

function syncRealLlmModelSelect() {
  if (!fields.llmModel) return;
  fields.llmModel.disabled = !fields.realLlm.checked;
}

function populateModelSelect(catalog) {
  if (!fields.llmModel) return;

  const models = Array.isArray(catalog?.models) ? catalog.models : [];
  const defaultModel = catalog?.default_model || "";
  fields.llmModel.innerHTML = "";

  if (!models.length) {
    const option = el("option", null, defaultModel || "Default model");
    option.value = defaultModel;
    fields.llmModel.append(option);
    syncRealLlmModelSelect();
    return;
  }

  models.forEach((model) => {
    const option = el("option", null, model.label || model.id);
    option.value = model.id;
    if (model.id === defaultModel) option.selected = true;
    fields.llmModel.append(option);
  });
  syncRealLlmModelSelect();
}

async function loadModelCatalog() {
  if (!fields.llmModel) return;
  try {
    const response = await fetch(modelsEndpoint());
    const payload = await response.json();
    if (!response.ok || payload.code !== 200) {
      throw new Error(payload.message || `Model catalog request failed with ${response.status}`);
    }
    populateModelSelect(payload.data || {});
  } catch (error) {
    fields.llmModel.innerHTML = "";
    const option = el("option", null, "Model catalog unavailable");
    option.value = "";
    fields.llmModel.append(option);
    syncRealLlmModelSelect();
  }
}

/* ------------------------------------------------------------------ */
/* 结论层：评级 + Chief 总结 + 三列建议                                  */
/* ------------------------------------------------------------------ */

function renderVerdict(payload) {
  const analysis = payload.data || {};
  const coverage = payload.coverage || {};
  const metadata = analysis.metadata || {};

  const rating = String(analysis.overall_rating || "--").toLowerCase();
  const tone = RATING_TONE[rating] || "muted";
  fields.overallRating.textContent = rating === "--" ? "--" : (RATING_LABEL[rating] || rating.toUpperCase());
  fields.overallRating.className = `ai-rating-badge ai-rating-badge--${tone}`;

  const hasScore = analysis.overall_score !== null && analysis.overall_score !== undefined;
  const score = hasScore ? Number(analysis.overall_score) : 0;
  fields.overallScore.textContent = hasScore ? score.toFixed(1) : "—";
  fields.scoreFill.style.width = `${Math.max(0, Math.min(100, score))}%`;
  fields.scoreFill.className = `ai-scorebar__fill ai-scorebar__fill--${tone}`;

  const navPoints = coverage.nav_points ?? 0;
  const reliability = metadata.quant_metrics_reliability || "";
  if (reliability) {
    fields.reliabilityBadge.hidden = false;
    fields.reliabilityBadge.textContent = `${navPoints} NAV points · ${reliability} reliability`;
    fields.reliabilityBadge.className = `ai-badge ai-badge--${reliability === "high" ? "green" : "amber"}`;
  } else {
    fields.reliabilityBadge.hidden = true;
  }

  fields.confidenceBadge.hidden = true;

  fields.fundName.textContent = coverage.fund_name || fields.fundCode.value.trim() || "Unknown fund";
  const metaParts = [
    coverage.fund_type && coverage.fund_type !== "unknown" ? coverage.fund_type : "",
    metadata.llm_mode === "real" ? `real LLM · ${metadata.llm_model || ""}` : "mock LLM (real data)",
  ].filter(Boolean);
  fields.fundMeta.textContent = metaParts.join(" · ");

  fields.summary.textContent = plainText(analysis.summary) || "Analysis completed.";
  fields.scoreExplanation.textContent = plainText(analysis.score_explanation) || "No rating explanation returned.";

  listItems(fields.keyThesis, analysis.key_thesis);
  listItems(fields.mainRisks, analysis.main_risks);
  listItems(fields.actionPlan, analysis.action_plan);
}

/* ------------------------------------------------------------------ */
/* 量化指标条：quant_metrics 瓦片                                        */
/* ------------------------------------------------------------------ */

const METRIC_TILES = [
  { key: "total_return", label: "Total Return", kind: "signed-pct" },
  { key: "annualized_return", label: "Annualized Return", kind: "signed-pct" },
  { key: "annualized_volatility", label: "Volatility (ann.)", kind: "pct" },
  { key: "max_drawdown", label: "Max Drawdown", kind: "drawdown-pct" },
  { key: "sharpe_ratio", label: "Sharpe Ratio", kind: "ratio" },
  { key: "positive_period_ratio", label: "Positive Days", kind: "pct" },
];

function renderQuantMetrics(payload) {
  const analysis = payload.data || {};
  const metrics = analysis.quant_metrics || {};
  const metadata = analysis.metadata || {};
  fields.quantMetrics.innerHTML = "";

  const available = METRIC_TILES.filter((tile) => metrics[tile.key] !== undefined);
  if (!available.length) {
    fields.quantMetrics.append(
      el("p", "ai-placeholder", "No NAV-based metrics were returned for this run.")
    );
    const sample = Number(metrics.sample_size || 0);
    const reliability = metadata.quant_metrics_reliability || "unknown";
    fields.metricsNote.textContent = sample
      ? `Only ${sample} NAV points this run — annualized metrics withheld (${reliability} reliability).`
      : "No NAV points were available this run — annualized metrics withheld.";
    return;
  }

  available.forEach((tile) => {
    const value = Number(metrics[tile.key] || 0);
    const cell = el("div", "ai-metric");
    cell.append(el("span", "ai-metric__k", tile.label));

    let text = "";
    let tone = "";
    if (tile.kind === "signed-pct") {
      text = formatPercent(value);
      tone = value >= 0 ? "pos" : "neg";
    } else if (tile.kind === "drawdown-pct") {
      text = formatPercent(value);
      tone = value < -0.0001 ? "neg" : "";
    } else if (tile.kind === "pct") {
      text = `${(value * 100).toFixed(2)}%`;
    } else {
      text = value.toFixed(2);
      tone = value >= 0 ? "pos" : "neg";
    }
    cell.append(el("strong", `ai-metric__v ${tone ? `ai-metric__v--${tone}` : ""}`, text));
    fields.quantMetrics.append(cell);
  });

  const sample = Number(metrics.sample_size || 0);
  const reliability = metadata.quant_metrics_reliability || "unknown";
  fields.metricsNote.textContent =
    `Computed deterministically from ${sample} NAV points (${reliability} reliability) — the LLM only explains them.`;
}

/* ------------------------------------------------------------------ */
/* 过程层：四阶段流水线 + 阶段抽屉                                        */
/* ------------------------------------------------------------------ */

function groupTraceByCategory(trace) {
  const groups = { backend: [], feature: [], agent: [], aggregation: [] };
  (Array.isArray(trace) ? trace : []).forEach((event) => {
    const category = groups[event.category] ? event.category : "backend";
    groups[category].push(event);
  });
  return groups;
}

function stageState(events) {
  const statuses = events.map((event) => event.status || "success");
  if (statuses.includes("error")) return "error";
  if (statuses.includes("warning")) return "warning";
  return "ok";
}

function agentStatusCounts(agents) {
  const counts = { success: 0, insufficient: 0, notApplicable: 0, error: 0 };
  (agents || []).forEach((agent) => {
    if (agent.status === "success") counts.success += 1;
    else if (agent.status === "error") counts.error += 1;
    else if (agent.stance === "not_applicable") counts.notApplicable += 1;
    else counts.insufficient += 1;
  });
  return counts;
}

function agentCountSummary(counts) {
  return (
    `${counts.success} completed` +
    `${counts.notApplicable ? ` · ${counts.notApplicable} not applicable` : ""}` +
    `${counts.insufficient ? ` · ${counts.insufficient} skipped` : ""}` +
    `${counts.error ? ` · ${counts.error} failed` : ""}`
  );
}

function buildStageStats(payload, groups) {
  const analysis = payload.data || {};
  const coverage = payload.coverage || {};
  const metadata = analysis.metadata || {};
  const agents = analysis.agent_outputs || [];
  const counts = agentStatusCounts(agents);

  const successTools = String(coverage.successful_backend_tools || "")
    .split(",")
    .filter(Boolean);
  const featureTechnical = (groups.feature[0] || {}).technical || {};
  const metricCount =
    Number(featureTechnical.return_metric_count || 0) +
    Number(featureTechnical.risk_metric_count || 0) +
    Number(featureTechnical.benchmark_metric_count || 0);

  const summarySource = metadata.summary_source === "llm" ? "LLM explains the evidence" : "deterministic summary";

  return {
    backend: `${successTools.length} backend tools · ${coverage.nav_points || 0} NAV points`,
    feature: metricCount ? `${metricCount} return/risk metrics in code` : "return & risk metrics in code",
    agent: `${agents.length} agents · ${agentCountSummary(counts)}`,
    aggregation: `score → ${String(analysis.overall_rating || "--").toUpperCase()} · ${summarySource}`,
  };
}

function renderStageDrawer(stageKey, groups) {
  const drawer = fields.stageDrawer;
  drawer.innerHTML = "";
  const events = groups[stageKey] || [];
  if (!events.length) {
    drawer.hidden = true;
    return;
  }

  const def = STAGE_DEFS.find((item) => item.key === stageKey);
  drawer.append(el("h4", "ai-drawer__title", def ? def.title : stageKey));

  events.forEach((event) => {
    const item = el("div", "ai-drawer__item");
    const status = event.status || "success";
    item.append(el("span", `trace-status trace-status--${status}`, status));
    item.append(el("strong", null, event.title || "Analysis step"));
    if (event.detail) item.append(el("p", null, event.detail));

    const chips = el("div", "trace-evidence");
    Object.entries(event.evidence || {})
      .slice(0, 4)
      .forEach(([key, value]) => {
        chips.append(el("span", null, `${key}: ${formatEvidenceValue(value)}`));
      });
    if (chips.childNodes.length) item.append(chips);
    drawer.append(item);
  });
  drawer.hidden = false;
}

function renderPipeline(payload) {
  const analysis = payload.data || {};
  const groups = groupTraceByCategory(analysis.analysis_trace);
  const stats = buildStageStats(payload, groups);

  fields.pipelineStages.innerHTML = "";
  fields.stageDrawer.hidden = true;
  fields.stageDrawer.innerHTML = "";

  STAGE_DEFS.forEach((def, index) => {
    const events = groups[def.key] || [];
    const state = events.length ? stageState(events) : "idle";
    const item = el("li", `ai-stage ai-stage--${state}`);
    const button = el("button", "ai-stage__inner");
    button.type = "button";
    button.append(el("span", "ai-stage__step", String(index + 1)));
    const body = el("div", "ai-stage__body");
    body.append(el("strong", null, def.title));
    body.append(el("span", "ai-stage__stat", stats[def.key] || "no events"));
    body.append(el("span", "ai-stage__sub", def.sub));
    button.append(body);
    button.addEventListener("click", () => {
      const isOpen = fields.stageDrawer.dataset.openStage === def.key && !fields.stageDrawer.hidden;
      document.querySelectorAll(".ai-stage").forEach((node) => node.classList.remove("ai-stage--open"));
      if (isOpen) {
        fields.stageDrawer.hidden = true;
        fields.stageDrawer.dataset.openStage = "";
        return;
      }
      item.classList.add("ai-stage--open");
      fields.stageDrawer.dataset.openStage = def.key;
      renderStageDrawer(def.key, groups);
    });
    item.append(button);
    fields.pipelineStages.append(item);
  });
}

/* ------------------------------------------------------------------ */
/* Agent 卡片网格 + 详情抽屉                                             */
/* ------------------------------------------------------------------ */

function agentDisplay(agent) {
  const meta = AGENT_META[agent.agent_name] || { label: agent.agent_name, desc: "Specialist analysis module" };
  const stance = STANCE_META[agent.stance] || { label: agent.stance || "--", tone: "muted" };
  return { meta, stance };
}

function renderAgentDrawer(agent) {
  const drawer = fields.agentDrawer;
  drawer.innerHTML = "";
  const { meta, stance } = agentDisplay(agent);

  drawer.append(el("h4", "ai-drawer__title", `${meta.label} · details`));
  const statusLine = el("div", "ai-drawer__item");
  statusLine.append(
    el(
      "p",
      null,
      agent.status === "success"
        ? `Completed with score ${Number(agent.score).toFixed(1)}/100, stance ${stance.label.toLowerCase()}, confidence ${(Number(agent.confidence || 0) * 100).toFixed(0)}%.`
        : stance.label
    )
  );
  drawer.append(statusLine);

  const sections = [
    ["Key points", agent.key_points],
    ["Risks", agent.risks],
    ["Recommendations", agent.recommendations],
  ];
  sections.forEach(([title, items]) => {
    if (!items || !items.length) return;
    const block = el("div", "ai-drawer__item");
    block.append(el("strong", null, title));
    const list = el("ul", "ai-drawer__list");
    items.forEach((entry) => list.append(el("li", null, entry)));
    block.append(list);
    drawer.append(block);
  });

  if (agent.narrative) {
    const block = el("div", "ai-drawer__item");
    block.append(el("strong", null, agent.status === "success" ? "AI narrative" : "Agent note"));
    block.append(el("p", null, plainText(agent.narrative)));
    drawer.append(block);
  }

  drawer.hidden = false;
}

function renderAgents(payload) {
  const agents = (payload.data || {}).agent_outputs || [];
  fields.agentGrid.innerHTML = "";
  fields.agentDrawer.hidden = true;
  fields.agentDrawer.innerHTML = "";

  if (!agents.length) {
    fields.agentGrid.append(el("p", "ai-placeholder", "No agent output."));
    fields.agentCount.textContent = "idle";
    return;
  }

  const counts = agentStatusCounts(agents);
  fields.agentCount.textContent = agentCountSummary(counts);

  agents.forEach((agent, index) => {
    const { meta, stance } = agentDisplay(agent);
    const card = el("article", `ai-agent-card ai-agent-card--${agent.status === "success" ? stance.tone : "off"}`);
    const button = el("button", "ai-agent-card__inner");
    button.type = "button";

    const head = el("header", "ai-agent-card__head");
    head.append(el("strong", null, meta.label));
    head.append(el("span", "ai-agent-card__desc", meta.desc));
    button.append(head);

    if (agent.status === "success") {
      const scoreRow = el("div", "ai-agent-card__score");
      const bar = el("div", "ai-scorebar ai-scorebar--sm");
      const fill = el("div", `ai-scorebar__fill ai-scorebar__fill--${stance.tone}`);
      fill.style.width = `${Math.max(0, Math.min(100, Number(agent.score || 0)))}%`;
      bar.append(fill);
      scoreRow.append(bar);
      scoreRow.append(el("span", "ai-agent-card__scorenum", Number(agent.score).toFixed(1)));
      button.append(scoreRow);

      const chips = el("div", "ai-agent-card__chips");
      chips.append(el("span", `ai-badge ai-badge--${stance.tone}`, stance.label));
      chips.append(el("span", "ai-badge ai-badge--muted", `${(Number(agent.confidence || 0) * 100).toFixed(0)}% conf`));
      if ((agent.metadata || {}).narrative_source === "deterministic_fallback") {
        chips.append(el("span", "ai-badge ai-badge--amber", "Narrative fallback"));
      }
      button.append(chips);

      if ((agent.metadata || {}).narrative_source === "deterministic_fallback") {
        button.append(
          el(
            "p",
            "ai-agent-card__note",
            "The deterministic score was retained; the optional LLM explanation was unavailable."
          )
        );
      }

      const points = (agent.key_points || []).slice(0, 2);
      if (points.length) {
        const list = el("ul", "ai-agent-card__points");
        points.forEach((point) => list.append(el("li", null, point)));
        button.append(list);
      }
    } else if (agent.status === "error") {
      const chips = el("div", "ai-agent-card__chips");
      chips.append(el("span", "ai-badge ai-badge--red", "Failed"));
      button.append(chips);
      button.append(
        el(
          "p",
          "ai-agent-card__note",
          "This module hit a technical error and its score was excluded. Check the overall coverage status to see whether a partial rating remains available."
        )
      );
    } else {
      const chips = el("div", "ai-agent-card__chips");
      chips.append(el("span", `ai-badge ai-badge--${stance.tone}`, stance.label));
      button.append(chips);
      const note =
        agent.stance === "not_applicable"
          ? "This check does not apply to this fund type, so no score is invented for it."
          : "Required data is unavailable, so this check refuses to guess instead of scoring.";
      button.append(el("p", "ai-agent-card__note", note));
    }

    button.append(el("span", "ai-agent-card__more", "View details"));
    button.addEventListener("click", () => {
      const isOpen = fields.agentDrawer.dataset.openAgent === String(index) && !fields.agentDrawer.hidden;
      document.querySelectorAll(".ai-agent-card").forEach((node) => node.classList.remove("ai-agent-card--openx"));
      if (isOpen) {
        fields.agentDrawer.hidden = true;
        fields.agentDrawer.dataset.openAgent = "";
        return;
      }
      card.classList.add("ai-agent-card--openx");
      fields.agentDrawer.dataset.openAgent = String(index);
      renderAgentDrawer(agent);
    });

    card.append(button);
    fields.agentGrid.append(card);
  });
}

/* ------------------------------------------------------------------ */
/* 开发者层：coverage / 元数据 / technical JSON                          */
/* ------------------------------------------------------------------ */

function coverageCell(label, value) {
  const cell = el("div");
  cell.append(el("span", null, label));
  cell.append(el("strong", null, value === undefined || value === null || value === "" ? "--" : String(value)));
  return cell;
}

function renderDevPanel(payload) {
  const analysis = payload.data || {};
  const coverage = payload.coverage || {};
  const metadata = analysis.metadata || {};

  fields.runId.textContent = analysis.request_id || "no run yet";

  fields.devCoverage.innerHTML = "";
  fields.devCoverage.append(coverageCell("NAV points", coverage.nav_points));
  fields.devCoverage.append(coverageCell("Fund type", `${coverage.fund_type || "--"} → ${coverage.normalized_fund_type || "--"}`));
  fields.devCoverage.append(coverageCell("Data source", coverage.data_source));
  fields.devCoverage.append(coverageCell("Missing fields", (analysis.missing_fields || []).join(", ") || "none"));
  fields.devCoverage.append(coverageCell("Agent health", metadata.agent_health));
  fields.devCoverage.append(coverageCell("Successful tools", coverage.successful_backend_tools));
  fields.devCoverage.append(coverageCell("Errored tools", coverage.errored_backend_tools || "none"));
  const dataCoverage = coverage.data_coverage || {};
  fields.devCoverage.append(
    coverageCell(
      "Data coverage",
      Object.entries(dataCoverage)
        .map(([key, value]) => `${key}=${value}`)
        .join(" · ") || "--"
    )
  );

  fields.devMetadata.innerHTML = "";
  const metaKeys = [
    "llm_mode",
    "llm_model",
    "summary_source",
    "analysis_status",
    "rating_eligible",
    "rating_scored_agent_count",
    "rating_applicable_agent_count",
    "rating_coverage_ratio",
    "rating_expected_agents",
    "rating_policy_issue_agents",
    "min_rating_agent_count",
    "min_rating_coverage_ratio",
    "specialist_narrative_fallback_count",
    "narrative_health",
    "has_benchmark",
    "has_news_signal",
    "has_sector_context",
    "has_bond_exposure",
    "prompt_version",
    "average_confidence",
    "quant_metrics_sample_size",
    "quant_metrics_reliability",
    "agent_execution_mode",
    "agent_worker_count",
  ];
  metaKeys.forEach((key) => {
    if (metadata[key] === undefined) return;
    fields.devMetadata.append(el("li", null, `${key} = ${metadata[key]}`));
  });

  fields.technicalEvidence.innerHTML = "";
  const events = Array.isArray(analysis.analysis_trace) ? analysis.analysis_trace : [];
  if (!events.length) {
    fields.technicalEvidence.append(el("li", null, "No backend or agent trace has been recorded yet."));
    return;
  }
  events.forEach((event) => {
    const payloadText = JSON.stringify({
      category: event.category,
      evidence: event.evidence || {},
      technical: event.technical || {},
    });
    fields.technicalEvidence.append(el("li", null, `${event.title || "Analysis step"} · ${payloadText}`));
  });
}

function syncDevPanel() {
  if (!fields.devPanel || !fields.devToggle) return;
  fields.devPanel.hidden = !fields.devToggle.checked;
}

/* ------------------------------------------------------------------ */
/* 主流程                                                               */
/* ------------------------------------------------------------------ */

function renderResult(payload) {
  lastPayload = payload;
  renderVerdict(payload);
  renderQuantMetrics(payload);
  renderPipeline(payload);
  renderAgents(payload);
  renderDevPanel(payload);
}

function renderFailure(message) {
  resetResultState();
  fields.fundName.textContent = "Analysis failed";
  fields.fundMeta.textContent = message;
  fields.summary.textContent = message;
  fields.scoreExplanation.textContent = "No rating explanation available because the analysis request failed.";
  fields.quantMetrics.innerHTML = "";
  fields.quantMetrics.append(el("p", "ai-placeholder", "No metrics — the analysis request failed."));
  fields.metricsNote.textContent = "No metrics were computed because this analysis request failed.";
  fields.pipelineStages.querySelectorAll(".ai-stage").forEach((node) => {
    const stat = node.querySelector(".ai-stage__stat");
    if (stat) stat.textContent = "not run";
  });
  fields.agentGrid.innerHTML = "";
  fields.agentGrid.append(el("p", "ai-placeholder", message));
  fields.agentCount.textContent = "failed";
}

async function runAnalysis(event) {
  event.preventDefault();
  resetResultState();
  setStatus("Running…");
  if (fields.submitBtn) fields.submitBtn.disabled = true;

  const body = {
    code: fields.fundCode.value.trim(),
    start_date: fields.startDate.value,
    client_risk_profile: fields.riskProfile.value,
    mock: !fields.realLlm.checked,
    max_nav_points: 260,
    llm_timeout_seconds: fields.realLlm.checked ? 180 : 60,
    max_parallel_agents: fields.realLlm.checked ? 3 : 5,
  };
  if (fields.realLlm.checked && fields.llmModel && fields.llmModel.value) {
    body.llm_model = fields.llmModel.value;
  }

  try {
    const response = await fetch(endpoint(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const payload = await response.json();
    if (!response.ok || payload.code !== 200) {
      throw new Error(payload.message || `Request failed with ${response.status}`);
    }
    renderResult(payload);
    if (payload.message === "success_with_partial_coverage") {
      setStatus("Partial coverage", "warn");
    } else if (payload.message === "insufficient_data") {
      setStatus("Insufficient data", "warn");
    } else if (payload.message === "analysis_incomplete") {
      setStatus("Not rated", "warn");
    } else {
      setStatus("Complete");
    }
  } catch (error) {
    renderFailure(error.message);
    setStatus("Error", "warn");
  } finally {
    if (fields.submitBtn) fields.submitBtn.disabled = false;
  }
}

if (form) {
  form.addEventListener("submit", runAnalysis);
}
if (fields.realLlm) {
  fields.realLlm.addEventListener("change", syncRealLlmModelSelect);
}
if (fields.devToggle) {
  fields.devToggle.addEventListener("change", syncDevPanel);
}

syncDevPanel();
loadModelCatalog();
