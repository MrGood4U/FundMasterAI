import os

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional convenience dependency
    load_dotenv = None

if load_dotenv:
    load_dotenv(override=False)

LLM_API_KEY = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL") or os.getenv(
    "OPENAI_BASE_URL",
    "https://opencode.ai/zen/go/v1",
)
LLM_MODEL = os.getenv("LLM_MODEL") or os.getenv("DEFAULT_MODEL_NAME", "deepseek-v4-flash")
LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
LLM_THINKING_MODE = os.getenv("LLM_THINKING_MODE", "").strip().lower()
LLM_REASONING_EFFORT = os.getenv("LLM_REASONING_EFFORT", "").strip().lower()

# Backward-compatible aliases for older code paths.
OPENAI_API_KEY = LLM_API_KEY
OPENAI_BASE_URL = LLM_BASE_URL
DEFAULT_MODEL_NAME = LLM_MODEL
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# A final investment rating needs enough observations to avoid degenerate
# one/two-point return and volatility calculations.  Thirty NAV observations
# are still labelled low-reliability elsewhere, but form the minimum floor for
# publishing BUY/HOLD/WATCH/AVOID rather than an abstention.
MIN_NAV_POINTS_FOR_RATING = 30

# Failure-isolation quorum for publishing a partial rating.  Performance and
# Risk remain mandatory; beyond those core checks, at least three specialist
# scores and 60% of currently applicable outputs must be available.
MIN_RATING_AGENT_COUNT = 3
MIN_RATING_COVERAGE_RATIO = 0.60

# Prompt 版本标记（Phase 2 evidence）：任何 agent prompt 措辞变更时同步递增，
# 让 golden case 结果、真实模型样例和人工评估记录能对上是哪一版 prompt 产生的。
PROMPT_VERSION = "2026-07-15.4"
