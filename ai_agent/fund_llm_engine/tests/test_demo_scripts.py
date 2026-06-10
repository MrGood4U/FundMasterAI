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


class DemoScriptsTest(unittest.TestCase):
    def test_run_mock_demo_prints_json_by_default(self):
        module = load_script_module("run_mock_demo.py")
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()

        with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
            exit_code = module.main(["run_mock_demo.py", "examples/mock_input.json"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr_buffer.getvalue(), "")
        payload = json.loads(stdout_buffer.getvalue())
        self.assertEqual(payload["request_id"], "mock-demo-001")
        self.assertEqual(len(payload["agent_outputs"]), 6)

    def test_run_mock_demo_supports_output_file(self):
        module = load_script_module("run_mock_demo.py")
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "mock_result.json")
            with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
                exit_code = module.main(
                    ["run_mock_demo.py", "examples/mock_input.json", "--output", output_path]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout_buffer.getvalue(), "")
            self.assertIn("Wrote analysis result to", stderr_buffer.getvalue())
            with open(output_path, "r", encoding="utf-8") as file:
                payload = json.load(file)
            self.assertEqual(payload["request_id"], "mock-demo-001")
            self.assertEqual(len(payload["agent_outputs"]), 6)

    def test_run_real_demo_supports_output_file(self):
        module = load_script_module("run_real_demo.py")

        class DummyResult:
            def __init__(self, request_id: str):
                self.request_id = request_id

            def to_dict(self):
                return {
                    "request_id": self.request_id,
                    "overall_rating": "hold",
                    "overall_score": 61.0,
                    "key_thesis": ["demo thesis"],
                    "main_risks": ["demo risk"],
                    "action_plan": ["demo action"],
                    "agent_outputs": [],
                    "summary": "demo summary",
                    "missing_fields": [],
                    "metadata": {"llm_mode": "real"},
                }

        def fake_run_real_analysis_for_input(payload, max_parallel_agents=None):
            return DummyResult(payload.request_id)

        module.run_real_analysis_for_input = fake_run_real_analysis_for_input

        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "real_result.json")
            with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
                exit_code = module.main(
                    ["run_real_demo.py", "examples/mock_input.json", "--output", output_path]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(stdout_buffer.getvalue(), "")
            self.assertIn("Wrote analysis result to", stderr_buffer.getvalue())
            with open(output_path, "r", encoding="utf-8") as file:
                payload = json.load(file)
            self.assertEqual(payload["request_id"], "mock-demo-001")
            self.assertEqual(payload["metadata"]["llm_mode"], "real")


if __name__ == "__main__":
    unittest.main()
