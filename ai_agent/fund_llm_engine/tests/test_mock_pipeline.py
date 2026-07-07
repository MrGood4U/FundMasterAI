import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fund_llm.mock_pipeline import (
    build_mock_engine,
    build_mock_input,
    run_mock_analysis,
    run_mock_analysis_as_dict,
    run_mock_analysis_for_input,
)


class MockPipelineTest(unittest.TestCase):
    def test_build_mock_input_contains_expected_fields(self):
        payload = build_mock_input()

        self.assertEqual(payload.request_id, "mock-demo-001")
        self.assertEqual(payload.fund_info.code, "005827")
        self.assertEqual(len(payload.nav_series), 5)
        self.assertIsNotNone(payload.analysis_window)
        self.assertIsNotNone(payload.benchmark)
        self.assertEqual(len(payload.benchmark_nav_series), 5)
        self.assertTrue(payload.industry_exposure)
        self.assertIsNotNone(payload.top_holdings_weight)

    def test_run_mock_analysis_executes_full_pipeline(self):
        result = run_mock_analysis(mock_response="demo narrative")

        self.assertEqual(result.request_id, "mock-demo-001")
        self.assertEqual(len(result.agent_outputs), 7)
        self.assertEqual(result.summary, "demo narrative")
        self.assertIn(result.overall_rating, {"buy", "hold", "watch", "avoid"})

    def test_run_mock_analysis_as_dict_is_json_friendly(self):
        result = run_mock_analysis_as_dict(mock_response="json narrative")

        self.assertEqual(result["request_id"], "mock-demo-001")
        self.assertEqual(result["summary"], "json narrative")
        self.assertEqual(len(result["agent_outputs"]), 7)
        self.assertEqual(result["missing_fields"], [])

    def test_build_mock_engine_uses_seven_domain_agents(self):
        engine = build_mock_engine()

        self.assertEqual(len(engine.agents), 7)
        self.assertEqual(engine.agents[0].name, "PerformanceAgent")
        self.assertEqual(engine.agents[1].name, "ExposureAgent")
        self.assertEqual(engine.agents[2].name, "BondExposureAgent")
        self.assertEqual(engine.agents[3].name, "RiskAgent")
        self.assertEqual(engine.agents[4].name, "SentimentAgent")
        self.assertEqual(engine.agents[5].name, "SectorAgent")
        self.assertEqual(engine.agents[6].name, "MarketAgent")

    def test_mock_input_supports_market_agent_success(self):
        result = run_mock_analysis(mock_response="market narrative")

        market_output = [
            output for output in result.agent_outputs if output.agent_name == "MarketAgent"
        ][0]
        self.assertEqual(market_output.status, "success")
        self.assertTrue(any("peers" in point for point in market_output.key_points))

    def test_run_mock_analysis_for_input_accepts_external_payload(self):
        payload = build_mock_input()
        payload.top_holdings_weight = None

        result = run_mock_analysis_for_input(payload, mock_response="external narrative")

        self.assertEqual(result.summary, "external narrative")
        self.assertIn("top_holdings_weight", result.missing_fields)


if __name__ == "__main__":
    unittest.main()
