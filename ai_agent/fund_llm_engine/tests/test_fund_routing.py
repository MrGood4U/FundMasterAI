import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fund_llm.contracts import FundAnalysisInput, FundInfo, NavPoint
from fund_llm.fund_routing import (
    AVAILABLE,
    MISSING,
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

    def test_classifies_fixed_income_index_as_bond_like(self):
        profile = classify_fund_type("index_fixed_income")

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

    def test_classifies_etf_feeder_from_fund_name(self):
        profile = classify_fund_type(
            "指数型-股票",
            "南方标普红利低波50ETF联接A",
        )

        self.assertEqual(profile.normalized_type, "etf_feeder_fund")
        self.assertEqual(profile.family, "etf_feeder")
        self.assertFalse(profile.equity_exposure_applicable)
        self.assertFalse(profile.sector_analysis_applicable)
        self.assertFalse(profile.bond_exposure_applicable)

    def test_etf_feeder_direct_holdings_do_not_reactivate_equity_routes(self):
        payload = FundAnalysisInput(
            request_id="feeder-008163",
            fund_info=FundInfo(
                code="008163",
                name="南方标普红利低波50ETF联接A",
                asset_type="fund_open",
                category="指数型-股票",
            ),
            nav_series=[NavPoint(date="2026-01-01", nav=1.0)],
            top_holdings_weight=0.0027,
            top_holdings=[{"stock_code": "residual", "weight_fraction": 0.0027}],
            industry_exposure={"制造业": 0.0022},
        )

        coverage = build_data_coverage(payload)

        self.assertEqual(coverage["stock_holdings"], NOT_APPLICABLE)
        self.assertEqual(coverage["industry_exposure"], NOT_APPLICABLE)

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

    def test_coverage_accepts_structured_bond_payload_fields(self):
        payload = FundAnalysisInput(
            request_id="demo-bond-structured",
            fund_info=FundInfo(
                code="003358",
                name="易方达中债7-10年期国开行债券指数A",
                asset_type="fund_open",
                category="index_fixed_income",
            ),
            nav_series=[NavPoint(date="2026-01-01", nav=1.0)],
            bond_holdings=[{"bond_name": "20国开10", "pct": "21.28%"}],
            asset_allocation={"债券": 0.86, "现金": 0.07},
        )

        coverage = build_data_coverage(payload)

        self.assertEqual(coverage["bond_holdings"], AVAILABLE)
        self.assertEqual(coverage["asset_allocation"], AVAILABLE)

    def test_coverage_expands_bond_default_when_equity_data_is_disclosed(self):
        stock_payload = FundAnalysisInput(
            request_id="secondary-bond-stock-data",
            fund_info=FundInfo(
                code="000171",
                name="易方达裕丰回报债券A",
                asset_type="fund_open",
                category="债券型-普通债券",
            ),
            nav_series=[NavPoint(date="2026-01-01", nav=1.0)],
            top_holdings_weight=0.1237,
            top_holdings=[{"stock_code": "600000", "weight_fraction": 0.1237}],
        )

        stock_coverage = build_data_coverage(stock_payload)

        self.assertEqual(stock_coverage["stock_holdings"], AVAILABLE)
        self.assertEqual(stock_coverage["industry_exposure"], MISSING)

        industry_payload = FundAnalysisInput(
            request_id="secondary-bond-industry-data",
            fund_info=stock_payload.fund_info,
            nav_series=stock_payload.nav_series,
            industry_exposure={"制造业": 0.1237},
        )

        industry_coverage = build_data_coverage(industry_payload)

        self.assertEqual(industry_coverage["stock_holdings"], MISSING)
        self.assertEqual(industry_coverage["industry_exposure"], AVAILABLE)


if __name__ == "__main__":
    unittest.main()
