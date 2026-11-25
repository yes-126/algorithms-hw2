import csv
import tempfile
import unittest
from pathlib import Path

from experiments.probe_experiment import (
    FAILURE_TRIALS,
    TABLE_CAPACITY,
    run_experiment,
    write_results_csv,
    write_svg,
)


class ProbeExperimentTest(unittest.TestCase):
    def test_experiment_uses_fixed_capacity_and_reports_theoretical_values(self):
        results = run_experiment(
            load_factors=(0.25, 4.0),
            capacity=13,
            failure_trials=100,
            seed=17,
        )

        self.assertEqual(TABLE_CAPACITY, 4093)
        self.assertGreater(FAILURE_TRIALS, 0)
        self.assertEqual([result.entries for result in results], [3, 52])
        for result in results:
            self.assertEqual(result.actual_load, result.entries / 13)
            self.assertAlmostEqual(
                result.success_theory, 1 + result.actual_load / 2
            )
            self.assertAlmostEqual(result.failure_theory, result.actual_load)
            self.assertGreaterEqual(result.success_average, 1)
            self.assertGreaterEqual(result.failure_average, 0)

    def test_seed_makes_the_experiment_reproducible(self):
        arguments = {
            "load_factors": (0.25, 1.0),
            "capacity": 17,
            "failure_trials": 40,
            "seed": 23,
        }

        first = run_experiment(**arguments)
        second = run_experiment(**arguments)

        self.assertEqual(first, second)

    def test_writers_create_comparable_csv_and_svg_outputs(self):
        results = run_experiment(
            load_factors=(0.5, 1.0),
            capacity=19,
            failure_trials=30,
            seed=31,
        )
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "results.csv"
            svg_path = Path(directory) / "graph.svg"

            write_results_csv(results, csv_path)
            write_svg(results, svg_path)

            with csv_path.open(newline="", encoding="utf-8") as file:
                rows = list(csv.DictReader(file))
            self.assertEqual(len(rows), len(results))
            self.assertIn("success_theory", rows[0])
            self.assertIn("failure_theory", rows[0])
            svg = svg_path.read_text(encoding="utf-8")
            self.assertIn("<svg", svg)
            self.assertIn("Success measured", svg)
            self.assertIn("Failure theory", svg)


if __name__ == "__main__":
    unittest.main()
