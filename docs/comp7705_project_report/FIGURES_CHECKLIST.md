# Figures checklist (what to insert before PDF submission)

Guidelines require numbered, captioned diagrams/tables. Architecture diagrams are already generated as SVG in this folder. **UI screenshots must be captured from a running system** (local or cloud).

## Already provided (vector diagrams)
- `fig2_system_architecture.svg`
- `fig3_agent_workflow.svg`

Open each SVG in a browser → Export/Print to PDF or PNG → insert into Word/Google Docs.

## Screenshots you (or I via automation script) still need

| Figure | Capture | Pass criteria |
|------|---------|----------------|
| Fig.4 | AI Insights page empty state | page loads at `:8080/ai-insights.html` |
| Fig.5 | Analysis of `000385` or `000171` (strong HOLD) | rating + agent cards visible |
| Fig.6 | Analysis of `161725` (weak / AVOID) | contrasting rating |
| Fig.7 | Developer / agent detail drawer | scores + skip reasons visible |
| Fig.8 | Market / fund rankings page | live list loads |
| Fig.9 | News page (if demoing) | page loads; note static 88% if still present |
| Fig.10 | Service health / Docker compose ps OR systemd status | evidence stack is up |

## Suggested caption style
`Figure 5. AI Insights result for fund 000171 (易方达裕丰回报债券A), mock LLM mode.`

## Note on screenshots vs “I cannot click your mouse”
Screenshots are produced by automation (Chrome/Playwright script) or by you manually. Both are valid evidence. The report text below already references these figure numbers.
