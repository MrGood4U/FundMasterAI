import json
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fund_llm.llm_models import (  # noqa: E402
    clear_model_catalog_cache,
    filter_chat_completion_models,
    infer_provider_label,
    parse_gateway_models_payload,
    resolve_available_models,
)


class LLMModelsTest(unittest.TestCase):
    def setUp(self):
        clear_model_catalog_cache()

    def tearDown(self):
        clear_model_catalog_cache()

    def test_parse_gateway_models_payload(self):
        payload = {
            "object": "list",
            "data": [
                {"id": "deepseek-v4-flash", "object": "model"},
                {"id": "minimax-m3", "object": "model"},
            ],
        }
        self.assertEqual(
            parse_gateway_models_payload(payload),
            ["deepseek-v4-flash", "minimax-m3"],
        )

    def test_filter_chat_completion_models_excludes_messages_only_models(self):
        models = filter_chat_completion_models(
            ["deepseek-v4-pro", "minimax-m3", "qwen3.7-max", "glm-5.1"]
        )
        self.assertEqual([item.id for item in models], ["deepseek-v4-pro", "glm-5.1"])

    def test_infer_provider_label(self):
        self.assertEqual(
            infer_provider_label("https://opencode.ai/zen/go/v1"),
            "opencode-go",
        )
        self.assertEqual(
            infer_provider_label("https://generativelanguage.googleapis.com/v1beta/openai/"),
            "gemini",
        )

    def test_resolve_available_models_falls_back_to_static_when_live_fetch_fails(self):
        with patch.dict(
            os.environ,
            {
                "LLM_BASE_URL": "https://opencode.ai/zen/go/v1",
                "LLM_MODEL": "deepseek-v4-flash",
            },
            clear=False,
        ), patch("fund_llm.llm_models.config.LLM_API_KEY", ""), patch(
            "fund_llm.llm_models.config.LLM_BASE_URL",
            "https://opencode.ai/zen/go/v1",
        ), patch("fund_llm.llm_models.config.LLM_MODEL", "deepseek-v4-flash"), patch(
            "fund_llm.llm_models.fetch_gateway_models",
            side_effect=RuntimeError("offline"),
        ):
            clear_model_catalog_cache()
            catalog = resolve_available_models(use_cache=False)

        self.assertEqual(catalog["source"], "static")
        self.assertEqual(catalog["default_model"], "deepseek-v4-flash")
        self.assertTrue(any(item["id"] == "deepseek-v4-flash" for item in catalog["models"]))

    def test_resolve_available_models_uses_live_catalog_when_available(self):
        with patch.dict(
            os.environ,
            {
                "LLM_BASE_URL": "https://opencode.ai/zen/go/v1",
                "LLM_MODEL": "deepseek-v4-pro",
            },
            clear=False,
        ), patch("fund_llm.llm_models.config.LLM_API_KEY", "demo-key"), patch(
            "fund_llm.llm_models.config.LLM_BASE_URL",
            "https://opencode.ai/zen/go/v1",
        ), patch("fund_llm.llm_models.config.LLM_MODEL", "deepseek-v4-pro"), patch(
            "fund_llm.llm_models.fetch_gateway_models",
            return_value=["deepseek-v4-pro", "deepseek-v4-flash", "minimax-m3"],
        ):
            clear_model_catalog_cache()
            catalog = resolve_available_models(use_cache=False)

        self.assertEqual(catalog["source"], "live")
        self.assertEqual(
            [item["id"] for item in catalog["models"]],
            ["deepseek-v4-pro", "deepseek-v4-flash"],
        )

    def test_llm_allowed_models_env_limits_catalog(self):
        with patch.dict(
            os.environ,
            {
                "LLM_BASE_URL": "https://opencode.ai/zen/go/v1",
                "LLM_MODEL": "deepseek-v4-flash",
                "LLM_ALLOWED_MODELS": "deepseek-v4-flash,deepseek-v4-pro",
            },
            clear=False,
        ), patch("fund_llm.llm_models.config.LLM_API_KEY", ""), patch(
            "fund_llm.llm_models.config.LLM_BASE_URL",
            "https://opencode.ai/zen/go/v1",
        ), patch("fund_llm.llm_models.config.LLM_MODEL", "deepseek-v4-flash"):
            clear_model_catalog_cache()
            catalog = resolve_available_models(use_cache=False)

        self.assertEqual(
            [item["id"] for item in catalog["models"]],
            ["deepseek-v4-flash", "deepseek-v4-pro"],
        )


if __name__ == "__main__":
    unittest.main()
