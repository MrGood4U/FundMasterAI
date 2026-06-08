import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fund_llm.contracts import FundAnalysisInput, FundInfo, NavPoint
from fund_llm.fund_routing import (
    AVAILABLE,
    MISSING_BACKEND_CAPABILITY,
    NOT_APPLICABLE,
    build_data_coverage,
    classify_fund_type,
)


class FundRoutingTest(unittest.TestCase):
    def test_classifies_bond_index_from_backend_fund_type(self):
        profile = classify_fund_type("债券型-债券指数")

        self.assertEqual(profile.normalized_type, "bond_index_fund")
        self.assertEqual(profile.family, "bond")
        self.assertFalse(profile.equity_exposure_applicable)
        self.assertTrue(profile.bond_exposure_applicable)

    def test_classifies_mixed_fund_as_equity_like(self):
        profile = classify_fund_type("混合型-偏股")

        self.assertEqual(profile.normalized_type, "mixed_fund")
        self.assertEqual(profile.family, "equity_like")
        self.assertTrue(profile.equity_exposure_applicable)
        self.assertFalse(profile.bond_exposure_applicable)

    def test_coverage_marks_bond_specific_backend_gaps(self):
        payload = FundAnalysisInput(
            request_id="demo-bond",
            fund_info=FundInfo(
                code="003358",
                name="易方达中债7-10年期国开行债券指数A",
                asset_type="fund_open",
                category="债券型-债券指数",
            ),
            nav_series=[NavPoint(date="2026-01-01", nav=1.0)],
            extra_context={
                "data_source": "backend_function_registry",
                "available_backend_tools": "get_fund_hist,get_fund_individual_basic_info,get_fund_portfolio_holds",
            },
        )

        coverage = build_data_coverage(payload)

        self.assertEqual(coverage["nav"], AVAILABLE)
        self.assertEqual(coverage["stock_holdings"], NOT_APPLICABLE)
        self.assertEqual(coverage["industry_exposure"], NOT_APPLICABLE)
        self.assertEqual(coverage["bond_holdings"], MISSING_BACKEND_CAPABILITY)
        self.assertEqual(coverage["asset_allocation"], MISSING_BACKEND_CAPABILITY)

    def test_coverage_accepts_new_bond_and_asset_backend_tools(self):
        payload = FundAnalysisInput(
            request_id="demo-bond-rich",
            fund_info=FundInfo(
                code="003358",
                name="易方达中债7-10年期国开行债券指数A",
                asset_type="fund_open",
                category="债券型-债券指数",
            ),
            nav_series=[NavPoint(date="2026-01-01", nav=1.0)],
            extra_context={
                "data_source": "backend_function_registry",
                "available_backend_tools": (
                    "get_fund_hist,get_fund_individual_basic_info,"
                    "get_fund_portfolio_hold_bond,get_fund_individual_detail_hold"
                ),
                "bond_holdings_count": "3",
                "asset_allocation_count": "4",
            },
        )

        coverage = build_data_coverage(payload)

        self.assertEqual(coverage["bond_holdings"], AVAILABLE)
        self.assertEqual(coverage["asset_allocation"], AVAILABLE)


if __name__ == "__main__":
    unittest.main()
