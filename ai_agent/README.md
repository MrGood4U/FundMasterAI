# AI Agent Module

This directory contains the LLM-based analysis module for FundMaster AI.

Current module:

- `fund_llm_engine/`: multi-agent fund analysis engine

Quick local verification:

```bash
cd ai_agent/fund_llm_engine
python3.11 -m unittest discover -s tests
python3.11 scripts/run_mock_demo.py examples/mock_input.json
```

See `fund_llm_engine/README.md` and `fund_llm_engine/docs/agent_architecture_design.md`
for the module scope, contracts, provider setup, and integration notes.
