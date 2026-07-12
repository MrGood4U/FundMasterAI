import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fund_llm.contracts import BenchmarkInfo, FundAnalysisInput, FundInfo, NavPoint
from fund_llm.feature_builder import FeatureBuilder
from fund_llm.fund_routing import AVAILABLE, MISSING_BACKEND_CAPABILITY, NOT_APPLICABLE


def build_long_nav_series(point_count: int, start_nav: float = 1.0) -> list[NavPoint]:
    nav = start_nav
    nav_series = []
    for day_index in range(point_count):
        nav_series.append(NavPoint(date=f"2026-01-{day_index + 1:03d}", nav=round(nav, 6)))
        if day_index % 2 == 0:
            nav *= 1.012
        else:
            nav *= 0.996
    return nav_series


def build_sample_input() -> FundAnalysisInput:
    return FundAnalysisInput(
        request_id="demo-001",
        fund_info=FundInfo(
            code="005827",
            name="易方达蓝筹精选混合",
            asset_type="fund_open",
            category="mixed",
            manager="张坤",
        ),
        nav_series=[
            NavPoint(date="2026-01-01", nav=1.00),
            NavPoint(date="2026-01-02", nav=1.05),
            NavPoint(date="2026-01-03", nav=1.02),
            NavPoint(date="2026-01-04", nav=1.10),
            NavPoint(date="2026-01-05", nav=1.08),
        ],
        industry_exposure={
            "食品饮料": 0.35,
            "互联网": 0.20,
            "医药": 0.15,
        },
        top_holdings_weight=0.58,
        news_summary=[
            "消费板块热度回升",
            "白酒行业预期改善",
        ],
    )


class FeatureBuilderTest(unittest.TestCase):
    def test_build_features(self):
        payload = build_sample_input()
        builder = FeatureBuilder()
        features = builder.build(payload)

        self.assertEqual(features.request_id, "demo-001")
        self.assertEqual(features.fund_info.name, "易方达蓝筹精选混合")
        self.assertEqual(round(features.return_metrics["total_return"], 4), 0.0800)
        self.assertEqual(round(features.return_metrics["return_since_inception"], 4), 0.0800)
        self.assertEqual(round(features.risk_metrics["max_drawdown"], 4), -0.0286)
        self.assertGreater(features.risk_metrics["annualized_volatility"], 0)
        self.assertEqual(features.exposure_metrics["industry_concentration"], 0.35)
        self.assertEqual(features.exposure_metrics["top_holdings_weight"], 0.58)
        self.assertEqual(features.data_quality_metrics["nav_point_count"], 5)
        self.assertFalse(features.data_quality_flags["supports_return_1m"])
        self.assertEqual(features.missing_fields, [])

    def test_build_features_with_benchmark_series(self):
        payload = build_sample_input()
        payload.benchmark = BenchmarkInfo(code="000300", name="沪深300", asset_type="index")
        payload.benchmark_nav_series = [
            NavPoint(date="2026-01-01", nav=1.00),
            NavPoint(date="2026-01-02", nav=1.03),
            NavPoint(date="2026-01-03", nav=1.01),
            NavPoint(date="2026-01-04", nav=1.05),
            NavPoint(date="2026-01-05", nav=1.04),
        ]
        builder = FeatureBuilder()

        features = builder.build(payload)

        self.assertIn("benchmark_total_return", features.benchmark_metrics)
        self.assertIn("excess_return", features.benchmark_metrics)
        self.assertTrue(features.data_quality_flags["has_benchmark"])

    def test_build_features_adds_windowed_metrics_when_history_is_sufficient(self):
        payload = build_sample_input()
        payload.nav_series = build_long_nav_series(280)
        payload.benchmark = BenchmarkInfo(code="000300", name="沪深300", asset_type="index")
        payload.benchmark_nav_series = build_long_nav_series(280, start_nav=0.95)
        builder = FeatureBuilder()

        features = builder.build(payload)

        self.assertIn("return_1m", features.return_metrics)
        self.assertIn("return_3m", features.return_metrics)
        self.assertIn("return_6m", features.return_metrics)
        self.assertIn("return_1y", features.return_metrics)
        self.assertIn("benchmark_return_1m", features.benchmark_metrics)
        self.assertIn("excess_return_1m", features.benchmark_metrics)
        self.assertIn("annualized_volatility_1m", features.risk_metrics)
        self.assertIn("max_drawdown_3m", features.risk_metrics)
        self.assertTrue(features.data_quality_flags["supports_return_1y"])
        self.assertTrue(features.data_quality_flags["supports_benchmark_return_1y"])
        self.assertEqual(features.data_quality_metrics["nav_point_count"], 280)
        self.assertEqual(features.data_quality_metrics["benchmark_nav_point_count"], 280)

    def test_build_features_marks_bond_equity_fields_not_applicable(self):
        payload = FundAnalysisInput(
            request_id="bond-003358",
            fund_info=FundInfo(
                code="003358",
                name="易方达中债7-10年期国开行债券指数A",
                asset_type="fund_open",
                category="债券型-债券指数",
            ),
            nav_series=[
                NavPoint(date="2026-01-01", nav=1.00),
                NavPoint(date="2026-01-02", nav=1.01),
            ],
            # Legacy real-input fixtures may use this aggregate for bond
            # positions, so it must not activate equity analysis by itself.
            top_holdings_weight=0.8364,
            extra_context={
                "data_source": "backend_function_registry",
                "available_backend_tools": "get_fund_hist,get_fund_individual_basic_info,get_fund_portfolio_holds",
            },
        )

        features = FeatureBuilder().build(payload)

        self.assertEqual(features.normalized_fund_type, "bond_index_fund")
        self.assertFalse(features.data_quality_flags["equity_exposure_applicable"])
        self.assertFalse(features.data_quality_flags["sector_analysis_applicable"])
        self.assertTrue(features.data_quality_flags["bond_exposure_applicable"])
        self.assertEqual(features.data_coverage["stock_holdings"], NOT_APPLICABLE)
        self.assertEqual(features.data_coverage["industry_exposure"], NOT_APPLICABLE)
        self.assertEqual(features.data_coverage["bond_holdings"], MISSING_BACKEND_CAPABILITY)
        self.assertNotIn("industry_exposure", features.missing_fields)
        self.assertNotIn("top_holdings_weight", features.missing_fields)
        self.assertIn("bond_holdings", features.missing_fields)
        self.assertIn("asset_allocation", features.missing_fields)

    def test_build_features_enables_equity_routes_for_secondary_bond_fund(self):
        payload = FundAnalysisInput(
            request_id="secondary-bond-000171",
            fund_info=FundInfo(
                code="000171",
                name="易方达裕丰回报债券A",
                asset_type="fund_open",
                category="债券型-普通债券",
            ),
            nav_series=[
                NavPoint(date="2026-01-01", nav=1.00),
                NavPoint(date="2026-01-02", nav=1.01),
            ],
            top_holdings_weight=0.1237,
            top_holdings=[
                {
                    "stock_code": f"stock-{index:02d}",
                    "weight_fraction": 0.1237 / 11,
                }
                for index in range(1, 12)
            ],
            industry_exposure={
                "制造业": 0.0712,
                "金融业": 0.0315,
                "信息技术": 0.0210,
            },
        )

        features = FeatureBuilder().build(payload)

        self.assertEqual(features.normalized_fund_type, "bond_fund")
        self.assertTrue(features.data_quality_flags["equity_exposure_applicable"])
        self.assertTrue(features.data_quality_flags["sector_analysis_applicable"])
        self.assertTrue(features.data_quality_flags["bond_exposure_applicable"])
        self.assertEqual(features.data_coverage["stock_holdings"], AVAILABLE)
        self.assertEqual(features.data_coverage["industry_exposure"], AVAILABLE)
        self.assertNotIn("top_holdings_weight", features.missing_fields)
        self.assertNotIn("industry_exposure", features.missing_fields)

    def test_build_features_extracts_bond_exposure_metrics(self):
        payload = FundAnalysisInput(
            request_id="bond-rich-003358",
            fund_info=FundInfo(
                code="003358",
                name="易方达中债7-10年期国开行债券指数A",
                asset_type="fund_open",
                category="index_fixed_income",
            ),
            nav_series=[
                NavPoint(date="2026-01-01", nav=1.00),
                NavPoint(date="2026-01-02", nav=1.01),
            ],
            bond_holdings=[
                {"bond_name": "20国开10", "pct": "21.28%"},
                {"bond_name": "21国开03", "pct": "19.96"},
                {"bond_name": "22国开05", "weight_fraction": 0.1504},
            ],
            asset_allocation={"债券": "86.00%", "现金": 0.07, "其他": 0.07},
        )

        features = FeatureBuilder().build(payload)

        self.assertEqual(features.normalized_fund_type, "bond_index_fund")
        self.assertEqual(features.data_coverage["bond_holdings"], AVAILABLE)
        self.assertEqual(features.data_coverage["asset_allocation"], AVAILABLE)
        self.assertTrue(features.data_quality_flags["has_bond_holdings"])
        self.assertTrue(features.data_quality_flags["has_asset_allocation"])
        self.assertEqual(features.data_quality_metrics["bond_holding_count"], 3)
        self.assertEqual(features.data_quality_metrics["asset_allocation_count"], 3)
        self.assertAlmostEqual(features.bond_exposure_metrics["bond_top_holding_weight"], 0.2128)
        self.assertAlmostEqual(features.bond_exposure_metrics["bond_top_three_weight"], 0.5628)
        self.assertAlmostEqual(features.bond_exposure_metrics["asset_bond_weight"], 0.86)
        self.assertNotIn("bond_holdings", features.missing_fields)
        self.assertNotIn("asset_allocation", features.missing_fields)

    def test_realistic_sub_one_bond_percentages_keep_backend_units(self):
        percentages = [
            3.18, 3.03, 2.51, 2.50, 2.09, 0.59, 0.53, 0.43, 0.42,
            0.34, 0.34, 0.28, 0.26, 0.24, 0.23, 0.22, 0.20, 0.19,
            0.19, 0.18, 0.17, 0.16, 0.16, 0.13, 0.13, 0.13, 0.09,
            0.08, 0.06, 0.06, 0.06, 0.06, 0.05, 0.05, 0.04, 0.04,
            0.03, 0.03, 0.01,
        ]
        payload = FundAnalysisInput(
            request_id="bond-realistic-000171",
            fund_info=FundInfo(
                code="000171",
                name="易方达裕丰回报债券A",
                asset_type="fund_open",
                category="债券型-普通债券",
            ),
            nav_series=[
                NavPoint(date="2026-01-01", nav=1.00),
                NavPoint(date="2026-01-02", nav=1.01),
            ],
            bond_holdings=[
                {"bond_name": f"Bond {index}", "pct": percentage}
                for index, percentage in enumerate(percentages, start=1)
            ],
            asset_allocation={"债券": 0.927, "股票": 0.1795, "现金": 0.0023, "其他": 0.009},
        )

        features = FeatureBuilder().build(payload)

        self.assertAlmostEqual(features.bond_exposure_metrics["bond_top_holding_weight"], 0.0318)
        self.assertAlmostEqual(features.bond_exposure_metrics["bond_top_three_weight"], 0.0872)
        self.assertAlmostEqual(features.bond_exposure_metrics["bond_total_disclosed_weight"], 0.1949)
        self.assertAlmostEqual(features.bond_exposure_metrics["asset_bond_weight"], 0.927)
        self.assertTrue(features.data_quality_flags["bond_holdings_valid"])
        self.assertTrue(features.data_quality_flags["asset_allocation_valid"])

    def test_gross_asset_fraction_above_one_is_not_divided_twice(self):
        payload = FundAnalysisInput(
            request_id="leveraged-bond-allocation",
            fund_info=FundInfo(
                code="000171",
                name="Leveraged Bond Fund",
                asset_type="fund_open",
                category="债券型-普通债券",
            ),
            nav_series=[
                NavPoint(date="2026-01-01", nav=1.00),
                NavPoint(date="2026-01-02", nav=1.01),
            ],
            asset_allocation={"债券": 1.12, "现金": 0.03},
        )

        features = FeatureBuilder().build(payload)

        self.assertAlmostEqual(features.asset_allocation_breakdown["债券"], 1.12)
        self.assertAlmostEqual(features.bond_exposure_metrics["asset_bond_weight"], 1.12)
        self.assertTrue(features.data_quality_flags["asset_allocation_valid"])

    def test_build_features_adds_nav_only_risk_adjusted_metrics(self):
        payload = build_sample_input()
        payload.nav_series = build_long_nav_series(280)

        features = FeatureBuilder().build(payload)

        # A 类指标只依赖净值序列，应当全部产出
        self.assertIn("annualized_return", features.return_metrics)
        self.assertIn("sharpe_ratio", features.risk_metrics)
        self.assertIn("sortino_ratio", features.risk_metrics)
        self.assertIn("calmar_ratio", features.risk_metrics)
        self.assertIn("positive_period_ratio", features.risk_metrics)

        positive_ratio = features.risk_metrics["positive_period_ratio"]
        self.assertGreaterEqual(positive_ratio, 0.0)
        self.assertLessEqual(positive_ratio, 1.0)

        # build_long_nav_series 总体上行，年化收益与夏普应为正且有限
        self.assertGreater(features.return_metrics["annualized_return"], 0.0)
        self.assertGreater(features.risk_metrics["sharpe_ratio"], 0.0)

    def test_risk_adjusted_metrics_are_safe_on_short_series(self):
        payload = build_sample_input()  # 仅 5 个净值点

        features = FeatureBuilder().build(payload)

        # 短序列也不应抛错或除零，应给出有限的数值
        self.assertIn("sharpe_ratio", features.risk_metrics)
        self.assertIn("calmar_ratio", features.risk_metrics)
        self.assertGreaterEqual(features.risk_metrics["positive_period_ratio"], 0.0)

    def test_quant_metrics_reliability_thresholds(self):
        from fund_llm.agents.chief_agent import _quant_metrics_reliability

        # 满一年(≥252个交易日)算高可靠;半年以上中等;更少则低
        self.assertEqual(_quant_metrics_reliability(300), "high")
        self.assertEqual(_quant_metrics_reliability(252), "high")
        self.assertEqual(_quant_metrics_reliability(200), "medium")
        self.assertEqual(_quant_metrics_reliability(120), "medium")
        self.assertEqual(_quant_metrics_reliability(60), "low")
        self.assertEqual(_quant_metrics_reliability(0), "low")

    def test_quant_metrics_includes_sample_size(self):
        from fund_llm.agents.chief_agent import _build_quant_metrics

        payload = build_sample_input()
        payload.nav_series = build_long_nav_series(280)
        features = FeatureBuilder().build(payload)

        quant_metrics = _build_quant_metrics(features)
        self.assertEqual(quant_metrics["sample_size"], 280.0)
        self.assertIn("sharpe_ratio", quant_metrics)


if __name__ == "__main__":
    unittest.main()
