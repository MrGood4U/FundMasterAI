import json
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fund_llm.llm_client import LLMClient, _extract_text_content


class FakeHTTPResponse:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class LLMClientTest(unittest.TestCase):
    def test_extract_text_content_supports_string_content(self):
        payload = {"choices": [{"message": {"content": "hello"}}]}
        self.assertEqual(_extract_text_content(payload), "hello")

    def test_extract_text_content_supports_list_content(self):
        payload = {
            "choices": [
                {
                    "message": {
                        "content": [
                            {"type": "text", "text": "first"},
                            {"type": "text", "text": "second"},
                        ]
                    }
                }
            ]
        }
        self.assertEqual(_extract_text_content(payload), "first\nsecond")

    def test_chat_posts_to_openai_compatible_endpoint(self):
        captured = {}

        def fake_urlopen(http_request, timeout):
            captured["url"] = http_request.full_url
            captured["authorization"] = http_request.headers.get("Authorization")
            captured["timeout"] = timeout
            captured["payload"] = json.loads(http_request.data.decode("utf-8"))
            return FakeHTTPResponse({"choices": [{"message": {"content": "PROJECT_OK"}}]})

        client = LLMClient(
            api_key="demo-key",
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            model="gemini-3-flash-preview",
            timeout_seconds=12,
        )

        with patch("fund_llm.llm_client.request.urlopen", side_effect=fake_urlopen):
            response = client.chat(
                system_prompt="system message",
                user_prompt="user message",
                temperature=0.2,
                max_tokens=50,
            )

        self.assertEqual(response, "PROJECT_OK")
        self.assertEqual(
            captured["url"],
            "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        )
        self.assertEqual(captured["authorization"], "Bearer demo-key")
        self.assertEqual(captured["timeout"], 12)
        self.assertEqual(captured["payload"]["model"], "gemini-3-flash-preview")
        self.assertEqual(captured["payload"]["temperature"], 0.2)
        self.assertEqual(captured["payload"]["max_tokens"], 50)

    def test_chat_can_include_provider_specific_thinking_controls(self):
        captured = {}

        def fake_urlopen(http_request, timeout):
            captured["payload"] = json.loads(http_request.data.decode("utf-8"))
            return FakeHTTPResponse({"choices": [{"message": {"content": "OK"}}]})

        client = LLMClient(
            api_key="demo-key",
            base_url="https://api.deepseek.com",
            model="deepseek-v4-flash",
            thinking_mode="disabled",
            reasoning_effort="high",
        )

        with patch("fund_llm.llm_client.request.urlopen", side_effect=fake_urlopen):
            response = client.chat(system_prompt="system", user_prompt="user")

        self.assertEqual(response, "OK")
        self.assertEqual(captured["payload"]["thinking"], {"type": "disabled"})
        self.assertEqual(captured["payload"]["reasoning_effort"], "high")

    def test_invalid_thinking_mode_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "LLM_THINKING_MODE"):
            LLMClient(
                api_key="demo-key",
                base_url="https://api.deepseek.com",
                model="deepseek-v4-flash",
                thinking_mode="maybe",
            )


if __name__ == "__main__":
    unittest.main()
