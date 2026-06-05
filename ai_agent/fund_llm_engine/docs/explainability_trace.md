# Explainability Trace

The AI demo now returns a structured `analysis_trace` with the final analysis.
This trace shows that the result is built from backend data, deterministic
metrics, specialist agent checks, and chief aggregation rather than one direct
prompt-only LLM call.

## Trace Sources

- `app.py` adds backend-source events: function registry discovery, NAV history
  loading, fund profile routing, and data coverage checks.
- `src/fund_llm/orchestration/engine.py` adds engine events: feature
  calculation, each specialist agent result, and final aggregation.
- `frontend_new/ai-insights.html` and `frontend_new/js/ai-insights.js` render
  these events as `Analysis Evidence` cards with expandable technical details.

## Demo Meaning

User-facing cards should stay short and readable:

- Loaded real fund history
- Calculated fund metrics
- Evaluated performance
- Measured risk profile
- Combined specialist views

Technical details remain available for instructors and developers through the
expandable `Technical evidence` section.
