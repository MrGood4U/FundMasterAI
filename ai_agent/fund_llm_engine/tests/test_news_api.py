import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))


def load_agent_app():
    spec = importlib.util.spec_from_file_location("fundmaster_agent_news_app", ROOT / "app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


agent_app = load_agent_app()


def backend_style_rows():
    return [
        {
            "news_title": "公司业绩超预期，机构上调评级",
            "news_content": "多家机构认为盈利改善趋势确立。",
            "publish_time": "2026-07-07 09:30:00",
            "文章来源": "证券时报",
        },
        {
            "news_title": "监管处罚落地，短期承压",
            "news_content": "公司收到监管警示函。",
            "publish_time": "2026-07-07 08:00:00",
            "文章来源": "财联社",
        },
    ]


class NewsApiContractTest(unittest.TestCase):
    def setUp(self):
        self.client = agent_app.create_app().test_client()

    def assert_keys(self, payload, expected_keys):
        self.assertTrue(
            set(expected_keys).issubset(payload),
            f"Missing keys: {sorted(set(expected_keys) - set(payload))}",
        )

    def test_news_summary_success_matches_contract(self):
        response = self.client.post(
            "/api/ai/news/summary",
            json={"items": backend_style_rows(), "symbol": "300059", "mock": True},
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["code"], 200)
        self.assert_keys(body, ["code", "data", "coverage", "message"])

        data = body["data"]
        self.assert_keys(
            data,
            [
                "request_id",
                "status",
                "summary",
                "sentiment",
                "confidence",
                "related_symbols",
                "items_analyzed",
                "item_signals",
                "metadata",
                "analysis_trace",
            ],
        )
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["related_symbols"], ["300059"])
        self.assertEqual(data["items_analyzed"], 2)
        self.assert_keys(
            data["sentiment"],
            ["label", "positive_count", "negative_count", "neutral_count", "risk_event_count"],
        )
        self.assertGreaterEqual(data["confidence"], 0.4)
        self.assertLessEqual(data["confidence"], 0.9)
        self.assertEqual(data["metadata"]["llm_mode"], "mock")
        self.assertEqual(data["metadata"]["analysis_level"], "news")
        for signal in data["item_signals"]:
            self.assert_keys(signal, ["title", "sentiment", "risk_event"])

        coverage = body["coverage"]
        self.assert_keys(
            coverage,
            ["items_received", "items_used", "has_symbol", "data_source"],
        )
        self.assertEqual(coverage["items_received"], 2)
        self.assertTrue(coverage["has_symbol"])

    def test_news_alias_field_is_accepted(self):
        response = self.client.post(
            "/api/ai/news/summary",
            json={"news": backend_style_rows(), "mock": True},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"]["related_symbols"], [])

    def test_missing_items_returns_400(self):
        response = self.client.post("/api/ai/news/summary", json={"symbol": "300059"})

        body = response.get_json()
        self.assertEqual(response.status_code, 400)
        self.assertIn("items is required", body["message"])

    def test_unusable_items_return_422(self):
        response = self.client.post(
            "/api/ai/news/summary",
            json={"items": [{"publish_time": "2026-07-07"}], "mock": True},
        )

        body = response.get_json()
        self.assertEqual(response.status_code, 422)
        self.assertIn("No usable news items", body["message"])

    def test_real_mode_accepts_llm_model_override(self):
        captured = {}

        def fake_real(raw_items, symbol="", max_items=10, model=None, timeout_seconds=None):
            captured["model"] = model
            captured["timeout_seconds"] = timeout_seconds
            from fund_llm.news_summary import run_mock_news_summary

            result = run_mock_news_summary(raw_items, symbol=symbol, max_items=max_items)
            result["metadata"]["llm_mode"] = "real"
            result["metadata"]["llm_model"] = model or ""
            return result

        with patch.object(agent_app, "run_real_news_summary", side_effect=fake_real):
            response = self.client.post(
                "/api/ai/news/summary",
                json={
                    "items": backend_style_rows(),
                    "symbol": "300059",
                    "mock": False,
                    "llm_model": "deepseek-v4-pro",
                    "llm_timeout_seconds": 45,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(captured["model"], "deepseek-v4-pro")
        self.assertEqual(captured["timeout_seconds"], 45)

    def test_unexpected_error_response_is_sanitized(self):
        with patch.object(
            agent_app,
            "run_mock_news_summary",
            side_effect=RuntimeError("secret stacktrace"),
        ):
            response = self.client.post(
                "/api/ai/news/summary",
                json={"items": backend_style_rows(), "mock": True},
            )

        body = response.get_json()
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("secret stacktrace", body["message"])
        self.assertIn("Internal error", body["message"])


if __name__ == "__main__":
    unittest.main()
