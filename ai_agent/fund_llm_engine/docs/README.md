# AI Agent Docs Index

Use this index to choose the right document. The code and tests remain the final
authority; for a prose snapshot of current implementation status, start with
[`ai_agent_development_log.md`](./ai_agent_development_log.md).

## Current Status

- [`ai_agent_development_log.md`](./ai_agent_development_log.md): current task-level status ledger for implemented, partial, todo, and backend-dependent AI Agent work.
- [`implementation_plan.md`](./implementation_plan.md): forward-looking plan only. Do not use it as proof that a feature is implemented.
- [`version_history.md`](./version_history.md): real Git tags and a warning about former conceptual milestone names that were never tags.

## Architecture And Contracts

- [`architecture.md`](./architecture.md): module boundary and layer overview.
- [`contracts.en.md`](./contracts.en.md): English input and output contract notes.
- [`explainability_trace.md`](./explainability_trace.md): trace semantics for explaining how results were produced.

## Setup And Provider Configuration

- [`../README.en.md`](../README.en.md): Agent-focused development and native
  debugging.
- [`../../../DOCKER.en.md`](../../../DOCKER.en.md): complete-project Docker
  startup, configuration, and troubleshooting.
- [`dev_backend_integration_handoff.md`](./dev_backend_integration_handoff.md): historical 2026-05-30 dev-backend integration snapshot. Keep for traceability, but verify current behavior from the development log, code, and tests.

## Evaluation And Golden Cases

- [`llm_evaluation.md`](./llm_evaluation.md): automatic and manual output evaluation rubric.

Chinese team references remain available in [`README.zh-CN.md`](./README.zh-CN.md),
including environment/provider setup, historical design and migration notes,
golden cases, manual acceptance, score guardrails, the former-provider benchmark,
and real-sample notes.

## Real Sample Notes

- [`real_sample_003358_notes.md`](./real_sample_003358_notes.md): fixed-income sample notes.
- [`real_sample_005827_notes.md`](./real_sample_005827_notes.md): mixed / blue-chip sample notes.
- [`real_sample_008163_notes.md`](./real_sample_008163_notes.md): real sample notes.
- [`real_sample_161725_notes.md`](./real_sample_161725_notes.md): sector-concentrated index sample notes.

## Maintenance Rules

- Current status belongs in `ai_agent_development_log.md`.
- Future work belongs in `implementation_plan.md`.
- Historical snapshots should be clearly marked historical.
- A milestone name must not be documented as a usable Git tag unless `git tag --list` actually contains it.
- Runtime secrets, including LLM API keys, must stay out of repository files.
