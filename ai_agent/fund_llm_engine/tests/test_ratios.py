import math
import unittest

from fund_llm.ratios import (
    canonical_fraction,
    holding_weight_fraction,
    normalize_backend_holding,
    percentage_points_to_fraction,
    to_finite_float,
)


class RatioContractTest(unittest.TestCase):
    def test_backend_percentage_points_are_always_divided_by_one_hundred(self):
        cases = {
            0.0: 0.0,
            0.99: 0.0099,
            1.00: 0.01,
            1.01: 0.0101,
            112.0: 1.12,
        }
        for raw_value, expected in cases.items():
            with self.subTest(raw_value=raw_value):
                self.assertAlmostEqual(
                    percentage_points_to_fraction(raw_value),
                    expected,
                )

    def test_internal_fraction_is_not_reinterpreted_by_magnitude(self):
        self.assertAlmostEqual(canonical_fraction(0.0059), 0.0059)
        self.assertAlmostEqual(canonical_fraction(1.12), 1.12)
        self.assertAlmostEqual(canonical_fraction("0.59%"), 0.0059)

    def test_backend_holding_keeps_raw_percentage_and_adds_fraction(self):
        row = normalize_backend_holding({"pct": 0.59, "bond_name": "Small Bond"})

        self.assertEqual(row["pct"], 0.59)
        self.assertAlmostEqual(row["weight_fraction"], 0.0059)
        self.assertAlmostEqual(holding_weight_fraction(row), 0.0059)

    def test_explicit_fraction_wins_over_raw_percentage(self):
        row = {"pct": 99.0, "weight_fraction": 0.007}
        self.assertAlmostEqual(holding_weight_fraction(row), 0.007)

    def test_zero_percentage_is_not_lost_by_truthiness(self):
        row = normalize_backend_holding({"pct": 0.0, "net_value_pct": None})
        self.assertEqual(row["weight_fraction"], 0.0)

    def test_nonfinite_values_are_rejected(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                self.assertIsNone(to_finite_float(value))
                self.assertIsNone(percentage_points_to_fraction(value))
                self.assertIsNone(canonical_fraction(value))


if __name__ == "__main__":
    unittest.main()
