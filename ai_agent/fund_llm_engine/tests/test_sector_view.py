import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fund_llm.contracts import FundInfo
from fund_llm.sector_pipeline import (
    run_mock_sector_view_for_funds,
    run_sector_view_for_funds,
)
from fund_llm.sector_view import SectorViewFund, build_sector_view, classify_sector_status


def build_fund(code, category="混合型-偏股", exposure=None):
    return SectorViewFund(
        fund_info=FundInfo(code=code, name=f"Fund {code}", asset_type="fund_open", category=category),
        industry_exposure=exposure or {},
    )


class SectorStatusTest(unittest.TestCase):
    def test_equity_fund_with_data_is_available(self):
        fund = build_fund("000001", exposure={"食品饮料": 0.3})
        self.assertEqual(classify_sector_status(fund), "available")

    def test_equity_fund_without_data_is_insufficient(self):
        fund = build_fund("000001")
        self.assertEqual(classify_sector_status(fund), "insufficient_data")

    def test_bond_fund_is_not_applicable_even_without_data(self):
        fund = build_fund("003358", category="债券型-债券指数")
        self.assertEqual(classify_sector_status(fund), "not_applicable")


class BuildSectorViewTest(unittest.TestCase):
    def build_three_funds(self):
        fund_a = build_fund("A", exposure={"食品饮料": 0.40, "医药": 0.20})
        fund_b = build_fund("B", exposure={"食品饮料": 0.10, "电力设备": 0.30})
        fund_bond = build_fund("C", category="债券型-债券指数")
        return [fund_a, fund_b, fund_bond]

    def test_matrix_ranks_sectors_by_average_weight(self):
        view = build_sector_view(self.build_three_funds())

        self.assertEqual(view["status"], "partial")
        top_row = view["sector_matrix"][0]
        # 食品饮料平均 = (40% + 10%) / 2 只有数据的基金 = 25%
        self.assertEqual(top_row["sector"], "食品饮料")
        self.assertAlmostEqual(top_row["average_weight"], 0.25)
        self.assertEqual(top_row["funds_holding"], 2)
        self.assertEqual(top_row["max_fund"], "A")
        self.assertAlmostEqual(top_row["max_weight"], 0.40)

    def test_common_sectors_require_two_or_more_funds(self):
        view = build_sector_view(self.build_three_funds())

        self.assertEqual(view["common_sectors"], ["食品饮料"])

    def test_funds_without_data_are_listed_with_status(self):
        view = build_sector_view(self.build_three_funds())

        self.assertEqual(view["funds_without_data"], ["C"])
        bond_row = [row for row in view["funds"] if row["code"] == "C"][0]
        self.assertEqual(bond_row["sector_status"], "not_applicable")
        self.assertEqual(bond_row["top_sector"], "")

    def test_missing_status_when_no_fund_has_data(self):
        view = build_sector_view([build_fund("A"), build_fund("B")])

        self.assertEqual(view["status"], "missing")
        self.assertEqual(view["sector_matrix"], [])

    def test_empty_fund_list_raises(self):
        with self.assertRaises(ValueError):
            build_sector_view([])


class SectorPipelineTest(unittest.TestCase):
    def test_mock_pipeline_produces_full_result(self):
        funds = [
            build_fund("A", exposure={"食品饮料": 0.40}),
            build_fund("B", exposure={"食品饮料": 0.10, "电力设备": 0.30}),
        ]

        result = run_mock_sector_view_for_funds(funds, context={"data_source": "unit_test"})

        self.assertEqual(result["request_id"], "sector-view-A-B")
        self.assertEqual(result["status"], "available")
        self.assertEqual(result["summary"], "Mock sector comparison narrative.")
        self.assertEqual(result["metadata"]["llm_mode"], "mock")
        self.assertEqual(result["metadata"]["analysis_level"], "sector")
        trace_titles = [event["title"] for event in result["analysis_trace"]]
        self.assertIn("Built sector comparison matrix", trace_titles)

    def test_llm_failure_falls_back_to_deterministic_summary(self):
        class BrokenLLMClient:
            def chat(self, system_prompt, user_prompt, **kwargs):
                raise RuntimeError("provider down")

        funds = [
            build_fund("A", exposure={"食品饮料": 0.40}),
            build_fund("C", category="债券型-债券指数"),
        ]

        result = run_sector_view_for_funds(funds, BrokenLLMClient())

        self.assertEqual(result["metadata"]["summary_source"], "deterministic_fallback")
        self.assertIn("食品饮料", result["summary"])
        # 缺数据的基金必须被明确说明，而不是被编造行业结论
        self.assertIn("C", result["summary"])


if __name__ == "__main__":
    unittest.main()
