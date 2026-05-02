import json
from typing import Any, Dict, List, Optional
from urllib import error, request

from fund_llm import config


def _join_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def _extract_text_content(payload: Dict[str, Any]) -> Optional[str]:
    choices = payload.get("choices") or []
    if not choices:
        return None

    message = choices[0].get("message") or {}
    content = message.get("content")

    if isinstance(content, str):
        text = content.strip()
        return text or None

    if isinstance(content, list):
        parts: List[str] = []
        for item in content:
            if isinstance(item, str):
                if item.strip():
                    parts.append(item.strip())
                continue
            if not isinstance(item, dict):
                continue
            text = item.get("text") or item.get("content")
            if text:
                parts.append(str(text).strip())
        joined = "\n".join(part for part in parts if part)
        return joined or None

    return None


class LLMClient:
    """Minimal OpenAI-compatible client with raw JSON parsing."""

    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        model: str = None,
        timeout_seconds: int = None,
        thinking_mode: str = None,
        reasoning_effort: str = None,
    ):
        self.api_key = api_key or config.LLM_API_KEY
        self.base_url = base_url or config.LLM_BASE_URL
        self.model = model or config.LLM_MODEL
        self.timeout_seconds = timeout_seconds or config.LLM_TIMEOUT_SECONDS
        self.thinking_mode = (
            config.LLM_THINKING_MODE if thinking_mode is None else str(thinking_mode)
        ).strip().lower()
        self.reasoning_effort = (
            config.LLM_REASONING_EFFORT if reasoning_effort is None else str(reasoning_effort)
        ).strip().lower()

        if not self.api_key:
            raise ValueError("LLM API key is missing. Set LLM_API_KEY, GEMINI_API_KEY, or OPENAI_API_KEY.")
        if not self.base_url:
            raise ValueError("LLM base URL is missing. Set LLM_BASE_URL or OPENAI_BASE_URL.")
        if not self.model:
            raise ValueError("LLM model name is missing. Set LLM_MODEL or DEFAULT_MODEL_NAME.")
        if self.thinking_mode and self.thinking_mode not in {"enabled", "disabled"}:
            raise ValueError("LLM_THINKING_MODE must be either 'enabled', 'disabled', or empty.")

    def _chat_endpoint(self) -> str:
        return _join_url(self.base_url, "chat/completions")

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.3, max_tokens: int = 1200) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if self.thinking_mode:
            payload["thinking"] = {"type": self.thinking_mode}
        if self.reasoning_effort:
            payload["reasoning_effort"] = self.reasoning_effort

        http_request = request.Request(
            self._chat_endpoint(),
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            response_body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"LLM HTTP {exc.code} returned from {self._chat_endpoint()}: {response_body[:400]}"
            ) from exc
        except error.URLError as exc:
            raise RuntimeError(f"LLM request failed for {self._chat_endpoint()}: {exc}") from exc

        content = _extract_text_content(response_payload)
        return content or "API returned empty response"


class MockLLMClient:
    """Deterministic mock client for tests."""

    def __init__(self, fixed_response: str = None):
        self.fixed_response = fixed_response or "Mock analysis narrative."
        self.call_log: List[Dict[str, str]] = []

    def chat(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        self.call_log.append(
            {
                "system_prompt": system_prompt[:120],
                "user_prompt": user_prompt[:120],
            }
        )
        return self.fixed_response
