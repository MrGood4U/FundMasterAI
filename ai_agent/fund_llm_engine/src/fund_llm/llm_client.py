import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
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


def _first_choice(payload: Dict[str, Any]) -> Dict[str, Any]:
    choices = payload.get("choices") or []
    if not choices or not isinstance(choices[0], dict):
        return {}
    return choices[0]


def _extract_reasoning_content(message: Dict[str, Any]) -> Optional[str]:
    reasoning = message.get("reasoning_content")
    if reasoning is None:
        reasoning = message.get("reasoning")

    if isinstance(reasoning, str):
        text = reasoning.strip()
        return text or None

    if isinstance(reasoning, list):
        parts: List[str] = []
        for item in reasoning:
            if isinstance(item, str) and item.strip():
                parts.append(item.strip())
                continue
            if isinstance(item, dict):
                text = item.get("text") or item.get("content") or item.get("summary")
                if text:
                    parts.append(str(text).strip())
        joined = "\n".join(part for part in parts if part)
        return joined or None

    if isinstance(reasoning, dict):
        text = reasoning.get("text") or reasoning.get("content") or reasoning.get("summary")
        if text:
            return str(text).strip() or None

    return None


def _sanitize_usage(usage: Any) -> Dict[str, int]:
    if not isinstance(usage, dict):
        return {}

    sanitized = {}
    for key, value in usage.items():
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            sanitized[str(key)] = value
    return sanitized


def _response_metadata(payload: Dict[str, Any], attempt: int) -> Dict[str, Any]:
    choice = _first_choice(payload)
    message = choice.get("message") or {}
    if not isinstance(message, dict):
        message = {}

    content = _extract_text_content(payload)
    reasoning_content = _extract_reasoning_content(message)
    finish_reason = str(choice.get("finish_reason") or "").strip().lower()

    metadata: Dict[str, Any] = {
        "attempt": attempt,
        "finish_reason": finish_reason or "unknown",
        "content_length": len(content or ""),
        "reasoning_content_present": bool(reasoning_content),
        "reasoning_content_length": len(reasoning_content or ""),
    }

    usage = _sanitize_usage(payload.get("usage"))
    if usage:
        metadata["usage"] = usage

    for key in ("id", "model", "object"):
        if payload.get(key):
            metadata[f"response_{key}"] = str(payload[key])

    return metadata


def _combined_metadata(
    attempts: List[Dict[str, Any]],
    retry_count: int,
    retry_reason: Optional[str] = None,
) -> Dict[str, Any]:
    final_metadata = dict(attempts[-1] if attempts else {})
    final_metadata["attempt_count"] = len(attempts)
    final_metadata["retry_count"] = retry_count
    final_metadata["attempts"] = attempts
    if retry_reason:
        final_metadata["retry_reason"] = retry_reason
    return final_metadata


def _retry_token_budget(max_tokens: int) -> int:
    expanded = max(max_tokens * 2, max_tokens + 512)
    return min(expanded, max(max_tokens, 4096))


def _format_empty_response_error(metadata: Dict[str, Any]) -> str:
    return (
        "LLM returned empty content "
        f"(finish_reason={metadata.get('finish_reason', 'unknown')}, "
        f"retry_count={metadata.get('retry_count', 0)}, "
        f"content_length={metadata.get('content_length', 0)}, "
        "reasoning_content_present="
        f"{str(metadata.get('reasoning_content_present', False)).lower()})."
    )


@dataclass
class LLMChatResult:
    content: str
    metadata: Dict[str, Any]


class LLMClientError(RuntimeError):
    """Base exception for sanitized LLM client failures."""


class LLMEmptyResponseError(LLMClientError):
    """Raised when the provider returns no user-visible content."""


class LLMHTTPError(LLMClientError):
    """Raised when the provider returns an HTTP error."""


class LLMTransportError(LLMClientError):
    """Raised when the provider request cannot be completed."""


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
        self.last_response_metadata: Dict[str, Any] = {}

    def _chat_endpoint(self) -> str:
        return _join_url(self.base_url, "chat/completions")

    def _build_payload(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        thinking_mode: str,
        reasoning_effort: str,
    ) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if thinking_mode:
            payload["thinking"] = {"type": thinking_mode}
        if reasoning_effort:
            payload["reasoning_effort"] = reasoning_effort
        return payload

    def _post_json(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        http_request = request.Request(
            self._chat_endpoint(),
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "FundMasterAI/1.0",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                response_text = response.read().decode("utf-8")
        except error.HTTPError as exc:
            try:
                response_body_length = len(exc.read() or b"")
            except Exception:
                response_body_length = 0
            raise LLMHTTPError(
                f"LLM HTTP {exc.code} returned from {self._chat_endpoint()}. "
                f"Provider response body omitted ({response_body_length} bytes)."
            ) from exc
        except error.URLError as exc:
            raise LLMTransportError(
                f"LLM request failed for {self._chat_endpoint()} "
                f"({exc.reason.__class__.__name__})."
            ) from exc

        try:
            response_payload = json.loads(response_text)
        except json.JSONDecodeError as exc:
            raise LLMClientError(
                f"LLM returned invalid JSON from {self._chat_endpoint()}."
            ) from exc
        if not isinstance(response_payload, dict):
            raise LLMClientError(
                f"LLM returned non-object JSON from {self._chat_endpoint()}."
            )
        return response_payload

    def _send_chat_attempt(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        thinking_mode: str,
        reasoning_effort: str,
        attempt: int,
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        payload = self._build_payload(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            thinking_mode=thinking_mode,
            reasoning_effort=reasoning_effort,
        )
        response_payload = self._post_json(payload)
        return _extract_text_content(response_payload), _response_metadata(response_payload, attempt)

    def chat_with_metadata(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1200,
    ) -> LLMChatResult:
        content, first_metadata = self._send_chat_attempt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            thinking_mode=self.thinking_mode,
            reasoning_effort=self.reasoning_effort,
            attempt=1,
        )
        attempts = [first_metadata]
        if content:
            metadata = _combined_metadata(attempts, retry_count=0)
            self.last_response_metadata = metadata
            return LLMChatResult(content=content, metadata=metadata)

        retry_count = 0
        retry_reason = None
        if first_metadata.get("finish_reason") == "length":
            retry_count = 1
            retry_reason = "empty_content_finish_reason_length"
            content, retry_metadata = self._send_chat_attempt(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_tokens=_retry_token_budget(max_tokens),
                thinking_mode="disabled" if self.thinking_mode else "",
                reasoning_effort="",
                attempt=2,
            )
            attempts.append(retry_metadata)
            if content:
                metadata = _combined_metadata(attempts, retry_count, retry_reason)
                self.last_response_metadata = metadata
                return LLMChatResult(content=content, metadata=metadata)

        metadata = _combined_metadata(attempts, retry_count, retry_reason)
        self.last_response_metadata = metadata
        raise LLMEmptyResponseError(_format_empty_response_error(metadata))

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.3, max_tokens: int = 1200) -> str:
        return self.chat_with_metadata(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        ).content


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
