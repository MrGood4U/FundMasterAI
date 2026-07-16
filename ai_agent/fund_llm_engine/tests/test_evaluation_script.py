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


class EvaluationScriptTest(unittest.TestCase):
    def test_evaluate_analysis_output_prints_report(self):
        module = load_script_module("evaluate_analysis_output.py")
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()

        with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
            exit_code = module.main(
                ["evaluate_analysis_output.py", "--input", "examples/mock_input.json", "--mode", "mock"]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr_buffer.getvalue(), "")
        report = json.loads(stdout_buffer.getvalue())
        self.assertEqual(report["request_id"], "mock-demo-001")
        self.assertIn(report["overall_status"], {"pass", "review"})

    def test_evaluate_analysis_output_supports_output_file(self):
        module = load_script_module("evaluate_analysis_output.py")
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "evaluation_report.json")
            with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
                exit_code = module.main(
                    [
                        "evaluate_analysis_output.py",
                        "--input",
                        "examples/mock_input.json",
                        "--mode",
                        "mock",
                        "--output",
                        output_path,
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout_buffer.getvalue(), "")
            self.assertIn("Wrote evaluation report to", stderr_buffer.getvalue())
            with open(output_path, "r", encoding="utf-8") as file:
                report = json.load(file)
            self.assertEqual(report["request_id"], "mock-demo-001")
            self.assertIn("checks", report)


if __name__ == "__main__":
    unittest.main()
