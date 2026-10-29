"""Testes determinísticos da estrutura, sem rede nem credenciais."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from market_structure import structure


class MarketStructureTests(unittest.TestCase):
    def candles(self):
        return [{"high": str(102 + (i % 5)), "low": str(98 + (i % 5)), "close": str(100 + (i % 5))} for i in range(80)]

    def test_structure_fields(self):
        result = structure(self.candles(), 2.0)
        self.assertIn(result["structure"], ("higher_highs_higher_lows", "lower_highs_lower_lows", "mixed_or_undetermined"))
        self.assertEqual(result["retest"], "not_evaluated")
        self.assertEqual(result["pivot_rule"], "2_left_2_right_confirmed")

    def test_latest_two_candles_cannot_create_pivots(self):
        candles = self.candles()
        baseline = structure(candles, 2.0)
        candles[-1]["high"] = "9999"
        result = structure(candles, 2.0)
        self.assertEqual(result["confirmed_swing_highs"], baseline["confirmed_swing_highs"])
        self.assertEqual(result["last_confirmed_swing_high"], baseline["last_confirmed_swing_high"])

    def test_short_history_fails(self):
        with self.assertRaises(ValueError):
            structure(self.candles()[:20], 2.0)


if __name__ == "__main__":
    unittest.main()
