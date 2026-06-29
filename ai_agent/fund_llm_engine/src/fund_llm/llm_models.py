"""LLM model catalog helpers for OpenAI-compatible gateways."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set
from urllib import error, request

from fund_llm import config


@dataclass(frozen=True)
class LLMModelOption:
    id: str
    label: str

    def to_dict(self) -> Dict[str, str]:
        return {"id": self.id, "label": self.label}


# Models known to work with LLMClient chat/completions (not /v1/messages).
DEFAULT_CHAT_COMPLETION_MODELS: List[LLMModelOption] = [
    LLMModelOption("deepseek-v4-flash", "DeepSeek V4 Flash"),
    LLMModelOption("deepseek-v4-pro", "DeepSeek V4 Pro"),
    LLMModelOption("glm-5.2", "GLM 5.2"),
    LLMModelOption("glm-5.1", "GLM 5.1"),
    LLMModelOption("kimi-k2.7", "Kimi K2.7"),
    LLMModelOption("kimi-k2.6", "Kimi K2.6"),
    LLMModelOption("mimo-v2.5", "MiMo V2.5"),
    LLMModelOption("mimo-v2.5-pro", "MiMo V2.5 Pro"),
    LLMModelOption("gemini-3-flash-preview", "Gemini 3 Flash Preview"),
]

_CHAT_COMPLETION_ALLOWLIST: Set[str] = {item.id for item in DEFAULT_CHAT_COMPLETION_MODELS}

_LABEL_BY_ID: Dict[str, str] = {item.id: item.label for item in DEFAULT_CHAT_COMPLETION_MODELS}

_CACHE_TTL_SECONDS = 3600
_cache_payload: Optional[Dict[str, Any]] = None
_cache_expires_at: float = 0.0


def _join_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def _humanize_model_id(model_id: str) -> str:
    if model_id in _LABEL_BY_ID:
        return _LABEL_BY_ID[model_id]
    return model_id.replace("-", " ").replace("_", " ").title()


def _parse_allowed_models_env() -> Optional[Set[str]]:
    raw = os.getenv("LLM_ALLOWED_MODELS", "").strip()
    if not raw:
        return None
    return {item.strip() for item in raw.split(",") if item.strip()}


def _apply_allowed_filter(models: List[LLMModelOption], allowed: Optional[Set[str]]) -> List[LLMModelOption]:
    if not allowed:
        return models
    return [item for item in models if item.id in allowed]


def _ensure_default_present(models: List[LLMModelOption], default_model: str) -> List[LLMModelOption]:
    if not default_model:
        return models
    if any(item.id == default_model for item in models):
        return models
    return [LLMModelOption(default_model, _humanize_model_id(default_model)), *models]


def infer_provider_label(base_url: str) -> str:
    normalized = base_url.lower()
    if "opencode.ai/zen/go" in normalized:
        return "opencode-go"
    if "opencode.ai/zen" in normalized:
        return "opencode-zen"
    if "generativelanguage.googleapis.com" in normalized:
        return "gemini"
    if "deepseek.com" in normalized:
        return "deepseek"
    if "openai.com" in normalized:
        return "openai"
    return "openai-compatible"


def parse_gateway_models_payload(payload: Dict[str, Any]) -> List[str]:
    data = payload.get("data")
    if not isinstance(data, list):
        return []

    model_ids: List[str] = []
    for item in data:
        if isinstance(item, dict):
            model_id = str(item.get("id") or "").strip()
            if model_id:
                model_ids.append(model_id)
    return model_ids


def filter_chat_completion_models(model_ids: List[str]) -> List[LLMModelOption]:
    filtered: List[LLMModelOption] = []
    seen: Set[str] = set()
    for model_id in model_ids:
        if model_id not in _CHAT_COMPLETION_ALLOWLIST or model_id in seen:
            continue
        seen.add(model_id)
        filtered.append(LLMModelOption(model_id, _humanize_model_id(model_id)))
    return filtered


def fetch_gateway_models(
    base_url: str,
    api_key: str,
    timeout_seconds: int = 10,
) -> List[str]:
    endpoint = _join_url(base_url, "models")
    http_request = request.Request(
        endpoint,
        headers={
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "FundMasterAI/1.0",
        },
        method="GET",
    )
    try:
        with request.urlopen(http_request, timeout=timeout_seconds) as response:
            response_text = response.read().decode("utf-8")
    except error.HTTPError as exc:
        raise RuntimeError(f"LLM models HTTP {exc.code} from {endpoint}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"LLM models request failed for {endpoint}") from exc

    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"LLM models returned invalid JSON from {endpoint}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"LLM models returned non-object JSON from {endpoint}")
    return parse_gateway_models_payload(payload)


def resolve_available_models(
    *,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    default_model: Optional[str] = None,
    timeout_seconds: int = 10,
    use_cache: bool = True,
) -> Dict[str, Any]:
    global _cache_payload, _cache_expires_at

    resolved_api_key = api_key or config.LLM_API_KEY
    resolved_base_url = base_url or config.LLM_BASE_URL
    resolved_default_model = default_model or config.LLM_MODEL
    allowed = _parse_allowed_models_env()
    cache_key = (
        resolved_base_url,
        resolved_default_model,
        tuple(sorted(allowed or ())),
        bool(resolved_api_key),
    )

    if use_cache and _cache_payload and time.time() < _cache_expires_at:
        if _cache_payload.get("cache_key") == cache_key:
            return dict(_cache_payload["data"])

    static_models = _apply_allowed_filter(list(DEFAULT_CHAT_COMPLETION_MODELS), allowed)
    static_models = _ensure_default_present(static_models, resolved_default_model)

    result: Dict[str, Any] = {
        "default_model": resolved_default_model,
        "provider": infer_provider_label(resolved_base_url),
        "base_url": resolved_base_url,
        "models": [item.to_dict() for item in static_models],
        "source": "static",
    }

    if resolved_api_key:
        try:
            live_ids = fetch_gateway_models(resolved_base_url, resolved_api_key, timeout_seconds=timeout_seconds)
            live_models = filter_chat_completion_models(live_ids)
            live_models = _apply_allowed_filter(live_models, allowed)
            live_models = _ensure_default_present(live_models, resolved_default_model)
            if live_models:
                result["models"] = [item.to_dict() for item in live_models]
                result["source"] = "live"
        except RuntimeError:
            pass

    if use_cache:
        _cache_payload = {"cache_key": cache_key, "data": result}
        _cache_expires_at = time.time() + _CACHE_TTL_SECONDS

    return result


def clear_model_catalog_cache() -> None:
    global _cache_payload, _cache_expires_at
    _cache_payload = None
    _cache_expires_at = 0.0
