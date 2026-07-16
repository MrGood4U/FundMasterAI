# Git History And Milestones

This file explains how to inspect real repository history. It is not the current
implementation ledger; use
[`ai_agent_development_log.md`](./ai_agent_development_log.md) for that.

## Real Git Tags

Always ask Git for the available tags before trying to switch versions:

```bash
git tag --list
```

At the 2026-07-15 documentation review, the repository contained these tags:

```text
aiagent-before-dev-backend-bonds-20260531
aiagent-before-fund-router-20260530
aiagent-demo-real-data-v1
backup-orig-cursor-trailer
dev_before_market_backend_cache
ui-ai-insights-baseline-2026-07-07
```

The live list from `git tag --list` is authoritative because tags may be added
after this document is written.

Inspect a tag without changing the working tree:

```bash
git show --stat aiagent-demo-real-data-v1
```

Temporarily inspect its files:

```bash
git switch --detach aiagent-demo-real-data-v1
```

Return to the branch you were using with `git switch <branch-name>`. Do not
detach or switch branches while uncommitted work is present.

## Former `v0.x` / `v1.x` Names

Older planning documents used names such as `v0.4-windowed-features` and
`v1.4-parallel-agent-execution` as readable capability milestones. Those names
were not created as Git tags in this repository. Commands such as
`git switch --detach v0.4-windowed-features` therefore do not work and must not
appear in current runbooks.

Their useful chronology is retained here as conceptual history only:

1. baseline contracts and mock-first pipeline;
2. rolling/windowed deterministic features;
3. specialist/Chief aggregation and exposure analysis;
4. real OpenAI-compatible provider support;
5. sentiment, sector, and fixed-income routing;
6. automatic evaluation and eight-case golden suite;
7. parallel specialist execution;
8. backend function-registry integration, portfolio/sector inputs, MarketAgent,
   news summary, rating gates, and narrative guardrails.

Use `git log --oneline -- <path>` to locate the actual commit for one of these
capabilities. For example:

```bash
git log --oneline -- ai_agent/fund_llm_engine/src/fund_llm/orchestration/engine.py
```

## Maintenance Rule

- create a tag only for an intentional, tested release point;
- do not document a proposed label as though the tag already exists;
- record current implementation in the development log;
- record future work in the forward plan;
- use Git itself, not copied hashes in prose, as the authority for history.
