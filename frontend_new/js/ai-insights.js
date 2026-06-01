const form = document.querySelector("[data-analysis-form]");
const statusPill = document.querySelector("[data-analysis-status]");
const sourceSummary = document.querySelector("[data-source-summary]");
const keyThesis = document.querySelector("[data-key-thesis]");
const mainRisks = document.querySelector("[data-main-risks]");
const actionPlan = document.querySelector("[data-action-plan]");
const agentRows = document.querySelector("[data-agent-rows]");

const fields = {
  fundCode: document.querySelector("[data-fund-code]"),
  startDate: document.querySelector("[data-start-date]"),
  riskProfile: document.querySelector("[data-risk-profile]"),
  realLlm: document.querySelector("[data-real-llm]"),
  overallRating: document.querySelector("[data-overall-rating]"),
  overallScore: document.querySelector("[data-overall-score]"),
  navCount: document.querySelector("[data-nav-count]"),
  missingCount: document.querySelector("[data-missing-count]"),
  llmMode: document.querySelector("[data-llm-mode]"),
  fundName: document.querySelector("[data-fund-name]"),
  fundWindow: document.querySelector("[data-fund-window]"),
  summary: document.querySelector("[data-summary]"),
  agentHealth: document.querySelector("[data-agent-health]"),
  successTools: document.querySelector("[data-success-tools]"),
  errorTools: document.querySelector("[data-error-tools]"),
};

function endpoint() {
  const params = new URLSearchParams(window.location.search);
  const base = params.get("agentBase") || window.FUNDMASTER_AGENT_BASE || "http://127.0.0.1:5003";
  return `${base.replace(/\/$/, "")}/api/ai/fund/analyze`;
}

function setStatus(text, state = "live") {
  statusPill.textContent = text;
  statusPill.classList.toggle("chip--warn", state === "warn");
  statusPill.classList.toggle("chip--live", state !== "warn");
}

function listItems(node, items) {
  node.innerHTML = "";
  if (!items || items.length === 0) {
    const li = document.createElement("li");
    li.textContent = "No output.";
    node.append(li);
    return;
  }
  items.forEach((item) => {
    const li = document.createElement("li");
    const strong = document.createElement("strong");
    strong.textContent = item;
    li.append(strong);
    node.append(li);
  });
}

function renderAgents(agents) {
  agentRows.innerHTML = "";
  if (!agents || agents.length === 0) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 5;
    cell.textContent = "No agent output.";
    row.append(cell);
    agentRows.append(row);
    return;
  }
  agents.forEach((agent) => {
    const row = document.createElement("tr");
    [
      agent.agent_name,
      agent.stance,
      agent.score == null ? "--" : Number(agent.score).toFixed(1),
      `${Math.round(Number(agent.confidence || 0) * 100)}%`,
      agent.status,
    ].forEach((value) => {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.append(cell);
    });
    agentRows.append(row);
  });
}

function renderResult(payload) {
  const analysis = payload.data || {};
  const coverage = payload.coverage || {};
  const metadata = analysis.metadata || {};
  fields.overallRating.textContent = String(analysis.overall_rating || "--").toUpperCase();
  fields.overallScore.textContent = Number(analysis.overall_score || 0).toFixed(1);
  fields.navCount.textContent = coverage.nav_points ?? "--";
  fields.missingCount.textContent = (analysis.missing_fields || []).length;
  fields.llmMode.textContent = metadata.llm_mode || "unknown";
  fields.fundName.textContent = coverage.fund_name || "Unknown fund";
  fields.fundWindow.textContent = analysis.request_id || "Analysis completed.";
  fields.summary.textContent = analysis.summary || "Analysis completed.";
  fields.agentHealth.textContent = metadata.agent_health || "ready";
  fields.successTools.textContent = coverage.successful_backend_tools || "--";
  fields.errorTools.textContent = coverage.errored_backend_tools || "--";

  sourceSummary.replaceChildren();
  const sourceName = document.createElement("strong");
  sourceName.textContent = coverage.fund_name || fields.fundCode.value.trim();
  const sourceMeta = document.createElement("span");
  sourceMeta.textContent = `${coverage.nav_points || 0} NAV points · ${coverage.fund_type || "unknown"} · ${coverage.data_source || "backend"}`;
  sourceSummary.append(sourceName, sourceMeta);

  listItems(keyThesis, analysis.key_thesis);
  listItems(mainRisks, analysis.main_risks);
  listItems(actionPlan, analysis.action_plan);
  renderAgents(analysis.agent_outputs);
}

async function runAnalysis(event) {
  event.preventDefault();
  setStatus("Running");
  fields.agentHealth.textContent = "running";
  const body = {
    code: fields.fundCode.value.trim(),
    start_date: fields.startDate.value,
    client_risk_profile: fields.riskProfile.value,
    mock: !fields.realLlm.checked,
    max_nav_points: 260,
    llm_timeout_seconds: fields.realLlm.checked ? 180 : 60,
    max_parallel_agents: fields.realLlm.checked ? 3 : 5,
  };

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
    setStatus("Complete");
  } catch (error) {
    setStatus("Error", "warn");
    fields.fundName.textContent = "Analysis failed";
    fields.fundWindow.textContent = error.message;
    fields.overallRating.textContent = "--";
    fields.overallScore.textContent = "--";
    fields.navCount.textContent = "--";
    fields.llmMode.textContent = "--";
    fields.summary.textContent = error.message;
    fields.agentHealth.textContent = "failed";
    fields.successTools.textContent = "--";
    fields.errorTools.textContent = "--";
  }
}

if (form) {
  form.addEventListener("submit", runAnalysis);
}
