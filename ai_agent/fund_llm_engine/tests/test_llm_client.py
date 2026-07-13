import json
import os
import sys
import unittest
from io import BytesIO
from unittest.mock import patch
from urllib import error

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fund_llm.llm_client import (
    LLMClient,
    LLMEmptyResponseError,
    LLMHTTPError,
    LLMTransportError,
    MockLLMClient,
    _extract_text_content,
)


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
            captured["user_agent"] = http_request.headers.get("User-agent")
            captured["timeout"] = timeout
            captured["payload"] = json.loads(http_request.data.decode("utf-8"))
            return FakeHTTPResponse({"choices": [{"message": {"content": "PROJECT_OK"}}]})

        client = LLMClient(
            api_key="demo-key",
            base_url="https://opencode.ai/zen/go/v1",
            model="deepseek-v4-flash",
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
            "https://opencode.ai/zen/go/v1/chat/completions",
        )
        self.assertEqual(captured["authorization"], "Bearer demo-key")
        self.assertEqual(captured["user_agent"], "FundMasterAI/1.0")
        self.assertEqual(captured["timeout"], 12)
        self.assertEqual(captured["payload"]["model"], "deepseek-v4-flash")
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

    def test_chat_retries_length_empty_content_with_diagnostics(self):
        captured_payloads = []
        responses = [
            {
                "id": "first",
                "model": "deepseek-v4-flash",
                "choices": [
                    {
                        "finish_reason": "length",
                        "message": {
                            "content": "",
                            "reasoning_content": "internal reasoning omitted",
                        },
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 50,
                    "total_tokens": 60,
                },
            },
            {
                "id": "retry",
                "model": "deepseek-v4-flash",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": "Recovered narrative"},
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30,
                },
            },
        ]

        def fake_urlopen(http_request, timeout):
            captured_payloads.append(json.loads(http_request.data.decode("utf-8")))
            return FakeHTTPResponse(responses.pop(0))

        client = LLMClient(
            api_key="demo-key",
            base_url="https://opencode.ai/zen/go/v1",
            model="deepseek-v4-flash",
            thinking_mode="enabled",
            reasoning_effort="high",
        )

        with patch("fund_llm.llm_client.request.urlopen", side_effect=fake_urlopen):
            response = client.chat("system", "user", max_tokens=100)

        self.assertEqual(response, "Recovered narrative")
        self.assertEqual(len(captured_payloads), 2)
        self.assertEqual(captured_payloads[0]["max_tokens"], 100)
        self.assertEqual(captured_payloads[0]["thinking"], {"type": "enabled"})
        self.assertEqual(captured_payloads[0]["reasoning_effort"], "high")
        self.assertGreater(captured_payloads[1]["max_tokens"], 100)
        self.assertEqual(captured_payloads[1]["thinking"], {"type": "disabled"})
        self.assertNotIn("reasoning_effort", captured_payloads[1])
        self.assertEqual(client.last_response_metadata["retry_count"], 1)
        self.assertEqual(client.last_response_metadata["attempt_count"], 2)
        self.assertEqual(client.last_response_metadata["attempts"][0]["finish_reason"], "length")
        self.assertTrue(client.last_response_metadata["attempts"][0]["reasoning_content_present"])
        self.assertEqual(client.last_response_metadata["finish_reason"], "stop")

    def test_chat_raises_empty_response_after_failed_retry(self):
        responses = [
            {
                "choices": [
                    {
                        "finish_reason": "length",
                        "message": {"content": "", "reasoning_content": "reasoning only"},
                    }
                ]
            },
            {
                "choices": [
                    {
                        "finish_reason": "length",
                        "message": {"content": ""},
                    }
                ]
            },
        ]

        def fake_urlopen(http_request, timeout):
            return FakeHTTPResponse(responses.pop(0))

        client = LLMClient(
            api_key="demo-key",
            base_url="https://api.deepseek.com",
            model="deepseek-v4-flash",
            thinking_mode="enabled",
        )

        with patch("fund_llm.llm_client.request.urlopen", side_effect=fake_urlopen):
            with self.assertRaisesRegex(LLMEmptyResponseError, "LLM returned empty content"):
                client.chat("system", "user", max_tokens=80)

        self.assertEqual(client.last_response_metadata["retry_count"], 1)
        self.assertEqual(client.last_response_metadata["attempt_count"], 2)

    def test_chat_raises_empty_response_without_retry_for_stop_finish_reason(self):
        call_count = 0

        def fake_urlopen(http_request, timeout):
            nonlocal call_count
            call_count += 1
            return FakeHTTPResponse(
                {
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {"content": ""},
                        }
                    ]
                }
            )

        client = LLMClient(
            api_key="demo-key",
            base_url="https://api.openai.com/v1",
            model="demo-model",
        )

        with patch("fund_llm.llm_client.request.urlopen", side_effect=fake_urlopen):
            with self.assertRaisesRegex(LLMEmptyResponseError, "finish_reason=stop"):
                client.chat("system", "user")

        self.assertEqual(call_count, 1)
        self.assertEqual(client.last_response_metadata["retry_count"], 0)

    def test_is_mock_flags_are_explicit(self):
        real_client = LLMClient(
            api_key="demo-key",
            base_url="https://api.openai.com/v1",
            model="demo-model",
        )
        self.assertFalse(real_client.is_mock)
        self.assertTrue(MockLLMClient("narrative").is_mock)

    def test_retryable_http_error_is_retried_once(self):
        call_count = 0

        def fake_urlopen(http_request, timeout):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise error.HTTPError(
                    url=http_request.full_url,
                    code=429,
                    msg="Too Many Requests",
                    hdrs=None,
                    fp=BytesIO(b"rate limited"),
                )
            return FakeHTTPResponse({"choices": [{"message": {"content": "recovered"}}]})

        client = LLMClient(
            api_key="demo-key",
            base_url="https://api.openai.com/v1",
            model="demo-model",
        )

        with patch("fund_llm.llm_client.request.urlopen", side_effect=fake_urlopen), patch(
            "fund_llm.llm_client.time.sleep"
        ) as fake_sleep:
            response = client.chat("system", "user")

        self.assertEqual(response, "recovered")
        self.assertEqual(call_count, 2)
        fake_sleep.assert_called_once()
        self.assertEqual(client.last_response_metadata["transport_retry_count"], 1)

    def test_timeout_is_retried_once_then_raised(self):
        call_count = 0

        def fake_urlopen(http_request, timeout):
            nonlocal call_count
            call_count += 1
            raise error.URLError(TimeoutError("timed out"))

        client = LLMClient(
            api_key="demo-key",
            base_url="https://api.openai.com/v1",
            model="demo-model",
        )

        with patch("fund_llm.llm_client.request.urlopen", side_effect=fake_urlopen), patch(
            "fund_llm.llm_client.time.sleep"
        ):
            with self.assertRaises(LLMTransportError) as context:
                client.chat("system", "user")

        self.assertEqual(call_count, 2)
        self.assertTrue(context.exception.is_timeout)

    def test_config_errors_are_not_retried(self):
        call_count = 0

        def fake_urlopen(http_request, timeout):
            nonlocal call_count
            call_count += 1
            raise error.HTTPError(
                url=http_request.full_url,
                code=401,
                msg="Unauthorized",
                hdrs=None,
                fp=BytesIO(b"bad key"),
            )

        client = LLMClient(
            api_key="demo-key",
            base_url="https://api.openai.com/v1",
            model="demo-model",
        )

        with patch("fund_llm.llm_client.request.urlopen", side_effect=fake_urlopen), patch(
            "fund_llm.llm_client.time.sleep"
        ) as fake_sleep:
            with self.assertRaises(LLMHTTPError) as context:
                client.chat("system", "user")

        self.assertEqual(call_count, 1)
        fake_sleep.assert_not_called()
        self.assertEqual(context.exception.status_code, 401)

    def test_non_timeout_transport_error_is_not_retried(self):
        call_count = 0

        def fake_urlopen(http_request, timeout):
            nonlocal call_count
            call_count += 1
            raise error.URLError(ConnectionRefusedError("refused"))

        client = LLMClient(
            api_key="demo-key",
            base_url="https://api.openai.com/v1",
            model="demo-model",
        )

        with patch("fund_llm.llm_client.request.urlopen", side_effect=fake_urlopen), patch(
            "fund_llm.llm_client.time.sleep"
        ) as fake_sleep:
            with self.assertRaises(LLMTransportError) as context:
                client.chat("system", "user")

        self.assertEqual(call_count, 1)
        fake_sleep.assert_not_called()
        self.assertFalse(context.exception.is_timeout)

    def test_http_errors_are_sanitized(self):
        def fake_urlopen(http_request, timeout):
            raise error.HTTPError(
                url=http_request.full_url,
                code=500,
                msg="Internal Server Error",
                hdrs=None,
                fp=BytesIO(b'{"error":"secret provider body with token"}'),
            )

        client = LLMClient(
            api_key="demo-key",
            base_url="https://api.openai.com/v1",
            model="demo-model",
        )

        # 500 属于可重试错误，这里两次都失败后应抛出脱敏后的异常。
        with patch("fund_llm.llm_client.request.urlopen", side_effect=fake_urlopen), patch(
            "fund_llm.llm_client.time.sleep"
        ):
            with self.assertRaises(LLMHTTPError) as context:
                client.chat("system", "user")

        message = str(context.exception)
        self.assertIn("LLM HTTP 500", message)
        self.assertIn("Provider response body omitted", message)
        self.assertNotIn("secret provider body", message)
        self.assertNotIn("token", message)


if __name__ == "__main__":
    unittest.main()
