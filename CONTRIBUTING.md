# Contributing to FundMasterAI

`dev` is the shared development line; `master` is the curated submission-ready
release line. Develop changes on a short-lived branch, merge them into `dev`
through a pull request, and promote only a verified release to `master`.

## Workflow

```bash
git switch dev
git pull --ff-only
git switch -c your-name/short-topic
```

After making a focused change:

```bash
git add <files>
git commit -m "Describe the change"
git push -u origin your-name/short-topic
```

Open a pull request into `dev`. Keep secrets, local `.env` files, generated
logs, PID files, and personal IDE state out of Git.

When `dev` is ready for submission, create a focused release PR from the tested
release state into `master`. Do not use `master` as the everyday integration
branch or copy local QA artifacts into it.

## Required verification

For complete-stack or documentation changes:

```bash
docker compose config --quiet
docker compose up --build --wait
docker compose run --rm smoke
```

Then open `http://localhost:8080/ai-insights.html` in a real browser and verify
the affected path after data loading completes.

Agent-only changes should also run:

```bash
cd ai_agent/fund_llm_engine
python -m unittest discover -s tests
python scripts/run_golden_suite.py --mode mock
```

## Pull-request scope

- explain the user-visible or contract-level change;
- include the commands that were actually run;
- keep backend, frontend, and Agent ownership boundaries explicit;
- update the matching English and Chinese entry points when navigation or
  startup behavior changes;
- never treat smoke success alone as visual acceptance.

There is no shared systemd server workflow on `master`. Local and classroom
execution use Docker Compose; any separate deployment environment must maintain
its own runbook outside this repository until it becomes a supported target.
