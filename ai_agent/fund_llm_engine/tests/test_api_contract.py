import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from fund_llm.mock_pipeline import build_mock_input  # noqa: E402


def load_agent_app():
    spec = importlib.util.spec_from_file_location("fundmaster_agent_app", ROOT / "app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


agent_app = load_agent_app()


class ApiContractTest(unittest.TestCase):
    def setUp(self):
        self.client = agent_app.create_app().test_client()

    def build_backend_payload(self):
        payload = build_mock_input()
        payload.extra_context.update(
            {
                "data_source": "backend_function_registry",
                "available_backend_tools": ",".join(
                    [
                        "get_fund_hist",
                        "get_fund_individual_basic_info",
                        "get_fund_portfolio_holds",
                        "get_fund_portfolio_industry_allocation",
                        "get_public_fund_announcement",
                    ]
                ),
                "successful_backend_tools": ",".join(
                    [
                        "get_fund_hist",
                        "get_fund_individual_basic_info",
                        "get_fund_portfolio_holds",
                        "get_public_fund_announcement",
                    ]
                ),
                "errored_backend_tools": "",
                "tool_trace": "[]",
            }
        )
        return payload

    def assert_keys(self, payload, expected_keys):
        self.assertTrue(
            set(expected_keys).issubset(payload),
            f"Missing keys: {sorted(set(expected_keys) - set(payload))}",
        )

    def test_analyze_success_response_matches_public_contract(self):
        with patch.object(
            agent_app,
            "build_fund_input_from_backend_functions",
            return_value=self.build_backend_payload(),
        ):
            response = self.client.post(
                "/api/ai/fund/analyze",
                json={
                    "code": "000001",
                    "start_date": "2025/01/01",
                    "mock": True,
                },
            )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["code"], 200)
        self.assertEqual(body["message"], "success")
        self.assert_keys(body, ["code", "data", "coverage", "message"])

        data = body["data"]
        self.assert_keys(
            data,
            [
                "request_id",
                "overall_rating",
                "overall_score",
                "summary",
                "score_explanation",
                "key_thesis",
                "main_risks",
                "action_plan",
                "agent_outputs",
                "analysis_trace",
                "missing_fields",
                "metadata",
            ],
        )
        self.assertIsInstance(data["overall_rating"], str)
        self.assertIsInstance(data["overall_score"], (int, float))
        self.assertIsInstance(data["summary"], str)
        self.assertIsInstance(data["score_explanation"], str)
        self.assertIsInstance(data["key_thesis"], list)
        self.assertIsInstance(data["main_risks"], list)
        self.assertIsInstance(data["action_plan"], list)
        self.assertIsInstance(data["agent_outputs"], list)
        self.assertIsInstance(data["analysis_trace"], list)
        self.assertIsInstance(data["missing_fields"], list)
        self.assertIsInstance(data["metadata"], dict)

        self.assertGreater(len(data["agent_outputs"]), 0)
        for output in data["agent_outputs"]:
            self.assert_keys(
                output,
                [
                    "agent_name",
                    "status",
                    "stance",
                    "score",
                    "confidence",
                    "key_points",
                    "risks",
                    "recommendations",
                    "narrative",
                ],
            )
            self.assertIn(output["status"], {"success", "skipped", "error"})
            self.assertIsInstance(output["agent_name"], str)
            self.assertIsInstance(output["stance"], str)
            self.assertTrue(output["score"] is None or isinstance(output["score"], (int, float)))
            self.assertIsInstance(output["confidence"], (int, float))
            self.assertIsInstance(output["key_points"], list)
            self.assertIsInstance(output["risks"], list)
            self.assertIsInstance(output["recommendations"], list)
            self.assertIsInstance(output["narrative"], str)

        self.assertGreater(len(data["analysis_trace"]), 0)
        for event in data["analysis_trace"]:
            self.assert_keys(
                event,
                ["category", "title", "detail", "status", "evidence", "technical"],
            )
            self.assertIsInstance(event["category"], str)
            self.assertIsInstance(event["title"], str)
            self.assertIsInstance(event["detail"], str)
            self.assertIsInstance(event["status"], str)
            self.assertIsInstance(event["evidence"], dict)
            self.assertIsInstance(event["technical"], dict)

        coverage = body["coverage"]
        self.assert_keys(
            coverage,
            [
                "nav_points",
                "has_top_holdings_weight",
                "has_industry_exposure",
                "has_news_items",
                "fund_name",
                "fund_type",
                "normalized_fund_type",
                "fund_family",
                "data_coverage",
                "data_source",
                "available_backend_tools",
                "successful_backend_tools",
                "errored_backend_tools",
            ],
        )
        self.assertIsInstance(coverage["nav_points"], int)
        self.assertIsInstance(coverage["data_coverage"], dict)
        allowed_coverage_values = {"available", "missing", "missing_backend_capability", "not_applicable"}
        self.assertTrue(set(coverage["data_coverage"].values()).issubset(allowed_coverage_values))

    def test_missing_code_error_matches_public_contract(self):
        response = self.client.post("/api/ai/fund/analyze", json={})

        body = response.get_json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(body, {"code": 400, "data": None, "message": "code is required"})

    def test_value_error_response_matches_public_contract(self):
        with patch.object(
            agent_app,
            "build_fund_input_from_backend_functions",
            side_effect=ValueError("No NAV data returned for fund 000002"),
        ):
            response = self.client.post("/api/ai/fund/analyze", json={"code": "000002", "mock": True})

        body = response.get_json()
        self.assertEqual(response.status_code, 422)
        self.assertEqual(body["code"], 422)
        self.assertIsNone(body["data"])
        self.assertEqual(body["message"], "No NAV data returned for fund 000002")

    def test_unexpected_error_response_matches_public_contract(self):
        with patch.object(
            agent_app,
            "build_fund_input_from_backend_functions",
            side_effect=RuntimeError("backend unavailable"),
        ):
            response = self.client.post("/api/ai/fund/analyze", json={"code": "000001", "mock": True})

        body = response.get_json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(body["code"], 500)
        self.assertIsNone(body["data"])
        self.assertEqual(body["message"], "backend unavailable")


if __name__ == "__main__":
    unittest.main()
