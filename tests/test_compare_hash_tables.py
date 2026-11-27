import csv
import tempfile
import unittest
from pathlib import Path

from experiments.compare_hash_tables import (
    DEFAULT_CAPACITY,
    run_comparison,
    write_results_csv,
    write_svg,
)


class CompareHashTablesTest(unittest.TestCase):
    def test_both_implementations_use_same_load_and_theoretical_values(self):
        results = run_comparison(
            load_factors=(0.1, 0.9),
            capacity=101,
            failure_trials=80,
            seed=41,
        )

        self.assertEqual(DEFAULT_CAPACITY, 4093)
        self.assertEqual([result.entries for result in results], [10, 90])
        for result in results:
            alpha = result.entries / result.capacity
            self.assertEqual(result.actual_load, alpha)
            self.assertAlmostEqual(result.chain_success_theory, 1 + alpha / 2)
            self.assertAlmostEqual(result.chain_failure_theory, alpha)
            self.assertAlmostEqual(
                result.linear_success_theory,
                (1 + 1 / (1 - alpha)) / 2,
            )
            self.assertAlmostEqual(
                result.linear_failure_theory,
                (1 + 1 / (1 - alpha) ** 2) / 2,
            )
            self.assertGreaterEqual(result.chain_success_average, 1)
            self.assertGreaterEqual(result.linear_success_average, 1)
            self.assertGreaterEqual(result.chain_failure_average, 0)
            self.assertGreaterEqual(result.linear_failure_average, 1)

    def test_seed_makes_the_comparison_reproducible(self):
        arguments = {
            "load_factors": (0.2, 0.6),
            "capacity": 97,
            "failure_trials": 50,
            "seed": 17,
        }

        self.assertEqual(run_comparison(**arguments), run_comparison(**arguments))

    def test_writers_output_both_measured_and_theoretical_series(self):
        results = run_comparison(
            load_factors=(0.2, 0.4, 0.6),
            capacity=101,
            failure_trials=50,
            seed=29,
        )
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "comparison.csv"
            svg_path = Path(directory) / "comparison.svg"

            write_results_csv(results, csv_path)
            write_svg(results, svg_path)

            with csv_path.open(newline="", encoding="utf-8") as file:
                rows = list(csv.DictReader(file))
            self.assertEqual(len(rows), len(results))
            for column in (
                "chain_success_measured",
                "chain_success_theory",
                "chain_failure_measured",
                "chain_failure_theory",
                "linear_success_measured",
                "linear_success_theory",
                "linear_failure_measured",
                "linear_failure_theory",
            ):
                self.assertIn(column, rows[0])

            svg = svg_path.read_text(encoding="utf-8")
            self.assertIn("<svg", svg)
            self.assertIn("Chaining success measured", svg)
            self.assertIn("Linear failure theory", svg)


if __name__ == "__main__":
    unittest.main()
