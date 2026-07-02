import os
import sys
import unittest
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fund_llm.contracts import FundInfo, NavPoint, PortfolioFundData, PortfolioPosition
from fund_llm.portfolio_analysis import (
    MIN_OVERLAP_POINTS,
    align_common_dates,
    build_constituent_metrics,
    build_portfolio_quant_metrics,
    compose_portfolio_nav,
    intersect_nav_dates,
    normalize_positions,
)

# 真实日历日期基准：start_day=1 对应 2026-01-01，往后按自然日递增，
# 跨月自动进位（不会生成 2026-01-40 这类后端不可能返回的日期）。
BASE_DATE = date(2026, 1, 1)


def build_nav_series(values, start_day=1):
    return [
        NavPoint(
            date=(BASE_DATE + timedelta(days=start_day - 1 + index)).isoformat(),
            nav=value,
        )
        for index, value in enumerate(values)
    ]


def build_fund(code, nav_series, weight, category="mixed", requested_weight=None):
    return PortfolioFundData(
        fund_info=FundInfo(code=code, name=f"Fund {code}", asset_type="fund_open", category=category),
        nav_series=nav_series,
        weight=weight,
        requested_weight=requested_weight if requested_weight is not None else weight,
    )


class NormalizePositionsTest(unittest.TestCase):
    def test_weights_are_normalized_to_one(self):
        positions = [
            PortfolioPosition(code="000001", weight=60),
            PortfolioPosition(code="003358", weight=40),
        ]

        normalized, was_rescaled = normalize_positions(positions)

        self.assertTrue(was_rescaled)
        self.assertAlmostEqual(normalized[0].weight, 0.6)
        self.assertAlmostEqual(normalized[1].weight, 0.4)
        self.assertAlmostEqual(sum(item.weight for item in normalized), 1.0)

    def test_already_normalized_weights_are_kept(self):
        positions = [
            PortfolioPosition(code="000001", weight=0.7),
            PortfolioPosition(code="003358", weight=0.3),
        ]

        normalized, was_rescaled = normalize_positions(positions)

        self.assertFalse(was_rescaled)
        self.assertAlmostEqual(normalized[0].weight, 0.7)

    def test_empty_positions_are_rejected(self):
        with self.assertRaises(ValueError):
            normalize_positions([])

    def test_non_positive_weight_is_rejected(self):
        with self.assertRaises(ValueError) as context:
            normalize_positions([PortfolioPosition(code="000001", weight=0.0)])
        self.assertIn("000001", str(context.exception))

    def test_duplicate_codes_are_rejected(self):
        with self.assertRaises(ValueError) as context:
            normalize_positions(
                [
                    PortfolioPosition(code="000001", weight=0.5),
                    PortfolioPosition(code="000001", weight=0.5),
                ]
            )
        self.assertIn("more than once", str(context.exception))

    def test_missing_code_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_positions([PortfolioPosition(code="", weight=1.0)])


class AlignCommonDatesTest(unittest.TestCase):
    def test_intersection_of_dates_is_used(self):
        # 40 个自然日会跨到 2 月，验证真实日历日期下的交集与排序。
        fund_a = build_fund("A", build_nav_series([1.0] * 40, start_day=1), weight=0.5)
        fund_b = build_fund("B", build_nav_series([1.0] * 40, start_day=5), weight=0.5)

        common_dates = align_common_dates([fund_a, fund_b])

        self.assertEqual(len(common_dates), 36)
        self.assertEqual(common_dates[0], "2026-01-05")
        self.assertEqual(common_dates[-1], "2026-02-09")
        self.assertEqual(common_dates, sorted(common_dates))

    def test_intersect_nav_dates_has_no_minimum_threshold(self):
        fund_a = build_fund("A", build_nav_series([1.0] * 5), weight=0.5)
        fund_b = build_fund("B", build_nav_series([1.0] * 5, start_day=3), weight=0.5)

        shared = intersect_nav_dates([fund_a, fund_b])

        self.assertEqual(shared, ["2026-01-03", "2026-01-04", "2026-01-05"])
        self.assertEqual(intersect_nav_dates([]), [])

    def test_insufficient_overlap_raises_with_fund_details(self):
        fund_a = build_fund("A", build_nav_series([1.0] * 10), weight=0.5)
        fund_b = build_fund("B", build_nav_series([1.0] * 10), weight=0.5)

        with self.assertRaises(ValueError) as context:
            align_common_dates([fund_a, fund_b])

        message = str(context.exception)
        self.assertIn(str(MIN_OVERLAP_POINTS), message)
        self.assertIn("A(10 NAV points)", message)
        self.assertIn("B(10 NAV points)", message)

    def test_disjoint_calendars_raise(self):
        fund_a = build_fund("A", build_nav_series([1.0] * 5, start_day=1), weight=0.5)
        fund_b = build_fund("B", build_nav_series([1.0] * 5, start_day=20), weight=0.5)

        with self.assertRaises(ValueError):
            align_common_dates([fund_a, fund_b])


class ComposePortfolioNavTest(unittest.TestCase):
    def test_single_period_return_is_exact_weighted_average(self):
        # Fund A gains 10%, fund B stays flat; 50/50 portfolio gains 5% for one period.
        fund_a = build_fund("A", build_nav_series([2.0, 2.2]), weight=0.5)
        fund_b = build_fund("B", build_nav_series([1.0, 1.0]), weight=0.5)
        common_dates = ["2026-01-01", "2026-01-02"]

        portfolio_nav = compose_portfolio_nav([fund_a, fund_b], common_dates)

        self.assertAlmostEqual(portfolio_nav[0].nav, 1.0)
        self.assertAlmostEqual(portfolio_nav[-1].nav, 1.05)

    def test_daily_rebalancing_compounds_weighted_daily_returns(self):
        # Fixed-weight (daily rebalanced) composition: each day contributes
        # 0.5 * fund A's daily return; fund B stays flat.
        fund_a = build_fund("A", build_nav_series([2.0, 2.1, 2.2]), weight=0.5)
        fund_b = build_fund("B", build_nav_series([1.0, 1.0, 1.0]), weight=0.5)
        common_dates = ["2026-01-01", "2026-01-02", "2026-01-03"]

        portfolio_nav = compose_portfolio_nav([fund_a, fund_b], common_dates)

        expected = (1 + 0.5 * (2.1 / 2.0 - 1)) * (1 + 0.5 * (2.2 / 2.1 - 1))
        self.assertAlmostEqual(portfolio_nav[-1].nav, expected, places=6)

    def test_absolute_nav_levels_are_irrelevant(self):
        # Same relative path at different absolute NAV levels must give the same portfolio.
        fund_high = build_fund("H", build_nav_series([5.0, 5.5]), weight=0.5)
        fund_low = build_fund("L", build_nav_series([0.5, 0.55]), weight=0.5)
        common_dates = ["2026-01-01", "2026-01-02"]

        portfolio_nav = compose_portfolio_nav([fund_high, fund_low], common_dates)

        self.assertAlmostEqual(portfolio_nav[-1].nav, 1.10)

    def test_zero_nav_raises(self):
        fund_a = build_fund("A", build_nav_series([0.0, 1.0]), weight=1.0)

        with self.assertRaises(ValueError):
            compose_portfolio_nav([fund_a], ["2026-01-01", "2026-01-02"])


class PortfolioMetricsTest(unittest.TestCase):
    def build_two_fund_setup(self):
        # Opposite zig-zag paths: individually volatile, jointly smooth.
        values_a = []
        values_b = []
        nav_a, nav_b = 1.0, 1.0
        for day_index in range(60):
            if day_index % 2 == 0:
                nav_a *= 1.02
                nav_b *= 0.99
            else:
                nav_a *= 0.99
                nav_b *= 1.02
            values_a.append(round(nav_a, 6))
            values_b.append(round(nav_b, 6))
        fund_a = build_fund("A", build_nav_series(values_a), weight=0.5)
        fund_b = build_fund("B", build_nav_series(values_b), weight=0.5, category="债券型-债券指数")
        return [fund_a, fund_b]

    def test_constituent_metrics_are_computed_on_aligned_window(self):
        funds = self.build_two_fund_setup()
        common_dates = align_common_dates(funds)

        constituents = build_constituent_metrics(funds, common_dates)

        self.assertEqual(len(constituents), 2)
        self.assertEqual(constituents[0].code, "A")
        self.assertEqual(constituents[0].nav_points, len(common_dates))
        self.assertEqual(constituents[1].normalized_fund_type, "bond_index_fund")
        self.assertGreater(constituents[0].annualized_volatility, 0.0)

    def test_diversification_benefit_is_positive_for_uncorrelated_funds(self):
        funds = self.build_two_fund_setup()
        common_dates = align_common_dates(funds)
        portfolio_nav = compose_portfolio_nav(funds, common_dates)
        constituents = build_constituent_metrics(funds, common_dates)

        metrics = build_portfolio_quant_metrics(portfolio_nav, constituents)

        self.assertGreater(metrics["diversification_benefit"], 0.0)
        self.assertLess(
            metrics["annualized_volatility"],
            metrics["weighted_average_volatility"],
        )
        self.assertEqual(metrics["sample_size"], float(len(common_dates)))

    def test_diversification_benefit_is_never_negative(self):
        # Perfectly correlated funds: daily-rebalanced composition guarantees
        # portfolio volatility <= weighted average volatility, so the benefit
        # must be >= 0 (about 0 here).
        values = []
        nav = 1.0
        for day_index in range(60):
            nav *= 1.01 if day_index % 2 == 0 else 0.995
            values.append(round(nav, 6))
        fund_a = build_fund("A", build_nav_series(values), weight=0.5)
        fund_b = build_fund("B", build_nav_series(values), weight=0.5)
        common_dates = align_common_dates([fund_a, fund_b])
        portfolio_nav = compose_portfolio_nav([fund_a, fund_b], common_dates)
        constituents = build_constituent_metrics([fund_a, fund_b], common_dates)

        metrics = build_portfolio_quant_metrics(portfolio_nav, constituents)

        self.assertGreaterEqual(metrics["diversification_benefit"], -1e-6)
        self.assertAlmostEqual(metrics["diversification_benefit"], 0.0, places=4)

    def test_portfolio_metrics_expose_fund_level_key_names(self):
        funds = self.build_two_fund_setup()
        common_dates = align_common_dates(funds)
        portfolio_nav = compose_portfolio_nav(funds, common_dates)
        constituents = build_constituent_metrics(funds, common_dates)

        metrics = build_portfolio_quant_metrics(portfolio_nav, constituents)

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
            self.assertIn(key, metrics)
        # 60 aligned points support the 1m rolling window but not 1y.
        self.assertIn("return_1m", metrics)
        self.assertNotIn("return_1y", metrics)


if __name__ == "__main__":
    unittest.main()
