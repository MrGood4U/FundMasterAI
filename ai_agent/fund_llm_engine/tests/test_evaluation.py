import os
import sys
import unittest
from copy import deepcopy
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fund_llm import config
from fund_llm.contracts import NavPoint
from fund_llm.evaluation import evaluate_analysis_result
from fund_llm.mock_pipeline import build_mock_input, run_mock_analysis, run_mock_analysis_for_input


def build_rating_eligible_input():
    payload = build_mock_input()
    point_count = config.MIN_NAV_POINTS_FOR_RATING + 5
    start = date(2025, 1, 1)
    payload.nav_series = [
        NavPoint(
            date=(start + timedelta(days=index)).isoformat(),
            nav=1.0 + index * 0.002,
        )
        for index in range(point_count)
    ]
    payload.benchmark_nav_series = [
        NavPoint(
            date=(start + timedelta(days=index)).isoformat(),
            nav=1.0 + index * 0.001,
        )
        for index in range(point_count)
    ]
    return payload


def refresh_agent_counts(result):
    result.metadata["success_agent_count"] = str(
        len([output for output in result.agent_outputs if output.status == "success"])
    )
    result.metadata["skipped_agent_count"] = str(
        len(
            [
                output
                for output in result.agent_outputs
                if output.status == "skipped" and output.stance != "not_applicable"
            ]
        )
    )
    result.metadata["not_applicable_agent_count"] = str(
        len(
            [
                output
                for output in result.agent_outputs
                if output.status == "skipped" and output.stance == "not_applicable"
            ]
        )
    )
    result.metadata["error_agent_count"] = str(
        len([output for output in result.agent_outputs if output.status == "error"])
    )


def mark_agent_error(result, agent_name):
    output = next(output for output in result.agent_outputs if output.agent_name == agent_name)
    output.status = "error"
    output.score = None
    output.stance = "mixed"
    output.key_points = []
    output.confidence = 0.0
    output.narrative = f"{agent_name} failed: injected test failure"
    refresh_agent_counts(result)


def mark_agent_insufficient(result, agent_name):
    output = next(output for output in result.agent_outputs if output.agent_name == agent_name)
    output.status = "skipped"
    output.score = None
    output.stance = "insufficient_data"
    output.confidence = 0.0
    output.narrative = f"{agent_name} skipped: injected insufficient data"
    refresh_agent_counts(result)


def get_check(report, name):
    return next(check for check in report.checks if check.name == name)


def mark_partial(result):
    result.metadata["analysis_status"] = "partial"
    refresh_agent_counts(result)


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

    def test_error_heavy_result_fails_execution_gate(self):
        payload = build_rating_eligible_input()
        result = run_mock_analysis_for_input(payload)
        for output in list(result.agent_outputs):
            if output.status == "success":
                mark_agent_error(result, output.agent_name)
        result.metadata["analysis_status"] = "technical_error"
        result.overall_rating = "unavailable"
        result.overall_score = None

        report = evaluate_analysis_result(payload, result)
        health_check = get_check(report, "agent_execution_health")

        self.assertFalse(health_check.passed)
        self.assertEqual(health_check.severity, "critical")
        self.assertEqual(report.overall_status, "fail")

    def test_single_technical_error_cannot_pass(self):
        payload = build_rating_eligible_input()
        result = run_mock_analysis_for_input(payload)
        mark_agent_error(result, "PerformanceAgent")
        result.metadata["analysis_status"] = "technical_error"
        result.overall_rating = "unavailable"
        result.overall_score = None

        report = evaluate_analysis_result(payload, result)
        health_check = get_check(report, "agent_execution_health")

        self.assertFalse(health_check.passed)
        self.assertEqual(health_check.severity, "high")
        self.assertNotEqual(report.overall_status, "pass")

    def test_valid_partial_aggregation_is_consistent_and_review_only(self):
        payload = build_rating_eligible_input()
        result = run_mock_analysis_for_input(payload)
        mark_agent_error(result, "SentimentAgent")
        result.metadata["analysis_status"] = "partial"

        report = evaluate_analysis_result(payload, result)

        self.assertTrue(get_check(report, "decision_eligibility").passed)
        self.assertTrue(get_check(report, "score_consistency").passed)
        health_check = get_check(report, "agent_execution_health")
        self.assertFalse(health_check.passed)
        self.assertEqual(health_check.severity, "high")
        self.assertEqual(report.overall_status, "review")

    def test_partial_rating_with_failed_core_agent_is_critical(self):
        payload = build_rating_eligible_input()
        result = run_mock_analysis_for_input(payload)
        mark_agent_error(result, "PerformanceAgent")
        result.metadata["analysis_status"] = "partial"

        report = evaluate_analysis_result(payload, result)
        decision_check = get_check(report, "decision_eligibility")

        self.assertFalse(decision_check.passed)
        self.assertEqual(decision_check.severity, "critical")
        self.assertTrue(
            any("PerformanceAgent" in detail for detail in decision_check.details)
        )
        self.assertEqual(report.overall_status, "fail")

    def test_partial_rating_below_score_coverage_quorum_is_critical(self):
        payload = build_rating_eligible_input()
        result = run_mock_analysis_for_input(payload)
        for agent_name in ("SentimentAgent", "SectorAgent", "MarketAgent"):
            mark_agent_insufficient(result, agent_name)
        result.metadata["analysis_status"] = "partial"

        report = evaluate_analysis_result(payload, result)
        decision_check = get_check(report, "decision_eligibility")

        self.assertFalse(decision_check.passed)
        self.assertTrue(
            any("50.00%" in detail for detail in decision_check.details)
        )
        self.assertEqual(report.overall_status, "fail")

    def test_partial_requires_directional_rating_and_non_null_score(self):
        payload = build_rating_eligible_input()
        result = run_mock_analysis_for_input(payload)
        result.metadata["analysis_status"] = "partial"
        result.overall_rating = "unavailable"
        result.overall_score = None

        report = evaluate_analysis_result(payload, result)

        self.assertFalse(get_check(report, "decision_eligibility").passed)
        self.assertFalse(get_check(report, "score_consistency").passed)
        self.assertEqual(report.overall_status, "fail")

    def test_missing_outputs_remain_in_fixed_rating_denominator(self):
        payload = build_rating_eligible_input()
        result = run_mock_analysis_for_input(payload)
        retained_names = {
            "PerformanceAgent",
            "RiskAgent",
            "ExposureAgent",
            "BondExposureAgent",
        }
        result.agent_outputs = [
            output
            for output in result.agent_outputs
            if output.agent_name in retained_names
        ]
        mark_partial(result)

        report = evaluate_analysis_result(payload, result)
        decision_check = get_check(report, "decision_eligibility")

        self.assertFalse(decision_check.passed)
        self.assertTrue(any("(3/6)" in detail for detail in decision_check.details))
        self.assertTrue(
            any(
                "Missing expected agent outputs" in detail
                for detail in get_check(report, "agent_execution_health").details
            )
        )

    def test_duplicate_output_cannot_supply_rating_quorum(self):
        payload = build_rating_eligible_input()
        result = run_mock_analysis_for_input(payload)
        sentiment = next(
            output for output in result.agent_outputs if output.agent_name == "SentimentAgent"
        )
        result.agent_outputs.append(deepcopy(sentiment))
        mark_agent_insufficient(result, "SectorAgent")
        mark_agent_insufficient(result, "MarketAgent")
        mark_partial(result)

        report = evaluate_analysis_result(payload, result)
        decision_check = get_check(report, "decision_eligibility")

        self.assertFalse(decision_check.passed)
        self.assertTrue(any("(3/6)" in detail for detail in decision_check.details))
        self.assertTrue(
            any(
                "Duplicate agent outputs" in detail and "SentimentAgent" in detail
                for detail in get_check(report, "agent_execution_health").details
            )
        )

    def test_nonfinite_and_out_of_range_scores_cannot_supply_quorum(self):
        payload = build_rating_eligible_input()
        result = run_mock_analysis_for_input(payload)
        next(
            output for output in result.agent_outputs if output.agent_name == "SentimentAgent"
        ).score = float("nan")
        next(
            output for output in result.agent_outputs if output.agent_name == "MarketAgent"
        ).score = 101.0
        mark_agent_insufficient(result, "SectorAgent")
        mark_partial(result)

        report = evaluate_analysis_result(payload, result)
        decision_check = get_check(report, "decision_eligibility")
        execution_check = get_check(report, "agent_execution_health")

        self.assertFalse(decision_check.passed)
        self.assertTrue(any("(3/6)" in detail for detail in decision_check.details))
        self.assertTrue(
            any(
                "Invalid scoring outputs" in detail
                and "SentimentAgent" in detail
                and "MarketAgent" in detail
                for detail in execution_check.details
            )
        )

    def test_unknown_agents_do_not_supply_rating_quorum(self):
        payload = build_rating_eligible_input()
        result = run_mock_analysis_for_input(payload)
        for agent_name in ("SentimentAgent", "SectorAgent", "MarketAgent"):
            mark_agent_insufficient(result, agent_name)
        template = next(
            output for output in result.agent_outputs if output.agent_name == "ExposureAgent"
        )
        for index in range(3):
            unknown_output = deepcopy(template)
            unknown_output.agent_name = f"UnknownAgent{index + 1}"
            result.agent_outputs.append(unknown_output)
        mark_partial(result)

        report = evaluate_analysis_result(payload, result)
        decision_check = get_check(report, "decision_eligibility")

        self.assertFalse(decision_check.passed)
        self.assertTrue(any("(3/6)" in detail for detail in decision_check.details))
        self.assertEqual(report.overall_status, "fail")

    def test_legitimate_insufficient_data_and_not_applicable_skips_are_healthy(self):
        payload = build_mock_input()
        payload.industry_exposure = {}
        payload.top_holdings_weight = None
        payload.news_summary = []
        payload.news_items = []
        payload.individual_analysis = []
        payload.profit_probability = []
        payload.nav_series = payload.nav_series[:2]

        result = run_mock_analysis_for_input(payload)
        report = evaluate_analysis_result(payload, result)
        health_check = get_check(report, "agent_execution_health")

        self.assertTrue(health_check.passed)
        self.assertTrue(
            any(output.stance == "insufficient_data" for output in result.agent_outputs)
        )
        self.assertTrue(
            any(output.stance == "not_applicable" for output in result.agent_outputs)
        )
        self.assertFalse(any(output.status == "success" for output in result.agent_outputs))

    def test_deterministic_narrative_fallback_is_not_a_technical_error(self):
        payload = build_rating_eligible_input()
        result = run_mock_analysis_for_input(payload)
        output = next(output for output in result.agent_outputs if output.status == "success")
        output.metadata["narrative_source"] = "deterministic_fallback"

        report = evaluate_analysis_result(payload, result)

        self.assertTrue(get_check(report, "agent_execution_health").passed)

    def test_invalid_skipped_state_forces_failure(self):
        payload = build_rating_eligible_input()
        result = run_mock_analysis_for_input(payload)
        output = next(output for output in result.agent_outputs if output.agent_name == "PerformanceAgent")
        output.status = "skipped"
        output.score = None
        output.stance = "neutral"
        refresh_agent_counts(result)

        report = evaluate_analysis_result(payload, result)
        health_check = get_check(report, "agent_execution_health")

        self.assertFalse(health_check.passed)
        self.assertEqual(health_check.severity, "critical")
        self.assertEqual(report.overall_status, "fail")

    def test_low_sample_abstention_is_score_consistent(self):
        payload = build_mock_input()
        payload.nav_series = payload.nav_series[:2]
        result = run_mock_analysis_for_input(payload)

        report = evaluate_analysis_result(payload, result)

        self.assertEqual(result.metadata.get("analysis_status"), "insufficient_data")
        self.assertEqual(result.overall_rating, "insufficient_data")
        self.assertIsNone(result.overall_score)
        self.assertTrue(get_check(report, "score_consistency").passed)
        self.assertTrue(get_check(report, "decision_eligibility").passed)

    def test_low_sample_directional_rating_fails_decision_gate(self):
        payload = build_mock_input()
        payload.nav_series = payload.nav_series[:2]
        result = run_mock_analysis_for_input(payload)
        result.metadata["analysis_status"] = "complete"
        result.overall_rating = "hold"
        result.overall_score = 60.0

        report = evaluate_analysis_result(payload, result)
        decision_check = get_check(report, "decision_eligibility")

        self.assertFalse(decision_check.passed)
        self.assertEqual(decision_check.severity, "critical")
        self.assertEqual(report.overall_status, "fail")


if __name__ == "__main__":
    unittest.main()
