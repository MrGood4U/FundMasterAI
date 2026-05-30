import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fund_llm.evaluation import evaluate_analysis_result
from fund_llm.mock_pipeline import build_mock_input, run_mock_analysis


class EvaluationTest(unittest.TestCase):
    def test_evaluation_passes_for_current_mock_baseline(self):
        payload = build_mock_input()
        result = run_mock_analysis()

        report = evaluate_analysis_result(payload, result)

        self.assertEqual(report.request_id, payload.request_id)
        self.assertIn(report.overall_status, {"pass", "review"})
        self.assertGreaterEqual(report.total_score, 80)
        self.assertTrue(any(check.name == "core_agent_coverage" for check in report.checks))

    def test_evaluation_flags_wrong_rating(self):
        payload = build_mock_input()
        result = run_mock_analysis()
        result.overall_rating = "buy"

        report = evaluate_analysis_result(payload, result)
        score_check = next(check for check in report.checks if check.name == "score_consistency")

        self.assertFalse(score_check.passed)
        self.assertTrue(any("overall_rating" in detail for detail in score_check.details))

    def test_evaluation_flags_missing_core_agent(self):
        payload = build_mock_input()
        result = run_mock_analysis()
        result.agent_outputs = [output for output in result.agent_outputs if output.agent_name != "SectorAgent"]

        report = evaluate_analysis_result(payload, result)
        coverage_check = next(check for check in report.checks if check.name == "core_agent_coverage")

        self.assertFalse(coverage_check.passed)
        self.assertTrue(any("SectorAgent" in detail for detail in coverage_check.details))


if __name__ == "__main__":
    unittest.main()
