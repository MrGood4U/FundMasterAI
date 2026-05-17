# AI Agent Module

This directory contains the LLM-based analysis module for FundMaster AI.

## Current Module

- `fund_llm_engine/`: multi-agent fund analysis engine.

The engine is intentionally kept as a standalone Python package under this
directory. The repository root integrates it with teammate backend and frontend
modules only for demo verification.

## Quick Verification

```bash
cd ai_agent/fund_llm_engine
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[backend]"
python3 -m unittest discover -s tests
python3 scripts/run_mock_demo.py examples/mock_input.json
```

Repository-level integration smoke test:

```bash
cd ../..
ai_agent/fund_llm_engine/.venv/bin/python scripts/run_integrated_smoke.py
```

See `fund_llm_engine/README.md` and
`fund_llm_engine/docs/agent_architecture_design.md` for module scope,
contracts, provider setup, and integration notes.
