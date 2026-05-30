import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fund_llm.golden_suite import run_golden_suite


class GoldenSuiteTest(unittest.TestCase):
    def test_golden_suite_runs_in_mock_mode(self):
        manifest_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "examples",
            "golden_cases_manifest.json",
        )
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


if __name__ == "__main__":
    unittest.main()
