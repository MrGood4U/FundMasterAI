import json
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fund_llm.golden_suite import run_golden_suite
from fund_llm.mock_pipeline import run_mock_analysis


class GoldenSuiteTest(unittest.TestCase):
    def manifest_path(self):
        return os.path.join(
            os.path.dirname(__file__),
            "..",
            "examples",
            "golden_cases_manifest.json",
        )

    def test_golden_suite_runs_in_mock_mode(self):
        manifest_path = self.manifest_path()
        with open(manifest_path, "r", encoding="utf-8") as file:
            manifest = json.load(file)

        report = run_golden_suite(manifest_path=manifest_path, analysis_mode="mock")

        self.assertEqual(report.analysis_mode, "mock")
        self.assertEqual(report.total_cases, len(manifest["cases"]))
        self.assertEqual(report.failed_cases, 0)
        self.assertIn(report.overall_status, {"pass", "review"})
        self.assertTrue(any(case.tier == "golden_real" for case in report.case_reports))
        self.assertTrue(any(case.tier == "regression_case" for case in report.case_reports))
        conflicting_case = next(
            case for case in report.case_reports if case.case_id == "regression_conflicting_signals"
        )
        self.assertTrue(any(check.name == "expected_text_fragments" for check in conflicting_case.checks))
        baijiu_case = next(
            case for case in report.case_reports if case.case_id == "real_161725_baijiu_single_sector"
        )
        self.assertEqual(baijiu_case.tier, "golden_real")
        self.assertTrue(any(check.name == "expected_text_fragments" for check in baijiu_case.checks))
        fixed_income_case = next(
            case for case in report.case_reports if case.case_id == "real_003358_fixed_income_duration"
        )
        self.assertEqual(fixed_income_case.tier, "golden_real")
        self.assertTrue(any(check.name == "expected_text_fragments" for check in fixed_income_case.checks))

    def test_golden_case_hard_fails_on_any_technical_agent_error(self):
        result = run_mock_analysis()
        output = next(output for output in result.agent_outputs if output.status == "success")
        output.status = "error"
        output.score = None
        output.stance = "mixed"
        output.key_points = []
        output.confidence = 0.0
        output.narrative = f"{output.agent_name} failed: injected test failure"
        result.metadata.update(
            {
                "analysis_status": "technical_error",
                "success_agent_count": str(
                    len([item for item in result.agent_outputs if item.status == "success"])
                ),
                "error_agent_count": "1",
            }
        )
        result.overall_rating = "unavailable"
        result.overall_score = None

        with patch("fund_llm.golden_suite._run_analysis", return_value=result):
            report = run_golden_suite(
                manifest_path=self.manifest_path(),
                analysis_mode="mock",
            )

        baseline_case = next(
            case for case in report.case_reports if case.case_id == "mock_baseline_full_context"
        )
        execution_check = next(
            check for check in baseline_case.checks if check.name == "agent_execution_health"
        )
        self.assertFalse(execution_check.passed)
        self.assertEqual(baseline_case.overall_status, "fail")


if __name__ == "__main__":
    unittest.main()
