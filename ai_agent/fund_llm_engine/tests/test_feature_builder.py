import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fund_llm.contracts import BenchmarkInfo, FundAnalysisInput, FundInfo, NavPoint
from fund_llm.feature_builder import FeatureBuilder


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


if __name__ == "__main__":
    unittest.main()
