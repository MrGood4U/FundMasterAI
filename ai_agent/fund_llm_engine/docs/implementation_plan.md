# AI Agent Forward Plan

This document contains future work only. It is not evidence that a feature is
implemented. For current behavior, use
[`ai_agent_development_log.md`](./ai_agent_development_log.md), then verify the
code and tests.

Last reconciled with the integrated codebase: 2026-07-16.

## Completed Baseline

The following capabilities are already implemented and should not remain in a
future-work checklist:

- fund analysis through `POST /api/ai/fund/analyze`;
- portfolio analysis and holdings/industry/asset look-through through
  `POST /api/ai/portfolio/analyze`;
- cross-fund sector comparison through `POST /api/ai/sector/analyze`;
- batch news summary through `POST /api/ai/news/summary`;
- deterministic fund-type routing and data-coverage checks;
- `PerformanceAgent`, `ExposureAgent`, `BondExposureAgent`, `RiskAgent`,
  `SentimentAgent`, `SectorAgent`, and `MarketAgent`;
- parallel specialist execution followed by serial Chief aggregation;
- structured holdings, peer-analysis, and profit-probability fields;
- provider retry/fallback behavior, sanitized server errors, rating eligibility
  gates, and `analysis_trace`;
- automated unit tests, output evaluation, and an eight-case mock golden suite.

Completed implementation history belongs in
[`ai_agent_development_log.md`](./ai_agent_development_log.md), not in this plan.

## Priority 0: Submission Stability

Goal: keep the checked-in demo reproducible for a new reviewer.

- Keep the root Docker runbook, Agent contracts, and current-status ledger in
  sync with code changes.
- Keep the clean-clone default in mock LLM mode; never commit API keys.
- Run unit tests, the mock golden suite, Docker smoke, and a real browser check
  before a submission release.
- Treat upstream-data timeouts as explicit degraded states rather than filling
  fields with plausible-looking placeholders.

Completion criteria:

- the commands in the root README work from a clean checkout;
- smoke ends with `FundMasterAI Docker smoke test passed.`;
- unit tests end in `OK` and the golden suite reports `overall_status: pass`;
- current and historical documents are clearly distinguished.

## Priority 1: Evaluation And Evidence

Goal: improve how claims can be defended without presenting heuristic ratings
as statistically calibrated predictions.

- Add prompt/run version metadata to archived real-model evaluation records.
- Preserve a small, privacy-safe set of representative real-model outputs for
  manual comparison after prompt changes.
- Expand golden cases only when a new failure mode or data contract needs to be
  protected; do not increase case count for appearance alone.
- Document the distinction between deterministic scores, LLM narratives, and
  any future predictive calibration experiment.

Completion criteria:

- each material prompt change has before/after evidence;
- automatic gates still catch technical errors, ineligible ratings, missing
  coverage, and unsupported narrative claims;
- report wording does not claim predictive accuracy that has not been tested.

## Priority 2: Data-Dependent Analysis Depth

These items should start only after the upstream contract is stable.

### Fixed-income depth

- The integrated Market backend now retrieves disclosed stock and bond
  positions from Eastmoney with the required request context. That restores
  holdings availability but does not add the fields below.
- Duration, maturity buckets, issuer type, and credit rating need reliable
  backend fields before they can affect `BondExposureAgent`.
- Missing fields must stay visible as missing; they must not be inferred from a
  fund name.

### CapitalFlowAgent

- The frontend Market Flow page has ETF/order-flow views, but the AI Agent does
  not yet have a validated fund-level capital-flow input contract.
- Before registering `CapitalFlowAgent`, define source, universe, time window,
  units, freshness, cache behavior, and fund-to-flow mapping.
- Until then, do not ship a permanently skipped Agent or an LLM-only macro
  paragraph under that name.

### Sentiment and sector evidence

- Improve structured news/topic fields and industry-classification quality when
  the backend can provide them consistently.
- Keep `success`, `insufficient_data`, `not_applicable`, and `error` semantics
  stable for frontend consumers.

## Optional Engineering Follow-ups

- Extend the shared data-driven confidence helper to specialist Agents that
  still use their own explicit formulas, while preserving regression baselines.
- Add more focused adapter tests when backend schemas change.
- Profile optional backend calls before introducing more concurrency; preserve
  deterministic trace order and year-fallback behavior.

## Non-goals Without A New Requirement

- autonomous trading or order execution;
- an LLM that invents missing market/fund data;
- a single payload that mixes unrelated fund, portfolio, and sector contracts;
- PDF export, account security, or frontend layout work inside the AI module;
- claiming that heuristic scores are calibrated probabilities.

## Maintenance Rule

When work is completed, move the verified result and commands to
`ai_agent_development_log.md`, update contracts/evaluation docs if semantics
changed, and remove the item from this file. Do not leave the same feature both
“completed” and “planned.”
