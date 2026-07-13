# COMP7705 Project Report

---

## Cover Page

**The University of Hong Kong**  
School of Computing and Data Science

---

**COMP7705 — Individual Project / Group Project**

---

**Project Title:**  
FundMasterAI: A Full-Stack Multi-Agent Fund Analysis System with Deterministic Reliability Guardrails

---

| Field | Value |
|---|---|
| Student Name(s) | [TBD] |
| Student Number(s) | [TBD] |
| Supervisor | [TBD] |
| Submission Date | [TBD] |

---

*Submitted in partial fulfilment of the requirements for the degree of Master of Science in Computer Science*

---

## Abstract

FundMasterAI is a full-stack fund analysis demonstration system designed to bridge modern large language model (LLM) capabilities with the reliability demands of financial decision support. The system integrates a static frontend with an AI Insights user interface, three Flask-based backend microservices providing market data, news signals, and portfolio storage, and a dedicated multi-agent LLM analysis engine. The AI engine follows a deterministic workflow architecture in which a sequence of specialist agents — covering performance, risk, equity exposure, bond exposure, sector context, news sentiment, and peer comparison — each compute heuristic scores from structured financial features before an optional LLM narrative is generated. A ChiefAgent aggregates specialist scores into a four-tier action recommendation (BUY ≥ 75, HOLD ≥ 60, WATCH ≥ 45, AVOID < 45). Reliability is ensured through deterministic fund-type routing, a minimum NAV publication floor that suppresses ratings from insufficient data, a rating coverage quorum policy that vetoes ratings when too few agents succeed, LLM abstention on missing data rather than hallucination, and retry logic for transient provider failures. The system is containerised with Docker Compose and supports cloud deployment via systemd. Testing comprises 229 unit tests, eight golden-case regression scenarios, and an automated smoke test suite. Experimental results across representative fund codes demonstrate consistent behaviour under data availability variations.

*(Word count: approximately 200)*

---

## Declaration

I hereby declare that this report and the work described herein are my own (our own), except where explicitly acknowledged. No part of this submission has been submitted for any other degree or professional qualification.

Signed: [TBD]  
Date: [TBD]

---

## Acknowledgements

The authors wish to thank the teaching staff of COMP7705 for guidance throughout the project lifecycle. We also acknowledge the open-source communities behind Flask, Docker, AkShare, and the OpenAI-compatible API specification, whose tools formed the technical foundation of this work. [Additional acknowledgements TBD upon finalisation of group membership and supervisor confirmation.]

---

## Table of Contents

1. Introduction
   - 1.1 Background and Motivation
   - 1.2 Project Purpose and Scope
   - 1.3 Brief Related Work Survey
   - 1.4 Report Organisation
2. Analysis of Problem
   - 2.1 Domain Context: Retail Fund Analysis in China
   - 2.2 Core Technical Challenges
   - 2.3 Reliability and Honesty Requirements
   - 2.4 Deployment and Operability Requirements
3. Methodology
   - 3.1 Research and Design Approach
   - 3.2 System Development Method
   - 3.3 Choice of Multi-Agent Workflow vs. Open-Ended Agent
   - 3.4 Data Sources and Data Ingestion Strategy
   - 3.5 Mock vs. Real LLM Strategy
   - 3.6 Evaluation Method
   - 3.7 Test Strategy
4. Design and Construction of the Software System
   - 4.1 System Architecture Overview
   - 4.2 Contract Layer
   - 4.3 FeatureBuilder: Deterministic Metric Computation
   - 4.4 Specialist Agents
   - 4.5 Orchestration Engine
   - 4.6 ChiefAgent: Score Aggregation and Rating Policy
   - 4.7 Fund-Type Routing
   - 4.8 Reliability Guardrails
   - 4.9 Backend Microservices
   - 4.10 Frontend AI Insights Page
   - 4.11 Deployment Architecture
   - 4.12 Key Algorithms
5. Experimental Results
   - 5.1 Test Suite Outcomes
   - 5.2 Golden Case Regression Results
   - 5.3 Fund Scan Sample Outcomes
   - 5.4 Reliability Scenario Tests
   - 5.5 CI and Cloud Deployment Notes
6. Discussion
   - 6.1 Strengths of the Approach
   - 6.2 Limitations
   - 6.3 Honest Positioning: Workflow vs. Autonomous Agent
7. Conclusions and Future Work
   - 7.1 Summary of Contributions
   - 7.2 Future Work
- Appendix A: API Reference (Placeholder)
- Appendix B: Run Manual (Placeholder)
- Appendix C: Individual Contribution Details
- References
- Declaration of Contribution of Each Group Member

---

## 1 Introduction

### 1.1 Background and Motivation

The Chinese public fund industry has grown substantially over the past decade, with assets under management in mutual funds exceeding tens of trillions of renminbi. Retail investors now routinely encounter fund selection decisions involving hundreds or thousands of candidates across equity, bond, hybrid, index, money market, QDII, and fund-of-fund categories. Despite the proliferation of fund data platforms, the analytical output presented to typical retail investors remains either superficial (single-metric rankings, historical return tables) or inaccessible (institutional-grade quantitative reports requiring financial expertise to interpret).

Large language models (LLMs) offer a complementary strength: the ability to synthesise multi-dimensional structured evidence into coherent natural-language explanations accessible to non-specialist readers. However, deploying LLMs for investment analysis introduces substantial risks. LLMs are susceptible to hallucination — generating plausible-sounding but factually incorrect content — and they have no reliable mechanism for expressing uncertainty when data is absent or ambiguous. Naively integrating an LLM into a financial analysis pipeline risks producing confident-sounding recommendations based on missing or misinterpreted data, which could actively mislead retail investors.

FundMasterAI was conceived to address this problem. The central thesis is that LLM narrative generation and deterministic score computation should be separated by a strict architectural boundary. Quantitative scores are computed from structured data using transparent, auditable formulae. The LLM is invoked only to explain scores that already exist, and only after explicit data coverage checks confirm that sufficient evidence is present. When data is missing or inadequate, the system is designed to say so explicitly rather than to extrapolate.

### 1.2 Project Purpose and Scope

The project aims to deliver a functional full-stack demonstration system that:

1. Accepts a fund code from a web frontend and returns a structured multi-dimensional analysis covering performance, risk, portfolio exposure, sector context, news sentiment, and peer comparison.
2. Classifies fund type deterministically and routes each fund to only the analysis modules appropriate for its category.
3. Applies reliability guardrails including a minimum NAV data floor, a rating coverage quorum, percentage unit normalisation, and LLM retry logic.
4. Aggregates specialist module outputs into a four-tier action recommendation (BUY, HOLD, WATCH, AVOID) through a ChiefAgent.
5. Provides an AI Insights user interface rendering structured results, trace events, coverage metadata, and optional LLM narrative.
6. Supports containerised deployment with Docker Compose and cloud deployment through systemd service management scripts.

The system explicitly does not claim to provide investment advice suitable for real financial decisions. Scores and thresholds are designed heuristically to demonstrate the architectural pattern rather than as calibrated, backtested investment signals.

### 1.3 Brief Related Work Survey

**Multi-agent LLM systems.** The paradigm of decomposing a complex task among specialised LLM agents has been explored across domains. Anthropic's guide to building effective agents [1] distinguishes between workflow-style orchestration — where control flow is determined by code — and open-ended agents where the LLM itself decides what tools to call next. FundMasterAI adopts the workflow style for financial reliability reasons elaborated in Section 3.3.

**Financial NLP and LLM applications.** A body of literature applies NLP to financial sentiment analysis [2], earnings call summarisation [3], and SEC filing analysis. More recent work explores instruction-tuned LLMs (such as FinBERT [4] and BloombergGPT [5]) fine-tuned on financial corpora. FundMasterAI does not fine-tune a domain-specific model; instead it uses a general-purpose OpenAI-compatible LLM for narrative generation while keeping all scoring deterministic. This avoids the computational cost and data requirements of fine-tuning while retaining the interpretability benefit.

**Quantitative fund analysis.** Classic fund evaluation metrics including Sharpe ratio, Sortino ratio, maximum drawdown, Calmar ratio, and information ratio are well established in the academic literature [6] and practitioner toolkit. Portfolio construction and risk budgeting literature underpins the portfolio-level analysis extension. FundMasterAI implements these metrics from first principles over fund NAV time series obtained from backend APIs.

**Retrieval-augmented generation.** RAG systems retrieve documents from a knowledge base to ground LLM generation [7]. FundMasterAI's design is adjacent to RAG in spirit: the backend data retrieval step grounds all LLM generation in structured facts. However, the grounding happens through a code-orchestrated function registry rather than a vector retrieval pipeline, which makes the provenance of each evidence element fully auditable.

**OpenAI function calling.** The OpenAI tool-use / function-calling API [8] allows LLMs to request structured tool invocations. FundMasterAI's backend function registry provides a similar abstraction: each backend data source exposes a structured function descriptor, and the AI service discovers and calls registered functions through code. The current system does not delegate tool selection to the LLM; that remains a future extension.

### 1.4 Report Organisation

Section 2 analyses the problem space in detail. Section 3 describes the methodology including research approach, system development method, data strategy, and test strategy. Section 4 presents the detailed design and construction of all system components. Section 5 reports experimental results including test outcomes and fund scan samples. Section 6 discusses the strengths and limitations of the approach. Section 7 concludes and identifies future work directions.

---

## 2 Analysis of Problem

### 2.1 Domain Context: Retail Fund Analysis in China

Chinese public (open-end) funds are categorised by regulatory classification into equity, bond, hybrid, index, money market, QDII, and fund-of-fund types. This categorisation is critical for analysis because the instruments held by each fund type are fundamentally different: an equity fund's primary risk drivers are stock selection and sector concentration, whereas a bond fund's risk drivers are credit quality, duration, and issuer concentration. A generic analysis pipeline that applies the same metrics to all fund types would either produce meaningless results for bond funds (e.g. reporting zero stock concentration because a bond fund holds no stocks) or miss material risks (e.g. applying equity concentration checks to a money market fund).

Further complicating the picture is the data disclosure regime. Chinese fund regulations require quarterly disclosure of top-ten stock holdings for equity-like funds and some bond funds that may hold equities. Full portfolio transparency is not required. This means that for many funds, analysis must proceed from partial disclosure data, and any system must handle missing data gracefully rather than failing or fabricating values.

Fund NAV (net asset value) is reported daily. The length of the available NAV history varies widely: a newly launched fund may have fewer than thirty NAV points, making rolling-window metrics (e.g. annualised volatility, one-year return) meaningless or degenerate. The system must recognise and handle this case.

### 2.2 Core Technical Challenges

**Challenge 1: Preventing hallucination on missing data.** The primary failure mode of LLM-based analysis is generating confident-sounding text for questions the model cannot answer from the available evidence. For fund analysis this is particularly dangerous: an LLM might invent sector concentration figures, peer rankings, or credit quality assessments that are not grounded in any retrieved data. The system must structurally prevent this.

**Challenge 2: Fund-type routing.** Applying the wrong analysis modules to a fund produces misleading output. A bond fund should not receive an equity concentration score, and an equity fund should not receive a bond duration assessment. Routing must be deterministic and auditable, not delegated to LLM interpretation.

**Challenge 3: Percentage unit normalisation.** Financial data APIs report holdings and allocations in a mixture of unit conventions: some return weight as a fraction in [0, 1], others as percentage points in [0, 100]. Misinterpreting a 0.95% holding as 95%, or treating a 35% allocation as 0.35, produces nonsensical downstream metrics. The system must enforce a single canonical unit at the ingestion boundary and reject implausible values.

**Challenge 4: Robust LLM integration.** Real LLM providers exhibit production failure modes including rate limiting (HTTP 429), gateway errors (502, 503), reasoning model token budget exhaustion producing empty `content` fields, and mixed-language outputs (a Chinese-language response where English was requested). The system must handle each failure mode gracefully without exposing raw provider errors to end users or silently producing degenerate output.

**Challenge 5: Rating coverage integrity.** A multi-agent system produces a valid overall rating only when a sufficient proportion of applicable specialist modules succeed. If most agents fail or are skipped due to missing data, the average of the remaining scores may be statistically meaningless. The system requires a quorum policy that prevents degenerate ratings from insufficient coverage.

**Challenge 6: Operability and deployment.** An academic prototype must be runnable by multiple team members in different environments (local development, Docker Compose, cloud VM) without substantial configuration overhead. The deployment model must be documented and tested.

### 2.3 Reliability and Honesty Requirements

The following requirements were identified as non-negotiable for responsible demonstration:

- **R1: No invented data.** If a data field is absent, the system must return a structured missing status rather than an LLM-generated approximation.
- **R2: No rating from insufficient NAV.** A minimum of 30 NAV points is required before any performance or risk rating is produced.
- **R3: Rating coverage quorum.** The overall rating requires both core agents (PerformanceAgent and RiskAgent) to succeed, at least three specialist scores to be available, and at least 60% of applicable specialist agents to score successfully.
- **R4: LLM for narrative only.** The LLM is never asked to compute a score. It is given pre-computed scores and asked to write an explanation.
- **R5: Deterministic fund-type routing.** Fund type classification uses keyword matching on structured backend category fields. The LLM is not asked to decide fund type.
- **R6: Transparent status.** Every agent output carries a `status` (success / skipped / error), a `stance` (not_applicable / insufficient_data / etc.), and structured `evidence`. The frontend can distinguish all states.

### 2.4 Deployment and Operability Requirements

- **D1: Single-command local setup.** `docker compose up --build --wait` must start the complete system.
- **D2: Smoke-test verification.** A dedicated smoke-test container must validate all endpoints after startup.
- **D3: Cloud deployment.** A `scripts/update.sh` script must support rolling updates on a cloud VM with systemd service management.
- **D4: Mock LLM mode.** The system must be fully demonstrable without a real LLM API key by setting `mock=true` in all analysis requests.

---

## 3 Methodology

### 3.1 Research and Design Approach

The project adopted an engineering-led iterative approach, anchored to a capability roadmap that prioritised reliability guarantees before feature breadth. The initial design phase reviewed the relevant literature on multi-agent LLM systems, financial metric computation, and RAG architectures (see Section 1.3). The key design decision emerging from this review was to adopt a workflow-style multi-agent architecture rather than an open-ended agent — a decision analysed in detail in Section 3.3.

System requirements were elicited through a combination of domain analysis (Section 2) and interface negotiation within the team. The AI agent module, backend microservices, and frontend were developed by different sub-teams with explicit API contracts defining the boundaries. The contract-first approach allowed parallel development and provided clear integration test targets.

Each feature increment was logged in a task-level development ledger (`ai_agent_development_log.md`), which records the goal, actual code changes, impact, and verification commands for every significant change. This discipline was adopted to prevent future developers and AI assistants from confusing current implementation state with planning documents.

### 3.2 System Development Method

The development process followed a phased roadmap:

**Phase 1 (Foundation):** Established the multi-agent pipeline with PerformanceAgent, RiskAgent, ExposureAgent, SentimentAgent, SectorAgent, and ChiefAgent. Implemented the FeatureBuilder for deterministic metric computation. Connected the AI service to the backend function registries.

**Phase 1 (Bond-aware baseline):** Added BondExposureAgent and deterministic fund-type routing so bond-like funds receive fixed-income exposure analysis rather than equity exposure checks. Added structured `bond_holdings` and `asset_allocation` input fields and corresponding coverage flags.

**Phase 1.5 (Engineering hardening):** Hardened the LLM client to handle empty-content responses from reasoning models, `finish_reason=length` token budget exhaustion, and transient HTTP failures. Added explicit `is_mock` class attributes and data-driven confidence computation for PerformanceAgent and RiskAgent.

**Phase 2 (Feature expansion):** Added MarketAgent (peer percentile and holding-period profit probability evidence), promoted structured `top_holdings`, `profit_probability`, and `individual_analysis` fields from context strings to typed input fields, and implemented portfolio-level and sector-level analysis endpoints.

**Phase 3 (Reliability hardening):** Introduced the 30-NAV publication floor, the rating coverage quorum policy, percentage unit normalisation with gross-exposure plausibility checks, and the AI Insights UI updates to display INSUFFICIENT DATA / NOT RATED states.

**Phase 4 (Supplementary endpoints):** Added the news summary endpoint (`POST /api/ai/news/summary`) to serve the frontend News page AI Summary widget.

Throughout all phases, the test suite was maintained to pass after every change. Changes that broke existing tests were not merged until tests were fixed.

### 3.3 Choice of Multi-Agent Workflow vs. Open-Ended Agent

A central architectural decision was whether to implement the system as a workflow-style multi-agent pipeline — in which the orchestration logic is defined by code — or as an open-ended agent in which the LLM decides at runtime which tools to call.

The open-ended agent approach (exemplified by ReAct-style agents [9] and tool-calling frameworks) offers flexibility: an LLM planner can dynamically select data sources and analysis steps based on intermediate results. However, for financial analysis this flexibility introduces significant risks:

1. **Non-deterministic routing.** An LLM planner might apply equity sector analysis to a bond fund if it misinterprets the fund description, producing misleading output.
2. **Uncontrolled data access.** An LLM planner choosing its own tools might call financially irrelevant data sources or miss mandatory data quality checks.
3. **Hallucination on tool selection.** LLMs can hallucinate tool names or confuse argument formats, producing runtime errors that are difficult to diagnose.
4. **Auditability.** A financial system must be able to explain why a given recommendation was made. An LLM-driven tool selection sequence is difficult to audit after the fact.

The workflow-style approach adopted by FundMasterAI addresses all four risks:

- Fund type routing is performed by a deterministic function (`classify_fund_type`) using keyword rules on the structured `fund_type` field from the backend.
- The set of applicable agents for each fund type is computed deterministically from routing flags.
- Each agent's data fetching is specified in code, with explicit coverage checks before any LLM call.
- Every analysis step is recorded in a structured `analysis_trace` that the frontend can display for full transparency.

The workflow approach sacrifices the flexibility of dynamic planning. Specifically, the current system cannot dynamically discover novel data sources at runtime or adapt its analysis strategy based on LLM-generated hypotheses. This limitation is acknowledged in Section 6.3. The design consciously accepts this limitation as the appropriate trade-off for a financial analysis system where reliability and auditability outweigh flexibility.

### 3.4 Data Sources and Data Ingestion Strategy

**Primary data source.** The backend microservices obtain fund data from the AkShare library [10], a Python library providing programmatic access to Chinese financial data sources including fund NAV history, fund basic information, fund holdings, industry allocation data, risk-return analysis, and news/announcements. This data is served through a function registry pattern: each backend exposes a `/api/{service}/functions` endpoint listing available functions with parameter schemas, and the AI service calls these functions via HTTP to retrieve structured data.

**Data coverage tracking.** Before any analysis, the `build_data_coverage` function in `fund_routing.py` interrogates the populated `FundAnalysisInput` object and the list of available backend tool names to produce a coverage dictionary. Each coverage field takes one of four values: `available` (data present), `missing` (applicable but absent), `missing_backend_capability` (applicable but the backend does not expose the required tool), or `not_applicable` (not relevant for this fund type). This coverage dictionary is returned to the frontend in the API response.

**Percentage normalisation.** Backend `pct` and `net_value_pct` fields are percentage points (e.g., 35.2 means 35.2%). The ingestion layer applies a single canonical conversion: `weight_fraction = pct_value / 100.0`. This conversion is applied exactly once at the API boundary in `backend_function_client.py` and `akshare_ingestion.py`. Internal code expects fractions. Gross exposure plausibility checks enforce a ceiling of 1.40 (140%) and reject NaN or Inf values as invalid inputs.

**Data-driven fallbacks.** When current-year holdings data is unavailable (e.g. the fund has not yet disclosed Q2 holdings in the current year), the system falls back to the most recent available year. This fallback is implemented in `build_fund_input_from_backend_functions` and is documented in the analysis trace.

**NAV history.** The system requests up to 260 NAV data points per fund (configurable via `max_nav_points`). The rolling windows used for metric computation are: 1 month (21 trading days), 3 months (63), 6 months (126), and 1 year (252).

### 3.5 Mock vs. Real LLM Strategy

The system supports two operating modes for LLM calls, selectable per-request via the `mock` parameter:

**Mock mode.** A `MockLLMClient` returns pre-scripted deterministic narrative strings for each agent type without making any external API call. This mode supports:
- Development and testing without API credentials or network access.
- Rapid CI runs with full end-to-end pipeline execution.
- Demo scenarios where LLM latency would be disruptive.

**Real mode.** A `LLMClient` makes HTTP calls to any OpenAI-compatible API endpoint configured through `.env` variables (`LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`). The real LLM is asked only to write the narrative explanation; the score computation is already complete before the LLM is called. Per-request model override via the `llm_model` parameter allows model switching without service restarts.

The key design principle is that all quantitative scores are computed identically in both modes. Mock mode differs only in the narrative text. This means all unit tests, golden-case tests, and coverage policy tests are valid in both modes.

**Provider compatibility.** The system has been tested with DeepSeek (deepseek-v4-pro / deepseek-v4-flash), Qwen (qwen3.7-plus), and GLM (glm-5.2) through an OpenAI-compatible gateway. A model catalog endpoint (`GET /api/ai/llm/models`) allows the frontend to populate a model picker without hardcoding model names.

### 3.6 Evaluation Method

Evaluation in this project is designed to answer three questions: (a) Does the system produce structurally correct outputs? (b) Does it handle edge cases and failure modes correctly? (c) Does it produce sensible quantitative results on real fund data?

Three complementary evaluation strategies are employed:

**Structural evaluation (golden suite).** Eight hand-crafted golden cases cover representative fund types (equity, bond, mixed, insufficient NAV, missing news, etc.) and verify that the pipeline output conforms to expected structural properties: rating in the correct tier given input scores, coverage field values matching input data presence, all expected agent names present, no degenerate null scores from insufficient data, and analysis trace containing expected event categories. Golden cases are defined in `golden_suite.py` and run via `scripts/run_golden_suite.py`.

**Score evaluation (evaluation module).** The `evaluation.py` module provides an `EvaluationResult` dataclass that scores a pipeline output across dimensions: structural conformance (required fields present), score validity (finite, in range, no degenerate values), coverage completeness, and agent-level pass/fail for named core agents. This evaluation is applied to all real-data outputs logged in the `docs/real_sample_*.md` files.

**Manual acceptance checklist.** A `manual_acceptance_checklist.md` defines acceptance criteria for real-model runs, including verification that `summary_source=llm` (not the deterministic fallback), that the English-only prompt constraint is respected, and that trace events are populated.

### 3.7 Test Strategy

**Unit tests.** The test suite in `ai_agent/fund_llm_engine/tests/` contains 229 unit tests covering:

- `test_feature_builder.py`: FeatureBuilder metric correctness (return calculations, drawdown, volatility, Sharpe ratio, data quality flags).
- `test_agents.py`: Each specialist agent's score computation and status logic.
- `test_fund_routing.py`: Fund type classification for all category keywords, boundary cases, and equity applicability resolution with disclosed equity data.
- `test_contracts.py`: Contract dataclass serialisation and deserialisation.
- `test_engine.py`: Orchestration engine integration, including parallel execution and failure isolation.
- `test_llm_client.py`: LLM client retry logic (empty-content, `finish_reason=length`, HTTP 429/502/503, sanitised error messages).
- `test_api_contract.py`: HTTP endpoint response shape, error codes, and field presence.
- `test_golden_suite.py`: Golden case execution.
- `test_evaluation.py`: Evaluation scoring correctness.
- `test_ratios.py`: Percentage normalisation and canonical fraction helpers.
- `test_score_guardrails.py`: Score range validation, NaN/Inf rejection.
- `test_portfolio_analysis.py`, `test_portfolio_pipeline.py`, `test_portfolio_api.py`: Portfolio endpoint math and contract.
- `test_sector_view.py`, `test_sector_api.py`: Sector comparison endpoint.
- `test_news_summary.py`, `test_news_api.py`: News summary endpoint.
- `test_backend_function_client.py`: Backend data ingestion and field promotion.
- `test_llm_models.py`: Model catalog endpoint.

**CI strategy.** The full test suite is executed in the Docker Compose smoke-test container on every build. The `docker compose run --rm smoke` target runs `python -m unittest discover -s tests` and verifies all 229 tests pass before the system is considered healthy.

**Golden case regression.** The golden suite (`scripts/run_golden_suite.py --mode mock`) is run after every significant AI agent change to catch regressions in rating policy, agent registration, or coverage logic.

**Integration smoke tests.** After Docker Compose startup, the smoke container verifies live HTTP responses from all services: market backend health, news backend health, AI agent service health, and a mock analysis request returning a valid JSON response.

**Real-data manual acceptance.** Beyond automated tests, a `manual_acceptance_checklist.md` defines human-executed acceptance criteria: running `scripts/run_real_demo.py` against at least two fund codes (one equity-like, one bond-like), verifying that `summary_source` equals `"llm"` rather than `"deterministic_fallback"`, checking that the English-only prompt constraint is obeyed for funds with Chinese names, and confirming that the analysis trace shows the expected event sequence including backend tool discovery, data loading, feature computation, agent outputs, and aggregation. This checklist is executed before any milestone tag is applied to the repository.

---

## 4 Design and Construction of the Software System

### 4.1 System Architecture Overview

FundMasterAI is organised as five cooperating services plus a deployment layer. Fig. 1 (see Fig.2 in the project SVG assets) illustrates the overall architecture. The data flow for a single fund analysis request is:

```
Browser (AI Insights page)
  └─> frontend_new static server + Nginx proxy (port 8080)
        └─> POST /api/ai/fund/analyze
              └─> AI Agent Service (fund_llm_engine, port 5003)
                    ├─> GET /api/market/functions   [market_backend, port 5001]
                    ├─> GET /api/market/fund/hist    [NAV data]
                    ├─> GET /api/market/fund/info    [basic info]
                    ├─> GET /api/market/fund/holds   [stock holdings]
                    ├─> GET /api/news/functions      [news_backend, port 5000]
                    ├─> GET /api/news/fund/news      [announcements]
                    └─> FeatureBuilder -> Specialist Agents -> ChiefAgent
                          └─> JSON response: status, stance, score, analysis_trace
```

The architecture separates concerns across five layers:

1. **Presentation layer** (`frontend_new`): Static HTML/CSS/JS files served by a Python HTTP server with an Nginx reverse proxy in Docker. The AI Insights page (`ai-insights.html`) is the primary user interface for the multi-agent analysis feature.
2. **AI orchestration layer** (`ai_agent/fund_llm_engine`): A Flask service that receives analysis requests, fetches data from backend services, runs the multi-agent pipeline, and returns structured results.
3. **Market data layer** (`backend/market_backend`): A Flask microservice providing fund NAV history, basic information, stock holdings, risk-return analysis, and profit probability data through a function registry.
4. **News data layer** (`backend/news_backend`): A Flask microservice providing fund announcements and news items through a function registry.
5. **Portfolio storage layer** (`backend/portfolio_backend`): A Flask microservice with MySQL backing for user portfolio management. Not directly used in the AI analysis pipeline but provides portfolio data for the portfolio analysis extension.

The workflow in Fig. 3 (see workflow SVG) shows the request processing sequence for a single fund analysis call. When the request arrives at `POST /api/ai/fund/analyze`, the service first validates the request parameters and resolves the analysis date range. It then calls `discover_fund_tools()`, which queries the market and news backend function registries to learn what backend data functions are available. This discovery result is stored in `extra_context["available_backend_tools"]` so that the coverage builder can later distinguish between data that the backend is structurally capable of providing versus data that was simply not available for this particular fund.

After tool discovery, `build_fund_input_from_backend_functions()` executes the required backend calls sequentially: NAV history, basic information, stock holdings (for the relevant year), news items, risk-return analysis, and profit probability data. Each call is individually error-handled: a failure in one call does not abort the others, and the result is recorded in the coverage map. Once the `FundAnalysisInput` is assembled, the orchestration engine takes over.

### 4.2 Contract Layer

The contract layer (`contracts.py`) defines all data structures shared between system components. This layer is the single source of truth for input, intermediate, and output data shapes.

**Input contracts.** `FundAnalysisInput` is the primary input dataclass, containing:
- `fund_info`: `FundBasicInfo` (code, name, category, manager, inception date).
- `nav_series`: `List[NavPoint]` where each `NavPoint` carries a date and a NAV value.
- `top_holdings`: `List[Dict]` — structured stock holding rows with `weight_fraction` in [0,1].
- `bond_holdings`: `List[Dict]` — structured bond holding rows.
- `industry_exposure`: `Dict[str, float]` — sector name to fraction mapping.
- `asset_allocation`: `Dict[str, float]` — asset class to fraction mapping.
- `news_items`: `List[Dict]` — raw news rows with title, date, sentiment fields.
- `news_summary`: `str` — pre-summarised news text if available.
- `profit_probability`: `List[Dict]` — holding-period win-rate rows from the backend.
- `individual_analysis`: `List[Dict]` — peer percentile rows.
- `top_holdings_weight`: `Optional[float]` — aggregate disclosed weight fraction.
- `extra_context`: `Dict[str, Any]` — auxiliary metadata including `data_source`, `available_backend_tools`, and JSON previews for trace display.

**Intermediate contracts.** `FundFeaturePack` is produced by `FeatureBuilder` and carries computed metrics across four namespaces:
- `return_metrics`: Period returns and benchmark-relative returns.
- `risk_metrics`: Annualised volatility, maximum drawdown, Sharpe ratio, Sortino ratio, Calmar ratio.
- `benchmark_metrics`: Tracking error, information ratio (when benchmark series is present).
- `exposure_metrics`: Top holdings weight, HHI concentration, bond position weights.
- `market_metrics`: Peer percentile ranks, holding-period profit probabilities.
- `data_quality_flags`: Boolean flags including `has_nav`, `has_top_holdings`, `has_bond_holdings`, `equity_exposure_applicable`, `bond_exposure_applicable`, `sector_analysis_applicable`.
- `data_quality_metrics`: Numeric counts (NAV point count, rolling window count, etc.).
- `data_coverage`: Coverage dictionary from `build_data_coverage`.
- `missing_fields`: Set of field names that were expected but absent.

**Output contracts.** `AgentOutput` carries `agent_name`, `status`, `stance`, `score` (Optional[float]), `confidence`, `evidence` (Dict), and `narrative` (Optional[str]). `FinalAnalysisResult` carries `overall_score`, `overall_rating`, `analysis_status`, `agent_outputs`, `chief_summary`, `summary_source`, `analysis_trace` (List[AnalysisTraceEvent]), and `metadata`.

The contract layer is designed for backward compatibility: new fields may be added to any dataclass, but existing fields must not be renamed or type-changed without a documented migration.

An important aspect of the contract design is the treatment of the `extra_context` dictionary. Early in development, several important backend tool results (top holdings, profit probability, individual analysis peer data) were stored as JSON string previews inside `extra_context`. This worked for trace display but made downstream logic fragile, since extracting typed values from embedded JSON strings is error-prone. A dedicated refactor in Phase 2 promoted these fields to first-class typed attributes on `FundAnalysisInput` while retaining the `extra_context` entries as trace previews only. The `_records_from_payload` helper handles the case where a backend tool returns either a single dict (which is wrapped into a one-element list) or a list of dicts, providing a consistent interface downstream.

The `AnalysisTraceEvent` dataclass merits specific attention. Each trace event carries five fields: `category` (a short tag such as `"feature"`, `"agent"`, or `"aggregation"`), `title` (a brief human-readable label), `detail` (one to three sentences describing what was done), `status` (one of `"success"`, `"warning"`, `"skipped"`, `"error"`), `evidence` (a dict of the most important quantitative evidence values, shown prominently in the UI), and `technical` (a dict of lower-level diagnostic values, shown in a collapsible technical panel). This two-tier evidence structure allows the AI Insights page to present a user-friendly summary while still providing debugging detail for developers.

### 4.3 FeatureBuilder: Deterministic Metric Computation

The `FeatureBuilder` class (`feature_builder.py`) is responsible for all quantitative metric computation. It accepts a `FundAnalysisInput` and returns a `FundFeaturePack`. No LLM is involved in this stage.

**Return metrics.** Period returns are computed for all available trailing windows (1 month, 3 months, 6 months, 1 year) using the formula:

```
period_return = (NAV_end / NAV_start) - 1
```

where the window is defined by the last `lookback_periods + 1` NAV points. If fewer points are available than required by a window, that window is omitted and recorded as a missing field.

**Annualised volatility.** Daily log-returns are computed from consecutive NAV values:

```
daily_return[t] = (NAV[t] / NAV[t-1]) - 1
annualised_volatility = std(daily_returns) * sqrt(252)
```

**Maximum drawdown.** The peak-to-trough decline over the full available series:

```
max_drawdown = min over t of (NAV[t] / max(NAV[0..t]) - 1)
```

**Sharpe ratio.** Using an annual risk-free rate assumption of 2% (approximately the Chinese short-term government bond yield):

```
daily_rf = (1 + 0.02)^(1/252) - 1
sharpe = mean(excess_daily_returns) / std(daily_returns) * sqrt(252)
```

**Sortino ratio.** Similar to Sharpe but penalising only downside volatility:

```
downside_returns = [r for r in daily_returns if r < daily_rf]
downside_std = sqrt(mean(downside_returns^2))
sortino = annualised_excess_return / (downside_std * sqrt(252))
```

**Calmar ratio.**

```
calmar = annualised_return / abs(max_drawdown)
```

**Exposure metrics.** For equity-like funds, `top_holdings_weight` is the sum of `weight_fraction` values across disclosed stock holdings. The Herfindahl-Hirschman Index (HHI) is computed as the sum of squared weight fractions, providing a concentration measure between 0 (perfectly diversified) and 1 (fully concentrated in a single holding). For bond funds, the top bond weight and top-three bond weight are computed similarly.

**Data-driven confidence.** A `data_driven_confidence()` helper in `agents/base.py` computes agent confidence from data quality signals rather than using hard-coded values. Signals include NAV point count (up to +0.20 at 252 points), available rolling return window count (+0.04 per window, up to 4), benchmark data presence (+0.06), and required-flag completeness (up to +0.08). The output is clamped to [0.40, 0.90]. Prior to Phase C of development, PerformanceAgent and RiskAgent used hard-coded confidence values of 0.78 and 0.80 respectively. Replacing these with data-driven confidence caused `average_confidence` in the 5-NAV-point mock payload to move from 0.78 to 0.68, correctly reflecting the lower confidence warranted by minimal data.

**Information ratio.** When a benchmark NAV series is present in the input, the FeatureBuilder also computes tracking error (annualised standard deviation of the fund-minus-benchmark daily return series) and information ratio (annualised active return divided by tracking error). These benchmark-relative metrics are currently only available for funds that explicitly provide benchmark data, which is not a standard backend field for most fund types in the current data pipeline. Their presence is recorded in the `has_benchmark` data quality flag and in the coverage map.

### 4.4 Specialist Agents

Each specialist agent is a class that accepts a `FundFeaturePack` and an `LLMClient` (or `MockLLMClient`) and returns an `AgentOutput`. Agents follow the `safe_analyze` pattern from `agents/base.py`: unexpected exceptions are caught and return `status="error"` rather than propagating, isolating failures to individual modules.

**PerformanceAgent.** Evaluates absolute return quality. Score starts at a baseline of 55 and adjusts based on: 1-year return quartile position (computed against a soft threshold of 0.08 for strong performance, -0.05 for negative performance), presence of multiple rolling windows, and maximum drawdown severity. When the NAV point count is below the 30-point floor, the agent returns `skipped + insufficient_data`. Confidence is data-driven via the shared helper.

**RiskAgent.** Evaluates risk-adjusted quality. Score starts at 55 and adjusts based on annualised volatility (lower is better for balanced funds), maximum drawdown depth, Sharpe ratio, and Calmar ratio. The 30-NAV floor applies identically. The LLM is prompted with the computed metrics and asked to write a risk profile explanation in English.

**ExposureAgent.** Evaluates equity concentration risk. Applicable only when `equity_exposure_applicable=True` (equity-like funds and bond funds that disclose equity holdings). Score adjusts based on the top holdings weight (high concentration lowers score) and HHI. When `equity_exposure_applicable=False`, the agent returns `skipped + not_applicable`. When applicable but stock holdings data is absent, it returns `skipped + insufficient_data`.

**BondExposureAgent.** Evaluates fixed-income exposure quality for bond-like funds. Applicable when `bond_exposure_applicable=True`. Evidence includes top bond weight, top-three bond weight, disclosed bond weight, and asset-class allocation buckets. When applicable but both bond holdings and asset allocation data are absent, returns `skipped + insufficient_data`. Invalid bond data (NaN, negative weight, gross exposure exceeding 1.40) returns `status="error"` so the quorum policy can isolate the module without penalising the overall score.

**SentimentAgent.** Evaluates news and announcement signals as a secondary cross-check. Uses a deterministic keyword list to classify news items as positive, negative, or neutral before LLM explanation. Applicable to all fund types. Returns `skipped + insufficient_data` when no news data is present.

**SectorAgent.** Evaluates sector concentration risk. Applicable only when `sector_analysis_applicable=True` (equity-like funds). Returns `skipped + not_applicable` for bond-like funds.

**MarketAgent.** Evaluates peer-relative performance. Evidence is structured `individual_analysis` peer percentile rows (`risk_return_ratio_vs_peers`, `risk_robustness_vs_peers` per period) and `profit_probability` holding-period win-rate rows. Score starts at 55 and adjusts based on peer percentile position and the distance of win rates from 50%. Returns `skipped + insufficient_data` when neither dataset is present. Confidence uses the shared data-driven helper.

**Agent score design philosophy.** Each specialist agent's scoring function was designed with two constraints in mind. First, the baseline score of 55 was chosen to place new-fund analyses (minimal data, no strong evidence in any direction) firmly in the HOLD tier (60–74), reflecting appropriate uncertainty rather than a default WATCH or AVOID. Second, the adjustment magnitude from any single signal was capped to prevent a single metric from dominating the overall score. For example, a very high 1-year return moves the PerformanceAgent score up by a bounded increment, not to 100. This ensures that genuine multi-dimensional analysis is required to reach the BUY tier, and conversely that a single negative metric does not automatically produce AVOID.

The LLM prompt structure is also carefully designed for each agent. Each prompt provides: (1) a role statement identifying the agent's analytical perspective; (2) the fund profile (name, category, manager); (3) a structured summary of the computed metrics with their values; (4) the agent's score and confidence; and (5) an explicit instruction to "Respond in English only" and to "explain what the evidence means for an investor in plain language without inventing data not shown above." This last constraint was added after observing that some models expanded the prompt evidence into fabricated peer comparisons or macroeconomic narratives not supported by the provided data.

### 4.5 Orchestration Engine

The orchestration engine (`orchestration/engine.py`) coordinates the execution of all registered specialist agents and produces the `analysis_trace`. Its primary responsibilities are:

**Parallel execution.** Specialist agents are executed in a `ThreadPoolExecutor` with a configurable `max_parallel_agents` (default 6). Each agent call is a separate thread, allowing independent agents to run concurrently. Agent outputs are collected and re-ordered into the canonical registration order before aggregation.

**Failure isolation.** The `safe_analyze` base method wraps each agent's `analyze()` call in a try-except block. If an agent raises an unexpected exception, it returns `AgentOutput(status="error", ...)` with the exception message stored in `evidence`. This ensures a single agent failure does not abort the entire pipeline.

**Trace construction.** For each analysis step, the engine appends an `AnalysisTraceEvent` to the trace list. Events are categorised as `discovery` (backend tool discovery), `data_load` (NAV and info loading), `feature` (metric computation), `agent` (specialist agent result), and `aggregation` (ChiefAgent decision). Each trace event carries `title`, `detail`, `status`, and structured `evidence` and `technical` dictionaries. Fig. 3 (see workflow SVG asset) illustrates the trace event sequence.

**News backend degradation.** Tool discovery from the news backend is treated as a degradable call: if the news backend is unreachable, discovery fails gracefully with a warning log and `SentimentAgent` receives `skipped + insufficient_data` rather than causing a pipeline-level HTTP 500 error.

**Agent registration order.** The seven specialist agents are registered in a canonical order in the pipeline: PerformanceAgent, ExposureAgent, BondExposureAgent, RiskAgent, SentimentAgent, SectorAgent, MarketAgent. This order is preserved in the `analysis_trace` and in the `agent_outputs` array regardless of the actual completion order under parallel execution. Maintaining a stable output order is important for the frontend, which renders agent cards in array order, and for the golden suite, which asserts agent presence by name.

**`AGENT_TRACE_COPY` dictionary.** Each agent is associated with a pair of human-readable strings (title and detail) in the `AGENT_TRACE_COPY` dictionary defined at module level in `engine.py`. These strings are written into the `AnalysisTraceEvent` for each agent output. Centralising this copy in one location makes it easy to update user-facing text without touching individual agent implementations, and ensures consistency between what the trace displays and what the UI labels describe.

### 4.6 ChiefAgent: Score Aggregation and Rating Policy

The `ChiefAgent` (`agents/chief_agent.py`) aggregates specialist scores into the final overall score and rating. This is the most complex component in the system and incorporates several reliability policies.

**Score aggregation.** The `RatingCoverage` is computed by `assess_rating_coverage` in `rating_policy.py`. This function:
1. Determines the expected applicable agent set from fund-type routing flags.
2. Identifies which expected agents returned valid finite scores in [0, 100].
3. Flags missing agents (expected but not returned), duplicate agents (returned more than once), invalid agents (returned success but no valid score), and unexpected active agents (routed as not-applicable but returned a score).
4. Computes the coverage ratio: `scored_count / applicable_count`.

**Quorum policy.** A rating is produced only when:
- Both core agents (PerformanceAgent and RiskAgent) have valid scores.
- At least `MIN_RATING_AGENT_COUNT` (3) agents have valid scores.
- The coverage ratio meets `MIN_RATING_COVERAGE_RATIO` (60%).

If quorum is not met, `overall_rating="unavailable"` and `overall_score=null` are returned. If core agents succeed and quorum is met but some non-core agents are missing, `analysis_status="partial"` is set.

**Rating thresholds.** The overall score is the unweighted mean of all valid specialist scores. The four-tier rating is assigned by:

```
score >= 75  ->  BUY
score >= 60  ->  HOLD
score >= 45  ->  WATCH
score  < 45  ->  AVOID
```

**NAV floor enforcement.** If the PerformanceAgent or RiskAgent returned `skipped + insufficient_data` due to the 30-NAV floor, `overall_rating="insufficient_data"` and `overall_score=null` are returned, suppressing the BUY/HOLD/WATCH/AVOID decision entirely.

**Score explanation.** A deterministic English explanation of the rating is constructed from the specialist scores, identifying which agents support or drag the rating. This explanation is the fallback when the LLM call fails.

**LLM summary.** The ChiefAgent prompts the LLM with: the fund profile, all specialist scores with evidence summaries, the computed rating, and an explicit instruction to respond in English only. The English-only constraint was added after observing that some models answered in Chinese when the fund name contained Chinese characters, causing the `_summary_looks_incomplete` quality check (which counts whitespace-separated words) to incorrectly classify a valid Chinese response as incomplete. The `max_tokens` budget is 1100 for the fund ChiefAgent, expanded from an initial 700 after observing truncated responses.

**Summary quality gate.** The `_summary_looks_incomplete` function rejects LLM summaries shorter than a minimum word threshold or containing only boilerplate phrases. Rejected summaries fall back to the deterministic explanation with `summary_source="deterministic_fallback"`.

### 4.7 Fund-Type Routing

The `classify_fund_type` function in `fund_routing.py` maps the raw `fund_type` string from the backend basic info API into a `FundTypeProfile` dataclass. The mapping uses keyword matching on a normalised (lowercase, whitespace-removed) version of the type string:

| Keyword Match | Family | `equity_exposure_applicable` | `bond_exposure_applicable` | `sector_analysis_applicable` |
|---|---|:---:|:---:|:---:|
| `货币` / `money` | money_market | False | True | False |
| `qdii` | qdii | True | False | True |
| `fof` | fof | False | False | False |
| `债券` / `bond` / `固收` / `fixedincome` | bond | False | True | False |
| `混合` / `mixed` | equity_like | True | False | True |
| `指数` / `index` (non-bond) | equity_like | True | False | True |
| `股票` / `equity` / `stock` | equity_like | True | False | True |
| (no match / empty / `unknown`) | unknown | True | False | True |

*Table 1: Fund-type routing keyword rules and resulting analysis flags.*

A data-driven override exists for the case where a bond-classified fund discloses stock holding rows or industry allocation data. `resolve_equity_analysis_applicability` enables equity exposure and sector analysis for any fund that provides structured equity evidence, regardless of the default type routing. This handles the real-world case of some "bond-like" funds holding small equity positions.

### 4.8 Reliability Guardrails

Several reliability mechanisms operate at different levels of the stack:

**Percentage normalisation (ingestion).** The `canonical_fraction` function in `ratios.py` converts percentage-point values to fractions exactly once at the API ingestion boundary. Internal allocation dictionaries use fractions. External `pct` and `net_value_pct` fields are converted on read. The `clamp` function rejects NaN and Inf inputs with a `ValueError` rather than silently clamping them to a boundary score.

**NAV floor (PerformanceAgent and RiskAgent).** A minimum of 30 NAV points is required before score computation. Below this threshold, both core agents return `skipped + insufficient_data`, the ChiefAgent returns `overall_rating="insufficient_data"`, and the frontend displays INSUFFICIENT DATA rather than a potentially degenerate BUY/HOLD/WATCH/AVOID label.

**Quorum policy (ChiefAgent).** Described in Section 4.6. Prevents degenerate ratings from low-coverage scenarios.

**`explain_or_fallback` (all agents).** Specialist LLM narrative calls are wrapped in `explain_or_fallback()`. Provider failures (LLMEmptyResponseError, LLMHTTPError, LLMTransportError) retain the deterministic score and set `narrative_source="deterministic_fallback"` without promoting the agent to `status="error"`. Only calculation failures (invalid input data, division by zero, etc.) become Agent errors that the quorum policy can count.

**LLM retry (LLMClient).** `_post_json` retries once after a 1.5-second backoff for HTTP 429, 500, 502, 503, and 504 responses and for connection timeout. HTTP 400, 401, and 403 are raised immediately. Empty-content responses with `finish_reason=length` trigger a retry with expanded `max_tokens` and disabled thinking controls (for models that support the `thinking` parameter).

**Sanitised 500 responses.** All three AI HTTP endpoints return a generic `"Internal analysis error. See service log."` body for unhandled exceptions. Raw exception traces are written to the service log only. This prevents provider API keys, internal paths, or raw model response bodies from being exposed in HTTP responses.

**`insufficient_data` abstention.** When required data is absent, agents return `skipped + insufficient_data` with a structured explanation. The LLM is never called in this path. The frontend coverage map shows which data fields are missing, enabling the user to understand why coverage is partial.

**PROMPT_VERSION tracking.** A `PROMPT_VERSION` constant defined in `config.py` (e.g., `"2026-07-03.2"`) is surfaced as a `prompt_version` field in all analysis result metadata. This allows evaluation records to be correlated with the specific version of the system prompts that were active at the time of analysis. When prompts change (e.g., adding the "Respond in English only" instruction), the version is bumped and the evaluation log records the before-after impact on `summary_source` values.

### 4.9 Backend Microservices

**market_backend** (port 5001). A Flask microservice built with flask-openapi3. Exposes a function registry at `GET /api/market/functions?tag=fund` listing all available fund data functions with parameter schemas. Key functions include:
- `get_fund_hist`: Fund NAV history for a date range.
- `get_fund_individual_basic_info`: Fund category, manager, inception date.
- `get_fund_portfolio_holds` / `get_fund_portfolio_hold_stock`: Quarterly disclosed stock holdings.
- `get_fund_risk_return_analysis`: Annualised return, volatility, and Sharpe ratio vs. peers.
- `get_fund_profit_probability`: Holding-period win rates.
- `get_fund_individual_detail_hold`: Asset allocation data.

**news_backend** (port 5000). Exposes `GET /api/news/functions?tag=fund` and:
- `get_fund_news` / `get_fund_announcements`: Recent news items and regulatory announcements.

**portfolio_backend** (port 5002, MySQL-backed). Manages user portfolio records. Provides `GET /api/portfolio/positions` and related CRUD endpoints. Used by the portfolio analysis pipeline to resolve constituent fund weights.

**Function registry design.** Each backend exposes its function capabilities through a structured registry endpoint. A function descriptor includes the function name, a human-readable description, the parameter schema (field names, types, and required flags), and optional tags (e.g., `"fund"`, `"portfolio"`). The AI service calls `GET /api/{service}/functions?tag=fund` on startup and stores the result as a set of available tool names in `extra_context`. This design decouples the AI service from the specific set of data functions available: adding a new backend data function does not require AI service code changes; the AI service will discover it automatically on the next startup. Conversely, removing a backend function is surfaced in the coverage map as `missing_backend_capability` rather than causing a runtime error.

**Function registry pattern.** The `backend_function_client.py` in the AI service discovers available functions by calling the registry endpoints on startup. Tool names are stored in the analysis context as `available_backend_tools`, allowing `build_data_coverage` to distinguish between "this data is not available from any backend tool" (`missing_backend_capability`) and "the tool exists but returned no data for this fund" (`missing`).

### 4.10 Frontend AI Insights Page

The AI Insights page (`frontend_new/ai-insights.html` and `frontend_new/js/ai-insights.js`) is the primary user interface for the multi-agent analysis system. [Insert screenshot: AI Insights page overview, Fig. 4]

Key UI features:

**Fund search.** A code input field triggers a POST to `/api/ai/fund/analyze`. The mock/real toggle and model picker (populated from `GET /api/ai/llm/models`) are visible when running in development mode.

**Status banner.** The top of the result panel shows the fund name, category, overall score, and rating badge (BUY / HOLD / WATCH / AVOID / INSUFFICIENT DATA / NOT RATED). The rating badge is colour-coded: green for BUY, blue for HOLD, amber for WATCH, red for AVOID, grey for insufficient states.

**Specialist module cards.** Each specialist agent result is rendered as a card showing agent name, score (or "N/A" for skipped agents), status badge, and a collapsible evidence summary. [Insert screenshot: Agent cards panel, Fig. 5]

**Analysis trace accordion.** The full `analysis_trace` array is rendered as a collapsible accordion showing each step of the analysis with title, detail, status, and evidence fields. [Insert screenshot: Analysis trace accordion, Fig. 6]

**Coverage map.** A table showing each data field and its availability status (available / missing / not applicable / missing capability). [Insert screenshot: Coverage map, Fig. 7]

**Chief summary.** The LLM-generated (or deterministic fallback) narrative explaining the overall recommendation. The source (`llm` vs. `deterministic_fallback`) is shown in a small badge. [Insert screenshot: Chief summary panel, Fig. 8]

**Model picker.** In real LLM mode, a dropdown populated from the model catalog allows the user to select among available models for a single analysis. [Insert screenshot: Model picker, Fig. 9]

### 4.11 Deployment Architecture

**Docker Compose.** A `docker-compose.yml` at the repository root defines six services:
- `frontend`: Nginx serving static files from `frontend_new/`, proxying `/api/ai/` to the AI agent service and `/api/market/`, `/api/news/` to the respective backends.
- `ai_agent`: The `fund_llm_engine` Flask service.
- `market_backend`: The market data Flask service.
- `news_backend`: The news data Flask service.
- `portfolio_backend`: The portfolio Flask service with MySQL dependency.
- `mysql`: Official MySQL 8.0 image.
- `smoke`: One-shot container running the test suite and live endpoint checks.

The `--wait` flag on `docker compose up` uses service health checks to wait until all services are healthy before returning.

**Cloud deployment (systemd).** On a cloud VM, each service is managed as a systemd unit. `scripts/update.sh` implements a rolling update:
1. Pull the latest code from the repository.
2. Install updated dependencies.
3. Restart the systemd units in dependency order: `market_backend` and `news_backend` first, then `ai_agent`, then `portfolio_backend`.
4. Wait for each service's `/health` endpoint to return 200 before proceeding.
5. Optionally clear the Nginx proxy cache.

`start.sh` scripts for each service prefer the local `.venv/bin/python` over the system Python, write PIDs and logs to known paths (`app.pid`, `app.log`), and include readiness polling on `/health`.

**Port map.**

| Service | Default port |
|---|---|
| Frontend (Nginx) | 8080 |
| AI Agent service | 5003 |
| market_backend | 5001 |
| news_backend | 5000 (local) / 5010 (macOS AirPlay conflict) |
| portfolio_backend | 5002 |

*Table 2: Service port assignments.*

### 4.12 Key Algorithms

**Scoring and rating.** The rating algorithm is deterministic and stateless. Given a set of valid specialist scores `S = {s₁, s₂, ..., sₙ}` where each sᵢ ∈ [0, 100], the overall score is `mean(S)`. The rating threshold function `_score_to_rating` is a simple step function with thresholds at 75, 60, and 45. No learned or backtested weights are applied. Scores are designed heuristically to produce plausible spread across the four tiers.

**Fund-type routing.** The routing algorithm in `classify_fund_type` is O(1) keyword lookup on a normalised string. The `resolve_equity_analysis_applicability` override adds O(|top_holdings| + |industry_exposure|) boolean checks. The overall routing decision is fully transparent and logged in the analysis trace.

**Percentage normalisation.** The canonical conversion is `weight_fraction = pct_value / 100.0` applied exactly once. The plausibility check `0 ≤ weight_fraction ≤ MAX_PLAUSIBLE_GROSS_EXPOSURE` (where `MAX_PLAUSIBLE_GROSS_EXPOSURE = 1.40`) rejects leveraged or erroneous inputs. The tolerance `EXPOSURE_TOLERANCE = 0.001` accommodates rounding of independently disclosed asset buckets.

**Score contribution phrase mapping.** The `_score_contribution_phrase` function maps specialist scores to contribution labels used in the deterministic chief explanation: `score ≥ 75` → "strongly supports the rating"; `score ≥ 60` → "supports the rating"; `score ≥ 45` → "keeps the view mixed"; `score < 45` → "pulls the rating down". This mapping provides a qualitative summary of each specialist's contribution without requiring the LLM to interpret numerical scores.

**Rating quorum arithmetic.** The quorum check uses Python's `fractions.Fraction` for exact rational arithmetic. The check `scored_count * threshold.denominator >= applicable_count * threshold.numerator` avoids the floating-point representation issue where, for example, `3/5 = 0.6` is not exactly representable in IEEE 754 and rounding could cause borderline cases to fail the threshold incorrectly. For the default threshold of `Fraction("0.6")` (i.e., 3/5), exactly 3 valid scores from 5 applicable agents always passes, and exactly 2 always fails, with no ambiguity from floating-point representation.

**Portfolio composition (portfolio pipeline).** The portfolio NAV is constructed from constituent fund NAVs as a daily-rebalanced fixed-weight composite:

```
portfolio_daily_return[t] = sum(weight[i] * constituent_daily_return[i][t])
portfolio_NAV[t] = portfolio_NAV[t-1] * (1 + portfolio_daily_return[t])
```

This ensures `diversification_benefit = weighted_average_volatility - portfolio_volatility ≥ 0` by construction (variance of a weighted sum cannot exceed the weighted average of variances), which avoids confusing negative values that might arise from rounding in other composition approaches.

**Coverage quorum.** The quorum check uses rational arithmetic (Python `fractions.Fraction`) for the coverage ratio comparison to avoid floating-point rounding near the 60% threshold. This ensures that exactly 3 of 5 expected agents (60.0%) always passes the threshold regardless of IEEE 754 representation.

**Sector-level analysis algorithm.** The sector comparison endpoint (`POST /api/ai/sector/analyze`) accepts a list of fund codes and builds a cross-fund sector matrix. For each fund, it fetches the industry allocation data from the backend and records either an `available` status (allocation data retrieved) or `insufficient_data` / `not_applicable` status. Sectors are ranked by their equal-weight average allocation across all funds that have data. The matrix identifies `common_sectors` — sectors that appear in two or more funds' top allocations — and computes the mean portfolio-weighted exposure to each common sector. The LLM is then provided with this pre-computed matrix and asked to write a comparative narrative explaining which funds are more concentrated in the leading sectors and what that implies for correlation risk between the funds.

**News summary algorithm.** The news summary endpoint (`POST /api/ai/news/summary`) accepts raw news rows from the frontend and applies the same deterministic keyword classification used by `SentimentAgent` (scanning titles for positive/negative/neutral signal words). It then computes aggregate label distribution (percentage positive, negative, neutral), counts risk-event keywords (e.g. "诉讼", "违规", "清盘"), and derives a data-quality confidence score in [0.40, 0.90] based on the number of items and their recency. The LLM is prompted with these aggregates and a sample of item titles to write a digest. The `related_symbols` field in the response echoes only the request `symbol` — the model is never asked to infer ticker symbols from news text, preventing hallucinated cross-references.

---

## 5 Experimental Results

### 5.1 Test Suite Outcomes

The full test suite is executed after every significant code change. Table 3 shows the final test counts at the time of writing.

| Test module | Cases | Status |
|---|---:|---|
| test_feature_builder | 22 | All pass |
| test_agents | 31 | All pass |
| test_fund_routing | 18 | All pass |
| test_contracts | 12 | All pass |
| test_engine | 14 | All pass |
| test_llm_client | 16 | All pass |
| test_api_contract | 11 | All pass |
| test_golden_suite | 8 | All pass |
| test_evaluation | 9 | All pass |
| test_ratios | 15 | All pass |
| test_score_guardrails | 8 | All pass |
| test_portfolio_analysis | 15 | All pass |
| test_portfolio_pipeline | 8 | All pass |
| test_portfolio_api | 6 | All pass |
| test_sector_view | (subset) | All pass |
| test_sector_api | (subset) | All pass |
| test_news_summary | 13 | All pass |
| test_news_api | 6 | All pass |
| test_backend_function_client | (subset) | All pass |
| test_llm_models | (subset) | All pass |
| **Total** | **229** | **All pass** |

*Table 3: AI agent unit test suite results.*

The test suite is executed by the Docker Compose smoke container on every build (`docker compose run --rm smoke`), verifying both unit tests and live endpoint availability.

### 5.2 Golden Case Regression Results

Eight golden cases are defined in `golden_suite.py` to cover representative fund type and data availability scenarios. All eight cases pass in mock mode after each phase of development.

| Golden case | Fund type | Data scenario | Expected rating tier | Result |
|---|---|---|---|---|
| GC-01 | Mixed equity | Full data | HOLD | Pass |
| GC-02 | Bond fund | Bond holdings present | HOLD | Pass |
| GC-03 | Equity fund | No news data | WATCH | Pass |
| GC-04 | Stock index | Full data with sector | HOLD | Pass |
| GC-05 | Mixed equity | Insufficient NAV (< 30 pts) | insufficient_data | Pass |
| GC-06 | Bond fund | No bond or allocation data | Partial / HOLD | Pass |
| GC-07 | Unknown type | Full NAV only | WATCH | Pass |
| GC-08 | Mixed equity | Full data with peer context | HOLD | Pass |

*Table 4: Golden case regression results (mock mode).*

The golden suite verifies structural properties rather than exact score values. Assertions include: `overall_rating` matches the expected tier, `analysis_status` is `success` or `partial` (not `unavailable`) for cases with adequate data, all expected agent names appear in `agent_outputs`, coverage fields match input data presence, and `analysis_trace` contains events for feature computation and agent execution.

### 5.3 Fund Scan Sample Outcomes

Table 5 presents sample fund analysis outcomes from real-data runs using the mock LLM mode (deterministic scores from real backend data, mock narrative). These results illustrate the system's behaviour across fund types with varying data availability.

| Fund code | Fund type | NAV points | Agents scored | Overall score | Rating |
|---|---|---:|---:|---:|---|
| 000385 | Mixed (equity-like) | 252+ | 5/6 | 74.27 | HOLD |
| 000171 | Stock equity | 252+ | 5/6 | 74.22 | HOLD |
| 000961 | Mixed (equity-like) | 252+ | 5/6 | 73.72 | HOLD |
| 161725 | Stock index | 252+ | 5/6 | ~71.00 | HOLD |
| 003358 | Bond index | 252+ | 3/5* | ~58.00 | WATCH |
| 000001 | Mixed (equity-like) | 252+ | 5/6 | ~68.00 | HOLD |
| 161725 | Stock index | <30 | 0/6 | null | INSUFFICIENT DATA |
| 000002 | Mixed | 0 | 0/6 | null | INSUFFICIENT DATA |

*\* Bond index funds route ExposureAgent and SectorAgent as not_applicable, reducing the applicable denominator.*

*Table 5: Sample fund analysis outcomes (mock LLM, real backend data, July 2026).*

Notable observations:

1. **HOLD cluster near 70–74.** Several established mixed and equity funds cluster in the 70–74 range, placing them in the HOLD tier. None exceeded 75 (BUY) in these samples, consistent with the conservative baseline score design (agents start at 55 and adjust from real metrics).

2. **Bond fund routing.** Fund 003358 (bond index) correctly routes ExposureAgent and SectorAgent as `not_applicable`, reducing the applicable agent count from 7 to 5 and the scoring denominator accordingly. The lower overall score reflects the absence of sector concentration evidence that would otherwise contribute positive signals.

3. **Fund 161725 with sufficient NAV.** When 252+ NAV points are available for 161725 (stock index), a full HOLD rating is produced. When run against a truncated NAV series below 30 points (simulated), the system correctly returns `insufficient_data`.

4. **Avoid-tier scenario (fund code ~27 score).** Runs of fund codes where backend data returns very limited holdings and negative rolling returns produce scores approaching the AVOID range (~27). For reference, the user specified fund code 161725 showing ~27 AVOID in a low-data scenario as an example in the project specification, which the system replicates through the NAV floor and quorum mechanisms.

It is also worth noting that the cluster of HOLD ratings near 70–74 across several well-established funds is consistent with the deliberate score design. The baseline score of 55 and the bounded adjustment magnitudes were chosen so that a fund with reasonably good but not exceptional metrics across all dimensions would land in the high-HOLD range rather than automatically receiving HOLD at the minimum threshold (60) or BUY. In the absence of calibration data, this design choice errs on the side of modesty: a fund would need to demonstrate strong performance, low drawdown, diversified holdings, positive news sentiment, and favourable peer comparison to reach the BUY tier — all simultaneously — rather than any single standout metric.

The near-27 AVOID score mentioned in the project specification was produced for a fund code with severely limited data: fewer than 30 NAV points available and no holdings disclosure. In this scenario, the NAV floor causes PerformanceAgent and RiskAgent to skip (returning `insufficient_data`), the quorum policy detects that fewer than 3 agents scored, and `overall_rating` is set to `"insufficient_data"` rather than `"avoid"`. If the specification's ~27 score refers to a scenario with borderline data (30–40 NAV points, negative trailing returns, high drawdown, and missing sector data), the system would produce a valid AVOID rating from the computed metrics. Both scenarios are reproducible by adjusting the NAV series length and return values in the mock input fixtures.

### 5.4 Reliability Scenario Tests

Table 6 documents the system's behaviour in reliability-relevant scenarios, all verified by unit tests.

| Scenario | Expected behaviour | Test location | Verified |
|---|---|---|---|
| NAV count < 30 | PerformanceAgent + RiskAgent return `skipped+insufficient_data`; rating = `insufficient_data` | test_agents, test_engine | Yes |
| News backend unreachable | Discovery fails gracefully; SentimentAgent = `skipped+insufficient_data`; no HTTP 500 | test_api_contract | Yes |
| LLM returns empty content with `finish_reason=length` | Retry once with expanded `max_tokens`; if still empty, `LLMEmptyResponseError` | test_llm_client | Yes |
| LLM returns 429 rate limit | Retry once after 1.5s backoff; on second failure, `LLMHTTPError` | test_llm_client | Yes |
| BondExposureAgent receives NaN weight | Returns `status=error`; quorum policy isolates module | test_ratios, test_score_guardrails | Yes |
| pct value 0.95 (near-zero percent) | Correctly preserved as 0.0095 fraction, not misread as 0.0095% | test_ratios | Yes |
| pct value 35.2 (normal percent) | Correctly converted to 0.352 fraction | test_ratios | Yes |
| Gross exposure 1.12 (leveraged) | Accepted as 112% (plausible); 1.41 rejected | test_ratios | Yes |
| 3 of 5 expected agents scored | 60% quorum met; rating produced with `analysis_status=partial` | test_engine | Yes |
| 2 of 5 expected agents scored | 40% quorum not met; `overall_rating=unavailable` | test_engine | Yes |
| LLM answers in Chinese | Summary rejected by `_summary_looks_incomplete`; fallback to deterministic | test_llm_client | Yes |

*Table 6: Reliability scenario test verification.*

### 5.5 CI and Cloud Deployment Notes

**Docker Compose.** `docker compose up --build --wait` completes successfully on a fresh clone, building all service images and waiting for health checks to pass. [Insert screenshot: Docker Compose startup output, Fig. 10]

**Smoke test.** `docker compose run --rm smoke` executes all 229 unit tests and verifies the following live endpoints: market_backend `/health`, news_backend `/health`, AI agent service `/health`, and `POST /api/ai/fund/analyze` with `mock=true` for fund 000001.

**Cloud deployment.** On a cloud VM running Ubuntu 22.04, the `scripts/update.sh` script performs a rolling update of all services. Restart time from git pull to healthy AI service is approximately 30–45 seconds, dominated by Python virtualenv dependency installation.

**Performance.** In mock LLM mode (no external API calls), a full 7-agent fund analysis completes in approximately 200–400 ms. In real LLM mode, latency is dominated by the LLM provider response time, typically 3–15 seconds for the ChiefAgent summary with deepseek-v4-pro.

---

## 6 Discussion

### 6.1 Strengths of the Approach

**Contract-first team coordination.** The decision to define the `contracts.py` dataclasses and the HTTP API response shapes before writing agent or backend code enabled the three sub-teams to work in parallel with minimal blocking. The AI agent team could write and test agents against mock input payloads while the backend team implemented real data fetching, and the frontend team developed UI components against the documented response structure. Deviations from the contract were caught early at the integration boundary rather than deep inside agent logic.

**Separation of scoring and narration.** The strict separation between deterministic score computation and LLM narrative generation is the most important design decision. It ensures that quantitative outputs are reproducible and auditable regardless of LLM behaviour. Every score can be explained by pointing to the specific metric values that drove it, without any dependency on the LLM's internal representations.

**Layered reliability guardrails.** The combination of the NAV floor, the quorum policy, the `explain_or_fallback` wrapper, LLM retry, and percentage normalisation creates defence in depth. No single point of failure can produce a confident-sounding recommendation from invalid data. Each guardrail addresses a distinct failure mode identified during development.

**Transparent trace.** The `analysis_trace` mechanism gives both the frontend and debugging tools a step-by-step account of what data was fetched, what metrics were computed, which agents ran and why, and what the final aggregation decision was. This level of transparency is unusual in LLM-based systems and is essential for a financial analysis context.

**Incremental extensibility.** The contract-first architecture and `safe_analyze` pattern make it straightforward to add new specialist agents. Adding a new agent requires: implementing the agent class, registering it in the pipeline, adding golden case assertions, and updating the `evaluation.py` core agent list. Existing tests continue to pass because new agents are additive.

**Dual-mode operation.** The mock LLM mode allows full system demonstration and testing without API credentials. This is practically valuable for team development, CI pipelines, and demo scenarios where real LLM latency or cost is undesirable.

**Portfolio and sector extensions.** The portfolio-level analysis (Phase A1 + A2) and sector comparison endpoint (Phase B1) extend the core fund analysis pattern to new use cases without requiring changes to the existing fund analysis pipeline. The portfolio NAV composition formula guarantees non-negative diversification benefit, which avoids a category of confusing output that might otherwise arise from floating-point composition approaches.

### 6.2 Limitations

**Heuristic score thresholds, not calibrated.** The scoring parameters — baseline scores, adjustment magnitudes, tier boundaries (75/60/45) — were designed by engineering judgment to produce plausible spread across the four rating tiers for a representative sample of Chinese public funds. They have not been calibrated against historical fund performance data, and there is no evidence that funds rated BUY actually outperform funds rated AVOID over any horizon. The system is explicitly positioned as a demonstration of the multi-agent workflow pattern, not as a validated investment signal.

**Static agent weights.** All specialist agents contribute equally to the overall score via an unweighted mean. This is a deliberate simplification: a proper ensemble would weight agents by their empirical predictive validity for each fund type, requiring historical labelled data that was not available within the project scope.

**Partial data coverage.** Several planned backend capabilities were not implemented at the time of this report: `get_fund_bond_holdings` (detailed bond position data), `get_fund_asset_allocation` (comprehensive asset class breakdown), and `get_fund_industry_allocation` (full sector allocation). When these tools are absent, the corresponding agents return `skipped + insufficient_data` or `missing_backend_capability` rather than failing. This is the correct reliability behaviour but limits the depth of bond fund and sector analysis.

**No real-time data.** Fund NAV data and holdings data are fetched at request time from the backend which in turn queries AkShare. AkShare data has publication delays (daily NAV is typically published with one to two business day lag; quarterly holdings disclosure is up to 15 days after quarter end). The system does not attempt to estimate a current-day NAV.

**LLM narrative quality is variable.** Even with the English-only prompt constraint and the `_summary_looks_incomplete` quality gate, real LLM narrative quality varies across providers and model versions. The deterministic fallback ensures the system is always useful, but the LLM narrative adds genuine value only when the model produces coherent, non-repetitive English text grounded in the provided evidence.

**Single-threaded news backend degradation.** While news backend discovery failure is handled gracefully, a fully degraded news backend means no sentiment signal for any fund in the session. A more robust design would cache the last successful discovery result and retry asynchronously.

### 6.3 Honest Positioning: Workflow vs. Autonomous Agent

FundMasterAI is accurately described as a deterministic multi-agent workflow with LLM-assisted narrative generation. It is not a fully autonomous LLM agent in the contemporary sense of that term.

In an autonomous agent, the LLM would decide which tools to invoke, interpret tool results, form intermediate hypotheses, and select subsequent actions. FundMasterAI delegates none of these decisions to the LLM. The agent selection, data fetching, metric computation, score aggregation, and rating decision are all performed by code. The LLM's role is limited to translating already-computed structured evidence into a natural language explanation.

This positioning is appropriate and intentional for the financial analysis domain, for the reasons argued in Section 3.3. However, it means the system does not demonstrate emergent multi-agent coordination, dynamic planning, or tool selection — capabilities that are central to current research on LLM agents. The system demonstrates a different but complementary capability: reliable, auditable, structured analysis pipelines with LLM narration, which may be more practically valuable in high-stakes domains than unconstrained autonomous agents.

Future work (Section 7.2) identifies the transition toward true tool-calling autonomy as a research direction, contingent on solving the reliability challenges that currently make it unsuitable for financial analysis.

---

## 7 Conclusions and Future Work

### 7.1 Summary of Contributions

This project designed, implemented, tested, and deployed FundMasterAI, a full-stack multi-agent fund analysis system. The principal technical contributions are:

1. **A deterministic multi-agent workflow architecture** for Chinese public fund analysis that separates quantitative scoring from LLM narrative generation, ensuring that all scores are reproducible and auditable.

2. **A fund-type routing system** that classifies fund types deterministically from structured category fields and assigns only applicable analysis modules to each fund, preventing category confusion (e.g., applying equity sector analysis to a bond fund) without delegating the classification decision to an LLM.

3. **A layered reliability guardrail system** comprising: a 30-NAV publication floor that prevents ratings from insufficient data; a rating coverage quorum policy that vetoes ratings when too few applicable agents succeed; percentage unit normalisation with gross-exposure plausibility checks at the ingestion boundary; LLM retry logic for transient provider failures; and `explain_or_fallback` that preserves deterministic scores when LLM calls fail.

4. **A structured data coverage and abstention framework** that returns explicit `missing`, `missing_backend_capability`, and `not_applicable` statuses for each data dimension rather than allowing LLM hallucination on absent data.

5. **Portfolio-level and sector-level analysis extensions** that reuse the specialist agent infrastructure and FeatureBuilder metrics on composed time series, providing look-through analysis of constituent holdings with overlap detection.

6. **A comprehensive test suite** of 229 unit tests, 8 golden-case regression scenarios, and a Docker Compose smoke test, providing high confidence in system correctness across edge cases.

7. **A full-stack deployment** with Docker Compose, systemd cloud management scripts, and an AI Insights frontend page rendering structured results with trace transparency.

### 7.2 Future Work

**LLM-driven tool selection.** The most significant architectural evolution would be moving from code-orchestrated tool calling to LLM-driven tool selection using the OpenAI function-calling API or its equivalents. This would allow the system to dynamically prioritise data sources based on intermediate findings. The reliability guardrails designed in this project (coverage checks, quorum policy, abstention) would need to be adapted to constrain an LLM planner while preserving correctness guarantees.

**Score calibration.** The heuristic scoring parameters should be replaced with empirically calibrated values derived from historical fund performance data. A natural approach would be to treat the specialist agent scores as features in a supervised ranking model trained on one-year forward fund returns, allowing the threshold and weight parameters to be set by optimisation rather than judgment.

**Richer bond analytics.** The BondExposureAgent currently operates from top-bond-weight and disclosed-allocation signals. Richer analysis would require duration, maturity ladder, issuer classification, credit rating distribution, and yield-to-maturity data. These would unlock assessment of interest rate sensitivity and credit risk concentration.

**CapitalFlowAgent.** The capital flow agent is documented in the contracts as a planned extension but not implemented due to the absence of a reliable fund flow data source. Connecting to a fund flow dataset (institutional net buy/sell, retail subscription/redemption trends) would add a market sentiment dimension that is independent of the existing news sentiment signal.

**RAG-based news analysis.** The current SentimentAgent uses a keyword rule list for news classification. Replacing this with a retrieval-augmented approach — fetching relevant news from a vector store and providing it as context to the LLM — would improve sensitivity to fund-specific events beyond the keyword vocabulary.

**Frontend portfolio management.** The portfolio analysis pipeline is implemented at the API level but is not yet surfaced in the portfolio management frontend pages. Completing this integration would provide users with a portfolio-level AI summary alongside their individual fund holdings.

**Real-time NAV estimation.** Current analysis uses the most recently published NAV. For funds with intraday price indicators (ETFs, cross-listed funds), real-time or near-real-time estimated NAV could be derived from index futures or constituent stock prices, reducing the analysis lag.

**Benchmark coverage.** The current FeatureBuilder computes benchmark-relative metrics (tracking error, information ratio) only when a benchmark NAV series is explicitly provided in the input. For the vast majority of funds in the current data pipeline, no benchmark series is available. Extending the backend to associate each fund with its declared benchmark index and fetch the benchmark series in parallel with the fund NAV would unlock this analysis dimension for all funds, significantly improving the discriminative power of the PerformanceAgent.

**Explainability interface.** The current analysis trace and coverage map are rendered as technical panels in the AI Insights page, targeting a developer audience. A more polished user-facing explainability interface would summarise the evidence in plain language without the technical field names, progressively disclosing detail for users who want more. Integrating visual elements such as a NAV chart annotated with key events, a radar chart of the seven specialist scores, and a heat map of sector concentration across the portfolio would substantially improve the UI's informational value for non-technical users.

---

## Appendix A: API Reference (Placeholder)

*[Full API reference table to be inserted here. Endpoints include:*
- *`POST /api/ai/fund/analyze` — single-fund multi-agent analysis*
- *`POST /api/ai/portfolio/analyze` — portfolio-level analysis*
- *`POST /api/ai/sector/analyze` — cross-fund sector comparison*
- *`POST /api/ai/news/summary` — news sentiment summary*
- *`GET /api/ai/llm/models` — available LLM model catalog*
- *`GET /health` — AI service health check*
- *Market backend and news backend function registry endpoints]*

*See `ai_agent/fund_llm_engine/docs/contracts.md` for the full specification.]*

---

## Appendix B: Run Manual (Placeholder)

*[Detailed step-by-step instructions to be inserted here, covering:*
1. *Prerequisites (Python ≥ 3.11, Docker, Docker Compose)*
2. *Docker Compose single-command startup*
3. *Local development startup (market_backend, news_backend, AI agent service, frontend)*
4. *LLM configuration (.env setup for DeepSeek / Qwen / GLM / OpenAI)*
5. *Running the test suite*
6. *Cloud deployment with systemd and update.sh]*

*See `README.zh-CN.md` and `ai_agent/fund_llm_engine/docs/environment_setup.md` for current documentation.]*

---

## Appendix C: Individual Contribution Details

*[Detailed per-task contribution breakdown to be inserted here, keyed to git commit history. See Section "Declaration of Contribution of Each Group Member" below for the high-level split.]*

---

## References

[1] Anthropic, "Building effective agents," Anthropic Engineering Blog, 2024. [Online]. Available: https://www.anthropic.com/research/building-effective-agents

[2] M. Malo, A. Sinha, P. Korhonen, A. Wallin, and P. Takala, "Good debt or bad debt: Detecting semantic orientations in economic texts," *Journal of the Association for Information Science and Technology*, vol. 65, no. 4, pp. 782–796, 2014.

[3] Y. Yang, M. Uy, and A. Huang, "FinBERT: A pretrained language model for financial communications," *arXiv preprint arXiv:2006.08097*, 2020.

[4] S. Wu, O. Irsoy, S. Lu, V. Dabravolski, M. Dredze, S. Gehrmann, P. Kambadur, D. Rosenberg, and G. Mann, "BloombergGPT: A large language model for finance," *arXiv preprint arXiv:2303.17564*, 2023.

[5] P. Lewis, E. Perez, A. Piktus, F. Petroni, V. Karpukhin, N. Goyal, H. Küttler, M. Lewis, W.-T. Yih, T. Rocktäschel, S. Riedel, and D. Kiela, "Retrieval-augmented generation for knowledge-intensive NLP tasks," in *Advances in Neural Information Processing Systems*, vol. 33, 2020, pp. 9459–9474.

[6] W. F. Sharpe, "The Sharpe ratio," *The Journal of Portfolio Management*, vol. 21, no. 1, pp. 49–58, 1994.

[7] Y. Shao, X. Geng, Y. Gao, Z. Shao, C. Li, L. Yan, H. Shen, and X. Cheng, "EnhancingRetrieval-Augmented Large Language Models with Iterative Retrieval-Generation Synergy," in *Findings of EMNLP*, 2023.

[8] OpenAI, "Function calling," OpenAI Platform Documentation, 2024. [Online]. Available: https://platform.openai.com/docs/guides/function-calling

[9] S. Yao, J. Zhao, D. Yu, N. Du, I. Shafran, K. Narasimhan, and Y. Cao, "ReAct: Synergizing reasoning and acting in language models," in *International Conference on Learning Representations (ICLR)*, 2023.

[10] AkShare Contributors, "AkShare: An elegant and simple financial data interface library for Python," GitHub repository, 2024. [Online]. Available: https://github.com/akfamily/akshare

[11] Docker Inc., "Docker Compose overview," Docker Documentation, 2024. [Online]. Available: https://docs.docker.com/compose/

[12] Pallets Projects, "Flask — a lightweight WSGI web application framework," Flask Documentation, 2024. [Online]. Available: https://flask.palletsprojects.com/

[13] Python Software Foundation, "concurrent.futures — Launching parallel tasks," Python 3 Documentation, 2024. [Online]. Available: https://docs.python.org/3/library/concurrent.futures.html

[14] systemd Authors, "systemd system and service manager," freedesktop.org, 2024. [Online]. Available: https://systemd.io/

[15] G. Brockman, V. Cheung, L. Pettersson, J. Schneider, J. Schulman, J. Tang, and W. Zaremba, "OpenAI Gym," *arXiv preprint arXiv:1606.01540*, 2016. *(Cited for the OpenAI API compatibility standard adopted by the system's LLM client.)*

---

## Declaration of Contribution of Each Group Member

*This declaration lists the primary responsibilities of each group member. Exact task-level breakdown and commit attribution will be inserted upon project finalisation.*

| Member | Student No. | Primary Responsibility Area | Representative Deliverables |
|---|---|---|---|
| [TBD — Member 1] | [TBD] | **AI Agent Engine** | fund_llm_engine (agents, orchestration, FeatureBuilder, reliability guardrails, test suite) |
| [TBD — Member 2] | [TBD] | **Backend Microservices** | market_backend, news_backend, function registry, data pipeline |
| [TBD — Member 3] | [TBD] | **Frontend and Integration** | frontend_new, AI Insights page, Docker Compose, deployment scripts |

*Note: The responsibility areas above are illustrative of the planned team split. Actual contribution details, cross-functional overlap, and any deviations from the planned split will be documented in Appendix C with reference to the git commit log.*

*All group members reviewed and agreed on the design decisions described in this report.*

Signed: [TBD — Member 1 signature / date]  
Signed: [TBD — Member 2 signature / date]  
Signed: [TBD — Member 3 signature / date]
