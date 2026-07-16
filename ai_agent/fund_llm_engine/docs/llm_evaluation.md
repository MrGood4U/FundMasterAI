# LLM Output Evaluation

Last reconciled with `src/fund_llm/evaluation.py`: 2026-07-15.

## Purpose

The evaluator does not prove investment accuracy. It checks whether one run is
structurally complete, internally consistent, evidence-aware, and honest about
missing data or technical failures.

Automatic evaluation is followed by manual review for unsupported or overly
strong narrative claims.

## Current Automatic Checks

The scored checks total 100 points:

| Check | Points | Main question |
|---|---:|---|
| `structure_completeness` | 20 | Are required result and Agent fields present? |
| `score_consistency` | 15 | Do score/rating/stance and metadata agree? |
| `core_agent_coverage` | 15 | Are all registered specialist outputs represented with valid statuses? |
| `evidence_coverage` | 20 | Do outputs reflect the metrics actually available? |
| `missing_data_handling` | 10 | Are missing benchmark/news/sector inputs handled explicitly? |
| `risk_profile_alignment` | 10 | Does the result reflect the supplied client risk profile? |
| `narrative_sanity` | 10 | Are narratives non-empty and free of known false-success patterns? |

Two non-scoring gates can still cap or fail a high numerical score:

- `agent_execution_health`: detects invalid statuses and technical-error-heavy
  output;
- `decision_eligibility`: prevents a published investment rating when NAV,
  core-Agent, or applicable-Agent coverage requirements are not satisfied.

The current specialist set checked by the evaluator is:

```text
PerformanceAgent
ExposureAgent
BondExposureAgent
RiskAgent
SentimentAgent
SectorAgent
MarketAgent
```

Some specialists may legitimately return `not_applicable` or
`insufficient_data` depending on fund type and available evidence. The evaluator
checks those semantics rather than requiring every Agent to publish a score.

## Result Classes

- `pass`: score at least 85 and no disqualifying high-priority gate;
- `review`: score from 60 to 84, or output that needs manual confirmation;
- `fail`: score below 60 or a critical structural/execution/eligibility failure.

## Commands

Evaluate the default mock input:

```bash
python scripts/evaluate_analysis_output.py \
  --input examples/mock_input.json \
  --mode mock
```

Run all checked-in cases:

```bash
python scripts/run_golden_suite.py --mode mock
```

Save the suite report:

```bash
python scripts/run_golden_suite.py \
  --mode mock \
  --output outputs/golden_suite_report.json
```

The current manifest contains eight cases. Do not hard-code that count in
startup instructions; verify `total_cases`, `passed_cases`, `failed_cases`, and
`overall_status` in the generated report.

## Manual Review

After automatic checks pass, inspect at least these questions:

1. Does any narrative cite a time window, benchmark, holding, industry, news
   event, or ranking that is absent from the input/evidence?
2. Are percentage units and comparison denominators stated correctly?
3. Does a `not_applicable` Agent look like an intentional route decision rather
   than a hidden failure?
4. Is the final recommendation stronger than the eligible specialist evidence?
5. Does the output clearly remain analytical guidance rather than a guaranteed
   return or automatic trading instruction?

## Scope Limit

Passing the evaluator means the output followed the repository's contracts and
guardrails for those cases. It does not establish out-of-sample predictive
accuracy, portfolio alpha, or suitability for real-money trading.
