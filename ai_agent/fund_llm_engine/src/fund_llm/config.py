import os

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional convenience dependency
    load_dotenv = None

if load_dotenv:
    load_dotenv(override=False)

LLM_API_KEY = os.getenv("LLM_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL") or os.getenv(
    "OPENAI_BASE_URL",
    "https://generativelanguage.googleapis.com/v1beta/openai/",
)
LLM_MODEL = os.getenv("LLM_MODEL") or os.getenv("DEFAULT_MODEL_NAME", "gemini-3-flash-preview")
LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
LLM_THINKING_MODE = os.getenv("LLM_THINKING_MODE", "").strip().lower()
LLM_REASONING_EFFORT = os.getenv("LLM_REASONING_EFFORT", "").strip().lower()

# Backward-compatible aliases for older code paths.
OPENAI_API_KEY = LLM_API_KEY
OPENAI_BASE_URL = LLM_BASE_URL
DEFAULT_MODEL_NAME = LLM_MODEL
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
