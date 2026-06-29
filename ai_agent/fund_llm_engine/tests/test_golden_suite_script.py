import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def load_script_module(script_name: str):
    script_path = os.path.join(os.path.dirname(__file__), "..", "scripts", script_name)
    spec = importlib.util.spec_from_file_location(f"test_{script_name.replace('.', '_')}", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def manifest_case_count() -> int:
    manifest_path = os.path.join(os.path.dirname(__file__), "..", "examples", "golden_cases_manifest.json")
    with open(manifest_path, "r", encoding="utf-8") as file:
        return len(json.load(file)["cases"])


class GoldenSuiteScriptTest(unittest.TestCase):
    def test_run_golden_suite_prints_report(self):
        module = load_script_module("run_golden_suite.py")
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()

        with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
            exit_code = module.main(["run_golden_suite.py", "--mode", "mock"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr_buffer.getvalue(), "")
        report = json.loads(stdout_buffer.getvalue())
        self.assertEqual(report["total_cases"], manifest_case_count())
        self.assertIn(report["overall_status"], {"pass", "review"})

    def test_run_golden_suite_supports_output_file(self):
        module = load_script_module("run_golden_suite.py")
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "golden_suite_report.json")
            with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
                exit_code = module.main(
                    ["run_golden_suite.py", "--mode", "mock", "--output", output_path]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout_buffer.getvalue(), "")
            self.assertIn("Wrote golden suite report to", stderr_buffer.getvalue())
            with open(output_path, "r", encoding="utf-8") as file:
                report = json.load(file)
            self.assertEqual(report["total_cases"], manifest_case_count())
            self.assertIn("case_reports", report)

    def test_run_golden_suite_can_write_full_case_results(self):
        module = load_script_module("run_golden_suite.py")
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "golden_suite_report.json")
            results_dir = os.path.join(temp_dir, "case_results")
            with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
                exit_code = module.main(
                    [
                        "run_golden_suite.py",
                        "--mode",
                        "mock",
                        "--output",
                        output_path,
                        "--results-dir",
                        results_dir,
                    ]
                )

            self.assertEqual(exit_code, 0)
            with open(output_path, "r", encoding="utf-8") as file:
                report = json.load(file)
            self.assertEqual(report["total_cases"], manifest_case_count())
            first_case = report["case_reports"][0]
            self.assertTrue(first_case["result_path"])

            result_files = os.listdir(results_dir)
            self.assertEqual(len(result_files), manifest_case_count())
            with open(os.path.join(results_dir, result_files[0]), "r", encoding="utf-8") as file:
                case_result = json.load(file)
            self.assertIn("summary", case_result)
            self.assertIn("agent_outputs", case_result)


if __name__ == "__main__":
    unittest.main()
