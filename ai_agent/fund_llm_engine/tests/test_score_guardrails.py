import contextlib
import importlib.util
import io
import json
import os
import subprocess
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


def sample_api_payload(
    *,
    performance_score=100.0,
    risk_score=43.1,
    exposure_score=60.0,
    sector_score=None,
    sector_status="skipped",
):
    agent_outputs = [
        {
            "agent_name": "PerformanceAgent",
            "status": "success",
            "stance": "positive",
            "score": performance_score,
            "confidence": 0.78,
            "narrative": "ignored unstable text",
        },
        {
            "agent_name": "ExposureAgent",
            "status": "success",
            "stance": "neutral",
            "score": exposure_score,
            "confidence": 0.70,
            "narrative": "ignored unstable text",
        },
        {
            "agent_name": "RiskAgent",
            "status": "success",
            "stance": "neutral",
            "score": risk_score,
            "confidence": 0.80,
            "narrative": "ignored unstable text",
        },
        {
            "agent_name": "SectorAgent",
            "status": sector_status,
            "stance": "insufficient_data" if sector_status == "skipped" else "neutral",
            "score": sector_score,
            "confidence": 0.0 if sector_status == "skipped" else 0.76,
            "narrative": "ignored unstable text",
        },
    ]
    scored = [item["score"] for item in agent_outputs if item["score"] is not None and item["status"] == "success"]
    return {
        "code": 200,
        "message": "success",
        "coverage": {
            "nav_points": 343,
            "fund_name": "华夏成长混合",
            "fund_type": "混合型-偏股",
            "normalized_fund_type": "mixed_fund",
            "fund_family": "equity_like",
            "data_coverage": {
                "nav": "available",
                "stock_holdings": "available",
                "industry_exposure": "available" if sector_status == "success" else "missing_backend_capability",
            },
        },
        "data": {
            "overall_score": sum(scored) / len(scored),
            "overall_rating": "hold",
            "missing_fields": [] if sector_status == "success" else ["industry_exposure"],
            "agent_outputs": agent_outputs,
            "analysis_trace": [
                {
                    "title": "Discovered backend tools",
                    "evidence": {
                        "available_tool_count": 20,
                        "successful_tool_count": 9,
                        "errored_tool_count": 0,
                    },
                },
                {
                    "title": "Checked backend data coverage",
                    "evidence": {
                        "missing_or_limited": {}
                        if sector_status == "success"
                        else {"industry_exposure": "missing_backend_capability"}
                    },
                },
            ],
        },
    }


class ScoreGuardrailsTest(unittest.TestCase):
    def test_snapshot_compacts_stable_fields_and_omits_narrative(self):
        module = load_script_module("score_guardrails.py")

        def fake_post_json(url, body, timeout):
            return sample_api_payload()

        module.post_json = fake_post_json

        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "snapshot.json")
            with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
                exit_code = module.main(
                    [
                        "score_guardrails.py",
                        "snapshot",
                        "--fund",
                        "000001",
                        "--output",
                        output_path,
                    ]
                )

            self.assertEqual(exit_code, 0)
            with open(output_path, "r", encoding="utf-8") as file:
                snapshot = json.load(file)
            fund = snapshot["funds"][0]
            self.assertEqual(fund["fund_code"], "000001")
            self.assertEqual(fund["coverage"]["nav_points"], 343)
            self.assertEqual(fund["analysis_trace"]["available_tool_count"], 20)
            self.assertNotIn("narrative", json.dumps(fund, ensure_ascii=False))

    def test_compare_flags_stable_agent_score_regression(self):
        module = load_script_module("score_guardrails.py")
        before_fund = module.compact_result(sample_api_payload(risk_score=43.1), {"code": "000001", "start_date": "2025/01/01", "mock": True})
        after_fund = module.compact_result(sample_api_payload(risk_score=51.0), {"code": "000001", "start_date": "2025/01/01", "mock": True})
        before = {"schema_version": 1, "funds": [before_fund]}
        after = {"schema_version": 1, "funds": [after_fund]}

        stdout_buffer = io.StringIO()
        with tempfile.TemporaryDirectory() as temp_dir:
            before_path = os.path.join(temp_dir, "before.json")
            after_path = os.path.join(temp_dir, "after.json")
            with open(before_path, "w", encoding="utf-8") as file:
                json.dump(before, file)
            with open(after_path, "w", encoding="utf-8") as file:
                json.dump(after, file)
            with contextlib.redirect_stdout(stdout_buffer):
                exit_code = module.main(
                    [
                        "score_guardrails.py",
                        "compare",
                        "--before",
                        before_path,
                        "--after",
                        after_path,
                        "--fail-on-unexpected",
                    ]
                )

        self.assertEqual(exit_code, 1)
        report = json.loads(stdout_buffer.getvalue())
        self.assertEqual(report["status"], "fail")
        risk_change = [
            item
            for item in report["comparisons"][0]["agent_changes"]
            if item["agent_name"] == "RiskAgent"
        ][0]
        self.assertEqual(risk_change["classification"], "unexpected")

    def test_compare_treats_new_sector_data_as_expected_data_change(self):
        module = load_script_module("score_guardrails.py")
        before_fund = module.compact_result(sample_api_payload(sector_status="skipped"), {"code": "000001", "start_date": "2025/01/01", "mock": True})
        after_fund = module.compact_result(
            sample_api_payload(exposure_score=30.4, sector_score=44.6, sector_status="success"),
            {"code": "000001", "start_date": "2025/01/01", "mock": True},
        )
        args = type("Args", (), {"stable_agent_tolerance": 0.5, "score_tolerance": 0.05})()
        comparison = module.compare_fund(before_fund, after_fund, args)

        self.assertEqual(comparison["status"], "pass")
        sector_change = [
            item
            for item in comparison["agent_changes"]
            if item["agent_name"] == "SectorAgent"
        ][0]
        self.assertEqual(sector_change["classification"], "expected_data_change")

    def test_scope_check_fails_backend_changes_without_override(self):
        module = load_script_module("score_guardrails.py")
        with tempfile.TemporaryDirectory() as temp_dir:
            subprocess.run(["git", "-C", temp_dir, "init"], check=True, capture_output=True)
            os.makedirs(os.path.join(temp_dir, "backend"), exist_ok=True)
            backend_file = os.path.join(temp_dir, "backend", "start.sh")
            with open(backend_file, "w", encoding="utf-8") as file:
                file.write("# changed\n")

            stdout_buffer = io.StringIO()
            with contextlib.redirect_stdout(stdout_buffer):
                exit_code = module.main(
                    [
                        "score_guardrails.py",
                        "scope-check",
                        "--repo-root",
                        temp_dir,
                    ]
                )

        self.assertEqual(exit_code, 1)
        report = json.loads(stdout_buffer.getvalue())
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["backend_changes"], ["backend/start.sh"])


if __name__ == "__main__":
    unittest.main()
