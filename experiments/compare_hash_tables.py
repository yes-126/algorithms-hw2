import csv
import math
import random
from dataclasses import dataclass
from pathlib import Path

from src.hash_table import HashTable, LinearProbingHashTable


DEFAULT_CAPACITY = 4093
DEFAULT_LOAD_FACTORS = tuple(step / 10 for step in range(1, 10))
DEFAULT_FAILURE_TRIALS = DEFAULT_CAPACITY
DEFAULT_SEED = 8026

CSV_COLUMNS = (
    "target_load",
    "actual_load",
    "capacity",
    "entries",
    "chain_success_measured",
    "chain_success_theory",
    "chain_failure_measured",
    "chain_failure_theory",
    "linear_success_measured",
    "linear_success_theory",
    "linear_failure_measured",
    "linear_failure_theory",
)


@dataclass(frozen=True)
class ComparisonResult:
    target_load: float
    actual_load: float
    capacity: int
    entries: int
    chain_success_average: float
    chain_success_theory: float
    chain_failure_average: float
    chain_failure_theory: float
    linear_success_average: float
    linear_success_theory: float
    linear_failure_average: float
    linear_failure_theory: float


def _random_key(generator, index):
    host = generator.getrandbits(64)
    return f"https://key-{host:016x}.example/{index:08x}"


def _make_keys(generator, count):
    return [_random_key(generator, index) for index in range(count)]


def run_comparison(
    load_factors=DEFAULT_LOAD_FACTORS,
    capacity=DEFAULT_CAPACITY,
    failure_trials=DEFAULT_FAILURE_TRIALS,
    seed=DEFAULT_SEED,
):
    if isinstance(capacity, bool) or not isinstance(capacity, int):
        raise TypeError("capacity must be an integer")
    if capacity <= 0:
        raise ValueError("capacity must be positive")
    if isinstance(failure_trials, bool) or not isinstance(failure_trials, int):
        raise TypeError("failure_trials must be an integer")
    if failure_trials <= 0:
        raise ValueError("failure_trials must be positive")

    load_factors = tuple(load_factors)
    if not load_factors:
        raise ValueError("at least one load factor is required")
    for load_factor in load_factors:
        if isinstance(load_factor, bool) or not isinstance(
            load_factor, (int, float)
        ):
            raise TypeError("load factors must be numbers")
        if not 0 < load_factor < 1:
            raise ValueError("linear probing load factors must be between 0 and 1")

    maximum_entries = max(int(load_factor * capacity) for load_factor in load_factors)
    if maximum_entries <= 0:
        raise ValueError("load factors must produce at least one entry")

    generator = random.Random(seed)
    keys = _make_keys(generator, maximum_entries)
    results = []

    for target_load in load_factors:
        entries = int(target_load * capacity)
        actual_load = entries / capacity
        chain_table = HashTable(capacity=capacity, max_load=None)
        linear_table = LinearProbingHashTable(capacity=capacity, max_load=None)
        selected_keys = keys[:entries]

        for value, key in enumerate(selected_keys):
            chain_table.put(key, value)
            linear_table.put(key, value)

        chain_success_total = 0
        linear_success_total = 0
        for value, key in enumerate(selected_keys):
            chain_value, chain_count = chain_table.get_with_count(key)
            linear_value, linear_count = linear_table.get_with_count(key)
            if chain_value != value or linear_value != value:
                raise RuntimeError("successful lookup returned an unexpected value")
            chain_success_total += chain_count
            linear_success_total += linear_count

        chain_failure_total = 0
        linear_failure_total = 0
        for trial in range(failure_trials):
            missing_key = f"https://miss-{trial}.example/{seed}"
            chain_value, chain_count = chain_table.get_with_count(missing_key)
            linear_value, linear_count = linear_table.get_with_count(missing_key)
            if chain_value is not None or linear_value is not None:
                raise RuntimeError("failure lookup unexpectedly found a key")
            chain_failure_total += chain_count
            linear_failure_total += linear_count

        results.append(
            ComparisonResult(
                target_load=float(target_load),
                actual_load=actual_load,
                capacity=capacity,
                entries=entries,
                chain_success_average=chain_success_total / entries,
                chain_success_theory=1 + actual_load / 2,
                chain_failure_average=chain_failure_total / failure_trials,
                chain_failure_theory=actual_load,
                linear_success_average=linear_success_total / entries,
                linear_success_theory=(1 + 1 / (1 - actual_load)) / 2,
                linear_failure_average=linear_failure_total / failure_trials,
                linear_failure_theory=(1 + 1 / (1 - actual_load) ** 2) / 2,
            )
        )

    return results


def write_results_csv(results, path):
    with Path(path).open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(CSV_COLUMNS)
        for result in results:
            writer.writerow(
                (
                    f"{result.target_load:.2f}",
                    f"{result.actual_load:.12f}",
                    result.capacity,
                    result.entries,
                    f"{result.chain_success_average:.8f}",
                    f"{result.chain_success_theory:.8f}",
                    f"{result.chain_failure_average:.8f}",
                    f"{result.chain_failure_theory:.8f}",
                    f"{result.linear_success_average:.8f}",
                    f"{result.linear_success_theory:.8f}",
                    f"{result.linear_failure_average:.8f}",
                    f"{result.linear_failure_theory:.8f}",
                )
            )


def print_results_table(results):
    headings = (
        "alpha",
        "chain success (meas/theory)",
        "chain failure (meas/theory)",
        "linear success (meas/theory)",
        "linear failure (meas/theory)",
    )
    rows = [
        (
            f"{result.actual_load:.3f}",
            f"{result.chain_success_average:.3f} / {result.chain_success_theory:.3f}",
            f"{result.chain_failure_average:.3f} / {result.chain_failure_theory:.3f}",
            f"{result.linear_success_average:.3f} / {result.linear_success_theory:.3f}",
            f"{result.linear_failure_average:.3f} / {result.linear_failure_theory:.3f}",
        )
        for result in results
    ]
    widths = [
        max(len(heading), *(len(row[index]) for row in rows))
        for index, heading in enumerate(headings)
    ]
    print(" | ".join(heading.ljust(widths[index]) for index, heading in enumerate(headings)))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(" | ".join(value.rjust(widths[index]) for index, value in enumerate(row)))


def write_svg(results, path):
    width = 1120
    height = 700
    left = 95
    right = 40
    top = 70
    bottom = 115
    plot_width = width - left - right
    plot_height = height - top - bottom
    y_max = max(
        1.0,
        *(getattr(result, name) for result in results for name in (
            "chain_success_average",
            "chain_success_theory",
            "chain_failure_average",
            "chain_failure_theory",
            "linear_success_average",
            "linear_success_theory",
            "linear_failure_average",
            "linear_failure_theory",
        )),
    )
    tick_step = 10 if y_max > 15 else 2
    y_max = math.ceil(y_max / tick_step) * tick_step

    min_load = min(result.actual_load for result in results)
    max_load = max(result.actual_load for result in results)

    def x_position(load_factor):
        if min_load == max_load:
            return left + plot_width / 2
        return left + (load_factor - min_load) / (max_load - min_load) * plot_width

    def y_position(comparisons):
        return top + (y_max - comparisons) / y_max * plot_height

    series = (
        ("Chaining success measured", "chain_success_average", "#1769aa", ""),
        ("Chaining success theory", "chain_success_theory", "#1769aa", "7 5"),
        ("Chaining failure measured", "chain_failure_average", "#25855a", ""),
        ("Chaining failure theory", "chain_failure_theory", "#25855a", "7 5"),
        ("Linear success measured", "linear_success_average", "#d17a00", ""),
        ("Linear success theory", "linear_success_theory", "#d17a00", "7 5"),
        ("Linear failure measured", "linear_failure_average", "#c43b3b", ""),
        ("Linear failure theory", "linear_failure_theory", "#c43b3b", "7 5"),
    )
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<title>Chaining and linear probing lookup costs</title>",
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width / 2}" y="32" text-anchor="middle" font-family="sans-serif" font-size="20">Chaining vs linear probing: measured and theoretical probes</text>',
    ]

    for tick in range(0, y_max + 1, tick_step):
        y = y_position(tick)
        lines.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{left + plot_width}" y2="{y:.2f}" stroke="#dddddd"/>'
        )
        lines.append(
            f'<text x="{left - 12}" y="{y + 5:.2f}" text-anchor="end" font-family="sans-serif" font-size="12">{tick}</text>'
        )

    for result in results:
        x = x_position(result.actual_load)
        lines.append(
            f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{top + plot_height}" stroke="#eeeeee"/>'
        )
        lines.append(
            f'<text x="{x:.2f}" y="{top + plot_height + 22}" text-anchor="middle" font-family="sans-serif" font-size="11">{result.target_load:.1f}</text>'
        )

    lines.extend(
        (
            f'<line x1="{left}" y1="{top + plot_height}" x2="{left + plot_width}" y2="{top + plot_height}" stroke="#333333"/>',
            f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_height}" stroke="#333333"/>',
            f'<text x="{left + plot_width / 2}" y="{height - 18}" text-anchor="middle" font-family="sans-serif" font-size="14">Load factor alpha (entries / slots)</text>',
            f'<text x="24" y="{top + plot_height / 2}" transform="rotate(-90 24 {top + plot_height / 2})" text-anchor="middle" font-family="sans-serif" font-size="14">Average comparisons / slots inspected</text>',
        )
    )

    for name, attribute, color, dash in series:
        points = " ".join(
            f"{x_position(result.actual_load):.2f},{y_position(getattr(result, attribute)):.2f}"
            for result in results
        )
        dash_attribute = f' stroke-dasharray="{dash}"' if dash else ""
        lines.append(
            f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2.5"{dash_attribute}/>'
        )
        for result in results:
            lines.append(
                f'<circle cx="{x_position(result.actual_load):.2f}" cy="{y_position(getattr(result, attribute)):.2f}" r="3" fill="{color}"/>'
            )

    legend_columns = (left, left + 255, left + 510, left + 765)
    for index, (name, _, color, dash) in enumerate(series):
        row = index // 4
        x = legend_columns[index % 4]
        y = height - 76 + row * 24
        dash_attribute = f' stroke-dasharray="{dash}"' if dash else ""
        lines.append(
            f'<line x1="{x}" y1="{y}" x2="{x + 25}" y2="{y}" stroke="{color}" stroke-width="2.5"{dash_attribute}/>'
        )
        lines.append(
            f'<text x="{x + 32}" y="{y + 4}" font-family="sans-serif" font-size="11">{name}</text>'
        )

    lines.append("</svg>")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    results = run_comparison()
    output_directory = Path(__file__).resolve().parent
    csv_path = output_directory / "comparison_results.csv"
    svg_path = output_directory / "hash_table_comparison.svg"
    write_results_csv(results, csv_path)
    write_svg(results, svg_path)
    print_results_table(results)
    print(f"\nCSV: {csv_path}")
    print(f"SVG: {svg_path}")


if __name__ == "__main__":
    main()
