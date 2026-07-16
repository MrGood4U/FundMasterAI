import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fund_llm.contracts import (
    AnalysisWindow,
    FundInfo,
    NavPoint,
    PortfolioAnalysisInput,
    PortfolioFundData,
)
from fund_llm.portfolio_pipeline import (
    run_mock_portfolio_analysis_for_input,
    run_portfolio_analysis_for_input,
)
from fund_llm.llm_client import MockLLMClient


def build_nav_series(drift_up: float, drift_down: float, point_count: int = 90):
    nav = 1.0
    series = []
    for day_index in range(point_count):
        series.append(NavPoint(date=f"2026-{(day_index // 28) + 1:02d}-{(day_index % 28) + 1:02d}", nav=round(nav, 6)))
        nav *= drift_up if day_index % 2 == 0 else drift_down
    return series


def build_portfolio_input(weights=(0.6, 0.4)) -> PortfolioAnalysisInput:
    fund_a = PortfolioFundData(
        fund_info=FundInfo(
            code="000001",
            name="Demo Mixed Fund",
            asset_type="fund_open",
            category="混合型-偏股",
        ),
        nav_series=build_nav_series(1.015, 0.995),
        weight=weights[0],
        requested_weight=weights[0],
    )
    fund_b = PortfolioFundData(
        fund_info=FundInfo(
            code="003358",
            name="Demo Bond Index Fund",
            asset_type="fund_open",
            category="债券型-债券指数",
        ),
        nav_series=build_nav_series(0.999, 1.004),
        weight=weights[1],
        requested_weight=weights[1],
    )
    return PortfolioAnalysisInput(
        request_id="portfolio-test-001",
        funds=[fund_a, fund_b],
        analysis_window=AnalysisWindow(start_date="2026-01-01", end_date="2026-04-06"),
        client_risk_profile="balanced",
        extra_context={"data_source": "unit_test", "weights_rescaled": "false"},
    )


class PortfolioPipelineTest(unittest.TestCase):
    def test_mock_pipeline_produces_full_result(self):
        result = run_mock_portfolio_analysis_for_input(
            build_portfolio_input(),
            mock_response="portfolio mock narrative",
        )

        self.assertEqual(result.request_id, "portfolio-test-001")
        self.assertIn(result.overall_rating, {"buy", "hold", "watch", "avoid"})
        self.assertGreaterEqual(result.overall_score, 0.0)
        self.assertLessEqual(result.overall_score, 100.0)
        self.assertEqual(result.summary, "portfolio mock narrative")
        self.assertEqual(result.metadata["llm_mode"], "mock")
        self.assertEqual(result.metadata["analysis_level"], "portfolio")
        self.assertEqual(result.metadata["fund_count"], "2")
        self.assertEqual(len(result.constituents), 2)
        self.assertEqual(result.constituents[0].code, "000001")
        self.assertAlmostEqual(result.constituents[0].weight, 0.6)

    def test_quant_metrics_include_diversification_evidence(self):
        result = run_mock_portfolio_analysis_for_input(build_portfolio_input())

        self.assertIn("diversification_benefit", result.quant_metrics)
        self.assertIn("weighted_average_volatility", result.quant_metrics)
        self.assertIn("sample_size", result.quant_metrics)
        for key in (
            "total_return",
            "annualized_return",
            "annualized_volatility",
            "max_drawdown",
            "sharpe_ratio",
            "sortino_ratio",
            "calmar_ratio",
            "positive_period_ratio",
        ):
            self.assertIn(key, result.quant_metrics)

    def test_trace_covers_alignment_composition_and_aggregation(self):
        result = run_mock_portfolio_analysis_for_input(build_portfolio_input())

        titles = [event.title for event in result.analysis_trace]
        self.assertIn("Aligned constituent NAV calendars", titles)
        self.assertIn("Composed weighted portfolio NAV", titles)
        self.assertIn("Aggregated portfolio view", titles)
        alignment_event = result.analysis_trace[0]
        self.assertEqual(alignment_event.evidence["fund_count"], 2)
        self.assertGreaterEqual(alignment_event.evidence["shared_nav_points"], 30)

    def test_insufficient_overlap_raises_value_error(self):
        payload = build_portfolio_input()
        payload.funds[0].nav_series = payload.funds[0].nav_series[:10]

        with self.assertRaises(ValueError) as context:
            run_mock_portfolio_analysis_for_input(payload)

        self.assertIn("common NAV date", str(context.exception))

    def test_missing_required_fields_raise_value_error(self):
        payload = build_portfolio_input()
        payload.funds = []

        with self.assertRaises(ValueError) as context:
            run_mock_portfolio_analysis_for_input(payload)

        self.assertIn("funds", str(context.exception))

    def test_llm_failure_falls_back_to_deterministic_summary(self):
        class BrokenLLMClient:
            def chat(self, system_prompt, user_prompt, **kwargs):
                raise RuntimeError("provider down")

        result = run_portfolio_analysis_for_input(build_portfolio_input(), BrokenLLMClient())

        self.assertEqual(result.metadata["summary_source"], "deterministic_fallback")
        self.assertTrue(result.summary)
        self.assertIn("portfolio", result.summary.lower())
        self.assertNotIn("score", result.summary.lower())
        self.assertNotIn("rating", result.summary.lower())
        for label in ("buy", "hold", "watch", "avoid"):
            self.assertNotIn(label, result.summary.lower())

    def test_lookthrough_fields_flow_into_result(self):
        payload = build_portfolio_input()
        payload.funds[0].top_holdings = [
            {"stock_code": "600519", "stock_name": "贵州茅台", "net_value_pct": "10.0", "quarter": "2026Q1"},
        ]
        payload.funds[1].top_holdings = [
            {"stock_code": "600519", "stock_name": "贵州茅台", "net_value_pct": "5.0", "quarter": "2026Q1"},
        ]
        payload.funds[0].industry_exposure = {"食品饮料": 0.40}
        payload.funds[0].asset_allocation = {"股票": 0.90, "现金": 0.10}

        result = run_mock_portfolio_analysis_for_input(payload)

        self.assertEqual(result.holdings_lookthrough["status"], "available")
        overlap = result.holdings_lookthrough["overlapping_holdings"][0]
        self.assertEqual(overlap["stock_code"], "600519")
        # 0.6*10% + 0.4*5% = 8%
        self.assertAlmostEqual(overlap["portfolio_weight"], 0.08)
        self.assertEqual(result.industry_lookthrough["status"], "partial")
        self.assertEqual(result.asset_allocation_lookthrough["status"], "partial")
        self.assertEqual(result.metadata["holdings_lookthrough_status"], "available")
        # 重叠暴露必须进入 chief 的风险陈述
        self.assertTrue(
            any("贵州茅台" in risk and "overlap" in risk for risk in result.main_risks),
            result.main_risks,
        )
        trace_titles = [event.title for event in result.analysis_trace]
        self.assertIn("Merged constituent holdings look-through", trace_titles)

    def test_lookthrough_degrades_to_missing_without_data(self):
        result = run_mock_portfolio_analysis_for_input(build_portfolio_input())

        self.assertEqual(result.holdings_lookthrough["status"], "missing")
        self.assertEqual(result.industry_lookthrough["status"], "missing")
        self.assertEqual(result.asset_allocation_lookthrough["status"], "missing")
        # 缺数据时不应出现编造的穿透陈述
        self.assertFalse(any("Look-through" in item for item in result.key_thesis))

    def test_weights_rescaled_flag_reaches_action_plan(self):
        payload = build_portfolio_input()
        payload.extra_context["weights_rescaled"] = "true"

        result = run_mock_portfolio_analysis_for_input(payload)

        self.assertEqual(result.metadata["weights_rescaled"], "true")
        self.assertTrue(
            any("rescaled" in item for item in result.action_plan),
            result.action_plan,
        )


class PortfolioChiefAgentScoreTest(unittest.TestCase):
    def test_positive_portfolio_scores_above_neutral(self):
        result = run_portfolio_analysis_for_input(
            build_portfolio_input(),
            MockLLMClient("narrative"),
        )

        self.assertGreater(result.overall_score, 50.0)
        self.assertIn("deterministic portfolio score", result.score_explanation)


if __name__ == "__main__":
    unittest.main()
